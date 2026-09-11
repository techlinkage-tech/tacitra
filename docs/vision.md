# Vision

Tacitra is a programming language and tool protocol optimized for **accepted changes per total LLM token**, not for visual terseness. A compact program that needs a long specification, ambiguous repairs, or repeated compiler conversations is a regression.

## Design thesis

Existing coding models transfer knowledge best from regular, familiar constructs. Tacitra therefore uses a small canonical surface language, explicit semantics, a typed canonical AST/IR as the eventual semantic authority, deterministic tools, and concise machine-readable feedback. The language should let an agent request only the symbol, type, dependency, effect, or repair context it needs.

The intended feedback loop is:

1. retrieve a bounded task and relevant semantic context;
2. generate source or a structural patch;
3. validate it without hidden effects;
4. receive stable, localized diagnostics;
5. repair only the affected semantic nodes;
6. accept after tests and contracts pass.

## Principles

- Optimize correctness per total token, including failed attempts.
- Give each meaning one canonical source representation.
- Prefer syntax recognizable from Python, TypeScript, Go, and Rust.
- Make diagnostics stable, ordered, short, and actionable.
- Keep dependencies, types, effects, capabilities, and contracts queryable.
- Keep foreign boundaries small and typed.
- Require reproducible measurements before claiming improvement.

## Boundaries

Milestones 0–1 establish measurement and the deterministic syntax front end. Type checking, evaluation, structural AI patches, and interoperability are deliberate future extension points, not partial features in the current implementation.
