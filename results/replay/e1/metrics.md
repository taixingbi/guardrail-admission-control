# E1 static safety-load (freeze replay)

R_gateway=3.01 rps, Rg=0.4 rps, 40s/cell. q=e0a_live. Live ApplyGuardrail, no Maverick.
Oracle cell archived in `results/replay/e1_oracle/`.

| policy | demand | G_safe | UAR | reject | efficiency |
| --- | --- | --- | --- | --- | --- |
| always_strong | 0.50 Rg | 0.350 | 0.000 | 0.667 | 1.00 |
| always_strong | 1.00 Rg | 0.250 | 0.000 | 0.733 | 1.00 |
| always_strong | 1.50 Rg | 0.350 | 0.000 | 0.783 | 1.00 |
| risk_only | 0.50 Rg | 2.700 | 0.000 | 0.100 | — |
| risk_only | 1.00 Rg | 2.325 | 0.000 | 0.225 | — |
| risk_only | 1.50 Rg | 2.550 | 0.000 | 0.150 | — |
| load_aware | 0.50 Rg | 2.850 | 0.000 | 0.050 | — |
| load_aware | 1.00 Rg | 2.500 | 0.000 | 0.167 | — |
| load_aware | 1.50 Rg | 2.350 | 0.000 | 0.217 | — |
| proposed | 0.50 Rg | 2.750 | 0.000 | 0.083 | — |
| proposed | 1.00 Rg | 2.775 | 0.000 | 0.075 | — |
| proposed | 1.50 Rg | 2.400 | 0.000 | 0.200 | 1.00 |

## Read

Live E0a q. 40 s cells, Tenant A, no Maverick.

- Proposed **G_safe 2.75 / 2.78 / 2.40** at 0.5 / 1.0 / 1.5 Rg. Identical to the oracle archive. UAR 0.
- Always-Strong stays ~0.25–0.35 (offers ~7.5 Rg, deadline / queue timeout). Adaptive policies stay ~2.3–2.9.
- Risk-Only / Load-Aware / Proposed match the oracle table row-for-row. Always-Strong G_safe moves a little (sequential ApplyGuardrail vs the archived cell) but the gap vs Proposed is the same order.
- τ and `Rg` unchanged. Residual UAR is not a scheduler bypass; it is zero on this freeze.
