# Real-model paired pilot report

Evidence: `measured`; mode: `model`; provider: `openai-responses`; model: `gpt-5.6-luna`; settings: `{"max_output_tokens":2048,"reasoning":{"effort":"low"}}`.

| Suite | Accepted | compile@1 | pass@1 | Repairs median | Input mean | Output mean | Total / accepted |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline | 3/3 | 100% | 100% | 0 | 3,999.00 | 229.33 | 4,228.33 |
| optimized | 3/3 | 100% | 100% | 0 | 2,133.00 | 162.00 | 2,295.00 |

Complete run: 6/6 accepted; 19,570 provider-reported total tokens.

Observed optimized-minus-baseline difference: -1,933.33 tokens (45.72% reduction).

Seeded paired-bootstrap 95% interval for the token difference: [-1,953.00, -1,916.00].

Decision: `not_preregistered`. This pilot did not preregister an acceptance non-inferiority margin.

## Interpretation limits

- The paired bootstrap is conditional on the observed cases and repetitions.
- An all-success pilot produces a degenerate empirical acceptance interval and does not prove population-level non-inferiority.
- The run covers one repository-change case and three paired repetitions; it is pilot evidence, not confirmatory proof.
- Provider token totals are measured. Prompt-section byte fields are not model-token estimates.
- Failed trials would remain in the numerator; this run had no failed or repair trials.
