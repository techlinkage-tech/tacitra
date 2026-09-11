# Tacitra

Tacitra is an experimental programming language for minimizing the total LLM input and output tokens needed to produce an accepted program change. It optimizes the whole loop—context, generation, compiler feedback, and repair—not source length alone.

Milestones 0 through 7 provide the measurement contract, deterministic syntax tooling, typed execution, hash-guarded structural patches, typed process-isolated interoperability, reproducible model measurements, measured task-scoped context optimization, and a release-readiness gate.

```tacitra
fn add(a: Int, b: Int) -> Int {
  a + b
}

let answer = add(40, 2);
let accepted = answer == 42;
```

## Build and use

Rust 1.85.1 is pinned by `rust-toolchain.toml`. See the [clean-environment installation guide](docs/install.md).

```sh
cargo build
cargo test --workspace
cargo run -p tacitra-cli -- check examples/basic.taci
cargo run -p tacitra-cli -- fmt examples/basic.taci
cargo run -p tacitra-cli -- parse --json examples/basic.taci
cargo run -p tacitra-cli -- run examples/algebraic.taci
cargo run -p tacitra-cli -- symbol.describe examples/agent_target.taci sym:fn:increment
cargo run -p tacitra-cli -- symbol.edit-context examples/agent_target.taci sym:fn:increment
cargo run -p tacitra-cli -- patch.validate examples/agent_target.taci examples/patches/increment-by-two.json
cargo run -p tacitra-cli -- interop.inspect examples/interop/python/manifest.json
cargo run -p tacitra-cli -- external.call-context examples/interop/python/manifest.json add
cargo run -p tacitra-cli -- interop.call examples/interop/python/manifest.json add examples/interop/python/add.arguments.json
python3 benchmarks/harness.py validate
python3 benchmarks/run_optimized.py validate
python3 scripts/release_check.py
```

`check`, `parse`, and `run` return a non-zero status for invalid source. Add `--json` for stable machine-readable output. `check` includes name and type analysis; `run` executes only successfully checked HIR and invokes a zero-argument `main`. `fmt` writes canonical source to stdout; `fmt --write FILE` updates a valid file, and `fmt --check FILE` reports whether it is already canonical. Semantic query, patch, and interoperability commands always return JSON; see [the agent protocol](docs/agent-protocol.md) and [interoperability specification](docs/interop.md).

## Repository map

- `crates/tacitra-syntax`: lexer, source-positioned AST, parser, formatter, and diagnostics
- `crates/tacitra-semantics`: name resolution, typed HIR, type checking, and interpreter
- `crates/tacitra-agent`: stable semantic indexing, queries, and structural patches
- `crates/tacitra-interop`: typed manifests, shared value codec, and standard-I/O JSON-RPC
- `crates/tacitra-cli`: compiler, execution, query, patch, and interoperability commands
- `protocol/schema`: machine-readable protocol schemas
- `docs/language`: accepted syntax for the implemented milestone
- `docs/decisions`: architectural and public-syntax decisions
- `benchmarks`: versioned case schema and comparable language fixtures

Start with the [tutorial](docs/tutorial.md). Release and operational details are in [compatibility](docs/compatibility.md), [security boundaries](docs/security.md), [known limitations](docs/known-limitations.md), and the [release check](docs/release-check.md). See also the [roadmap](docs/roadmap.md), [current status](docs/status.md), [measurement rules](docs/metrics.md), [Milestone 6 optimization record](docs/m6-optimization-plan.md), and [real-model confirmation results](docs/model-confirmation-results.md). The preregistered 60-pair evaluation supported adoption: both conditions accepted 60/60, while provider tokens per accepted solution fell 40.04% under the pinned model condition.
