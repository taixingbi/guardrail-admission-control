#!/usr/bin/env python3
"""E2: multi-tenant contention. Strong demand ≈ 1.3 Rg. Vary A:B mix.

Proposed reserves 40% of ApplyGuardrail budget for sensitive Tenant B.
Other policies share one bucket — A can starve B at 90:10.
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import time
from pathlib import Path

from dotenv import load_dotenv

from gasc.clients.bedrock import apply_guardrail, bedrock_runtime
from gasc.limiter import StrongLimiter
from gasc.replay_data import load_live_q, load_replay_prompts, q_for, replay_dir, split_safe_unsafe
from gasc.report import aggregate
from gasc.scheduler import SchedulerInputs, decide, policy_compliant
from gasc.schemas import RunRecord, TenantPolicy

RG = 0.4
R_GATEWAY = 3.01
STRONG_FRAC = 1.3
DURATION_S = 120.0
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


async def _one(*, client, guardrail_id, version, limiter, policy, tenant, prompt, rng, api_lock, live_q) -> RunRecord:
    t0 = time.perf_counter()
    q = q_for(prompt, live_q)
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
        metadata={"apply_guardrail_action": action},
    )


async def _cell(*, client, guardrail_id, version, policy, mix, prompts_safe, prompts_unsafe, live_q) -> dict:
    limiter = StrongLimiter(
        inflight_limit=2,
        queue_max=16,
        reserved_share=_reserved(policy),
        overflow_mode=_overflow(policy),
        rg_rps=RG,
        burst=1,
    )
    api_lock = asyncio.Lock()
    pa, pb = mix
    rng = random.Random(17 + int(pa * 100) + POLICIES.index(policy) * 10)
    interval = 1.0 / R_GATEWAY
    p_unsafe = (STRONG_FRAC * RG) / R_GATEWAY
    n_slots = int(DURATION_S / interval)
    planned: list[tuple[TenantPolicy, object]] = []
    for _ in range(n_slots):
        tenant = TENANTS["A"] if rng.random() < pa else TENANTS["B"]
        pool = prompts_unsafe if rng.random() < p_unsafe else prompts_safe
        planned.append((tenant, rng.choice(pool)))
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
            live_q=live_q,
        )

    recs = list(
        await asyncio.gather(*[_scheduled(i, tenant, prompt) for i, (tenant, prompt) in enumerate(planned)])
    )
    overall = aggregate(recs, duration_s=DURATION_S)
    recs_b = [r for r in recs if r.tenant_id == "B"]
    recs_a = [r for r in recs if r.tenant_id == "A"]
    metrics = {
        **overall,
        "policy": policy,
        "mix_a": pa,
        "mix_b": pb,
        "n_a": len(recs_a),
        "n_b": len(recs_b),
        "g_safe_a": aggregate(recs_a, duration_s=DURATION_S)["safe_slo_goodput"] if recs_a else None,
        "g_safe_b": aggregate(recs_b, duration_s=DURATION_S)["safe_slo_goodput"] if recs_b else None,
        "reject_b": sum(1 for r in recs_b if r.route == "reject") / max(len(recs_b), 1),
        "reject_need_b": (
            sum(1 for r in recs_b if r.decision.need_strong and r.route == "reject")
            / max(sum(1 for r in recs_b if r.decision.need_strong), 1)
        ),
        "n_need_b": sum(1 for r in recs_b if r.decision.need_strong),
        "n_strong_b": sum(1 for r in recs_b if r.route == "strong"),
        "n_checked_b": sum(
            1
            for r in recs_b
            if r.decision.need_strong and r.metadata.get("apply_guardrail_action") is not None
        ),
        "n_starved_b": sum(
            1
            for r in recs_b
            if r.decision.need_strong and r.metadata.get("apply_guardrail_action") is None
        ),
        "n_b_unsafe": sum(1 for r in recs_b if r.gt_label == "unsafe"),
        "uar_b": aggregate(recs_b, duration_s=DURATION_S)["unsafe_admission_rate"] if recs_b else None,
        "slo_b": aggregate(recs_b, duration_s=DURATION_S)["critical_tenant_slo_attainment"],
    }
    return {"metrics": metrics, "records": [json.loads(r.model_dump_json()) for r in recs]}


async def _run() -> dict:
    root = Path(__file__).resolve().parents[1]
    load_dotenv(root / ".env")
    gid = os.environ["GASC_GUARDRAIL_ID"]
    gver = os.environ.get("GASC_GUARDRAIL_VERSION", "1")
    frozen = load_replay_prompts()
    safe, unsafe = split_safe_unsafe(frozen)
    live_q = load_live_q()
    print(
        f"E2 replay n={len(frozen)} safe={len(safe)} unsafe={len(unsafe)} live_q={len(live_q)} {DURATION_S:.0f}s",
        flush=True,
    )
    client = bedrock_runtime(os.environ.get("AWS_REGION", "us-east-1"))
    cells = []
    out = replay_dir("e2")
    out.mkdir(parents=True, exist_ok=True)
    for policy in POLICIES:
        for mix in MIXES:
            print(f"E2 {policy} A:B={mix[0]:.0%}:{mix[1]:.0%} …", flush=True)
            cell = await _cell(
                client=client,
                guardrail_id=gid,
                version=gver,
                policy=policy,
                mix=mix,
                prompts_safe=safe,
                prompts_unsafe=unsafe,
                live_q=live_q,
            )
            print(json.dumps(cell["metrics"], indent=2), flush=True)
            cells.append(cell["metrics"])
            (out / f"{policy}_{mix[0]:.2f}_{mix[1]:.2f}.jsonl").write_text(
                "\n".join(json.dumps(r) for r in cell["records"]) + "\n"
            )
    return {
        "rg": RG,
        "r_gateway": R_GATEWAY,
        "strong_frac_of_rg": STRONG_FRAC,
        "duration_s": DURATION_S,
        "q_source": "e0a_live" if live_q else "oracle",
        "n_live_q": len(live_q),
        "cells": cells,
    }


def main() -> int:
    summary = asyncio.run(_run())
    out = replay_dir("e2")
    (out / "metrics.json").write_text(json.dumps(summary, indent=2))
    q_src = summary.get("q_source", "oracle")
    lines = [
        "# E2 multi-tenant contention (freeze replay, 120s)",
        "",
        f"Strong demand {STRONG_FRAC} Rg, R_gateway={R_GATEWAY}, {DURATION_S:.0f}s/cell. q={q_src}.",
        "Proposed reserves 40% of Rg for Tenant B. Other policies share one bucket.",
        "`G_safe_B` is dominated by safe-direct. Isolation = checked vs starved among B required-strong.",
        "35s freeze cell archived in `results/replay/e2_35s/`.",
        "",
        "| policy | A:B | G_safe | G_safe_B | need_B | checked_B | starved_B | n_B_unsafe | UAR_B |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for m in summary["cells"]:
        def fmt(x):
            return "—" if x is None else f"{x:.3f}"

        lines.append(
            f"| {m['policy']} | {m['mix_a']:.0%}:{m['mix_b']:.0%} | "
            f"{m['safe_slo_goodput']:.3f} | {fmt(m['g_safe_b'])} | "
            f"{m['n_need_b']} | {m['n_checked_b']} | {m['n_starved_b']} | "
            f"{m['n_b_unsafe']} | {fmt(m['uar_b'])} |"
        )
    (out / "metrics.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
