# Typed semantics and execution

## Types and declarations

`Int`, `Bool`, `String`, and `Unit` are primitive types. `Option[T]` and `Result[T, E]` are built-in constructed types; other named types must name a module record or union. User-defined generics and implicit conversions do not exist.

Every function parameter and result is explicit. Local and top-level immutable bindings infer exactly the initializer type. Function and union-constructor names are visible throughout the module. Top-level values become visible in source order. A local initializer can use earlier bindings in its lexical scope; branch and match-pattern bindings do not escape. Shadowing an outer scope is permitted, while a duplicate in one scope is rejected.

## Expressions

- Arithmetic and ordered comparison require `Int` operands.
- Boolean operators and `!` require `Bool`; `&&` and `||` short-circuit.
- Equality requires equal operand types and does not accept functions.
- Calls require the declared arity and argument types.
- An `if` condition is `Bool`, and its branch result types are identical.
- Record construction requires every declared field exactly once, in declaration order, and no unknown fields.
- Field access requires a record and a declared field.
- `Some(value)` can infer `Option` from its payload. `None()` needs an expected `Option` type.
- `Ok(value)` and `Err(value)` need an expected `Result` type because one component is otherwise unknown.

## Pattern matching

`match` accepts only `Option`, `Result`, or a declared tagged union. An arm names an exact variant. Payload variants require one binding; payload-free variants forbid one. Each variant occurs once and all variants must be covered in type declaration order (`Some` then `None`, or `Ok` then `Err`). Every arm returns the same type. There is no wildcard or nested pattern in Milestone 2.

## Checked HIR and execution

Successful analysis produces typed HIR in which every expression has a resolved `Type` and every name refers to a declaration-order `SymbolId`. Any lexer, parser, name, or type diagnostic prevents HIR execution.

`tacitra run FILE` evaluates module bindings in dependency order and invokes `fn main() -> T` with no parameters. Cyclic initialization is rejected. It prints the canonical value. `--json` prints `{"type":...,"value":...}`. Integer operations are checked; division by zero and overflow are runtime diagnostics. There are no external effects in this milestone.
