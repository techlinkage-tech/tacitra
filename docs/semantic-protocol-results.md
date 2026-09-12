# Semantic protocol v1 results

Preregistered decision: `does_not_support_semantic_protocol`.

> The frozen comparator stopped on Rust's zero accepted trials. The primary rule is unchanged; this report uses an identified post-run compatibility processor and marks Rust token-per-accepted metrics as not estimable.

| Comparison | Left accepted | Right accepted | Left tokens/accepted | Right tokens/accepted | Difference | Status |
|---|---:|---:|---:|---:|---:|---|
| tacitra-semantic vs tacitra-ordinary | 60/60 | 59/60 | 1065.87 | 911.90 | 153.97 | does_not_support |
| tacitra-semantic vs python-ordinary | 60/60 | 57/60 | 1065.87 | 714.40 | 351.46 | does_not_support |
| tacitra-semantic vs go-ordinary | 60/60 | 59/60 | 1065.87 | 861.19 | 204.68 | does_not_support |
| tacitra-semantic vs rust-ordinary | 60/60 | 0/60 | 1065.87 | not estimable | not estimable | not_estimable_zero_comparator_acceptance |

## Provider-token totals

| Representation | Total | Input | Visible output | Reasoning | Cached | Repair calls | Repair total |
|---|---:|---:|---:|---:|---:|---:|---:|
| python-ordinary | 40721 | 27773 | 7412 | 5536 | 0 | 10 | 8577 |
| go-ordinary | 50810 | 31789 | 12370 | 6651 | 0 | 16 | 15005 |
| rust-ordinary | 133935 | 92890 | 30638 | 10407 | 0 | 120 | 97634 |
| tacitra-ordinary | 53802 | 41863 | 7792 | 4147 | 0 | 2 | 2378 |
| tacitra-semantic | 63952 | 36721 | 6741 | 20490 | 0 | 11 | 11016 |

## Category results

| Category | Semantic accepted | Ordinary accepted | Semantic tokens/accepted | Ordinary tokens/accepted | Difference |
|---|---:|---:|---:|---:|---:|
| debug-repair | 30/30 | 29/30 | 980.90 | 958.90 | 22.00 |
| repository-change | 30/30 | 30/30 | 1150.83 | 866.47 | 284.37 |

## Interpretation

- Task capsule + task-scoped specification reduced measured input by 5,142 tokens (12.29%) versus Tacitra ordinary, but this combined system comparison does not isolate the specification alone.
- Compact typed edits averaged 186.05 bytes versus 333.38 ordinary diff bytes. Non-reasoning output was 6,741 versus 7,792 tokens, while semantic reasoning rose to 20,490 versus 4,147 tokens.
- Semantic repair used 11 calls and 11,016 tokens. Its repair-attempt input averaged 629.55 tokens versus 816.50 for two ordinary repairs, but no preregistered repair ablation exists, and stateless requests resend the initial prompt.
- Cached input was zero in every condition. Warm-session values remain static arithmetic projections, not real-model measurements.
- Static development ablations remain the only evidence for individually disabling task-scoped specification, semantic query, and typed patch; they must not be interpreted as model causal effects.

## Execution limitations

Rust accepted 0/60 because every compile command failed with `[Errno 2] No such file or directory: 'rustc'`; this is an execution-environment failure, not evidence about Rust generation quality. The raw run is retained and was not rerun. The frozen comparator then failed on the zero-acceptance token denominator; this report's compatibility processor preserves the primary rule and marks Rust token comparisons unestimable.

Provider totals, category details, repair usage, context-byte classifications, and limitations are retained in the machine-readable aggregate, comparison, and breakdown files.
