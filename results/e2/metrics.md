# E2 multi-tenant contention (frozen minilm-l12-h384 q, 5 reps)

Gateway safety budget Bg=0.4 rps (not ApplyGuardrail provider capacity). R_gateway=3.01, 120s/cell × 5 reps.
q = frozen Function URL MiniLM. Tenant-split band is 0.40 ≤ q < 0.75 (A direct, B strong).
Isolation = checked vs starved among B required-strong. Paper cells are median [p25, p75].
MiniLM is an inexpensive risk estimator, not a low-latency guardrail. Do not retune τ.
Novelty is tenant isolation / B strong-check coverage, not better UAR_B.

## Tenant-split routing (pooled)

| policy | A:B | split_A | A direct | split_B | B need_strong | B checked |
| --- | --- | --- | --- | --- | --- | --- |
| always_strong | 90%:10% | 435 | 0 | 44 | 44 | 9 |
| always_strong | 70%:30% | 366 | 0 | 153 | 153 | 22 |
| always_strong | 50%:50% | 271 | 0 | 249 | 249 | 43 |
| always_strong | 30%:70% | 155 | 0 | 325 | 325 | 39 |
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

| policy | A:B | G_safe | G_safe_B | need_B | checked_B | starved_B | coverage | n_B_unsafe | UAR_B |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| always_strong | 90%:10% | 0.258 [0.242, 0.267] | 0.017 [0.017, 0.017] | 168 | 23 | 145 | 13.7% | 105 | 0.091 [0.074, 0.100] |
| always_strong | 70%:30% | 0.267 [0.225, 0.275] | 0.033 [0.025, 0.050] | 536 | 68 | 468 | 12.7% | 302 | 0.141 [0.121, 0.172] |
| always_strong | 50%:50% | 0.217 [0.208, 0.225] | 0.083 [0.058, 0.083] | 910 | 123 | 787 | 13.5% | 543 | 0.152 [0.127, 0.157] |
| always_strong | 30%:70% | 0.208 [0.200, 0.208] | 0.117 [0.117, 0.133] | 1270 | 157 | 1113 | 12.4% | 713 | 0.111 [0.109, 0.119] |
| risk_only | 90%:10% | 1.900 [1.842, 1.908] | 0.125 [0.100, 0.133] | 83 | 26 | 57 | 31.3% | 86 | 0.500 [0.500, 0.529] |
| risk_only | 70%:30% | 1.733 [1.675, 1.742] | 0.325 [0.300, 0.333] | 293 | 90 | 203 | 30.7% | 322 | 0.523 [0.357, 0.556] |
| risk_only | 50%:50% | 1.492 [1.483, 1.567] | 0.583 [0.575, 0.583] | 479 | 129 | 350 | 26.9% | 526 | 0.456 [0.436, 0.465] |
| risk_only | 30%:70% | 1.292 [1.233, 1.308] | 0.683 [0.675, 0.767] | 715 | 172 | 543 | 24.1% | 740 | 0.435 [0.413, 0.439] |
| load_aware | 90%:10% | 1.833 [1.808, 1.900] | 0.058 [0.058, 0.083] | 107 | 32 | 75 | 29.9% | 117 | 0.500 [0.263, 0.548] |
| load_aware | 70%:30% | 1.700 [1.683, 1.733] | 0.358 [0.342, 0.392] | 284 | 77 | 207 | 27.1% | 297 | 0.419 [0.380, 0.437] |
| load_aware | 50%:50% | 1.458 [1.458, 1.517] | 0.475 [0.450, 0.542] | 520 | 133 | 387 | 25.6% | 551 | 0.410 [0.402, 0.431] |
| load_aware | 30%:70% | 1.258 [1.250, 1.317] | 0.758 [0.675, 0.783] | 722 | 160 | 562 | 22.2% | 735 | 0.357 [0.351, 0.389] |
| proposed | 90%:10% | 2.008 [1.992, 2.067] | 0.108 [0.108, 0.133] | 116 | 76 | 40 | 65.5% | 104 | 0.667 [0.625, 0.722] |
| proposed | 70%:30% | 1.775 [1.742, 1.783] | 0.292 [0.267, 0.342] | 352 | 142 | 210 | 40.3% | 301 | 0.492 [0.481, 0.492] |
| proposed | 50%:50% | 1.567 [1.567, 1.683] | 0.517 [0.492, 0.517] | 570 | 176 | 394 | 30.9% | 515 | 0.392 [0.391, 0.413] |
| proposed | 30%:70% | 1.283 [1.258, 1.317] | 0.658 [0.642, 0.667] | 832 | 210 | 622 | 25.2% | 717 | 0.347 [0.329, 0.349] |

Coverage = checked / need among B required-strong. Headline is isolation, not UAR_B.
UAR_B mixes MiniLM FN (q below τ_B) and G_strong misses; it is not fail-open bypass.
