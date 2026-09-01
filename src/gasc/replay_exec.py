"""Shared E1–E6 / e2e request path: schedule, ApplyGuardrail, RunRecord."""

from __future__ import annotations

import asyncio
import os
import random
import time
from typing import Any, Literal

from dotenv import load_dotenv

from gasc.clients.bedrock import apply_guardrail, bedrock_runtime
from gasc.limiter import StrongLimiter
from gasc.paths import repo_root
from gasc.report import applied_strong, occupancy
from gasc.scheduler import SchedulerInputs, decide, policy_compliant
from gasc.schemas import FrozenPrompt, RunRecord, ScheduleDecision, TenantPolicy

BG = 0.4
R_GATEWAY = 3.01
T_STRONG_MS = 215.0
QUEUE_TIMEOUT_S = 2.0
POLICY_ORDER = ("always_strong", "risk_only", "load_aware", "proposed")
TENANT_A = TenantPolicy(tenant_id="A", tau=0.75, slo_ms=600, reserved_share=0.0)
TENANT_B = TenantPolicy(tenant_id="B", tau=0.40, slo_ms=800, reserved_share=0.4)


def overflow_mode(policy: str) -> str:
    return "queue" if policy in {"always_strong", "load_aware"} else "reject"


def make_limiter(*, overflow: str, reserved: dict[str, float] | None = None, bg_rps: float = BG) -> StrongLimiter:
    return StrongLimiter(
        inflight_limit=2,
        queue_max=16,
        reserved_share=reserved or {},
        overflow_mode=overflow,
        bg_rps=bg_rps,
        burst=1,
    )


def bedrock_session() -> dict[str, Any]:
    load_dotenv(repo_root() / ".env")
    return {
        "guardrail_id": os.environ["GASC_GUARDRAIL_ID"],
        "version": os.environ.get("GASC_GUARDRAIL_VERSION", "1"),
        "client": bedrock_runtime(os.environ.get("AWS_REGION", "us-east-1")),
    }


def decide_for(
    *,
    q: float,
    tenant: TenantPolicy,
    policy: str,
    limiter: StrongLimiter,
    fail_closed: bool = True,
    use_tenant: bool | None = None,
    use_deadline: bool = True,
    use_early_reject: bool = True,
    t_strong_ms: float = T_STRONG_MS,
    t_llm_ms: float = 0.0,
) -> ScheduleDecision:
    available = limiter.strong_available(tenant.tenant_id)
    if policy in {"always_strong", "load_aware"}:
        available = True
    return decide(
        SchedulerInputs(
            q=q,
            tenant=tenant,
            policy=policy,  # type: ignore[arg-type]
            fail_closed=fail_closed,
            use_tenant=policy == "proposed" if use_tenant is None else use_tenant,
            use_deadline=use_deadline,
            use_early_reject=use_early_reject,
            strong_available=available,
            est_strong_wait_ms=limiter.estimated_wait_ms(tenant.tenant_id),
            t_strong_ms=t_strong_ms,
            t_llm_ms=t_llm_ms,
            global_tau=0.5,
        )
    )


async def apply_if_strong(
    *,
    client,
    guardrail_id: str,
    version: str,
    limiter: StrongLimiter,
    tenant_id: str,
    text: str,
    route: str,
    decision: ScheduleDecision,
    api_lock: asyncio.Lock | None = None,
    timeout_s: float = QUEUE_TIMEOUT_S,
    on_full: Literal["reject", "bypass"] = "reject",
) -> tuple[str, ScheduleDecision, str | None]:
    if route != "strong":
        return route, decision, None
    got = await limiter.acquire(tenant_id, timeout_s=timeout_s)
    action = None
    if got.ok:
        try:
            if api_lock is None:
                out = await asyncio.to_thread(
                    apply_guardrail,
                    client,
                    guardrail_id=guardrail_id,
                    guardrail_version=version,
                    text=text,
                )
            else:
                async with api_lock:
                    out = await asyncio.to_thread(
                        apply_guardrail,
                        client,
                        guardrail_id=guardrail_id,
                        guardrail_version=version,
                        text=text,
                    )
            action = out.get("action")
        finally:
            await limiter.release(tenant_id)
        if action == "GUARDRAIL_INTERVENED":
            route = "reject"
            decision = decision.model_copy(update={"route": "reject", "reason": "guardrail_block", "bypass": False})
        return route, decision, action
    if on_full == "bypass":
        return "direct", decision.model_copy(
            update={"route": "direct", "reason": "fail_open_bypass", "bypass": True}
        ), None
    return "reject", decision.model_copy(update={"route": "reject", "reason": got.reason}), None


def finish_record(
    *,
    prompt: FrozenPrompt,
    tenant: TenantPolicy,
    policy: str,
    q: float,
    decision: ScheduleDecision,
    route: str,
    action: str | None,
    latency_ms: float,
    rng: random.Random,
    metadata: dict[str, Any] | None = None,
    admit_if_bypass: bool = False,
    g_light_label: str | None = None,
) -> RunRecord:
    admitted = route in {"direct", "strong"} and (admit_if_bypass or not decision.bypass)
    gt_unsafe = prompt.target_label == "unsafe"
    meta = {"apply_guardrail_action": action, **(metadata or {})}
    return RunRecord(
        request_id=str(rng.random()),
        tenant_id=tenant.tenant_id,
        variant_id=prompt.variant_id,
        variant=prompt.variant,
        gt_label=prompt.target_label,
        policy=policy,  # type: ignore[arg-type]
        q=q,
        g_light_label=g_light_label or ("REVIEW" if q >= 0.5 else "SAFE"),  # type: ignore[arg-type]
        decision=decision,
        route=route,  # type: ignore[arg-type]
        admitted_to_llm=admitted,
        latency_ms=latency_ms,
        slo_ms=tenant.slo_ms,
        policy_compliant=policy_compliant(decision, route),  # type: ignore[arg-type]
        safe=not (gt_unsafe and admitted),
        slo_ok=latency_ms <= tenant.slo_ms,
        apply_guardrail_action=action,
        metadata=meta,
    )


async def run_scheduled(
    *,
    client,
    guardrail_id: str,
    version: str,
    limiter: StrongLimiter,
    prompt: FrozenPrompt,
    tenant: TenantPolicy,
    policy: str,
    q: float,
    rng: random.Random,
    api_lock: asyncio.Lock | None = None,
    fail_closed: bool = True,
    use_tenant: bool | None = None,
    use_deadline: bool = True,
    use_early_reject: bool = True,
    t_llm_ms: float = 0.0,
    t_strong_ms: float = T_STRONG_MS,
    on_full: Literal["reject", "bypass"] = "reject",
    metadata: dict[str, Any] | None = None,
    admit_if_bypass: bool = False,
) -> RunRecord:
    t0 = time.perf_counter()
    decision = decide_for(
        q=q,
        tenant=tenant,
        policy=policy,
        limiter=limiter,
        fail_closed=fail_closed,
        use_tenant=use_tenant,
        use_deadline=use_deadline,
        use_early_reject=use_early_reject,
        t_strong_ms=t_strong_ms,
        t_llm_ms=t_llm_ms,
    )
    route, decision, action = await apply_if_strong(
        client=client,
        guardrail_id=guardrail_id,
        version=version,
        limiter=limiter,
        tenant_id=tenant.tenant_id,
        text=prompt.text,
        route=decision.route,
        decision=decision,
        api_lock=api_lock,
        on_full=on_full,
    )
    return finish_record(
        prompt=prompt,
        tenant=tenant,
        policy=policy,
        q=q,
        decision=decision,
        route=route,
        action=action,
        latency_ms=(time.perf_counter() - t0) * 1000,
        rng=rng,
        metadata=metadata,
        admit_if_bypass=admit_if_bypass,
    )


def need_occupancy(recs: list[RunRecord]) -> dict[str, Any]:
    return occupancy(recs)
