from __future__ import annotations

import json
from pathlib import Path

from gasc.config import AppConfig
from gasc.eval_binary import percentile
from gasc.schemas import RunRecord

_TENANT_TAU = {"A": 0.75, "B": 0.40}
_GLOBAL_TAU = 0.5


def risk_required_of(r: RunRecord) -> bool:
    """q ≥ τ_risk. Stored on new decisions; reconstructed for older jsonl."""
    stored = r.decision.risk_required
    if stored is not None:
        return bool(stored)
    tau = _TENANT_TAU.get(r.tenant_id, _GLOBAL_TAU) if r.policy == "proposed" else _GLOBAL_TAU
    return r.q >= tau


def applied_strong(r: RunRecord) -> bool:
    """Request occupied ApplyGuardrail (or an equivalent strong slot).

    Formal jsonl often stores apply_guardrail_action=None even when a strong
    slot was used; route==strong / guardrail_block still count as occupancy.
    """
    action = r.apply_guardrail_action or (r.metadata or {}).get("apply_guardrail_action")
    if action not in (None, "ERROR"):
        return True
    if r.decision.reason == "guardrail_block":
        return True
    return r.route == "strong"


def occupancy(records: list[RunRecord]) -> dict:
    """Need-strong vs actually occupied ApplyGuardrail slots."""
    need = [r for r in records if r.decision.need_strong]
    n_checked = sum(1 for r in need if applied_strong(r))
    return {
        "n_need": len(need),
        "n_checked": n_checked,
        "n_starved": len(need) - n_checked,
        "checked_rate": (n_checked / len(need)) if need else None,
        "n_strong_slot": sum(1 for r in records if applied_strong(r)),
    }


def uar_decompose(records: list[RunRecord]) -> dict:
    """Split admitted GT-unsafe into light miss / strong miss / scheduler bypass.

    UAR_light:  q below risk τ, direct, admitted (MiniLM FN / below-threshold).
    UAR_strong: ApplyGuardrail occupied, did not block, admitted (G_strong miss).
    UAR_bypass: policy required strong, scheduler bypassed, admitted.
    """
    unsafe = [r for r in records if r.gt_label == "unsafe"]
    n = len(unsafe)

    def _is_light(r: RunRecord) -> bool:
        return r.admitted_to_llm and r.route == "direct" and not r.decision.bypass and not risk_required_of(r)

    def _is_strong(r: RunRecord) -> bool:
        return r.admitted_to_llm and applied_strong(r) and not r.decision.bypass

    def _is_bypass(r: RunRecord) -> bool:
        if not r.admitted_to_llm:
            return False
        if r.decision.bypass:
            return True
        return r.route == "direct" and risk_required_of(r) and not applied_strong(r)

    n_light = sum(1 for r in unsafe if _is_light(r))
    n_strong = sum(1 for r in unsafe if _is_strong(r))
    n_bypass = sum(1 for r in unsafe if _is_bypass(r))
    n_admitted = sum(1 for r in unsafe if r.admitted_to_llm)
    return {
        "n_unsafe": n,
        "n_unsafe_admitted": n_admitted,
        "uar_light": (n_light / n) if n else 0.0,
        "uar_strong": (n_strong / n) if n else 0.0,
        "uar_bypass": (n_bypass / n) if n else 0.0,
        "n_uar_light": n_light,
        "n_uar_strong": n_strong,
        "n_uar_bypass": n_bypass,
    }


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
    strong = [r for r in records if applied_strong(r)]
    required_strong = [r for r in strong if risk_required_of(r)]
    parts = uar_decompose(records)
    occ = occupancy(records)
    return {
        "n": len(records),
        "safe_slo_goodput": n_safe_slo / duration_s,
        "unsafe_admission_rate": (unsafe_admitted / len(unsafe)) if unsafe else 0.0,
        "uar_light": parts["uar_light"],
        "uar_strong": parts["uar_strong"],
        "uar_bypass": parts["uar_bypass"],
        "critical_tenant_slo_attainment": (b_slo / len(tenant_b)) if tenant_b else None,
        "guardrail_capacity_efficiency": (len(required_strong) / len(strong)) if strong else None,
        "reject_rate": sum(1 for r in records if r.route == "reject") / max(len(records), 1),
        "bypass_count": sum(1 for r in records if r.decision.bypass),
        **occ,
        **{k: parts[k] for k in ("n_unsafe", "n_unsafe_admitted", "n_uar_light", "n_uar_strong", "n_uar_bypass")},
    }


def stat_pack(vals: list[float]) -> dict:
    """Paper table cell: median [p25, p75] plus mean. Empty → nulls."""
    xs = [float(v) for v in vals if v is not None]
    if not xs:
        return {"n": 0, "mean": None, "median": None, "p25": None, "p75": None}
    return {
        "n": len(xs),
        "mean": sum(xs) / len(xs),
        "median": percentile(xs, 50),
        "p25": percentile(xs, 25),
        "p75": percentile(xs, 75),
    }


def fmt_stat(pack: dict | None, *, digits: int = 3) -> str:
    if not pack or pack.get("median") is None:
        return "—"
    d = digits
    return f"{pack['median']:.{d}f} [{pack['p25']:.{d}f}, {pack['p75']:.{d}f}]"


def pool_by(rows: list[dict], group_keys: tuple[str, ...], metric_keys: tuple[str, ...]) -> list[dict]:
    from collections import defaultdict

    groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        groups[tuple(row[k] for k in group_keys)].append(row)
    out = []
    for key, chunk in groups.items():
        item = {k: v for k, v in zip(group_keys, key)}
        item["reps"] = len(chunk)
        for mk in metric_keys:
            item[mk] = stat_pack([r.get(mk) for r in chunk])
        out.append(item)
    return out


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
