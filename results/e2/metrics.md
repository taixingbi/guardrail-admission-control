# E2 multi-tenant contention (scout)

Strong demand 1.3 Rg, R_gateway=3.01, 35 s/cell, concurrent open-loop.
Proposed reserves 40% of Rg for Tenant B. Other policies share one bucket.
Bypass = 0 in every cell. Residual UAR is ApplyGuardrail `NONE` on weak S2, not scheduler bypass.

`G_safe_B` is dominated by safe-direct traffic and is not the isolation metric.
Headline: among Tenant B requests that **required** strong, how many received ApplyGuardrail (`checked`) vs were dropped before the API (`starved`: deadline / strong_full / safety_floor).

| policy | A:B | G_safe | G_safe_B | need_B | checked_B | starved_B | UAR_B |
| --- | --- | --- | --- | --- | --- | --- | --- |
| always_strong | 90%:10% | 0.200 | 0.029 | 10 | 2 | 8 | 0.000 |
| always_strong | 70%:30% | 0.314 | 0.057 | 32 | 3 | 29 | 0.000 |
| always_strong | 50%:50% | 0.143 | 0.086 | 50 | 8 | 42 | 0.000 |
| always_strong | 30%:70% | 0.114 | 0.086 | 85 | 11 | 74 | 0.000 |
| risk_only | 90%:10% | 2.457 | 0.200 | 0 | 0 | 0 | 0.000 |
| risk_only | 70%:30% | 2.371 | 0.657 | 10 | 5 | 5 | 0.000 |
| risk_only | 50%:50% | 2.543 | 1.229 | 9 | 4 | 5 | 0.000 |
| risk_only | 30%:70% | 2.514 | 1.571 | 13 | 6 | 7 | 0.077 |
| load_aware | 90%:10% | 2.429 | 0.257 | 3 | 2 | 1 | 0.000 |
| load_aware | 70%:30% | 2.486 | 0.743 | 5 | 2 | 3 | 0.000 |
| load_aware | 50%:50% | 2.800 | 1.457 | 3 | 2 | 1 | 0.000 |
| load_aware | 30%:70% | 2.486 | 1.686 | 13 | 7 | 6 | 0.000 |
| proposed | 90%:10% | 2.543 | 0.171 | 1 | 1 | 0 | 0.000 |
| proposed | 70%:30% | 2.457 | 0.571 | 3 | 2 | 1 | 0.000 |
| proposed | 50%:50% | 2.371 | 1.086 | 14 | 7 | 7 | 0.000 |
| proposed | 30%:70% | 2.543 | 1.657 | 14 | 7 | 7 | 0.000 |

## Read

- Always-Strong offers 7.5 Rg. Deadline rejects starve everyone; B is not isolated.
- Risk-Only / Load-Aware share one 0.4 rps bucket. About half of B's required-strong requests are `strong_full` or deadline.
- Proposed at 90:10 and 70:30 checks a higher fraction of B's required-strong requests. At 50:50 and 30:70, B's own strong demand (0.26–0.36 rps) exceeds the 0.16 rps reservation, so leftover demand still starves — expected.
- 90:10 cells have 0–3 B-unsafe requests in 35 s. This is a mechanism scout, not a paper table. A 120 s cell would yield ~6 B-unsafe at 90:10.

Limiter: unused reserved tokens are stealable only if that tenant never appeared in the cell (keeps E1 Tenant-A-only at full Rg). Once B appears, its 40% floor is not stolen.
