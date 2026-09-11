# Task-scoped specification profiles

The files under `benchmarks/specs/tacitra-*-v1.md` are versioned, concise projections of the accepted language and tool specifications. They do not define an alternate Tacitra dialect. `syntax.md`, `semantics.md`, and the relevant protocol document remain authoritative.

A benchmark or agent task may use a profile only when all syntax, types, semantics, diagnostics, and operations needed by that task are stated in it. If a task uses an omitted construct—such as records, unions, pattern matching, or an unlisted patch operation—the applicable full specification or another versioned supplement must be supplied and counted. Profiles cannot add syntax, weaken validation, or change execution semantics.

Version one provides a scalar/function core plus separate diagnostic, structural-edit, and one-export interoperability supplements. This selection rule keeps specification context bounded without introducing multiple spellings for one program meaning.
