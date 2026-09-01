#!/usr/bin/env python3
"""E3: dynamic safety load. Gateway RPS fixed; strong-mix steps over 480 s.

Phases: 0.5 → 0.9 → 1.5 → 0.6 Bg. Tenant A only. Frozen Function URL q.
Live ApplyGuardrail; Maverick skipped so the series isolates safety capacity.
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

DURATION_S = 480.0
BIN_S = 10.0
REPS = 5
PHASES = (
    (120.0, 0.5),
    (240.0, 0.9),
    (360.0, 1.5),
    (480.0, 0.6),
)
POLICIES = POLICY_ORDER
TENANT = TENANT_A


def _frac_at(t_s: float) -> float:
    for until, frac in PHASES:
        if t_s < until:
            return frac
    return PHASES[-1][1]


def _phase_name(t_s: float) -> str:
    prev = 0.0
    for until, frac in PHASES:
        if t_s < until:
            return f"{prev:.0f}-{until:.0f}s@{frac:.1f}Bg"
        prev = until
    until, frac = PHASES[-1]
    return f"{prev:.0f}-{until:.0f}s@{frac:.1f}Bg"


async def _one(*, client, guardrail_id, version, limiter, policy, prompt, rng, api_lock, t_s, live_q) -> RunRecord:
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
        metadata={"t_s": t_s, "strong_frac_of_bg": _frac_at(t_s), "phase": _phase_name(t_s)},
    )


def _window_metrics(recs: list[RunRecord], duration_s: float) -> dict:
    m = aggregate(recs, duration_s=duration_s)
    m.update(need_occupancy(recs))
    return m


async def _cell(*, client, guardrail_id, version, policy, prompts_safe, prompts_unsafe, live_q, rep: int = 0) -> dict:
    limiter = make_limiter(overflow=overflow_mode(policy))
    api_lock = asyncio.Lock()
    rng = random.Random(30 + POLICIES.index(policy) * 17 + rep * 1000)
    interval = 1.0 / R_GATEWAY
    n_slots = int(DURATION_S / interval)
    planned = []
    for i in range(n_slots):
        t_s = i * interval
        p_unsafe = (_frac_at(t_s) * BG) / R_GATEWAY
        pool = prompts_unsafe if rng.random() < p_unsafe else prompts_safe
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
    for until, frac in PHASES:
        chunk = [r for r in recs if prev <= float(r.metadata["t_s"]) < until]
        row = _window_metrics(chunk, until - prev)
        row.update({"policy": policy, "phase": f"{prev:.0f}-{until:.0f}s", "strong_frac_of_bg": frac, "n": len(chunk)})
        phases.append(row)
        prev = until
    series = []
    n_bins = int(DURATION_S / BIN_S)
    for b in range(n_bins):
        lo, hi = b * BIN_S, (b + 1) * BIN_S
        chunk = [r for r in recs if lo <= float(r.metadata["t_s"]) < hi]
        row = _window_metrics(chunk, BIN_S)
        row.update({"t0": lo, "t1": hi, "n": len(chunk), "strong_frac_of_bg": _frac_at(lo)})
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
        f"E3 replay n={len(frozen)} safe={len(safe)} unsafe={len(unsafe)} "
        f"frozen_q={len(live_q)} {REPS} reps",
        flush=True,
    )
    out = results_dir("e3")
    cells = []
    for rep in range(REPS):
        for policy in POLICIES:
            print(f"E3 r{rep} {policy} 480s …", flush=True)
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
        "phases": [{"until_s": u, "strong_frac_of_bg": f} for u, f in PHASES],
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
        "# E3 dynamic safety load (frozen minilm-l12-h384 q, 5 reps)",
        "",
        f"R_gateway={R_GATEWAY} rps, Bg={BG} rps, {DURATION_S:.0f}s/policy × {summary['reps']} reps. Mix 0.5→0.9→1.5→0.6 Bg.",
        f"Tenant A only. q={summary.get('q_source')}. Live ApplyGuardrail, no Maverick.",
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
        "## Per phase (rep 0 shown in jsonl; pooled overall is the paper cell)",
        "",
        "| policy | phase | demand | G_safe | UAR | reject | checked | starved |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for cell in summary["cells"]:
        if cell["overall"].get("rep", 0) != 0:
            continue
        for m in cell["phases"]:
            chk = m["checked_rate"]
            chk_s = "—" if chk is None else f"{chk:.2f}"
            lines.append(
                f"| {m['policy']} | {m['phase']} | {m['strong_frac_of_bg']:.1f} Bg | "
                f"{m['safe_slo_goodput']:.3f} | {m['unsafe_admission_rate']:.3f} | "
                f"{m['reject_rate']:.3f} | {chk_s} | {m['n_starved']} |"
            )
    return "\n".join(lines) + "\n"


def main() -> int:
    summary = asyncio.run(_run())
    out = results_dir("e3")
    (out / "metrics.json").write_text(json.dumps(summary, indent=2))
    (out / "metrics.md").write_text(_md(summary))
    print(f"wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
