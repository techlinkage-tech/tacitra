# Tacitra

Tacitra is an experimental typed programming language designed to reduce the
**total LLM tokens required to complete a correct change**. It optimizes the whole
loop—specification, repository context, generated edits, diagnostics, and repairs—
rather than making only the final source code shorter.

## Why Tacitra?

- **Less context:** task-scoped specifications and semantic queries return only the
  types and expressions needed for the current task, without sending whole files.
- **Smaller, safer edits:** patches target stable semantic IDs instead of line
  numbers and use a content hash to reject stale changes before writing.
- **Fewer ambiguous repairs:** one canonical syntax, explicit types, deterministic
  formatting, and concise structured diagnostics give an LLM one predictable form
  to generate and fix.
- **Reuse without foreign source:** typed manifests summarize Python, Go, and Rust
  APIs and execute them behind a validated, process-isolated JSON-RPC boundary.

The intended benefit is lower model cost and less context-window pressure while
preserving correctness checks and human-reviewable source diffs. Tacitra source
alone has not shown that benefit: in `cross-language-v1` it used about 50–60%
more provider tokens than Python, Go, and Rust. A separate AI semantic surface has
now reduced tokens relative to ordinary Tacitra editing, but has not been fairly
shown to outperform those other languages.

### Measured result

In a preregistered evaluation with 60 paired held-out tasks using the same pinned
model and settings, baseline and optimized Tacitra both accepted **60/60** changes.
Provider-reported tokens per accepted solution fell from **3,506.73 to 2,102.68**,
an observed **40.04% reduction**. This supports the optimized context protocol for
these small tasks and this model; it does not yet establish a cross-model result or
superiority over Python, Go, or Rust. See the [full results](docs/model-confirmation-results.md).

```tacitra
fn add(a: Int, b: Int) -> Int {
  a + b
}

fn main() -> Int {
  add(40, 2)
}
```

## Quick start

Rust 1.85.1 is pinned by `rust-toolchain.toml`. See [installation](docs/install.md)
and the [tutorial](docs/tutorial.md).

```sh
cargo build --locked -p tacitra-cli
target/debug/tacitra check examples/sample-project/main.taci
target/debug/tacitra fmt --check examples/sample-project/main.taci
target/debug/tacitra run examples/sample-project/main.taci
```

Query a function and validate a semantic patch without modifying the source:

```sh
target/debug/tacitra symbol.edit-context examples/sample-project/main.taci increment
target/debug/tacitra patch.validate examples/sample-project/main.taci \
  examples/sample-project/increment-by-two.patch.json
```

Generate a source-free task capsule and preview a compact typed edit:

```sh
target/debug/tacitra ai.context examples/ai-surface/main.taci increment \
  --success 'increment adds two'
target/debug/tacitra ai.edit.validate examples/ai-surface/main.taci \
  examples/ai-surface/increment-by-two.edit.json
target/debug/tacitra ai.edit.diff examples/ai-surface/main.taci \
  examples/ai-surface/increment-by-two.edit.json
```

Inspect and call the typed Python example without reading its implementation:

```sh
target/debug/tacitra external.call-context examples/interop/python/manifest.json add
target/debug/tacitra interop.call examples/interop/python/manifest.json add \
  examples/interop/python/add.arguments.json
```

Run the complete offline release-readiness check with:

```sh
python3 scripts/release_check.py
```

## Repository map

- `crates/tacitra-syntax`: lexer, source-positioned AST, parser, formatter, diagnostics
- `crates/tacitra-semantics`: name resolution, typed HIR, type checking, interpreter
- `crates/tacitra-agent`: semantic IDs, focused queries, structural patches
- `crates/tacitra-interop`: typed manifests, value codec, standard-I/O JSON-RPC
- `crates/tacitra-cli`: compiler, execution, query, patch, and interop commands
- `protocol/schema`: versioned machine-readable schemas
- `benchmarks`: comparable fixtures, raw measurements, and reproducible reports

For scope and evidence boundaries, see [status](docs/status.md),
[known limitations](docs/known-limitations.md), [security](docs/security.md), and
the [measurement contract](docs/metrics.md).

Benchmark toolchain failures are diagnosed before provider access by the
[replication preflight](docs/rust-benchmark-recovery.md); the original failed
Rust evidence remains preserved rather than rewritten.

The follow-up semantic-protocol-v2 confirmation kept Tacitra syntax unchanged and
used normal Tacitra function-body fragments. Both conditions accepted 60/60 held-out
changes; tokens per accepted solution fell from 854.68 to 616.97, a preregistered
27.81% observed reduction. This confirms the protocol relative to ordinary Tacitra
for these tasks and this model, not superiority over Python, Go, or Rust; see the
[v2 confirmation results](docs/semantic-protocol-v2-results.md).
