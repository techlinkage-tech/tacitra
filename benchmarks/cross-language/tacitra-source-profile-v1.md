# Tacitra cross-language source profile v1

Use canonical Tacitra source. A program consists of declarations and executes
`fn main() -> Int`; the CLI prints that integer followed by a newline. Every
function has explicit parameter and return types:

```tacitra
fn name(value: Int, enabled: Bool) -> Int {
  let offset = 1;
  if enabled {
    value + offset
  } else {
    value
  }
}
```

Available scalar types are `Int`, `Bool`, and `String`; literals use decimal
integers, `true`, `false`, and double-quoted strings. Operators used here are
`+`, `-`, `*`, `/`, `==`, `<`, `<=`, `>`, `>=`, and `&&`. There are no implicit
returns or conversions. Blocks end in one result expression without a semicolon;
immutable locals use `let name = expression;`.

Declare and construct records in declaration-field order:

```tacitra
record Packet {
  value: Int,
  enabled: Bool,
}

new Packet { value: 4, enabled: true }
```

Recoverable errors use `Result[T, E]`, `Ok(value)`, and `Err(error)`. Consume both
variants with an exhaustive match in canonical order:

```tacitra
match result {
  Ok(value) => value,
  Err(message) => -1,
}
```

Use only these constructs. Validate with `tacitra check` and execute with
`tacitra run`.
