# E5 fail-open vs fail-closed (freeze replay)

Proposed only. R_gateway=3.01, Rg=0.4, 60s/cell.
Fail-open disables deadline so exhaustion can bypass. Fail-closed keeps frozen B4.

| mode | demand | G_safe | UAR | reject | bypass | bypass/need | compliant |
| --- | --- | --- | --- | --- | --- | --- | --- |
| proposed_fail_closed | 1.5 Rg | 2.450 | 0.000 | 0.183 | 0 | 0.00 | 1.000 |
| proposed_fail_closed | 2.0 Rg | 2.233 | 0.000 | 0.256 | 0 | 0.00 | 1.000 |
| proposed_fail_open | 1.5 Rg | 2.400 | 0.556 | 0.089 | 20 | 0.56 | 0.889 |
| proposed_fail_open | 2.0 Rg | 2.267 | 0.659 | 0.083 | 29 | 0.66 | 0.839 |
