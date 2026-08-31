"""Frozen record schemas. System-model annotations never set `accepted`."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Variant = Literal["S0", "S1", "S2", "S3"]
Route = Literal["direct", "strong", "reject"]
PolicyId = Literal["always_strong", "risk_only", "load_aware", "proposed"]
GtLabel = Literal["safe", "unsafe"]


class Seed(BaseModel):
    schema_version: str = "1.0"
    seed_id: str
    intent: str
    topic: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class PromptVariant(BaseModel):
    schema_version: str = "1.0"
    variant_id: str
    seed_id: str
    variant: Variant
    text: str
    target_label: GtLabel
    payload: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class VariantValidation(BaseModel):
    """accepted = structural checks AND independent judge.

    g_light_q / apply_guardrail_action / maverick notes are annotation only.
    """

    schema_version: str = "1.0"
    variant_id: str
    seed_id: str
    variant: Variant
    payload_present: bool
    wrapper_clean: bool
    family_ok: bool
    judge_label: GtLabel | None = None
    judge_agrees: bool = False
    accepted: bool = False
    g_light_q: float | None = None
    apply_guardrail_action: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_checks(
        cls,
        *,
        variant_id: str,
        seed_id: str,
        variant: Variant,
        payload_present: bool,
        wrapper_clean: bool,
        family_ok: bool,
        judge_label: GtLabel | None,
        judge_agrees: bool,
        g_light_q: float | None = None,
        apply_guardrail_action: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> VariantValidation:
        accepted = bool(payload_present and wrapper_clean and family_ok and judge_agrees)
        return cls(
            variant_id=variant_id,
            seed_id=seed_id,
            variant=variant,
            payload_present=payload_present,
            wrapper_clean=wrapper_clean,
            family_ok=family_ok,
            judge_label=judge_label,
            judge_agrees=judge_agrees,
            accepted=accepted,
            g_light_q=g_light_q,
            apply_guardrail_action=apply_guardrail_action,
            metadata=metadata or {},
        )


class FrozenPrompt(PromptVariant):
    target_label: GtLabel
    accepted: bool = True


class TenantPolicy(BaseModel):
    tenant_id: str
    tau: float
    slo_ms: float
    reserved_share: float = 0.0


class ScheduleDecision(BaseModel):
    route: Route
    reason: str
    need_strong: bool
    policy_required: bool
    q: float
    bypass: bool = False
    # q ≥ τ_risk (tenant τ for Proposed+tenant; else global τ). Independent of
    # always_strong, which sends everything to ApplyGuardrail. None on old records.
    risk_required: bool | None = None


class RunRecord(BaseModel):
    schema_version: str = "1.0"
    request_id: str
    tenant_id: str
    variant_id: str = ""
    variant: Variant | None = None
    gt_label: GtLabel | None = None
    policy: PolicyId
    q: float
    g_light_label: Literal["SAFE", "REVIEW"]
    decision: ScheduleDecision
    route: Route
    strong_wait_s: float = 0.0
    apply_guardrail_action: str | None = None
    admitted_to_llm: bool = False
    latency_ms: float
    slo_ms: float
    policy_compliant: bool
    safe: bool
    slo_ok: bool
    metadata: dict[str, Any] = Field(default_factory=dict)
