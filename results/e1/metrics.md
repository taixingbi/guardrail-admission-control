# E1 static safety-load (frozen minilm-l12-h384 q, 5 reps)

R_gateway=3.01 rps, Bg=0.4 rps (gateway safety budget, not provider capacity), 40s/cell × 5 reps. q=frozen_g_light. Live ApplyGuardrail, no Maverick.
Paper cells are median [p25, p75]. Do not retune τ.
UAR = UAR_light + UAR_strong + UAR_bypass. Always-Strong UAR is G_strong miss, not MiniLM FN.
Efficiency = risk-required strong occupancy / all strong occupancy (Always-Strong waste is q < τ).

| policy | demand | G_safe | UAR | reject | efficiency |
| --- | --- | --- | --- | --- | --- |
| always_strong | 0.50 Bg | 0.200 [0.150, 0.200] | 0.000 [0.000, 0.000] | 0.933 [0.933, 0.950] | 0.06 [0.00, 0.18] |
| always_strong | 1.00 Bg | 0.175 [0.150, 0.200] | 0.000 [0.000, 0.000] | 0.942 [0.933, 0.950] | 0.24 [0.18, 0.29] |
| always_strong | 1.50 Bg | 0.175 [0.150, 0.200] | 0.000 [0.000, 0.000] | 0.942 [0.933, 0.950] | 0.24 [0.24, 0.29] |
| risk_only | 0.50 Bg | 2.675 [2.650, 2.700] | 0.000 [0.000, 0.000] | 0.108 [0.100, 0.108] | 1.00 [1.00, 1.00] |
| risk_only | 1.00 Bg | 2.550 [2.525, 2.575] | 0.056 [0.000, 0.074] | 0.142 [0.133, 0.150] | 1.00 [1.00, 1.00] |
| risk_only | 1.50 Bg | 2.350 [2.350, 2.450] | 0.000 [0.000, 0.045] | 0.208 [0.183, 0.217] | 1.00 [1.00, 1.00] |
| load_aware | 0.50 Bg | 2.700 [2.675, 2.750] | 0.000 [0.000, 0.000] | 0.100 [0.083, 0.108] | 1.00 [1.00, 1.00] |
| load_aware | 1.00 Bg | 2.475 [2.450, 2.475] | 0.050 [0.050, 0.067] | 0.167 [0.158, 0.167] | 1.00 [1.00, 1.00] |
| load_aware | 1.50 Bg | 2.300 [2.275, 2.375] | 0.000 [0.000, 0.045] | 0.233 [0.200, 0.242] | 1.00 [1.00, 1.00] |
| proposed | 0.50 Bg | 2.700 [2.700, 2.800] | 0.067 [0.000, 0.091] | 0.092 [0.067, 0.100] | 1.00 [1.00, 1.00] |
| proposed | 1.00 Bg | 2.525 [2.475, 2.625] | 0.050 [0.000, 0.056] | 0.150 [0.125, 0.158] | 1.00 [1.00, 1.00] |
| proposed | 1.50 Bg | 2.400 [2.375, 2.400] | 0.083 [0.045, 0.100] | 0.192 [0.183, 0.200] | 1.00 [1.00, 1.00] |
