# Sample project

From the repository root, build the CLI and exercise the same program through
the complete front end and interpreter:

```sh
cargo build -p tacitra-cli
target/debug/tacitra parse examples/sample-project/main.taci
target/debug/tacitra fmt --check examples/sample-project/main.taci
target/debug/tacitra check examples/sample-project/main.taci
target/debug/tacitra run examples/sample-project/main.taci
```

`run` prints `42`. Query the function without retrieving the complete source:

```sh
target/debug/tacitra symbol.edit-context \
  examples/sample-project/main.taci sym:fn:increment
target/debug/tacitra patch.validate \
  examples/sample-project/main.taci \
  examples/sample-project/increment-by-two.patch.json
```

Validation is a dry run and leaves `main.taci` unchanged. Copy the directory to
a temporary location before trying `patch.apply`; the supplied patch is stale
after it has been applied once by design.
