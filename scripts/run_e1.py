#!/usr/bin/env python3
"""E1: static safety-load sweep at fixed R_gateway.

Frozen Function URL q. 5 reps. Live ApplyGuardrail; Maverick skipped.
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
from gasc.report import aggregate, fmt_stat, pool_by
from gasc.scheduler import SchedulerInputs, decide, policy_compliant
from gasc.schemas import RunRecord, TenantPolicy

BG = 0.4
R_GATEWAY = 3.01
DURATION_S = 40.0
REPS = 5
FRACS = (0.50, 1.00, 1.50)
POLICIES = (
    ("always_strong", "queue"),
    ("risk_only", "reject"),
    ("load_aware", "queue"),
    ("proposed", "reject"),
)
TENANT = TenantPolicy(tenant_id="A", tau=0.75, slo_ms=600, reserved_share=0.0)
T_STRONG_MS = 215.0
T_LLM_MS = 0.0
QUEUE_TIMEOUT_S = 2.0


def _overflow(policy: str) -> str:
    return "queue" if policy in {"always_strong", "load_aware"} else "reject"


async def _one(
    *,
    client,
    guardrail_id: str,
    version: str,
    limiter: StrongLimiter,
    policy: str,
    prompt,
    rng: random.Random,
    live_q,
) -> RunRecord:
    t0 = time.perf_counter()
    q = q_for(prompt, live_q)
    wait_ms = limiter.estimated_wait_ms()
    available = limiter.strong_available(TENANT.tenant_id)
    if policy in {"always_strong", "load_aware"}:
        available = True
    decision = decide(
        SchedulerInputs(
            q=q,
            tenant=TENANT,
            policy=policy,  # type: ignore[arg-type]
            fail_closed=True,
            strong_available=available,
            est_strong_wait_ms=wait_ms,
            t_strong_ms=T_STRONG_MS,
            t_llm_ms=T_LLM_MS,
            global_tau=0.5,
        )
    )
    route = decision.route
    action = None
    acquired = False
    if route == "strong":
        got = await limiter.acquire(TENANT.tenant_id, timeout_s=QUEUE_TIMEOUT_S)
        if got.ok:
            acquired = True
            out = await asyncio.to_thread(
                apply_guardrail,
                client,
                guardrail_id=guardrail_id,
                guardrail_version=version,
                text=prompt.text,
            )
            action = out.get("action")
            if action not in {None, "NONE", "GUARDRAIL_INTERVENED"}:
                pass
        else:
            route = "reject"
            decision = decision.model_copy(update={"route": "reject", "reason": got.reason})
    if acquired:
        await limiter.release(TENANT.tenant_id)

    latency_ms = (time.perf_counter() - t0) * 1000
    admitted = route in {"direct", "strong"} and not decision.bypass
    blocked = action == "GUARDRAIL_INTERVENED"
    if blocked:
        admitted = False
        route = "reject"
        decision = decision.model_copy(update={"route": "reject", "reason": "guardrail_block"})
    gt_unsafe = prompt.target_label == "unsafe"
    safe = not (gt_unsafe and admitted)
    return RunRecord(
        request_id=str(rng.random()),
        tenant_id="A",
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
        slo_ms=TENANT.slo_ms,
        policy_compliant=policy_compliant(decision, route),  # type: ignore[arg-type]
        safe=safe,
        slo_ok=latency_ms <= TENANT.slo_ms,
        apply_guardrail_action=action,
        metadata={"apply_guardrail_action": action},
    )


async def _cell(
    *,
    client,
    guardrail_id: str,
    version: str,
    policy: str,
    frac: float,
    prompts_safe: list,
    prompts_unsafe: list,
    live_q,
    rep: int = 0,
) -> dict:
    limiter = StrongLimiter(
        inflight_limit=2,
        queue_max=16,
        reserved_share={"A": 0.0, "B": 0.4},
        overflow_mode=_overflow(policy),
        bg_rps=BG,
        burst=1,
    )
    rng = random.Random(
        {"always_strong": 1, "risk_only": 2, "load_aware": 3, "proposed": 4}[policy] * 100
        + int(frac * 100)
        + rep * 1000
    )
    interval = 1.0 / R_GATEWAY
    p_unsafe = (frac * BG) / R_GATEWAY
    n_slots = int(DURATION_S / interval)
    recs: list[RunRecord] = []
    t_start = time.perf_counter()
    for i in range(n_slots):
        target = t_start + i * interval
        delay = target - time.perf_counter()
        if delay > 0:
            await asyncio.sleep(delay)
        unsafe = rng.random() < p_unsafe
        pool = prompts_unsafe if unsafe else prompts_safe
        prompt = rng.choice(pool)
        recs.append(
            await _one(
                client=client,
                guardrail_id=guardrail_id,
                version=version,
                limiter=limiter,
                policy=policy,
                prompt=prompt,
                rng=rng,
                live_q=live_q,
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
    return {"metrics": metrics, "records": [json.loads(r.model_dump_json()) for r in recs]}


async def _run() -> dict:
    root = Path(__file__).resolve().parents[1]
    load_dotenv(root / ".env")
    gid = os.environ["GASC_GUARDRAIL_ID"]
    gver = os.environ.get("GASC_GUARDRAIL_VERSION", "1")
    region = os.environ.get("AWS_REGION", "us-east-1")
    frozen = load_replay_prompts()
    safe, unsafe = split_safe_unsafe(frozen)
    live_q = load_live_q(required=True)
    print(
        f"E1 replay n={len(frozen)} safe={len(safe)} unsafe={len(unsafe)} "
        f"frozen_q={len(live_q)} {REPS} reps",
        flush=True,
    )
    client = bedrock_runtime(region)
    cells = []
    out = replay_dir("e1")
    for rep in range(REPS):
        for policy, _mode in POLICIES:
            for frac in FRACS:
                print(f"E1 r{rep} {policy} frac={frac} …", flush=True)
                cell = await _cell(
                    client=client,
                    guardrail_id=gid,
                    version=gver,
                    policy=policy,
                    frac=frac,
                    prompts_safe=safe,
                    prompts_unsafe=unsafe,
                    live_q=live_q,
                    rep=rep,
                )
                print(json.dumps(cell["metrics"], indent=2))
                cells.append(cell["metrics"])
                (out / f"r{rep}_{policy}_{frac:.2f}.jsonl").write_text(
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
            ("policy", "strong_demand_frac_of_bg"),
            ("safe_slo_goodput", "unsafe_admission_rate", "reject_rate", "guardrail_capacity_efficiency"),
        ),
    }
    order = ("always_strong", "risk_only", "load_aware", "proposed")
    summary["pooled"].sort(
        key=lambda m: (order.index(m["policy"]), m["strong_demand_frac_of_bg"])
    )
    return summary


def main() -> int:
    summary = asyncio.run(_run())
    out = replay_dir("e1")
    (out / "metrics.json").write_text(json.dumps(summary, indent=2))
    lines = [
        "# E1 static safety-load (frozen minilm-l12-h384 q, 5 reps)",
        "",
        f"R_gateway={R_GATEWAY} rps, Bg={BG} rps (gateway safety budget, not provider capacity), "
        f"{DURATION_S:.0f}s/cell × {summary['reps']} reps. "
        f"q={summary.get('q_source')}. Live ApplyGuardrail, no Maverick.",
        "Paper cells are median [p25, p75]. Do not retune τ.",
        "UAR is MiniLM false negatives (q below τ, so scheduler never requires strong), not fail-open.",
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
