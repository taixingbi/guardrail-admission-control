# Paper table drafts (E1–E6 rerun, 2026-11-09, live guardrail)

All E1–E6 cells: frozen Function URL MiniLM \(q\), live ApplyGuardrail **`wmw1sagwsxi7` v1 (account 751605536513, us-east-1, re-created from `scripts/guardrail-content-policy.json`)**, no Maverick, 5 reps, **median [p25, p75]**.
\(R_{\mathrm{gateway}}=3.01\) rps, \(B_g=0.4\) rps (gateway safety budget, not provider capacity).
E1–E6 P95 is **safety-stage** latency (scheduler wait + ApplyGuardrail), not user E2E.
Provenance: `results/rerun_provenance/` (HEAD, diff, campaign log). The Aug 30–31 campaign ran with a blank guardrail ID (no strong check ever executed) and is archived in `results/_stale_blank_guardrail_2026-08-31/`; **no number below comes from it.**

Every strong-routed record carries a verdict (8,073 `GUARDRAIL_INTERVENED`, 1,370 `NONE` across E1–E6); ApplyGuardrail P50 ≈ 185–192 ms in-run.

**UAR definition (code):** \(UAR = \#\{\text{GT-unsafe admitted to the LLM}\} / \#\{\text{GT-unsafe}\}\) = \(UAR_{\mathrm{light}} + UAR_{\mathrm{strong}} + UAR_{\mathrm{bypass}}\).

**Do not write:** “Proposed guarantees safety.” “MiniLM is a low-latency guardrail.” “Proposed dominates on every metric.”

---

## Table 1 — G_light characterization (E0a) — unchanged (no guardrail involved)

| Set | \(n\) | AUROC | AUPRC | Recall@0.50 | FPR@0.50 | P50 (ms) | P95 (ms) | \(0.40\le q<0.75\) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Freeze | 1888 | 0.986 | 0.990 | 0.956 | 0.034 | 524 | 619 | 38 |
| XSTest | 450 | 0.811 | 0.785 | 0.375 | 0.048 | 522 | 628 | 40 |
| WildGuardTest | 1699 | 0.876 | 0.876 | 0.720 | 0.105 | 661 | 1356 | 142 |

*Claim (updated).* MiniLM is useful but imperfect. Function URL P50/P95 (524/619 ms) exceeds ApplyGuardrail at \(C\le 16\) (new E0b: P50 141–181 ms, P95 222–254 ms).

---

## Table 2 — Safe SLO-Goodput and strong-budget efficiency (E1)

Static safety load, Tenant A only, 40 s/cell.

| Policy | \(0.5 B_g\) | \(1.0 B_g\) | \(1.5 B_g\) | Efficiency \(0.5 / 1.0 / 1.5 B_g\) |
| --- | --- | --- | --- | --- |
| Always-Strong | 0.200 [0.150, 0.200] | 0.175 [0.150, 0.200] | 0.175 [0.150, 0.200] | 0.06 / 0.24 / 0.24 |
| Risk-only | 2.675 [2.650, 2.700] | 2.550 [2.525, 2.575] | 2.350 [2.350, 2.450] | 1.00 / 1.00 / 1.00 |
| Load-aware | 2.700 [2.675, 2.750] | 2.475 [2.450, 2.475] | 2.300 [2.275, 2.375] | 1.00 / 1.00 / 1.00 |
| Proposed | 2.700 [2.700, 2.800] | 2.525 [2.475, 2.625] | 2.400 [2.375, 2.400] | 1.00 / 1.00 / 1.00 |

Always-Strong reject rate 0.93–0.95: with real ~190 ms checks the 0.4 rps budget admits ~17 checks / 40 s, so ~94% of traffic is deadline-rejected (old table: 0.80–0.93 G_safe, because blank-ID calls returned in ~20 ms). Adaptive policies remain statistically close.

---

## Table 3 — UAR with counts (E1)

With a live guardrail, \(UAR_{\mathrm{strong}} = 0\) and \(UAR_{\mathrm{bypass}} = 0\) in **every** E1 cell: all residual E1 UAR is MiniLM false negatives (\(q<\tau\), routed direct). Elsewhere guardrail misses are rare but nonzero: pooled strong misses / strong checks are 0–3 / ~490 per policy in E3 and E4, 1/76 in E5 fail-open 1.5 B_g, 0 in E6, and 9–21 / 150–230 per E2 cell (Tenant B traffic). Counts are pooled over 5 reps.

| Policy | \(0.5 B_g\) | \(1.0 B_g\) | \(1.5 B_g\) |
| --- | --- | --- | --- |
| Always-Strong | 0.000 (0/37) | 0.000 (0/76) | 0.000 (0/125) |
| Risk-only | 0.000 [0.000, 0.000] (1/46) | 0.056 [0.000, 0.074] (5/84) | 0.000 [0.000, 0.045] (2/101) |
| Load-aware | 0.000 [0.000, 0.000] (1/32) | 0.050 [0.050, 0.067] (6/93) | 0.000 [0.000, 0.045] (2/128) |
| Proposed | 0.067 [0.000, 0.091] (3/49) | 0.050 [0.000, 0.056] (5/79) | 0.083 [0.045, 0.100] (10/116) |

Always-Strong achieves UAR 0 by rejecting ~94% of all traffic, not by checking it (85 checks pooled).

---

## Table 4 — Tenant isolation under contention (E2) — novelty

Split band \(0.40\le q<0.75\): Proposed routes Tenant A direct and Tenant B to strong. 120 s/cell. Coverage = checked / need among B required-strong (pooled).

| Policy | A:B | Split A → direct | Split B → need strong | Need\(_B\) | Checked\(_B\) | Coverage | \(UAR_B\) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Load-aware | 90:10 | 156 / 485 | 41 / 56 | 107 | 32 | 29.9% | 0.231 [0.158, 0.235] |
| Proposed | 90:10 | **491 / 491** | **47 / 47** | 116 | 76 | **65.5%** | 0.222 [0.125, 0.250] |
| Load-aware | 70:30 | 117 / 374 | 112 / 165 | 284 | 77 | 27.1% | 0.242 [0.220, 0.268] |
| Proposed | 70:30 | **367 / 367** | **170 / 170** | 352 | 142 | **40.3%** | **0.175** [0.154, 0.183] |

All mixes (90:10 / 70:30 / 50:50 / 30:70):
- Coverage: Proposed 65.5 / 40.3 / 30.9 / 25.2% vs load-aware 29.9 / 27.1 / 25.6 / 22.0% (risk-only 31.3 / 30.7 / 26.9 / 24.1%).
- \(UAR_B\): Proposed 0.222 / 0.175 / 0.140 / 0.122 vs load-aware 0.231 / 0.242 / 0.232 / 0.206 (risk-only 0.294 / 0.231 / 0.263 / 0.231).

*Claim (stronger than before).* Tenant-aware admission raises Tenant B strong-check coverage and, with a live guardrail, also lowers \(UAR_B\) at 70:30–30:70 (IQRs do not overlap); at 90:10 the \(UAR_B\) difference is within noise.

---

## Table 5 — Safety demand overload at constant gateway RPS (E4)

\(R_{\mathrm{gateway}}=3.01\) rps fixed. Suspicious mix 5% → 50% → 5% inflates offered strong demand \(0.38\to 3.76\to 0.38 B_g\). Phenomenon experiment.

Proposed only (median over 5 reps):

| Phase | Mix | Offered strong | \(G_{\mathrm{safe}}\) | Checked | Starved | Checked rate |
| --- | ---: | --- | --- | --- | --- | --- |
| 0–120 s | 5% | \(0.38 B_g\) | 2.817 [2.800, 2.850] | 15 [14, 18] | 6 [5, 11] | 0.67 [0.58, 0.78] |
| 120–300 s | 50% | \(3.76 B_g\) | 1.478 [1.461, 1.550] | 59 [59, 60] | 200 [188, 203] | 0.23 [0.23, 0.24] |
| 300–420 s | 5% | \(0.38 B_g\) | 2.850 [2.842, 2.858] | 14 [13, 15] | 5 [3, 6] | 0.72 [0.65, 0.83] |

Overall \(G_{\mathrm{safe}}\) / UAR / reject: Proposed 2.257 [2.250, 2.264] / 0.059 [0.058, 0.060] / 0.238; load-aware 2.229 / 0.044 / 0.249; risk-only 2.183 / 0.048 / 0.263; Always-Strong 0.133 / 0.000 / 0.956. Burst-phase \(G_{\mathrm{safe}}\) is statistically tied across adaptive policies (1.478 / 1.483 / 1.494). Proposed UAR is slightly *higher* than load-aware here — do not claim UAR superiority from E4.

---

## Table 6 — Fail-closed vs fail-open (E5)

Proposed only, 60 s/cell. Fail-closed: zero scheduler-induced bypass, not a GT-safety guarantee.

| Mode | Demand | \(G_{\mathrm{safe}}\) | UAR (adm/unsafe) | \(UAR_{\mathrm{light}}\) | \(UAR_{\mathrm{bypass}}\) | Bypass/need | Reject |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Closed | \(1.5 B_g\) | 2.333 [2.200, 2.333] | 0.051 [0.029, 0.061] (11/201) | 0.051 | **0.000** | **0.00** | 0.211 |
| Open | \(1.5 B_g\) | 2.350 [2.350, 2.433] | **0.611** [0.588, 0.632] (108/177) | 0.056 | **0.529** [0.528, 0.556] | **0.57** [0.56, 0.58] | 0.083 |
| Closed | \(2.0 B_g\) | 2.200 [2.200, 2.217] | 0.095 [0.043, 0.104] (20/226) | 0.095 | **0.000** | **0.00** | 0.239 |
| Open | \(2.0 B_g\) | 2.267 [2.250, 2.283] | **0.636** [0.634, 0.659] (138/215) | 0.057 | **0.591** [0.549, 0.610] | **0.62** [0.61, 0.64] | 0.089 |

\(UAR_{\mathrm{strong}}\) median 0 in all cells (1 pooled miss in Open 1.5 B_g). *Claim.* Fail-open bypasses 57–62% of required strong checks and raises UAR ~7–12× (0.05–0.10 → 0.61–0.64) for ≤3% extra \(G_{\mathrm{safe}}\). **The old “UAR = 1.000” was an artifact of the blank guardrail ID** (every “checked” unsafe request was admitted).

---

## Table 7 — Deadline-aware early rejection (E6) — systems headline

Same arrivals as E3 Proposed overload phase (\(1.5 B_g\), 240–360 s).

| Ablation | \(G_{\mathrm{safe}}\) | UAR | Reject | Checked | Safety-stage P95 (ms) |
| --- | --- | --- | --- | --- | --- |
| Full | 2.458 [2.358, 2.517] | 0.041 [0.035, 0.048] | 0.175 | 29 [27, 30] | **178** [178, 179] |
| −NoTenant | 2.417 [2.333, 2.425] | 0.041 [0.026, 0.048] | 0.191 | 31 [27, 32] | 177 [177, 178] |
| −NoDeadline | 2.458 [2.358, 2.517] | 0.041 [0.035, 0.048] | 0.175 | 29 [27, 30] | 177 [177, 183] |
| −NoEarlyReject | 2.458 [2.358, 2.517] | 0.041 [0.035, 0.048] | 0.175 | **39** [38, 41] | **2002** [2002, 2002] |

Full → −NoEarlyReject: \(G_{\mathrm{safe}}\), UAR and reject identical; strong work +34%; safety-stage P95 **×11** (178 → 2002 ms). *Old text said ×77 (26 → 2002 ms); 26 ms was the blank-ID no-op.* −NoTenant ≈ Full because this cell is Tenant A only.

---

## Appendix A — Capacity characterization (E0b, E0c)

**ApplyGuardrail (E0b, rerun), 12 s/C, `wmw1sagwsxi7` v1**

| \(C\) | Goodput (rps) | P50 (ms) | P95 (ms) | Throttle | Healthy |
| ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 5.25 | 181 | 254 | 0.000 | yes |
| 2 | 11.67 | 175 | 242 | 0.000 | yes |
| 4 | 24.92 | 145 | 222 | 0.000 | yes |
| 8 | 51.42 | 141 | 231 | 0.000 | yes |
| 16 | **101.67** | 141 | 231 | 0.000 | yes |
| 32 | 110.17 | 147 | 806 | 0.001 | P95 unstable |

\(B_g^{\mathrm{raw}}=101.67\) rps at \(C=16\) (was 71.4). Raw G_strong is still not the bottleneck; experimental \(B_g=0.4\) rps is a gateway token bucket.

**Maverick (E0c), unchanged:** \(C^*=2\), \(R_{\mathrm{knee}}=4.30\), \(R_{\mathrm{gateway}}=0.7\times R_{\mathrm{knee}}=3.01\) rps.

---

## Appendix B — Dynamic mix (E3)

Gateway RPS fixed; strong mix 0.5 → 0.9 → 1.5 → 0.6 \(B_g\) over 480 s.

| Policy | \(G_{\mathrm{safe}}\) | UAR (adm/unsafe) | Reject | Overload-phase \(G_{\mathrm{safe}}\) (240–360 s) | Overload starved |
| --- | --- | --- | --- | --- | --- |
| Always-Strong | 0.167 [0.165, 0.181] | 0.000 (1/874) | 0.945 | 0.158 [0.158, 0.158] | 316 |
| Risk-only | 2.587 [2.573, 2.596] | 0.038 [0.031, 0.049] (32/816) | 0.136 | 2.333 [2.333, 2.392] | 46 [42, 48] |
| Load-aware | 2.600 [2.577, 2.604] | 0.052 [0.043, 0.061] (39/810) | 0.130 | 2.325 [2.292, 2.358] | 46 [46, 49] |
| Proposed | **2.642** [2.623, 2.646] | 0.042 [0.042, 0.044] (34/816) | **0.117** | **2.458** [2.358, 2.517] | **36** [30, 43] |

Proposed by phase:

| Phase | Demand | \(G_{\mathrm{safe}}\) | Checked | Starved | Checked rate |
| --- | --- | --- | --- | --- | --- |
| 0–120 s | \(0.5 B_g\) | 2.767 [2.700, 2.800] | 19 [18, 20] | 10 [8, 15] | 0.66 [0.57, 0.68] |
| 120–240 s | \(0.9 B_g\) | 2.600 [2.550, 2.600] | 26 [24, 27] | 24 [24, 24] | 0.50 [0.49, 0.55] |
| 240–360 s | \(1.5 B_g\) | 2.458 [2.358, 2.517] | 28 [27, 30] | 36 [30, 43] | 0.43 [0.43, 0.46] |
| 360–480 s | \(0.6 B_g\) | 2.758 [2.758, 2.792] | 17 [15, 20] | 9 [8, 12] | 0.65 [0.64, 0.68] |

---

## Appendix C — End-to-end sanity (e2e `replay_q`, rerun)

Proposed, \(1.0 B_g\), 40 s, frozen \(q\) + live guardrail + Maverick (\(C^*=2\)).

| \(G_{\mathrm{safe}}\)@600 | \(G_{\mathrm{safe}}\)@800 | UAR | E2E P50 / P95 (ms) | TTFT P95 | Admitted within SLO |
| --- | --- | --- | --- | --- | --- |
| 1.775 | 2.525 | 0.000 (0/17) | 555 / 703 | 343 | 0.70 |

`live_path` (Function URL on every request) not rerun: the MiniLM Function URL does not exist in the current account.

---

## Sensitivity — reserved share ρ (sweep_rho, 2026-11-09)

Proposed, E2 arrivals (same seeds), 120 s × 5 reps. ρ = 0.4 is `results/e2`.

| ρ | 90:10 cov B | 90:10 UAR_B | 90:10 G_safe | 70:30 cov B | 70:30 UAR_B | 70:30 G_safe |
| --- | ---: | --- | --- | ---: | --- | --- |
| 0.0 | 45.7% | 0.167 [0.100, 0.222] | 1.983 | 32.4% | 0.169 [0.135, 0.173] | 1.708 |
| 0.2 | 62.1% | 0.222 [0.100, 0.250] | 1.992 | 37.2% | 0.169 [0.135, 0.190] | 1.717 |
| 0.4 | 65.5% | 0.222 [0.125, 0.250] | 1.983 | 40.3% | 0.175 [0.154, 0.183] | 1.708 |
| 0.6 | 67.2% | 0.222 [0.100, 0.222] | 1.975 | 43.8% | 0.175 [0.127, 0.183] | 1.717 |
| load-aware | 29.9% | 0.231 | 1.758 | 27.1% | 0.242 | 1.625 |

*Claim.* Coverage rises monotonically with ρ at flat overall G_safe; UAR_B is flat in ρ, so the E2 UAR_B gain comes from Tenant B's τ=0.40, not from the reservation. ρ=0.4 is not a tuned optimum.

## Sensitivity — deadline (sweep_deadline, 2026-11-09)

E6 trace (1.5 B_g), Tenant A deadline 400 / 600 (E6) / 800 / 1200 ms, 5 reps. Every metric identical across deadlines: Full 29 checks, P95 178–188 ms; −NoEarlyReject 39 checks, P95 2002 ms; G_safe 2.458, UAR 0.041, reject 0.175 for both. At B_g = 0.4 the token refill interval (2.5 s) exceeds every deadline tested, so the budget, not the deadline, decides which requests are rejected. Deadlines > 2.5 s are not covered.

---

## Suggested figure / table mapping

| Paper slot | Source | One-line claim |
| --- | --- | --- |
| Table 7 (systems headline) | E6 Full vs −NoEarlyReject | Same \(G_{\mathrm{safe}}\) and UAR, +34% strong work, safety-stage P95 ×11 |
| Table 4 (novelty) | E2 | Tenant B coverage up to 2.2×; \(UAR_B\) lower at 70:30–30:70 |
| Table 2 / 3 | E1 | Uniform strong collapses goodput (0.18 vs ~2.5); residual UAR is MiniLM FN only |
| Table 6 | E5 | Fail-open: 57–62% bypass, UAR ×7–12 for ≤3% \(G_{\mathrm{safe}}\) |
| Table 5 | E4 | Safety demand ≠ gateway RPS |
| Appendix | E0b/E0c, E3, e2e | Capacity, dynamic robustness, E2E sanity |
