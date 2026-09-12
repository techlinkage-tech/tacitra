# ADR 0013: Evaluate task capsules with familiar edit outputs

- Status: accepted for evaluation
- Date: 2026-09-12

## Context

Semantic protocol v1 reduced input and visible output relative to ordinary Tacitra, but reasoning tokens rose from 4,147 to 20,490 and total tokens per accepted solution worsened from 911.90 to 1,065.87. Its compact tuple was byte-efficient but unfamiliar to the pinned model. Public Tacitra syntax was not the measured bottleneck.

## Decision

Keep the human language unchanged. Compare one ordinary baseline and four task-capsule workflows: unified diff, ordinary source fragment, readable named edit, and the frozen compact-tuple control. All capsule workflows receive the same task packet, including the same editable source fragment; only the required output contract differs. Every output passes through the same stale-hash, semantic-target, parser, type-checker, formatter, execution, and source-diff boundary.

Use a 12-case, two-repetition development pilot to select among diff, fragment, and named edit. Compact tuple is a control, not a selection candidate. Proceed to a separately preregistered 60-case confirmation only when an eligible candidate beats ordinary total provider tokens per accepted solution. Keep stateless requests primary and use a common minimal repair-information rule without resending the complete initial capsule prompt.

## Consequences

Source fragments minimize model-side protocol construction but rely on compiler-side binding to an explicit content hash and semantic ID. Named edits provide schema-readable fields but are longer. Unified diffs remain familiar but require models to reproduce diff syntax. Pilot results are selection evidence only. No Python, Go, or Rust advantage may be inferred from this Tacitra-only experiment.
