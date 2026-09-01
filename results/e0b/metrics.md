# E0b ApplyGuardrail capacity

Duration 12s per C. Guardrail `bklyj6c5nrb5` v1. Prompt = S1-length cookie text.

| C | goodput rps | P50 ms | P95 ms | throttle | error | healthy (no 429) | P95-stable |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 4.42 | 217 | 317 | 0 | 0 | yes | yes |
| 2 | 8.50 | 217 | 308 | 0 | 0 | yes | yes |
| 4 | 15.83 | 238 | 333 | 0 | 0 | yes | yes |
| 8 | 33.17 | 232 | 334 | 0 | 0 | yes | yes |
| 16 | 71.42 | 205 | 356 | 0 | 0 | yes | yes |
| 32 | 105.58 | 214 | 718 | 0 | 0 | yes | **no** |

No `ThrottlingException` even at C=32 (burst above the documented 50 rps quota). The usable cliff is **latency**: P95 stays ~310–360 ms through C=16, then doubles at C=32.

- **\(B_g^{\mathrm{raw}}\)** = **71.4 rps** at C=16 (best goodput with P95 ≤ 1.5 × C=1 P95).
- C=32 is not the operating point (P95 718 ms).
- **Experimental \(B_g\)** = **0.4 rps** (gateway token-bucket). This is an org safety budget so E1–E4 can saturate G_strong without first hitting Maverick (~1.8 rps) or raw ApplyGuardrail (~71 rps).

ApplyGuardrail P50 (~215 ms) is lower than MiniLM Function URL G_light P50 (~524 ms). MiniLM is an inexpensive risk estimator, not a low-latency guardrail. Raw G_strong is not the bottleneck; the scheduled resource is the gateway quota.
