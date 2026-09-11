# Reproducible benchmark harness

Case schema version 2 stores one shared task and acceptance contract plus every compared representation's reference artifact, specification, repository context, supplied diagnostic, setup, and argument-array commands. The five retained categories are syntax compression, complete generation, repository change, diagnostic repair, and external-module use.

Representations use the same result normalization and expected integer inside a case. Python, Go, Rust, and Tacitra source use language-specific pinned profiles. Tacitra cases always count the declared Tacitra specification. The repository-change case additionally compares full Tacitra source plus a normal diff against a bounded `symbol.describe` response plus a structural patch.

## Reproduce

Requirements are Python 3.12+, Go, Rust 1.85+, GNU `patch`, and a built Tacitra CLI. No Python packages or network access are needed.

```sh
cargo build --workspace
python3 benchmarks/harness.py validate
python3 benchmarks/harness.py run \
  --output benchmarks/results/local/raw.jsonl \
  --run-id local --repetitions 3
python3 benchmarks/harness.py aggregate \
  --raw benchmarks/results/local/raw.jsonl \
  --output benchmarks/results/local/aggregate.json
python3 benchmarks/harness.py report \
  --aggregate benchmarks/results/local/aggregate.json \
  --output benchmarks/results/local/report.md
python3 -m unittest benchmarks/tests/test_harness.py
```

Milestone 6 keeps the baseline cases immutable and stores task-scoped profiles under `optimized/`. Reproduce the specification-only intermediate stage and complete after run with:

```sh
TACITRA_BENCHMARK_PROFILE=stage1 python3 benchmarks/run_optimized.py validate
TACITRA_BENCHMARK_PROFILE=stage1 python3 benchmarks/run_optimized.py run \
  --output benchmarks/results/m6-optimization-v1/stage1.raw.jsonl \
  --run-id m6-stage1-spec-profiles-v1 --repetitions 3
python3 benchmarks/run_optimized.py run \
  --output benchmarks/results/m6-optimization-v1/after.raw.jsonl \
  --run-id m6-optimized-v1 --repetitions 3
python3 benchmarks/compare.py \
  --before benchmarks/results/m6-optimization-v1/before.aggregate.json \
  --after benchmarks/results/m6-optimization-v1/after.aggregate.json \
  --output benchmarks/results/m6-optimization-v1/comparison.json
```

If `rustc` is not on `PATH`, set `RUSTC` to its absolute path. `--case CASE_ID` may be repeated for a focused run. The runner continues after failures and writes every trial with bounded failure output. Aggregation revalidates raw rows and rejects mixed tokenizer or evidence modes.

## Evidence status

[`results/static-reference-v1`](results/static-reference-v1/) is measured with the pinned local `utf8-bytes/1` tokenizer. It measures reference artifacts and acceptance commands, not model generation. No available API credential was present for the initial run; model, temperature, sampling, repair, and model success metrics remain unmeasured. Future model runs must record a non-null model identifier, fixed settings, tokenizer revision, attempt budget, and every failed attempt in a distinct result set.

The byte tokenizer is intentionally simple: one retained UTF-8 byte is one token. Its counts are exact and reproducible but are neither estimates nor projections of LLM subword tokens. See [`docs/benchmark-results.md`](../docs/benchmark-results.md) for interpretation.

## Real-model pilot

`model_harness.py` uses the same case-v2 suites and validation commands, but generates artifacts with one pinned model, retains every repair attempt in model-result schema v3, and uses provider-reported token totals. `paired-run` interleaves baseline and optimized conditions with a fixed seed. `model_compare.py` calculates failure-inclusive paired results and bootstrap intervals.

No key or model ID is stored. Copy `model/config.example.json` to the ignored `model/pilot.local.json`, pin an available exact model and settings, and export `OPENAI_API_KEY` only in the process environment. See [`docs/model-evaluation.md`](../docs/model-evaluation.md) for pilot, aggregation, comparison, and confirmatory decision procedures.

The first retained credentialed result is [`results/model-pilot-v1`](results/model-pilot-v1/): six accepted `gpt-5.6-luna` trials on one paired repository-change representation. Read its report limitations before interpreting the observed token difference.

The preregistered [`confirmation-v1`](confirmation/preregistration-v1.json) suite adds 20 unused cases and 60 pairs. Its retained [`model-confirmation-v1`](results/model-confirmation-v1/) run passed all frozen adoption gates; see [`docs/model-confirmation-results.md`](../docs/model-confirmation-results.md). Rebuilding cases or changing any pinned evaluation file invalidates the preregistration and is rejected by the confirmation runner.
