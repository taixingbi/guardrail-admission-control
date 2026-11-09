# E0b ApplyGuardrail capacity

Duration 12s per C. Guardrail `wmw1sagwsxi7` v1.

| C | goodput rps | P50 ms | P95 ms | throttle | error | healthy |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 5.25 | 181 | 254 | 0.000 | 0.000 | True |
| 2 | 11.67 | 175 | 242 | 0.000 | 0.000 | True |
| 4 | 24.92 | 145 | 222 | 0.000 | 0.000 | True |
| 8 | 51.42 | 141 | 231 | 0.000 | 0.000 | True |
| 16 | 101.67 | 141 | 231 | 0.000 | 0.000 | True |
| 32 | 110.17 | 147 | 806 | 0.001 | 0.000 | True |

**B_g^{raw}** = 101.67 rps at C=16
**Experimental \(B_g\)** = 0.4 rps (gateway safety budget, not provider capacity).

