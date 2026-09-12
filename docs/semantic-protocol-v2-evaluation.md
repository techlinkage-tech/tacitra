# Semantic protocol v2 evaluation

This evaluation tests whether task-scoped semantic context combined with familiar model output reduces total provider tokens relative to ordinary Tacitra. It does not change public syntax and does not compare Tacitra with Python, Go, or Rust.

The development pilot has 12 cases—six repository changes and six diagnostic repairs—disjoint from previous experiments. Two repetitions across ordinary, capsule+diff, capsule+fragment, capsule+named edit, and compact control produce 120 trials and at most 360 calls. Candidate eligibility requires no more than 5% observed losses on ordinary-accepted trials and acceptance in both categories. Eligible candidates are ranked by failure-inclusive total tokens per accepted solution, then reasoning tokens. Confirmation stops if all are worse than ordinary. Executable preregistration v3 is `sha256:a888e06939a625fcd047fe649fbf7f0a79a4e7df27d3c51329d80b2965c55d85`; v1/v2 were retained but abandoned before provider access after reproducibility checks exposed missing or conflicting pins.

The selected `capsule-fragment` candidate was confirmed on 60 new independent cases, 30 per category, against ordinary editing for 120 trials. The Phase 3 preregistration is `sha256:2cc188bef0bc575986f1723ad7e726a404f400fa58a46b94ca0012eea80fc433`. Its decision required a one-sided 95% acceptance-loss upper bound no greater than 5%, paired-bootstrap token upper bound below zero, at least 5% observed reduction, success in both categories, and no environment/provider invalidation; all gates passed. See [confirmation results](semantic-protocol-v2-results.md).

Both phases pin `gpt-5.6-luna`, low reasoning effort, 2,048 maximum output tokens, two repairs, stateless execution, seeded interleaving, all input revisions, and a combined 750,000-provider-token stop. Cached and reasoning tokens remain subsets of provider totals. Failed trials and all repairs remain in the numerator.

Estimated usage before API access is 117,754 tokens per phase and 235,508 total, derived from retained semantic-protocol-v1 Tacitra trials. At the historical mean per attempt, all 720 allowed calls project to 637,465 tokens. These are estimates, not measurements. Dollar cost is not estimated because the current exact model price could not be verified.

## Reproduction

```sh
python3 benchmarks/semantic_protocol_v2.py preflight-pilot --env-file .env.local
python3 benchmarks/semantic_protocol_v2.py run-pilot --env-file .env.local
python3 benchmarks/semantic_protocol_v2.py aggregate --raw benchmarks/results/semantic-protocol-v2-pilot/raw.jsonl --output benchmarks/results/semantic-protocol-v2-pilot/aggregate.json
python3 benchmarks/semantic_protocol_v2_compare.py --phase pilot --raw benchmarks/results/semantic-protocol-v2-pilot/raw.jsonl --output benchmarks/results/semantic-protocol-v2-pilot/comparison.json
python3 benchmarks/semantic_protocol_v2_report.py --aggregate benchmarks/results/semantic-protocol-v2-pilot/aggregate.json --comparison benchmarks/results/semantic-protocol-v2-pilot/comparison.json --output docs/semantic-protocol-v2-pilot-results.md
```

The retained Phase 3 run can be regenerated without provider access with:

```sh
python3 benchmarks/semantic_protocol_v2_confirmation.py postrun --output /tmp/semantic-protocol-v2-recomputed
```

Raw and event files refuse overwrite; `--resume` skips retained trial IDs.
