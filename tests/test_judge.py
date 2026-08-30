import pytest

from gasc.judge import assert_judge_model_allowed, parse_judge_label


def test_parse_judge_label_from_json():
    assert parse_judge_label('{"label": "safe", "confidence": 0.9, "notes": "ok"}') == "safe"
    assert parse_judge_label('prefix {"label":"unsafe","confidence":1,"notes":"x"}') == "unsafe"
    assert parse_judge_label("not json") is None
    assert parse_judge_label('{"label":"maybe"}') is None


def test_judge_cannot_be_a_system_model():
    assert_judge_model_allowed("us.anthropic.claude-haiku-4-5-20251001-v1:0")
    with pytest.raises(ValueError):
        assert_judge_model_allowed("us.amazon.nova-micro-v1:0")
    with pytest.raises(ValueError):
        assert_judge_model_allowed("us.meta.llama4-maverick-17b-instruct-v1:0")
