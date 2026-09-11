# Release-readiness check

From a clean checkout with the prerequisites in [installation](install.md), run:

```sh
python3 scripts/release_check.py
```

The command is offline and does not call a model API. It verifies Rust formatting,
Clippy, all Rust and Python tests, public JSON schema metadata, dependency license
metadata, the sample parse/format/check/run flow, semantic query and patch dry-run,
the Python interoperability example, benchmark cases, all 40 frozen confirmation
references, confirmation pins, and byte-identical regeneration of retained static,
Milestone 6, and confirmatory model aggregates/reports. It also checks that
`.env.local` is ignored when present and runs `git diff --check`.

The check validates retained measurements; it does not spend tokens by repeating
the external model experiment. A fresh model replication is a separately approved,
credentialed experiment and must write to a new results directory.

The release check may build and execute local Python, Go, and Rust fixtures. Review
the repository before running it in an untrusted checkout.
