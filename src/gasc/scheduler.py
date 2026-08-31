from __future__ import annotations

from dataclasses import dataclass

from gasc.schemas import PolicyId, Route, ScheduleDecision, TenantPolicy


@dataclass
class SchedulerInputs:
    q: float
    tenant: TenantPolicy
    policy: PolicyId
    fail_closed: bool = True
    use_tenant: bool = True
    use_deadline: bool = True
    use_early_reject: bool = True
    strong_available: bool = True
    est_strong_wait_ms: float = 0.0
    t_strong_ms: float = 40.0
    t_llm_ms: float = 200.0
    elapsed_ms: float = 0.0
    global_tau: float = 0.5


def _risk_tau(inp: SchedulerInputs) -> float:
    if inp.policy == "proposed" and inp.use_tenant:
        return inp.tenant.tau
    return inp.global_tau


def _risk_required(inp: SchedulerInputs) -> bool:
    """True iff q ≥ the risk threshold (not always_strong's 'everything needs strong')."""
    return inp.q >= _risk_tau(inp)


def _need_strong(inp: SchedulerInputs) -> bool:
    if inp.policy == "always_strong":
        return True
    return _risk_required(inp)


def _deadline_miss(inp: SchedulerInputs) -> bool:
    if not inp.use_deadline:
        return False
    remaining = inp.tenant.slo_ms - inp.elapsed_ms
    need = inp.est_strong_wait_ms + inp.t_strong_ms + inp.t_llm_ms
    return need > remaining


def decide(inp: SchedulerInputs) -> ScheduleDecision:
    need = _need_strong(inp)
    risk_req = _risk_required(inp)
    if not need:
        return ScheduleDecision(
            route="direct",
            reason="below_threshold",
            need_strong=False,
            policy_required=False,
            q=inp.q,
            risk_required=risk_req,
        )

    if inp.policy == "risk_only":
        return ScheduleDecision(
            route="strong",
            reason="risk_only",
            need_strong=True,
            policy_required=True,
            q=inp.q,
            risk_required=risk_req,
        )

    if inp.use_deadline and inp.use_early_reject and _deadline_miss(inp):
        return ScheduleDecision(
            route="reject",
            reason="deadline",
            need_strong=True,
            policy_required=True,
            q=inp.q,
            risk_required=risk_req,
        )

    if inp.strong_available:
        return ScheduleDecision(
            route="strong",
            reason="strong_available",
            need_strong=True,
            policy_required=True,
            q=inp.q,
            risk_required=risk_req,
        )

    if inp.policy == "load_aware" or not inp.use_early_reject:
        # Queue until SLO explodes; still does not bypass.
        return ScheduleDecision(
            route="strong",
            reason="queue_anyway",
            need_strong=True,
            policy_required=True,
            q=inp.q,
            risk_required=risk_req,
        )

    if inp.fail_closed:
        return ScheduleDecision(
            route="reject",
            reason="safety_floor",
            need_strong=True,
            policy_required=True,
            q=inp.q,
            risk_required=risk_req,
        )

    return ScheduleDecision(
        route="direct",
        reason="fail_open_bypass",
        need_strong=True,
        policy_required=True,
        q=inp.q,
        bypass=True,
        risk_required=risk_req,
    )


def policy_compliant(decision: ScheduleDecision, route: Route) -> bool:
    if not decision.policy_required:
        return True
    if decision.bypass or route == "direct":
        return False
    return route in {"strong", "reject"}
