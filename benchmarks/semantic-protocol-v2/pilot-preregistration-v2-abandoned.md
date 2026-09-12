# Pilot preregistration v2 disposition

`pilot-preregistration-v2.json` was frozen locally but never used for a provider call. Full Python release checking showed that adding candidate adapters inside the v1-pinned `ai.rs` invalidated the retained semantic-protocol-v1 reproducibility check. The adapters were isolated in `candidate.rs`; pilot preregistration v3 pins that module and supersedes v2 before any model result existed.
