# ADR 0004: Versioned typed manifests over one-shot stdio JSON-RPC

- Status: Accepted
- Date: 2026-09-11

## Context

Milestone 4 needs to reuse Python, Go, and Rust assets without exposing arbitrary foreign objects or implementing a separate type system for each runtime. The earlier roadmap placed interoperability in Milestone 5 and planned bounded collections and language effects for Milestone 4. The approved Milestone 4 request explicitly moves interoperability forward and fixes the initial transport as versioned JSON-RPC over standard I/O.

## Decision

Use one strict, version-one JSON manifest as the authoritative foreign interface. It recursively describes the allowed scalar, collection, record, optional, result, and opaque-handle types, plus every function's parameter, result, error, mode, effects, capabilities, ownership, and examples. Runtime-specific source and internal types are outside this contract.

Use a fresh child process for each JSON-RPC 2.0 call. Send one object on standard input, close input, accept one object on standard output, and wait for exit. Validate arguments before spawning and validate success or declared error data before exposing it. Kill and wait for a child on timeout. Native FFI, persistent workers, callbacks, arbitrary foreign objects, and foreign references are excluded.

Treat manifests and launch commands as trusted project configuration, but require explicit per-invocation grants for declared effects and capabilities. A cooperative worker may report observed effects and capabilities; reject observations outside both the manifest and grant. This is a useful consistency check, not a security sandbox.

Expose bounded `external.summary` and `external.describe` queries that omit worker source and command details. This reuses the deterministic machine-readable query approach from ADR 0003 without merging external symbols into Tacitra source-module IDs prematurely.

## Consequences

The same controller, validator, value codec, and error vocabulary serve all three sample languages. Process isolation prevents foreign exceptions and panics from unwinding through Tacitra, at the cost of process startup and JSON copying per call. Async declarations are descriptive in version one; the controller still waits synchronously. Effects cannot be reliably observed against a malicious worker until an operating-system sandbox or capability broker is added.

No Tacitra public syntax changes in this decision. Bounded collections and language-level effects/contracts remain a later milestone.
