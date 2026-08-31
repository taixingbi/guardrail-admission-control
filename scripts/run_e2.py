#!/usr/bin/env python3
"""E2 formal: multi-tenant contention with frozen/live G_light q(x).

Bg is the gateway safety budget (0.4 rps), not ApplyGuardrail provider capacity.
Tenant A τ=0.75 vs B τ=0.40 only diverge when 0.40 ≤ q < 0.75.
5 reps. Mid-q oversample + B-unsafe boost so that band is actually tested.
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import time
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv

from gasc.clients.bedrock import apply_guardrail, bedrock_runtime
from gasc.limiter import StrongLimiter
from gasc.replay_data import load_scored_prompts, q_for, replay_dir, split_q_bands, split_safe_unsafe
from gasc.report import aggregate, applied_strong, fmt_stat, stat_pack
from gasc.scheduler import SchedulerInputs, decide, policy_compliant
from gasc.schemas import RunRecord, TenantPolicy

BG = 0.4
R_GATEWAY = 3.01
STRONG_FRAC = 1.3
DURATION_S = 120.0
REPS = 5
MID_Q_FRAC = 0.25
B_UNSAFE_P = 0.50
MIXES = ((0.90, 0.10), (0.70, 0.30), (0.50, 0.50), (0.30, 0.70))
POLICIES = ("always_strong", "risk_only", "load_aware", "proposed")
TENANTS = {
    "A": TenantPolicy(tenant_id="A", tau=0.75, slo_ms=600, reserved_share=0.0),
    "B": TenantPolicy(tenant_id="B", tau=0.40, slo_ms=800, reserved_share=0.4),
}
T_STRONG_MS = 215.0
QUEUE_TIMEOUT_S = 2.0


def _overflow(policy: str) -> str:
    return "queue" if policy in {"always_strong", "load_aware"} else "reject"


def _reserved(policy: str) -> dict[str, float]:
    return {"A": 0.0, "B": 0.4} if policy == "proposed" else {}


def _q_band(q: float) -> str:
    if q < 0.40:
        return "both_direct"
    if q < 0.75:
        return "tenant_split"
    return "both_strong"


def _pick(rng: random.Random, tenant: TenantPolicy, safe, unsafe, mid, p_unsafe):
    if mid and rng.random() < MID_Q_FRAC:
        return rng.choice(mid)
    if tenant.tenant_id == "B" and unsafe and rng.random() < B_UNSAFE_P:
        return rng.choice(unsafe)
    pool = unsafe if rng.random() < p_unsafe else safe
    return rng.choice(pool)


async def _one(*, client, guardrail_id, version, limiter, policy, tenant, prompt, rng, api_lock) -> RunRecord:
    t0 = time.perf_counter()
    q = q_for(prompt)
    available = limiter.strong_available(tenant.tenant_id)
    if policy in {"always_strong", "load_aware"}:
        available = True
    decision = decide(
        SchedulerInputs(
            q=q,
            tenant=tenant,
            policy=policy,  # type: ignore[arg-type]
            fail_closed=True,
            use_tenant=policy == "proposed",
            strong_available=available,
            est_strong_wait_ms=limiter.estimated_wait_ms(tenant.tenant_id),
            t_strong_ms=T_STRONG_MS,
            t_llm_ms=0.0,
            global_tau=0.5,
        )
    )
    route = decision.route
    action = None
    acquired = False
    if route == "strong":
        got = await limiter.acquire(tenant.tenant_id, timeout_s=QUEUE_TIMEOUT_S)
        if got.ok:
            acquired = True
            async with api_lock:
                out = await asyncio.to_thread(
                    apply_guardrail,
                    client,
                    guardrail_id=guardrail_id,
                    guardrail_version=version,
                    text=prompt.text,
                )
            action = out.get("action")
        else:
            route = "reject"
            decision = decision.model_copy(update={"route": "reject", "reason": got.reason})
    if acquired:
        await limiter.release(tenant.tenant_id)
    latency_ms = (time.perf_counter() - t0) * 1000
    admitted = route in {"direct", "strong"} and not decision.bypass
    if action == "GUARDRAIL_INTERVENED":
        admitted = False
        route = "reject"
        decision = decision.model_copy(update={"route": "reject", "reason": "guardrail_block"})
    gt_unsafe = prompt.target_label == "unsafe"
    return RunRecord(
        request_id=str(rng.random()),
        tenant_id=tenant.tenant_id,
        variant_id=prompt.variant_id,
        variant=prompt.variant,
        gt_label=prompt.target_label,
        policy=policy,  # type: ignore[arg-type]
        q=q,
        g_light_label="REVIEW" if q >= 0.5 else "SAFE",
        decision=decision,
        route=route,  # type: ignore[arg-type]
        admitted_to_llm=admitted,
        latency_ms=latency_ms,
        slo_ms=tenant.slo_ms,
        policy_compliant=policy_compliant(decision, route),  # type: ignore[arg-type]
        safe=not (gt_unsafe and admitted),
        slo_ok=latency_ms <= tenant.slo_ms,
        apply_guardrail_action=action,
        metadata={
            "apply_guardrail_action": action,
            "q_band": _q_band(q),
            "source": (prompt.metadata or {}).get("source"),
        },
    )


def _cell_metrics(recs: list[RunRecord], *, policy: str, mix, duration_s: float, rep: int) -> dict:
    pa, pb = mix
    recs_b = [r for r in recs if r.tenant_id == "B"]
    recs_a = [r for r in recs if r.tenant_id == "A"]
    split_a = [r for r in recs_a if r.metadata.get("q_band") == "tenant_split"]
    split_b = [r for r in recs_b if r.metadata.get("q_band") == "tenant_split"]
    overall = aggregate(recs, duration_s=duration_s)
    return {
        **overall,
        "policy": policy,
        "mix_a": pa,
        "mix_b": pb,
        "rep": rep,
        "n_a": len(recs_a),
        "n_b": len(recs_b),
        "g_safe_a": aggregate(recs_a, duration_s=duration_s)["safe_slo_goodput"] if recs_a else None,
        "g_safe_b": aggregate(recs_b, duration_s=duration_s)["safe_slo_goodput"] if recs_b else None,
        "n_need_b": sum(1 for r in recs_b if r.decision.need_strong),
        "n_checked_b": sum(1 for r in recs_b if r.decision.need_strong and applied_strong(r)),
        "n_starved_b": sum(1 for r in recs_b if r.decision.need_strong and not applied_strong(r)),
        "n_b_unsafe": sum(1 for r in recs_b if r.gt_label == "unsafe"),
        "uar_b": aggregate(recs_b, duration_s=duration_s)["unsafe_admission_rate"] if recs_b else None,
        "n_split_a": len(split_a),
        "n_split_b": len(split_b),
        "split_a_direct": sum(1 for r in split_a if r.decision.route == "direct" or r.route == "direct"),
        "split_b_need_strong": sum(1 for r in split_b if r.decision.need_strong),
        "split_b_checked": sum(
            1 for r in split_b if r.decision.need_strong and applied_strong(r)
        ),
    }


async def _cell(*, client, guardrail_id, version, policy, mix, safe, unsafe, mid, rep) -> dict:
    limiter = StrongLimiter(
        inflight_limit=2,
        queue_max=16,
        reserved_share=_reserved(policy),
        overflow_mode=_overflow(policy),
        bg_rps=BG,
        burst=1,
    )
    api_lock = asyncio.Lock()
    pa, pb = mix
    rng = random.Random(170 + rep * 97 + int(pa * 100) + POLICIES.index(policy) * 13)
    interval = 1.0 / R_GATEWAY
    p_unsafe = (STRONG_FRAC * BG) / R_GATEWAY
    n_slots = int(DURATION_S / interval)
    planned = []
    for _ in range(n_slots):
        tenant = TENANTS["A"] if rng.random() < pa else TENANTS["B"]
        planned.append((tenant, _pick(rng, tenant, safe, unsafe, mid, p_unsafe)))
    t_start = time.perf_counter()

    async def _scheduled(i: int, tenant: TenantPolicy, prompt) -> RunRecord:
        delay = t_start + i * interval - time.perf_counter()
        if delay > 0:
            await asyncio.sleep(delay)
        return await _one(
            client=client,
            guardrail_id=guardrail_id,
            version=version,
            limiter=limiter,
            policy=policy,
            tenant=tenant,
            prompt=prompt,
            rng=rng,
            api_lock=api_lock,
        )

    recs = list(
        await asyncio.gather(*[_scheduled(i, tenant, prompt) for i, (tenant, prompt) in enumerate(planned)])
    )
    return {
        "metrics": _cell_metrics(recs, policy=policy, mix=mix, duration_s=DURATION_S, rep=rep),
        "records": [json.loads(r.model_dump_json()) for r in recs],
    }


def _pool_reps(cells: list[dict]) -> list[dict]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for m in cells:
        groups[(m["policy"], m["mix_a"], m["mix_b"])].append(m)
    out = []
    for (policy, pa, pb), rows in groups.items():
        n = len(rows)
        out.append(
            {
                "policy": policy,
                "mix_a": pa,
                "mix_b": pb,
                "reps": n,
                "safe_slo_goodput": stat_pack([r["safe_slo_goodput"] for r in rows]),
                "g_safe_b": stat_pack([r["g_safe_b"] for r in rows]),
                "n_need_b": sum(r["n_need_b"] for r in rows),
                "n_checked_b": sum(r["n_checked_b"] for r in rows),
                "n_starved_b": sum(r["n_starved_b"] for r in rows),
                "n_b_unsafe": sum(r["n_b_unsafe"] for r in rows),
                "uar_b": stat_pack([r["uar_b"] for r in rows]),
                "n_split_a": sum(r["n_split_a"] for r in rows),
                "n_split_b": sum(r["n_split_b"] for r in rows),
                "split_a_direct": sum(r["split_a_direct"] for r in rows),
                "split_b_need_strong": sum(r["split_b_need_strong"] for r in rows),
                "split_b_checked": sum(r["split_b_checked"] for r in rows),
            }
        )
    out.sort(key=lambda m: (POLICIES.index(m["policy"]), -m["mix_a"]))
    return out


async def _run() -> dict:
    root = Path(__file__).resolve().parents[1]
    load_dotenv(root / ".env")
    gid = os.environ["GASC_GUARDRAIL_ID"]
    gver = os.environ.get("GASC_GUARDRAIL_VERSION", "1")
    scored = load_scored_prompts()
    safe, unsafe = split_safe_unsafe(scored)
    bands = split_q_bands(scored)
    mid = bands["tenant_split"]
    print(
        f"E2 formal n={len(scored)} safe={len(safe)} unsafe={len(unsafe)} "
        f"tenant_split={len(mid)} both_strong={len(bands['both_strong'])} "
        f"{DURATION_S:.0f}s x {REPS} reps Bg={BG}",
        flush=True,
    )
    if len(mid) < 5:
        raise RuntimeError(f"tenant-split band too small ({len(mid)}); need live q in [0.40, 0.75)")
    client = bedrock_runtime(os.environ.get("AWS_REGION", "us-east-1"))
    out = replay_dir("e2")
    cells = []
    for rep in range(REPS):
        for policy in POLICIES:
            for mix in MIXES:
                print(f"E2 r{rep} {policy} A:B={mix[0]:.0%}:{mix[1]:.0%} …", flush=True)
                cell = await _cell(
                    client=client,
                    guardrail_id=gid,
                    version=gver,
                    policy=policy,
                    mix=mix,
                    safe=safe,
                    unsafe=unsafe,
                    mid=mid,
                    rep=rep,
                )
                print(json.dumps(cell["metrics"], indent=2), flush=True)
                cells.append(cell["metrics"])
                (out / f"r{rep}_{policy}_{mix[0]:.2f}_{mix[1]:.2f}.jsonl").write_text(
                    "\n".join(json.dumps(r) for r in cell["records"]) + "\n"
                )
    return {
        "bg_rps": BG,
        "r_gateway": R_GATEWAY,
        "strong_frac_of_bg": STRONG_FRAC,
        "duration_s": DURATION_S,
        "reps": REPS,
        "q_source": "frozen_g_light",
        "n_scored": len(scored),
        "n_tenant_split": len(mid),
        "cells": cells,
        "pooled": _pool_reps(cells),
    }


def main() -> int:
    summary = asyncio.run(_run())
    out = replay_dir("e2")
    (out / "metrics.json").write_text(json.dumps(summary, indent=2))
    lines = [
        "# E2 multi-tenant contention (frozen minilm-l12-h384 q, 5 reps)",
        "",
        f"Gateway safety budget Bg={BG} rps (not ApplyGuardrail provider capacity). "
        f"R_gateway={R_GATEWAY}, {DURATION_S:.0f}s/cell × {REPS} reps.",
        "q = frozen Function URL MiniLM. Tenant-split band is 0.40 ≤ q < 0.75 (A direct, B strong).",
        "Isolation = checked vs starved among B required-strong. Paper cells are median [p25, p75].",
        "MiniLM is a screener; ApplyGuardrail is the authority. Do not retune τ on XSTest/WildGuardTest.",
        "",
        "## Tenant-split routing (pooled)",
        "",
        "| policy | A:B | split_A | A direct | split_B | B need_strong | B checked |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for m in summary["pooled"]:
        lines.append(
            f"| {m['policy']} | {m['mix_a']:.0%}:{m['mix_b']:.0%} | "
            f"{m['n_split_a']} | {m['split_a_direct']} | {m['n_split_b']} | "
            f"{m['split_b_need_strong']} | {m['split_b_checked']} |"
        )
    lines += [
        "",
        "## Isolation (pooled B required-strong)",
        "",
        "| policy | A:B | G_safe | G_safe_B | need_B | checked_B | starved_B | coverage | n_B_unsafe | UAR_B |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for m in summary["pooled"]:
        need = m["n_need_b"] or 0
        cov = (m["n_checked_b"] / need) if need else 0.0
        lines.append(
            f"| {m['policy']} | {m['mix_a']:.0%}:{m['mix_b']:.0%} | "
            f"{fmt_stat(m['safe_slo_goodput'])} | {fmt_stat(m['g_safe_b'])} | "
            f"{m['n_need_b']} | {m['n_checked_b']} | {m['n_starved_b']} | "
            f"{cov:.1%} | {m['n_b_unsafe']} | {fmt_stat(m['uar_b'])} |"
        )
    lines += [
        "",
        "Coverage = checked / need among B required-strong. UAR_B includes MiniLM false negatives",
        "(GT-unsafe with q below τ_B); that is classifier error, not fail-open bypass.",
        "Proposed guarantees policy compliance conditional on q, not GT safety.",
    ]
    (out / "metrics.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
