# AGENTS.md

## Project objective

Build an experimental programming language optimized for minimizing the total LLM tokens required to create, understand, modify, validate, and repair correct programs.

The primary metric is total tokens per accepted solution or accepted change, including:

- persistent instructions;
- language specification supplied to the model;
- repository context read by the model;
- generated code or patches;
- compiler and test feedback;
- retries and repair attempts.

Do not optimize only for character count, source line count, or the token count of a successful final program.

## Product principles

- Treat correctness per token as more important than brevity alone.
- Prefer one canonical representation for each program meaning.
- Avoid implicit behavior, ambiguous grammar, context-sensitive syntax, and redundant syntax alternatives.
- Keep the human-facing syntax familiar enough for existing coding models to transfer knowledge from Python, TypeScript, Go, and Rust.
- Use a typed canonical AST or IR as the authoritative semantic representation.
- Design a compact AI editing protocol based on stable semantic IDs and structural patches.
- Make compiler diagnostics deterministic, structured, concise, and actionable.
- Make type, dependency, effect, ownership, and capability information queryable without reading entire source files.
- Keep external effects explicit.
- Treat tests, contracts, and machine-checkable intent as part of the language design.
- Design interoperability around small typed interface manifests rather than exposing complete foreign source trees.

## Current scope

The first usable version should contain only:

- modules;
- immutable local bindings;
- functions;
- primitive scalar types;
- records;
- tagged unions;
- `Option` and `Result`;
- conditionals;
- pattern matching;
- bounded collection operations;
- explicit effects;
- tests and basic contracts;
- a deterministic formatter;
- structured compiler diagnostics;
- an interpreter for the core IR;
- a CLI suitable for use by coding agents.

The first version does not require:

- a native-code backend;
- garbage-collector optimization;
- macros;
- classes or inheritance;
- operator overloading;
- unrestricted metaprogramming;
- a public package registry;
- transparent compatibility with arbitrary foreign objects.

Do not expand these non-goals without recording a design decision and demonstrating why the expansion is required for the current milestone.

## Source of truth

Use the following hierarchy:

1. Tests and accepted benchmark fixtures define required observable behavior.
2. `docs/language/` defines accepted language semantics.
3. `docs/decisions/` records design decisions and their rationale.
4. `docs/roadmap.md` defines milestone order.
5. `docs/status.md` records implemented and incomplete capabilities.

When behavior and documentation disagree, stop extending the feature. Determine whether the implementation or specification is wrong, then update both in the same change.

Do not silently change syntax or semantics.

## Work procedure

Before implementing a task:

1. Read `docs/status.md` and the relevant section of `docs/roadmap.md`.
2. Read only the specification files relevant to the requested change.
3. Inspect the existing implementation and tests before proposing a new abstraction.
4. State the smallest vertical slice that can produce executable or measurable behavior.
5. Implement that slice completely.

During implementation:

- Keep changes scoped to the current milestone.
- Prefer simple, explicit data structures over premature abstraction.
- Preserve deterministic output.
- Do not add a dependency when a small stable implementation is reasonable.
- Do not duplicate parser, type-system, or diagnostic rules across crates.
- Assign stable error codes to user-visible compiler failures.
- Provide machine-readable diagnostic output in addition to human-readable output.
- Do not claim token savings without reproducible benchmark results.
- Record material language-design choices as short ADRs in `docs/decisions/`.

After implementation:

1. Run the focused tests for the changed component.
2. Run integration tests if parser, AST, type checking, diagnostics, or runtime behavior changed.
3. Run formatter and static checks.
4. Run the relevant token benchmark when representation, diagnostics, prompts, or AI editing behavior changed.
5. Update `docs/status.md`.
6. Report completed behavior, test results, benchmark results, and remaining limitations concisely.

## Language-design rules

- Every valid source file has one canonical formatted representation.
- Formatting must be idempotent.
- Parsing formatted source must preserve semantic structure.
- Avoid optional punctuation unless it produces a measured token benefit without increasing errors.
- Avoid multiple equivalent spellings for the same construct.
- Avoid implicit imports and hidden global state.
- Avoid implicit numeric or nullable conversions.
- Represent recoverable failures with `Result`.
- Represent absence with `Option`.
- Model external actions with explicit effects or capabilities.
- Require public APIs to expose complete parameter, return, error, and effect information.
- Generate stable semantic IDs independently of source line positions whenever practical.
- Keep language keywords and common constructs favorable across the tokenizers included in the benchmark suite.

## AI protocol rules

The AI protocol should support focused queries such as:

- symbol lookup;
- type and effect description;
- dependency and reference lookup;
- relevant examples;
- diagnostic explanation;
- candidate repairs;
- structural patch validation;
- impact analysis.

Do not require an agent to read a whole module when a symbol-level response is sufficient.

Structural edits must:

- reference semantic nodes rather than raw line numbers where possible;
- reject stale or ambiguous targets;
- return concise structured errors;
- support validation without applying the change;
- produce a human-reviewable source diff after application.

## Interoperability rules

Use typed interface manifests as the common boundary for Python, Rust, Go, and other runtimes.

The manifest must describe:

- exported symbol names;
- parameter and result types;
- error behavior;
- effects and capabilities;
- ownership or copying behavior;
- sync or async behavior;
- short usage examples.

Start with process-isolated JSON-RPC interoperability. Add Wasm or native FFI only after benchmarks show a concrete need.

Do not expose arbitrary dynamic foreign objects directly in the core type system. Use explicit opaque handles when a value cannot be represented safely.

## Benchmark requirements

Maintain comparable implementations in the new language, Python, Go, and Rust where practical.

Measure at least:

- tokenizer-specific input tokens;
- tokenizer-specific output tokens;
- specification and instruction overhead;
- code-generation pass rate;
- compile success on the first attempt;
- test pass rate;
- number of repair rounds;
- compiler-feedback tokens;
- repository-context tokens;
- patch size;
- wall-clock time as a secondary metric.

Pin benchmark cases, prompts, tokenizers, model identifiers, and settings. Store raw results in machine-readable form.

Separate:

- syntax-only compression;
- complete-program generation;
- repository-level modification;
- debugging and repair;
- foreign-module usage.

Never present estimates as measured results.

## Testing requirements

Required invariants include:

- parser tests for valid and invalid syntax;
- parse-format-parse equivalence;
- formatter idempotence;
- deterministic diagnostic ordering;
- stable diagnostic codes;
- type-checker positive and negative tests;
- runtime behavior tests;
- structural patch round trips;
- rejection of stale patch targets;
- interoperability serialization round trips.

Use property-based or fuzz testing for parser and formatter invariants once the basic implementation is stable.

## Communication

Lead with the completed result. Keep explanations concise.

Clearly distinguish:

- implemented behavior;
- proposed behavior;
- measured results;
- estimates;
- open questions.

Ask the user only when a decision materially changes public syntax, semantics, security boundaries, or the current milestone. Otherwise, make the smallest reversible assumption and continue.

Do not commit, publish, release, or add production credentials unless the user explicitly requests it.
