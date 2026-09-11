# Confirmatory real-model evaluation report

Evidence: `measured`; mode: `model`; provider: `openai-responses`; model: `gpt-5.6-luna`; settings: `{"max_output_tokens":2048,"reasoning":{"effort":"low"}}`.

| Suite | Accepted | compile@1 | pass@1 | Repairs median | Input mean | Output mean | Total / accepted |
|---|---:|---:|---:|---:|---:|---:|---:|
| confirmation-baseline | 12/12 | 100% | 100% | 0.0 | 3,401.50 | 142.75 | 3,544.25 |
| confirmation-baseline | 12/12 | 100% | 100% | 0.0 | 2,786.75 | 124.42 | 2,911.17 |
| confirmation-baseline | 12/12 | 100% | 100% | 0.0 | 3,805.25 | 136.75 | 3,942.00 |
| confirmation-baseline | 12/12 | 100% | 100% | 0.0 | 3,996.75 | 227.08 | 4,223.83 |
| confirmation-baseline | 12/12 | 100% | 100% | 0.0 | 2,786.75 | 125.67 | 2,912.42 |
| confirmation-optimized | 12/12 | 100% | 100% | 0.0 | 2,030.50 | 146.00 | 2,176.50 |
| confirmation-optimized | 12/12 | 100% | 100% | 0.0 | 1,854.75 | 119.25 | 1,974.00 |
| confirmation-optimized | 12/12 | 100% | 100% | 0.0 | 1,946.25 | 123.17 | 2,069.42 |
| confirmation-optimized | 12/12 | 100% | 100% | 0.0 | 2,127.75 | 205.83 | 2,333.58 |
| confirmation-optimized | 12/12 | 100% | 100% | 0.0 | 1,854.75 | 105.17 | 1,959.92 |

Complete run: 120/120 accepted; 336,565 provider-reported total tokens.

Observed optimized-minus-baseline difference: -1,404.05 tokens (40.04% reduction).

Seeded paired-bootstrap 95% interval for the token difference: [-1,508.60, -1,297.57].

Decision: `supports_adoption`.

## Interpretation limits

- The paired bootstrap is conditional on the observed cases and repetitions.
- An all-success run produces a degenerate empirical acceptance-difference bootstrap interval; the separate one-sided accepted-loss bound is used for non-inferiority.
- Accepted-loss one-sided 95% upper bound: 4.87% against a 5.00% maximum.
- Provider token totals are measured. Prompt-section byte fields are not model-token estimates.
- Failed trials would remain in the numerator; this run had no failed or repair trials.
