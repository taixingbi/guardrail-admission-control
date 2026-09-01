#!/usr/bin/env python3
"""E1: static safety-load sweep at fixed R_gateway.

Frozen Function URL q. 5 reps. Live ApplyGuardrail; Maverick skipped.
"""

from __future__ import annotations

import asyncio
import json
import random
import time

from gasc.io import write_jsonl
from gasc.replay_data import load_live_q, load_replay_prompts, q_for, results_dir, split_safe_unsafe
from gasc.replay_exec import (
    BG,
    POLICY_ORDER,
    R_GATEWAY,
    TENANT_A,
    bedrock_session,
    make_limiter,
    overflow_mode,
    run_scheduled,
)
from gasc.report import aggregate, fmt_stat, pool_by

DURATION_S = 40.0
REPS = 5
FRACS = (0.50, 1.00, 1.50)
POLICIES = POLICY_ORDER


async def _cell(*, client, guardrail_id, version, policy, frac, prompts_safe, prompts_unsafe, live_q, rep: int) -> dict:
    limiter = make_limiter(overflow=overflow_mode(policy), reserved={"A": 0.0, "B": 0.4})
    rng = random.Random({"always_strong": 1, "risk_only": 2, "load_aware": 3, "proposed": 4}[policy] * 100 + int(frac * 100) + rep * 1000)
    interval = 1.0 / R_GATEWAY
    p_unsafe = (frac * BG) / R_GATEWAY
    n_slots = int(DURATION_S / interval)
    recs = []
    t_start = time.perf_counter()
    for i in range(n_slots):
        delay = t_start + i * interval - time.perf_counter()
        if delay > 0:
            await asyncio.sleep(delay)
        prompt = rng.choice(prompts_unsafe if rng.random() < p_unsafe else prompts_safe)
        recs.append(
            await run_scheduled(
                client=client,
                guardrail_id=guardrail_id,
                version=version,
                limiter=limiter,
                prompt=prompt,
                tenant=TENANT_A,
                policy=policy,
                q=q_for(prompt, live_q),
                rng=rng,
            )
        )
    metrics = aggregate(recs, duration_s=DURATION_S)
    metrics.update(
        {
            "policy": policy,
            "strong_demand_frac_of_bg": frac,
            "oracle_strong_rps": frac * BG,
            "offered_rps": R_GATEWAY,
            "n": len(recs),
            "rep": rep,
        }
    )
    return {"metrics": metrics, "records": recs}


async def _run() -> dict:
    env = bedrock_session()
    frozen = load_replay_prompts()
    safe, unsafe = split_safe_unsafe(frozen)
    live_q = load_live_q(required=True)
    print(f"E1 replay n={len(frozen)} safe={len(safe)} unsafe={len(unsafe)} frozen_q={len(live_q)} {REPS} reps", flush=True)
    cells = []
    out = results_dir("e1")
    for rep in range(REPS):
        for policy in POLICIES:
            for frac in FRACS:
                print(f"E1 r{rep} {policy} frac={frac} …", flush=True)
                cell = await _cell(
                    client=env["client"],
                    guardrail_id=env["guardrail_id"],
                    version=env["version"],
                    policy=policy,
                    frac=frac,
                    prompts_safe=safe,
                    prompts_unsafe=unsafe,
                    live_q=live_q,
                    rep=rep,
                )
                print(json.dumps(cell["metrics"], indent=2))
                cells.append(cell["metrics"])
                write_jsonl(out / f"r{rep}_{policy}_{frac:.2f}.jsonl", cell["records"])
    summary = {
        "bg": BG,
        "r_gateway": R_GATEWAY,
        "duration_s": DURATION_S,
        "reps": REPS,
        "q_source": "frozen_g_light",
        "n_live_q": len(live_q),
        "cells": cells,
        "pooled": pool_by(
            cells,
            ("policy", "strong_demand_frac_of_bg"),
            (
                "safe_slo_goodput",
                "unsafe_admission_rate",
                "uar_light",
                "uar_strong",
                "uar_bypass",
                "reject_rate",
                "guardrail_capacity_efficiency",
            ),
        ),
    }
    summary["pooled"].sort(key=lambda m: (POLICY_ORDER.index(m["policy"]), m["strong_demand_frac_of_bg"]))
    return summary


def main() -> int:
    summary = asyncio.run(_run())
    out = results_dir("e1")
    (out / "metrics.json").write_text(json.dumps(summary, indent=2))
    lines = [
        "# E1 static safety-load (frozen minilm-l12-h384 q, 5 reps)",
        "",
        f"R_gateway={R_GATEWAY} rps, Bg={BG} rps (gateway safety budget, not provider capacity), "
        f"{DURATION_S:.0f}s/cell × {summary['reps']} reps. q={summary.get('q_source')}. Live ApplyGuardrail, no Maverick.",
        "Paper cells are median [p25, p75]. Do not retune τ.",
        "UAR = UAR_light + UAR_strong + UAR_bypass. Always-Strong UAR is G_strong miss, not MiniLM FN.",
        "Efficiency = risk-required strong occupancy / all strong occupancy (Always-Strong waste is q < τ).",
        "",
        "| policy | demand | G_safe | UAR | reject | efficiency |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for m in summary["pooled"]:
        lines.append(
            f"| {m['policy']} | {m['strong_demand_frac_of_bg']:.2f} Bg | "
            f"{fmt_stat(m['safe_slo_goodput'])} | {fmt_stat(m['unsafe_admission_rate'])} | "
            f"{fmt_stat(m['reject_rate'])} | {fmt_stat(m['guardrail_capacity_efficiency'], digits=2)} |"
        )
    (out / "metrics.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
