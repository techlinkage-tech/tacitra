# Cross-language-v1 real-model results

Evidence: `measured`; model: `gpt-5.6-luna`; decision: `does_not_support_advantage`.

| Language | Accepted | compile@1 | pass@1 | Repairs median | Input mean | Output mean | Total / accepted |
|---|---:|---:|---:|---:|---:|---:|---:|
| tacitra | 85/85 | 98.8% | 94.1% | 0.00 | 669.82 | 281.12 | 950.94 |
| python | 85/85 | 100.0% | 91.8% | 0.00 | 376.46 | 219.15 | 595.61 |
| go | 85/85 | 88.2% | 83.5% | 0.00 | 389.38 | 244.67 | 634.05 |
| rust | 85/85 | 100.0% | 92.9% | 0.00 | 384.45 | 243.06 | 627.51 |

## Preregistered comparisons

Differences are Tacitra minus comparator. Negative token differences favor Tacitra.

| Comparator | Acceptance Δ | Token Δ | Adjusted upper | Tacitra losses | FWER upper | Status |
|---|---:|---:|---:|---:|---:|---|
| python | 0.000 | 355.33 | 473.12 | 0/85 | 0.05 | does_not_support |
| go | 0.000 | 316.89 | 441.44 | 0/85 | 0.05 | does_not_support |
| rust | 0.000 | 323.44 | 429.01 | 0/85 | 0.05 | does_not_support |

## Interpretation limits

- Case-cluster bootstrap treats each case as the resampling unit and does not treat repeated attempts as independent.
- The cases are fixed benchmark tasks rather than a random sample of all programming work.
- Differences in pretrained familiarity and native type systems are intentionally part of the language effect.
- Provider usage is authoritative; cached and reasoning tokens are informational subsets and are not added twice.
- Failed trials and every repair attempt remain in the primary token numerator.
- This primary evaluation does not use semantic queries or structural patches for any language.
