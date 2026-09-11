# ADR 0003: Semantic paths with canonical content hashes

- Status: Accepted
- Date: 2026-09-11

## Context

Coding agents need bounded semantic queries and edits without receiving or replacing a complete module. Line numbers are compact but become stale after unrelated edits. Fully persistent graph identities would add disproportionate complexity in the first protocol version.

## Decision

Use deterministic local semantic paths as IDs. Top-level examples are `sym:fn:increment`, `sym:global:answer`, `type:record:Config`, and `sym:variant:State.Ready`. Parameters, locals, pattern bindings, and expressions extend their owning function or global with named structural roles such as `/param:value`, `/body/let:offset`, `/arm:Some/bind:value`, and `/body/result/right`.

IDs contain no byte offsets or source text. Formatting and `//` line-comment changes therefore do not alter IDs. Named nodes survive body-only changes. Expression IDs survive edits that preserve their structural role, but may change after surrounding expression structure or argument ordering changes; this is an intentional first-version limit.

Each query returns a SHA-256 hash of canonical parsed source. A patch includes that hash as `base_hash`, plus operations addressed primarily by semantic ID. Hashes ignore whitespace and line comments because both disappear from canonical source. Any semantic module change rejects the old patch before an edit is produced.

Patch version 1 supports `replace_function_body` and `replace_expression`. Validation resolves all targets against one checked snapshot, rejects missing, ambiguous, kind-invalid, overlapping, stale, syntactically invalid, or ill-typed results, then returns a conventional unified source diff and short explanations. `patch.validate` never writes. `patch.apply` writes only after the same validation succeeds, using a same-directory temporary file and rename.

Exact semantic IDs are the canonical patch target. A unique name is accepted as CLI shorthand; an ambiguous name is rejected and must be replaced by an ID.

## Consequences

The protocol is deterministic, reviewable, and small enough for focused edits. It does not promise ID persistence across symbol renames or arbitrary structural refactors. It indexes one source module and has no LLM generation, database, network service, IDE integration, cross-repository operation, or foreign-language support.
