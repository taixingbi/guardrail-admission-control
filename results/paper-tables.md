# Paper table drafts (locked MiniLM campaign)

All E1–E6 cells: frozen Function URL MiniLM \(q\), live ApplyGuardrail, **no Maverick**, 5 reps, **median [p25, p75]**.
\(R_{\mathrm{gateway}}=3.01\) rps, \(B_g=0.4\) rps (gateway safety budget, not provider capacity).
E1–E6 P95 is **safety-stage** latency (scheduler wait + ApplyGuardrail), not user E2E.
Component UAR medians need not sum to UAR median; per-rep they do.

**Do not write:** “Proposed guarantees safety.” “UAR is MiniLM FN” for all policies. “MiniLM is a low-latency guardrail.” “Proposed dominates load-aware / risk-only.”

---

## Table 1 — G_light characterization (E0a)

*Caption.* MiniLM-L12-H384 Function URL as an inexpensive risk estimator \(q(x)\). Threshold \(\tau=0.50\) is frozen; we do not retune on external sets. The tenant-split band \(0.40\le q<0.75\) contains **220 examples across the scored evaluation sets** (freeze 38 + XSTest 40 + WildGuardTest 142), not 220 in the freeze set alone.

| Set | \(n\) | AUROC | AUPRC | Recall@0.50 | FPR@0.50 | P50 (ms) | P95 (ms) | \(0.40\le q<0.75\) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Freeze | 1888 | 0.986 | 0.990 | 0.956 | 0.034 | 524 | 619 | 38 |
| XSTest | 450 | 0.811 | 0.785 | 0.375 | 0.048 | 522 | 628 | 40 |
| WildGuardTest | 1699 | 0.876 | 0.876 | 0.720 | 0.105 | 661 | 1356 | 142 |

*Claim.* MiniLM is useful but imperfect (XSTest recall 0.375). Do not sell G_light as faster than ApplyGuardrail: Function URL P50/P95 (524/619 ms) exceeds ApplyGuardrail at \(C\le 16\) (P50 ~205–238 ms, P95 ~308–356 ms).

---

## Table 2 — Safe SLO-Goodput and strong-budget efficiency (E1)

*Caption.* Static safety load, Tenant A only, 40 s/cell. Uniform strong checking wastes a bounded safety budget; selective admission substantially improves policy-compliant goodput. Adaptive policies (risk-only, load-aware, Proposed) are statistically close — **this table is not a Proposed-dominance result.**

Safe SLO-Goodput is SLO-compliant goodput under the **modeled controller deadline**, not a measured user E2E SLO.

| Policy | \(0.5 B_g\) | \(1.0 B_g\) | \(1.5 B_g\) | Efficiency \(0.5 / 1.0 / 1.5 B_g\) |
| --- | --- | --- | --- | --- |
| Always-Strong | 0.925 [0.900, 1.025] | 0.900 [0.875, 0.950] | 0.800 [0.775, 0.875] | 0.10 / 0.15 / 0.21 |
| Risk-only | 2.750 [2.700, 2.800] | 2.575 [2.550, 2.600] | 2.400 [2.400, 2.475] | 1.00 / 1.00 / 1.00 |
| Load-aware | 2.750 [2.750, 2.825] | 2.500 [2.475, 2.500] | 2.300 [2.300, 2.400] | 1.00 / 1.00 / 1.00 |
| Proposed | 2.725 [2.700, 2.825] | 2.550 [2.500, 2.675] | 2.400 [2.400, 2.400] | 1.00 / 1.00 / 1.00 |

Efficiency = risk-required ApplyGuardrail occupancy / all ApplyGuardrail occupancy. Always-Strong occupancy with \(q<\tau\) is waste.

---

## Table 3 — UAR decomposition (E1)

*Caption.* \(UAR = UAR_{\mathrm{light}} + UAR_{\mathrm{strong}} + UAR_{\mathrm{bypass}}\). Always-Strong never consults the MiniLM threshold (`need_strong` is always true), so its residual UAR is an **ApplyGuardrail miss**, not a MiniLM false negative. Fail-closed adaptive policies have \(UAR_{\mathrm{bypass}}=0\).

| Policy | Demand | UAR | \(UAR_{\mathrm{light}}\) | \(UAR_{\mathrm{strong}}\) | \(UAR_{\mathrm{bypass}}\) |
| --- | --- | --- | --- | --- | --- |
| Always-Strong | \(0.5 B_g\) | 0.571 [0.500, 0.800] | 0.000 | 0.571 [0.500, 0.800] | 0.000 |
| Always-Strong | \(1.0 B_g\) | 0.471 [0.438, 0.692] | 0.000 | 0.471 [0.438, 0.692] | 0.000 |
| Always-Strong | \(1.5 B_g\) | 0.550 [0.429, 0.560] | 0.000 | 0.550 [0.429, 0.560] | 0.000 |
| Proposed | \(0.5 B_g\) | 0.900 [0.818, 1.000] | 0.067 [0.000, 0.091] | 0.833 [0.727, 0.900] | 0.000 |
| Proposed | \(1.0 B_g\) | 0.667 [0.667, 0.700] | 0.050 [0.000, 0.056] | 0.611 [0.600, 0.667] | 0.000 |
| Proposed | \(1.5 B_g\) | 0.545 [0.542, 0.577] | 0.083 [0.045, 0.100] | 0.458 [0.423, 0.500] | 0.000 |

\(UAR_{\mathrm{light}}\): GT-unsafe, \(q<\tau\), direct, admitted.
\(UAR_{\mathrm{strong}}\): GT-unsafe, ApplyGuardrail occupied, not blocked, admitted.
\(UAR_{\mathrm{bypass}}\): GT-unsafe, policy required strong, scheduler bypassed, admitted.

---

## Table 4 — Tenant isolation under contention (E2) — novelty

*Caption.* Split-band \(0.40\le q<0.75\): Proposed routes Tenant A direct and Tenant B to strong. Headline is **policy isolation / Tenant B strong-check coverage**, not better end-to-end safety accuracy. Do not headline \(UAR_B\) (Proposed \(UAR_B\) can be worse than load-aware).

120 s/cell. Coverage = checked / need among B required-strong. Split-band routing pooled over 5 reps.

| Policy | A:B | Split A → direct | Split B → need strong | Need\(_B\) | Checked\(_B\) | Coverage | \(UAR_B\) (do not headline) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Load-aware | 90:10 | 156 / 485 | 41 / 56 | 107 | 32 | **29.9%** | 0.500 [0.263, 0.548] |
| Proposed | 90:10 | **491 / 491** | **47 / 47** | 116 | 76 | **65.5%** | 0.667 [0.625, 0.722] |
| Load-aware | 70:30 | 117 / 374 | 112 / 165 | 284 | 77 | **27.1%** | 0.419 [0.380, 0.437] |
| Proposed | 70:30 | **367 / 367** | **170 / 170** | 352 | 142 | **40.3%** | 0.492 [0.481, 0.492] |

*Claim.* Tenant-aware admission protects the sensitive tenant’s access to scarce safety capacity under contention.

Appendix (same experiment, all mixes): coverage Proposed 65.5 / 40.3 / 30.9 / 25.2% vs load-aware 29.9 / 27.1 / 25.6 / 22.2% at 90:10 / 70:30 / 50:50 / 30:70.

---

## Table 5 — Safety demand can overload at constant gateway RPS (E4)

*Caption.* Gateway offered load fixed at \(R_{\mathrm{gateway}}=3.01\) rps. Suspicious mix 5% → 50% → 5% inflates offered strong demand \(0.38\to 3.76\to 0.38 B_g\) independently of total request rate. Phenomenon experiment; **do not claim Proposed dominates.** Occupancy via `applied_strong` (route `strong` / `guardrail_block`).

Proposed only (median over 5 reps):

| Phase | Mix | Offered strong | \(G_{\mathrm{safe}}\) | Checked | Starved | Checked rate |
| --- | ---: | --- | --- | --- | --- | --- |
| 0–120 s | 5% | \(0.38 B_g\) | 2.833 [2.825, 2.858] | 15 [14, 18] | 6 [5, 11] | 0.67 [0.58, 0.78] |
| 120–300 s | 50% | \(3.76 B_g\) | 1.489 [1.461, 1.556] | 59 [59, 60] | 200 [188, 203] | 0.23 [0.23, 0.24] |
| 300–420 s | 5% | \(0.38 B_g\) | 2.875 [2.867, 2.883] | 14 [13, 15] | 5 [3, 6] | 0.72 [0.65, 0.83] |

Overall Proposed \(G_{\mathrm{safe}}\) 2.269 [2.267, 2.283]; Always-Strong stuck at 0.286 [0.271, 0.293].

---

## Table 6 — Fail-closed vs fail-open (E5)

*Caption.* Proposed only. Fail-closed: **zero scheduler-induced bypass** (\(UAR_{\mathrm{bypass}}=0\)), not a GT-safety guarantee. Fail-open admits all GT-unsafe traffic in these cells and bypasses 57–62% of required strong checks for only ~3% additional Safe Goodput.

| Mode | Demand | \(G_{\mathrm{safe}}\) | UAR | \(UAR_{\mathrm{light}}\) | \(UAR_{\mathrm{strong}}\) | \(UAR_{\mathrm{bypass}}\) | Bypass/need | Checked |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Closed | \(1.5 B_g\) | 2.333 [2.200, 2.367] | 0.436 [0.429, 0.457] | 0.051 [0.029, 0.061] | 0.385 [0.367, 0.400] | **0.000** | **0.00** | 15 [15, 18] |
| Open | \(1.5 B_g\) | 2.400 [2.367, 2.433] | **1.000** | 0.056 [0.056, 0.059] | 0.394 [0.389, 0.412] | **0.529** [0.528, 0.556] | **0.57** [0.56, 0.58] | 15 [14, 16] |
| Closed | \(2.0 B_g\) | 2.200 [2.200, 2.267] | 0.458 [0.370, 0.476] | 0.095 [0.043, 0.104] | 0.326 [0.319, 0.354] | **0.000** | **0.00** | 16 [16, 17] |
| Open | \(2.0 B_g\) | 2.267 [2.250, 2.300] | **1.000** | 0.057 [0.024, 0.068] | 0.364 [0.341, 0.366] | **0.591** [0.549, 0.610] | **0.62** [0.61, 0.64] | 16 [16, 16] |

Residual fail-closed UAR is MiniLM FN **and/or** ApplyGuardrail miss.

---

## Table 7 — Deadline-aware early rejection (E6) — systems headline

*Caption.* Same arrivals as E3 Proposed overload phase (\(1.5 B_g\), 240–360 s). Without deadline-aware early rejection the gateway performs substantially more strong-guard work **without increasing** Safe SLO-Goodput, while **safety-stage** P95 increases by roughly two orders of magnitude. −NoTenant ≈ Full because this cell is Tenant A only.

| Ablation | \(G_{\mathrm{safe}}\) | UAR | Checked | Safety-stage P95 (ms) |
| --- | --- | --- | --- | --- |
| Full | 2.467 [2.392, 2.517] | 0.460 [0.425, 0.492] | 29 [27, 30] | **26** [24, 29] |
| −NoTenant | 2.442 [2.375, 2.458] | 0.429 [0.411, 0.458] | 31 [27, 32] | 26 [25, 26] |
| −NoDeadline | 2.467 [2.392, 2.517] | 0.460 [0.425, 0.492] | 29 [27, 30] | 25 [24, 26] |
| −NoEarlyReject | 2.467 [2.358, 2.517] | 0.635 [0.603, 0.678] | **39** [38, 41] | **2002** [2000, 2002] |

Full → −NoEarlyReject: \(G_{\mathrm{safe}}\) unchanged; strong work +34%; safety-stage P95 \(\times\sim 77\).

---

## Appendix A — Capacity characterization (E0b, E0c)

*Do not treat \(B_g^{\mathrm{raw}}\) as the paper’s scarce resource.* Experimental \(B_g=0.4\) rps is a gateway token-bucket.

**ApplyGuardrail (E0b), 12 s/C**

| \(C\) | Goodput (rps) | P50 (ms) | P95 (ms) | 429 | P95-stable |
| ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 4.42 | 217 | 317 | 0 | yes |
| 2 | 8.50 | 217 | 308 | 0 | yes |
| 4 | 15.83 | 238 | 333 | 0 | yes |
| 8 | 33.17 | 232 | 334 | 0 | yes |
| 16 | **71.42** | 205 | 356 | 0 | yes |
| 32 | 105.58 | 214 | 718 | 0 | no |

\(B_g^{\mathrm{raw}}=71.4\) rps at \(C=16\). Raw G_strong is not the bottleneck.

**Maverick (E0c), short prompts, 20 s/C**

| \(C\) | Goodput (rps) | TTFT P50 | TTFT P95 | E2E P95 | Healthy |
| ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 2.10 | 252 | 327 | 556 | yes |
| 2 | **4.30** | 249 | 322 | 563 | yes |
| 4 | 2.00 | 1094 | 6697 | 6838 | no |

\(C^*=2\), \(R_{\mathrm{knee}}=4.30\), \(R_{\mathrm{gateway}}=0.7\times R_{\mathrm{knee}}=3.01\) rps.

---

## Appendix B — Dynamic mix robustness (E3)

*Caption.* Gateway RPS fixed; strong-mix 0.5 → 0.9 → 1.5 → 0.6 \(B_g\) over 480 s. Use for **dynamic-load behavior**, not superiority. Proposed overall \(G_{\mathrm{safe}}\) 2.656 vs load-aware 2.650 vs risk-only 2.621; Proposed UAR 0.538 is not better than load-aware 0.500.

| Policy | \(G_{\mathrm{safe}}\) | UAR | \(UAR_{\mathrm{light}}\) | \(UAR_{\mathrm{strong}}\) | \(UAR_{\mathrm{bypass}}\) |
| --- | --- | --- | --- | --- | --- |
| Always-Strong | 0.327 [0.327, 0.329] | 0.136 [0.126, 0.139] | 0.000 | 0.136 [0.126, 0.139] | 0.000 |
| Risk-only | 2.621 [2.619, 2.640] | 0.510 [0.503, 0.531] | 0.038 [0.031, 0.044] | 0.459 [0.452, 0.500] | 0.000 |
| Load-aware | 2.650 [2.625, 2.658] | 0.500 [0.481, 0.516] | 0.047 [0.043, 0.052] | 0.440 [0.438, 0.465] | 0.000 |
| Proposed | 2.656 [2.642, 2.658] | 0.538 [0.527, 0.564] | 0.042 [0.042, 0.044] | 0.503 [0.485, 0.521] | 0.000 |

Proposed by phase (checked/starved rebuilt):

| Phase | Demand | \(G_{\mathrm{safe}}\) | Checked | Starved | Checked rate |
| --- | --- | --- | --- | --- | --- |
| 0–120 s | \(0.5 B_g\) | 2.767 [2.708, 2.825] | 19 [17, 20] | 10 [8, 15] | 0.66 [0.57, 0.68] |
| 120–240 s | \(0.9 B_g\) | 2.617 [2.583, 2.642] | 26 [24, 27] | 24 [24, 24] | 0.50 [0.49, 0.55] |
| 240–360 s | \(1.5 B_g\) | 2.467 [2.392, 2.517] | 28 [27, 30] | 36 [30, 43] | 0.43 [0.43, 0.46] |
| 360–480 s | \(0.6 B_g\) | 2.792 [2.775, 2.792] | 17 [15, 20] | 9 [8, 12] | 0.65 [0.64, 0.68] |

---

## Appendix C — Latency naming (do not put E1–E6 P95 in an E2E table)

| Quantity | What it includes | Where measured |
| --- | --- | --- |
| Safety-stage / controller-path | Scheduler wait + ApplyGuardrail | E1–E6 P95 (e.g. E6 Full 26 ms) |
| G_light endpoint | MiniLM Function URL | E0a freeze P50/P95 524 / 619 ms |
| User E2E | G_light + safety stage + Maverick | e2e `replay_q` P50 ~584 ms (frozen \(q\)); `live_path` puts Function URL on every request (P50 6.3 s) and is **not** the 600 ms SLO architecture number |

Tenant A SLO is 600 ms. Freeze MiniLM P95 (619 ms) already exceeds it, so E1–E6 cannot claim real-user E2E SLO compliance.

---

## Suggested figure / table mapping

| Paper slot | Source | One-line claim |
| --- | --- | --- |
| Fig / Table 7 (headline systems) | E6 Full vs −NoEarlyReject | Same \(G_{\mathrm{safe}}\), +34% strong work, safety-stage P95 \(\times 77\) |
| Table 2 | E1 G_safe + efficiency | Uniform strong wastes \(B_g\) |
| Table 4 | E2 90:10 and 70:30 | Tenant-aware coverage, not \(UAR_B\) |
| Table 6 | E5 | Fail-open: UAR 1.0 and 57–62% bypass for ~3% extra \(G_{\mathrm{safe}}\) |
| Table 5 | E4 Proposed phases | Safety demand ≠ gateway RPS |
| Table 1 | E0a | Honest screener, not low-latency |
| Appendix | E0b/E0c, E3 | Capacity lock-in; dynamic robustness |
