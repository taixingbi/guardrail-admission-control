import json

from gasc.replay_data import FROZEN_PROMPTS, load_live_q, load_replay_prompts, q_for, split_safe_unsafe
from gasc.schemas import FrozenPrompt


def test_freeze_replay_set_is_complete_families():
    if not FROZEN_PROMPTS.exists():
        return
    prompts = load_replay_prompts()
    assert len(prompts) == 1888
    safe, unsafe = split_safe_unsafe(prompts)
    assert len(safe) == 944
    assert len(unsafe) == 944


def test_q_for_prefers_live_e0a(tmp_path):
    scores = tmp_path / "scores.jsonl"
    scores.write_text(json.dumps({"variant_id": "p1_0001_S0", "q": 0.95}) + "\n")
    live = load_live_q(scores)
    safe = FrozenPrompt(
        variant_id="p1_0001_S0",
        seed_id="p1_0001",
        variant="S0",
        text="hi",
        target_label="safe",
    )
    unsafe = FrozenPrompt(
        variant_id="p1_0001_S2",
        seed_id="p1_0001",
        variant="S2",
        text="bad",
        target_label="unsafe",
    )
    assert q_for(safe, live) == 0.95
    assert q_for(unsafe, live) == 1.0
    assert q_for(safe, {}) == 0.0
