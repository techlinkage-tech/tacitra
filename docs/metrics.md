# Measurement contract

The primary unit is **total tokens per accepted solution or accepted change**. Every run records raw counts for a pinned tokenizer; counts from different tokenizers are never added or directly ranked.

For one attempt `a`:

```text
input(a) = persistent_instructions(a)
         + language_specification(a)
         + repository_context(a)
         + task_prompt(a)
         + compiler_and_test_feedback(a)

output(a) = generated_code_or_patch(a)
          + model_explanation(a)

total_tokens(run) = sum(input(a) + output(a) for a in attempts_through_acceptance)
```

The feedback from attempt `a` is counted as input only if it is actually supplied to a later model attempt. Tool output produced after the accepted attempt is reported separately as validation overhead. Cached prompt tokens remain tokens and are recorded as an informational subset of the input components, never added a second time or subtracted. If no attempt is accepted within the case budget, report failure plus tokens consumed; do not report a misleading “tokens per accepted change” value.

## Required raw fields

Each result pins the case revision, language, model identifier and settings, tokenizer name and revision, harness revision, attempt budget, and environment. Per attempt it stores every component above, compile and test outcomes, elapsed time, patch bytes, and diagnostic tokens. Aggregate reports include first-pass compile rate, test pass rate, acceptance rate, repair rounds, repository-context tokens, patch size, and wall-clock time.

## Comparability

- Use the same behavioral contract and acceptance tests for Tacitra, Python, Go, and Rust.
- Keep language-specific scaffolding visible and count any scaffolding shown to the model.
- Pin prompts, specifications, tool versions, tokenizers, models, sampling settings, and timeouts.
- Run paired cases with a declared repetition count and retain all raw results.
- Separate syntax compression, complete-program generation, repository modification, debugging/repair, and foreign-module tasks.
- Treat wall-clock time as secondary; correctness and tokens remain primary.

## Evidence labels

Every numeric result must be labeled exactly one of:

- `measured`: produced by the pinned harness from retained raw artifacts;
- `estimated`: derived without a complete reproducible run, with assumptions recorded;
- `projected`: a forward-looking target, never presented as observed performance.

Tables must not combine these labels in one aggregate. Missing data is `null`, never zero. Examples in documentation are labeled `illustrative` and are not benchmark evidence. A measured claim must link to the case, raw run file, tokenizer revision, model/settings, and a harness commit or retained content hash. Recomputed summaries remain measured only when their inputs are unchanged and retained.

## Harness field mapping

Benchmark schema version 2 records the persistent instruction, language specification, repository context, task, supplied diagnostics, output, and repair subsets as separate integer fields. For a retained row:

```text
input_tokens = instruction_tokens
             + specification_tokens
             + repository_context_tokens
             + task_tokens
             + diagnostic_tokens

total_tokens = input_tokens + output_tokens
```

`repair_tokens` is an informational subset of `output_tokens` from attempts after the first and is never added twice. The current static-reference run has no model attempts, feedback loop, or repair output, so `repair_tokens` and `repair_rounds` are zero rather than estimates. A missing inapplicable metric such as source-generation patch size is `null`.

Across trials, the primary metric is `sum(total_tokens for all successful and failed trials) / accepted_count`. It is `null` if the accepted count is zero. Reports also retain trial and success counts, compile-at-one and pass-at-one rates, arithmetic mean, median, population variance, patch-size statistics, and wall-clock statistics.

`static_reference` and `model` measurement modes cannot be aggregated together. The dependency-free `utf8-bytes/1` tokenizer counts one UTF-8 byte per token and supports reproducible static comparisons only; it is not an estimate of a model tokenizer.

## Optimization comparisons

An optimization run preserves the before raw rows and records every after row under the same tokenizer, attempt budget, prompt, acceptance command, and repetition count. Task-scoped specification or query profiles are versioned inputs and participate in the case revision. Intermediate stages may contain only the affected representations, but the final comparison must restore the complete representation set so overall success and token cost include unchanged controls.

Deterministic static-reference byte counts can establish representation-size changes and fixture acceptance, but cannot establish LLM pass-rate or repair effects. Zero within-group token variance is reported as deterministic, not as a confidence interval. Model accuracy, subword-token effects, and repair behavior remain `null`/unmeasured until a pinned model run is retained.

## Real-model result contract

Model result schema version 3 treats the provider response's `input_tokens`, `output_tokens`, and `total_tokens` as authoritative. Cached-input and reasoning counts are informational fields already contained in provider totals and are not added again. Each raw row retains the persistent instructions, reconstructed per-attempt input, response, decoded artifact, provider usage, compile/test result, feedback, and elapsed time. A request that returns no trustworthy usage aborts rather than recording invented counts.

Prompt-section attribution is recorded as measured UTF-8 bytes unless a separately pinned compatible tokenizer is available. Byte fields and provider token fields are never added or presented as the same unit. Model rows cannot be aggregated with static-reference rows.

Baseline and optimized model trials are paired by case, representation, and repetition index and interleaved with a fixed schedule seed. Paired bootstrap intervals report uncertainty for acceptance-rate and total-token-per-accepted-solution differences. A confirmatory adoption decision additionally requires a non-inferiority margin fixed before held-out results are examined.
