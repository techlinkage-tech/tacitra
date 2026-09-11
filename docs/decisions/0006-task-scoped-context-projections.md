# ADR 0006: Use task-scoped specification and semantic context projections

- Status: Accepted
- Date: 2026-09-11

## Context

The retained Milestone 5 static-reference run measured 738,105 `utf8-bytes/1` total tokens across 63 accepted trials. Persistent instructions contributed 536,823 (72.7%) and specifications 155,292 (21.0%). Tacitra's full specification cost 4,790–8,353 tokens per representation even when a task used only scalar functions. The repository semantic query cost 917 tokens and the complete external manifest cost 1,786. Tacitra outputs were only 23–219 tokens, so the measurements did not support a public syntax change.

## Decision

Keep the accepted syntax and semantics unchanged. Add versioned task-scoped specification profiles that are projections of the authoritative documents and may be selected only when they cover every feature used by a task.

Add `symbol.edit-context` for small function-body edits. Its deterministic response retains the content hash, stable function/body targets, function type, and typed leaf values while omitting spans and unrelated semantic facts. Continue to support `symbol.describe` for broader investigation.

Add `external.call-context` for a known one-export invocation. It retains the complete typed call contract, declared failure/effects/capabilities, ownership, mode, and one example while omitting transport and other exports. The full manifest remains authoritative and is validated at execution.

Prefer an already-supported `replace_function_body` patch where it expresses the intended bounded change. No patch schema version or accepted operation is removed.

## Compatibility and migration

There is no source-language, runtime, manifest, or patch-schema incompatibility. Existing commands and full responses remain available. Agents may opt into the new CLI projections; callers requiring omitted facts migrate back to the full query. Profile selection is benchmark/input configuration rather than a language-mode switch.

## Consequences

The final static run measured 642,129 total tokens and 63/63 accepted trials, compared with 738,105 and 63/63 before. Total tokens per accepted solution changed from 11,715.95 to 10,192.52 (-13.00%). Specification tokens fell 58.09%, repository context 28.35%, and output 0.18% across the full suite. These exact byte-token measurements do not establish LLM token savings or model accuracy; that trade-off remains statistically unknown until pinned model trials are run.
