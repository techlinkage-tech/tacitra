# ADR 0010: Preregistered cross-language source comparison

- Status: accepted
- Date: 2026-09-11

## Context

The retained `confirmation-v1` result measures two Tacitra context protocols. It
does not isolate the effect of choosing Tacitra rather than Python, Go, or Rust.
A language comparison can be biased if Tacitra alone receives semantic queries,
structural patches, tuned cases, or a different feedback budget.

## Decision

Create an independent `cross-language-v1` primary evaluation with 85 previously
unused, language-neutral cases. Each case has one frozen implementation and the
same observable result in all four languages. Complete generation returns source;
repository change and diagnostic repair return unified diffs in every language.
No language receives semantic queries or structural patches.

Use one common information-selection rule, prompt template, persistent
instruction, maximum output, repair limit, model condition, and seeded
interleaved schedule. Language-native syntax, type systems, compilers,
formatters, and standard libraries remain part of the language effect. Tacitra's
minimum specification is supplied and counted; familiar languages receive only
their small execution profiles rather than artificial filler.

The primary metric is failure-inclusive provider-reported total tokens divided
by accepted solutions. The three paired contrasts are Tacitra minus Python, Go,
and Rust. Cases, not repair attempts, are the independent unit. Use a 20,000-draw
case-cluster bootstrap and a Bonferroni family-wise one-sided alpha of `0.05/3`.
For the success gate, use the exact one-sided upper bound on Tacitra losses among
comparator-accepted cases with a 5% non-inferiority limit.

With zero losses, 80 comparator-accepted cases make this upper bound 4.9892%.
Freeze 85 cases so the target remains reachable with up to 5% comparator
nonacceptance. One attempt plus at most two repairs gives 340 trials and at most
1,020 provider calls.

The protocol-assisted comparison is not run in version one because equivalent
semantic-query and structural-edit protocols do not yet exist for Python, Go,
and Rust.

## Consequences

The primary result can support a language advantage only if all three adjusted
token intervals favor Tacitra, all three success non-inferiority gates pass, and
Tacitra succeeds in every category. Passing only some comparisons is reported as
partial advantage. Pretrained familiarity with established languages is retained
as a real deployment property, while ecosystem-heavy tasks are excluded.

This suite is deliberately larger and more expensive than `confirmation-v1`.
Its frozen preregistration and content hashes prevent post-result changes to
cases, prompts, settings, schedule, harness, comparison, or report logic.
