# GASC campaign summary

Locked Function URL MiniLM (`minilm-l12-h384`) campaign. E1–E6 replay frozen \(q\); live ApplyGuardrail; Maverick off except e2e. Median [p25, p75] over 5 reps. No E7/E8. Do not retune \(\tau\) or \(B_g\).

**Claim:** Proposed guarantees **policy compliance conditional on** \(q(x)\) — it never bypasses a request the policy marks as requiring strong. Fail-closed means **zero scheduler-induced bypass** (\(UAR_{bypass}=0\)). It does **not** guarantee GT safety. Residual fail-closed UAR is MiniLM FN and/or ApplyGuardrail miss, not fail-open.

**Do not cite** Nova Micro, laptop MiniLM, or old oracle tables.

E1–E6 P95 is **safety-stage / controller-path** latency (scheduler wait + ApplyGuardrail), not user E2E. MiniLM is an inexpensive risk estimator, not a low-latency guardrail (Function URL P50/P95 524/619 ms > ApplyGuardrail at C≤16).

## Layout

| path | what |
| --- | --- |
| `e0a/` | Function URL \(q\) on freeze + XSTest + WildGuardTest |
| `e0b/` `e0c/` | ApplyGuardrail raw capacity; Maverick knee (lock \(B_g\), \(R_{gateway}\)) |
| `e1/`–`e6/` | 5-rep replay cells (`r0`…`r4` jsonl + `metrics.md`) |
| `e2e/` | Proposed sanity: frozen \(q\) vs live Function URL on the hot path |
| `freeze/` | P4 prompt freeze (1888 / 472 families) |
| `metrics.md` | one-line index |
| `paper-tables.md` | locked paper table drafts |

## Locked knobs

| knob | value |
| --- | --- |
| G_light | Function URL `minilm-l12-h384` (inexpensive risk estimator) |
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

Freeze AUROC **0.986**, P50/P95 **524 / 619 ms**. Split-band \(0.40\le q<0.75\): **220 across scored evaluation sets** (freeze 38 + XSTest 40 + WildGuard 142). XSTest recall@0.50 is **0.375** — MiniLM is useful but imperfect.

### E1 — static safety load (40 s)

Always-Strong wastes \(B_g\) (efficiency **0.10 / 0.15 / 0.21** at 0.5 / 1.0 / 1.5 \(B_g\)). Proposed G_safe **2.73 / 2.55 / 2.40**; efficiency 1.00. Claim is efficiency, not Proposed-dominance vs load-aware/risk-only. Always-Strong UAR is G_strong miss.

### E2 — multi-tenant isolation (120 s)

Split-band: Proposed A **100% direct**, B **100% strong**. Tenant B coverage **65.5% / 40.3%** vs load-aware **29.9% / 27.1%** at 90:10 / 70:30. Headline is policy isolation / coverage, not UAR_B.

### E3 — dynamic mix at fixed RPS (480 s)

Phases 0.5 → 0.9 → 1.5 → 0.6 \(B_g\). Proposed overall G_safe **2.656**. Dynamic-load robustness; not a superiority experiment.

### E4 — exhaustion at constant RPS (420 s)

Suspicious mix 5% → 50% → 5% (offered strong ≈ 0.38 → 3.76 → 0.38 \(B_g\)). **Phenomenon only** — do not claim Proposed dominates. Checked/starved rebuilt via `applied_strong`.

### E5 — fail-open vs fail-closed

At 1.5 \(B_g\): fail-closed UAR **0.436**, G_safe **2.333**, bypass/need **0**; fail-open UAR **1.0**, G_safe **2.400**, bypass/need **0.57**. Fail-open admits all GT-unsafe in these cells and bypasses 57–62% of required strong checks for only ~3% additional Safe Goodput. Fail-closed claim is **zero scheduler-induced bypass**, not a safety guarantee.

### E6 — ablations (E3 overload 1.5 \(B_g\))

Full: checked **29**, safety-stage P95 **26 ms**, UAR **0.46**. −NoEarlyReject: checked **39**, P95 **2002 ms**, UAR **0.64**. Same G_safe **2.467**. Without deadline-aware early rejection the gateway does substantially more strong-guard work without increasing safe goodput, while safety-stage P95 increases by roughly two orders of magnitude.

### e2e — wiring check

`replay_q` (frozen \(q\)) P50 **~584 ms** is paper-comparable. `live_path` P50 **6.3 s** / P95 **21 s** puts Function URL MiniLM on every request and is **not** the 600 ms SLO architecture number.

## Paper tables (cite these)

E1 Proposed 1.5 \(B_g\): G_safe 2.400, UAR 0.545, reject 0.100, efficiency 1.00.

E2 Proposed vs load-aware B coverage: 65.5% / 40.3% vs 29.9% / 27.1% (90:10 / 70:30).

E5 1.5 \(B_g\): fail-closed UAR 0.436 bypass 0; fail-open UAR 1.0 bypass/need 0.57.

E6 Full vs −NoEarlyReject: safety-stage P95 26 ms vs 2002 ms.

Rebuild per-experiment `metrics.md` with `python3 scripts/refresh_replay_metrics.py` (no AWS). This summary is the locked campaign snapshot.
