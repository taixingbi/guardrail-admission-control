#!/usr/bin/env python3
"""Live end-to-end sanity: Function URL MiniLM + scheduler + ApplyGuardrail + Maverick.

Not a substitute for E1–E6 (those replay frozen q). One Proposed cell at 1.0 Bg.
replay_q is the paper-comparable path (frozen q). live_path puts Function URL MiniLM
on every request (~500 ms P50 from E0a) and is not the 600 ms SLO architecture number.
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import time
from pathlib import Path

from dotenv import load_dotenv

from gasc.clients.minilm import score_minilm_remote
from gasc.clients.bedrock import apply_guardrail, bedrock_runtime, converse_stream
from gasc.eval_binary import percentile
from gasc.limiter import StrongLimiter
from gasc.replay_data import load_live_q, load_replay_prompts, q_for, replay_dir, split_safe_unsafe
from gasc.report import aggregate
from gasc.scheduler import SchedulerInputs, decide, policy_compliant
from gasc.schemas import RunRecord, TenantPolicy

BG = 0.4
R_GATEWAY = 3.01
DURATION_S = 40.0
FRAC = 1.0
TENANT = TenantPolicy(tenant_id="A", tau=0.75, slo_ms=600, reserved_share=0.0)
T_STRONG_MS = 215.0
T_LLM_MS = 250.0
QUEUE_TIMEOUT_S = 2.0
C_STAR = 2
LLM = "us.meta.llama4-maverick-17b-instruct-v1:0"
MAX_TOKENS = 64


def _score_live(_client, text: str) -> tuple[float, str, float]:
    t0 = time.perf_counter()
    q, label = score_minilm_remote(text)
    return q, label, (time.perf_counter() - t0) * 1000


async def _one(
    *,
    client,
    guardrail_id: str,
    version: str,
    limiter: StrongLimiter,
    llm_sem: asyncio.Semaphore,
    prompt,
    rng: random.Random,
    api_lock: asyncio.Lock,
    live_q: dict[str, float],
    live_g_light: bool,
) -> RunRecord:
    t0 = time.perf_counter()
    g_light_ms = 0.0
    if live_g_light:
        q, label, g_light_ms = await asyncio.to_thread(_score_live, client, prompt.text)
    else:
        q = q_for(prompt, live_q)
        label = "REVIEW" if q >= 0.5 else "SAFE"
    available = limiter.strong_available(TENANT.tenant_id)
    decision = decide(
        SchedulerInputs(
            q=q,
            tenant=TENANT,
            policy="proposed",
            fail_closed=True,
            use_tenant=True,
            strong_available=available,
            est_strong_wait_ms=limiter.estimated_wait_ms(TENANT.tenant_id),
            t_strong_ms=T_STRONG_MS,
            t_llm_ms=T_LLM_MS,
            global_tau=0.5,
        )
    )
    route = decision.route
    action = None
    acquired = False
    strong_ms = 0.0
    if route == "strong":
        got = await limiter.acquire(TENANT.tenant_id, timeout_s=QUEUE_TIMEOUT_S)
        if got.ok:
            acquired = True
            t_s = time.perf_counter()
            async with api_lock:
                out = await asyncio.to_thread(
                    apply_guardrail,
                    client,
                    guardrail_id=guardrail_id,
                    guardrail_version=version,
                    text=prompt.text,
                )
            strong_ms = (time.perf_counter() - t_s) * 1000
            action = out.get("action")
        else:
            route = "reject"
            decision = decision.model_copy(update={"route": "reject", "reason": got.reason})
    if acquired:
        await limiter.release(TENANT.tenant_id)
    if action == "GUARDRAIL_INTERVENED":
        route = "reject"
        decision = decision.model_copy(update={"route": "reject", "reason": "guardrail_block"})
    admitted = route in {"direct", "strong"} and not decision.bypass
    llm_ttft = None
    llm_e2e = None
    llm_err = None
    if admitted:
        async with llm_sem:
            t_l = time.perf_counter()
            rec = await asyncio.to_thread(
                converse_stream,
                client,
                model_id=LLM,
                user=prompt.text,
                max_tokens=MAX_TOKENS,
            )
            llm_e2e = (time.perf_counter() - t_l) * 1000
        llm_ttft = rec.ttft_ms
        if rec.throttled or rec.error:
            llm_err = rec.error or "throttled"
            admitted = False
            route = "reject"
            decision = decision.model_copy(update={"route": "reject", "reason": "llm_error"})
    latency_ms = (time.perf_counter() - t0) * 1000
    gt_unsafe = prompt.target_label == "unsafe"
    return RunRecord(
        request_id=str(rng.random()),
        tenant_id=TENANT.tenant_id,
        variant_id=prompt.variant_id,
        variant=prompt.variant,
        gt_label=prompt.target_label,
        policy="proposed",
        q=q,
        g_light_label=label,  # type: ignore[arg-type]
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
            "g_light_ms": g_light_ms,
            "strong_ms": strong_ms,
            "llm_ttft_ms": llm_ttft,
            "llm_e2e_ms": llm_e2e,
            "llm_error": llm_err,
            "live_g_light": live_g_light,
        },
    )


def _extra(recs: list[RunRecord]) -> dict:
    admitted = [r for r in recs if r.admitted_to_llm]
    e2e = [r.latency_ms for r in admitted]
    ttft = [r.metadata["llm_ttft_ms"] for r in admitted if r.metadata.get("llm_ttft_ms") is not None]
    gms = [r.metadata["g_light_ms"] for r in recs if r.metadata.get("g_light_ms")]
    served_800 = sum(1 for r in recs if r.admitted_to_llm and r.safe and r.policy_compliant and r.latency_ms <= 800)
    return {
        "n_admitted": len(admitted),
        "e2e_p50_ms": percentile(e2e, 50) if e2e else None,
        "e2e_p95_ms": percentile(e2e, 95) if e2e else None,
        "ttft_p50_ms": percentile(ttft, 50) if ttft else None,
        "ttft_p95_ms": percentile(ttft, 95) if ttft else None,
        "g_light_p50_ms": percentile(gms, 50) if gms else None,
        "g_light_p95_ms": percentile(gms, 95) if gms else None,
        "slo_800_goodput": served_800 / DURATION_S,
        "n_llm_error": sum(1 for r in recs if r.metadata.get("llm_error")),
        "slo_ok_admitted": (sum(1 for r in admitted if r.slo_ok) / len(admitted)) if admitted else None,
    }


async def _cell(*, client, guardrail_id, version, live_q, live_g_light, prompts_safe, prompts_unsafe) -> dict:
    limiter = StrongLimiter(
        inflight_limit=2,
        queue_max=16,
        reserved_share={},
        overflow_mode="reject",
        bg_rps=BG,
        burst=1,
    )
    llm_sem = asyncio.Semaphore(C_STAR)
    api_lock = asyncio.Lock()
    rng = random.Random(80 if live_g_light else 70)
    interval = 1.0 / R_GATEWAY
    p_unsafe = (FRAC * BG) / R_GATEWAY
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
            llm_sem=llm_sem,
            prompt=prompt,
            rng=rng,
            api_lock=api_lock,
            live_q=live_q,
            live_g_light=live_g_light,
        )

    recs = list(await asyncio.gather(*[_scheduled(i, p) for i, p in enumerate(planned)]))
    metrics = aggregate(recs, duration_s=DURATION_S)
    metrics.update(_extra(recs))
    metrics.update({"cell": "live_path" if live_g_light else "replay_q", "n": len(recs)})
    return {"metrics": metrics, "records": [json.loads(r.model_dump_json()) for r in recs]}


async def _run() -> dict:
    root = Path(__file__).resolve().parents[1]
    load_dotenv(root / ".env")
    gid = os.environ["GASC_GUARDRAIL_ID"]
    gver = os.environ.get("GASC_GUARDRAIL_VERSION", "1")
    frozen = load_replay_prompts()
    safe, unsafe = split_safe_unsafe(frozen)
    live_q = load_live_q(required=True)
    print(f"E2e n={len(frozen)} live_q={len(live_q)}", flush=True)
    client = bedrock_runtime(os.environ.get("AWS_REGION", "us-east-1"))
    out = replay_dir("e2e")
    cells = []
    for live_g_light, name in ((False, "replay_q"), (True, "live_path")):
        print(f"E2e {name} 40s …", flush=True)
        cell = await _cell(
            client=client,
            guardrail_id=gid,
            version=gver,
            live_q=live_q,
            live_g_light=live_g_light,
            prompts_safe=safe,
            prompts_unsafe=unsafe,
        )
        print(json.dumps(cell["metrics"], indent=2), flush=True)
        cells.append(cell["metrics"])
        (out / f"{name}.jsonl").write_text("\n".join(json.dumps(r) for r in cell["records"]) + "\n")
    return {
        "bg": BG,
        "r_gateway": R_GATEWAY,
        "duration_s": DURATION_S,
        "frac": FRAC,
        "c_star": C_STAR,
        "t_llm_ms": T_LLM_MS,
        "note": "Scout only. Does not retune tau, Bg, or Tenant A SLO. live_path is wiring, not the SLO path.",
        "cells": cells,
    }


def main() -> int:
    summary = asyncio.run(_run())
    out = replay_dir("e2e")
    (out / "metrics.json").write_text(json.dumps(summary, indent=2))
    lines = [
        "# E2e sanity (Proposed, 1.0 Bg, 40s)",
        "",
        "Tenant A SLO 600 ms unchanged. Maverick C*=2. t_llm_ms=250 (E0c TTFT P50).",
        "Does not retune τ or Bg. E1–E6 stay Maverick-off.",
        "replay_q uses frozen Function URL q (paper path). live_path scores every request via Function URL;",
        "E0a MiniLM P50 is ~524 ms, so live_path cannot represent the 600 ms SLO architecture.",
        "",
        "| cell | G_safe@600 | G_safe@800 | UAR | e2e P50 | e2e P95 | TTFT P95 | admitted SLO |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for m in summary["cells"]:
        def fmt(x):
            return "—" if x is None else f"{x:.0f}" if isinstance(x, float) and x > 2 else ( "—" if x is None else f"{x:.3f}")

        slo = m["slo_ok_admitted"]
        slo_s = "—" if slo is None else f"{slo:.2f}"
        lines.append(
            f"| {m['cell']} | {m['safe_slo_goodput']:.3f} | {m['slo_800_goodput']:.3f} | "
            f"{m['unsafe_admission_rate']:.3f} | {fmt(m['e2e_p50_ms'])} | {fmt(m['e2e_p95_ms'])} | "
            f"{fmt(m['ttft_p95_ms'])} | {slo_s} |"
        )
    (out / "metrics.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
