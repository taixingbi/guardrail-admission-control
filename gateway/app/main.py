from __future__ import annotations

import time
import uuid
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from gasc.limiter import StrongLimiter
from gasc.scheduler import SchedulerInputs, decide, policy_compliant
from gasc.schemas import TenantPolicy

from gateway.app.config import Settings

app = FastAPI(title="GASC gateway")
settings = Settings()
limiter = StrongLimiter(
    inflight_limit=settings.strong_inflight,
    queue_max=settings.queue_max,
    reserved_share={"A": 0.0, "B": 0.4},
    overflow_mode="reject" if settings.fail_closed else "queue",
)

TENANTS = {
    "A": TenantPolicy(tenant_id="A", tau=0.75, slo_ms=600, reserved_share=0.0),
    "B": TenantPolicy(tenant_id="B", tau=0.40, slo_ms=800, reserved_share=0.4),
}


class InferRequest(BaseModel):
    tenant_id: str = "A"
    text: str
    q: float | None = None
    g_light_label: str | None = None
    variant: str | None = None
    gt_label: str | None = None
    est_strong_wait_ms: float = 0.0


class InferResponse(BaseModel):
    request_id: str
    route: str
    reason: str
    q: float
    bypass: bool
    policy_compliant: bool
    admitted_to_llm: bool
    latency_ms: float
    metadata: dict[str, Any] = Field(default_factory=dict)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/infer", response_model=InferResponse)
async def infer(req: InferRequest) -> InferResponse:
    t0 = time.perf_counter()
    tenant = TENANTS.get(req.tenant_id, TENANTS["A"])
    if req.q is None:
        if settings.skip_llm:
            q, label = 0.1, "SAFE"
        else:
            from gasc.clients import score_risk

            q, label = score_risk(
                req.text,
                model_id=settings.g_light_model,
                region=settings.aws_region,
            )
    else:
        q = req.q
        label = req.g_light_label or ("REVIEW" if q >= 0.5 else "SAFE")

    available = limiter.inflight < limiter.limit
    decision = decide(
        SchedulerInputs(
            q=q,
            tenant=tenant,
            policy=settings.policy,  # type: ignore[arg-type]
            fail_closed=settings.fail_closed,
            strong_available=available,
            est_strong_wait_ms=req.est_strong_wait_ms,
            global_tau=settings.default_tau,
        )
    )
    route = decision.route
    acquired = False
    if route == "strong":
        got = await limiter.acquire(tenant.tenant_id)
        if got.ok:
            acquired = True
        elif settings.fail_closed:
            route = "reject"
            decision = decision.model_copy(update={"route": "reject", "reason": "safety_floor"})
        else:
            route = "direct"
            decision = decision.model_copy(update={"route": "direct", "reason": "fail_open_bypass", "bypass": True})

    admitted = route in {"direct", "strong"} and not decision.bypass
    if decision.bypass:
        admitted = True  # fail-open still hits Maverick
    if route == "reject":
        admitted = False

    if acquired:
        await limiter.release(tenant.tenant_id)

    latency_ms = (time.perf_counter() - t0) * 1000
    return InferResponse(
        request_id=str(uuid.uuid4()),
        route=route,
        reason=decision.reason,
        q=q,
        bypass=decision.bypass,
        policy_compliant=policy_compliant(decision, route),  # type: ignore[arg-type]
        admitted_to_llm=admitted,
        latency_ms=latency_ms,
        metadata={"g_light_label": label, "variant": req.variant, "gt_label": req.gt_label},
    )
