# Known limitations

- One source file is one module; there are no imports, packages, or multi-file name
  resolution.
- There are no bounded collections in Tacitra source, language test/contract syntax,
  language-level effects, generics, traits, advanced inference, macros, closures,
  concurrency, native code generation, or package registry.
- The interpreter is experimental and has no resource budget. User programs cannot
  perform external effects, while a deeply nested or expensive pure program can
  still consume CPU or stack.
- Semantic IDs survive formatting, comments, and small body changes, but not renames
  or arbitrary structural rearrangement. Patch v1 supports only function-body and
  expression replacement in one file.
- `patch.apply` removes comments through canonical formatting and does not provide
  transactional coordination with another process editing the same file.
- JSON schemas cover public protocol artifacts; serialized internal AST/HIR is not
  a stable interchange format.
- External interop is one-shot, synchronous-at-the-controller, trusted-command
  execution. It has no OS sandbox, persistent worker, streaming, callback, native
  FFI, or direct call syntax inside Tacitra.
- The measured confirmation uses one model, small programs, and no repair rounds.
  Its 40.04% observed token reduction does not establish a cross-model result,
  superiority over Python/Go/Rust, or performance on large repositories.
- Property tests use deterministic generated corpora for reproducibility; continuous
  coverage-guided fuzzing and formal resource-exhaustion bounds remain future work.
