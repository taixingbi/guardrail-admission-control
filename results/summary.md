# GASC campaign summary

Locked Function URL MiniLM (`minilm-l12-h384`) campaign. E1–E6 replay frozen \(q\); live ApplyGuardrail; Maverick off except e2e. Median [p25, p75] over 5 reps. No E7/E8. Do not retune \(\tau\) or \(B_g\).

**Claim:** Proposed guarantees **policy compliance conditional on** \(q(x)\) — it never bypasses a request the policy marks as requiring strong. It does **not** guarantee GT safety. Residual UAR is MiniLM false negatives (especially XSTest), not scheduler fail-open.

**Do not cite** Nova Micro, laptop MiniLM, or old oracle tables.

## Layout

| path | what |
| --- | --- |
| `e0a/` | Function URL \(q\) on freeze + XSTest + WildGuardTest |
| `e0b/` `e0c/` | ApplyGuardrail raw capacity; Maverick knee (lock \(B_g\), \(R_{gateway}\)) |
| `e1/`–`e6/` | 5-rep replay cells (`r0`…`r4` jsonl + `metrics.md`) |
| `e2e/` | Proposed sanity: frozen \(q\) vs live Function URL on the hot path |
| `freeze/` | P4 prompt freeze (1888 / 472 families) |
| `metrics.md` | one-line index |

## Locked knobs

| knob | value |
| --- | --- |
| G_light | Function URL `minilm-l12-h384` (screener) |
| G_strong | ApplyGuardrail `bklyj6c5nrb5` v1 |
| LLM | Llama 4 Maverick 17B |
| \(\tau\) | 0.50 global; Tenant A 0.75 / B 0.40 |
| \(B_g\) | **0.4 rps** gateway token-bucket (not provider capacity) |
| \(B_g^{raw}\) | 71.4 rps at C=16 (E0b characterization only) |
| \(R_{gateway}\) | **3.01 rps** (`0.7 ×` Maverick knee 4.30; \(C^*=2\)) |
| Fail mode | fail-closed (E5 compares open) |
| Frozen prompts | 1888 (Haiku 4.5 judge; not Nova / Guardrail / Maverick) |

## Headlines

### E0a — G_light

Freeze AUROC **0.986**, P50/P95 **524 / 619 ms**. Tenant-split band \(0.40\le q<0.75\): **220** across freeze+XSTest+WildGuardTest (freeze-only 38). XSTest recall@0.50 is **0.375** — MiniLM FN, not a scheduler bug.

### E1 — static safety load (40 s)

Always-Strong wastes \(B_g\) (efficiency **0.10 / 0.15 / 0.21** at 0.5 / 1.0 / 1.5 \(B_g\)). Proposed G_safe **2.73 / 2.55 / 2.40**; efficiency 1.00. UAR is MiniLM FN.

### E2 — multi-tenant isolation (120 s)

Split-band: Proposed A **100% direct**, B **100% strong**. Tenant B coverage **65.5% / 40.3%** vs load-aware **29.9% / 27.1%** at 90:10 / 70:30.

### E3 — dynamic mix at fixed RPS (480 s)

Phases 0.5 → 0.9 → 1.5 → 0.6 \(B_g\). Proposed overall G_safe **2.656**. G_safe moves with strong-mix; Always-Strong stuck at ~0.33.

### E4 — exhaustion at constant RPS (420 s)

Suspicious mix 5% → 50% → 5% (offered strong ≈ 0.38 → 3.76 → 0.38 \(B_g\)). **Phenomenon only** — do not claim Proposed dominates. Proposed G_safe **2.269**.

### E5 — fail-open vs fail-closed

At 1.5 \(B_g\): fail-closed UAR **0.436**, G_safe **2.333**, bypass/need **0**; fail-open UAR **1.0**, G_safe **2.400**, bypass/need **0.57**. Fail-open raises UAR without raising Safe Goodput.

### E6 — ablations (E3 overload 1.5 \(B_g\))

Full: checked **29**, P95 **26 ms**, UAR **0.46**. −NoEarlyReject: checked **39**, P95 **2002 ms**, UAR **0.64**. −NoTenant ≈ Full because this cell is Tenant A only.

### e2e — wiring check

`replay_q` (frozen \(q\)) P50 **~584 ms** is paper-comparable. `live_path` P50 **6.3 s** / P95 **21 s** puts Function URL MiniLM on every request and is **not** the 600 ms SLO architecture number.

## Paper tables (cite these)

E1 Proposed 1.5 \(B_g\): G_safe 2.400, UAR 0.545, reject 0.100, efficiency 1.00.

E2 Proposed vs load-aware B coverage: 65.5% / 40.3% vs 29.9% / 27.1% (90:10 / 70:30).

E5 1.5 \(B_g\): fail-closed UAR 0.436 bypass 0; fail-open UAR 1.0 bypass/need 0.57.

E6 Full vs −NoEarlyReject: P95 26 ms vs 2002 ms.

Rebuild per-experiment `metrics.md` with `python3 scripts/refresh_replay_metrics.py` (no AWS). This summary is the locked campaign snapshot.
