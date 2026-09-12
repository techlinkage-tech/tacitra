# Cross-language-v1 evaluation protocol

## Purpose and separation

`cross-language-v1` measures the source-language effect of Tacitra, Python, Go,
and Rust under one model condition. It is independent of `confirmation-v1` and
does not compare Tacitra baseline and optimized contexts. The existing
confirmation inputs, results, and hashes are unchanged.

The primary evaluation gives all four languages the same natural-language task
and information-selection rule. Generation responses are complete source files;
change and repair responses are unified diffs. Tacitra semantic queries and
structural patches are prohibited. A protocol-assisted secondary evaluation is
not run because the other three languages do not yet have frozen equivalent
protocols.

## Frozen cases

The suite contains 85 independent cases:

| Category | Cases | Required output |
|---|---:|---|
| Complete generation | 29 | complete source |
| Local repository change | 28 | unified diff |
| Diagnostic repair | 28 | unified diff |

The language-neutral definitions cover function composition, branches, locals,
integers, booleans, strings, records, explicit error handling, changes across
multiple functions, boundary values, and type/name diagnostics. Each case has
four frozen reference fixtures and one observable integer result. All 340
references passed their native compile/check and execution commands before the
suite was frozen. Cases from prior Tacitra optimization experiments are rejected
by the builder.

Generation gets no repository source. Both change categories get exactly one
source file. Diagnostic repair additionally gets the first failing native
compiler/check/test result, stored as deterministic JSON with stdout and stderr
limited to their last 4,096 bytes. Reference artifacts and acceptance results are
never placed in model input. No external packages are used.

## Sample size and inference

There are three primary comparisons. Bonferroni controls the one-sided
family-wise error rate at 5%, making each comparison's alpha `0.05 / 3`. For zero
Tacitra losses among comparator-accepted cases, the exact upper bound is

```text
1 - (0.05 / 3)^(1 / n)
```

It first falls at or below the 5% non-inferiority limit at `n = 80` (4.9892%;
`n = 79` gives 5.0507%). The design freezes `ceil(80 / 0.95) = 85` unique cases,
allowing up to 5% comparator nonacceptance. Repeated attempts are not independent
observations. Token and acceptance differences use a 20,000-draw paired
case-cluster bootstrap with seed `20260912`.

For Python, Go, and Rust separately, reports contain acceptance, compile/pass at
one, failure-inclusive total tokens per accepted solution, Tacitra-minus-
comparator differences, adjusted intervals, Tacitra losses among comparator
successes, the exact adjusted one-sided upper bound, and category results.

The frozen classifications are `supports_language_advantage`,
`supports_partial_advantage`, `inconclusive`, and
`does_not_support_advantage`. Full advantage requires all three comparisons to
have an adjusted token upper bound below zero, an adjusted loss upper bound no
greater than 5%, and at least one accepted Tacitra trial in every category.

## Model, schedule, and evidence

The condition matches `confirmation-v1`: OpenAI Responses, model
`gpt-5.6-luna`, low reasoning effort, and 2,048 maximum output tokens. No model
substitution is allowed. Temperature is not sent because that pinned model
condition did not use it. There is one trial per language and case, at most two
repair rounds, and at most three attempts per trial. Seed `20260912` shuffles
cases and rotates/reverses four-language blocks to limit time-order bias.

Raw JSONL retains every reconstructed input, response, provider usage including
cached input and reasoning tokens, artifact, attempt, validation result, and wall
time. An adjacent event journal preserves starts, completions, and interruptions.
Writes refuse to overwrite existing raw data. Credentials and environment values
are never serialized.

The frozen preregistration is
[`preregistration-v1.json`](../benchmarks/cross-language/preregistration-v1.json),
revision `sha256:f55adce47d3e7734e0d756c3ee6dfb5fba946a8968667cc8d1e6b20aeef2d325`.
It pins cases, definitions, prompt, persistent instructions, configuration and
schema, seeded schedule, builder, runner, comparison, and report code.

## Phase A reproduction

These commands do not call the model API:

```sh
cargo build --locked -p tacitra-cli
python3 benchmarks/cross-language/build_cases.py validate
python3 benchmarks/cross_language.py validate
python3 benchmarks/cross_language.py dry-run
python3 -m unittest benchmarks.tests.test_cross_language
python3 scripts/check_confirmation.py
```

The case builder refuses to regenerate after preregistration. The dry run uses a
fake provider that returns each frozen reference artifact through the production
prompt, decoding, patching, validation, raw-record, and scheduling paths.

## Phase B commands (not yet authorized or run)

After explicit approval, execute the frozen run exactly once:

```sh
python3 benchmarks/cross_language.py run --env-file .env.local
python3 benchmarks/cross_language.py aggregate \
  --raw benchmarks/results/cross-language-v1/raw.jsonl \
  --output benchmarks/results/cross-language-v1/aggregate.json
python3 benchmarks/cross_language_compare.py \
  --raw benchmarks/results/cross-language-v1/raw.jsonl \
  --output benchmarks/results/cross-language-v1/comparison.json \
  --bootstrap-samples 20000 --seed 20260912
python3 benchmarks/cross_language_report.py \
  --aggregate benchmarks/results/cross-language-v1/aggregate.json \
  --comparison benchmarks/results/cross-language-v1/comparison.json \
  --output benchmarks/results/cross-language-v1/report.md
```

## Pre-run budget and remaining confounds

Using the median provider-token/UTF-8-byte ratios from 120 retained
`confirmation-v1` trials, the estimated first-attempt total is 187,287 provider
tokens. There are 340 calls if no repair is needed and at most 1,020 calls. A
deliberately conservative three-attempt/output-limit ceiling is 1,954,501 tokens.
These values are estimates, not measurements.

The frozen preregistration recorded no dollar estimate because an official rate
had not yet been confirmed during Phase A. Immediately before the approved Phase
B run, official documentation showed $0.20 per million input tokens, $0.02 per
million cached input tokens, and $1.20 per million output tokens. The frozen
configuration and token projections were not changed.

The main remaining confounds are model pretraining familiarity, irreducible
differences in native type systems and diagnostics, unequal but rule-selected
specification length, language toolchain behavior, small synthetic programs, one
model and one trial per case, and time-varying provider infrastructure. The first
three are intentional components of practical language choice; the others limit
generalization.
