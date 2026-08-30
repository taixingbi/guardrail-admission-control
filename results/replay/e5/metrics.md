# E5 fail-open vs fail-closed (freeze replay)

Proposed only. R_gateway=3.01, Rg=0.4, 60s/cell. q=e0a_live.
Fail-open disables deadline so exhaustion can bypass. Fail-closed keeps frozen B4.
Oracle cell archived in `results/replay/e5_oracle/`.

| mode | demand | G_safe | UAR | reject | bypass | bypass/need | compliant |
| --- | --- | --- | --- | --- | --- | --- | --- |
| proposed_fail_closed | 1.5 Rg | 2.450 | 0.000 | 0.183 | 0 | 0.00 | 1.000 |
| proposed_fail_closed | 2.0 Rg | 2.233 | 0.000 | 0.256 | 0 | 0.00 | 1.000 |
| proposed_fail_open | 1.5 Rg | 2.383 | 0.556 | 0.089 | 21 | 0.57 | 0.883 |
| proposed_fail_open | 2.0 Rg | 2.267 | 0.659 | 0.083 | 29 | 0.66 | 0.839 |

## Read

Live E0a q. Same 60 s cells as the oracle archive.

- Fail-closed UAR **0 / 0** at 1.5 and 2.0 Rg. Bypass 0. Compliant 1.000. Exhaustion is reject (`deadline` / `safety_floor`), never a skipped strong check.
- Fail-open UAR **0.556 / 0.659**. Bypass 21 / 29 (57% / 66% of required-strong). `G_safe` does not rise (2.38 / 2.27 vs closed 2.45 / 2.23) because a bypass is not policy-compliant goodput.
- Matches the oracle cell (open 1.5 had 20 bypasses; live q has 21). τ and `Rg` unchanged. Fail-closed stays the frozen B4 path.
