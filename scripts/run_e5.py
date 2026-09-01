#!/usr/bin/env python3
"""E5: fail-open vs fail-closed at 1.5 and 2.0 Bg.

Proposed only. Fail-open turns off deadline so exhaustion can reach bypass;
fail-closed keeps the frozen B4 path (deadline + safety_floor).
"""

from __future__ import annotations

import asyncio
import json
import random
import time

from gasc.replay_data import load_live_q, load_replay_prompts, q_for, results_dir, split_safe_unsafe
from gasc.replay_exec import BG, R_GATEWAY, TENANT_A, bedrock_session, make_limiter, need_occupancy, run_scheduled
from gasc.report import aggregate, fmt_stat, pool_by
from gasc.schemas import RunRecord

DURATION_S = 60.0
REPS = 5
FRACS = (1.5, 2.0)
MODES = (
    ("proposed_fail_closed", True, True),
    ("proposed_fail_open", False, False),
)
TENANT = TENANT_A


async def _one(*, client, guardrail_id, version, limiter, mode, fail_closed, use_deadline, prompt, rng, api_lock, live_q) -> RunRecord:
    rec = await run_scheduled(
        client=client,
        guardrail_id=guardrail_id,
        version=version,
        limiter=limiter,
        prompt=prompt,
        tenant=TENANT,
        policy="proposed",
        q=q_for(prompt, live_q),
        rng=rng,
        api_lock=api_lock,
        fail_closed=fail_closed,
        use_deadline=use_deadline,
        on_full="reject" if fail_closed else "bypass",
        admit_if_bypass=not fail_closed,
        metadata={"mode": mode, "fail_closed": fail_closed},
    )
    return rec


def _extra(recs: list[RunRecord]) -> dict:
    occ = need_occupancy(recs)
    need = [r for r in recs if r.decision.need_strong]
    bypass = [r for r in recs if r.decision.bypass]
    unsafe = [r for r in recs if r.gt_label == "unsafe"]
    return {
        **occ,
        "n_bypass": len(bypass),
        "n_bypass_unsafe": sum(1 for r in bypass if r.gt_label == "unsafe"),
        "bypass_rate_need": (len(bypass) / len(need)) if need else 0.0,
        "n_unsafe": len(unsafe),
    }


async def _cell(*, client, guardrail_id, version, mode, fail_closed, use_deadline, frac, prompts_safe, prompts_unsafe, live_q, rep: int = 0) -> dict:
    limiter = make_limiter(overflow="reject")
    api_lock = asyncio.Lock()
    rng = random.Random(50 + int(frac * 10) + (0 if fail_closed else 7) + rep * 1000)
    interval = 1.0 / R_GATEWAY
    p_unsafe = (frac * BG) / R_GATEWAY
    n_slots = int(DURATION_S / interval)
    planned = [rng.choice(prompts_unsafe if rng.random() < p_unsafe else prompts_safe) for _ in range(n_slots)]
    t_start = time.perf_counter()

    async def _scheduled(i: int, prompt) -> RunRecord:
        delay = t_start + i * interval - time.perf_counter()
        if delay > 0:
            await asyncio.sleep(delay)
        return await _one(
            client=client,
            guardrail_id=guardrail_id,
            version=version,
            limiter=limiter,
            mode=mode,
            fail_closed=fail_closed,
            use_deadline=use_deadline,
            prompt=prompt,
            rng=rng,
            api_lock=api_lock,
            live_q=live_q,
        )

    recs = list(await asyncio.gather(*[_scheduled(i, p) for i, p in enumerate(planned)]))
    metrics = aggregate(recs, duration_s=DURATION_S)
    metrics.update(_extra(recs))
    metrics.update(
        {
            "mode": mode,
            "fail_closed": fail_closed,
            "strong_demand_frac_of_bg": frac,
            "n": len(recs),
            "rep": rep,
        }
    )
    return {"metrics": metrics, "records": [json.loads(r.model_dump_json()) for r in recs]}


async def _run() -> dict:
    env = bedrock_session()
    frozen = load_replay_prompts()
    safe, unsafe = split_safe_unsafe(frozen)
    live_q = load_live_q(required=True)
    print(
        f"E5 replay n={len(frozen)} safe={len(safe)} unsafe={len(unsafe)} "
        f"frozen_q={len(live_q)} {REPS} reps",
        flush=True,
    )
    out = results_dir("e5")
    cells = []
    for rep in range(REPS):
        for mode, fail_closed, use_deadline in MODES:
            for frac in FRACS:
                print(f"E5 r{rep} {mode} {frac:.1f} Bg …", flush=True)
                cell = await _cell(
                    client=env["client"],
                    guardrail_id=env["guardrail_id"],
                    version=env["version"],
                    mode=mode,
                    fail_closed=fail_closed,
                    use_deadline=use_deadline,
                    frac=frac,
                    prompts_safe=safe,
                    prompts_unsafe=unsafe,
                    live_q=live_q,
                    rep=rep,
                )
                print(json.dumps(cell["metrics"], indent=2), flush=True)
                cells.append(cell["metrics"])
                (out / f"r{rep}_{mode}_{frac:.1f}.jsonl").write_text(
                    "\n".join(json.dumps(r) for r in cell["records"]) + "\n"
                )
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
            ("mode", "strong_demand_frac_of_bg"),
            ("safe_slo_goodput", "unsafe_admission_rate", "reject_rate", "bypass_rate_need"),
        ),
    }
    summary["pooled"].sort(key=lambda m: (0 if "closed" in m["mode"] else 1, m["strong_demand_frac_of_bg"]))
    return summary


def main() -> int:
    summary = asyncio.run(_run())
    out = results_dir("e5")
    (out / "metrics.json").write_text(json.dumps(summary, indent=2))
    lines = [
        "# E5 fail-open vs fail-closed (frozen minilm-l12-h384 q, 5 reps)",
        "",
        f"Proposed only. R_gateway={R_GATEWAY}, Bg={BG}, {DURATION_S:.0f}s/cell × {summary['reps']} reps. q={summary.get('q_source')}.",
        "Fail-open disables deadline so exhaustion can bypass. Fail-closed keeps frozen B4.",
        "Paper cells are median [p25, p75]. MiniLM is a screener, not the authority. Do not retune τ.",
        "Fail-open raises UAR without raising Safe Goodput. Residual fail-closed UAR is MiniLM FN, not bypass.",
        "",
        "| mode | demand | G_safe | UAR | reject | bypass/need |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for m in summary["pooled"]:
        lines.append(
            f"| {m['mode']} | {m['strong_demand_frac_of_bg']:.1f} Bg | "
            f"{fmt_stat(m['safe_slo_goodput'])} | {fmt_stat(m['unsafe_admission_rate'])} | "
            f"{fmt_stat(m['reject_rate'])} | {fmt_stat(m['bypass_rate_need'], digits=2)} |"
        )
    (out / "metrics.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
