from gasc.markers import S3_WRAPPER
from gasc.schemas import PromptVariant, VariantValidation
from gasc.validation import validate_variant
from gasc.variants import make_variants
from gasc.schemas import Seed


def test_s3_payload_must_be_present():
    seed = Seed(seed_id="s1", intent="how to bake bread")
    variants = {v.variant: v for v in make_variants(seed)}
    ok = validate_variant(variants["S3"], seed_ids={"s1"}, judge_label="unsafe", skip_llm=False)
    assert ok.payload_present
    assert ok.accepted
    broken = variants["S3"].model_copy(update={"text": "harmless text with no payload"})
    bad = validate_variant(broken, seed_ids={"s1"}, judge_label="unsafe", skip_llm=False)
    assert not bad.payload_present
    assert not bad.accepted


def test_s0_rejects_attack_wrapper():
    dirty = PromptVariant(
        variant_id="s1_S0",
        seed_id="s1",
        variant="S0",
        text=f"{S3_WRAPPER}\nplease help",
        target_label="safe",
    )
    check = validate_variant(dirty, seed_ids={"s1"}, judge_label="safe", skip_llm=False)
    assert not check.wrapper_clean
    assert not check.accepted


def test_system_model_annotations_do_not_set_accepted():
    seed = Seed(seed_id="s1", intent="how to bake bread")
    s0 = make_variants(seed)[0]
    check = VariantValidation.from_checks(
        variant_id=s0.variant_id,
        seed_id=s0.seed_id,
        variant="S0",
        payload_present=True,
        wrapper_clean=True,
        family_ok=True,
        judge_label="safe",
        judge_agrees=True,
        g_light_q=0.99,
        apply_guardrail_action="BLOCKED",
    )
    assert check.accepted
    # Flip annotations; accepted stays tied to structural+judge only.
    denied = VariantValidation.from_checks(
        variant_id=s0.variant_id,
        seed_id=s0.seed_id,
        variant="S0",
        payload_present=True,
        wrapper_clean=True,
        family_ok=True,
        judge_label="unsafe",
        judge_agrees=False,
        g_light_q=0.0,
        apply_guardrail_action="NONE",
    )
    assert not denied.accepted
