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
