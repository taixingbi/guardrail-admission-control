#!/usr/bin/env python3
"""E1 scout: static safety-load sweep at fixed R_gateway.

Oracle mix of S2/S3 hits 0.5 / 1.0 / 1.5 Rg. Live E0a q when present.
Live ApplyGuardrail; Maverick skipped so the cell isolates safety capacity.
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
DURATION_S = 40.0
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
) -> dict:
    limiter = StrongLimiter(
        inflight_limit=2,
        queue_max=16,
        reserved_share={"A": 0.0, "B": 0.4},
        overflow_mode=_overflow(policy),
        rg_rps=RG,
        burst=1,
    )
    rng = random.Random({"always_strong": 1, "risk_only": 2, "load_aware": 3, "proposed": 4}[policy] * 100 + int(frac * 100))
    interval = 1.0 / R_GATEWAY
    p_unsafe = (frac * RG) / R_GATEWAY
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
            "strong_demand_frac_of_rg": frac,
            "oracle_strong_rps": frac * RG,
            "offered_rps": R_GATEWAY,
            "n": len(recs),
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
    live_q = load_live_q()
    print(f"E1 replay n={len(frozen)} safe={len(safe)} unsafe={len(unsafe)} live_q={len(live_q)}", flush=True)
    client = bedrock_runtime(region)
    cells = []
    out = replay_dir("e1")
    for policy, _mode in POLICIES:
        for frac in FRACS:
            print(f"E1 {policy} frac={frac} …", flush=True)
            cell = await _cell(
                client=client,
                guardrail_id=gid,
                version=gver,
                policy=policy,
                frac=frac,
                prompts_safe=safe,
                prompts_unsafe=unsafe,
                live_q=live_q,
            )
            print(json.dumps(cell["metrics"], indent=2))
            cells.append(cell["metrics"])
            (out / f"{policy}_{frac:.2f}.jsonl").write_text(
                "\n".join(json.dumps(r) for r in cell["records"]) + "\n"
            )
    return {
        "rg": RG,
        "r_gateway": R_GATEWAY,
        "duration_s": DURATION_S,
        "q_source": "e0a_live" if live_q else "oracle",
        "n_live_q": len(live_q),
        "cells": cells,
    }


def main() -> int:
    summary = asyncio.run(_run())
    out = replay_dir("e1")
    (out / "metrics.json").write_text(json.dumps(summary, indent=2))
    lines = [
        "# E1 static safety-load (freeze replay)",
        "",
        f"R_gateway={R_GATEWAY} rps, Rg={RG} rps, {DURATION_S:.0f}s/cell. q={summary.get('q_source', 'oracle')}. Live ApplyGuardrail, no Maverick.",
        "Oracle cell archived in `results/replay/e1_oracle/`.",
        "",
        "| policy | demand | G_safe | UAR | reject | efficiency |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for m in summary["cells"]:
        eff = m["guardrail_capacity_efficiency"]
        eff_s = f"{eff:.2f}" if eff is not None else "—"
        lines.append(
            f"| {m['policy']} | {m['strong_demand_frac_of_rg']:.2f} Rg | "
            f"{m['safe_slo_goodput']:.3f} | {m['unsafe_admission_rate']:.3f} | "
            f"{m['reject_rate']:.3f} | {eff_s} |"
        )
    (out / "metrics.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
