# E2 multi-tenant contention (formal, live q, 5 reps)

Gateway safety budget Bg=0.4 rps (not ApplyGuardrail provider capacity). R_gateway=3.01, 120s/cell × 5 reps.
q = frozen/live G_light. Tenant-split band is 0.40 ≤ q < 0.75 (A direct, B strong).
Isolation = checked vs starved among B required-strong. Pooled over reps.

## Tenant-split routing (pooled)

| policy | A:B | split_A | A direct | split_B | B need_strong | B checked |
| --- | --- | --- | --- | --- | --- | --- |
| always_strong | 90%:10% | 435 | 0 | 44 | 44 | 9 |
| always_strong | 70%:30% | 366 | 0 | 153 | 153 | 22 |
| always_strong | 50%:50% | 271 | 0 | 249 | 249 | 43 |
| always_strong | 30%:70% | 155 | 0 | 325 | 325 | 43 |
| risk_only | 90%:10% | 464 | 154 | 44 | 33 | 8 |
| risk_only | 70%:30% | 331 | 107 | 139 | 101 | 30 |
| risk_only | 50%:50% | 236 | 72 | 254 | 173 | 42 |
| risk_only | 30%:70% | 159 | 58 | 398 | 275 | 67 |
| load_aware | 90%:10% | 485 | 156 | 56 | 41 | 11 |
| load_aware | 70%:30% | 374 | 117 | 165 | 112 | 34 |
| load_aware | 50%:50% | 256 | 92 | 278 | 197 | 51 |
| load_aware | 30%:70% | 148 | 42 | 358 | 259 | 63 |
| proposed | 90%:10% | 491 | 491 | 47 | 47 | 29 |
| proposed | 70%:30% | 367 | 367 | 170 | 170 | 69 |
| proposed | 50%:50% | 253 | 253 | 270 | 270 | 87 |
| proposed | 30%:70% | 167 | 167 | 396 | 396 | 92 |

## Isolation (pooled B required-strong)

| policy | A:B | G_safe | G_safe_B | need_B | checked_B | starved_B | n_B_unsafe | UAR_B |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| always_strong | 90%:10% | 0.105 | 0.007 | 168 | 23 | 145 | 105 | 0.038 |
| always_strong | 70%:30% | 0.115 | 0.012 | 536 | 68 | 468 | 302 | 0.030 |
| always_strong | 50%:50% | 0.112 | 0.038 | 910 | 123 | 787 | 543 | 0.014 |
| always_strong | 30%:70% | 0.093 | 0.052 | 1270 | 157 | 1113 | 713 | 0.015 |
| risk_only | 90%:10% | 1.792 | 0.110 | 83 | 26 | 57 | 86 | 0.239 |
| risk_only | 70%:30% | 1.662 | 0.303 | 293 | 90 | 203 | 322 | 0.238 |
| risk_only | 50%:50% | 1.470 | 0.557 | 479 | 129 | 350 | 526 | 0.266 |
| risk_only | 30%:70% | 1.203 | 0.657 | 715 | 172 | 543 | 740 | 0.235 |
| load_aware | 90%:10% | 1.773 | 0.073 | 107 | 32 | 75 | 117 | 0.208 |
| load_aware | 70%:30% | 1.638 | 0.325 | 284 | 77 | 207 | 297 | 0.248 |
| load_aware | 50%:50% | 1.392 | 0.450 | 520 | 133 | 387 | 551 | 0.228 |
| load_aware | 30%:70% | 1.230 | 0.692 | 722 | 160 | 562 | 735 | 0.209 |
| proposed | 90%:10% | 1.988 | 0.095 | 116 | 76 | 40 | 104 | 0.195 |
| proposed | 70%:30% | 1.712 | 0.265 | 352 | 142 | 210 | 301 | 0.170 |
| proposed | 50%:50% | 1.505 | 0.447 | 570 | 176 | 394 | 515 | 0.156 |
| proposed | 30%:70% | 1.225 | 0.590 | 832 | 210 | 622 | 717 | 0.117 |

## Read

Local MiniLM \(q(x)\), 4037 scored prompts, **220** in \(0.40\le q<0.75\). \(B_g=0.4\), 120 s × 5 reps. Isolation = checked / (checked + starved) among B required-strong.

**Tenant thresholds now move routes.** On the split band, Proposed sends every A request direct (491/491, 367/367, 253/253, 167/167) and every B request to strong. always_strong sends none of those A requests direct. That is the \(q\approx 0.6\), A \(\tau=0.75\) vs B \(\tau=0.40\) test Nova Micro could not run.

**Isolation.** Proposed vs load-aware at 90:10 / 70:30: **65.5% / 40.3%** vs **29.9% / 27.1%**. The reserved share still protects B when A dominates. The 70:30 gap is smaller than the old bimodal-\(q\) campaign; do not quote those earlier percentages.

**Safety / goodput.** Proposed \(G_{safe}\) 1.99 / 1.71 / 1.51 / 1.23. Highest at 90:10 (risk_only 1.79). At 30:70 the risk-gated policies cluster. always_strong sits at \(\approx 0.11\). Proposed \(UAR_B\) 0.12–0.20 (risk_only 0.24–0.27): MiniLM underscores some GT-unsafe below \(\tau_B=0.40\), especially XSTest. ApplyGuardrail remains the authority. Do not retune \(\tau\) or \(B_g\).

\(n_{B,unsafe}\) pooled is 86–740. The thin-count problem is gone.
