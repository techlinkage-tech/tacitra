# Static reference benchmark report

Evidence: `measured`; mode: `static_reference`; tokenizer: `utf8-bytes/1`.

This report measures retained reference artifacts with a local byte tokenizer. It is not a model-generation or LLM-token benchmark.

| Category | Representation | Success | total / accepted | Input median | Output median | Variance |
|---|---|---:|---:|---:|---:|---:|
| debug-repair | go-diagnostic-patch | 3/3 | 9174.0 | 9016 | 158 | 0 |
| debug-repair | python-diagnostic-patch | 3/3 | 9158.0 | 9000 | 158 | 0 |
| debug-repair | rust-diagnostic-patch | 3/3 | 9149.0 | 9014 | 135 | 0 |
| debug-repair | tacitra-diagnostic-patch | 3/3 | 15829.0 | 15687 | 142 | 0 |
| generation | go-source | 3/3 | 8978.0 | 8835 | 143 | 0 |
| generation | python-source | 3/3 | 8960.0 | 8857 | 103 | 0 |
| generation | rust-source | 3/3 | 8966.0 | 8834 | 132 | 0 |
| generation | tacitra-source | 3/3 | 13560.0 | 13465 | 95 | 0 |
| interop | go-worker | 3/3 | 15152.0 | 14530 | 622 | 0 |
| interop | python-worker | 3/3 | 16655.0 | 15608 | 1047 | 0 |
| interop | rust-worker | 3/3 | 15253.0 | 14531 | 722 | 0 |
| interop | tacitra-interop-call | 3/3 | 15449.0 | 15426 | 23 | 0 |
| repository-change | go-source-patch | 3/3 | 9141.0 | 8988 | 153 | 0 |
| repository-change | python-source-patch | 3/3 | 9114.0 | 8963 | 151 | 0 |
| repository-change | rust-source-patch | 3/3 | 9091.0 | 8962 | 129 | 0 |
| repository-change | tacitra-semantic-patch | 3/3 | 18192.0 | 17973 | 219 | 0 |
| repository-change | tacitra-source-patch | 3/3 | 13715.0 | 13579 | 136 | 0 |
| syntax | go-source | 3/3 | 8989.0 | 8890 | 99 | 0 |
| syntax | python-source | 3/3 | 8965.0 | 8912 | 53 | 0 |
| syntax | rust-source | 3/3 | 8964.0 | 8889 | 75 | 0 |
| syntax | tacitra-source | 3/3 | 13581.0 | 13520 | 61 | 0 |

Failed trials remain in raw data and in the numerator of the primary metric.
