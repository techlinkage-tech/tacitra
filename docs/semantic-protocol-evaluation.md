# Semantic protocol v1 evaluation

This experiment compares an AI-oriented Tacitra system with ordinary source workflows; it is not a source-language-only comparison. The confirmatory contrast is `tacitra-semantic` minus `tacitra-ordinary`. Python, Go, and Rust ordinary workflows are exploratory contrasts.

Phase A reaggregates immutable `cross-language-v1` raw data. Phase B uses six development cases and `utf8-bytes/1` for selection only. Phase C freezes 60 new held-out cases (30 repository changes and 30 diagnostic repairs), one trial per five representations, for 300 independent-condition calls. References and graders are never included in prompts. The semantic prompt carries the task exactly once inside the capsule.

The pinned model is `gpt-5.6-luna`, reasoning effort `low`, max output 2,048 tokens, at most two repairs, and a seeded interleaved order. Failed attempts stay in the total-token numerator. Provider input, output, cached input, reasoning and total tokens, compile/pass@1, acceptance, repair rounds, patch bytes, and time are retained verbatim. No model substitution is allowed.

The primary decision requires a paired case-bootstrap one-sided token upper bound below zero, an exact one-sided acceptance-loss upper bound at or below 5%, and semantic acceptance in both categories. Sixty independent cases give a 4.87% upper bound with zero losses (`1 - 0.05^(1/60)`). Repetitions do not inflate the sample size.

Cold single task is one complete stateless request. Stateless repeated task is the preregistered real-model condition. Warm sessions are not mixed into it: the fixed protocol is arithmetically amortized over 1, 10, and 100 tasks and marked projected until a stateful experiment is separately frozen.

## Reproduction

```sh
python3 benchmarks/semantic_protocol_static.py --output benchmarks/semantic-protocol/static-analysis-v1.json
python3 benchmarks/semantic_protocol.py validate
python3 benchmarks/semantic_protocol.py dry-run
# Only after explicit approval:
python3 benchmarks/semantic_protocol.py run --env-file .env.local
python3 benchmarks/semantic_protocol.py aggregate --raw benchmarks/results/semantic-protocol-v1/raw.jsonl --output benchmarks/results/semantic-protocol-v1/aggregate.json
python3 benchmarks/semantic_protocol_compare.py --raw benchmarks/results/semantic-protocol-v1/raw.jsonl --output benchmarks/results/semantic-protocol-v1/comparison.json
python3 benchmarks/semantic_protocol_report.py --comparison benchmarks/results/semantic-protocol-v1/comparison.json --output docs/semantic-protocol-results.md
```

Raw output and its append-only event journal refuse overwrite. Credentials are read only at execution and are never serialized.
