#!/usr/bin/env python3
"""E0b: ApplyGuardrail concurrency sweep → B_g^{raw}, then lock experimental Bg."""

from __future__ import annotations

import asyncio
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv

from gasc.clients.bedrock import apply_guardrail, bedrock_runtime
from gasc.eval_binary import percentile
from gasc.variants import make_variants
from gasc.schemas import Seed

SWEEP = (1, 2, 4, 8, 16, 32)
DURATION_S = 12.0
HEALTHY_THROTTLE = 0.02
HEALTHY_ERROR = 0.02


def _prompt() -> str:
    seed = Seed(seed_id="e0b", intent="How do I bake chocolate chip cookies at home?")
    return make_variants(seed)[1].text  # S1 borderline-length


def _one(client, guardrail_id: str, version: str, text: str) -> dict:
    t0 = time.perf_counter()
    out = apply_guardrail(client, guardrail_id=guardrail_id, guardrail_version=version, text=text)
    out["latency_ms"] = (time.perf_counter() - t0) * 1000
    return out


async def _run_level(
    *,
    client,
    guardrail_id: str,
    version: str,
    text: str,
    concurrency: int,
    duration_s: float,
    pool: ThreadPoolExecutor,
) -> dict:
    sem = asyncio.Semaphore(concurrency)
    loop = asyncio.get_running_loop()
    rows: list[dict] = []
    t_end = time.perf_counter() + duration_s

    async def worker() -> None:
        while time.perf_counter() < t_end:
            async with sem:
                rec = await loop.run_in_executor(
                    pool,
                    lambda: _one(client, guardrail_id, version, text),
                )
                rows.append(rec)

    tasks = [asyncio.create_task(worker()) for _ in range(concurrency)]
    await asyncio.gather(*tasks)
    n = len(rows)
    ok = [r for r in rows if not r.get("throttled") and r.get("action") != "ERROR"]
    throttled = sum(1 for r in rows if r.get("throttled"))
    errors = sum(1 for r in rows if r.get("action") == "ERROR" and not r.get("throttled"))
    lat = [r["latency_ms"] for r in ok]
    elapsed = duration_s
    achieved = n / elapsed if elapsed else 0.0
    goodput = len(ok) / elapsed if elapsed else 0.0
    throttle_rate = throttled / n if n else 0.0
    error_rate = errors / n if n else 0.0
    healthy = (
        throttle_rate <= HEALTHY_THROTTLE
        and error_rate <= HEALTHY_ERROR
        and len(ok) > 0
    )
    p95 = percentile(lat, 95) if lat else None
    return {
        "concurrency": concurrency,
        "n": n,
        "ok": len(ok),
        "throttled": throttled,
        "errors": errors,
        "achieved_rps": achieved,
        "goodput_rps": goodput,
        "throttle_rate": throttle_rate,
        "error_rate": error_rate,
        "p50_ms": percentile(lat, 50) if lat else None,
        "p95_ms": p95,
        "healthy": healthy,
    }


async def _sweep(guardrail_id: str, version: str, region: str) -> list[dict]:
    text = _prompt()
    client = bedrock_runtime(region)
    levels = []
    max_c = max(SWEEP)
    with ThreadPoolExecutor(max_workers=max_c) as pool:
        for c in SWEEP:
            print(f"E0b C={c} for {DURATION_S:.0f}s…")
            rec = await _run_level(
                client=client,
                guardrail_id=guardrail_id,
                version=version,
                text=text,
                concurrency=c,
                duration_s=DURATION_S,
                pool=pool,
            )
            print(json.dumps(rec, indent=2))
            levels.append(rec)
            await asyncio.sleep(1.0)
    return levels


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    load_dotenv(root / ".env")
    gid = os.environ.get("GASC_GUARDRAIL_ID", "").strip()
    gver = os.environ.get("GASC_GUARDRAIL_VERSION", "1").strip() or "1"
    region = os.environ.get("AWS_REGION", "us-east-1")
    if not gid:
        raise SystemExit("GASC_GUARDRAIL_ID missing in .env")
    levels = asyncio.run(_sweep(gid, gver, region))
    healthy = [r for r in levels if r["healthy"]]
    baseline_p95 = next((r["p95_ms"] for r in levels if r["concurrency"] == 1), None)
    p95_stable = [
        r
        for r in healthy
        if r["p95_ms"] is not None
        and baseline_p95
        and r["p95_ms"] <= 1.5 * baseline_p95
    ]
    best = max(p95_stable or healthy, key=lambda r: r["goodput_rps"]) if (p95_stable or healthy) else None
    rg_raw = best["goodput_rps"] if best else None
    # Experimental Bg is a gateway org budget, not AWS quota.
    # Paper 9 Maverick knee ~1.84 rps; keep Bg << 0.7 * knee.
    experimental_bg = 0.4
    summary = {
        "guardrail_id": gid,
        "guardrail_version": gver,
        "duration_s": DURATION_S,
        "sweep": levels,
        "bg_raw_rps": rg_raw,
        "rg_raw_rps": rg_raw,
        "bg_raw_concurrency": best["concurrency"] if best else None,
        "rg_raw_concurrency": best["concurrency"] if best else None,
        "experimental_bg_rps": experimental_bg,
        "experimental_rg_rps": experimental_bg,
        "note": "experimental_bg is a gateway token-bucket, not B_g^{raw}.",
    }
    out = root / "results" / "e0b"
    out.mkdir(parents=True, exist_ok=True)
    (out / "metrics.json").write_text(json.dumps(summary, indent=2))
    lines = [
        "# E0b ApplyGuardrail capacity",
        "",
        f"Duration {DURATION_S:.0f}s per C. Guardrail `{gid}` v{gver}.",
        "",
        "| C | goodput rps | P50 ms | P95 ms | throttle | error | healthy |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in levels:
        lines.append(
            f"| {r['concurrency']} | {r['goodput_rps']:.2f} | "
            f"{r['p50_ms']:.0f} | {r['p95_ms']:.0f} | "
            f"{r['throttle_rate']:.3f} | {r['error_rate']:.3f} | {r['healthy']} |"
            if r["p50_ms"] is not None
            else f"| {r['concurrency']} | {r['goodput_rps']:.2f} | — | — | "
            f"{r['throttle_rate']:.3f} | {r['error_rate']:.3f} | {r['healthy']} |"
        )
    lines.extend(
        [
            "",
            f"**B_g^{{raw}}** = {rg_raw:.2f} rps at C={best['concurrency']}" if best else "**B_g^{raw}** unavailable",
            f"**Experimental Bg** = {experimental_bg} rps (gateway safety budget, not provider capacity).",
            "",
        ]
    )
    (out / "metrics.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({"bg_raw_rps": rg_raw, "experimental_bg_rps": experimental_bg}, indent=2))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
