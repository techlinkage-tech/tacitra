# Status

Last updated: 2026-09-12

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
- Frozen `cross-language-v1` Phase A with 85 independent, previously unused language-neutral cases and 340 validated Tacitra/Python/Go/Rust reference fixtures.
- A common complete-source/unified-diff model protocol, seeded four-language interleaving, fake-provider dry run, reference-leakage checks, and immutable hashes for every cross-language input and analysis component.
- Preregistered three-comparison family-wise inference, case-cluster bootstrap, exact 5% success non-inferiority gate, failure-inclusive provider token accounting, and fixed result classifications.
- Completed the frozen `cross-language-v1` real-model run: 340/340 accepted, 373 attempts, 238,689 provider tokens, with retained raw, aggregate, comparison, event, and report artifacts.
- `does_not_support_advantage` cross-language decision: Tacitra passed success non-inferiority against Python, Go, and Rust but used more total tokens per accepted solution in every adjusted comparison.
- Version-one two-layer AI surface: deterministic source-free task capsules, compact typed body/expression edits, legacy-patch conversion, atomic checked application, ordinary source diffs, and bounded repair contexts.
- `ai.context`, `ai.context-size`, `ai.edit.validate`, `ai.edit.dry-run`, `ai.edit.apply`, `ai.edit.diff`, `ai.edit.compact`, `ai.edit.expand`, and `ai.repair-context` CLI operations plus three versioned JSON schemas.
- Six semantic-protocol development cases measured locally: 1,477.50 versus 2,181.33 `utf8-bytes/1` for semantic and ordinary Tacitra. This is a 32.27% byte reduction, not provider-token evidence; the semantic-query-only ablation was unfavorable on these small files.
- Completed the frozen `semantic-protocol-v1` run: 300/300 scheduled trials and 459 API attempts retained, 235 final acceptances, and 343,220 provider tokens.
- Tacitra semantic accepted 60/60 versus ordinary 59/60, but used 1,065.87 versus 911.90 total provider tokens per accepted solution; the preregistered decision is `does_not_support_semantic_protocol`.
- Semantic input fell 12.29% and patches averaged 186.05 versus 333.38 bytes, but higher reasoning and repair cost outweighed those savings. Cached input was zero.
- The Rust exploratory condition is invalid: all 60 trials failed because `rustc` was unavailable in the API-run environment. The frozen comparator also failed on its zero-acceptance denominator; an identified post-run compatibility analysis preserves the primary decision and marks Rust token comparisons not estimable.
- New replication runtime preflight resolves Python, Go, rustc, Cargo, Tacitra, and patch to validated absolute paths; checks the pinned Rust version, frozen hashes, required files, unused outputs, and temporary writes before provider construction; and strips credentials from child environments while retaining PATH.
- API-free recovery validation compiled and ran all 60/60 frozen Rust reference fixtures with rustc/Cargo 1.85.1 through the same isolated subprocess path intended for a future replication; provider calls were zero.
- Version-two comparison/report handling emits `null`/`not estimable` with `zero_accepted_trials`, retains failed-token and repair costs, and continues valid comparisons without changing the retained Phase D evidence.
- Semantic protocol v2 Phase 1 adds capsule+unified-diff, capsule+ordinary-source-fragment, and capsule+named-edit candidates while preserving ordinary Tacitra syntax and the compact-tuple control. Fragment and named inputs share the existing stale-hash, semantic-target, parse, type-check, formatter, execution, and human-diff boundary.
- The v2 pilot has 12 independent development cases, five conditions, two repetitions, a 120-trial seeded schedule, API-free reference/fake-provider validation, a 750,000-token combined stop, append-only evidence, and executable preregistration v3 `sha256:a888e06939a625fcd047fe649fbf7f0a79a4e7df27d3c51329d80b2965c55d85`. Preregistrations v1/v2 were abandoned before provider access after release checks found a missing CLI pin and then a conflict with the retained v1 AI-library pin; both remain retained for audit.
- Completed semantic-protocol-v2 Phase 3 confirmation on 60 unused cases: ordinary and capsule+fragment both accepted 60/60 with 100% compile@1/pass@1 and zero repairs. Tokens per accepted solution fell from 854.68 to 616.97 (-27.81% observed); the paired-bootstrap 95% interval for the difference was [-248.90, -226.38], and the zero-loss one-sided upper bound was 4.8703%.
- Phase 3's preregistered decision is `supports_semantic_protocol_v2`; 88,299 provider tokens were used in Phase 3 and 295,584 across pilot plus confirmation. This supports the capsule+fragment protocol over ordinary Tacitra for the frozen tasks/model only.

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
- Protocol-assisted cross-language evidence; equivalent semantic-query and structural-edit protocols are not available for Python, Go, and Rust.
- Warm-session/cache savings for `semantic-protocol-v1`; the completed run was stateless and reported zero cached input tokens.
- Causal real-model ablations separating task-scoped specification, semantic query, compact edit, and minimal repair. The completed run measured their combined system effect only.
- An executed environment-corrected replication. The draft recommends a new full 300-trial interleaved run; no model access is authorized or performed by the recovery work.
- Fully typed serialized HIR edits, cross-module atomic edits, capability-bearing core edits, or proof that source-free capsules are smaller than source for small modules.

## Next milestone

Freeze the documented full interleaved environment-corrected replication only after reviewing its reused-case limitation, estimated token budget, and account-specific price. Do not reinterpret or replace the retained `semantic-protocol-v1` run.
