from gasc.markers import ATTACK_MARKERS
from gasc.seeds import assert_bank_clean, make_seeds
from gasc.variants import make_variants


def test_bank_is_500_unique_clean_intents():
    assert_bank_clean()
    seeds = make_seeds(500)
    assert len(seeds) == 500
    assert len({s.intent for s in seeds}) == 500
    assert len({s.seed_id for s in seeds}) == 500
    assert not any(m in s.intent for s in seeds for m in ATTACK_MARKERS)


def test_seed_limit_and_variant_family():
    seeds = make_seeds(3)
    assert [s.seed_id for s in seeds] == ["p1_0001", "p1_0002", "p1_0003"]
    variants = make_variants(seeds[0])
    assert {v.variant for v in variants} == {"S0", "S1", "S2", "S3"}
    s2 = next(v for v in variants if v.variant == "S2")
    assert "bake chocolate chip cookies" not in s2.text.lower()
    assert "credit-card fraud" in s2.text.lower() or "fraud" in s2.text.lower()
