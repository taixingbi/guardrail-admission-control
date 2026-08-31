#!/usr/bin/env python3
"""E5: fail-open vs fail-closed at 1.5 and 2.0 Rg.

Proposed only. Fail-open turns off deadline so exhaustion can reach bypass;
fail-closed keeps the frozen B4 path (deadline + safety_floor).
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

RG = 0.4
R_GATEWAY = 3.01
DURATION_S = 60.0
REPS = 5
FRACS = (1.5, 2.0)
MODES = (
    ("proposed_fail_closed", True, True),
    ("proposed_fail_open", False, False),
)
TENANT = TenantPolicy(tenant_id="A", tau=0.75, slo_ms=600, reserved_share=0.0)
T_STRONG_MS = 215.0
QUEUE_TIMEOUT_S = 2.0


async def _one(*, client, guardrail_id, version, limiter, mode, fail_closed, use_deadline, prompt, rng, api_lock, live_q) -> RunRecord:
    t0 = time.perf_counter()
    q = q_for(prompt, live_q)
    available = limiter.strong_available(TENANT.tenant_id)
    decision = decide(
        SchedulerInputs(
            q=q,
            tenant=TENANT,
            policy="proposed",
            fail_closed=fail_closed,
            use_tenant=True,
            use_deadline=use_deadline,
            use_early_reject=True,
            strong_available=available,
            est_strong_wait_ms=limiter.estimated_wait_ms(TENANT.tenant_id),
            t_strong_ms=T_STRONG_MS,
            t_llm_ms=0.0,
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
            async with api_lock:
                out = await asyncio.to_thread(
                    apply_guardrail,
                    client,
                    guardrail_id=guardrail_id,
                    guardrail_version=version,
                    text=prompt.text,
                )
            action = out.get("action")
        elif fail_closed:
            route = "reject"
            decision = decision.model_copy(update={"route": "reject", "reason": got.reason})
        else:
            route = "direct"
            decision = decision.model_copy(
                update={"route": "direct", "reason": "fail_open_bypass", "bypass": True}
            )
    if acquired:
        await limiter.release(TENANT.tenant_id)
    latency_ms = (time.perf_counter() - t0) * 1000
    if action == "GUARDRAIL_INTERVENED":
        route = "reject"
        decision = decision.model_copy(update={"route": "reject", "reason": "guardrail_block", "bypass": False})
    admitted = route in {"direct", "strong"}
    gt_unsafe = prompt.target_label == "unsafe"
    return RunRecord(
        request_id=str(rng.random()),
        tenant_id=TENANT.tenant_id,
        variant_id=prompt.variant_id,
        variant=prompt.variant,
        gt_label=prompt.target_label,
        policy="proposed",
        q=q,
        g_light_label="REVIEW" if q >= 0.5 else "SAFE",
        decision=decision,
        route=route,  # type: ignore[arg-type]
        admitted_to_llm=admitted,
        latency_ms=latency_ms,
        slo_ms=TENANT.slo_ms,
        policy_compliant=policy_compliant(decision, route),  # type: ignore[arg-type]
        safe=not (gt_unsafe and admitted),
        slo_ok=latency_ms <= TENANT.slo_ms,
        metadata={
            "apply_guardrail_action": action,
            "mode": mode,
            "fail_closed": fail_closed,
        },
    )


def _extra(recs: list[RunRecord]) -> dict:
    need = [r for r in recs if r.decision.need_strong]
    bypass = [r for r in recs if r.decision.bypass]
    unsafe = [r for r in recs if r.gt_label == "unsafe"]
    return {
        "n_need": len(need),
        "n_bypass": len(bypass),
        "n_bypass_unsafe": sum(1 for r in bypass if r.gt_label == "unsafe"),
        "bypass_rate_need": (len(bypass) / len(need)) if need else 0.0,
        "n_checked": sum(1 for r in need if r.metadata.get("apply_guardrail_action") is not None),
        "n_unsafe": len(unsafe),
    }


async def _cell(*, client, guardrail_id, version, mode, fail_closed, use_deadline, frac, prompts_safe, prompts_unsafe, live_q, rep: int = 0) -> dict:
    limiter = StrongLimiter(
        inflight_limit=2,
        queue_max=16,
        reserved_share={},
        overflow_mode="reject",
        rg_rps=RG,
        burst=1,
    )
    api_lock = asyncio.Lock()
    rng = random.Random(50 + int(frac * 10) + (0 if fail_closed else 7) + rep * 1000)
    interval = 1.0 / R_GATEWAY
    p_unsafe = (frac * RG) / R_GATEWAY
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
            "strong_demand_frac_of_rg": frac,
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
    frozen = load_replay_prompts()
    safe, unsafe = split_safe_unsafe(frozen)
    live_q = load_live_q(required=True)
    print(
        f"E5 replay n={len(frozen)} safe={len(safe)} unsafe={len(unsafe)} "
        f"frozen_q={len(live_q)} {REPS} reps",
        flush=True,
    )
    client = bedrock_runtime(os.environ.get("AWS_REGION", "us-east-1"))
    out = replay_dir("e5")
    out.mkdir(parents=True, exist_ok=True)
    cells = []
    for rep in range(REPS):
        for mode, fail_closed, use_deadline in MODES:
            for frac in FRACS:
                print(f"E5 r{rep} {mode} {frac:.1f} Rg …", flush=True)
                cell = await _cell(
                    client=client,
                    guardrail_id=gid,
                    version=gver,
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
    return {
        "rg": RG,
        "r_gateway": R_GATEWAY,
        "duration_s": DURATION_S,
        "reps": REPS,
        "q_source": "frozen_g_light",
        "n_live_q": len(live_q),
        "cells": cells,
        "pooled": pool_by(
            cells,
            ("mode", "strong_demand_frac_of_rg"),
            ("safe_slo_goodput", "unsafe_admission_rate", "reject_rate", "bypass_rate_need"),
        ),
    }


def main() -> int:
    summary = asyncio.run(_run())
    out = replay_dir("e5")
    (out / "metrics.json").write_text(json.dumps(summary, indent=2))
    lines = [
        "# E5 fail-open vs fail-closed (frozen minilm-l12-h384 q, 5 reps)",
        "",
        f"Proposed only. R_gateway={R_GATEWAY}, Rg={RG}, {DURATION_S:.0f}s/cell × {summary['reps']} reps. q={summary.get('q_source')}.",
        "Fail-open disables deadline so exhaustion can bypass. Fail-closed keeps frozen B4.",
        "Paper cells are median [p25, p75]. MiniLM is a screener, not the authority. Do not retune τ.",
        "",
        "| mode | demand | G_safe | UAR | reject | bypass/need |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for m in summary["pooled"]:
        lines.append(
            f"| {m['mode']} | {m['strong_demand_frac_of_rg']:.1f} Rg | "
            f"{fmt_stat(m['safe_slo_goodput'])} | {fmt_stat(m['unsafe_admission_rate'])} | "
            f"{fmt_stat(m['reject_rate'])} | {fmt_stat(m['bypass_rate_need'], digits=2)} |"
        )
    (out / "metrics.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
