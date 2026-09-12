# ADR 0011: Separate human source from the AI semantic surface

Status: accepted

## Context

`confirmation-v1` measured a 40.04% token reduction from task-scoped Tacitra context, but `cross-language-v1` measured Tacitra ordinary source/diff at 950.94 provider tokens per accepted solution versus 595.61 for Python, 634.05 for Go, and 627.51 for Rust. All languages accepted 85/85. Input accounted for 82.56%–88.50% of Tacitra's gap. Shortening public syntax without evidence would risk transferability and compatibility while missing the measured bottleneck.

## Decision

Keep canonical Tacitra source as the human/review surface. Add a versioned AI surface composed of a task capsule, compact typed edits, and minimal repair context. The compiler translates edits through the existing structural patch implementation, rejects stale/unknown/ambiguous/type-invalid/capability-invalid input, and emits canonical source plus a normal diff.

Three edit encodings were measured on six development cases with `utf8-bytes/1`: legacy verbose object 249.33 bytes, compact named object 257.33, and compact tuple 185.33. Adopt the tuple encoding because it is smallest while remaining versioned, schema-validatable, deterministic, and convertible to the legacy format. Reject the named object because it was larger than legacy; preserve legacy for compatibility.

Local end-to-end static measurement was 1,477.50 bytes for semantic versus 2,181.33 for Tacitra ordinary, a measured 703.83-byte (32.27%) reduction. This is not a provider-token or success-rate claim. Ablation showed the capsule was 214.50 bytes larger than the small full-source contexts; therefore no independent token benefit is claimed for semantic query on these cases. Task-scoped specification and compact edits were the supported contributors. The capsule is retained as the typed, source-free safety boundary and must be tested on larger repositories.

## Consequences

Existing source syntax and verbose patch clients remain compatible. Cold/stateless evaluation includes the protocol on every request. Warm-session amortization is reported only as arithmetic simulation until actually measured, and cached tokens are never subtracted from provider totals. Python/Go/Rust comparisons are exploratory system comparisons because equivalent semantic protocols are not implemented for them.
