# Tacitra AI surface v1

Tacitra has two deliberately separate surfaces. The human surface is canonical `.taci` source and normal Git diffs. The AI surface is a versioned, task-scoped transport that lets a model inspect and change semantic units without receiving or returning a whole file. The compiler remains the trust boundary and always renders accepted edits back to canonical source.

## Task capsule

`tacitra ai.context FILE SYMBOL --success TEXT` returns deterministic `task-capsule-v1`. It contains the module content hash, target semantic ID and complete signature, in-scope typed values, directly referenced type definitions and calls, effects, capabilities, contracts, allowed operations, and success condition. It excludes source text and unrelated declarations. `ai.context-size` reports UTF-8 byte sizes by section. Missing information can be requested through the existing symbol/type/module queries; it does not imply sending the full specification.

## Typed edit

The compact canonical transport is:

```json
{"v":1,"h":"sha256:...","cap":[],"ops":[["body","sym:fn:add","{ value + 2 }"]]}
```

`body` replaces a function body and `expr` replaces an expression selected by semantic ID. Operations are ordered and atomic. Replacement fragments use canonical Tacitra syntax and are checked through the existing parser, resolver, type checker, formatter, and structural patch engine. `cap` must be a subset of capabilities declared by the capsule; v1 rejects requested capabilities because core evaluation is pure. The existing verbose patch schema remains supported unchanged. `ai.edit.compact` and `ai.edit.expand` convert at the explicit version boundary.

Two experimental input adapters use the same checked semantics without changing `.taci` syntax. `ai.fragment.*` binds a normal Tacitra function-body fragment to an explicit module hash and semantic target. `ai.edit.named.*` accepts `named-edit-v1`, whose operation objects use `operation`, `target`, and `replacement` fields. Both reject stale, missing, ambiguous, syntactically invalid, and ill-typed edits before producing canonical source and a reviewable diff. The named schema is `protocol/schema/named-edit-v1.schema.json`.

The CLI provides `ai.edit.validate`, `ai.edit.dry-run`, `ai.edit.apply`, and `ai.edit.diff`. Validation and dry-run never write the source. Apply checks the module hash, resolves unique IDs, checks types, formats the result, and writes atomically. Diff emits an ordinary reviewable unified diff.

## Repair context and errors

`ai.repair-context FILE EDIT` returns only repair-context-v1: stable code, failed operation index, target ID, expected/actual type when available, in-scope values or allowed operations, current hash, and retryability. It does not repeat source, capsule, protocol, or successful operations.

- `A0001`–`A0007`: existing parse, target, stale, type/check, overlap, and I/O failures.
- `A0008`: malformed typed-edit document or unsupported compact operation.
- `A0010`: undeclared/requested capability.

Schemas live in `protocol/schema/{task-capsule,typed-edit,repair-context}-v1.schema.json`. Unknown versions and extra fields are rejected. All JSON keys and diagnostic order are deterministic.

## Security and limits

Semantic edits are untrusted input. They receive no ambient capabilities, cannot bypass checking, and cannot apply against a stale hash. V1 embeds replacement expressions as Tacitra fragments rather than a fully typed serialized HIR, supports only body/expression replacement, and does not provide transactional edits across modules. Semantic IDs are stable under formatting/comments but may change after relevant structural changes.

## Example

```sh
cargo run -p tacitra-cli -- ai.context examples/ai-surface/main.taci increment --success 'increment adds two'
cargo run -p tacitra-cli -- ai.edit.validate examples/ai-surface/main.taci examples/ai-surface/increment-by-two.edit.json
cargo run -p tacitra-cli -- ai.edit.diff examples/ai-surface/main.taci examples/ai-surface/increment-by-two.edit.json
```
