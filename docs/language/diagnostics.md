# Diagnostic codes

Diagnostics are sorted by start byte, then code, then message. JSON diagnostics always contain `code`, `severity`, `message`, `span`, `expected_type`, and `actual_type`; the type fields are `null` when not applicable.

## Lexer and parser

- `L0001` unexpected character; `L0002` unterminated string; `L0003` unsupported escape.
- `P0001`–`P0015` base declaration/expression grammar failures.
- `P0016`–`P0052` typed signature, algebraic declaration, record, `if`, and `match` grammar failures.

## Names and types

- `N0001` duplicate definition.
- `N0002` undefined value name.
- `N0003` undefined type or record name.
- `T0001` expected and actual types differ.
- `T0002` expression is not callable or constructor call syntax is missing.
- `T0003` call arity differs.
- `T0005` invalid equality operand.
- `T0008` unknown record field.
- `T0009` missing record field.
- `T0010` field access on a non-record.
- `T0011` invalid match target or foreign variant.
- `T0012` non-exhaustive match.
- `T0013` duplicate match arm.
- `T0014` union payload pattern mismatch.
- `T0015` algebraic constructor lacks required expected type.
- `T0016` invalid `main` signature.
- `T0017` record values use non-canonical field order.
- `T0018` match arms use non-canonical variant order.

## Runtime

- `R0001` division by zero.
- `R0002` integer overflow.
- `R0003` missing executable `main`.
- `R0004` cyclic top-level initialization.
- `R0099` violated checked-HIR invariant; this indicates an implementation defect.

Agent-protocol `A0001`–`A0007` codes are specified in `docs/agent-protocol.md` because they report query or patch failures rather than compiler failures.

External-module `I0001`–`I0013` codes are specified in `docs/interop.md`. They report manifest, policy, process, protocol, and boundary-value failures rather than Tacitra source failures.
