from gasc.scheduler import SchedulerInputs, decide, policy_compliant
from gasc.schemas import TenantPolicy

A = TenantPolicy(tenant_id="A", tau=0.75, slo_ms=600, reserved_share=0.0)
B = TenantPolicy(tenant_id="B", tau=0.40, slo_ms=800, reserved_share=0.4)


def test_proposed_never_bypasses_required_strong():
    d = decide(
        SchedulerInputs(
            q=0.9,
            tenant=B,
            policy="proposed",
            fail_closed=True,
            strong_available=False,
        )
    )
    assert d.route == "reject"
    assert d.reason == "safety_floor"
    assert not d.bypass
    assert policy_compliant(d, "reject")


def test_fail_open_bypasses_when_no_capacity():
    d = decide(
        SchedulerInputs(
            q=0.9,
            tenant=B,
            policy="proposed",
            fail_closed=False,
            strong_available=False,
        )
    )
    assert d.route == "direct"
    assert d.bypass
    assert not policy_compliant(d, "direct")


def test_below_threshold_goes_direct():
    d = decide(SchedulerInputs(q=0.2, tenant=A, policy="proposed", global_tau=0.5))
    assert d.route == "direct"
    assert not d.policy_required


def test_tenant_b_requires_strong_earlier_than_a():
    low = 0.5
    a = decide(SchedulerInputs(q=low, tenant=A, policy="proposed"))
    b = decide(SchedulerInputs(q=low, tenant=B, policy="proposed"))
    assert a.route == "direct"
    assert b.route == "strong"


def test_deadline_early_reject():
    d = decide(
        SchedulerInputs(
            q=0.9,
            tenant=A,
            policy="proposed",
            strong_available=True,
            est_strong_wait_ms=500,
            t_strong_ms=40,
            t_llm_ms=200,
        )
    )
    assert d.route == "reject"
    assert d.reason == "deadline"


def test_no_early_reject_queues():
    d = decide(
        SchedulerInputs(
            q=0.9,
            tenant=A,
            policy="proposed",
            use_early_reject=False,
            strong_available=False,
        )
    )
    assert d.route == "strong"
    assert d.reason == "queue_anyway"
    assert not d.bypass


def test_always_strong_ignores_q():
    d = decide(SchedulerInputs(q=0.01, tenant=A, policy="always_strong"))
    assert d.need_strong
    assert d.route == "strong"
    assert d.policy_required
    assert d.risk_required is False


def test_always_strong_risk_required_tracks_global_tau():
    low = decide(SchedulerInputs(q=0.01, tenant=A, policy="always_strong", global_tau=0.5))
    high = decide(SchedulerInputs(q=0.9, tenant=A, policy="always_strong", global_tau=0.5))
    assert low.need_strong and not low.risk_required
    assert high.need_strong and high.risk_required


def test_proposed_risk_required_uses_tenant_tau():
    d = decide(SchedulerInputs(q=0.6, tenant=A, policy="proposed", global_tau=0.5))
    assert d.route == "direct"
    assert d.risk_required is False
    d = decide(SchedulerInputs(q=0.6, tenant=B, policy="proposed", global_tau=0.5))
    assert d.route == "strong"
    assert d.risk_required is True


def test_finish_record_fail_open_admits_bypass():
    import random

    from gasc.replay_exec import finish_record
    from gasc.schemas import FrozenPrompt, ScheduleDecision

    prompt = FrozenPrompt(
        variant_id="p",
        seed_id="p",
        variant="S2",
        text="x",
        target_label="unsafe",
    )
    decision = ScheduleDecision(
        route="direct",
        reason="fail_open_bypass",
        need_strong=True,
        policy_required=True,
        q=0.9,
        bypass=True,
        risk_required=True,
    )
    closed = finish_record(
        prompt=prompt,
        tenant=A,
        policy="proposed",
        q=0.9,
        decision=decision,
        route="direct",
        action=None,
        latency_ms=10.0,
        rng=random.Random(0),
    )
    opened = finish_record(
        prompt=prompt,
        tenant=A,
        policy="proposed",
        q=0.9,
        decision=decision,
        route="direct",
        action=None,
        latency_ms=10.0,
        rng=random.Random(0),
        admit_if_bypass=True,
    )
    assert not closed.admitted_to_llm
    assert opened.admitted_to_llm
    assert not opened.safe
