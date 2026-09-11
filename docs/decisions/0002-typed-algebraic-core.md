# ADR 0002: Typed algebraic core and checked execution

- Status: Accepted
- Date: 2026-09-11

## Context

Milestone 2 requires a compact typed semantic foundation, algebraic data, exhaustive matching, and execution. The earlier roadmap placed algebraic data and interpretation in Milestone 3, but the approved Milestone 2 request explicitly brings them forward. ADR 0001 deferred the canonical spelling of types.

## Decision

Functions now require `name: Type` on every parameter and `-> Type` before the body. This intentionally replaces the provisional untyped Milestone 1 function syntax before language stabilization. Bindings remain immutable and infer their type from the initializer; there is no second annotated binding spelling.

Primitive types are `Int`, `Bool`, `String`, and `Unit`; the unit value is `()`. Constructed types use `Option[T]` and `Result[T, E]`. Their constructors are the reserved calls `Some(value)`, `None()`, `Ok(value)`, and `Err(value)`. `None`, `Ok`, and `Err` require an expected type when unconstrained components cannot be inferred.

Records use `record Name { field: Type, }`, field access uses `.`, and values use `new Name { field: value }`. Tagged unions use `union Name { Tag, Tag(Type), }`; each tag is a module-level constructor called with zero or one argument. Record and union declarations require a trailing comma for every member. Record values have no trailing comma and retain declared-field checking.

`if condition { value } else { value }` is an expression and both branches must agree. `match value { Tag(binding) => value, Tag => value, }` is an expression. Match arms require trailing commas, may destructure exactly one payload, and must cover every `Option`, `Result`, or declared-union variant exactly once in declaration order. Record values likewise follow field declaration order. These order checks preserve one accepted canonical representation per meaning.

The compiler lowers valid AST into source-positioned typed HIR with stable, declaration-order `SymbolId` values. Invalid programs never expose executable HIR. `run` invokes a zero-argument `main`, evaluates immutable bindings, and prints its value; JSON mode returns a `{type,value}` object.

## Consequences

The syntax remains recognizable while having one formatter-controlled representation. Separate type and value namespaces allow a type and function to share a name; duplicate names within either namespace are rejected. Local scopes may shadow outer scopes but not redefine a name in the same scope. Function declarations and union constructors are module-wide; top-level values are introduced in source order.

This milestone has no generics beyond the built-in `Option` and `Result`, no user-defined generic types, traits, macros, full closures, concurrency, effects, external modules, or native backend.
