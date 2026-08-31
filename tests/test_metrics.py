from gasc.report import aggregate
from gasc.risk import parse_minilm, parse_risk
from gasc.scheduler import ScheduleDecision
from gasc.schemas import RunRecord


def _rec(**kwargs) -> RunRecord:
    base = dict(
        request_id="r",
        tenant_id="A",
        policy="proposed",
        q=0.2,
        g_light_label="SAFE",
        decision=ScheduleDecision(
            route="direct",
            reason="below_threshold",
            need_strong=False,
            policy_required=False,
            q=0.2,
        ),
        route="direct",
        admitted_to_llm=True,
        latency_ms=100,
        slo_ms=600,
        policy_compliant=True,
        safe=True,
        slo_ok=True,
        gt_label="safe",
    )
    base.update(kwargs)
    return RunRecord(**base)


def test_parse_risk_fail_closed():
    q, label = parse_risk("not json")
    assert q == 1.0 and label == "REVIEW"
    q, label = parse_risk('{"q": 0.1, "label": "SAFE"}')
    assert q == 0.1 and label == "SAFE"


def test_parse_minilm_harmful_probs():
    q, label = parse_minilm(
        '{"label":"harmful","score":0.91,"probs":{"unharmful":0.09,"harmful":0.91},"tokens":8}'
    )
    assert abs(q - 0.91) < 1e-9 and label == "REVIEW"
    q, label = parse_minilm(
        '{"label":"unharmful","score":0.97,"probs":{"unharmful":0.97,"harmful":0.03}}'
    )
    assert abs(q - 0.03) < 1e-9 and label == "SAFE"
    q, label = parse_risk(
        '{"label":"harmful","score":0.8,"probs":{"unharmful":0.2,"harmful":0.8}}'
    )
    assert abs(q - 0.8) < 1e-9 and label == "REVIEW"


def test_safe_slo_goodput_and_unsafe_admission():
    records = [
        _rec(request_id="1"),
        _rec(
            request_id="2",
            gt_label="unsafe",
            admitted_to_llm=True,
            safe=False,
            tenant_id="B",
            policy_compliant=False,
        ),
        _rec(request_id="3", tenant_id="B", route="reject", admitted_to_llm=False, slo_ok=True, safe=True),
    ]
    m = aggregate(records, duration_s=2.0)
    assert m["safe_slo_goodput"] == 0.5  # only served compliant-safe-SLO record / 2s
    assert m["unsafe_admission_rate"] == 1.0
    assert m["bypass_count"] == 0


def test_always_strong_efficiency_counts_risk_waste():
    """Always-Strong occupancy with q < τ is waste; efficiency is not identically 1."""
    waste = _rec(
        request_id="waste",
        policy="always_strong",
        q=0.1,
        route="strong",
        decision=ScheduleDecision(
            route="strong",
            reason="strong_available",
            need_strong=True,
            policy_required=True,
            q=0.1,
            risk_required=False,
        ),
    )
    needed = _rec(
        request_id="need",
        policy="always_strong",
        q=0.9,
        route="strong",
        decision=ScheduleDecision(
            route="strong",
            reason="strong_available",
            need_strong=True,
            policy_required=True,
            q=0.9,
            risk_required=True,
        ),
    )
    m = aggregate([waste, needed], duration_s=1.0)
    assert m["guardrail_capacity_efficiency"] == 0.5


def test_risk_only_efficiency_is_one():
    recs = [
        _rec(
            request_id="s",
            policy="risk_only",
            q=0.8,
            route="strong",
            decision=ScheduleDecision(
                route="strong",
                reason="risk_only",
                need_strong=True,
                policy_required=True,
                q=0.8,
                risk_required=True,
            ),
        ),
        _rec(request_id="d", q=0.1),
    ]
    m = aggregate(recs, duration_s=1.0)
    assert m["guardrail_capacity_efficiency"] == 1.0


def test_legacy_jsonl_efficiency_reconstructs_from_q():
    """Older records omit risk_required; reconstruct vs global τ=0.50."""
    waste = _rec(
        request_id="waste",
        policy="always_strong",
        q=0.1,
        route="strong",
        decision=ScheduleDecision(
            route="strong",
            reason="strong_available",
            need_strong=True,
            policy_required=True,
            q=0.1,
        ),
    )
    needed = _rec(
        request_id="need",
        policy="always_strong",
        q=0.9,
        route="strong",
        decision=ScheduleDecision(
            route="strong",
            reason="strong_available",
            need_strong=True,
            policy_required=True,
            q=0.9,
        ),
    )
    m = aggregate([waste, needed], duration_s=1.0)
    assert m["guardrail_capacity_efficiency"] == 0.5
