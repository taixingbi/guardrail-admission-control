# E3 dynamic safety load (frozen minilm-l12-h384 q, 5 reps)

R_gateway=3.01 rps, Rg=0.4 rps, 480s/policy × 5 reps. Mix 0.5→0.9→1.5→0.6 Rg.
Tenant A only. q=frozen_g_light. Live ApplyGuardrail, no Maverick.
Paper overall cells are median [p25, p75]. Do not retune τ.

## Overall (median [IQR])

| policy | G_safe | UAR | reject |
| --- | --- | --- | --- |
| always_strong | 0.327 [0.327, 0.329] | 0.136 [0.126, 0.139] | 0.875 [0.875, 0.875] |
| risk_only | 2.621 [2.619, 2.640] | 0.510 [0.503, 0.531] | 0.070 [0.064, 0.075] |
| load_aware | 2.650 [2.625, 2.658] | 0.500 [0.481, 0.516] | 0.064 [0.064, 0.073] |
| proposed | 2.656 [2.642, 2.658] | 0.538 [0.527, 0.564] | 0.057 [0.054, 0.059] |

## Per phase (rep 0 shown in jsonl; pooled overall is the paper cell)

| policy | phase | demand | G_safe | UAR | reject | checked | starved |
| --- | --- | --- | --- | --- | --- | --- | --- |
| always_strong | 0-120s | 0.5 Rg | 0.358 | 0.107 | 0.873 | 0.00 | 362 |
| always_strong | 120-240s | 0.9 Rg | 0.317 | 0.143 | 0.875 | 0.00 | 361 |
| always_strong | 240-360s | 1.5 Rg | 0.317 | 0.103 | 0.875 | 0.00 | 361 |
| always_strong | 360-480s | 0.6 Rg | 0.367 | 0.038 | 0.875 | 0.00 | 360 |
| risk_only | 0-120s | 0.5 Rg | 2.692 | 0.613 | 0.055 | 0.00 | 45 |
| risk_only | 120-240s | 0.9 Rg | 2.658 | 0.541 | 0.061 | 0.00 | 44 |
| risk_only | 240-360s | 1.5 Rg | 2.467 | 0.450 | 0.105 | 0.00 | 64 |
| risk_only | 360-480s | 0.6 Rg | 2.667 | 0.594 | 0.058 | 0.00 | 44 |
| load_aware | 0-120s | 0.5 Rg | 2.733 | 0.519 | 0.055 | 0.00 | 41 |
| load_aware | 120-240s | 0.9 Rg | 2.717 | 0.562 | 0.047 | 0.00 | 36 |
| load_aware | 240-360s | 1.5 Rg | 2.350 | 0.411 | 0.136 | 0.00 | 82 |
| load_aware | 360-480s | 0.6 Rg | 2.700 | 0.533 | 0.056 | 0.00 | 41 |
| proposed | 0-120s | 0.5 Rg | 2.775 | 0.704 | 0.028 | 0.00 | 29 |
| proposed | 120-240s | 0.9 Rg | 2.558 | 0.509 | 0.075 | 0.00 | 53 |
| proposed | 240-360s | 1.5 Rg | 2.517 | 0.492 | 0.083 | 0.00 | 56 |
| proposed | 360-480s | 0.6 Rg | 2.775 | 0.692 | 0.025 | 0.00 | 29 |
