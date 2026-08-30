# E3 dynamic safety load

R_gateway=3.01 rps, Rg=0.4 rps, 480s/policy. Mix 0.5→0.9→1.5→0.6 Rg.
Tenant A only. Injected oracle q. Live ApplyGuardrail, no Maverick.

## Per phase

| policy | phase | demand | G_safe | UAR | reject | checked | starved |
| --- | --- | --- | --- | --- | --- | --- | --- |
| always_strong | 0-120s | 0.5 Rg | 0.217 | 0.037 | 0.925 | 0.13 | 316 |
| always_strong | 120-240s | 0.9 Rg | 0.150 | 0.000 | 0.950 | 0.12 | 316 |
| always_strong | 240-360s | 1.5 Rg | 0.167 | 0.000 | 0.945 | 0.12 | 316 |
| always_strong | 360-480s | 0.6 Rg | 0.200 | 0.000 | 0.933 | 0.12 | 315 |
| risk_only | 0-120s | 0.5 Rg | 2.825 | 0.000 | 0.064 | 0.65 | 8 |
| risk_only | 120-240s | 0.9 Rg | 2.742 | 0.000 | 0.089 | 0.62 | 12 |
| risk_only | 240-360s | 1.5 Rg | 2.425 | 0.014 | 0.191 | 0.37 | 44 |
| risk_only | 360-480s | 0.6 Rg | 2.792 | 0.080 | 0.064 | 0.72 | 7 |
| load_aware | 0-120s | 0.5 Rg | 2.842 | 0.000 | 0.058 | 0.76 | 5 |
| load_aware | 120-240s | 0.9 Rg | 2.717 | 0.057 | 0.091 | 0.60 | 14 |
| load_aware | 240-360s | 1.5 Rg | 2.517 | 0.000 | 0.163 | 0.49 | 30 |
| load_aware | 360-480s | 0.6 Rg | 2.792 | 0.000 | 0.069 | 0.68 | 8 |
| proposed | 0-120s | 0.5 Rg | 2.850 | 0.000 | 0.055 | 0.75 | 5 |
| proposed | 120-240s | 0.9 Rg | 2.683 | 0.000 | 0.108 | 0.51 | 19 |
| proposed | 240-360s | 1.5 Rg | 2.283 | 0.000 | 0.241 | 0.37 | 55 |
| proposed | 360-480s | 0.6 Rg | 2.750 | 0.000 | 0.083 | 0.67 | 10 |

## Overall

| policy | G_safe | UAR | reject | checked | starved |
| --- | --- | --- | --- | --- | --- |
| always_strong | 0.183 | 0.006 | 0.938 | 0.13 | 1263 |
| risk_only | 2.696 | 0.020 | 0.102 | 0.53 | 71 |
| load_aware | 2.717 | 0.014 | 0.096 | 0.59 | 57 |
| proposed | 2.642 | 0.000 | 0.122 | 0.49 | 89 |

## Read

- Always-Strong is saturated at every mix: \(G_{safe}\approx 0.18\), reject \(\approx 94\%\). Sending every request to ApplyGuardrail wastes the 0.4 rps budget on safe traffic.
- Risk-Only / Load-Aware / Proposed all follow the mix: healthy at 0.5 \(R_g\), dip at 1.5 \(R_g\), recover at 0.6 \(R_g\).
- Proposed is the only policy with UAR = 0 in every phase. Risk-Only leaks in the 1.5 and 0.6 phases (ApplyGuardrail `NONE` on weak S2 plus a few admits). Load-Aware leaks in the 0.9 phase.
- Proposed's overload \(G_{safe}\) (2.28) is below Load-Aware (2.52) because it deadline-rejects when the strong path cannot make the 600 ms SLO. Reject at 1.5 \(R_g\): proposed 24% vs load-aware 16%. That is the fail-closed trade.

## G_safe time series (10 s bins)

- **always_strong:** `0.40 0.30 0.30 0.20 0.10 0.30 0.30 0.20 0.20 0.10 0.00 0.20 0.10 0.20 0.30 0.10 0.00 0.20 0.10 0.20 0.10 0.30 0.10 0.10 0.30 0.10 0.20 0.00 0.10 0.10 0.20 0.10 0.30 0.10 0.20 0.30 0.40 0.00 0.30 0.20 0.20 0.30 0.20 0.20 0.00 0.30 0.00 0.30`
- **risk_only:** `3.00 3.00 2.90 2.90 2.70 2.80 2.50 2.60 2.80 3.00 3.00 2.70 2.90 2.90 2.80 2.70 2.60 2.80 2.40 2.80 3.10 2.60 2.70 2.60 2.40 2.50 2.30 2.20 2.30 2.50 2.80 2.70 2.40 2.50 2.20 2.30 2.80 2.60 2.70 2.80 2.90 2.80 2.90 2.90 2.90 2.80 2.70 2.70`
- **load_aware:** `2.90 2.70 2.80 2.70 2.80 2.80 2.90 2.90 2.70 3.00 3.10 2.80 2.60 2.80 2.80 2.80 2.60 2.50 2.70 2.70 3.00 2.60 2.70 2.80 2.70 2.50 2.50 2.60 2.10 2.50 2.20 2.70 2.80 2.50 2.30 2.80 2.80 2.90 2.40 2.80 2.80 3.00 2.90 2.80 2.90 2.70 2.60 2.90`
- **proposed:** `2.90 2.90 2.80 2.70 2.80 2.60 2.80 2.80 3.00 2.90 3.00 3.00 2.60 2.60 2.50 2.80 2.70 2.60 2.90 2.80 2.80 2.40 2.70 2.80 2.50 2.30 2.10 2.30 2.30 2.00 2.50 2.40 2.30 2.40 2.20 2.10 2.70 2.80 2.50 2.70 2.80 2.80 2.80 2.70 2.90 2.80 2.80 2.70`
