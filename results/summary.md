# GASC campaign summary

Locked Function URL MiniLM (`minilm-l12-h384`) campaign; E0b–E6 + e2e `replay_q` **rerun 2026-11-08/09 with live guardrail `wmw1sagwsxi7` v1** (the Aug 30–31 run had a blank guardrail ID; archived in `_stale_blank_guardrail_2026-08-31/`, do not cite). E1–E6 replay frozen \(q\); live ApplyGuardrail; Maverick off except e2e. Median [p25, p75] over 5 reps. No E7/E8. Do not retune \(\tau\) or \(B_g\).

**Claim:** Proposed guarantees **policy compliance conditional on** \(q(x)\) — it never bypasses a request the policy marks as requiring strong. Fail-closed means **zero scheduler-induced bypass** (\(UAR_{bypass}=0\)). It does **not** guarantee GT safety. Residual fail-closed UAR is almost entirely MiniLM FN (ApplyGuardrail misses are rare: 0 in E1/E6, ≤3 per policy in E3/E4, 9–21 per E2 cell).

**Do not cite** Nova Micro, laptop MiniLM, or old oracle tables.

E1–E6 P95 is **safety-stage / controller-path** latency (scheduler wait + ApplyGuardrail), not user E2E. MiniLM is an inexpensive risk estimator, not a low-latency guardrail (Function URL P50/P95 524/619 ms > ApplyGuardrail at C≤16).

## Layout

| path | what |
| --- | --- |
| `e0a/` | Function URL \(q\) on freeze + XSTest + WildGuardTest |
| `e0b/` `e0c/` | ApplyGuardrail raw capacity; Maverick knee (lock \(B_g\), \(R_{gateway}\)) |
| `e1/`–`e6/` | 5-rep replay cells (`r0`…`r4` jsonl + `metrics.md`) |
| `e2e/` | Proposed sanity: frozen \(q\) + live guardrail + Maverick (`replay_q` only after rerun) |
| `rerun_provenance/` | HEAD, diff, campaign log for the 2026-11 rerun |
| `_stale_blank_guardrail_2026-08-31/` | invalid Aug campaign (blank guardrail ID) — do not cite |
| `freeze/` | P4 prompt freeze (1888 / 472 families) |
| `metrics.md` | one-line index |
| `paper-tables.md` | locked paper table drafts |

## Locked knobs

| knob | value |
| --- | --- |
| G_light | Function URL `minilm-l12-h384` (inexpensive risk estimator) |
| G_strong | ApplyGuardrail `wmw1sagwsxi7` v1 (account 751605536513; re-created from `scripts/guardrail-content-policy.json`; original `bklyj6c5nrb5` unreachable) |
| LLM | Llama 4 Maverick 17B |
| \(\tau\) | 0.50 global; Tenant A 0.75 / B 0.40 |
| \(B_g\) | **0.4 rps** gateway token-bucket (not provider capacity) |
| \(B_g^{raw}\) | 101.67 rps at C=16 (E0b rerun; was 71.4) |
| \(R_{gateway}\) | **3.01 rps** (`0.7 ×` Maverick knee 4.30; \(C^*=2\)) |
| Fail mode | fail-closed (E5 compares open) |
| Frozen prompts | 1888 (Haiku 4.5 judge; not Nova / Guardrail / Maverick) |

## Headlines (rerun)

### E0a — G_light (unchanged)

Freeze AUROC **0.986**, P50/P95 **524 / 619 ms**. XSTest recall@0.50 **0.375**. ApplyGuardrail is faster (E0b P50 141–181 ms at C≤16).

### E1 — static safety load (40 s)

Always-Strong G_safe **0.20 / 0.18 / 0.18** (rejects 93–95%), efficiency 0.06 / 0.24 / 0.24. Proposed G_safe **2.70 / 2.53 / 2.40**; adaptive policies statistically close. UAR is MiniLM FN only (UAR_strong = UAR_bypass = 0 in every cell).

### E2 — multi-tenant isolation (120 s)

Tenant B coverage Proposed **65.5 / 40.3 / 30.9 / 25.2%** vs load-aware **29.9 / 27.1 / 25.6 / 22.0%**. UAR_B Proposed **0.222 / 0.175 / 0.140 / 0.122** vs load-aware 0.231 / 0.242 / 0.232 / 0.206 (IQRs separate at 70:30–30:70).

### E3 — dynamic mix at fixed RPS (480 s)

Proposed G_safe **2.642** vs load-aware 2.600, risk-only 2.587, Always-Strong 0.167; overload phase 2.458 vs ~2.33. UAR 0.04–0.05 for adaptive policies.

### E4 — exhaustion at constant RPS (420 s)

Proposed phases G_safe 2.817 → **1.478** → 2.850; checked rate 0.67 → 0.23 → 0.72. Burst phase tied across adaptive policies. Overall Proposed 2.257 (best) but UAR 0.059 vs 0.044–0.048.

### E5 — fail-open vs fail-closed

1.5 \(B_g\): fail-closed UAR **0.051** (11/201), G_safe 2.333, bypass 0; fail-open UAR **0.611** (108/177), G_safe 2.350, bypass/need **0.57**. 2.0 \(B_g\): 0.095 → 0.636, bypass 0.62. ≤3% G_safe gain for 7–12× UAR.

### E6 — ablations (E3 overload 1.5 \(B_g\))

Full: checked **29**, safety-stage P95 **178 ms**. −NoEarlyReject: checked **39**, P95 **2002 ms** (×11). G_safe 2.458, UAR 0.041, reject 0.175 identical.

### e2e — `replay_q`

Proposed 1.0 \(B_g\), live guardrail + Maverick: E2E P50/P95 **555 / 703 ms**, G_safe@600 1.775, UAR 0/17. `live_path` not rerun (Function URL absent in the new account).

## Paper tables

See `paper-tables.md` (rebuilt from the rerun). Per-experiment `metrics.md` were written by the runners during the rerun.
