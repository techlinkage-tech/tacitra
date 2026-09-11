# Confirmation-v1 real-model results

## Conclusion

The preregistered decision is `supports_adoption` for the Milestone 6 task-scoped context projections under this frozen experiment. Both conditions accepted 60/60 paired trials on the first attempt. Total provider tokens per accepted solution measured 3,506.73 for baseline and 2,102.68 for optimized, an observed reduction of 1,404.05 tokens (40.04%).

This conclusion compares Tacitra baseline context with Tacitra optimized context. It does not compare Tacitra with Python, Go, or Rust and does not establish performance for another model or broader programs.

## Frozen design

- Preregistration: [`confirmation-v1`](../benchmarks/confirmation/preregistration-v1.json), revision `sha256:54f9aebf43be32f3d5d08bf1fc29bb688abde108fc23ebfc6e93c8c2280d748d`.
- Model: `gpt-5.6-luna`; reasoning effort `low`; maximum output 2,048 tokens.
- Twenty previously unused cases: four each for syntax, generation, repository change, diagnostic repair, and external-module calls.
- Three repetitions per case, producing 60 pairs and 120 total trials in one seeded interleaved schedule.
- At most two repair rounds; all failed trials and attempts would remain in the primary numerator.
- Accuracy gate: optimized failures among baseline-accepted pairs must have a one-sided 95% upper bound no greater than 5%.
- Token gate: the paired-bootstrap 95% upper bound for optimized-minus-baseline total tokens per accepted solution must be below zero.
- Coverage gate: every category must contain an accepted optimized trial.

All 40 retained reference fixtures passed their acceptance commands before freezing. The runner rejected any later mismatch in model configuration, harness, prompt, case revisions, comparison implementation, or report implementation.

## Measured results

| Category | Baseline total / accepted | Optimized total / accepted | Difference | Reduction | Success |
|---|---:|---:|---:|---:|---:|
| Syntax | 2,912.42 | 1,959.92 | -952.50 | 32.70% | 12/12 vs 12/12 |
| Generation | 2,911.17 | 1,974.00 | -937.17 | 32.19% | 12/12 vs 12/12 |
| Repository change | 4,223.83 | 2,333.58 | -1,890.25 | 44.75% | 12/12 vs 12/12 |
| Diagnostic repair | 3,544.25 | 2,176.50 | -1,367.75 | 38.59% | 12/12 vs 12/12 |
| Interoperability | 3,942.00 | 2,069.42 | -1,872.58 | 47.50% | 12/12 vs 12/12 |
| **Overall** | **3,506.73** | **2,102.68** | **-1,404.05** | **40.04%** | **60/60 vs 60/60** |

All 120 trials had `compile_at_1 = true`, `pass_at_1 = true`, and zero repair rounds. The complete run consumed 336,565 provider-reported tokens. The seeded paired-bootstrap 95% interval for the primary difference was [-1,508.60, -1,297.57]. There were zero optimized losses among 60 baseline successes; the exact one-sided 95% accepted-loss upper bound was 4.8703%, within the frozen 5% limit. Every category had optimized acceptance.

## Retained evidence

- [`raw.jsonl`](../benchmarks/results/model-confirmation-v1/raw.jsonl): all inputs, model outputs, provider usage, generated artifacts, and validation outcomes.
- [`aggregate.json`](../benchmarks/results/model-confirmation-v1/aggregate.json): failure-inclusive group statistics.
- [`comparison.json`](../benchmarks/results/model-confirmation-v1/comparison.json): paired intervals and decision fields.
- [`report.md`](../benchmarks/results/model-confirmation-v1/report.md): generated compact report.

The API credential was not present in raw results. Provider totals count cached tokens rather than subtracting them. Prompt-section byte counts remain attribution aids and are not presented as model-token estimates.

## Remaining limits

The cases are intentionally small and use the implemented first-version feature set. All trials succeeding without repair means the experiment confirms input/output reduction and observed first-pass non-inferiority, but does not characterize difficult repair loops. Results are specific to the pinned model and configuration. Cross-model replication and more complex held-out changes remain separate research questions.
