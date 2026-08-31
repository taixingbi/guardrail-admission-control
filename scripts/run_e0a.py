#!/usr/bin/env python3
"""E0a: appendix Nova Micro G_light (not paper). Formal E0a is scripts/score_g_light.py."""

from __future__ import annotations

import json
import time
from pathlib import Path

from botocore.exceptions import ClientError

from gasc.clients import score_risk
from gasc.config import load_config
from gasc.eval_binary import average_precision, percentile, roc_auc, sweep_tau, at_threshold
from gasc.pipeline import run_pipeline


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    cfg = load_config(root / "configs" / "e0a.yaml", skip_llm=True)
    frozen = run_pipeline(cfg)
    model = cfg.models.g_light
    rows = []
    for i, prompt in enumerate(frozen, start=1):
        last_err = None
        for attempt in range(4):
            t0 = time.perf_counter()
            try:
                q, label = score_risk(prompt.text, model_id=model)
                latency_ms = (time.perf_counter() - t0) * 1000
                last_err = None
                break
            except ClientError as exc:
                last_err = exc
                time.sleep(0.5 * (attempt + 1))
        if last_err is not None:
            raise last_err
        y = 1 if prompt.target_label == "unsafe" else 0
        rows.append(
            {
                "variant_id": prompt.variant_id,
                "seed_id": prompt.seed_id,
                "variant": prompt.variant,
                "gt": prompt.target_label,
                "y_unsafe": y,
                "q": q,
                "g_light_label": label,
                "latency_ms": latency_ms,
            }
        )
        print(f"[{i}/{len(frozen)}] {prompt.variant_id} gt={prompt.target_label} q={q:.2f} {label} {latency_ms:.0f}ms")

    y_true = [r["y_unsafe"] for r in rows]
    scores = [r["q"] for r in rows]
    lat = [r["latency_ms"] for r in rows]
    sweep, best = sweep_tau(y_true, scores)
    policy_points = {
        "global_default_0.50": at_threshold(y_true, scores, 0.50),
        "tenant_B_0.40": at_threshold(y_true, scores, 0.40),
        "tenant_A_0.75": at_threshold(y_true, scores, 0.75),
    }
    summary = {
        "n": len(rows),
        "model": model,
        "auroc": roc_auc(y_true, scores),
        "auprc": average_precision(y_true, scores),
        "p50_ms": percentile(lat, 50),
        "p95_ms": percentile(lat, 95),
        "mean_ms": sum(lat) / len(lat),
        "parse_fail_review": sum(1 for r in rows if r["q"] == 1.0 and r["g_light_label"] == "REVIEW"),
        "chosen_tau": best,
        "policy_points": policy_points,
        "sweep": sweep,
    }
    out = root / "results" / "e0a"
    out.mkdir(parents=True, exist_ok=True)
    (out / "scores.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    (out / "metrics.json").write_text(json.dumps(summary, indent=2))
    (out / "metrics.md").write_text(
        "# E0a G_light (Nova Micro)\n\n"
        f"n={summary['n']}  AUROC={summary['auroc']:.3f}  AUPRC={summary['auprc']:.3f}\n\n"
        f"P50={summary['p50_ms']:.0f} ms  P95={summary['p95_ms']:.0f} ms\n\n"
        f"Chosen τ (Youden)={best['tau']:.2f}  recall={best['unsafe_recall']:.3f}  "
        f"FPR={best['fpr']:.3f}  escalation={best['escalation_rate']:.3f}\n"
    )
    print(json.dumps({k: summary[k] for k in ("n", "auroc", "auprc", "p50_ms", "p95_ms", "chosen_tau")}, indent=2))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
