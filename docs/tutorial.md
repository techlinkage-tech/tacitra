# Minimal tutorial

Build the CLI, then run the sample project:

```sh
cargo build --locked -p tacitra-cli
target/debug/tacitra check examples/sample-project/main.taci
target/debug/tacitra run examples/sample-project/main.taci
```

The program returns the final expression from `main`; all bindings are immutable
and every function parameter and return type is explicit. Use
`target/debug/tacitra fmt --check FILE` in validation and `fmt --write FILE` to
canonicalize a valid source file.

`examples/algebraic.taci` is an executable example of a record, tagged union,
`Option`, `Result`, `if`, and exhaustive `match`:

```sh
target/debug/tacitra check examples/algebraic.taci
target/debug/tacitra run examples/algebraic.taci
```

To inspect only the information needed for a small edit and validate a semantic
patch without changing the file:

```sh
target/debug/tacitra symbol.edit-context examples/sample-project/main.taci increment
target/debug/tacitra patch.validate examples/sample-project/main.taci \
  examples/sample-project/increment-by-two.patch.json
```

The patch uses a semantic ID and canonical content hash instead of line numbers.
See [the sample README](../examples/sample-project/README.md) before applying it.

The Python interoperability example runs one typed JSON-RPC call in a child
process:

```sh
target/debug/tacitra interop.inspect examples/interop/python/manifest.json
target/debug/tacitra external.call-context examples/interop/python/manifest.json add
target/debug/tacitra interop.call examples/interop/python/manifest.json add \
  examples/interop/python/add.arguments.json
```

Review the manifest command before invoking external code. This boundary is
process-isolated but is not an operating-system sandbox.
