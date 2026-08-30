# E3 dynamic safety load (freeze replay)

R_gateway=3.01 rps, Rg=0.4 rps, 480s/policy. Mix 0.5→0.9→1.5→0.6 Rg.
Tenant A only. q=e0a_live. Live ApplyGuardrail, no Maverick.
Oracle cell archived in `results/replay/e3_oracle/`.

## Per phase

| policy | phase | demand | G_safe | UAR | reject | checked | starved |
| --- | --- | --- | --- | --- | --- | --- | --- |
| always_strong | 0-120s | 0.5 Rg | 0.167 | 0.000 | 0.945 | 0.13 | 316 |
| always_strong | 120-240s | 0.9 Rg | 0.150 | 0.020 | 0.947 | 0.12 | 316 |
| always_strong | 240-360s | 1.5 Rg | 0.150 | 0.000 | 0.947 | 0.12 | 316 |
| always_strong | 360-480s | 0.6 Rg | 0.175 | 0.000 | 0.939 | 0.12 | 315 |
| risk_only | 0-120s | 0.5 Rg | 2.758 | 0.000 | 0.086 | 0.58 | 13 |
| risk_only | 120-240s | 0.9 Rg | 2.700 | 0.000 | 0.102 | 0.59 | 15 |
| risk_only | 240-360s | 1.5 Rg | 2.508 | 0.000 | 0.166 | 0.45 | 33 |
| risk_only | 360-480s | 0.6 Rg | 2.733 | 0.000 | 0.089 | 0.66 | 11 |
| load_aware | 0-120s | 0.5 Rg | 2.792 | 0.000 | 0.075 | 0.63 | 10 |
| load_aware | 120-240s | 0.9 Rg | 2.742 | 0.000 | 0.089 | 0.62 | 12 |
| load_aware | 240-360s | 1.5 Rg | 2.400 | 0.000 | 0.202 | 0.41 | 43 |
| load_aware | 360-480s | 0.6 Rg | 2.750 | 0.000 | 0.083 | 0.60 | 12 |
| proposed | 0-120s | 0.5 Rg | 2.792 | 0.000 | 0.075 | 0.67 | 9 |
| proposed | 120-240s | 0.9 Rg | 2.567 | 0.000 | 0.147 | 0.45 | 29 |
| proposed | 240-360s | 1.5 Rg | 2.517 | 0.000 | 0.163 | 0.47 | 32 |
| proposed | 360-480s | 0.6 Rg | 2.775 | 0.000 | 0.075 | 0.70 | 8 |

## Overall

| policy | G_safe | UAR | reject | checked | starved |
| --- | --- | --- | --- | --- | --- |
| always_strong | 0.160 | 0.006 | 0.945 | 0.13 | 1263 |
| risk_only | 2.675 | 0.000 | 0.111 | 0.55 | 72 |
| load_aware | 2.671 | 0.000 | 0.112 | 0.52 | 77 |
| proposed | 2.663 | 0.000 | 0.115 | 0.53 | 78 |

## G_safe time series (10 s bins)

- **always_strong:** `0.20 0.10 0.30 0.20 0.20 0.00 0.20 0.10 0.20 0.20 0.20 0.10 0.10 0.30 0.20 0.20 0.10 0.10 0.20 0.20 0.20 0.00 0.00 0.20 0.20 0.20 0.00 0.20 0.30 0.20 0.10 0.00 0.10 0.10 0.30 0.10 0.20 0.10 0.30 0.10 0.20 0.20 0.20 0.10 0.30 0.10 0.00 0.30`
- **risk_only:** `2.70 3.00 2.70 2.80 2.80 2.80 2.90 2.80 2.40 2.50 2.70 3.00 2.80 2.70 2.90 2.70 2.50 2.70 2.80 2.60 2.50 2.60 2.90 2.70 2.00 2.70 2.40 2.60 2.40 2.30 2.90 2.80 2.50 2.40 2.70 2.40 2.70 2.80 2.80 2.60 3.00 2.80 2.40 2.90 2.80 2.70 2.60 2.70`
- **load_aware:** `3.00 2.80 2.80 2.70 2.90 2.40 3.00 2.60 2.90 2.70 2.80 2.90 2.70 2.70 2.80 2.80 2.50 2.90 2.70 2.60 2.90 2.80 2.80 2.70 2.40 2.70 3.00 2.40 2.20 2.00 2.50 2.20 2.50 2.30 2.10 2.50 2.90 2.80 2.70 2.60 3.10 2.80 2.70 2.60 2.70 2.70 2.90 2.50`
- **proposed:** `2.80 2.90 2.90 2.70 2.60 2.50 2.80 2.90 2.80 2.80 2.90 2.90 2.40 2.70 2.40 2.50 2.70 2.30 2.40 2.50 2.80 2.70 2.80 2.60 2.90 2.70 2.30 2.60 2.40 2.40 2.20 2.50 2.40 2.50 2.70 2.60 2.50 2.50 2.70 2.80 3.00 3.00 3.00 2.80 2.80 2.90 2.50 2.80`

## Read

Live E0a q. Same arrivals as the oracle archive (seeded mix). Proposed **2.79 → 2.57 → 2.52 → 2.78** at 0.5 / 0.9 / 1.5 / 0.6 Rg. UAR 0 in every proposed phase.

- Always-Strong stays ~0.16 (offers ~7.5 Rg). Adaptive policies track the mix and recover after overload.
- Proposed overload (240–360 s) G_safe 2.52 matches E6 Full. Deadline-reject trades a little goodput vs load-aware 2.40 in that window (load-aware queues, higher reject 0.202).
- Risk-Only / Load-Aware / Proposed overall G_safe 2.675 / 2.671 / 2.663 — same as oracle to two decimals. Always-Strong 0.160 vs 0.154 (timing).
- τ and `Rg` unchanged.
