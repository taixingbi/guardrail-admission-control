# E0a G_light (minilm-l12-h384 Function URL)

Formal paper G_light. Laptop MiniLM is not this cell. τ=0.50 frozen. Do not retune.

| set | n | AUROC | AUPRC | recall@0.50 | FPR@0.50 | P50 ms | P95 ms | 0.40≤q<0.75 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| freeze | 1888 | 0.986 | 0.990 | 0.956 | 0.034 | 524.4 | 618.7 | 38 |
| xstest | 450 | 0.811 | 0.785 | 0.375 | 0.048 | 522.2 | 628.1 | 40 |
| wildguardtest | 1699 | 0.876 | 0.876 | 0.720 | 0.105 | 660.9 | 1355.5 | 142 |

## q histogram (rounded 0.1)

- **freeze:** `0.0:719 0.1:148 0.2:48 0.3:25 0.4:12 0.5:10 0.6:11 0.7:12 0.8:11 0.9:16 1.0:876`
- **xstest:** `0.0:263 0.1:58 0.2:10 0.3:15 0.4:10 0.5:15 0.6:6 0.7:17 0.8:14 0.9:22 1.0:20`
- **wildguardtest:** `0.0:678 0.1:196 0.2:67 0.3:45 0.4:39 0.5:48 0.6:38 0.7:36 0.8:57 0.9:94 1.0:401`

Tenant-split band 0.40≤q<0.75 across scored sets: **220** (both_direct=2306, both_strong=1511).

Freeze this q(x). E1–E6 replay only. Do not retune τ or Bg.
