# Cross-language-v1 real-model results

## Conclusion

The preregistered classification is `does_not_support_advantage`. Tacitra,
Python, Go, and Rust all accepted 85/85 cases, so Tacitra passed the 5% success
non-inferiority gate against every comparator. Tacitra nevertheless used more
provider-reported tokens per accepted solution than every comparator, and all
three Bonferroni-adjusted token intervals exclude zero in the unfavorable
direction.

This result does not contradict the earlier `confirmation-v1` result:
`confirmation-v1` showed that task-scoped context reduces tokens relative to a
larger Tacitra context. This experiment asks whether Tacitra source language,
without Tacitra-only semantic queries or structural patches, beats established
languages. Under these frozen small tasks and this model, it does not.

## Frozen condition

- Preregistration revision:
  `sha256:f55adce47d3e7734e0d756c3ee6dfb5fba946a8968667cc8d1e6b20aeef2d325`.
- Model: `gpt-5.6-luna`; reasoning effort `low`; maximum output 2,048 tokens.
- 85 independent cases and 340 language trials in one seeded interleaved order.
- One initial attempt and at most two repairs; all attempts remain in token cost.
- 20,000 case-cluster bootstrap draws and Bonferroni one-sided alpha `0.05/3`.
- No Tacitra semantic query or structural patch in the primary evaluation.

## Overall measured results

| Language | Accepted | compile@1 | pass@1 | Mean repairs | Input mean | Output mean | Reasoning mean | Total / accepted | Patch bytes mean | Time mean (s) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Tacitra | 85/85 | 98.82% | 94.12% | 0.071 | 669.82 | 281.12 | 174.13 | 950.94 | 252.82 | 3.79 |
| Python | 85/85 | 100.00% | 91.76% | 0.082 | 376.46 | 219.15 | 122.31 | 595.61 | 260.68 | 3.38 |
| Go | 85/85 | 88.24% | 83.53% | 0.165 | 389.38 | 244.67 | 137.82 | 634.05 | 214.86 | 6.27 |
| Rust | 85/85 | 100.00% | 92.94% | 0.071 | 384.45 | 243.06 | 133.95 | 627.51 | 240.09 | 3.56 |

There were 373 attempts and 33 repair rounds. Across all languages the run used
154,709 input, 83,980 output, and 238,689 total provider tokens. Reasoning tokens
were 48,298 and cached-input tokens were zero; both are informational subsets and
are not added again. The measured all-attempt total exceeded the 187,287-token
first-attempt-only Phase A estimate because repairs occurred.

Using the official rate available at execution time—$0.20 per million uncached
input tokens, $0.02 per million cached input tokens, and $1.20 per million output
tokens—the usage-derived cost estimate is $0.1317. This is an estimate from
provider usage, not a billing invoice.

## Preregistered comparisons

Differences are Tacitra minus comparator; positive token differences favor the
comparator.

| Comparator | Acceptance difference | Token difference | Paired 95% interval | Adjusted one-sided upper | Tacitra losses | Adjusted loss upper | Status |
|---|---:|---:|---:|---:|---:|---:|---|
| Python | 0.000 | +355.33 | [269.05, 463.76] | 473.12 | 0/85 | 4.7027% | `does_not_support` |
| Go | 0.000 | +316.89 | [221.19, 430.84] | 441.44 | 0/85 | 4.7027% | `does_not_support` |
| Rust | 0.000 | +323.44 | [251.66, 418.88] | 429.01 | 0/85 | 4.7027% | `does_not_support` |

The success gate passed because every exact adjusted upper bound is below 5%.
The token gate failed in the opposite direction for all three comparisons.

## Category results

Each entry is provider tokens per accepted solution; every language accepted
every case in every category.

| Category | Tacitra | Python | Go | Rust |
|---|---:|---:|---:|---:|
| Complete generation | 776.72 | 542.00 | 471.00 | 521.72 |
| Local repository change | 1,179.68 | 659.04 | 707.64 | 745.82 |
| Diagnostic repair | 902.64 | 587.71 | 729.32 | 618.75 |

Tacitra's largest observed disadvantage was in repository changes. Its longer
required language specification increased input tokens, while several repair
attempts also increased input, output, and reasoning usage. Generation was the
only category in which Tacitra had 100% pass-at-one; that accuracy benefit was not
large enough to offset its context and output cost.

## Retained evidence

- [`raw.jsonl`](../benchmarks/results/cross-language-v1/raw.jsonl), SHA-256
  `28b34c564562539fd5a2a288eda8bf719b63a50b4f2621f88387a9613acd445f`:
  all 340 inputs, outputs, provider usage records, 373 attempts, artifacts, and
  validation results.
- [`raw.jsonl.events.jsonl`](../benchmarks/results/cross-language-v1/raw.jsonl.events.jsonl),
  SHA-256 `3b46c28cdfbbb77a0317604d0023a9430d2095a3d5a9b453473241d10b2fa722`:
  one run start, 340 trial starts, and 340 trial completions; no interruption.
- [`aggregate.json`](../benchmarks/results/cross-language-v1/aggregate.json),
  SHA-256 `1d3ec19cdbe97560957235b95a429b598b97e3ebff9aceb24a7148bcb5215f75`.
- [`comparison.json`](../benchmarks/results/cross-language-v1/comparison.json),
  SHA-256 `38c04d624e88f9ed40f8583da20f94da5c2bca9656127209580ad72538688755`.
- [`report.md`](../benchmarks/results/cross-language-v1/report.md), SHA-256
  `ec5906d2dd9d245ad07b559b6e3bd467d28000728c98fe8cc5d79d6cc9f2e55f`.

The credential value, authorization header, and environment assignment are not
present in raw output. Existing `confirmation-v1` inputs and evidence remain
unchanged.

## Claims and limits

The data support the claim that, for this pinned model and these small common-
feature tasks, Tacitra preserved final success but required more total tokens than
Python, Go, and Rust when all languages used ordinary source or unified diffs.

The data do not establish performance on larger repositories, another model,
ecosystem-heavy tasks, multiple independent model samples per case, or equivalent
protocol-assisted editing. Pretraining familiarity, specification length, native
type systems, and compiler feedback are intentionally part of the practical
language effect, but they prevent attributing the difference to syntax alone.
