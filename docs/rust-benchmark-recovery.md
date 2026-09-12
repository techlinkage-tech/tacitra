# Rust benchmark environment recovery

## Root cause

The failed Phase D process ran on Linux under WSL2. Its parent `PATH` resolved Python, Go, and `patch`, but not `rustc`, `cargo`, `rustup`, `rustc.exe`, or `cargo.exe`; `RUSTC`, `CARGO`, and `RUSTUP_HOME` were unset. Rust 1.85.1 existed under an ephemeral toolchain root but was not visible to that process. The frozen harness used an argument array with `shell=False`, preserved the parent environment, and moved into an isolated temporary directory. Its expansion rule fell back from `RUSTC`/`which(rustc)` to the unresolved string `rustc`. `subprocess.run` therefore raised `FileNotFoundError` during compile. Prepare had succeeded, so the generated `program.rs` was present; the compiler executable was missing.

`.env.local` was not responsible. Its parser reads only `OPENAI_API_KEY` and never mutates `PATH`. Credential sanitization also did not remove `PATH`; the frozen acceptance subprocess inherited the parent environment. On this WSL Linux host the required executable is an ELF `rustc`, not Windows `rustc.exe`.

The machine-readable evidence is in `benchmarks/results/rust-environment-recovery-v1/root-cause.json`; `evidence.sha256` pins it together with the local prevalidation result. Existing Phase D evidence remains byte-identical and its Rust failures remain environment failures, not generated-code failures.

## New preflight and command runtime

The replication runtime resolves each executable once, validates an absolute executable path, records a normalized name, binary hash and version, and uses that absolute path in every temporary directory. Resolution supports explicit `RUSTC`/`CARGO`, PATH, `rustup which`, and OS-appropriate `.exe` names. Rust and Cargo must match `rust-toolchain.toml`; nothing is installed automatically.

Preflight verifies Python, Go, Rust, Cargo, Tacitra, GNU-compatible `patch`, required frozen files, the old preregistration hash, unused output paths, and a writable temporary directory. It completes before a provider factory or client can be constructed. Child processes retain the safe parent `PATH` but remove API keys and authorization tokens. Timeout handling kills the process group on POSIX and waits for it, preventing child residue.

For the current local toolchain:

```sh
export RUSTC="$(rustup which rustc)"
export CARGO="$(rustup which cargo)"
python3 benchmarks/semantic_protocol_recovery.py preflight
python3 benchmarks/semantic_protocol_recovery.py prevalidate-rust
```

If `rustup` is not available, set `RUSTC` and `CARGO` to verified absolute paths. A missing tool or version mismatch returns `tool_not_found` or `tool_version_mismatch` before any trial event or API call.

The local prevalidation ran all 60 frozen Rust reference patches through the same `validate_artifact` and subprocess implementation intended for the replication. All 60 compiled and passed using rustc 1.85.1 and Cargo 1.85.1, with one isolated temporary directory per case and zero provider calls. This is local fixture evidence, not a model result.

## Failure classes

The new revision distinguishes `environment_preflight_failure`, `tool_not_found`, `tool_version_mismatch`, `fixture_prevalidation_failure`, `model_generation_failure`, `compile_failure`, `test_failure`, `timeout`, and `provider_failure`. Missing tools cannot become language trials. Provider failures without trustworthy usage abort and are never recorded as successful or zero-token attempts.

The version-two comparison returns `null` with reason `zero_accepted_trials` for tokens per accepted solution, differences, and intervals when either side has no acceptance. It retains failed trials, total tokens and repair rounds, while continuing other valid comparisons. Markdown renders the same value as `not estimable`.

## Replication recommendation

A Rust-only recovery would require 60 trials and at most 180 API calls. It can verify technical recovery but cannot repair contemporaneous language comparisons. The recommended design is a full five-condition interleaved replication: 60 already-used cases, 300 trials and at most 900 calls, under a new schedule, harness hash, preregistration and result directory. It must be labeled an environment-corrected replication, not a new held-out confirmation.

Based on the retained first attempts, the full run is estimated at 208,610 provider tokens if no repairs occur; Rust-only is estimated at 36,301. Dollar cost is intentionally `null` because no public price exists for the exact pinned model. Apply account input/output rates at execution time. No future model run is authorized by this document.
