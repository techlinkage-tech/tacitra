# Tacitra AI surface v1 profile

Return one compact typed edit JSON object: `{"v":1,"h":HASH,"cap":[],"ops":[OP...]}`.
Copy `HASH` from the task capsule. An operation is
`["body",FUNCTION_ID,"{ result_expression }"]` or
`["expr",EXPRESSION_ID,"replacement_expression"]`. Replacements use canonical
Tacitra syntax and must match the target type. Multiple operations are atomic.
Use only IDs, values, types, calls, and capabilities present in the capsule.
