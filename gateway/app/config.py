from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    aws_region: str = "us-east-1"
    g_light_model: str = "minilm-l12-h384"
    llm_model: str = "us.meta.llama4-maverick-17b-instruct-v1:0"
    guardrail_id: str = ""
    guardrail_version: str = "DRAFT"
    policy: str = "proposed"
    fail_closed: bool = True
    rg_rps: float = 0.4
    strong_inflight: int = 2
    queue_max: int = 16
    default_tau: float = 0.5
    skip_llm: bool = False
