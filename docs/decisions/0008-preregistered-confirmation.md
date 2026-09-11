# ADR 0008: Adopt Milestone 6 projections after preregistered confirmation

- Status: Accepted
- Date: 2026-09-11

## Context

The first real-model pilot observed a 45.72% token reduction, but used one development case, three pairs, and no preregistered accuracy threshold. It could not justify adoption. A confirmation needed cases not used to select the optimization, enough baseline-success pairs to bound lost successes, and a frozen decision rule.

## Decision

Freeze 20 new cases, four in each benchmark category, with three repetitions for 60 pairs. Use the same `gpt-5.6-luna` low-reasoning configuration and a seeded interleaved schedule. Require the paired-bootstrap token-difference interval to remain below zero, at least one optimized success in every category, and a one-sided 95% upper bound of at most 5% for optimized failures among baseline-accepted pairs.

With zero observed losses, 60 baseline successes give an exact one-sided binomial upper bound of 4.8703%, making 60 the smallest round-number design above the required threshold. Hash the harness, prompt, case builder, comparison/report code, configuration, and all baseline/optimized case inputs before execution. Reject a run if any hash or fixed count changes.

The retained run met every gate: 60/60 successes in each condition, zero repairs, a 4.8703% accepted-loss upper bound, and a provider-token difference interval of [-1,508.60, -1,297.57]. The primary metric changed from 3,506.73 to 2,102.68 tokens per accepted solution, an observed 40.04% reduction. Adopt the task-scoped specification, semantic edit context, and external call context for covered tasks, retaining full-query fallback for omitted information.

## Consequences

Milestone 6 optimization is supported for the frozen cases and model condition. The decision does not assert superiority over Python, Go, or Rust, nor generalize to other models, larger programs, or repair-heavy tasks. Profiles must continue enforcing their coverage rule. Cross-model replication or new task classes require new preregistration and separately retained evidence.
