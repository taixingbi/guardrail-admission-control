# External replay (G_light, frozen τ=0.50)

Native labels only. τ is not retuned.

| set | n | AUROC | AUPRC | recall@0.50 | FPR@0.50 |
| --- | --- | --- | --- | --- | --- |
| xstest | 450 | 0.928 | 0.833 | 0.985 | 0.272 |
| wildguardtest | 1699 | 0.908 | 0.898 | 0.918 | 0.219 |
| wildguardtest/adversarial | 796 | 0.861 | 0.799 | 0.909 | 0.321 |
| wildguardtest/vanilla | 903 | 0.935 | 0.941 | 0.925 | 0.124 |

## Read

- τ stays **0.50**. On WildGuard, 0.40 matches 0.50. 0.75 nudges recall 0.918→0.914 and FPR 0.219→0.210. That is not a retune.
- WildGuardTest cache is 1699 rows (754 harmful / 945 unharmful; 796 adversarial). Fetch wrote remapped `safe`/`unsafe`; the loader now accepts those as well as native `harmful`/`unharmful`.
- Transfer holds: AUROC 0.908 vs freeze ~1.0 and XSTest 0.928. G_light is a cheap risk estimator, not safety authority. The 62 harmful misses (stereotypes, copyright, “others”) are why required-strong stays fail-closed.
- FPR 0.219 is extra ApplyGuardrail on benign (207/945). Adversarial wraps drive most of it (FPR 0.321 vs vanilla 0.124). Same shape as XSTest exaggerated-safety (FPR 0.272).
- q is less binary than the freeze: 357 scores sit at 0.1 / 0.7 / 0.8 / 0.9. Tenant τ can matter here; it cannot on the P4 freeze.
- P50/P95 514 / 717 ms. Same latency story as E0a.

XSTest numbers are reused from the earlier cell (`results/external/xstest.jsonl`). WildGuard scores: `results/external/wildguardtest.jsonl`.
