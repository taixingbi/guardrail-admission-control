# E0c Maverick knee (short prompts)

ConverseStream, `max_tokens=64`, 20s per C. Prompt: cookie S0, one short paragraph.

| C | goodput rps | TTFT P50 | TTFT P95 | E2E P95 | throttle | healthy |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 2.10 | 252 | 327 | 556 | 0 | yes |
| 2 | **4.30** | 249 | 322 | 563 | 0 | yes |
| 4 | 2.00 | 1094 | 6697 | 6838 | 0.048 | **no** |

C=2 keeps TTFT P95 ≈ C=1 and doubles goodput. C=4 is the cliff (429s + multi-second TTFT).

This is **not** Paper 9's 512+128 scout (`C*=1`, `R_knee≈1.84`). Short safety prompts allow C=2.

- **C\\*** = 2
- **R_knee** = 4.30 rps
- **R_gateway** = **3.01 rps** (`0.7 × R_knee`)

E3/E4 offered load stays at `R_gateway`. Strong demand is still relative to experimental `B_g=0.4` rps, so `1.5 B_g=0.6` rps of ApplyGuardrail demand at a total ~3 rps mix.

Caveat: MiniLM Function URL G_light P50 is ~524 ms (P95 ~619 ms). The full user path is G_light + safety stage + Maverick; E0c only characterizes Maverick. E1–E6 P95 is safety-stage latency only.
