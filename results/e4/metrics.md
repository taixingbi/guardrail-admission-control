# E4 safety-capacity exhaustion (frozen minilm-l12-h384 q, 5 reps)

R_gateway=3.01 rps (constant), Bg=0.4 rps, 420s/policy × 5 reps.
Suspicious/adversarial mix 5% → 50% → 5%. Offered strong demand ≈ 0.38 → 3.76 → 0.38 Bg.
Tenant A only. q=frozen_g_light. Live ApplyGuardrail, no Maverick.
Phenomenon: safety-resource exhaustion at constant gateway RPS. Do not use E4 to claim Proposed dominates.
Paper overall cells are median [p25, p75]. Do not retune τ.

## Overall (median [IQR])

| policy | G_safe | UAR | reject |
| --- | --- | --- | --- |
| always_strong | 0.133 [0.133, 0.138] | 0.000 [0.000, 0.000] | 0.956 [0.954, 0.956] |
| risk_only | 2.183 [2.179, 2.224] | 0.048 [0.046, 0.057] | 0.263 [0.248, 0.267] |
| load_aware | 2.229 [2.181, 2.240] | 0.044 [0.041, 0.059] | 0.249 [0.246, 0.261] |
| proposed | 2.257 [2.250, 2.264] | 0.059 [0.058, 0.060] | 0.238 [0.233, 0.239] |

## Per phase (rep 0)

| policy | phase | sus | offered | G_safe | UAR | reject | checked | starved |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| always_strong | 0-120s | 5% | 0.38 Bg | 0.208 | 0.000 | 0.931 | 0.13 | 316 |
| always_strong | 120-300s | 50% | 3.76 Bg | 0.083 | 0.000 | 0.972 | 0.12 | 474 |
| always_strong | 300-420s | 5% | 0.38 Bg | 0.158 | 0.000 | 0.947 | 0.12 | 316 |
| risk_only | 0-120s | 5% | 0.38 Bg | 2.850 | 0.000 | 0.055 | 0.55 | 9 |
| risk_only | 120-300s | 50% | 3.76 Bg | 1.494 | 0.050 | 0.479 | 0.22 | 201 |
| risk_only | 300-420s | 5% | 0.38 Bg | 2.833 | 0.000 | 0.058 | 0.67 | 7 |
| load_aware | 0-120s | 5% | 0.38 Bg | 2.767 | 0.056 | 0.080 | 0.69 | 9 |
| load_aware | 120-300s | 50% | 3.76 Bg | 1.483 | 0.038 | 0.488 | 0.23 | 205 |
| load_aware | 300-420s | 5% | 0.38 Bg | 2.808 | 0.125 | 0.061 | 0.78 | 5 |
| proposed | 0-120s | 5% | 0.38 Bg | 2.817 | 0.045 | 0.064 | 0.78 | 5 |
| proposed | 120-300s | 50% | 3.76 Bg | 1.583 | 0.060 | 0.445 | 0.25 | 181 |
| proposed | 300-420s | 5% | 0.38 Bg | 2.842 | 0.125 | 0.050 | 0.72 | 5 |
