from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field


class ModelIds(BaseModel):
    g_light: str = "minilm-l12-h384"
    llm: str = "us.meta.llama4-maverick-17b-instruct-v1:0"
    judge: str = "us.anthropic.claude-haiku-4-5-20251001-v1:0"


class TenantSpec(BaseModel):
    tenant_id: str
    tau: float
    slo_ms: float
    reserved_share: float = 0.0


class AppConfig(BaseModel):
    run_id: str = "smoke"
    output_dir: str = "data/runs/smoke"
    seed_limit: int = 4
    skip_llm: bool = False
    reuse_from: str | None = None
    use_fixture_seeds: bool = True
    variants: list[str] = Field(default_factory=lambda: ["S0", "S1", "S2", "S3"])
    models: ModelIds = Field(default_factory=ModelIds)
    tenants: list[TenantSpec] = Field(
        default_factory=lambda: [
            TenantSpec(tenant_id="A", tau=0.75, slo_ms=600, reserved_share=0.0),
            TenantSpec(tenant_id="B", tau=0.40, slo_ms=800, reserved_share=0.4),
        ]
    )
    default_tau: float = 0.5
    policy: Literal["always_strong", "risk_only", "load_aware", "proposed"] = "proposed"
    fail_closed: bool = True
    bg_rps: float = 0.4
    strong_inflight: int = 2
    queue_max: int = 16
    t_strong_ms: float = 40.0
    t_llm_ms: float = 200.0

    @property
    def out(self) -> Path:
        return Path(self.output_dir)


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, val in overlay.items():
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], val)
        else:
            out[key] = val
    return out


def load_config(path: Path, *, skip_llm: bool | None = None) -> AppConfig:
    raw: dict[str, Any] = {}
    current = path
    chain: list[dict[str, Any]] = []
    while True:
        data = yaml.safe_load(current.read_text()) or {}
        parent = data.pop("extends", None)
        chain.append(data)
        if not parent:
            break
        current = (current.parent / parent).resolve()
    for item in reversed(chain):
        raw = _deep_merge(raw, item)
    cfg = AppConfig.model_validate(raw)
    if skip_llm is not None:
        cfg.skip_llm = skip_llm
    return cfg
