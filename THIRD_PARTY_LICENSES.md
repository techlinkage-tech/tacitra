# Third-party dependency review

This snapshot's direct Rust dependencies are `serde`, `serde_json`, and `sha2`.
The table below includes their locked transitive dependencies. It was checked from
`cargo metadata --locked --format-version 1` with Rust 1.85.1 and Cargo.lock on
2026-09-11. The release check fails when a registry dependency has no declared
license metadata.

| Package | Locked version | Declared license expression |
|---|---:|---|
| block-buffer | 0.10.4 | MIT OR Apache-2.0 |
| cfg-if | 1.0.4 | MIT OR Apache-2.0 |
| cpufeatures | 0.2.17 | MIT OR Apache-2.0 |
| crypto-common | 0.1.7 | MIT OR Apache-2.0 |
| digest | 0.10.7 | MIT OR Apache-2.0 |
| generic-array | 0.14.7 | MIT |
| itoa | 1.0.18 | MIT OR Apache-2.0 |
| libc | 0.2.189 | MIT OR Apache-2.0 |
| memchr | 2.8.3 | Unlicense OR MIT |
| proc-macro2 | 1.0.107 | MIT OR Apache-2.0 |
| quote | 1.0.47 | MIT OR Apache-2.0 |
| serde | 1.0.229 | MIT OR Apache-2.0 |
| serde_core | 1.0.229 | MIT OR Apache-2.0 |
| serde_derive | 1.0.229 | MIT OR Apache-2.0 |
| serde_json | 1.0.151 | MIT OR Apache-2.0 |
| sha2 | 0.10.9 | MIT OR Apache-2.0 |
| syn | 3.0.5 | MIT OR Apache-2.0 |
| typenum | 1.20.1 | MIT OR Apache-2.0 |
| unicode-ident | 1.0.24 | (MIT OR Apache-2.0) AND Unicode-3.0 |
| version_check | 0.9.5 | MIT/Apache-2.0 |
| zmij | 1.0.23 | MIT |

The repository declares MIT and already includes its owner-provided MIT text in
`LICENSE`. This inventory confirms declared metadata, not legal compatibility or
notice obligations. Before publication, the owner should independently review the
selected license branches and upstream notices.
