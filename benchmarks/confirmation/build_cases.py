#!/usr/bin/env python3
"""Build and validate the frozen-input candidates for confirmation-v1."""

from __future__ import annotations

import difflib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "benchmarks/confirmation"
SHARED = BASE / "shared"
TACITRA = ROOT / "target/debug/tacitra"


SOURCE_CASES = [
    ("heldout-syntax-call", "syntax", "Write a complete Tacitra program with `fn combine(left: Int, right: Int) -> Int` returning their sum. `main` must call it with 17 and 25 and return 42.", "fn combine(left: Int, right: Int) -> Int {\n  left + right\n}\n\nfn main() -> Int {\n  combine(17, 25)\n}\n"),
    ("heldout-syntax-locals", "syntax", "Write a complete Tacitra program whose `main` binds immutable `base = 39` and `increment = 3`, then returns their sum 42.", "fn main() -> Int {\n  let base = 39;\n  let increment = 3;\n  base + increment\n}\n"),
    ("heldout-syntax-composition", "syntax", "Write a complete Tacitra program defining `double(value: Int) -> Int` and `add_two(value: Int) -> Int`. Compose them in `main` so the program returns 42 from input 20.", "fn double(value: Int) -> Int {\n  value * 2\n}\n\nfn add_two(value: Int) -> Int {\n  value + 2\n}\n\nfn main() -> Int {\n  add_two(double(20))\n}\n"),
    ("heldout-syntax-division", "syntax", "Write a complete Tacitra program defining `halve(value: Int) -> Int` and calling it from `main` with 84 so the result is 42.", "fn halve(value: Int) -> Int {\n  value / 2\n}\n\nfn main() -> Int {\n  halve(84)\n}\n"),
    ("heldout-generation-adjust", "generation", "Generate a complete Tacitra program with `adjust(value: Int, offset: Int) -> Int`. Use it from `main` to turn 37 and 5 into 42.", "fn adjust(value: Int, offset: Int) -> Int {\n  value + offset\n}\n\nfn main() -> Int {\n  adjust(37, 5)\n}\n"),
    ("heldout-generation-product", "generation", "Generate a complete Tacitra program with `area(width: Int, height: Int) -> Int`. `main` must return the area for 6 by 7, which is 42.", "fn area(width: Int, height: Int) -> Int {\n  width * height\n}\n\nfn main() -> Int {\n  area(6, 7)\n}\n"),
    ("heldout-generation-pipeline", "generation", "Generate a complete Tacitra program defining `triple(value: Int) -> Int` and `subtract_three(value: Int) -> Int`. Compose them in `main` with 15 to return 42.", "fn triple(value: Int) -> Int {\n  value * 3\n}\n\nfn subtract_three(value: Int) -> Int {\n  value - 3\n}\n\nfn main() -> Int {\n  subtract_three(triple(15))\n}\n"),
    ("heldout-generation-balance", "generation", "Generate a complete Tacitra program whose `main` uses immutable `gross = 50` and `fee = 8` bindings and returns the balance 42.", "fn main() -> Int {\n  let gross = 50;\n  let fee = 8;\n  gross - fee\n}\n"),
]

REPOSITORY_CASES = [
    ("heldout-repository-shift", "shift", "Change only function `shift` so it adds 4 instead of 3. Keep `main` unchanged; the result must become 42.", "value + 3", "value + 4", 38),
    ("heldout-repository-scale", "scale", "Change only function `scale` so it multiplies by 7 instead of 6. Keep `main` unchanged; the result must become 42.", "value * 6", "value * 7", 6),
    ("heldout-repository-charge", "charge", "Change only function `charge` so it subtracts 8 instead of 9. Keep `main` unchanged; the result must become 42.", "value - 9", "value - 8", 50),
    ("heldout-repository-halve", "halve", "Change only function `halve` so it divides by 2 instead of 3. Keep `main` unchanged; the result must become 42.", "value / 3", "value / 2", 84),
]

DEBUG_CASES = [
    ("heldout-debug-offset", "Fix the undefined name in `compute` with the smallest source change so `main` returns 42.", "fn compute(value: Int) -> Int {\n  value + offset\n}\n\nfn main() -> Int {\n  compute(40)\n}\n", "fn compute(value: Int) -> Int {\n  value + 2\n}\n\nfn main() -> Int {\n  compute(40)\n}\n"),
    ("heldout-debug-call", "Fix the undefined function reference in `compute` with the smallest source change so `main` returns 42.", "fn compute(value: Int) -> Int {\n  missing(value)\n}\n\nfn main() -> Int {\n  compute(40)\n}\n", "fn compute(value: Int) -> Int {\n  value + 2\n}\n\nfn main() -> Int {\n  compute(40)\n}\n"),
    ("heldout-debug-local", "Fix the undefined local initializer in `compute` with the smallest source change so `main` returns 42.", "fn compute(value: Int) -> Int {\n  let step = delta;\n  value + step\n}\n\nfn main() -> Int {\n  compute(40)\n}\n", "fn compute(value: Int) -> Int {\n  let step = 2;\n  value + step\n}\n\nfn main() -> Int {\n  compute(40)\n}\n"),
    ("heldout-debug-top-level", "Fix the undefined top-level initializer with the smallest source change so `main` returns 42.", "let offset = missing;\n\nfn main() -> Int {\n  40 + offset\n}\n", "let offset = 2;\n\nfn main() -> Int {\n  40 + offset\n}\n"),
]

INTEROP_CASES = [
    ("heldout-interop-add", "add", "Produce the JSON arguments for external export `add` so the typed call returns 42."),
    ("heldout-interop-subtract", "subtract", "Produce the JSON arguments for external export `subtract` so the typed call returns 42."),
    ("heldout-interop-multiply", "multiply", "Produce the JSON arguments for external export `multiply` so the typed call returns 42."),
    ("heldout-interop-affine", "affine", "Produce the JSON arguments for external export `affine` so the typed call returns 42."),
]

INTEROP_ARGUMENTS = {
    "add": {"left": 19, "right": 23},
    "subtract": {"left": 50, "right": 8},
    "multiply": {"left": 6, "right": 7},
    "affine": {"value": 8, "factor": 5, "offset": 2},
}


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, value: object) -> None:
    write(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def command(*arguments: str, expected: int = 0) -> str:
    result = subprocess.run(arguments, cwd=ROOT, capture_output=True, text=True, check=False)
    if result.returncode != expected:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(arguments)}\n{result.stderr}")
    return result.stdout


def canonical(source: str) -> str:
    temporary = BASE / ".canonical-input.taci"
    write(temporary, source)
    output = command(str(TACITRA), "fmt", str(temporary))
    temporary.unlink()
    return output


def unified_patch(before: str, after: str) -> str:
    return "".join(difflib.unified_diff(
        before.splitlines(keepends=True), after.splitlines(keepends=True),
        fromfile="program.taci", tofile="program.taci",
    ))


def representation(kind: str, optimized: bool, shared: Path, **values) -> dict:
    shared_prefix = f"../../../shared/{shared.name}"
    full_prefix = "../../../../../docs"
    brief_prefix = "../../../../specs"
    if kind == "source":
        specifications = [f"{brief_prefix}/tacitra-core-v1.md"] if optimized else [
            f"{full_prefix}/language/syntax.md", f"{full_prefix}/language/semantics.md"]
        return {
            "id": "tacitra-source", "language": "tacitra", "surface": "human-source",
            "artifact": f"{shared_prefix}/reference.taci", "artifact_kind": "source",
            "specification": specifications, "repository_context": [], "diagnostic_context": [],
            "setup_files": [], "prepare_commands": [],
            "compile_commands": [["{repo}/target/debug/tacitra", "check", "{artifact}"]],
            "test_commands": [["{repo}/target/debug/tacitra", "run", "{artifact}"]],
            "result_kind": "integer",
        }
    if kind == "repository":
        specifications = [f"{brief_prefix}/tacitra-core-v1.md", f"{brief_prefix}/tacitra-edit-v1.md"] if optimized else [
            f"{full_prefix}/language/syntax.md", f"{full_prefix}/language/semantics.md", f"{full_prefix}/agent-protocol.md"]
        context = "edit-context.json" if optimized else "describe.json"
        return {
            "id": "tacitra-semantic-patch", "language": "tacitra", "surface": "semantic-query",
            "artifact": f"{shared_prefix}/reference.patch.json", "artifact_kind": "patch",
            "specification": specifications, "repository_context": [f"{shared_prefix}/{context}"],
            "diagnostic_context": [],
            "setup_files": [{"source": f"{shared_prefix}/base.taci", "target": "program.taci"}],
            "prepare_commands": [["{repo}/target/debug/tacitra", "patch.apply", "{work}/program.taci", "{artifact}"]],
            "compile_commands": [["{repo}/target/debug/tacitra", "check", "{work}/program.taci"]],
            "test_commands": [["{repo}/target/debug/tacitra", "run", "{work}/program.taci"]],
            "result_kind": "integer",
        }
    if kind == "debug":
        specifications = [f"{brief_prefix}/tacitra-core-v1.md", f"{brief_prefix}/tacitra-diagnostic-v1.md"] if optimized else [
            f"{full_prefix}/language/syntax.md", f"{full_prefix}/language/semantics.md", f"{full_prefix}/language/diagnostics.md"]
        return {
            "id": "tacitra-diagnostic-patch", "language": "tacitra", "surface": "human-source",
            "artifact": f"{shared_prefix}/reference.patch", "artifact_kind": "patch",
            "specification": specifications, "repository_context": [f"{shared_prefix}/base.taci"],
            "diagnostic_context": [f"{shared_prefix}/diagnostic.json"],
            "setup_files": [{"source": f"{shared_prefix}/base.taci", "target": "program.taci"}],
            "prepare_commands": [["patch", "--silent", "{work}/program.taci", "{artifact}"]],
            "compile_commands": [["{repo}/target/debug/tacitra", "check", "{work}/program.taci"]],
            "test_commands": [["{repo}/target/debug/tacitra", "run", "{work}/program.taci"]],
            "result_kind": "integer",
        }
    manifest = "{repo}/benchmarks/confirmation/shared/interop-worker/manifest.json"
    specifications = [f"{brief_prefix}/tacitra-interop-call-v1.md"] if optimized else [f"{full_prefix}/interop.md"]
    context = f"{shared_prefix}/call-context.json" if optimized else "../../../shared/interop-worker/manifest.json"
    export = values["export"]
    return {
        "id": "tacitra-interop-call", "language": "tacitra", "surface": "interop-manifest",
        "artifact": f"{shared_prefix}/reference.arguments.json", "artifact_kind": "arguments",
        "specification": specifications, "repository_context": [context], "diagnostic_context": [],
        "setup_files": [], "prepare_commands": [],
        "compile_commands": [["{repo}/target/debug/tacitra", "interop.inspect", manifest]],
        "test_commands": [["{repo}/target/debug/tacitra", "interop.call", manifest, export, "{artifact}"]],
        "result_kind": "json-result",
    }


def write_case(case_id: str, category: str, kind: str, prompt: str, **values) -> None:
    shared = SHARED / case_id
    write(shared / "prompt.md", prompt + "\n")
    for optimized in (False, True):
        suite = "optimized" if optimized else "baseline"
        document = {
            "schema_version": 2,
            "id": case_id,
            "category": category,
            "prompt": f"../../../shared/{case_id}/prompt.md",
            "acceptance": {"description": "generated change returns integer 42", "expected_integer": 42},
            "max_repair_rounds": 2,
            "representations": [representation(kind, optimized, shared, **values)],
        }
        write_json(BASE / suite / "cases" / case_id / "case.json", document)


def write_interop_worker() -> None:
    int_type = {"kind": "int", "signed": True, "bits": 64}
    exports = []
    parameters = {
        "add": ["left", "right"],
        "subtract": ["left", "right"],
        "multiply": ["left", "right"],
        "affine": ["value", "factor", "offset"],
    }
    for name, names in parameters.items():
        exports.append({
            "name": name,
            "parameters": [{"name": item, "type": int_type} for item in names],
            "result": int_type,
            "error": None,
            "mode": "sync",
            "effects": [],
            "capabilities": [],
            "ownership": "copy",
            "examples": [{
                "description": f"{name} example yielding 42",
                "arguments": INTEROP_ARGUMENTS[name],
                "result": 42,
            }],
        })
    manifest = {
        "schema_version": 1,
        "module": "confirmation_math",
        "transport": {
            "kind": "stdio-json-rpc", "protocol_version": "2.0",
            "command": ["python3", "worker.py"], "timeout_ms": 1000,
        },
        "exports": exports,
    }
    worker = '''import json
import sys


def dispatch(method, values):
    if method == "add":
        return values["left"] + values["right"]
    if method == "subtract":
        return values["left"] - values["right"]
    if method == "multiply":
        return values["left"] * values["right"]
    if method == "affine":
        return values["value"] * values["factor"] + values["offset"]
    raise KeyError(method)


request = json.loads(sys.stdin.readline())
response = {"jsonrpc": "2.0", "id": request["id"], "result": dispatch(request["method"], request["params"]), "meta": {"effects": [], "capabilities": []}}
print(json.dumps(response, separators=(",", ":"), sort_keys=True))
'''
    write_json(SHARED / "interop-worker/manifest.json", manifest)
    write(SHARED / "interop-worker/worker.py", worker)


def build() -> None:
    if not TACITRA.is_file():
        raise RuntimeError("build target/debug/tacitra first")
    for case_id, category, prompt, source in SOURCE_CASES:
        shared = SHARED / case_id
        write(shared / "reference.taci", canonical(source))
        write_case(case_id, category, "source", prompt)

    for case_id, function, prompt, before_expression, after_expression, argument in REPOSITORY_CASES:
        before = canonical(f"fn {function}(value: Int) -> Int {{\n  {before_expression}\n}}\n\nfn main() -> Int {{\n  {function}({argument})\n}}\n")
        shared = SHARED / case_id
        write(shared / "base.taci", before)
        describe = command(str(TACITRA), "symbol.describe", str(shared / "base.taci"), f"sym:fn:{function}")
        edit = command(str(TACITRA), "symbol.edit-context", str(shared / "base.taci"), f"sym:fn:{function}")
        write(shared / "describe.json", describe)
        write(shared / "edit-context.json", edit)
        content_hash = json.loads(edit)["content_hash"]
        write_json(shared / "reference.patch.json", {
            "schema_version": 1,
            "base_hash": content_hash,
            "operations": [{
                "op": "replace_function_body", "target": f"sym:fn:{function}",
                "replacement": f"{{ {after_expression} }}",
            }],
        })
        write_case(case_id, "repository-change", "repository", prompt)

    for case_id, prompt, before_source, after_source in DEBUG_CASES:
        before = canonical(before_source)
        after = canonical(after_source)
        shared = SHARED / case_id
        write(shared / "base.taci", before)
        diagnostic = command(str(TACITRA), "check", "--json", str(shared / "base.taci"), expected=1)
        write(shared / "diagnostic.json", diagnostic)
        write(shared / "reference.patch", unified_patch(before, after))
        write_case(case_id, "debug-repair", "debug", prompt)

    write_interop_worker()
    manifest = SHARED / "interop-worker/manifest.json"
    command(str(TACITRA), "interop.inspect", str(manifest))
    for case_id, export, prompt in INTEROP_CASES:
        shared = SHARED / case_id
        write_json(shared / "reference.arguments.json", INTEROP_ARGUMENTS[export])
        write(shared / "call-context.json", command(
            str(TACITRA), "external.call-context", str(manifest), export))
        write_case(case_id, "interop", "interop", prompt, export=export)


def validate_references() -> None:
    harness_path = ROOT / "benchmarks/harness.py"
    spec = importlib.util.spec_from_file_location("confirmation_static_harness", harness_path)
    harness = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = harness
    spec.loader.exec_module(harness)
    accepted = 0
    for suite in ("baseline", "optimized"):
        harness.BENCHMARKS = BASE / suite
        cases = harness.discover_cases()
        if len(cases) != 20:
            raise RuntimeError(f"{suite} has {len(cases)} cases instead of 20")
        for case_path, case in cases:
            row = harness.run_representation(
                case_path, case, case["representations"][0], "confirmation-reference", 1, 30)
            if not row["accepted"]:
                raise RuntimeError(f"reference failed: {suite}/{case['id']}: {row['failure']}")
            accepted += 1
    print(json.dumps({"valid": True, "cases_per_suite": 20, "accepted_references": accepted}))


if __name__ == "__main__":
    build()
    validate_references()
