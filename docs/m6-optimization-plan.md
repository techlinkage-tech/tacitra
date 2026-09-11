# Milestone 6 optimization record

## Preserved baseline

The immutable before-run is [`static-reference-v1`](../benchmarks/results/static-reference-v1/), with 63/63 accepted static-reference trials. [`before.aggregate.json`](../benchmarks/results/m6-optimization-v1/before.aggregate.json) was regenerated from that raw JSONL before implementation.

Measured aggregate component totals were 536,823 instruction, 155,292 specification, 20,265 repository context, 13,668 output, 10,974 task, 1,083 diagnostic, and zero repair byte-tokens, for 738,105 total. Persistent instructions were 72.7% and specifications 21.0% of the retained total; those percentages are derived measured values from the preserved raw rows.

The requested bottleneck split is therefore: persistent instructions 536,823; language specification 155,292; repository reading 20,265; code/patch generation 13,668; diagnostics 1,083; and repair iteration 0. Two non-additive task subsets make the specialized costs visible: external-module API information was 1,786 per interop trial (5,358 over three trials), while the repository structural-edit representation used a 917-token semantic query plus a 219-token patch per trial (3,408 over three trials). These subsets are already included in repository context and output and are not added again.

Relevant measured before medians were:

| Task / representation | Specification | Repository | Output | Total | Success |
|---|---:|---:|---:|---:|---:|
| generation / Tacitra source | 4,790 | 0 | 95 | 13,560 | 3/3 |
| debug repair / Tacitra patch | 6,668 | 93 | 142 | 15,829 | 3/3 |
| repository / Tacitra source diff | 4,790 | 86 | 136 | 13,715 | 3/3 |
| repository / semantic patch | 8,353 | 917 | 219 | 18,192 | 3/3 |
| interop / Tacitra call | 4,967 | 1,786 | 23 | 15,449 | 3/3 |

## Selected hypotheses

### O1: Task-scoped specification bundles

Hypothesis: most Tacitra benchmark tasks use only functions, integers, calls, and one CLI operation. A versioned concise core profile and operation-specific supplements can replace unrelated full-language chapters without changing accepted syntax or semantics. Expected metric: lower `specification_tokens` and total tokens for every Tacitra representation while preserving 3/3 acceptance.

Trade-off: the brief is valid only for tasks whose declared feature set it covers. The full specification remains authoritative and must be selected when algebraic types or other omitted constructs are needed.

### O2: Edit-context semantic query and function-body patch

Hypothesis: `symbol.describe` repeats spans, names, visibility, calls, and nested detail not needed to change a small function. A deterministic `symbol.edit-context` response containing the module hash, symbol ID/type, body target, and typed semantic leaves will lower repository-context tokens. Selecting the already supported `replace_function_body` operation should also lower patch bytes for this case. Expected metrics: lower repository context, patch size, and total tokens for `tacitra-semantic-patch`, with the same stale detection and post-patch type checking.

Trade-off: the compact response deliberately omits spans, call relationships, operators, and non-leaf expression nodes. Agents needing those facts must use the existing full query.

### O3: Function-scoped external call context

Hypothesis: calling one declared export does not require the full multi-export manifest. A deterministic `external.call-context` response plus a concise protocol profile can retain parameter/result/error/effect/capability/ownership/example information while omitting unrelated exports and launch details. Expected metrics: lower external API repository context and specification tokens with unchanged interop acceptance.

Trade-off: it cannot answer module-wide discovery questions and still trusts the separately validated manifest at execution time.

## Rejected before implementation

- Shortening `AGENTS.md`: it is the largest component but is shared governance supplied to every representation. Removing safety or measurement rules would change the experiment and project constraints rather than optimize Tacitra.
- Public syntax changes: Tacitra source output was only 61–95 byte-tokens in syntax/generation, while specification overhead was 4,790. Syntax risk is unsupported by the measured bottleneck.
- Compact diagnostic JSON: the entire measured diagnostic component was 1,083 of 738,105, and only one case consumed it. It is lower priority than specification and scoped context.
- Type or repair changes: the static run had 63/63 accepted, `repair_rounds = 0`, and `repair_tokens = 0`; there is no measured retry failure to optimize yet.

## Sequential measurements and decisions

All values below are measured with `utf8-bytes/1`; each affected representation has three trials. Stage 1 applies only O1 and retains the old query, patch, and full external manifest. The final stage adds O2 and O3. Raw stage and final rows are retained under [`m6-optimization-v1`](../benchmarks/results/m6-optimization-v1/).

| Representation | Before | After O1 | Final | Acceptance before/final |
|---|---:|---:|---:|---:|
| generation / Tacitra source | 13,560 | 9,359 | 9,359 | 3/3 / 3/3 |
| debug repair / Tacitra patch | 15,829 | 10,022 | 10,022 | 3/3 / 3/3 |
| repository / Tacitra source diff | 13,715 | 9,514 | 9,514 | 3/3 / 3/3 |
| repository / semantic patch | 18,192 | 10,964 | 10,432 | 3/3 / 3/3 |
| interop / Tacitra call | 15,449 | 11,018 | 9,627 | 3/3 / 3/3 |
| syntax / Tacitra source | 13,581 | 9,380 | 9,380 | 3/3 / 3/3 |

O1 was adopted: it reduced specification input in every affected case with no static fixture failure. O2 was adopted: the edit context fell from 917 to 393 tokens and its patch from 219 to 211, reducing the already-O1 repository semantic total by 532 (4.85%). O3 was adopted: call context fell from 1,786 to 395, reducing the already-O1 interop total by 1,391 (12.62%).

Across the complete 63-trial suite, total tokens changed from 738,105 to 642,129. `total_tokens_per_accepted_solution` changed from 11,715.95 to 10,192.52 (-13.00%), while accepted trials remained 63/63 (100%). Specification tokens changed 155,292 → 65,085 (-58.09%), repository context 20,265 → 14,520 (-28.35%), and output 13,668 → 13,644 (-0.18%). Instructions, task prompts, diagnostics, and repair were unchanged.

The accuracy/token trade-off is unresolved rather than assumed absent: static acceptance stayed 100%, but no model selected the right profile or acted on omitted query fields. LLM-token savings, model pass rate, and repair rounds are statistically unknown. Wall-clock timings are secondary and noisy and are not used to accept these changes.

## Reproduction

```sh
python3 benchmarks/harness.py aggregate \
  --raw benchmarks/results/static-reference-v1/raw.jsonl \
  --output benchmarks/results/m6-optimization-v1/before.aggregate.json
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
