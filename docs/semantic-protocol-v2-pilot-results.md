# Semantic protocol v2 pilot results

The measured development-pilot winner is `capsule-fragment`. This is candidate-selection evidence, not a confirmatory improvement claim. Executable preregistration v3 is `sha256:a888e06939a625fcd047fe649fbf7f0a79a4e7df27d3c51329d80b2965c55d85`; retained v1/v2 registrations were abandoned before any provider call.

| Condition | Accepted | compile@1 | pass@1 | Total / accepted | Input | Visible output | Reasoning | Cached | Repairs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ordinary | 24/24 | 100% | 100% | 856.88 | 15,936 | 4,629 | 1,490 | 0 | 0 |
| capsule + unified diff | 0/24 | 0% | 0% | not estimable | 23,375 | 28,624 | 23,359 | 0 | 48 |
| capsule + source fragment | 24/24 | 100% | 100% | 615.29 | 12,680 | 2,087 | 1,481 | 0 | 0 |
| capsule + named edit | 0/24 | 0% | 0% | not estimable | 25,393 | 29,099 | 21,497 | 0 | 48 |
| compact tuple control | 0/24 | 0% | 0% | not estimable | 25,167 | 40,295 | 32,611 | 0 | 48 |

Fragment preserved all ordinary successes in both categories and reduced failure-inclusive total tokens per accepted solution by 241.58, an observed 28.19%. Input fell 20.43%, visible output 54.92%, and reasoning 0.60%. Debug repair measured 588.00 versus ordinary 847.75; repository change measured 642.58 versus 866.00.

Diff outputs consistently omitted valid unified-diff hunk ranges. Named outputs changed required schema values such as integer `version: 1` and the exact operation name. Compact outputs changed tuple fields into an invented object form. Each failed all three attempts, so their full 144 repair rounds and provider cost remain in the result. Total pilot usage was 207,285 provider tokens across 264 calls; 48/120 condition trials were accepted.

The preregistered selection gates therefore select fragment and permit a separate confirmation. No Python, Go, or Rust comparison is implied.
