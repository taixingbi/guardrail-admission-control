# E2 multi-tenant contention (freeze replay)

Strong demand 1.3 Rg, R_gateway=3.01, 35s/cell.
Proposed reserves 40% of Rg for Tenant B. Other policies share one bucket.

| policy | A:B | G_safe | G_safe_B | need_B | strong_B | reject_need_B | UAR_B |
| --- | --- | --- | --- | --- | --- | --- | --- |
| always_strong | 90%:10% | 0.143 | 0.029 | 14 | 1 | 0.929 | 0.000 |
| always_strong | 70%:30% | 0.086 | 0.000 | 32 | 0 | 1.000 | 0.000 |
| always_strong | 50%:50% | 0.229 | 0.114 | 47 | 4 | 0.915 | 0.000 |
| always_strong | 30%:70% | 0.114 | 0.114 | 80 | 4 | 0.950 | 0.000 |
| risk_only | 90%:10% | 2.343 | 0.257 | 0 | 0 | 0.000 | 0.000 |
| risk_only | 70%:30% | 2.457 | 0.743 | 9 | 0 | 1.000 | 0.000 |
| risk_only | 50%:50% | 2.657 | 1.343 | 8 | 0 | 1.000 | 0.000 |
| risk_only | 30%:70% | 2.600 | 1.714 | 9 | 0 | 1.000 | 0.000 |
| load_aware | 90%:10% | 2.200 | 0.343 | 0 | 0 | 0.000 | 0.000 |
| load_aware | 70%:30% | 2.457 | 0.857 | 7 | 0 | 1.000 | 0.000 |
| load_aware | 50%:50% | 2.543 | 1.257 | 7 | 0 | 1.000 | 0.000 |
| load_aware | 30%:70% | 2.371 | 1.543 | 13 | 0 | 1.000 | 0.000 |
| proposed | 90%:10% | 2.486 | 0.086 | 5 | 0 | 1.000 | 0.000 |
| proposed | 70%:30% | 2.343 | 0.686 | 4 | 0 | 1.000 | 0.000 |
| proposed | 50%:50% | 2.457 | 1.257 | 12 | 0 | 1.000 | 0.000 |
| proposed | 30%:70% | 2.657 | 1.800 | 10 | 0 | 1.000 | 0.000 |
