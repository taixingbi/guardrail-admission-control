#!/usr/bin/env python3
"""E6: ablations on the E3 proposed overload phase (1.5 Bg, 240–360 s).

Replays the same arrivals/prompts as E3 proposed. Four scheduler flags:
Full / -NoTenant / -NoDeadline / -NoEarlyReject.
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

E3_DURATION_S = 480.0
OVERLOAD_LO = 240.0
OVERLOAD_HI = 360.0
REPS = 5
E3_PHASES = ((120.0, 0.5), (240.0, 0.9), (360.0, 1.5), (480.0, 0.6))
E3_PROPOSED_SEED = 30 + 3 * 17
VARIANTS = (
    ("full", True, True, True, "reject"),
    ("no_tenant", False, True, True, "reject"),
    ("no_deadline", True, False, True, "reject"),
    ("no_early_reject", True, True, False, "queue"),
)
TENANT = TENANT_A


def _frac_at(t_s: float) -> float:
    for until, frac in E3_PHASES:
        if t_s < until:
            return frac
    return E3_PHASES[-1][1]


def _e3_proposed_overload(prompts_safe, prompts_unsafe, *, rep: int = 0):
    rng = random.Random(E3_PROPOSED_SEED + rep * 1000)
    interval = 1.0 / R_GATEWAY
    n_slots = int(E3_DURATION_S / interval)
    planned = []
    for i in range(n_slots):
        t_s = i * interval
        p_unsafe = (_frac_at(t_s) * BG) / R_GATEWAY
        pool = prompts_unsafe if rng.random() < p_unsafe else prompts_safe
        planned.append((t_s, rng.choice(pool)))
    return [(t_s, p) for t_s, p in planned if OVERLOAD_LO <= t_s < OVERLOAD_HI]


async def _one(*, client, guardrail_id, version, limiter, variant, use_tenant, use_deadline, use_early_reject, prompt, rng, api_lock, t_s, live_q) -> RunRecord:
    return await run_scheduled(
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
        use_tenant=use_tenant,
        use_deadline=use_deadline,
        use_early_reject=use_early_reject,
        metadata={"ablation": variant, "t_s": t_s},
    )


def _window(recs: list[RunRecord], duration_s: float) -> dict:
    m = aggregate(recs, duration_s=duration_s)
    occ = need_occupancy(recs)
    need = [r for r in recs if r.decision.need_strong]
    reasons: dict[str, int] = {}
    for r in need:
        reasons[r.decision.reason] = reasons.get(r.decision.reason, 0) + 1
    lat = [r.latency_ms for r in recs]
    lat.sort()

    def pct(p: float) -> float | None:
        if not lat:
            return None
        i = min(len(lat) - 1, max(0, int(round((p / 100.0) * (len(lat) - 1)))))
        return lat[i]

    m.update(
        {
            **occ,
            "n_deadline": sum(1 for r in recs if r.decision.reason == "deadline"),
            "n_queue_anyway": sum(1 for r in recs if r.decision.reason == "queue_anyway"),
            "latency_p50_ms": pct(50),
            "latency_p95_ms": pct(95),
            "reasons_need": reasons,
        }
    )
    return m


async def _cell(*, client, guardrail_id, version, variant, use_tenant, use_deadline, use_early_reject, overflow, planned, live_q, rep: int = 0) -> dict:
    limiter = make_limiter(overflow=overflow)
    api_lock = asyncio.Lock()
    rng = random.Random(60 + {"full": 1, "no_tenant": 2, "no_deadline": 3, "no_early_reject": 4}[variant] + rep * 1000)
    t0_abs = planned[0][0]
    t_start = time.perf_counter()

    async def _scheduled(i: int, t_s: float, prompt) -> RunRecord:
        delay = t_start + (t_s - t0_abs) - time.perf_counter()
        if delay > 0:
            await asyncio.sleep(delay)
        return await _one(
            client=client,
            guardrail_id=guardrail_id,
            version=version,
            limiter=limiter,
            variant=variant,
            use_tenant=use_tenant,
            use_deadline=use_deadline,
            use_early_reject=use_early_reject,
            prompt=prompt,
            rng=rng,
            api_lock=api_lock,
            t_s=t_s,
            live_q=live_q,
        )

    recs = list(await asyncio.gather(*[_scheduled(i, t_s, p) for i, (t_s, p) in enumerate(planned)]))
    duration_s = OVERLOAD_HI - OVERLOAD_LO
    metrics = _window(recs, duration_s)
    metrics.update(
        {
            "ablation": variant,
            "use_tenant": use_tenant,
            "use_deadline": use_deadline,
            "use_early_reject": use_early_reject,
            "overflow_mode": overflow,
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
        f"E6 replay n={len(frozen)} safe={len(safe)} unsafe={len(unsafe)} "
        f"frozen_q={len(live_q)} {REPS} reps",
        flush=True,
    )
    out = results_dir("e6")
    cells = []
    for rep in range(REPS):
        planned = _e3_proposed_overload(safe, unsafe, rep=rep)
        for variant, use_tenant, use_deadline, use_early_reject, overflow in VARIANTS:
            print(f"E6 r{rep} {variant} ({len(planned)} req, 120s) …", flush=True)
            cell = await _cell(
                client=env["client"],
                guardrail_id=env["guardrail_id"],
                version=env["version"],
                variant=variant,
                use_tenant=use_tenant,
                use_deadline=use_deadline,
                use_early_reject=use_early_reject,
                overflow=overflow,
                planned=planned,
                live_q=live_q,
                rep=rep,
            )
            print(json.dumps(cell["metrics"], indent=2), flush=True)
            cells.append(cell["metrics"])
            (out / f"r{rep}_{variant}.jsonl").write_text("\n".join(json.dumps(r) for r in cell["records"]) + "\n")
    summary = {
        "bg": BG,
        "r_gateway": R_GATEWAY,
        "reps": REPS,
        "reuse_trace": "e3_proposed_240_360s_1.5Bg",
        "q_source": "frozen_g_light",
        "n_live_q": len(live_q),
        "cells": cells,
        "pooled": pool_by(
            cells,
            ("ablation",),
            ("safe_slo_goodput", "unsafe_admission_rate", "reject_rate", "n_checked", "latency_p95_ms"),
        ),
    }
    order = ("full", "no_tenant", "no_deadline", "no_early_reject")
    summary["pooled"].sort(key=lambda m: order.index(m["ablation"]))
    return summary


def main() -> int:
    summary = asyncio.run(_run())
    out = results_dir("e6")
    (out / "metrics.json").write_text(json.dumps(summary, indent=2))
    lines = [
        "# E6 ablations (frozen minilm-l12-h384 q, 5 reps, E3 overload 1.5 Bg)",
        "",
        f"Same arrival process as E3 proposed overload. Fail-closed. Tenant A only. q={summary.get('q_source')}.",
        "Paper cells are median [p25, p75]. Full vs −NoEarlyReject is the systems headline. Do not retune τ.",
        "−NoTenant ≈ Full because this cell is Tenant A only (not because q is bimodal).",
        "",
        "| ablation | G_safe | UAR | reject | checked | P95 ms |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for m in summary["pooled"]:
        lines.append(
            f"| {m['ablation']} | {fmt_stat(m['safe_slo_goodput'])} | "
            f"{fmt_stat(m['unsafe_admission_rate'])} | {fmt_stat(m['reject_rate'])} | "
            f"{fmt_stat(m['n_checked'], digits=1)} | {fmt_stat(m['latency_p95_ms'], digits=0)} |"
        )
    (out / "metrics.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
