from pathlib import Path

from gasc.config import load_config
from gasc.pipeline import run_pipeline


def test_skip_llm_freeze_four_variants(tmp_path: Path) -> None:
    cfg = load_config(Path("configs/smoke.yaml"), skip_llm=True)
    cfg.output_dir = str(tmp_path / "run")
    frozen = run_pipeline(cfg)
    assert len(frozen) == 16
    kinds = {p.variant for p in frozen}
    assert kinds == {"S0", "S1", "S2", "S3"}
    assert all(p.accepted for p in frozen)
