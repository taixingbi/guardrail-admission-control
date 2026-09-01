#!/usr/bin/env python3
"""Rebuild replay metrics.json/md from existing jsonl. No AWS.

Fixes: efficiency (risk-required occupancy), E2/E6 checked = strong slot,
user-facing Bg labels. Does not rerun experiments.
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gasc.io import load_jsonl  # noqa: E402
from gasc.report import aggregate, applied_strong, fmt_stat, pool_by  # noqa: E402
from gasc.replay_data import results_dir  # noqa: E402
from gasc.schemas import RunRecord  # noqa: E402

from run_e2 import DURATION_S as E2_DUR  # noqa: E402
from run_e2 import _cell_metrics, _pool_reps  # noqa: E402
from run_e6 import _window  # noqa: E402


def _e1() -> None:
    out = results_dir("e1")
    pat = re.compile(r"^r(\d+)_(always_strong|risk_only|load_aware|proposed)_(\d+\.\d+)\.jsonl$")
    cells = []
    for f in sorted(out.glob("r*.jsonl")):
        m = pat.match(f.name)
        if not m:
            continue
        rep, policy, frac = int(m.group(1)), m.group(2), float(m.group(3))
        recs = load_jsonl(f, RunRecord)
        metrics = aggregate(recs, duration_s=40.0)
        metrics.update(
            {
                "policy": policy,
                "strong_demand_frac_of_bg": frac,
                "rep": rep,
                "n": len(recs),
            }
        )
        cells.append(metrics)
    summary = {
        "bg": 0.4,
        "r_gateway": 3.01,
        "duration_s": 40.0,
        "reps": 5,
        "q_source": "frozen_g_light",
        "cells": cells,
        "pooled": pool_by(
            cells,
            ("policy", "strong_demand_frac_of_bg"),
            ("safe_slo_goodput", "unsafe_admission_rate", "reject_rate", "guardrail_capacity_efficiency"),
        ),
    }
    order = ("always_strong", "risk_only", "load_aware", "proposed")
    summary["pooled"].sort(
        key=lambda m: (order.index(m["policy"]), m["strong_demand_frac_of_bg"])
    )
    (out / "metrics.json").write_text(json.dumps(summary, indent=2))
    lines = [
        "# E1 static safety-load (frozen minilm-l12-h384 q, 5 reps)",
        "",
        "R_gateway=3.01 rps, Bg=0.4 rps (gateway safety budget, not provider capacity), "
        "40s/cell × 5 reps. q=frozen_g_light. Live ApplyGuardrail, no Maverick.",
        "Paper cells are median [p25, p75]. Do not retune τ.",
        "UAR is MiniLM false negatives (q below τ, so scheduler never requires strong), not fail-open.",
        "Efficiency = risk-required strong occupancy / all strong occupancy (Always-Strong waste is q < τ).",
        "Proposed guarantees policy compliance conditional on q, not GT safety.",
        "",
        "| policy | demand | G_safe | UAR | reject | efficiency |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for m in summary["pooled"]:
        lines.append(
            f"| {m['policy']} | {m['strong_demand_frac_of_bg']:.2f} Bg | "
            f"{fmt_stat(m['safe_slo_goodput'])} | {fmt_stat(m['unsafe_admission_rate'])} | "
            f"{fmt_stat(m['reject_rate'])} | {fmt_stat(m['guardrail_capacity_efficiency'], digits=2)} |"
        )
    (out / "metrics.md").write_text("\n".join(lines) + "\n")
    print(f"refreshed {out}")


def _e2() -> None:
    out = results_dir("e2")
    pat = re.compile(
        r"^r(\d+)_(always_strong|risk_only|load_aware|proposed)_(\d+\.\d+)_(\d+\.\d+)\.jsonl$"
    )
    cells = []
    for f in sorted(out.glob("r*.jsonl")):
        m = pat.match(f.name)
        if not m:
            continue
        rep, policy, pa, pb = int(m.group(1)), m.group(2), float(m.group(3)), float(m.group(4))
        recs = load_jsonl(f, RunRecord)
        cells.append(_cell_metrics(recs, policy=policy, mix=(pa, pb), duration_s=E2_DUR, rep=rep))
    summary = json.loads((out / "metrics.json").read_text())
    summary["cells"] = cells
    summary["pooled"] = _pool_reps(cells)
    (out / "metrics.json").write_text(json.dumps(summary, indent=2))
    lines = [
        "# E2 multi-tenant contention (frozen minilm-l12-h384 q, 5 reps)",
        "",
        "Gateway safety budget Bg=0.4 rps (not ApplyGuardrail provider capacity). R_gateway=3.01, 120s/cell × 5 reps.",
        "q = frozen Function URL MiniLM. Tenant-split band is 0.40 ≤ q < 0.75 (A direct, B strong).",
        "Isolation = checked vs starved among B required-strong. Paper cells are median [p25, p75].",
        "MiniLM is a screener; ApplyGuardrail is the authority. Do not retune τ on XSTest/WildGuardTest.",
        "Proposed guarantees policy compliance conditional on q, not GT safety.",
        "",
        "## Tenant-split routing (pooled)",
        "",
        "| policy | A:B | split_A | A direct | split_B | B need_strong | B checked |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for m in summary["pooled"]:
        lines.append(
            f"| {m['policy']} | {m['mix_a']:.0%}:{m['mix_b']:.0%} | "
            f"{m['n_split_a']} | {m['split_a_direct']} | {m['n_split_b']} | "
            f"{m['split_b_need_strong']} | {m['split_b_checked']} |"
        )
    lines += [
        "",
        "## Isolation (pooled B required-strong)",
        "",
        "| policy | A:B | G_safe | G_safe_B | need_B | checked_B | starved_B | coverage | n_B_unsafe | UAR_B |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for m in summary["pooled"]:
        need = m["n_need_b"] or 0
        cov = (m["n_checked_b"] / need) if need else 0.0
        lines.append(
            f"| {m['policy']} | {m['mix_a']:.0%}:{m['mix_b']:.0%} | "
            f"{fmt_stat(m['safe_slo_goodput'])} | {fmt_stat(m['g_safe_b'])} | "
            f"{m['n_need_b']} | {m['n_checked_b']} | {m['n_starved_b']} | "
            f"{cov:.1%} | {m['n_b_unsafe']} | {fmt_stat(m['uar_b'])} |"
        )
    lines += [
        "",
        "Coverage = checked / need among B required-strong. UAR_B includes MiniLM false negatives",
        "(GT-unsafe with q below τ_B); that is classifier error, not fail-open bypass.",
    ]
    (out / "metrics.md").write_text("\n".join(lines) + "\n")
    print(f"refreshed {out}")


def _patch_phase_checked(out: Path, cells: list) -> None:
    for cell in cells:
        if cell["overall"].get("rep", 0) != 0:
            continue
        policy = cell["overall"]["policy"]
        path = out / f"r0_{policy}.jsonl"
        if not path.exists():
            continue
        recs = load_jsonl(path, RunRecord)
        by_phase: dict[str, list] = defaultdict(list)
        for r in recs:
            by_phase[str((r.metadata or {}).get("phase") or "")].append(r)
        for m in cell.get("phases") or []:
            label = str(m.get("phase") or "")
            chunk = []
            for key, rows in by_phase.items():
                if key.startswith(label) or label in key:
                    chunk.extend(rows)
            if not chunk:
                continue
            need = [r for r in chunk if r.decision.need_strong]
            n_chk = sum(1 for r in need if applied_strong(r))
            m["n_checked"] = n_chk
            m["n_starved"] = len(need) - n_chk
            m["checked_rate"] = (n_chk / len(need)) if need else None


def _alias_frac(row: dict, *keys: str):
    for k in keys:
        if row.get(k) is not None:
            return row[k]
    return None


def _e3() -> None:
    out = results_dir("e3")
    summary = json.loads((out / "metrics.json").read_text())
    summary["bg"] = 0.4
    for ph in summary.get("phases") or []:
        frac = _alias_frac(ph, "strong_frac_of_bg", "strong_frac_of_rg")
        if frac is not None:
            ph["strong_frac_of_bg"] = frac
    for cell in summary.get("cells") or []:
        for m in cell.get("phases") or []:
            frac = _alias_frac(m, "strong_frac_of_bg", "strong_frac_of_rg")
            if frac is not None:
                m["strong_frac_of_bg"] = frac
    _patch_phase_checked(out, summary.get("cells") or [])
    (out / "metrics.json").write_text(json.dumps(summary, indent=2))
    lines = [
        "# E3 dynamic safety load (frozen minilm-l12-h384 q, 5 reps)",
        "",
        "R_gateway=3.01 rps, Bg=0.4 rps, 480s/policy × 5 reps. Mix 0.5→0.9→1.5→0.6 Bg.",
        f"Tenant A only. q={summary.get('q_source')}. Live ApplyGuardrail, no Maverick.",
        "Paper overall cells are median [p25, p75]. Do not retune τ.",
        "UAR is MiniLM false negatives, not fail-open. Dynamic strong-guard demand changes goodput at fixed gateway config.",
        "",
        "## Overall (median [IQR])",
        "",
        "| policy | G_safe | UAR | reject |",
        "| --- | --- | --- | --- |",
    ]
    for m in summary["pooled"]:
        lines.append(
            f"| {m['policy']} | {fmt_stat(m['safe_slo_goodput'])} | "
            f"{fmt_stat(m['unsafe_admission_rate'])} | {fmt_stat(m['reject_rate'])} |"
        )
    lines += [
        "",
        "## Per phase (rep 0 shown in jsonl; pooled overall is the paper cell)",
        "",
        "| policy | phase | demand | G_safe | UAR | reject | checked | starved |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for cell in summary["cells"]:
        if cell["overall"].get("rep", 0) != 0:
            continue
        for m in cell["phases"]:
            chk = m["checked_rate"]
            chk_s = "—" if chk is None else f"{chk:.2f}"
            frac = _alias_frac(m, "strong_frac_of_bg", "strong_frac_of_rg") or 0.0
            lines.append(
                f"| {m['policy']} | {m['phase']} | {frac:.1f} Bg | "
                f"{m['safe_slo_goodput']:.3f} | {m['unsafe_admission_rate']:.3f} | "
                f"{m['reject_rate']:.3f} | {chk_s} | {m['n_starved']} |"
            )
    (out / "metrics.md").write_text("\n".join(lines) + "\n")
    print(f"refreshed {out}")


def _e4() -> None:
    out = results_dir("e4")
    summary = json.loads((out / "metrics.json").read_text())
    summary["bg"] = 0.4
    for ph in summary.get("phases") or []:
        frac = _alias_frac(ph, "offered_strong_frac_of_bg", "offered_strong_frac_of_rg")
        if frac is not None:
            ph["offered_strong_frac_of_bg"] = frac
    for cell in summary.get("cells") or []:
        for m in cell.get("phases") or []:
            frac = _alias_frac(m, "offered_strong_frac_of_bg", "offered_strong_frac_of_rg")
            if frac is not None:
                m["offered_strong_frac_of_bg"] = frac
    _patch_phase_checked(out, summary.get("cells") or [])
    (out / "metrics.json").write_text(json.dumps(summary, indent=2))
    lines = [
        "# E4 safety-capacity exhaustion (frozen minilm-l12-h384 q, 5 reps)",
        "",
        "R_gateway=3.01 rps (constant), Bg=0.4 rps, 420s/policy × 5 reps.",
        "Suspicious/adversarial mix 5% → 50% → 5%. Offered strong demand ≈ 0.38 → 3.76 → 0.38 Bg.",
        f"Tenant A only. q={summary.get('q_source')}. Live ApplyGuardrail, no Maverick.",
        "Phenomenon: safety-resource exhaustion at constant gateway RPS. Do not use E4 to claim Proposed dominates.",
        "Paper overall cells are median [p25, p75]. Do not retune τ.",
        "",
        "## Overall (median [IQR])",
        "",
        "| policy | G_safe | UAR | reject |",
        "| --- | --- | --- | --- |",
    ]
    for m in summary["pooled"]:
        lines.append(
            f"| {m['policy']} | {fmt_stat(m['safe_slo_goodput'])} | "
            f"{fmt_stat(m['unsafe_admission_rate'])} | {fmt_stat(m['reject_rate'])} |"
        )
    lines += [
        "",
        "## Per phase (rep 0)",
        "",
        "| policy | phase | sus | offered | G_safe | UAR | reject | checked | starved |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for cell in summary["cells"]:
        if cell["overall"].get("rep", 0) != 0:
            continue
        for m in cell["phases"]:
            chk = m["checked_rate"]
            chk_s = "—" if chk is None else f"{chk:.2f}"
            offered = _alias_frac(m, "offered_strong_frac_of_bg", "offered_strong_frac_of_rg") or 0.0
            lines.append(
                f"| {m['policy']} | {m['phase']} | {m['suspicious_frac']:.0%} | "
                f"{offered:.2f} Bg | "
                f"{m['safe_slo_goodput']:.3f} | {m['unsafe_admission_rate']:.3f} | "
                f"{m['reject_rate']:.3f} | {chk_s} | {m['n_starved']} |"
            )
    (out / "metrics.md").write_text("\n".join(lines) + "\n")
    print(f"refreshed {out}")


def _e5() -> None:
    out = results_dir("e5")
    summary = json.loads((out / "metrics.json").read_text())
    summary["bg"] = 0.4
    for cell in summary.get("cells") or []:
        frac = _alias_frac(cell, "strong_demand_frac_of_bg", "strong_demand_frac_of_rg")
        if frac is not None:
            cell["strong_demand_frac_of_bg"] = frac
    pooled = pool_by(
        summary["cells"],
        ("mode", "strong_demand_frac_of_bg"),
        ("safe_slo_goodput", "unsafe_admission_rate", "reject_rate", "bypass_rate_need"),
    )
    pooled.sort(key=lambda m: (0 if "closed" in m["mode"] else 1, m["strong_demand_frac_of_bg"]))
    summary["pooled"] = pooled
    (out / "metrics.json").write_text(json.dumps(summary, indent=2))
    lines = [
        "# E5 fail-open vs fail-closed (frozen minilm-l12-h384 q, 5 reps)",
        "",
        f"Proposed only. R_gateway=3.01, Bg=0.4, 60s/cell × {summary['reps']} reps. q={summary.get('q_source')}.",
        "Fail-open disables deadline so exhaustion can bypass. Fail-closed keeps frozen B4.",
        "Paper cells are median [p25, p75]. MiniLM is a screener, not the authority. Do not retune τ.",
        "Fail-open raises UAR without raising Safe Goodput. Residual fail-closed UAR is MiniLM FN, not bypass.",
        "",
        "| mode | demand | G_safe | UAR | reject | bypass/need |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for m in pooled:
        lines.append(
            f"| {m['mode']} | {m['strong_demand_frac_of_bg']:.1f} Bg | "
            f"{fmt_stat(m['safe_slo_goodput'])} | {fmt_stat(m['unsafe_admission_rate'])} | "
            f"{fmt_stat(m['reject_rate'])} | {fmt_stat(m['bypass_rate_need'], digits=2)} |"
        )
    (out / "metrics.md").write_text("\n".join(lines) + "\n")
    print(f"refreshed {out}")


def _e6() -> None:
    out = results_dir("e6")
    pat = re.compile(r"^r(\d+)_(full|no_tenant|no_deadline|no_early_reject)\.jsonl$")
    cells = []
    flags = {
        "full": (True, True, True, "reject"),
        "no_tenant": (False, True, True, "reject"),
        "no_deadline": (True, False, True, "reject"),
        "no_early_reject": (True, True, False, "queue"),
    }
    for f in sorted(out.glob("r*.jsonl")):
        m = pat.match(f.name)
        if not m:
            continue
        rep, variant = int(m.group(1)), m.group(2)
        recs = load_jsonl(f, RunRecord)
        metrics = _window(recs, 120.0)
        use_tenant, use_deadline, use_early_reject, overflow = flags[variant]
        metrics.update(
            {
                "ablation": variant,
                "use_tenant": use_tenant,
                "use_deadline": use_deadline,
                "use_early_reject": use_early_reject,
                "overflow_mode": overflow,
                "n": len(recs),
                "rep": rep,
                "n_strong_slot": sum(1 for r in recs if applied_strong(r)),
            }
        )
        cells.append(metrics)
    summary = {
        "bg": 0.4,
        "r_gateway": 3.01,
        "reps": 5,
        "reuse_trace": "e3_proposed_240_360s_1.5Bg",
        "q_source": "frozen_g_light",
        "cells": cells,
        "pooled": pool_by(
            cells,
            ("ablation",),
            ("safe_slo_goodput", "unsafe_admission_rate", "reject_rate", "n_checked", "latency_p95_ms"),
        ),
    }
    order = ("full", "no_tenant", "no_deadline", "no_early_reject")
    summary["pooled"].sort(key=lambda m: order.index(m["ablation"]))
    (out / "metrics.json").write_text(json.dumps(summary, indent=2))
    lines = [
        "# E6 ablations (frozen minilm-l12-h384 q, 5 reps, E3 overload 1.5 Bg)",
        "",
        f"Same arrival process as E3 proposed overload. Fail-closed. Tenant A only. q={summary.get('q_source')}.",
        "Paper cells are median [p25, p75]. Full vs −NoEarlyReject is the systems headline. Do not retune τ.",
        "−NoTenant ≈ Full because this cell is Tenant A only (not because q is bimodal).",
        "",
        "| ablation | G_safe | UAR | reject | checked | P95 ms |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for m in summary["pooled"]:
        lines.append(
            f"| {m['ablation']} | {fmt_stat(m['safe_slo_goodput'])} | "
            f"{fmt_stat(m['unsafe_admission_rate'])} | {fmt_stat(m['reject_rate'])} | "
            f"{fmt_stat(m['n_checked'], digits=1)} | {fmt_stat(m['latency_p95_ms'], digits=0)} |"
        )
    (out / "metrics.md").write_text("\n".join(lines) + "\n")
    print(f"refreshed {out}")


def _e2e() -> None:
    out = results_dir("e2e")
    summary = json.loads((out / "metrics.json").read_text())
    summary["bg"] = 0.4
    (out / "metrics.json").write_text(json.dumps(summary, indent=2))
    lines = [
        "# E2e sanity (Proposed, 1.0 Bg, 40s)",
        "",
        "Tenant A SLO 600 ms unchanged. Maverick C*=2. t_llm_ms=250 (E0c TTFT P50).",
        "Does not retune τ or Bg. E1–E6 stay Maverick-off.",
        "replay_q uses frozen Function URL q (paper-comparable path). live_path scores every request",
        "via Function URL MiniLM (E0a P50 ~524 ms) and is not the 600 ms SLO architecture number.",
        "",
        "| cell | G_safe@600 | G_safe@800 | UAR | e2e P50 | e2e P95 | TTFT P95 | admitted SLO |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]

    def fmt(x):
        if x is None:
            return "—"
        if isinstance(x, float) and x > 2:
            return f"{x:.0f}"
        return f"{x:.3f}"

    for m in summary["cells"]:
        slo = m["slo_ok_admitted"]
        slo_s = "—" if slo is None else f"{slo:.2f}"
        lines.append(
            f"| {m['cell']} | {m['safe_slo_goodput']:.3f} | {m['slo_800_goodput']:.3f} | "
            f"{m['unsafe_admission_rate']:.3f} | {fmt(m['e2e_p50_ms'])} | {fmt(m['e2e_p95_ms'])} | "
            f"{fmt(m['ttft_p95_ms'])} | {slo_s} |"
        )
    (out / "metrics.md").write_text("\n".join(lines) + "\n")
    print(f"refreshed {out}")


def _index() -> None:
    out = Path(__file__).resolve().parents[1] / "results"
    text = r"""# E0–E6 Function URL MiniLM campaign (paper)

Paper write-up: [summary.md](summary.md).

All headline cells below replay the **same frozen** `minilm-l12-h384` Function URL \(q\).
Do not cite Nova Micro, laptop MiniLM, or old oracle tables.

Proposed **does not guarantee GT safety**. It guarantees policy compliance **conditional on** \(q(x)\):
it never bypasses a request the policy marks as requiring strong inspection.

| exp | status | headline |
| --- | --- | --- |
| E0a | **done** Function URL MiniLM | freeze AUROC 0.986, P50/P95 524/619 ms, tenant-split 220 |
| E1 | frozen MiniLM q, 5 reps | method locked; UAR is MiniLM FN (not fail-open); Always-Strong efficiency < 1 |
| E2 | frozen MiniLM q, 5 reps | tenant isolation: Proposed 65.5%/40.3% B coverage vs load-aware 29.9%/27.1% at 90:10/70:30 |
| E3 | frozen MiniLM q, 5 reps | G_safe moves with strong-mix at fixed gateway RPS; phenomenon + MiniLM UAR |
| E4 | frozen MiniLM q, 5 reps | exhaustion at constant RPS; **not** a Proposed-dominance result |
| E5 | frozen MiniLM q, 5 reps | fail-open raises UAR without raising G_safe (use MiniLM numbers, not Nova UAR=0) |
| E6 | frozen MiniLM q, 5 reps | −NoEarlyReject adds strong work and blows P95; −NoTenant ≈ Full because Tenant A only |
| e2e | replay_q vs live_path | replay_q P50 ~584 ms is paper-comparable; live_path 6.3s/21s is Function URL on the hot path |

Bg = gateway safety budget 0.4 rps, not ApplyGuardrail provider capacity (~71 rps). No E7/E8. Write the paper.
"""
    (out / "metrics.md").write_text(text)
    print(f"refreshed {out / 'metrics.md'}")


def main() -> int:
    _e1()
    _e2()
    _e3()
    _e4()
    _e5()
    _e6()
    _e2e()
    _index()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
