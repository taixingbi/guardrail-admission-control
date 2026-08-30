#!/usr/bin/env python3
"""E3: dynamic safety load. Gateway RPS fixed; strong-mix steps over 480 s.

Phases: 0.5 → 0.9 → 1.5 → 0.6 Rg. Tenant A only. Live E0a q when present.
Live ApplyGuardrail; Maverick skipped so the series isolates safety capacity.
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
DURATION_S = 480.0
BIN_S = 10.0
PHASES = (
    (120.0, 0.5),
    (240.0, 0.9),
    (360.0, 1.5),
    (480.0, 0.6),
)
POLICIES = ("always_strong", "risk_only", "load_aware", "proposed")
TENANT = TenantPolicy(tenant_id="A", tau=0.75, slo_ms=600, reserved_share=0.0)
T_STRONG_MS = 215.0
QUEUE_TIMEOUT_S = 2.0


def _overflow(policy: str) -> str:
    return "queue" if policy in {"always_strong", "load_aware"} else "reject"


def _frac_at(t_s: float) -> float:
    for until, frac in PHASES:
        if t_s < until:
            return frac
    return PHASES[-1][1]


def _phase_name(t_s: float) -> str:
    prev = 0.0
    for until, frac in PHASES:
        if t_s < until:
            return f"{prev:.0f}-{until:.0f}s@{frac:.1f}Rg"
        prev = until
    until, frac = PHASES[-1]
    return f"{prev:.0f}-{until:.0f}s@{frac:.1f}Rg"


async def _one(*, client, guardrail_id, version, limiter, policy, prompt, rng, api_lock, t_s, live_q) -> RunRecord:
    t0 = time.perf_counter()
    q = q_for(prompt, live_q)
    available = limiter.strong_available(TENANT.tenant_id)
    if policy in {"always_strong", "load_aware"}:
        available = True
    decision = decide(
        SchedulerInputs(
            q=q,
            tenant=TENANT,
            policy=policy,  # type: ignore[arg-type]
            fail_closed=True,
            use_tenant=policy == "proposed",
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
        else:
            route = "reject"
            decision = decision.model_copy(update={"route": "reject", "reason": got.reason})
    if acquired:
        await limiter.release(TENANT.tenant_id)
    latency_ms = (time.perf_counter() - t0) * 1000
    admitted = route in {"direct", "strong"} and not decision.bypass
    if action == "GUARDRAIL_INTERVENED":
        admitted = False
        route = "reject"
        decision = decision.model_copy(update={"route": "reject", "reason": "guardrail_block"})
    gt_unsafe = prompt.target_label == "unsafe"
    return RunRecord(
        request_id=str(rng.random()),
        tenant_id=TENANT.tenant_id,
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
        safe=not (gt_unsafe and admitted),
        slo_ok=latency_ms <= TENANT.slo_ms,
        metadata={
            "apply_guardrail_action": action,
            "t_s": t_s,
            "strong_frac_of_rg": _frac_at(t_s),
            "phase": _phase_name(t_s),
        },
    )


def _window_metrics(recs: list[RunRecord], duration_s: float) -> dict:
    m = aggregate(recs, duration_s=duration_s)
    need = [r for r in recs if r.decision.need_strong]
    checked = [r for r in need if r.metadata.get("apply_guardrail_action") is not None]
    starved = [r for r in need if r.metadata.get("apply_guardrail_action") is None]
    m.update(
        {
            "n_need": len(need),
            "n_checked": len(checked),
            "n_starved": len(starved),
            "checked_rate": (len(checked) / len(need)) if need else None,
        }
    )
    return m


async def _cell(*, client, guardrail_id, version, policy, prompts_safe, prompts_unsafe, live_q) -> dict:
    limiter = StrongLimiter(
        inflight_limit=2,
        queue_max=16,
        reserved_share={},
        overflow_mode=_overflow(policy),
        rg_rps=RG,
        burst=1,
    )
    api_lock = asyncio.Lock()
    rng = random.Random(30 + POLICIES.index(policy) * 17)
    interval = 1.0 / R_GATEWAY
    n_slots = int(DURATION_S / interval)
    planned = []
    for i in range(n_slots):
        t_s = i * interval
        p_unsafe = (_frac_at(t_s) * RG) / R_GATEWAY
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
    phases = []
    prev = 0.0
    for until, frac in PHASES:
        chunk = [r for r in recs if prev <= float(r.metadata["t_s"]) < until]
        row = _window_metrics(chunk, until - prev)
        row.update({"policy": policy, "phase": f"{prev:.0f}-{until:.0f}s", "strong_frac_of_rg": frac, "n": len(chunk)})
        phases.append(row)
        prev = until
    series = []
    n_bins = int(DURATION_S / BIN_S)
    for b in range(n_bins):
        lo, hi = b * BIN_S, (b + 1) * BIN_S
        chunk = [r for r in recs if lo <= float(r.metadata["t_s"]) < hi]
        row = _window_metrics(chunk, BIN_S)
        row.update({"t0": lo, "t1": hi, "n": len(chunk), "strong_frac_of_rg": _frac_at(lo)})
        series.append(row)
    return {
        "metrics": overall,
        "phases": phases,
        "series": series,
        "records": [json.loads(r.model_dump_json()) for r in recs],
    }


async def _run() -> dict:
    root = Path(__file__).resolve().parents[1]
    load_dotenv(root / ".env")
    gid = os.environ["GASC_GUARDRAIL_ID"]
    gver = os.environ.get("GASC_GUARDRAIL_VERSION", "1")
    frozen = load_replay_prompts()
    safe, unsafe = split_safe_unsafe(frozen)
    live_q = load_live_q()
    print(f"E3 replay n={len(frozen)} safe={len(safe)} unsafe={len(unsafe)} live_q={len(live_q)}", flush=True)
    client = bedrock_runtime(os.environ.get("AWS_REGION", "us-east-1"))
    out = replay_dir("e3")
    out.mkdir(parents=True, exist_ok=True)
    cells = []
    for policy in POLICIES:
        print(f"E3 {policy} 480s …", flush=True)
        cell = await _cell(
            client=client,
            guardrail_id=gid,
            version=gver,
            policy=policy,
            prompts_safe=safe,
            prompts_unsafe=unsafe,
            live_q=live_q,
        )
        print(json.dumps({"policy": policy, "overall": cell["metrics"], "phases": cell["phases"]}, indent=2), flush=True)
        (out / f"{policy}.jsonl").write_text("\n".join(json.dumps(r) for r in cell["records"]) + "\n")
        (out / f"{policy}_series.json").write_text(json.dumps(cell["series"], indent=2))
        cells.append({"overall": cell["metrics"], "phases": cell["phases"], "series": cell["series"]})
    return {
        "rg": RG,
        "r_gateway": R_GATEWAY,
        "duration_s": DURATION_S,
        "bin_s": BIN_S,
        "phases": [{"until_s": u, "strong_frac_of_rg": f} for u, f in PHASES],
        "q_source": "e0a_live" if live_q else "oracle",
        "n_live_q": len(live_q),
        "cells": cells,
    }


def _md(summary: dict) -> str:
    lines = [
        "# E3 dynamic safety load (freeze replay)",
        "",
        f"R_gateway={R_GATEWAY} rps, Rg={RG} rps, {DURATION_S:.0f}s/policy. Mix 0.5→0.9→1.5→0.6 Rg.",
        f"Tenant A only. q={summary.get('q_source', 'oracle')}. Live ApplyGuardrail, no Maverick.",
        "Oracle cell archived in `results/replay/e3_oracle/`.",
        "",
        "## Per phase",
        "",
        "| policy | phase | demand | G_safe | UAR | reject | checked | starved |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for cell in summary["cells"]:
        for m in cell["phases"]:
            chk = m["checked_rate"]
            chk_s = "—" if chk is None else f"{chk:.2f}"
            lines.append(
                f"| {m['policy']} | {m['phase']} | {m['strong_frac_of_rg']:.1f} Rg | "
                f"{m['safe_slo_goodput']:.3f} | {m['unsafe_admission_rate']:.3f} | "
                f"{m['reject_rate']:.3f} | {chk_s} | {m['n_starved']} |"
            )
    lines += [
        "",
        "## Overall",
        "",
        "| policy | G_safe | UAR | reject | checked | starved |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for cell in summary["cells"]:
        m = cell["overall"]
        chk = m["checked_rate"]
        chk_s = "—" if chk is None else f"{chk:.2f}"
        lines.append(
            f"| {m['policy']} | {m['safe_slo_goodput']:.3f} | {m['unsafe_admission_rate']:.3f} | "
            f"{m['reject_rate']:.3f} | {chk_s} | {m['n_starved']} |"
        )
    lines += ["", "## G_safe time series (10 s bins)", ""]
    for cell in summary["cells"]:
        policy = cell["overall"]["policy"]
        ys = " ".join(f"{row['safe_slo_goodput']:.2f}" for row in cell["series"])
        lines.append(f"- **{policy}:** `{ys}`")
    return "\n".join(lines) + "\n"


def main() -> int:
    summary = asyncio.run(_run())
    out = replay_dir("e3")
    (out / "metrics.json").write_text(json.dumps(summary, indent=2))
    (out / "metrics.md").write_text(_md(summary))
    print(f"wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
