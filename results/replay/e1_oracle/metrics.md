# E1 static safety-load (freeze replay)

R_gateway=3.01 rps, Rg=0.4 rps, 40s/cell. Injected oracle q. Live ApplyGuardrail, no Maverick.

| policy | demand | G_safe | UAR | reject | efficiency |
| --- | --- | --- | --- | --- | --- |
| always_strong | 0.50 Rg | 0.425 | 0.000 | 0.667 | 1.00 |
| always_strong | 1.00 Rg | 0.450 | 0.000 | 0.725 | 1.00 |
| always_strong | 1.50 Rg | 0.275 | 0.000 | 0.792 | 1.00 |
| risk_only | 0.50 Rg | 2.700 | 0.000 | 0.100 | — |
| risk_only | 1.00 Rg | 2.325 | 0.000 | 0.225 | — |
| risk_only | 1.50 Rg | 2.550 | 0.000 | 0.150 | — |
| load_aware | 0.50 Rg | 2.850 | 0.000 | 0.050 | — |
| load_aware | 1.00 Rg | 2.500 | 0.000 | 0.167 | — |
| load_aware | 1.50 Rg | 2.350 | 0.000 | 0.217 | — |
| proposed | 0.50 Rg | 2.750 | 0.000 | 0.083 | — |
| proposed | 1.00 Rg | 2.775 | 0.000 | 0.075 | — |
| proposed | 1.50 Rg | 2.400 | 0.000 | 0.200 | — |
