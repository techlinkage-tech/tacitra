# Tacitra external call profile v1

`external.call-context MANIFEST EXPORT` returns one validated function's module/name, parameters, result, error, sync/async mode, effects, capabilities, ownership, and one example without worker source or launch command. Call it with `interop.call MANIFEST EXPORT ARGUMENTS.json`; arguments are a JSON object named exactly like the parameters. The result is `{"valid":true,"result":value,"observed_effects":[],"observed_capabilities":[]}`. Required effects or capabilities need explicit allow flags.
