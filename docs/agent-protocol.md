# AI semantic query and patch protocol

All query output is deterministic compact JSON. Successful queries return no source text. A Tacitra source file is one module with ID `mod:root`; all top-level declarations are public because visibility syntax does not yet exist.

## Queries

```sh
tacitra module.summary examples/agent_target.taci
tacitra symbol.describe examples/agent_target.taci sym:fn:increment
tacitra symbol.edit-context examples/agent_target.taci sym:fn:increment
tacitra symbol.references examples/agent_target.taci sym:fn:increment
tacitra type.describe examples/agent_target.taci type:record:Config
```

- `module.summary` returns the semantic content hash, public symbols, available types, counts, and call graph.
- `symbol.describe` returns the symbol type, span, bounded expression index, calls, and function detail. Function detail contains parameters, return type, `failure_type` derived from `Result`, `effects`, and `contracts`. Effects and contracts are empty until those language features exist.
- `symbol.edit-context` is the task-scoped projection for a small function-body edit. It returns the module hash, symbol and body targets, function type, and typed semantic leaves with literal or resolved-name values. It deliberately omits spans, calls, operators, and declaration detail; use `symbol.describe` when those facts are required.
- `symbol.references` returns resolved reads and calls with owning symbol, expression ID, and span.
- `type.describe` returns primitive/record/union structure and the semantic IDs that use it.

Selectors may be exact IDs or unambiguous names. Responses never include the complete module source.

## Patch document

The authoritative JSON Schema is [`protocol/schema/patch.schema.json`](../protocol/schema/patch.schema.json).

```json
{
  "schema_version": 1,
  "base_hash": "sha256:...",
  "operations": [
    {
      "op": "replace_function_body",
      "target": "sym:fn:increment",
      "replacement": "{ value + 2 }"
    }
  ]
}
```

`replace_expression` uses an `expr:...` semantic path and an expression fragment. `replace_function_body` uses a function ID and a complete block fragment. Operations are resolved against the original snapshot and must not overlap.

```sh
tacitra patch.validate examples/agent_target.taci examples/patches/increment-by-two.json
tacitra patch.apply examples/agent_target.taci examples/patches/increment-by-two.json
```

Both commands parse and type-check the resulting complete module. Their JSON report includes the old/new hashes, whether content changes, operation explanations, and a unified diff. Validation leaves the file untouched. Apply atomically replaces it only after validation and writes canonical formatted source; non-semantic line comments are consequently removed. Copy the example target before running the apply example if the original fixture must remain unchanged.

## Agent error codes

- `A0001`: target does not exist.
- `A0002`: selector is ambiguous.
- `A0003`: `base_hash` is stale.
- `A0004`: operations overlap.
- `A0005`: patched module fails parsing or semantic checking.
- `A0006`: patch JSON or schema is invalid.
- `A0007`: operation and target kinds do not match.

These errors use `{"valid":false,"error":{"code", "message", "target"}}`. Compiler diagnostics retain their existing structured format.

## Measurement status

The Milestone 6 static-reference run measured the repository-change edit context at 393 `utf8-bytes/1` tokens versus 917 for `symbol.describe`; the selected function-body patch was 211 versus 219 bytes. Combined with the task-scoped specification, this representation fell from 18,192 to 10,432 total byte-tokens at unchanged 3/3 fixture acceptance. This is measured static evidence, not an LLM-token or model-accuracy result.

## External API queries

`external.summary MANIFEST.json` and `external.describe MANIFEST.json EXPORT` expose typed foreign APIs without returning worker source or launch commands. They use the common manifest described in [`docs/interop.md`](interop.md); interoperability failures retain their separate stable `I0001`–`I0013` vocabulary.
