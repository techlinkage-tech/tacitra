# ADR 0005: Separate static reference measurement from model evaluation

- Status: Accepted
- Date: 2026-09-11

## Context

Milestone 5 requires reproducible initial measurements across Python, Go, Rust, Tacitra source, semantic queries, and structural patches. No model API credential or installed model tokenizer is available in the current environment. The approved request forbids invented model measurements and permits a completed local-tokenizer static evaluation in this situation. The previous roadmap assigned bounded programs and effects to Milestone 5 and model evaluation to Milestone 6.

## Decision

Version benchmark cases and raw results independently as schema version 2. Every representation declares its exact artifact, specification, repository context, diagnostic context, setup, compile command, test command, output normalization, and shared integer acceptance contract. Commands are argument arrays rather than shell strings.

Pin the dependency-free tokenizer as `utf8-bytes/1`: each retained UTF-8 byte is one token. Label these runs `evidence: measured` and `measurement_mode: static_reference`, with `model: null` and empty model settings. These numbers are exact measurements for this tokenizer and the retained reference artifacts, but are not estimates of any LLM tokenizer or model-generation performance.

Count `AGENTS.md` as persistent instruction input for every trial. Count declared specification, repository, prompt, and supplied diagnostic artifacts separately. The reference artifact is output. `input_tokens` is the sum of all input categories; `total_tokens` is input plus output. `repair_tokens` is an informational output subset and remains zero for one-pass static reference trials.

Define the primary aggregate as:

```text
total_tokens_per_accepted_solution = sum(total_tokens for every trial) / accepted_trial_count
```

Failed trials stay in the numerator. The result is `null` when nothing is accepted. Report count, accepted/failed count, rates, mean, median, population variance, and wall-clock statistics. Retain one JSONL row per trial, including failures and bounded stdout/stderr.

Use three repetitions for the first retained static run. Hash the harness, complete case inputs, output artifacts, Cargo lockfile, and Tacitra CLI; record tool versions and unique trial IDs. Generate aggregate JSON and Markdown only from the retained JSONL.

## Consequences

The run is locally reproducible without network access or model credentials and clearly exposes Tacitra's current specification overhead. Byte counts cannot predict subword token counts, first-pass model success, or repair behavior. A future model run must use a separately pinned tokenizer/model/settings and `measurement_mode: model`; it must not be combined with this static aggregate.

This approved milestone moves evaluation forward to Milestone 5. Bounded collections and language-level effects/contracts move to the next milestone.
