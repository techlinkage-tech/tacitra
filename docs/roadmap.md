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

## Cross-language-v1 research track (complete)

- Freeze 85 new language-neutral cases spanning complete generation, local repository changes, and diagnostic repair.
- Validate equivalent Tacitra, Python, Go, and Rust reference fixtures under one common information-selection and response protocol.
- Preregister model settings, seeded interleaving, failure-inclusive metrics, family-wise comparisons, success non-inferiority, classifications, and all content hashes.
- Complete the fake-model dry run and leakage tests without calling the real model API.
- Run the frozen real-model evaluation once after Phase B approval and retain all evidence. (complete: `does_not_support_advantage`; all languages 85/85 accepted, while Tacitra used more tokens in every adjusted comparison)
- Protocol-assisted comparison remains future work until all four languages have equivalent mechanisms.

## Semantic-protocol-v1 research track (complete; does not support primary advantage)

- Preserve canonical Tacitra as the human surface and add a versioned AI surface for source-free task capsules, compact typed edits, and minimal repairs.
- Reaggregate cross-language evidence, measure three edit encodings and component ablations on six development cases, and retain unfavorable ablations.
- Freeze 60 unused independent cases, five workflows, 300 stateless calls, model settings, seeded schedule, graders, hashes, bootstrap comparison, and 5% acceptance non-inferiority rule.
- The frozen real-model run retained 300 trials and yielded `does_not_support_semantic_protocol`: semantic was fully accepted but used more total tokens per accepted solution than ordinary Tacitra.
- Warm-session values remain projected. Rust comparison is invalid because `rustc` was absent; any replication or causal ablation requires a new preregistration and cases.
- Environment recovery is implemented: tool/version preflight, credential-safe absolute-path subprocesses, 60/60 Rust reference prevalidation, timeout cleanup, and zero-acceptance-safe comparison/reporting.
- A full five-condition, 300-trial environment-corrected replication is recommended but remains an unfrozen draft with no model execution authorization.

## Milestone 10 — Familiar-output semantic protocol (complete)

- Keep public Tacitra syntax unchanged and compare task capsule plus unified diff, source fragment, named edit, and compact control against ordinary editing.
- Freeze a 12-case/120-trial development pilot before model access; select by success preservation, total provider tokens per accepted solution, then reasoning tokens.
- Run a separately frozen 60-case/120-trial confirmation only if the pilot winner beats ordinary Tacitra.
- Phase 1, the 120-trial pilot, and the separately frozen 60-case/120-trial confirmation are complete. Confirmation retained 60/60 acceptance in both conditions and measured 616.97 versus ordinary 854.68 total provider tokens per accepted solution, a 27.81% observed reduction. The preregistered decision supports this protocol relative to ordinary Tacitra for the frozen tasks and model, not against other languages.
