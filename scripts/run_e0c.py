#!/usr/bin/env python3
"""E0c: Maverick short-prompt knee scout. Lock R_gateway below R_knee."""

from __future__ import annotations

import asyncio
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv

from gasc.clients.bedrock import bedrock_runtime, converse_stream
from gasc.eval_binary import percentile

SWEEP = (1, 2, 4)
DURATION_S = 20.0
MODEL = "us.meta.llama4-maverick-17b-instruct-v1:0"
PROMPT = "How do I bake chocolate chip cookies at home? Answer in one short paragraph."
MAX_TOKENS = 64
HEALTHY_THROTTLE = 0.02
HEALTHY_ERROR = 0.02


async def _run_level(*, client, model_id: str, concurrency: int, duration_s: float, pool: ThreadPoolExecutor) -> dict:
    sem = asyncio.Semaphore(concurrency)
    loop = asyncio.get_running_loop()
    rows: list = []
    t_end = time.perf_counter() + duration_s

    async def worker() -> None:
        while time.perf_counter() < t_end:
            async with sem:
                rec = await loop.run_in_executor(
                    pool,
                    lambda: converse_stream(client, model_id=model_id, user=PROMPT, max_tokens=MAX_TOKENS),
                )
                rows.append(rec)

    await asyncio.gather(*[asyncio.create_task(worker()) for _ in range(concurrency)])
    n = len(rows)
    ok = [r for r in rows if not r.throttled and r.error is None and r.ttft_ms is not None]
    throttled = sum(1 for r in rows if r.throttled)
    errors = sum(1 for r in rows if r.error and not r.throttled)
    ttft = [r.ttft_ms for r in ok]
    e2e = [r.e2e_ms for r in ok]
    goodput = len(ok) / duration_s
    throttle_rate = throttled / n if n else 0.0
    error_rate = errors / n if n else 0.0
    healthy = throttle_rate <= HEALTHY_THROTTLE and error_rate <= HEALTHY_ERROR and len(ok) > 0
    return {
        "concurrency": concurrency,
        "n": n,
        "ok": len(ok),
        "throttled": throttled,
        "errors": errors,
        "goodput_rps": goodput,
        "throttle_rate": throttle_rate,
        "error_rate": error_rate,
        "ttft_p50_ms": percentile(ttft, 50) if ttft else None,
        "ttft_p95_ms": percentile(ttft, 95) if ttft else None,
        "e2e_p50_ms": percentile(e2e, 50) if e2e else None,
        "e2e_p95_ms": percentile(e2e, 95) if e2e else None,
        "healthy": healthy,
    }


async def _sweep(region: str) -> list[dict]:
    client = bedrock_runtime(region)
    levels = []
    with ThreadPoolExecutor(max_workers=max(SWEEP)) as pool:
        for c in SWEEP:
            print(f"E0c C={c} for {DURATION_S:.0f}s…")
            rec = await _run_level(
                client=client, model_id=MODEL, concurrency=c, duration_s=DURATION_S, pool=pool
            )
            print(json.dumps(rec, indent=2))
            levels.append(rec)
            await asyncio.sleep(2.0)
    return levels


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    load_dotenv(root / ".env")
    region = os.environ.get("AWS_REGION", "us-east-1")
    levels = asyncio.run(_sweep(region))
    healthy = [r for r in levels if r["healthy"]]
    baseline = next((r["ttft_p95_ms"] for r in levels if r["concurrency"] == 1), None)
    stable = [
        r
        for r in healthy
        if r["ttft_p95_ms"] is not None and baseline and r["ttft_p95_ms"] <= 1.5 * baseline
    ]
    best = max(stable or healthy, key=lambda r: r["goodput_rps"]) if (stable or healthy) else None
    r_knee = best["goodput_rps"] if best else None
    r_gateway = round(0.7 * r_knee, 3) if r_knee else None
    summary = {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "duration_s": DURATION_S,
        "sweep": levels,
        "c_star": best["concurrency"] if best else None,
        "r_knee_rps": r_knee,
        "r_gateway_rps": r_gateway,
        "ttft_p95_at_cstar_ms": best["ttft_p95_ms"] if best else None,
        "note": "R_gateway = 0.7 * R_knee so E3/E4 do not mix LLM overload into safety-capacity effects.",
    }
    out = root / "results" / "e0c"
    out.mkdir(parents=True, exist_ok=True)
    (out / "metrics.json").write_text(json.dumps(summary, indent=2))
    lines = [
        "# E0c Maverick knee (short prompts)",
        "",
        f"ConverseStream, max_tokens={MAX_TOKENS}, {DURATION_S:.0f}s per C.",
        "",
        "| C | goodput rps | TTFT P50 | TTFT P95 | E2E P95 | throttle | healthy |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in levels:
        if r["ttft_p50_ms"] is None:
            lines.append(
                f"| {r['concurrency']} | {r['goodput_rps']:.2f} | — | — | — | "
                f"{r['throttle_rate']:.3f} | {r['healthy']} |"
            )
        else:
            lines.append(
                f"| {r['concurrency']} | {r['goodput_rps']:.2f} | "
                f"{r['ttft_p50_ms']:.0f} | {r['ttft_p95_ms']:.0f} | "
                f"{r['e2e_p95_ms']:.0f} | {r['throttle_rate']:.3f} | {r['healthy']} |"
            )
    lines.extend(
        [
            "",
            f"**C\\*** = {best['concurrency']}" if best else "**C*** unavailable",
            f"**R_knee** = {r_knee:.2f} rps" if r_knee else "",
            f"**R_gateway** = {r_gateway} rps (0.7 × R_knee)" if r_gateway else "",
            "",
        ]
    )
    (out / "metrics.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({"c_star": summary["c_star"], "r_knee_rps": r_knee, "r_gateway_rps": r_gateway}, indent=2))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
