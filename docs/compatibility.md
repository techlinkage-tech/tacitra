# Versioning and compatibility

The first public-ready experimental version is `0.1.0`. Cargo packages and the
CLI follow Semantic Versioning. While the major version is zero, a minor release
may make breaking source, CLI, HIR, or protocol changes; patch releases preserve
documented behavior. Every such change must update tests, specifications, and an
ADR together.

Compiler diagnostic JSON uses
[`diagnostics-v1.schema.json`](../protocol/schema/diagnostics-v1.schema.json) and
contains `schema_version: 1`. Diagnostic meanings are append-only within v1:
existing codes are not reassigned, removed codes remain reserved, and message
wording may only change when consumers rely on `code` and typed fields rather
than exact prose. A field removal, changed type, changed code meaning, or changed
ordering rule requires a new schema version. Unknown fields should be ignored by
tolerant readers, although the authoritative v1 schema describes emitted output
strictly.

The older diagnostic, agent-protocol, and interoperability prose files are frozen
inputs to the preregistered confirmation experiment and show the pre-release
envelope without `schema_version`. Their diagnostic/error objects remain accurate;
for the public-ready 0.1.0 envelope, this document and the versioned schemas are
authoritative. Keeping those measured inputs byte-identical prevents a post-hoc
change to retained evidence.

Semantic patches and interoperability manifests each carry `schema_version: 1`.
The schema `$id` contains `v1`. The current parsers are intentionally strict:
they reject unknown fields and unsupported versions. A compatible producer must
therefore emit exactly the selected version rather than feature-detecting fields.

## External protocol v1

- Manifest v1 is paired with JSON-RPC `2.0` and one request per fresh process.
- Adding an export is compatible for consumers that select exports by exact name.
- Removing or renaming an export, changing a parameter/result/error type, mode,
  ownership, effect, capability, encoding, or launch behavior is breaking.
- Reordering exports, parameters, record fields, effects, or capabilities is not
  permitted as an accidental compatibility mechanism; canonical order is part of
  deterministic output and parameters are named at the wire boundary.
- New optional wire metadata may be ignored only where v1 explicitly permits it.
  New manifest fields require a new schema version because the v1 parser is strict.
- A v1 controller rejects non-v1 manifests before spawning a worker. Workers must
  echo JSON-RPC version `2.0` and request ID `1`; malformed responses fail closed.

No compatibility is promised for Rust library APIs or the serialized internal AST
and HIR in 0.1.0. Stable public boundaries are the documented source language,
CLI behavior, diagnostic schema, patch schema, manifest schema, and benchmark
artifact schemas.
