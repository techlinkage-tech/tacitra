# ADR 0007: Use provider-metered paired model evaluation

- Status: Accepted
- Date: 2026-09-11

## Context

Milestone 6 measured smaller retained inputs with `utf8-bytes/1`, but could not establish whether an LLM remains accurate or requires fewer repair rounds. Model-specific tokenization cannot be inferred from bytes. Comparing separate agent implementations or only successful generations would confound the language representation with orchestration and selection effects.

## Decision

Use one stateless artifact-generation and repair loop for every language and Tacitra surface. Run baseline and optimized suites through the same pinned provider, endpoint, model, settings, prompt template, attempt budget, commands, and deterministic randomized schedule. Ask for one strict JSON envelope containing the candidate artifact; never include the retained reference artifact in model input.

Treat token usage returned by the provider response as the authoritative total. Retain input, output, total, cached-input, and reasoning-token fields exactly as reported. Store source-category sizes separately as UTF-8 bytes because provider usage does not attribute input tokens to individual prompt sections. Do not estimate that attribution.

Retain every attempt, model response, reconstructed input, validation failure, and token count in result schema version 3. Failed trials remain in the numerator of `total_tokens_per_accepted_solution`. Stop after the case's fixed repair budget. Refuse to overwrite raw runs and flush each completed trial so interrupted experiments retain auditable partial evidence.

Compare paired trials with the same case, representation, and repetition index. Report acceptance and token differences plus a seeded paired-bootstrap interval. Use existing cases only for pilot calibration; define new cases after the pilot and freeze them before confirmatory evaluation.

## Security

Read `OPENAI_API_KEY` only from the process environment and never serialize it. Reject endpoint URLs containing user information, query parameters, or fragments. Raw model inputs and outputs may contain repository data and must be treated as potentially sensitive experimental artifacts.

## Consequences

Model token totals and repair costs become directly measurable without pretending byte counts are model tokens. Exact per-section model-token attribution remains unavailable unless a separately pinned compatible tokenizer is added. Provider outages with no usage response abort the run rather than inventing a zero-cost failure; already flushed rows remain available but a partial run is not a complete comparison.
