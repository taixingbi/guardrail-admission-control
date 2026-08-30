"""Laptop fallback G_light. Paper G_light is minilm-l12-h384 (Function URL)."""

from __future__ import annotations

import time
from functools import lru_cache
from pathlib import Path
from typing import Literal

from gasc.paths import repo_root

DEFAULT_MODEL_DIR = repo_root() / "models" / "g_light"
DEFAULT_BASE = "microsoft/MiniLM-L12-H384-uncased"


def _device():
    import torch

    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


@lru_cache(maxsize=1)
def load_classifier(model_dir: str | None = None):
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    path = Path(model_dir) if model_dir else DEFAULT_MODEL_DIR
    if not path.exists():
        raise FileNotFoundError(f"local G_light missing at {path}. Run scripts/train_g_light.py")
    tok = AutoTokenizer.from_pretrained(path)
    model = AutoModelForSequenceClassification.from_pretrained(path)
    model.to(_device())
    model.eval()
    return tok, model


def score_local(text: str, *, model_dir: str | None = None, tau: float = 0.50) -> tuple[float, Literal["SAFE", "REVIEW"], float]:
    """Return (q, label, latency_ms). q is P(unsafe/REVIEW)."""
    import torch
    import torch.nn.functional as F

    tok, model = load_classifier(model_dir)
    t0 = time.perf_counter()
    enc = tok(text, truncation=True, max_length=256, return_tensors="pt")
    enc = {k: v.to(model.device) for k, v in enc.items()}
    with torch.no_grad():
        logits = model(**enc).logits[0]
        q = float(F.softmax(logits, dim=-1)[1].item())
    q = min(1.0, max(0.0, q))
    label: Literal["SAFE", "REVIEW"] = "REVIEW" if q >= tau else "SAFE"
    return q, label, (time.perf_counter() - t0) * 1000
