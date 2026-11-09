# E3 dynamic safety load (frozen minilm-l12-h384 q, 5 reps)

R_gateway=3.01 rps, Bg=0.4 rps, 480s/policy × 5 reps. Mix 0.5→0.9→1.5→0.6 Bg.
Tenant A only. q=frozen_g_light. Live ApplyGuardrail, no Maverick.
Paper overall cells are median [p25, p75]. Robustness under dynamic mix, not Proposed-dominance.
Latency is safety-stage, not user E2E. UAR residual is MiniLM FN and/or G_strong miss.

## Overall (median [IQR])

| policy | G_safe | UAR | reject |
| --- | --- | --- | --- |
| always_strong | 0.167 [0.165, 0.181] | 0.000 [0.000, 0.000] | 0.945 [0.940, 0.945] |
| risk_only | 2.587 [2.573, 2.596] | 0.038 [0.031, 0.049] | 0.136 [0.133, 0.143] |
| load_aware | 2.600 [2.577, 2.604] | 0.052 [0.043, 0.061] | 0.130 [0.128, 0.139] |
| proposed | 2.642 [2.623, 2.646] | 0.042 [0.042, 0.044] | 0.117 [0.116, 0.123] |

## Per phase (rep 0 shown in jsonl; pooled overall is the paper cell)

| policy | phase | demand | G_safe | UAR | reject | checked | starved |
| --- | --- | --- | --- | --- | --- | --- | --- |
| always_strong | 0-120s | 0.5 Bg | 0.167 | 0.000 | 0.945 | 0.13 | 316 |
| always_strong | 120-240s | 0.9 Bg | 0.150 | 0.020 | 0.947 | 0.12 | 316 |
| always_strong | 240-360s | 1.5 Bg | 0.158 | 0.000 | 0.947 | 0.12 | 316 |
| always_strong | 360-480s | 0.6 Bg | 0.183 | 0.000 | 0.939 | 0.12 | 315 |
| risk_only | 0-120s | 0.5 Bg | 2.633 | 0.032 | 0.124 | 0.56 | 20 |
| risk_only | 120-240s | 0.9 Bg | 2.633 | 0.027 | 0.122 | 0.50 | 22 |
| risk_only | 240-360s | 1.5 Bg | 2.450 | 0.050 | 0.177 | 0.41 | 38 |
| risk_only | 360-480s | 0.6 Bg | 2.633 | 0.000 | 0.122 | 0.52 | 21 |
| load_aware | 0-120s | 0.5 Bg | 2.675 | 0.000 | 0.113 | 0.51 | 20 |
| load_aware | 120-240s | 0.9 Bg | 2.692 | 0.062 | 0.100 | 0.53 | 17 |
| load_aware | 240-360s | 1.5 Bg | 2.292 | 0.055 | 0.227 | 0.40 | 49 |
| load_aware | 360-480s | 0.6 Bg | 2.650 | 0.033 | 0.114 | 0.51 | 20 |
| proposed | 0-120s | 0.5 Bg | 2.767 | 0.037 | 0.080 | 0.66 | 10 |
| proposed | 120-240s | 0.9 Bg | 2.542 | 0.057 | 0.147 | 0.49 | 27 |
| proposed | 240-360s | 1.5 Bg | 2.517 | 0.051 | 0.155 | 0.46 | 30 |
| proposed | 360-480s | 0.6 Bg | 2.758 | 0.000 | 0.081 | 0.69 | 9 |
