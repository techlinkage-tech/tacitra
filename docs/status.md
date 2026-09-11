# Status

Last updated: 2026-09-11

## Implemented

- Milestone 0 measurement contract, evidence rules, benchmark schemas, and comparable fixture layout.
- Deterministic lexer/parser, source-positioned AST, canonical formatter, typed HIR, name/type checking, and checked interpreter.
- Primitive and algebraic types, records, tagged unions, expression conditionals, and exhaustive matching.
- CLI `parse`, `fmt`, `check`, and `run` commands with stable human and JSON diagnostics.
- Non-semantic `//` line comments.
- SHA-256 semantic module hashes computed from canonical parsed source.
- Deterministic IDs for modules, types, public symbols, parameters, locals, pattern bindings, and expressions. IDs exclude positions, formatting, comments, and expression contents.
- `module.summary`, `symbol.describe`, `symbol.references`, and `type.describe` deterministic JSON queries without full-source responses.
- Function summaries containing parameters, return type, `Result` failure type, effects, contracts, calls, and bounded expression metadata.
- Version-one JSON structural patches with `replace_function_body` and `replace_expression`.
- `patch.validate` dry runs and atomically written `patch.apply` operations.
- SHA-256 stale rejection; missing, ambiguous, overlapping, target-kind-invalid, malformed, syntactically invalid, and ill-typed patch rejection.
- Human-reviewable operation descriptions and unified source diffs.
- Schema, ID stability, deterministic query, patch round-trip, invalid patch, dry-run, CLI, compiler, and runtime tests.
- One versioned typed external-module manifest shared by Python, Go, and Rust fixtures.
- Strict boundary validation for booleans, fixed-width integers, floats, strings, bytes, lists, records, options, results, and opaque handles.
- One-shot standard-I/O JSON-RPC execution with configurable timeout, child termination/reaping, response validation, and structured foreign failures.
- Explicit effect/capability grants plus rejection of worker-reported undeclared or ungranted activity.
- `interop.inspect`, `interop.call`, `external.summary`, and `external.describe` CLI operations.
- Deterministic external API summaries without worker source or launch commands.
- Version-two benchmark case and result schemas covering five distinct task categories.
- Dependency-free benchmark CLI for validation, static measurement, raw JSONL retention, aggregation, and Markdown reporting.
- Fixed prompts, common acceptance tests, language profiles, context classifications, attempt budgets, hashes, tool versions, and trial IDs.
- Python, Go, Rust, Tacitra source, bounded semantic-query, and structural-patch reference fixtures.
- Measured `utf8-bytes/1` static-reference run with 63/63 accepted validation trials and retained raw/aggregate/report artifacts.
- Aggregates with success counts/rates, mean, median, population variance, patch size, wall time, and total tokens per accepted solution including failure cost.
- Milestone 6 task-scoped Tacitra specification profiles with an explicit coverage/fallback rule.
- Deterministic `symbol.edit-context` and `external.call-context` projections for bounded edit and foreign-call tasks.
- Preserved before, specification-only intermediate, and final static-reference raw measurements plus a reproducible comparison CLI.
- Measured final static suite: 642,129 versus 738,105 byte-tokens, 63/63 accepted in both; this is static `utf8-bytes/1` evidence, not an LLM-token claim.
- Real-model result schema version 3 and an OpenAI Responses API adapter using environment-only credentials.
- A common model artifact/repair loop that never sends reference solutions, reuses existing acceptance commands, retains every attempt, and refuses raw-result overwrites.
- Seeded interleaved baseline/optimized schedules, provider-metered token accounting, failure-inclusive aggregation, paired bootstrap comparison, and optional preregistered non-inferiority decisions.
- Fake-model tests covering provider usage parsing, reference-solution isolation, successful generation, repair, failure cost, deterministic comparison, and invalid output.
- First retained `gpt-5.6-luna` paired pilot: baseline and optimized both 3/3 compile@1/pass@1 with zero repairs; provider-token primary metric 4,228.33 → 2,295.00 (-45.72% observed).
- Preregistered confirmation suite with 20 unused cases, four per category, three repetitions, immutable input hashes, and 40/40 validated reference fixtures.
- Completed 60-pair confirmation: baseline and optimized both 60/60 compile@1/pass@1, zero repairs, and 3,506.73 → 2,102.68 provider tokens per accepted solution (-40.04%).
- `supports_adoption` decision: token-difference 95% interval [-1,508.60, -1,297.57], accepted-loss one-sided 95% upper bound 4.8703% within the frozen 5% limit, and success in every category.
- Experimental version 0.1.0 with a pinned Rust 1.85.1 toolchain and complete top-level CLI help/version output.
- Version-one compiler diagnostic, agent-error, interop-error, semantic-patch, and interop-manifest JSON schemas with documented compatibility rules.
- Deterministic generated property corpora for parse-format-parse, formatter idempotence, structured patch round trips, malformed source/JSON, and invalid replacement no-panic behavior.
- Clean-environment installation guide, minimal tutorial, executable sample project, security boundary, known limitations, and benchmark reproduction guide.
- Confirmed existing MIT repository license plus locked third-party license metadata inventory and automated missing-license check.
- One offline `python3 scripts/release_check.py` gate covering formatting, lint, all tests, examples, interoperability, frozen confirmation inputs, and byte-identical result regeneration.

## Deliberately not implemented

- Natural-language or model-generated patches, vector databases, IDE plugins, or network services.
- Multi-file modules, multi-repository indexing, arbitrary refactoring, symbol rename patches, or import updates.
- ID persistence across symbol renames or arbitrary surrounding expression restructuring.
- User-defined generics, traits, advanced inference, macros, full closures, concurrency, or native code generation.
- Bounded collections in Tacitra source, language-level test/contract declarations, or effects/capability syntax. Tacitra source queries report empty effects/contracts until these exist.
- Native FFI, persistent worker pools, callbacks, streaming RPC, or external calls directly from Tacitra source programs.
- Operating-system sandbox enforcement; effect observation is cooperative and manifests/commands are trusted project configuration.
- Any claim that `utf8-bytes/1` predicts LLM subword-token savings, model pass rates, or repair behavior.
- Cross-model evidence, larger programs, and repair-heavy confirmation; the retained confirmation is specific to `gpt-5.6-luna` and small first-version tasks.

## Next milestone

After a human release decision, proceed to bounded programs/effects or preregister a cross-model and repair-heavy replication without changing the accepted Milestone 6 profiles.
