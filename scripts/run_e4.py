#!/usr/bin/env python3
"""E4: safety-capacity exhaustion. Gateway RPS fixed; suspicious mix 5%→50%→5%.

Attack inflates ApplyGuardrail demand without raising LLM offered load.
Tenant A only. Frozen Function URL q. Live ApplyGuardrail; no Maverick.
Phenomenon experiment: do not use E4 to claim Proposed dominates other policies.
"""

from __future__ import annotations

import asyncio
import json
import random
import time

from gasc.replay_data import load_live_q, load_replay_prompts, q_for, results_dir, split_safe_unsafe
from gasc.replay_exec import (
    BG,
    POLICY_ORDER,
    R_GATEWAY,
    TENANT_A,
    bedrock_session,
    make_limiter,
    need_occupancy,
    overflow_mode,
    run_scheduled,
)
from gasc.report import aggregate, fmt_stat, pool_by
from gasc.schemas import RunRecord

DURATION_S = 420.0
BIN_S = 10.0
REPS = 5
PHASES = (
    (120.0, 0.05),
    (300.0, 0.50),
    (420.0, 0.05),
)
POLICIES = POLICY_ORDER
TENANT = TENANT_A


def _sus_at(t_s: float) -> float:
    for until, frac in PHASES:
        if t_s < until:
            return frac
    return PHASES[-1][1]


def _offered_bg(sus: float) -> float:
    return (sus * R_GATEWAY) / BG


async def _one(*, client, guardrail_id, version, limiter, policy, prompt, rng, api_lock, t_s, live_q) -> RunRecord:
    sus = _sus_at(t_s)
    return await run_scheduled(
        client=client,
        guardrail_id=guardrail_id,
        version=version,
        limiter=limiter,
        prompt=prompt,
        tenant=TENANT,
        policy=policy,
        q=q_for(prompt, live_q),
        rng=rng,
        api_lock=api_lock,
        metadata={
            "t_s": t_s,
            "suspicious_frac": sus,
            "offered_strong_frac_of_bg": _offered_bg(sus),
        },
    )


def _window_metrics(recs: list[RunRecord], duration_s: float) -> dict:
    m = aggregate(recs, duration_s=duration_s)
    m.update(need_occupancy(recs))
    return m


async def _cell(*, client, guardrail_id, version, policy, prompts_safe, prompts_unsafe, live_q, rep: int = 0) -> dict:
    limiter = make_limiter(overflow=overflow_mode(policy))
    api_lock = asyncio.Lock()
    rng = random.Random(40 + POLICIES.index(policy) * 19 + rep * 1000)
    interval = 1.0 / R_GATEWAY
    n_slots = int(DURATION_S / interval)
    planned = []
    for i in range(n_slots):
        t_s = i * interval
        pool = prompts_unsafe if rng.random() < _sus_at(t_s) else prompts_safe
        planned.append((t_s, rng.choice(pool)))
    t_start = time.perf_counter()

    async def _scheduled(i: int, t_s: float, prompt) -> RunRecord:
        delay = t_start + i * interval - time.perf_counter()
        if delay > 0:
            await asyncio.sleep(delay)
        return await _one(
            client=client,
            guardrail_id=guardrail_id,
            version=version,
            limiter=limiter,
            policy=policy,
            prompt=prompt,
            rng=rng,
            api_lock=api_lock,
            t_s=t_s,
            live_q=live_q,
        )

    recs = list(await asyncio.gather(*[_scheduled(i, t_s, p) for i, (t_s, p) in enumerate(planned)]))
    overall = _window_metrics(recs, DURATION_S)
    overall["policy"] = policy
    overall["rep"] = rep
    phases = []
    prev = 0.0
    for until, sus in PHASES:
        chunk = [r for r in recs if prev <= float(r.metadata["t_s"]) < until]
        row = _window_metrics(chunk, until - prev)
        row.update(
            {
                "policy": policy,
                "phase": f"{prev:.0f}-{until:.0f}s",
                "suspicious_frac": sus,
                "offered_strong_frac_of_bg": _offered_bg(sus),
                "n": len(chunk),
            }
        )
        phases.append(row)
        prev = until
    series = []
    n_bins = int(DURATION_S / BIN_S)
    for b in range(n_bins):
        lo, hi = b * BIN_S, (b + 1) * BIN_S
        chunk = [r for r in recs if lo <= float(r.metadata["t_s"]) < hi]
        row = _window_metrics(chunk, BIN_S)
        sus = _sus_at(lo)
        row.update(
            {
                "t0": lo,
                "t1": hi,
                "n": len(chunk),
                "suspicious_frac": sus,
                "offered_strong_frac_of_bg": _offered_bg(sus),
            }
        )
        series.append(row)
    return {
        "metrics": overall,
        "phases": phases,
        "series": series,
        "records": [json.loads(r.model_dump_json()) for r in recs],
    }


async def _run() -> dict:
    env = bedrock_session()
    frozen = load_replay_prompts()
    safe, unsafe = split_safe_unsafe(frozen)
    live_q = load_live_q(required=True)
    print(
        f"E4 replay n={len(frozen)} safe={len(safe)} unsafe={len(unsafe)} "
        f"frozen_q={len(live_q)} {REPS} reps",
        flush=True,
    )
    out = results_dir("e4")
    cells = []
    for rep in range(REPS):
        for policy in POLICIES:
            print(f"E4 r{rep} {policy} 420s …", flush=True)
            cell = await _cell(
                client=env["client"],
                guardrail_id=env["guardrail_id"],
                version=env["version"],
                policy=policy,
                prompts_safe=safe,
                prompts_unsafe=unsafe,
                live_q=live_q,
                rep=rep,
            )
            print(json.dumps({"policy": policy, "rep": rep, "overall": cell["metrics"], "phases": cell["phases"]}, indent=2), flush=True)
            (out / f"r{rep}_{policy}.jsonl").write_text("\n".join(json.dumps(r) for r in cell["records"]) + "\n")
            (out / f"r{rep}_{policy}_series.json").write_text(json.dumps(cell["series"], indent=2))
            cells.append({"overall": cell["metrics"], "phases": cell["phases"], "series": cell["series"]})
    overall_rows = [c["overall"] for c in cells]
    return {
        "bg": BG,
        "r_gateway": R_GATEWAY,
        "duration_s": DURATION_S,
        "bin_s": BIN_S,
        "reps": REPS,
        "phases": [
            {
                "until_s": u,
                "suspicious_frac": f,
                "offered_strong_frac_of_bg": _offered_bg(f),
            }
            for u, f in PHASES
        ],
        "q_source": "frozen_g_light",
        "n_live_q": len(live_q),
        "cells": cells,
        "pooled": pool_by(
            overall_rows,
            ("policy",),
            ("safe_slo_goodput", "unsafe_admission_rate", "reject_rate"),
        ),
    }


def _md(summary: dict) -> str:
    lines = [
        "# E4 safety-capacity exhaustion (frozen minilm-l12-h384 q, 5 reps)",
        "",
        f"R_gateway={R_GATEWAY} rps (constant), Bg={BG} rps, {DURATION_S:.0f}s/policy × {summary['reps']} reps.",
        "Suspicious/adversarial mix 5% → 50% → 5%. Offered strong demand ≈ 0.38 → 3.76 → 0.38 Bg.",
        f"Tenant A only. q={summary.get('q_source')}. Live ApplyGuardrail, no Maverick.",
        "Phenomenon: safety-resource exhaustion at constant gateway RPS. Do not use E4 to claim Proposed dominates.",
        "Paper overall cells are median [p25, p75]. Do not retune τ.",
        "",
        "## Overall (median [IQR])",
        "",
        "| policy | G_safe | UAR | reject |",
        "| --- | --- | --- | --- |",
    ]
    for m in summary["pooled"]:
        lines.append(
            f"| {m['policy']} | {fmt_stat(m['safe_slo_goodput'])} | "
            f"{fmt_stat(m['unsafe_admission_rate'])} | {fmt_stat(m['reject_rate'])} |"
        )
    lines += [
        "",
        "## Per phase (rep 0)",
        "",
        "| policy | phase | sus | offered | G_safe | UAR | reject | checked | starved |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for cell in summary["cells"]:
        if cell["overall"].get("rep", 0) != 0:
            continue
        for m in cell["phases"]:
            chk = m["checked_rate"]
            chk_s = "—" if chk is None else f"{chk:.2f}"
            lines.append(
                f"| {m['policy']} | {m['phase']} | {m['suspicious_frac']:.0%} | "
                f"{m['offered_strong_frac_of_bg']:.2f} Bg | "
                f"{m['safe_slo_goodput']:.3f} | {m['unsafe_admission_rate']:.3f} | "
                f"{m['reject_rate']:.3f} | {chk_s} | {m['n_starved']} |"
            )
    return "\n".join(lines) + "\n"


def main() -> int:
    summary = asyncio.run(_run())
    out = results_dir("e4")
    (out / "metrics.json").write_text(json.dumps(summary, indent=2))
    (out / "metrics.md").write_text(_md(summary))
    print(f"wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
