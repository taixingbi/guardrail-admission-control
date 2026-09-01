#!/usr/bin/env python3
"""E2 formal: multi-tenant contention with frozen/live G_light q(x).

Bg is the gateway safety budget (0.4 rps), not ApplyGuardrail provider capacity.
Tenant A τ=0.75 vs B τ=0.40 only diverge when 0.40 ≤ q < 0.75.
5 reps. Mid-q oversample + B-unsafe boost so that band is actually tested.
"""

from __future__ import annotations

import asyncio
import json
import random
import time
from collections import defaultdict

from gasc.io import write_jsonl
from gasc.replay_data import load_scored_prompts, q_for, results_dir, split_q_bands, split_safe_unsafe
from gasc.report import aggregate, applied_strong, fmt_stat, stat_pack
from gasc.replay_exec import (
    BG,
    POLICY_ORDER,
    R_GATEWAY,
    TENANT_A,
    TENANT_B,
    bedrock_session,
    make_limiter,
    overflow_mode,
    run_scheduled,
)
from gasc.schemas import RunRecord, TenantPolicy

STRONG_FRAC = 1.3
DURATION_S = 120.0
REPS = 5
MID_Q_FRAC = 0.25
B_UNSAFE_P = 0.50
MIXES = ((0.90, 0.10), (0.70, 0.30), (0.50, 0.50), (0.30, 0.70))
POLICIES = POLICY_ORDER
TENANTS = {"A": TENANT_A, "B": TENANT_B}


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
    q = q_for(prompt)
    return await run_scheduled(
        client=client,
        guardrail_id=guardrail_id,
        version=version,
        limiter=limiter,
        prompt=prompt,
        tenant=tenant,
        policy=policy,
        q=q,
        rng=rng,
        api_lock=api_lock,
        metadata={"q_band": _q_band(q), "source": (prompt.metadata or {}).get("source")},
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
    limiter = make_limiter(overflow=overflow_mode(policy), reserved=_reserved(policy))
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
        "records": recs,
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
    env = bedrock_session()
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
    out = results_dir("e2")
    cells = []
    for rep in range(REPS):
        for policy in POLICIES:
            for mix in MIXES:
                print(f"E2 r{rep} {policy} A:B={mix[0]:.0%}:{mix[1]:.0%} …", flush=True)
                cell = await _cell(
                    client=env["client"],
                    guardrail_id=env["guardrail_id"],
                    version=env["version"],
                    policy=policy,
                    mix=mix,
                    safe=safe,
                    unsafe=unsafe,
                    mid=mid,
                    rep=rep,
                )
                print(json.dumps(cell["metrics"], indent=2), flush=True)
                cells.append(cell["metrics"])
                write_jsonl(out / f"r{rep}_{policy}_{mix[0]:.2f}_{mix[1]:.2f}.jsonl", cell["records"])
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
    out = results_dir("e2")
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
