# E5 fail-open vs fail-closed

Proposed only. R_gateway=3.01, Rg=0.4, 60s/cell.
Fail-open disables deadline so exhaustion can bypass. Fail-closed keeps frozen B4 (deadline + safety_floor).

| mode | demand | G_safe | UAR | reject | bypass | bypass/need | checked |
| --- | --- | --- | --- | --- | --- | --- | --- |
| fail-closed | 1.5 Rg | 2.317 | 0.000 | 0.228 | 0 | 0.00 | 16 |
| fail-closed | 2.0 Rg | 2.233 | 0.022 | 0.250 | 0 | 0.00 | 19 |
| fail-open | 1.5 Rg | 2.467 | 0.438 | 0.100 | 14 | 0.44 | 18 |
| fail-open | 2.0 Rg | 2.100 | 0.704 | 0.089 | 36 | 0.67 | 18 |

## Read

- Fail-closed never bypasses. UAR is 0 at 1.5 \(R_g\) and 2.2% at 2.0 \(R_g\) (ApplyGuardrail `NONE` on weak S2).
- Fail-open bypasses 44% / 67% of required-strong requests. Every bypass is GT-unsafe, so UAR is 44% / 70%.
- \(G_{safe}\) does not improve under fail-open (bypass is non-compliant, so it is not goodput). The open path only admits unsafe traffic the closed path would reject.
