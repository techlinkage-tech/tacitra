# Real-model evaluation

The model harness runs the existing baseline and Milestone 6 optimized representations through one artifact-generation loop. It uses the retained compile and success commands, supplies validation feedback for at most the case's two repair rounds, records failed attempts, and obtains token totals from the provider response.

## Configure

Copy `benchmarks/model/config.example.json` to an ignored `benchmarks/model/pilot.local.json`. Replace `SET_PINNED_MODEL_ID` with the exact model identifier available to the account. Pin every supported setting explicitly; do not add a setting that the selected model rejects. Keep the same file for both conditions.

Set `OPENAI_API_KEY` in the process environment, or pass `--env-file .env.local` to read only that key without executing the file as a shell script. The key is used only in the Authorization header and is not written to results. `OPENAI_BASE_URL` defaults to `https://api.openai.com/v1`; endpoint URLs containing credentials, a query, or a fragment are rejected.

```sh
python3 benchmarks/model_harness.py validate \
  --suite baseline --config benchmarks/model/pilot.local.json
python3 benchmarks/model_harness.py validate \
  --suite optimized --config benchmarks/model/pilot.local.json
```

## Pilot

Start with one paired repository-change or generation case. `paired-run` interleaves both conditions with the config's fixed schedule seed and starts each API call without server-side conversation state.

```sh
python3 benchmarks/model_harness.py paired-run \
  --config benchmarks/model/pilot.local.json \
  --output benchmarks/results/model-pilot-v1/raw.jsonl \
  --run-id model-pilot-v1 \
  --case repository-increment \
  --representation tacitra-semantic-patch \
  --repetitions 3

python3 benchmarks/model_harness.py aggregate \
  --raw benchmarks/results/model-pilot-v1/raw.jsonl \
  --output benchmarks/results/model-pilot-v1/aggregate.json

python3 benchmarks/model_compare.py \
  --paired benchmarks/results/model-pilot-v1/raw.jsonl \
  --output benchmarks/results/model-pilot-v1/comparison.json \
  --bootstrap-samples 10000 --seed 20260911
```

The raw file contains the actual reconstructed input, response, decoded artifact, provider usage, validation result, and per-attempt elapsed time. The reference solution is used only indirectly through its already-declared artifact filename/validation commands and is never read into the prompt.

## Evidence and decision gates

Pilot results calibrate prompts and variance and are not confirmatory evidence. After the pilot, freeze new evaluation cases that were not used to select Milestone 6 changes. Record the intended number of repetitions and an accuracy non-inferiority margin before running them.

A confirmatory optimization should be accepted only when:

- baseline and optimized use the exact same model condition and paired cases;
- the lower bound for optimized-minus-baseline acceptance is above the preregistered non-inferiority margin;
- the paired interval for total tokens per accepted solution supports a reduction;
- no category shows an unexplained repair-cost or failure concentration.

For a confirmatory run, add the margin fixed before execution, for example `--acceptance-noninferiority-margin -0.05`. This example value is illustrative rather than an approved threshold; select and record the actual margin from pilot variance and product risk before opening held-out results. The comparison emits `supports_adoption`, `reject`, `inconclusive`, or `not_preregistered`.

Provider `input_tokens`, `output_tokens`, and `total_tokens` are measured model tokens. Cached-input and reasoning tokens are informational subsets and are not added again. Prompt-section fields ending in `_bytes` are measured bytes for attribution audits, not estimates of model tokens.

## First retained pilot

[`benchmarks/results/model-pilot-v1`](../benchmarks/results/model-pilot-v1/) contains the first credentialed run: `gpt-5.6-luna`, low reasoning, three paired repository-change semantic-patch trials per suite. All six trials passed compile and tests on the first attempt. Total tokens per accepted solution measured 4,228.33 for baseline and 2,295.00 for optimized, a 1,933.33-token (45.72%) observed reduction. The paired empirical bootstrap interval was [-1,953, -1,916].

This is pilot evidence only. It uses one development case that informed the optimization, has no failed examples, and did not preregister an acceptance non-inferiority margin. Its comparison classification is therefore `not_preregistered`, not `supports_adoption`. See the retained [`report.md`](../benchmarks/results/model-pilot-v1/report.md).

## Preregistered confirmation

Confirmation-v1 froze 20 new cases, 60 pairs, the same model condition, and a maximum 5% accepted-loss rate before execution. All 120 trials passed on the first attempt. The primary metric measured 3,506.73 baseline versus 2,102.68 optimized provider tokens per accepted solution (-40.04%). The preregistered result is `supports_adoption`; see the [full interpretation](model-confirmation-results.md) and [machine-readable preregistration](../benchmarks/confirmation/preregistration-v1.json).
