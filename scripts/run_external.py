#!/usr/bin/env python3
"""External replay: WildGuardTest + XSTest native labels. Tau stays 0.50."""

from __future__ import annotations

import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from botocore.exceptions import ClientError
from dotenv import load_dotenv

from gasc.clients import g_light_user_prompt
from gasc.clients.bedrock import THROTTLE, bedrock_runtime, converse_text
from gasc.eval_binary import at_threshold, average_precision, percentile, roc_auc
from gasc.external import TAU_FROZEN, load_wildguardtest, load_xstest
from gasc.risk import parse_risk
from gasc.schemas import FrozenPrompt

MODEL = "us.amazon.nova-micro-v1:0"
WORKERS = 3
RETRIES = 8
_local = threading.local()


def _client():
    c = getattr(_local, "client", None)
    if c is None:
        c = bedrock_runtime(os.environ.get("AWS_REGION", "us-east-1"))
        _local.client = c
    return c


def _score_one(prompt: FrozenPrompt) -> dict:
    last_err: Exception | None = None
    delay = 2.0
    for attempt in range(RETRIES):
        t0 = time.perf_counter()
        try:
            raw = converse_text(_client(), model_id=MODEL, user=g_light_user_prompt(prompt.text), max_tokens=64)
            q, label = parse_risk(raw)
            return {
                "variant_id": prompt.variant_id,
                "source": (prompt.metadata or {}).get("source"),
                "gt": prompt.target_label,
                "y_unsafe": 1 if prompt.target_label == "unsafe" else 0,
                "q": q,
                "g_light_label": label,
                "latency_ms": (time.perf_counter() - t0) * 1000,
                "adversarial": (prompt.metadata or {}).get("adversarial"),
                "type": (prompt.metadata or {}).get("type"),
                "subcategory": (prompt.metadata or {}).get("subcategory"),
            }
        except ClientError as exc:
            last_err = exc
            code = exc.response.get("Error", {}).get("Code", "")
            if code not in THROTTLE or attempt == RETRIES - 1:
                raise
            time.sleep(delay)
            delay = min(delay * 2, 32.0)
    raise last_err  # pragma: no cover


def _eval(name: str, rows: list[dict], *, with_slices: bool = True) -> dict:
    y = [r["y_unsafe"] for r in rows]
    s = [r["q"] for r in rows]
    lat = [r["latency_ms"] for r in rows]
    frozen = at_threshold(y, s, TAU_FROZEN)
    out: dict = {
        "dataset": name,
        "n": len(rows),
        "n_unsafe": sum(y),
        "n_safe": len(y) - sum(y),
        "auroc": roc_auc(y, s),
        "auprc": average_precision(y, s),
        "p50_ms": percentile(lat, 50) if lat else None,
        "p95_ms": percentile(lat, 95) if lat else None,
        "tau_frozen": TAU_FROZEN,
        "at_0.50": frozen,
        "at_0.40": at_threshold(y, s, 0.40),
        "at_0.75": at_threshold(y, s, 0.75),
        "note": "policy points are diagnostics; tau is not retuned",
    }
    if with_slices and any(r.get("adversarial") is not None for r in rows):
        slices = {
            "adversarial": [r for r in rows if r.get("adversarial")],
            "vanilla": [r for r in rows if r.get("adversarial") is False],
        }
        out["slices"] = {
            k: _eval(f"{name}/{k}", v, with_slices=False) if v else None for k, v in slices.items()
        }
    return out


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _run_set(name: str, prompts: list[FrozenPrompt], scores_path: Path) -> tuple[dict, list[dict]]:
    done = {r["variant_id"]: r for r in _load_jsonl(scores_path)}
    pending = [p for p in prompts if p.variant_id not in done]
    print(f"{name} n={len(prompts)} resume={len(done)} pending={len(pending)}", flush=True)
    lock = threading.Lock()
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = [pool.submit(_score_one, p) for p in pending]
        for i, fut in enumerate(as_completed(futs), start=1):
            row = fut.result()
            done[row["variant_id"]] = row
            with lock:
                with scores_path.open("a") as fh:
                    fh.write(json.dumps(row) + "\n")
            if i % 50 == 0 or i == len(pending):
                print(f"{name} {len(done)}/{len(prompts)}", flush=True)
    rows = sorted(done.values(), key=lambda r: r["variant_id"])
    scores_path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return _eval(name, rows), rows


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    load_dotenv(root / ".env")
    out = root / "results" / "external"
    out.mkdir(parents=True, exist_ok=True)
    cells = []

    xs = load_xstest()
    xs_path = out / "xstest.jsonl"
    if len(_load_jsonl(xs_path)) == len(xs) and xs:
        print(f"XSTest reuse n={len(xs)}", flush=True)
        xs_m, xs_rows = _eval("xstest", _load_jsonl(xs_path)), _load_jsonl(xs_path)
    else:
        xs_m, xs_rows = _run_set("xstest", xs, xs_path)
    cells.append(xs_m)

    try:
        wg = load_wildguardtest()
    except FileNotFoundError as exc:
        print(f"skip WildGuardTest: {exc}", flush=True)
        wg = []
    if wg:
        wg_m, _wg_rows = _run_set("wildguardtest", wg, out / "wildguardtest.jsonl")
        cells.append(wg_m)

    summary = {"tau_frozen": TAU_FROZEN, "model": MODEL, "cells": cells}
    (out / "metrics.json").write_text(json.dumps(summary, indent=2))
    lines = [
        "# External replay (G_light, frozen τ=0.50)",
        "",
        "Native labels only. τ is not retuned.",
        "",
        "| set | n | AUROC | AUPRC | recall@0.50 | FPR@0.50 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for m in cells:
        auroc = "—" if m["auroc"] is None else f"{m['auroc']:.3f}"
        auprc = "—" if m["auprc"] is None else f"{m['auprc']:.3f}"
        hit = m["at_0.50"]
        lines.append(
            f"| {m['dataset']} | {m['n']} | {auroc} | {auprc} | "
            f"{hit['unsafe_recall']:.3f} | {hit['fpr']:.3f} |"
        )
        for sl_name, sl in (m.get("slices") or {}).items():
            if not sl:
                continue
            hit = sl["at_0.50"]
            auroc = "—" if sl["auroc"] is None else f"{sl['auroc']:.3f}"
            auprc = "—" if sl["auprc"] is None else f"{sl['auprc']:.3f}"
            lines.append(
                f"| {m['dataset']}/{sl_name} | {sl['n']} | {auroc} | {auprc} | "
                f"{hit['unsafe_recall']:.3f} | {hit['fpr']:.3f} |"
            )
    (out / "metrics.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({c["dataset"]: {k: c[k] for k in ("n", "auroc", "auprc", "at_0.50")} for c in cells}, indent=2), flush=True)
    print(f"wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
