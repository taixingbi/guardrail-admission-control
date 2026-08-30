from gasc.replay_data import q_for, split_q_bands
from gasc.schemas import FrozenPrompt


def test_continuous_q_splits_tenants():
    mid = FrozenPrompt(
        variant_id="m",
        seed_id="m",
        variant="S1",
        text="x",
        target_label="safe",
        metadata={"q": 0.60},
    )
    low = FrozenPrompt(
        variant_id="l",
        seed_id="l",
        variant="S0",
        text="x",
        target_label="safe",
        metadata={"q": 0.10},
    )
    high = FrozenPrompt(
        variant_id="h",
        seed_id="h",
        variant="S2",
        text="x",
        target_label="unsafe",
        metadata={"q": 0.90},
    )
    assert 0.40 <= q_for(mid) < 0.75
    bands = split_q_bands([low, mid, high])
    assert bands["both_direct"] == [low]
    assert bands["tenant_split"] == [mid]
    assert bands["both_strong"] == [high]
