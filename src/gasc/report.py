from __future__ import annotations

import json
from pathlib import Path

from gasc.config import AppConfig
from gasc.schemas import RunRecord


def aggregate(records: list[RunRecord], *, duration_s: float) -> dict:
    if duration_s <= 0:
        duration_s = 1.0
    n_safe_slo = sum(
        1
        for r in records
        if r.policy_compliant and r.safe and r.slo_ok and r.admitted_to_llm
    )
    unsafe = [r for r in records if r.gt_label == "unsafe"]
    unsafe_admitted = sum(1 for r in unsafe if r.admitted_to_llm)
    tenant_b = [r for r in records if r.tenant_id == "B" and r.route != "reject"]
    b_slo = sum(1 for r in tenant_b if r.slo_ok)
    strong = [r for r in records if r.route == "strong"]
    required_strong = [r for r in strong if r.decision.policy_required]
    return {
        "n": len(records),
        "safe_slo_goodput": n_safe_slo / duration_s,
        "unsafe_admission_rate": (unsafe_admitted / len(unsafe)) if unsafe else 0.0,
        "critical_tenant_slo_attainment": (b_slo / len(tenant_b)) if tenant_b else None,
        "guardrail_capacity_efficiency": (len(required_strong) / len(strong)) if strong else None,
        "reject_rate": sum(1 for r in records if r.route == "reject") / max(len(records), 1),
        "bypass_count": sum(1 for r in records if r.decision.bypass),
    }


def write_metrics(cfg: AppConfig, n_frozen: int | None = None) -> Path:
    out = cfg.out / "6_metrics"
    out.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": cfg.run_id,
        "n_frozen": n_frozen,
        "skip_llm": cfg.skip_llm,
        "policy": cfg.policy,
        "metrics": None,
    }
    records_path = cfg.out / "5_runs" / "run_records.jsonl"
    if records_path.exists():
        from gasc.io import load_jsonl

        recs = load_jsonl(records_path, RunRecord)
        payload["metrics"] = aggregate(recs, duration_s=1.0)
    (out / "metrics.json").write_text(json.dumps(payload, indent=2))
    (out / "metrics.md").write_text(
        f"# {cfg.run_id}\n\n"
        f"Frozen prompts: {n_frozen}\n\n"
        f"Primary metrics: Safe SLO-Goodput, Unsafe Admission Rate, "
        f"Critical-tenant SLO attainment, Guardrail capacity efficiency.\n"
    )
    return out / "metrics.json"
