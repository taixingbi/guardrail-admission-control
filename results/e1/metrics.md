# E1 static safety-load (scout)

`R_gateway=3.01` rps, `Rg=0.4` rps, 40s/cell, 120 requests/cell. Tenant A only. Injected oracle \(q\) (S0/S1=0, S2/S3=1). Live ApplyGuardrail, no Maverick.

Always-Strong offered demand is **always** \(R_{gateway}=7.5 R_g\). B2/B3/B4 offered strong demand follows the S2/S3 mix.

| policy | demand | \(G_{safe}\) | UAR | reject | oracle efficiency |
| --- | --- | --- | --- | --- | --- |
| always_strong | 0.50 \(R_g\) | 0.575 | 0.000 | 0.767 | 0.08 |
| always_strong | 1.00 \(R_g\) | 0.650 | 0.000 | 0.783 | 0.11 |
| always_strong | 1.50 \(R_g\) | 0.525 | 0.045 | 0.792 | 0.15 |
| risk_only | 0.50 \(R_g\) | 2.900 | 0.250 | 0.025 | 1.00 |
| risk_only | 1.00 \(R_g\) | 2.575 | 0.000 | 0.142 | 1.00 |
| risk_only | 1.50 \(R_g\) | 2.350 | 0.000 | 0.217 | 1.00 |
| load_aware | 0.50 \(R_g\) | 2.850 | 0.000 | 0.050 | 1.00 |
| load_aware | 1.00 \(R_g\) | 2.600 | 0.062 | 0.125 | 1.00 |
| load_aware | 1.50 \(R_g\) | 2.550 | 0.056 | 0.142 | 1.00 |
| proposed | 0.50 \(R_g\) | 2.875 | 0.200 | 0.033 | 1.00 |
| proposed | 1.00 \(R_g\) | 2.450 | 0.045 | 0.175 | 1.00 |
| proposed | 1.50 \(R_g\) | 2.525 | 0.000 | 0.158 | 1.00 |

Oracle efficiency = ApplyGuardrail calls on GT-unsafe / all ApplyGuardrail calls.

What this scout supports:

- Always-Strong collapses \(G_{safe}\) (~0.5 vs ~2.5) because it spends the 0.4 rps budget on S0/S1.
- B2/B3/B4 stay near offered goodput and use every strong slot on oracle-unsafe traffic.
- Residual UAR is mostly ApplyGuardrail `NONE` on weak S2 templates (cookies / photosynthesis), not scheduler bypass (`bypass_count=0`).
- Tenant B SLO is not in this experiment (E2).

Full 6-point sweep (`0.25…1.50`) and live G_light are not in this scout.
