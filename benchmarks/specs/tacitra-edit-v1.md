# Tacitra semantic edit profile v1

`symbol.edit-context FILE ID` returns a canonical module `content_hash`, typed function identity, a `body_target`, and typed leaf expressions with current values; it intentionally omits spans and graph detail. Patch v1 is `{"schema_version":1,"base_hash":"sha256:...","operations":[{"op":"replace_function_body","target":"sym:fn:name","replacement":"{ expression }"}]}`. The hash rejects stale edits. `patch.apply` parses, type-checks, canonically formats, and atomically writes only a valid result.
