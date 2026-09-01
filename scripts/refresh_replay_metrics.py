#!/usr/bin/env python3
"""Rebuild replay metrics.json/md from existing jsonl. No AWS.

Recomputes occupancy via applied_strong (route==strong / guardrail_block)
and UAR_light / UAR_strong / UAR_bypass. Does not rerun Bedrock.
"""

from __future__ import annotations

import json
import re
import sys
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
from run_e3 import DURATION_S as E3_DUR  # noqa: E402
from run_e3 import PHASES as E3_PHASES  # noqa: E402
from run_e4 import DURATION_S as E4_DUR  # noqa: E402
from run_e4 import PHASES as E4_PHASES  # noqa: E402
from run_e4 import _offered_bg  # noqa: E402
from run_e5 import DURATION_S as E5_DUR  # noqa: E402
from run_e5 import _extra as e5_extra  # noqa: E402
from run_e6 import _window  # noqa: E402

POLICY_RE = r"always_strong|risk_only|load_aware|proposed"
POLICY_ORDER = ("always_strong", "risk_only", "load_aware", "proposed")


def _t_s(r: RunRecord) -> float:
    return float((r.metadata or {}).get("t_s") or -1.0)


def _phase_rows(recs: list[RunRecord], phases: tuple, *, policy: str, rep: int, extra_fn) -> list[dict]:
    rows = []
    prev = 0.0
    for until, val in phases:
        chunk = [r for r in recs if prev <= _t_s(r) < until]
        row = aggregate(chunk, duration_s=until - prev)
        row.update({"policy": policy, "phase": f"{prev:.0f}-{until:.0f}s", "n": len(chunk), "rep": rep})
        extra_fn(row, val)
        rows.append(row)
        prev = until
    return rows


def _e1() -> None:
    out = results_dir("e1")
    pat = re.compile(rf"^r(\d+)_({POLICY_RE})_(\d+\.\d+)\.jsonl$")
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
            (
                "safe_slo_goodput",
                "unsafe_admission_rate",
                "uar_light",
                "uar_strong",
                "uar_bypass",
                "reject_rate",
                "guardrail_capacity_efficiency",
            ),
        ),
    }
    summary["pooled"].sort(
        key=lambda m: (POLICY_ORDER.index(m["policy"]), m["strong_demand_frac_of_bg"])
    )
    (out / "metrics.json").write_text(json.dumps(summary, indent=2))
    lines = [
        "# E1 static safety-load (frozen minilm-l12-h384 q, 5 reps)",
        "",
        "R_gateway=3.01 rps, Bg=0.4 rps (gateway safety budget, not provider capacity), "
        "40s/cell × 5 reps. q=frozen_g_light. Live ApplyGuardrail, no Maverick.",
        "Latency is **safety-stage** (scheduler + ApplyGuardrail), not user E2E (no MiniLM, no Maverick on this path).",
        "Paper cells are median [p25, p75]. Do not retune τ.",
        "UAR = UAR_light + UAR_strong + UAR_bypass. Always-Strong UAR is G_strong miss, not MiniLM FN.",
        "Efficiency = risk-required strong occupancy / all strong occupancy (Always-Strong waste is q < τ).",
        "Claim: uniform strong checking wastes a bounded safety budget. Not Proposed-dominance vs risk-only/load-aware.",
        "",
        "| policy | demand | G_safe | UAR | light | strong | bypass | reject | efficiency |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for m in summary["pooled"]:
        lines.append(
            f"| {m['policy']} | {m['strong_demand_frac_of_bg']:.2f} Bg | "
            f"{fmt_stat(m['safe_slo_goodput'])} | {fmt_stat(m['unsafe_admission_rate'])} | "
            f"{fmt_stat(m['uar_light'])} | {fmt_stat(m['uar_strong'])} | {fmt_stat(m['uar_bypass'])} | "
            f"{fmt_stat(m['reject_rate'])} | {fmt_stat(m['guardrail_capacity_efficiency'], digits=2)} |"
        )
    (out / "metrics.md").write_text("\n".join(lines) + "\n")
    print(f"refreshed {out}")


def _e2() -> None:
    out = results_dir("e2")
    pat = re.compile(rf"^r(\d+)_({POLICY_RE})_(\d+\.\d+)_(\d+\.\d+)\.jsonl$")
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
        "MiniLM is an inexpensive risk estimator, not a low-latency guardrail. Do not retune τ.",
        "Novelty is tenant isolation / B strong-check coverage, not better UAR_B.",
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
        "Coverage = checked / need among B required-strong. Headline is isolation, not UAR_B.",
        "UAR_B mixes MiniLM FN (q below τ_B) and G_strong misses; it is not fail-open bypass.",
    ]
    (out / "metrics.md").write_text("\n".join(lines) + "\n")
    print(f"refreshed {out}")


def _e3() -> None:
    out = results_dir("e3")
    pat = re.compile(rf"^r(\d+)_({POLICY_RE})\.jsonl$")
    cells = []
    for f in sorted(out.glob("r*.jsonl")):
        m = pat.match(f.name)
        if not m:
            continue
        rep, policy = int(m.group(1)), m.group(2)
        recs = load_jsonl(f, RunRecord)
        overall = aggregate(recs, duration_s=E3_DUR)
        overall.update({"policy": policy, "rep": rep, "n": len(recs)})
        cells.append(
            {
                "overall": overall,
                "phases": _phase_rows(
                    recs,
                    E3_PHASES,
                    policy=policy,
                    rep=rep,
                    extra_fn=lambda row, frac: row.update({"strong_frac_of_bg": frac}),
                ),
            }
        )
    pooled = pool_by(
        [c["overall"] for c in cells],
        ("policy",),
        (
            "safe_slo_goodput",
            "unsafe_admission_rate",
            "uar_light",
            "uar_strong",
            "uar_bypass",
            "reject_rate",
        ),
    )
    pooled.sort(key=lambda m: POLICY_ORDER.index(m["policy"]))
    pooled_phases = pool_by(
        [p for c in cells for p in c["phases"]],
        ("policy", "phase", "strong_frac_of_bg"),
        (
            "safe_slo_goodput",
            "unsafe_admission_rate",
            "reject_rate",
            "n_checked",
            "n_starved",
            "checked_rate",
        ),
    )
    pooled_phases.sort(key=lambda m: (POLICY_ORDER.index(m["policy"]), m["phase"]))
    summary = {
        "bg": 0.4,
        "r_gateway": 3.01,
        "duration_s": E3_DUR,
        "reps": 5,
        "q_source": "frozen_g_light",
        "phases": [{"until_s": u, "strong_frac_of_bg": f} for u, f in E3_PHASES],
        "cells": cells,
        "pooled": pooled,
        "pooled_phases": pooled_phases,
    }
    (out / "metrics.json").write_text(json.dumps(summary, indent=2))
    lines = [
        "# E3 dynamic safety load (frozen minilm-l12-h384 q, 5 reps)",
        "",
        "R_gateway=3.01 rps, Bg=0.4 rps, 480s/policy × 5 reps. Mix 0.5→0.9→1.5→0.6 Bg.",
        "Tenant A only. q=frozen_g_light. Live ApplyGuardrail, no Maverick.",
        "Latency is safety-stage (scheduler + ApplyGuardrail), not user E2E.",
        "Paper cells are median [p25, p75]. Robustness under dynamic mix, not Proposed-dominance.",
        "UAR = light + strong + bypass. Residual is MiniLM FN and/or G_strong miss, not fail-open.",
        "checked/starved rebuilt from jsonl via applied_strong (route==strong / guardrail_block).",
        "",
        "## Overall (median [IQR])",
        "",
        "| policy | G_safe | UAR | light | strong | bypass | reject |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for m in pooled:
        lines.append(
            f"| {m['policy']} | {fmt_stat(m['safe_slo_goodput'])} | "
            f"{fmt_stat(m['unsafe_admission_rate'])} | {fmt_stat(m['uar_light'])} | "
            f"{fmt_stat(m['uar_strong'])} | {fmt_stat(m['uar_bypass'])} | "
            f"{fmt_stat(m['reject_rate'])} |"
        )
    lines += [
        "",
        "## Per phase (median [IQR] over 5 reps)",
        "",
        "| policy | phase | demand | G_safe | UAR | reject | checked | starved | checked_rate |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for m in pooled_phases:
        lines.append(
            f"| {m['policy']} | {m['phase']} | {m['strong_frac_of_bg']:.1f} Bg | "
            f"{fmt_stat(m['safe_slo_goodput'])} | {fmt_stat(m['unsafe_admission_rate'])} | "
            f"{fmt_stat(m['reject_rate'])} | {fmt_stat(m['n_checked'], digits=1)} | "
            f"{fmt_stat(m['n_starved'], digits=1)} | {fmt_stat(m['checked_rate'], digits=2)} |"
        )
    (out / "metrics.md").write_text("\n".join(lines) + "\n")
    print(f"refreshed {out}")


def _e4() -> None:
    out = results_dir("e4")
    pat = re.compile(rf"^r(\d+)_({POLICY_RE})\.jsonl$")
    cells = []
    for f in sorted(out.glob("r*.jsonl")):
        m = pat.match(f.name)
        if not m:
            continue
        rep, policy = int(m.group(1)), m.group(2)
        recs = load_jsonl(f, RunRecord)
        overall = aggregate(recs, duration_s=E4_DUR)
        overall.update({"policy": policy, "rep": rep, "n": len(recs)})
        cells.append(
            {
                "overall": overall,
                "phases": _phase_rows(
                    recs,
                    E4_PHASES,
                    policy=policy,
                    rep=rep,
                    extra_fn=lambda row, sus: row.update(
                        {
                            "suspicious_frac": sus,
                            "offered_strong_frac_of_bg": _offered_bg(sus),
                        }
                    ),
                ),
            }
        )
    pooled = pool_by(
        [c["overall"] for c in cells],
        ("policy",),
        (
            "safe_slo_goodput",
            "unsafe_admission_rate",
            "uar_light",
            "uar_strong",
            "uar_bypass",
            "reject_rate",
        ),
    )
    pooled.sort(key=lambda m: POLICY_ORDER.index(m["policy"]))
    pooled_phases = pool_by(
        [p for c in cells for p in c["phases"]],
        ("policy", "phase", "suspicious_frac", "offered_strong_frac_of_bg"),
        (
            "safe_slo_goodput",
            "unsafe_admission_rate",
            "reject_rate",
            "n_checked",
            "n_starved",
            "checked_rate",
        ),
    )
    pooled_phases.sort(key=lambda m: (POLICY_ORDER.index(m["policy"]), m["phase"]))
    summary = {
        "bg": 0.4,
        "r_gateway": 3.01,
        "duration_s": E4_DUR,
        "reps": 5,
        "q_source": "frozen_g_light",
        "phases": [
            {
                "until_s": u,
                "suspicious_frac": f,
                "offered_strong_frac_of_bg": _offered_bg(f),
            }
            for u, f in E4_PHASES
        ],
        "cells": cells,
        "pooled": pooled,
        "pooled_phases": pooled_phases,
    }
    (out / "metrics.json").write_text(json.dumps(summary, indent=2))
    lines = [
        "# E4 safety-capacity exhaustion (frozen minilm-l12-h384 q, 5 reps)",
        "",
        "R_gateway=3.01 rps (constant), Bg=0.4 rps, 420s/policy × 5 reps.",
        "Suspicious/adversarial mix 5% → 50% → 5%. Offered strong demand ≈ 0.38 → 3.76 → 0.38 Bg.",
        "Tenant A only. q=frozen_g_light. Live ApplyGuardrail, no Maverick.",
        "Phenomenon: safety-resource exhaustion at constant gateway RPS. Do not claim Proposed dominates.",
        "Latency is safety-stage, not user E2E. Paper cells are median [p25, p75].",
        "checked/starved rebuilt from jsonl via applied_strong (E4 jsonl has t_s, not metadata.phase).",
        "",
        "## Overall (median [IQR])",
        "",
        "| policy | G_safe | UAR | light | strong | bypass | reject |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for m in pooled:
        lines.append(
            f"| {m['policy']} | {fmt_stat(m['safe_slo_goodput'])} | "
            f"{fmt_stat(m['unsafe_admission_rate'])} | {fmt_stat(m['uar_light'])} | "
            f"{fmt_stat(m['uar_strong'])} | {fmt_stat(m['uar_bypass'])} | "
            f"{fmt_stat(m['reject_rate'])} |"
        )
    lines += [
        "",
        "## Per phase (median [IQR] over 5 reps)",
        "",
        "| policy | phase | sus | offered | G_safe | UAR | reject | checked | starved | checked_rate |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for m in pooled_phases:
        lines.append(
            f"| {m['policy']} | {m['phase']} | {m['suspicious_frac']:.0%} | "
            f"{m['offered_strong_frac_of_bg']:.2f} Bg | "
            f"{fmt_stat(m['safe_slo_goodput'])} | {fmt_stat(m['unsafe_admission_rate'])} | "
            f"{fmt_stat(m['reject_rate'])} | {fmt_stat(m['n_checked'], digits=1)} | "
            f"{fmt_stat(m['n_starved'], digits=1)} | {fmt_stat(m['checked_rate'], digits=2)} |"
        )
    (out / "metrics.md").write_text("\n".join(lines) + "\n")
    print(f"refreshed {out}")


def _e5() -> None:
    out = results_dir("e5")
    pat = re.compile(r"^r(\d+)_(proposed_fail_closed|proposed_fail_open)_(\d+\.\d+)\.jsonl$")
    cells = []
    for f in sorted(out.glob("r*.jsonl")):
        m = pat.match(f.name)
        if not m:
            continue
        rep, mode, frac = int(m.group(1)), m.group(2), float(m.group(3))
        recs = load_jsonl(f, RunRecord)
        metrics = aggregate(recs, duration_s=E5_DUR)
        metrics.update(e5_extra(recs))
        metrics.update(
            {
                "mode": mode,
                "fail_closed": "closed" in mode,
                "strong_demand_frac_of_bg": frac,
                "n": len(recs),
                "rep": rep,
            }
        )
        cells.append(metrics)
    pooled = pool_by(
        cells,
        ("mode", "strong_demand_frac_of_bg"),
        (
            "safe_slo_goodput",
            "unsafe_admission_rate",
            "uar_light",
            "uar_strong",
            "uar_bypass",
            "reject_rate",
            "bypass_rate_need",
            "n_checked",
            "n_starved",
            "n_need",
        ),
    )
    pooled.sort(key=lambda m: (0 if "closed" in m["mode"] else 1, m["strong_demand_frac_of_bg"]))
    summary = {
        "bg": 0.4,
        "r_gateway": 3.01,
        "duration_s": E5_DUR,
        "reps": 5,
        "q_source": "frozen_g_light",
        "cells": cells,
        "pooled": pooled,
    }
    (out / "metrics.json").write_text(json.dumps(summary, indent=2))
    lines = [
        "# E5 fail-open vs fail-closed (frozen minilm-l12-h384 q, 5 reps)",
        "",
        "Proposed only. R_gateway=3.01, Bg=0.4, 60s/cell × 5 reps. q=frozen_g_light.",
        "Fail-open disables deadline so exhaustion can bypass. Fail-closed keeps frozen B4.",
        "Paper cells are median [p25, p75]. MiniLM is an inexpensive risk estimator, not the authority.",
        "Fail-closed: UAR_bypass = 0 (zero scheduler-induced bypass), not a GT-safety guarantee.",
        "Fail-open bypasses 57–62% of policy-required strong checks and drives UAR to 1.0",
        "for only about 3% additional Safe Goodput. Residual fail-closed UAR is MiniLM FN and/or G_strong miss.",
        "n_checked rebuilt from jsonl via applied_strong (formal records store action=None).",
        "",
        "| mode | demand | G_safe | UAR | light | strong | bypass | reject | bypass/need | checked | starved |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for m in pooled:
        lines.append(
            f"| {m['mode']} | {m['strong_demand_frac_of_bg']:.1f} Bg | "
            f"{fmt_stat(m['safe_slo_goodput'])} | {fmt_stat(m['unsafe_admission_rate'])} | "
            f"{fmt_stat(m['uar_light'])} | {fmt_stat(m['uar_strong'])} | {fmt_stat(m['uar_bypass'])} | "
            f"{fmt_stat(m['reject_rate'])} | {fmt_stat(m['bypass_rate_need'], digits=2)} | "
            f"{fmt_stat(m['n_checked'], digits=1)} | {fmt_stat(m['n_starved'], digits=1)} |"
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
        "P95 is **safety-stage** latency (scheduler wait + ApplyGuardrail), not user E2E",
        "(E1–E6 have frozen q and no Maverick; MiniLM Function URL is not on the replay hot path).",
        "Without deadline-aware early rejection the gateway does more strong-guard work without raising G_safe.",
        "−NoTenant ≈ Full because this cell is Tenant A only (not because q is bimodal).",
        "",
        "| ablation | G_safe | UAR | reject | checked | safety-stage P95 ms |",
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
        "E1–E6 P95 is safety-stage / controller-path latency. User E2E = G_light + safety stage + Maverick.",
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
Fail-closed means **zero scheduler-induced bypass** (\(UAR_{bypass}=0\)), not MiniLM-FN-only residual UAR.

E1–E6 P95 is **safety-stage / controller-path** latency (scheduler + ApplyGuardrail), not user E2E.
MiniLM is an inexpensive risk estimator, not a low-latency guardrail.

| exp | status | headline |
| --- | --- | --- |
| E0a | **done** Function URL MiniLM | freeze AUROC 0.986, P50/P95 524/619 ms; 220 split-band across freeze+XSTest+WildGuardTest |
| E1 | frozen MiniLM q, 5 reps | Always-Strong wastes \(B_g\); UAR split (Always-Strong UAR is G_strong miss) |
| E2 | frozen MiniLM q, 5 reps | tenant isolation: Proposed 65.5%/40.3% B coverage vs load-aware 29.9%/27.1% at 90:10/70:30 |
| E3 | frozen MiniLM q, 5 reps | dynamic-load robustness at fixed RPS; not Proposed-dominance |
| E4 | frozen MiniLM q, 5 reps | exhaustion at constant RPS; checked/starved from applied_strong; not dominance |
| E5 | frozen MiniLM q, 5 reps | fail-open: UAR_bypass ↑, ~3% extra G_safe; fail-closed UAR_bypass = 0 |
| E6 | frozen MiniLM q, 5 reps | −NoEarlyReject: +strong work, safety-stage P95 ~77×, same G_safe |
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
