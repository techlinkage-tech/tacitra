# ADR 0009: Version public diagnostics and gate release readiness

- Status: Accepted
- Date: 2026-09-11

## Context

The pre-release CLI already emitted deterministic compiler, agent, and interop
errors, but compiler envelopes had no explicit version and agent/interop error
schemas existed only as prose. Consumers could not safely pin a machine contract.
The repository also needed one repeatable check spanning correctness, examples,
licenses, and retained benchmark evidence. Public syntax and semantics do not need
to change for stabilization.

## Decision

Designate the workspace and CLI as experimental version 0.1.0. Add
`schema_version: 1` to compiler diagnostic and check-success envelopes and to agent
and interoperability error envelopes. Publish strict Draft 2020-12 schemas with
versioned filenames and `$id` values. Keep diagnostic object fields, meanings,
ordering, and codes unchanged. Patch and manifest documents remain schema v1; only
the patch schema identifier is made explicitly versioned.

Within a schema version, never reassign an error code. Reserve removed codes and
require a new schema version for field removal, field type changes, code semantic
changes, or ordering changes. Protocol inputs remain strict and reject unknown
fields. Document the external worker/controller compatibility matrix rather than
adding version negotiation to the first protocol.

Use deterministic generated property corpora for parser/formatter and patch
invariants without adding a runtime dependency. A single offline release check runs
formatting, linting, tests, examples, schema/license checks, frozen confirmation
validation, and byte-identical benchmark reaggregation. It validates retained model
evidence but never spends model tokens.

## Compatibility and migration

The extra `schema_version` member changes the exact pre-release JSON envelope.
Consumers migrate by accepting the member and selecting v1. Diagnostic objects and
all language behavior are unchanged. This one-time envelope break occurs before the
first public-ready experimental version; future breaks follow the documented 0.x
and schema-version policy.

## Consequences

Machine consumers can pin concrete schemas, and release candidates have one
reproducible gate. Deterministic property tests broaden invalid-input coverage but
are not continuous coverage-guided fuzzing or a resource-exhaustion proof. No new
language feature, syntax, or execution capability is introduced.
