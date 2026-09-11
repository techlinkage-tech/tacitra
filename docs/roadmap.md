# Roadmap

## Milestone 0 — Foundation (complete)

- Establish vision, scope, metrics, evidence rules, and status tracking.
- Record the initial language decision.
- Define a versioned benchmark-case format and a four-language comparison fixture.
- Specify total-token accounting across specification, generation, diagnostics, and repair.

## Milestone 1 — Deterministic syntax front end (complete)

- Implement source-positioned tokens and AST for bindings, scalar literals, functions, calls, and basic operators.
- Implement parsing, recovery, deterministic human/JSON diagnostics, and canonical formatting.
- Provide `parse`, `fmt`, and `check` CLI commands.
- Verify valid and invalid parsing, parse-format-parse equivalence, formatter idempotence, and diagnostic stability.

## Milestone 2 — Typed semantics and execution (complete)

- Add primitive and algebraic types, explicit function signatures, lexical name resolution, and type checking.
- Establish source-positioned typed HIR with stable declaration-order symbol IDs.
- Add records, tagged unions, `Option`, `Result`, expression conditionals, and exhaustive matching.
- Interpret checked HIR through a zero-argument `main` and expose `run` in the CLI.
- Add positive and negative name, type, exhaustiveness, runtime, and diagnostic-contract tests.

This milestone is broader than originally planned because the approved implementation request moved the earlier Milestone 3 algebraic-data and interpreter work into Milestone 2.

## Milestone 3 — Semantic queries and structural patches (complete)

- Add formatting- and comment-stable semantic IDs for modules, types, symbols, locals, and expressions.
- Add bounded module, symbol, type, reference, and call-graph JSON queries.
- Add a versioned semantic-patch schema, SHA-256 stale detection, dry-run validation, checked application, explanations, and source diffs.
- Reject missing, ambiguous, stale, overlapping, kind-invalid, and compiler-invalid edits.

This milestone replaces the earlier agent-editing Milestone 4 because the approved implementation request moved that work forward.

## Milestone 4 — External module interoperability (complete)

- Define one versioned typed manifest for Python, Go, Rust, and future runtimes.
- Add one-shot standard-I/O JSON-RPC, timeouts, process cleanup, value validation, and structured failures.
- Add external API inspection, bounded semantic summaries, and Python/Go/Rust compatibility fixtures.

This milestone replaces the earlier bounded-program Milestone 4 because the approved implementation request moved the earlier interoperability work forward from Milestone 5.

## Milestone 5 — Token evaluation foundation and initial measurements (complete)

- Version comparable cases for syntax, generation, repository change, repair, and interoperability.
- Pin prompts, context categories, tokenizer, trials, model metadata, commands, and acceptance tests.
- Retain raw JSONL and regenerate machine-readable aggregates and a success/token report.
- Execute a three-repetition static-reference run without inventing unavailable model results.

This milestone replaces the earlier bounded-program Milestone 5 and moves the local portion of measured evaluation forward from Milestone 6. The approved request made reproducible measurement the primary Milestone 5 result.

## Milestone 6 — Measured optimization and confirmation (complete)

- Reaggregate the retained Milestone 5 baseline and isolate input/output components.
- Add task-scoped specification, edit-context, and external-call projections without changing public syntax.
- Preserve staged and final raw measurements, compare total tokens and acceptance, and record rejected alternatives.
- Add provider-metered paired generation/repair, run a pilot, freeze held-out cases and the success non-inferiority gate, and retain the 60-pair confirmation. (complete: `supports_adoption`)

Real-model evaluation was initially recorded as Milestone 7 after a follow-up request. The approved stabilization request makes the first public-ready experiment Milestone 7, so the completed model evaluation is retained as the confirmation phase of Milestone 6. No artifacts or claims changed.

## Milestone 7 — Stabilization and first public-ready experiment (complete)

- Add deterministic property testing for parser/formatter and structured patches, including invalid-input no-panic checks.
- Version public diagnostic/error schemas and document compatibility.
- Pin the Rust toolchain, improve CLI help, and provide installation, tutorial, sample, limitations, and security documentation.
- Inventory locked dependency licenses and confirm the existing repository MIT license.
- Provide one offline release-readiness command that validates examples, tests, schemas, licenses, frozen evidence, and benchmark reaggregation.

## Milestone 8 — Bounded programs and explicit effects (planned)

- Add bounded collection operations.
- Add language-level tests and basic contracts.
- Define explicit language effects and capabilities while preserving deterministic execution.

## Milestone 9 — Cross-model and repair-heavy replication (planned)

- Repeat the paired design with separately frozen models and harder cases that provoke repair loops.
- Test profile-selection accuracy when task coverage is less obvious.
- Publish model-specific results without pooling incompatible model/tokenizer conditions.
