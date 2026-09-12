# Semantic protocol v2 confirmation results

The preregistered Phase 3 decision is `supports_semantic_protocol_v2`. This is measured confirmatory evidence for `capsule-fragment` versus ordinary Tacitra editing on this task suite and `gpt-5.6-luna`; it is not evidence that Tacitra outperforms Python, Go, or Rust.

The executable preregistration SHA-256 is `2cc188bef0bc575986f1723ad7e726a404f400fa58a46b94ca0012eea80fc433`. All 60 unused cases were run once per condition in the frozen seeded order. Both conditions accepted 60/60, with compile@1 and pass@1 both 100% and no repairs.

| Condition | Accepted | Tokens / accepted | Input | Visible output | Reasoning | Cached | Mean edit bytes | Wall time |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ordinary | 60/60 | 854.68 | 39,840 | 11,441 | 3,308 | 0 | 361.92 | 176.18 s |
| capsule-fragment | 60/60 | 616.97 | 31,747 | 5,271 | 3,756 | 0 | 47.37 | 123.44 s |

The paired difference (`capsule-fragment - ordinary`) was -237.72 provider tokens per accepted solution, a 27.81% observed reduction. The 20,000-draw paired case-bootstrap 95% interval was [-248.90, -226.38]. There were zero optimized losses among 60 ordinary-accepted cases; the exact one-sided 95% upper bound was 4.8703%, below the frozen 5% limit. Repair rounds and repair-output tokens were zero in both conditions.

## Category results

| Category | Condition | Accepted | compile@1 | pass@1 | Tokens / accepted |
|---|---|---:|---:|---:|---:|
| debug-repair | ordinary | 30/30 | 100% | 100% | 849.80 |
| debug-repair | capsule-fragment | 30/30 | 100% | 100% | 582.60 |
| repository-change | ordinary | 30/30 | 100% | 100% | 859.57 |
| repository-change | capsule-fragment | 30/30 | 100% | 100% | 651.33 |

Phase 3 consumed 88,299 provider tokens; Phase 2 and Phase 3 together consumed 295,584, below the frozen 750,000 limit. Provider totals include every trial and would include every repair; reasoning and cached counts are subsets and are not added twice.

## Evidence and limitations

Raw attempts, complete prompts and responses, generated artifacts, validation results, provider usage, events, aggregates, comparison, category breakdown, preflight environment, and hashes are retained under `benchmarks/results/semantic-protocol-v2/`. The evidence manifest itself has SHA-256 `e3b038032aa1604d3babd54688c91c03c0a8bc3bb3b2d2c6b7fa01b9f65659f4`.

The cases had unique requirements, initial sources, and whole-case revisions versus 218 prior cases. Ten short reference-fragment content hashes also occurred in prior suites, and 22 unique fragment contents occur more than once within Phase 3 because distinct tasks can share a small correct expression; this is retained in the case manifest. The test covers one model, simple single-file tasks, stateless calls, zero cache use, and no observed repair path. It does not isolate every capsule component or establish general language superiority.

Recompute the derived files without another API call:

```sh
python3 benchmarks/semantic_protocol_v2_confirmation.py postrun --output /tmp/semantic-protocol-v2-recomputed
```

The original run command refuses to overwrite retained raw results:

```sh
python3 benchmarks/semantic_protocol_v2_confirmation.py run --env-file .env.local
```
