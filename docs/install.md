# Installation

Tacitra 0.1.0 is an experimental source build. A clean environment needs Git,
Rust 1.85.1 with Cargo, Python 3.10 or newer, and `patch`. Go 1.24 and a standalone
`rustc` are needed only for the Go/Rust interoperability fixtures and complete
benchmark suite. The pinned Rust toolchain file installs `rustfmt` and `clippy`.

```sh
git clone REPOSITORY_URL tacitra
cd tacitra
cargo build --locked --release -p tacitra-cli
./target/release/tacitra --version
./target/release/tacitra --help
```

Replace `REPOSITORY_URL` after selecting the public host. No package registry or
prebuilt binary is provided. The CLI makes no network requests. External-module
commands execute the manifest's local child-process command and therefore need
the declared worker runtime.

For development, use `cargo build --locked`. Run `python3 scripts/release_check.py`
before distributing a snapshot; see the [release checklist](release-check.md).
