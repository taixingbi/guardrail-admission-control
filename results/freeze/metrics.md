# Main freeze (P1–P4)

Seeds requested: 500. Frozen prompts: **1888** (472 complete S0–S3 families).
Judge: `us.anthropic.claude-haiku-4-5-20251001-v1:0` (not Nova Micro / ApplyGuardrail / Maverick).
Judge agree: 1972/2000 (98.6%). The 28 misses are parse/empty responses (`label=None`), not flipped labels.

A family is kept only if all four variants pass structural checks and the judge.
Output: `data/runs/main`

S0/S1 are benign bank intents. S2/S3 are paired disallowed requests (not “harm related to cookies”).
