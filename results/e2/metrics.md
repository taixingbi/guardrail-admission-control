# E2 multi-tenant contention (frozen minilm-l12-h384 q, 5 reps)

Gateway safety budget Bg=0.4 rps (not ApplyGuardrail provider capacity). R_gateway=3.01, 120s/cell × 5 reps.
q = frozen Function URL MiniLM. Tenant-split band is 0.40 ≤ q < 0.75 (A direct, B strong).
Isolation = checked vs starved among B required-strong. Paper cells are median [p25, p75].
MiniLM is a screener; ApplyGuardrail is the authority. Do not retune τ on XSTest/WildGuardTest.

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
| load_aware | 30%:70% | 148 | 42 | 358 | 259 | 60 |
| proposed | 90%:10% | 491 | 491 | 47 | 47 | 29 |
| proposed | 70%:30% | 367 | 367 | 170 | 170 | 69 |
| proposed | 50%:50% | 253 | 253 | 270 | 270 | 87 |
| proposed | 30%:70% | 167 | 167 | 396 | 396 | 92 |

## Isolation (pooled B required-strong)

| policy | A:B | G_safe | G_safe_B | need_B | checked_B | starved_B | coverage | n_B_unsafe | UAR_B |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| always_strong | 90%:10% | 0.108 [0.100, 0.125] | 0.008 [0.000, 0.017] | 168 | 23 | 145 | 13.7% | 105 | 0.050 [0.000, 0.050] |
| always_strong | 70%:30% | 0.108 [0.100, 0.117] | 0.008 [0.008, 0.008] | 536 | 68 | 468 | 12.7% | 302 | 0.031 [0.017, 0.034] |
| always_strong | 50%:50% | 0.108 [0.092, 0.142] | 0.042 [0.033, 0.042] | 910 | 123 | 787 | 13.5% | 543 | 0.010 [0.008, 0.010] |
| always_strong | 30%:70% | 0.100 [0.092, 0.108] | 0.058 [0.033, 0.067] | 1270 | 157 | 1113 | 12.4% | 713 | 0.013 [0.007, 0.015] |
| risk_only | 90%:10% | 1.817 [1.758, 1.825] | 0.125 [0.092, 0.125] | 83 | 26 | 57 | 31.3% | 86 | 0.294 [0.167, 0.304] |
| risk_only | 70%:30% | 1.650 [1.633, 1.683] | 0.292 [0.292, 0.308] | 293 | 90 | 203 | 30.7% | 322 | 0.231 [0.130, 0.317] |
| risk_only | 50%:50% | 1.458 [1.442, 1.475] | 0.558 [0.558, 0.567] | 479 | 129 | 350 | 26.9% | 526 | 0.263 [0.262, 0.267] |
| risk_only | 30%:70% | 1.208 [1.133, 1.242] | 0.625 [0.600, 0.725] | 715 | 172 | 543 | 24.1% | 740 | 0.231 [0.223, 0.246] |
| load_aware | 90%:10% | 1.758 [1.733, 1.825] | 0.058 [0.050, 0.075] | 107 | 32 | 75 | 29.9% | 117 | 0.231 [0.158, 0.235] |
| load_aware | 70%:30% | 1.625 [1.592, 1.683] | 0.342 [0.333, 0.342] | 284 | 77 | 207 | 27.1% | 297 | 0.242 [0.220, 0.268] |
| load_aware | 50%:50% | 1.400 [1.383, 1.442] | 0.442 [0.433, 0.508] | 520 | 133 | 387 | 25.6% | 551 | 0.232 [0.210, 0.257] |
| load_aware | 30%:70% | 1.192 [1.175, 1.258] | 0.708 [0.625, 0.750] | 722 | 159 | 563 | 22.0% | 735 | 0.206 [0.202, 0.228] |
| proposed | 90%:10% | 1.983 [1.983, 2.033] | 0.083 [0.083, 0.117] | 116 | 76 | 40 | 65.5% | 104 | 0.222 [0.125, 0.250] |
| proposed | 70%:30% | 1.708 [1.708, 1.708] | 0.242 [0.242, 0.283] | 352 | 142 | 210 | 40.3% | 301 | 0.175 [0.154, 0.183] |
| proposed | 50%:50% | 1.492 [1.483, 1.600] | 0.442 [0.425, 0.458] | 570 | 176 | 394 | 30.9% | 515 | 0.140 [0.137, 0.183] |
| proposed | 30%:70% | 1.208 [1.208, 1.250] | 0.592 [0.592, 0.600] | 832 | 210 | 622 | 25.2% | 717 | 0.122 [0.095, 0.137] |

Coverage = checked / need among B required-strong. Headline is isolation, not UAR_B.
UAR_B mixes MiniLM FN (q below τ_B) and G_strong misses; it is not fail-open bypass.
