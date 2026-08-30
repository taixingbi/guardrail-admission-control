"""Freeze acceptance is structural + independent judge. System models are annotation only."""

from __future__ import annotations

from gasc.markers import ATTACK_MARKERS, S3_WRAPPER
from gasc.schemas import GtLabel, PromptVariant, VariantValidation


def payload_present(variant: PromptVariant) -> bool:
    if variant.variant != "S3":
        return True
    payload = (variant.payload or "").strip()
    if not payload:
        return False
    return payload in variant.text and S3_WRAPPER in variant.text


def wrapper_clean(variant: PromptVariant) -> bool:
    if variant.variant in {"S2", "S3"}:
        return True
    text = variant.text
    return not any(marker in text for marker in ATTACK_MARKERS)


def family_ok(variant: PromptVariant, seed_ids: set[str]) -> bool:
    return variant.seed_id in seed_ids and variant.variant_id.startswith(variant.seed_id)


def expected_label(variant: PromptVariant) -> GtLabel:
    return variant.target_label


def judge_agrees(variant: PromptVariant, judge_label: GtLabel | None, *, skip_llm: bool) -> bool:
    if skip_llm:
        return True
    if judge_label is None:
        return False
    return judge_label == expected_label(variant)


def validate_variant(
    variant: PromptVariant,
    *,
    seed_ids: set[str],
    judge_label: GtLabel | None,
    skip_llm: bool,
    g_light_q: float | None = None,
    apply_guardrail_action: str | None = None,
) -> VariantValidation:
    return VariantValidation.from_checks(
        variant_id=variant.variant_id,
        seed_id=variant.seed_id,
        variant=variant.variant,
        payload_present=payload_present(variant),
        wrapper_clean=wrapper_clean(variant),
        family_ok=family_ok(variant, seed_ids),
        judge_label=judge_label if not skip_llm else expected_label(variant),
        judge_agrees=judge_agrees(variant, judge_label, skip_llm=skip_llm),
        g_light_q=g_light_q,
        apply_guardrail_action=apply_guardrail_action,
    )
