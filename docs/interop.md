# External module interoperability

Version-one interoperability uses a typed JSON manifest and one JSON-RPC 2.0 request over a fresh child process's standard input and output. The manifest is the common source of truth for Python, Go, Rust, and future workers. Worker-language types are never imported into Tacitra.

The authoritative schema is [`protocol/schema/interop-manifest.schema.json`](../protocol/schema/interop-manifest.schema.json). A manifest declares its version, module name, launch command, default timeout, and exports. Every export declares parameter and result types, an optional recoverable error-data type, synchronous or asynchronous mode, effects, capabilities, ownership policy, and at least one short checked example.

## Boundary types and values

Types use one recursive tagged representation:

- `{"kind":"bool"}`, `{"kind":"int","signed":true,"bits":64}`, and `{"kind":"float","bits":64}`.
- `{"kind":"string"}` and `{"kind":"bytes"}`.
- `list`, `record`, `option`, `result`, and `opaque` contain their nested type or name explicitly.

Integers must fit the declared signed or unsigned 8, 16, 32, or 64-bit range. Floats are 32 or 64-bit finite JSON numbers. Strings use JSON strings. Composite value encodings are:

```json
{"$bytes":"VGFjaXRyYQ=="}
{"$some":"value"}
{"$none":true}
{"$ok":42}
{"$err":{"message":"failed"}}
{"$handle":{"type":"Session","id":"worker-issued-id"}}
```

Lists are JSON arrays. Records are JSON objects containing exactly the declared fields. Opaque handles are identity tokens only; Tacitra does not inspect, dereference, or treat them as foreign objects. An export containing an opaque type must declare `"ownership":"handle"`; all other examples use `"copy"`.

## Transport

The controller launches the manifest command with the manifest directory as its working directory. It writes exactly one request and closes standard input:

```json
{"jsonrpc":"2.0","id":1,"method":"add","params":{"left":20,"right":22}}
```

The worker writes exactly one JSON value and exits. A successful response contains `result`; a failed response contains a JSON-RPC `error`. Both may report cooperative observation metadata:

```json
{"jsonrpc":"2.0","id":1,"result":42,"meta":{"effects":[],"capabilities":[]}}
```

The controller validates parameters before launch and validates results or declared error data afterward. It refuses calls unless every declared effect and capability is explicitly granted. It also rejects any worker-reported effect or capability absent from the manifest or invocation grant. This detects honest protocol participants that exceed their declaration; it is not an operating-system sandbox and cannot detect a malicious worker that omits metadata. Workers inherit the controller environment and operating-system permissions, so manifests and their commands must be reviewed as executable project configuration.

Each call gets a new child. On timeout or controller-side I/O failure the controller kills and waits for it. Non-zero exit, malformed protocol, mismatched response types, and foreign exceptions become structured interoperability errors rather than Tacitra panics.

`mode: "async"` describes the foreign API; version one still waits for the one-shot worker response. It does not introduce Tacitra futures or background children.

## CLI and semantic queries

```sh
tacitra interop.inspect examples/interop/python/manifest.json
tacitra external.summary examples/interop/python/manifest.json
tacitra external.describe examples/interop/python/manifest.json add
tacitra external.call-context examples/interop/python/manifest.json add
tacitra interop.call examples/interop/python/manifest.json add examples/interop/python/add.arguments.json
```

For an export declaring an effect or capability, add repeated `--allow-effect NAME` or `--allow-capability NAME` flags. `--timeout-ms N` overrides the manifest default for one call. Inspection and external semantic queries return deterministic compact JSON without worker source or the launch command. `external.call-context` is the narrow projection for invoking one known export: it retains its parameters, result, declared error, mode, effects, capabilities, ownership, and first example while omitting transport and unrelated exports. Discovery still uses `external.summary` or `external.describe`.

The Python sample is directly executable. Build the Go and Rust fixtures before using their manifests:

```sh
go build -o examples/interop/go/worker examples/interop/go/worker.go
rustc --edition=2021 -o examples/interop/rust/worker examples/interop/rust/worker.rs
```

## Error codes

- `I0001`: malformed or invalid manifest.
- `I0002`: unsupported manifest version.
- `I0003`: argument or boundary value violates its declared type.
- `I0004`: export does not exist.
- `I0005`: required effect was not granted.
- `I0006`: required capability was not granted.
- `I0007`: worker spawn or transport I/O failed.
- `I0008`: call timed out; the worker was killed and reaped.
- `I0009`: worker exited unsuccessfully.
- `I0010`: invalid JSON-RPC response or error payload.
- `I0011`: structured external exception or JSON-RPC error.
- `I0012`: successful result violates the manifest.
- `I0013`: worker reported undeclared or ungranted activity.

All errors use `{"valid":false,"error":{"code","message","detail"}}`.
