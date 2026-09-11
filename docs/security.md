# Security boundaries

Tacitra source execution is deterministic and has no language-level file, network,
process, or environment operations in 0.1.0. Integer overflow and division by zero
produce diagnostics. The parser, formatter, semantic patch parser, and patch
validator are tested against generated invalid UTF-8 text and JSON strings, but
these tests are not a proof of memory or resource safety.

External manifests are executable project configuration. `interop.call` starts the
declared command with the manifest directory as its working directory and inherits
the controller's environment, filesystem access, user identity, and operating-system
permissions. Process isolation prevents a foreign panic or exception from unwinding
through Rust, but it is not a sandbox. Effect/capability declarations are policy
checks for cooperative workers and cannot detect omitted activity by malicious code.
Review manifests and workers, restrict OS permissions or run them in a container,
and do not pass secrets unless the worker is trusted.

The controller validates boundary values, limits configured calls to 300 seconds,
kills and waits for timed-out children, and rejects malformed responses. It does not
set memory, CPU, output-size, syscall, filesystem, or network limits. Opaque handles
are unforgeable only to the extent enforced by the worker; the protocol treats them
as typed identity strings.

Model evaluation sends prompts and selected repository context to the configured
provider endpoint. Raw results preserve those inputs and outputs and may be
sensitive. `OPENAI_API_KEY` is read from the environment or ignored `.env.local`
file, is never serialized by the harness, and must never be committed. Releasing
the retained model artifacts requires a separate review for proprietary source,
personal data, provider-policy obligations, and prompt-injection content.
