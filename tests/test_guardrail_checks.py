"""A strong check without an ApplyGuardrail verdict must stop the run, not be counted."""

from __future__ import annotations

import asyncio
import random

import pytest

from gasc.clients.bedrock import GuardrailError, apply_guardrail
from gasc.replay_exec import TENANT_A, bedrock_session, make_limiter, run_scheduled
from gasc.report import aggregate
from gasc.schemas import FrozenPrompt

PROMPT = FrozenPrompt.model_construct(variant_id="p_S2", variant="S2", target_label="unsafe", text="x")


class _Client:
    def __init__(self, resp: dict) -> None:
        self.resp = resp

    def apply_guardrail(self, **_kw) -> dict:
        return self.resp


def _run(resp: dict):
    return asyncio.run(
        run_scheduled(
            client=_Client(resp),
            guardrail_id="g",
            version="1",
            limiter=make_limiter(overflow="reject"),
            prompt=PROMPT,
            tenant=TENANT_A,
            policy="proposed",
            q=0.99,
            rng=random.Random(0),
        )
    )


def test_missing_action_becomes_error() -> None:
    out = apply_guardrail(_Client({}), guardrail_id="", guardrail_version="DRAFT", text="x")
    assert out["action"] == "ERROR"


def test_strong_check_without_verdict_raises() -> None:
    with pytest.raises(GuardrailError):
        _run({})


def test_intervention_blocks_and_records_latency() -> None:
    rec = _run({"action": "GUARDRAIL_INTERVENED"})
    assert rec.route == "reject" and rec.decision.reason == "guardrail_block"
    assert not rec.admitted_to_llm
    assert rec.metadata["strong_ms"] >= 0.0


def test_aggregate_rejects_records_without_verdict() -> None:
    rec = _run({"action": "NONE"})
    aggregate([rec], duration_s=1.0)
    stale = rec.model_copy(update={"apply_guardrail_action": None, "metadata": {}})
    with pytest.raises(GuardrailError):
        aggregate([stale], duration_s=1.0)


def test_session_rejects_blank_id_and_draft(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("gasc.replay_exec.load_dotenv", lambda *_a, **_k: None)
    monkeypatch.setenv("GASC_GUARDRAIL_ID", "")
    with pytest.raises(GuardrailError):
        bedrock_session(preflight=False)
    monkeypatch.setenv("GASC_GUARDRAIL_ID", "abc")
    monkeypatch.setenv("GASC_GUARDRAIL_VERSION", "DRAFT")
    monkeypatch.delenv("GASC_ALLOW_DRAFT_GUARDRAIL", raising=False)
    with pytest.raises(GuardrailError):
        bedrock_session(preflight=False)
