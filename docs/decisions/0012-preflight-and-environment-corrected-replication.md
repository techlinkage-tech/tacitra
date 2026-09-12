# ADR 0012: Preflight tools and use a full environment-corrected replication

- Status: accepted
- Date: 2026-09-12

## Context

`semantic-protocol-v1` called the provider before proving that its acceptance tools were executable. The host had Rust 1.85.1 outside the model process PATH; the harness substituted literal `rustc`, and all 60 Rust conditions consumed three attempts before failing locally. A zero-acceptance comparator also crashed the frozen comparison implementation. Those retained results cannot be repaired retrospectively.

## Decision

Preserve the frozen suite and evidence byte-for-byte. Build a new harness revision that resolves and version-checks every tool before constructing a provider client, passes validated absolute executable paths to shell-free subprocess arrays, strips credentials while preserving PATH, prevalidates every Rust reference through the same command path, and treats a missing tool as a run-level environment failure.

Make zero acceptance a first-class estimability state: retain failure costs but emit JSON `null` plus `zero_accepted_trials`, and Markdown `not estimable`. Do not mutate the frozen comparison; use the robust behavior in future replications.

Recommend a full interleaved five-condition replication rather than using old Python/Go/Tacitra results beside a later Rust-only run. Reuse of the 60 cases must be labeled a technical environment-corrected replication. Freeze a new schedule, all inherited and new hashes, the same model settings and decision rules, and a new output directory before any API access.

## Consequences

Preflight failure produces no trial-start event and zero provider calls. Personal absolute paths stay runtime-only; public reports use executable names, hashes and versions. A Rust-only 60-trial run remains available for technical diagnosis but cannot restore a formal cross-language comparison. The full replication costs 300 trials and up to 900 calls.
