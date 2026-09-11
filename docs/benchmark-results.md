# Initial benchmark results

## Evidence boundary

The retained run is [`static-reference-v1`](../benchmarks/results/static-reference-v1/). It contains 63 measured static-reference trials: five categories, 21 representations, and three repetitions. All 63 reference artifacts passed their declared compile/check and behavioral tests.

The tokenizer is `utf8-bytes/1`, exactly one token per retained UTF-8 byte. The environment had no OpenAI, Anthropic, or Google model credential, so no model was called. `model` is `null`, settings are `{}`, and repair rounds are zero in every raw row. Consequently, the 63/63 result measures reference-fixture validity, not model success probability.

## Selected measured results

All values below are `measured` under `static_reference`; they must not be interpreted as LLM token counts.

| Category | Representation | total tokens / accepted | Output tokens | Success |
|---|---|---:|---:|---:|
| generation | Python source | 8,960 | 103 | 3/3 |
| generation | Go source | 8,978 | 143 | 3/3 |
| generation | Rust source | 8,966 | 132 | 3/3 |
| generation | Tacitra source | 13,560 | 95 | 3/3 |
| syntax | Python source | 8,965 | 53 | 3/3 |
| syntax | Go source | 8,989 | 99 | 3/3 |
| syntax | Rust source | 8,964 | 75 | 3/3 |
| syntax | Tacitra source | 13,581 | 61 | 3/3 |
| repository change | Tacitra source patch | 13,715 | 136 | 3/3 |
| repository change | Tacitra semantic patch with bounded query | 18,192 | 219 | 3/3 |

The Tacitra generated source is smaller than the three conventional-language reference sources in these tiny cases, but the required Tacitra specification makes its measured total larger. The semantic-query route is also larger for the tiny repository case because the current 917-byte detailed symbol response plus agent-protocol specification exceeds the 86-byte source module. This run therefore does not demonstrate an end-to-end token saving. Larger repository cases and real model trials are needed to test the intended advantage.

The complete per-category table, including diagnostic repair and interoperability, is in [`report.md`](../benchmarks/results/static-reference-v1/report.md). Component counts, patch sizes, compile/pass rates, wall-clock mean/median/population variance, hashes, tool versions, and trial IDs are in [`aggregate.json`](../benchmarks/results/static-reference-v1/aggregate.json) and [`raw.jsonl`](../benchmarks/results/static-reference-v1/raw.jsonl).

Total-token variance is zero within each three-run group because tokenized artifacts are fixed. Wall-clock variance is non-zero and retained as a secondary metric. The harness has explicit tests proving that a failed trial remains stored and its token total remains in the primary metric numerator.
