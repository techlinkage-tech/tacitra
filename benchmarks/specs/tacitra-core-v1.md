# Tacitra core task profile v1

The full language specification remains authoritative. For these integer tasks, use only canonical `fn name(arg: Int) -> Int { expression }`, decimal integers, calls with parentheses, and `+`, `-`, `*`, or `/`. Blocks end in one result expression without a semicolon. Bindings, when needed, are immutable `let name = expression;`. Execution calls `fn main() -> Int` with no arguments and prints its value. There are no implicit returns, conversions, optional semicolons, or alternate spellings. Validate with `tacitra check` and execute with `tacitra run`.
