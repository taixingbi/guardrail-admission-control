#!/usr/bin/env python3
"""Sensitivity sweeps for the camera-ready (reviewer request).

    uv run python scripts/run_sweeps.py [rho] [deadline]

rho      E2 Proposed only, Tenant B reservation ρ ∈ RHOS at mixes 90:10 and 70:30.
         Same seeds/arrivals as E2 Proposed, so ρ=0.4 is the existing E2 cell.
         ρ=0 isolates the reservation from Tenant B's lower threshold.
deadline E6 setting (E3 overload, 1.5 Bg), Tenant A deadline ∈ DEADLINES_MS,
         Full vs −NoEarlyReject. Same arrivals as E6, so 600 ms is the existing cell.

Nothing else is retuned (τ, Bg, R_gateway, prompts, guardrail).
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from collections import defaultdict
from pathlib import Path

from gasc.io import write_jsonl
from gasc.replay_data import load_live_q, load_replay_prompts, load_scored_prompts, results_dir, split_q_bands, split_safe_unsafe
from gasc.replay_exec import TENANT_A, bedrock_session
from gasc.report import fmt_stat, stat_pack

ROOT = Path(__file__).resolve().parent
RHOS = (0.0, 0.2, 0.6)
RHO_MIXES = ((0.90, 0.10), (0.70, 0.30))
DEADLINES_MS = (400, 800, 1200)
DEADLINE_VARIANTS = (
    ("full", True, True, True, "reject"),
    ("no_early_reject", True, True, False, "queue"),
)


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


async def sweep_rho(env) -> None:
    e2 = _load("run_e2")
    scored = load_scored_prompts()
    safe, unsafe = split_safe_unsafe(scored)
    mid = split_q_bands(scored)["tenant_split"]
    out = results_dir("sweep_rho")
    cells = []
    total = e2.REPS * len(RHOS) * len(RHO_MIXES)
    k = 0
    for rep in range(e2.REPS):
        for rho in RHOS:
            e2._reserved = lambda policy, rho=rho: {"A": 0.0, "B": rho}
            for mix in RHO_MIXES:
                k += 1
                print(f"SWEEP rho {k}/{total} r{rep} rho={rho} A:B={mix[0]:.0%}:{mix[1]:.0%} …", flush=True)
                cell = await e2._cell(
                    client=env["client"], guardrail_id=env["guardrail_id"], version=env["version"],
                    policy="proposed", mix=mix, safe=safe, unsafe=unsafe, mid=mid, rep=rep,
                )
                m = {**cell["metrics"], "rho": rho}
                cells.append(m)
                write_jsonl(out / f"r{rep}_rho{rho:.1f}_{mix[0]:.2f}_{mix[1]:.2f}.jsonl", cell["records"])
    groups = defaultdict(list)
    for m in cells:
        groups[(m["rho"], m["mix_a"])].append(m)
    pooled = []
    for (rho, pa), rows in sorted(groups.items()):
        need = sum(r["n_need_b"] for r in rows)
        pooled.append({
            "rho": rho, "mix_a": pa, "mix_b": rows[0]["mix_b"], "reps": len(rows),
            "safe_slo_goodput": stat_pack([r["safe_slo_goodput"] for r in rows]),
            "g_safe_a": stat_pack([r["g_safe_a"] for r in rows]),
            "g_safe_b": stat_pack([r["g_safe_b"] for r in rows]),
            "uar_b": stat_pack([r["uar_b"] for r in rows]),
            "n_need_b": need, "n_checked_b": sum(r["n_checked_b"] for r in rows),
            "coverage_b": (sum(r["n_checked_b"] for r in rows) / need) if need else None,
        })
    (out / "metrics.json").write_text(json.dumps({"rhos": RHOS, "cells": cells, "pooled": pooled}, indent=2))
    lines = [
        "# ρ sweep (E2 Proposed, 120 s × 5 reps; ρ=0.4 is results/e2)", "",
        "| ρ | A:B | G_safe | G_safe_A | G_safe_B | need_B | checked_B | coverage_B | UAR_B |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for p in pooled:
        lines.append(
            f"| {p['rho']:.1f} | {p['mix_a']:.0%}:{p['mix_b']:.0%} | {fmt_stat(p['safe_slo_goodput'])} | "
            f"{fmt_stat(p['g_safe_a'])} | {fmt_stat(p['g_safe_b'])} | {p['n_need_b']} | {p['n_checked_b']} | "
            f"{p['coverage_b']:.1%} | {fmt_stat(p['uar_b'])} |"
        )
    (out / "metrics.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {out}", flush=True)


async def sweep_deadline(env) -> None:
    e6 = _load("run_e6")
    frozen = load_replay_prompts()
    safe, unsafe = split_safe_unsafe(frozen)
    live_q = load_live_q(required=True)
    out = results_dir("sweep_deadline")
    cells = []
    total = e6.REPS * len(DEADLINES_MS) * len(DEADLINE_VARIANTS)
    k = 0
    for rep in range(e6.REPS):
        planned = e6._e3_proposed_overload(safe, unsafe, rep=rep)
        for slo in DEADLINES_MS:
            e6.TENANT = TENANT_A.model_copy(update={"slo_ms": slo})
            for variant, use_tenant, use_deadline, use_early_reject, overflow in DEADLINE_VARIANTS:
                k += 1
                print(f"SWEEP deadline {k}/{total} r{rep} slo={slo} {variant} …", flush=True)
                cell = await e6._cell(
                    client=env["client"], guardrail_id=env["guardrail_id"], version=env["version"],
                    variant=variant, use_tenant=use_tenant, use_deadline=use_deadline,
                    use_early_reject=use_early_reject, overflow=overflow, planned=planned, live_q=live_q, rep=rep,
                )
                m = {**cell["metrics"], "slo_ms": slo}
                cells.append(m)
                (out / f"r{rep}_slo{slo}_{variant}.jsonl").write_text(
                    "\n".join(json.dumps(r) for r in cell["records"]) + "\n"
                )
    groups = defaultdict(list)
    for m in cells:
        groups[(m["slo_ms"], m["ablation"])].append(m)
    pooled = []
    for (slo, variant), rows in sorted(groups.items()):
        pooled.append({
            "slo_ms": slo, "ablation": variant, "reps": len(rows),
            **{key: stat_pack([r[key] for r in rows]) for key in
               ("safe_slo_goodput", "unsafe_admission_rate", "reject_rate", "n_checked", "latency_p95_ms")},
        })
    (out / "metrics.json").write_text(json.dumps({"deadlines_ms": DEADLINES_MS, "cells": cells, "pooled": pooled}, indent=2))
    lines = [
        "# Deadline sweep (E6 setting, 1.5 Bg, 120 s × 5 reps; 600 ms is results/e6)", "",
        "| deadline ms | variant | G_safe | UAR | reject | checked | safety-stage P95 ms |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for p in pooled:
        lines.append(
            f"| {p['slo_ms']} | {p['ablation']} | {fmt_stat(p['safe_slo_goodput'])} | "
            f"{fmt_stat(p['unsafe_admission_rate'])} | {fmt_stat(p['reject_rate'])} | "
            f"{fmt_stat(p['n_checked'], digits=1)} | {fmt_stat(p['latency_p95_ms'], digits=0)} |"
        )
    (out / "metrics.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {out}", flush=True)


async def _main(which: list[str]) -> None:
    env = bedrock_session()
    if "rho" in which:
        await sweep_rho(env)
    if "deadline" in which:
        await sweep_deadline(env)


if __name__ == "__main__":
    asyncio.run(_main(sys.argv[1:] or ["rho", "deadline"]))
    print("Sweeps done.", flush=True)
