# ADR 0001: Canonical minimal surface syntax

- Status: Accepted
- Date: 2026-09-11

## Context

Milestone 1 needs syntax familiar to existing coding models while avoiding equivalent spellings, newline-sensitive parsing, and formatter ambiguity. It must leave room for a typed semantic representation without pretending that type checking already exists.

## Decision

Use ASCII identifiers and keywords, decimal integers, `true`/`false`, immutable `let name = expression;` bindings, and `fn name(parameters) { ... }` functions. Parameters are comma-separated. Blocks contain zero or more semicolon-terminated `let` bindings followed by exactly one result expression without a semicolon. Top-level declarations are `let` or `fn`; top-level bindings require a semicolon.

Calls use parentheses. Grouping uses parentheses. Operators have one fixed precedence table: `||`, `&&`, equality, comparison, addition/subtraction, multiplication/division, unary `!`/`-`, then calls. Binary operators associate left. There are no optional semicolons, alternate function bodies, mutable bindings, implicit returns, or operator aliases.

The formatter emits two-space indentation, one blank line between top-level declarations, normalized spaces, and a final newline. Source spans use UTF-8 byte offsets plus one-based line and column positions.

## Consequences

The grammar resembles common languages and is deterministic to parse and format. Mandatory delimiters cost some tokens but reduce repair ambiguity; benchmarks will determine whether that trade is beneficial. Parameter and return types are intentionally absent until Milestone 2, when their single canonical spelling will be decided in a new ADR. The untyped, source-positioned AST is not the future semantic authority but provides an explicit boundary for a typed IR.
