#!/usr/bin/env python3
"""Build new semantic-protocol-v1 cases and validate all frozen references."""

from __future__ import annotations

import argparse
import difflib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "benchmarks/semantic-protocol"
CASES = BASE / "cases"
PREREG = BASE / "preregistration-v1.json"
LANGUAGES = ("python", "go", "rust", "tacitra")
EXT = {"python": "py", "go": "go", "rust": "rs", "tacitra": "taci"}
SPECS = {language: f"../../../specs/{language}-v1.md" for language in LANGUAGES}
SPECS["tacitra"] = "../../../cross-language/tacitra-source-profile-v1.md"

spec = importlib.util.spec_from_file_location("semantic_static", ROOT / "benchmarks/harness.py")
assert spec and spec.loader
STATIC = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = STATIC
spec.loader.exec_module(STATIC)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, value: object) -> None:
    write(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def wrap(language: str, body: str, call: str) -> str:
    if language == "python":
        noise = "def unrelated_alpha(value: int) -> int:\n    return value * 2\n\n\ndef unrelated_beta(value: int) -> int:\n    return value - 3\n\n\ndef unrelated_gamma(enabled: bool) -> int:\n    return 7 if enabled else 9"
        return f"{noise}\n\n\n{body}\n\n\nif __name__ == \"__main__\":\n    print({call})\n"
    if language == "go":
        noise = "func unrelatedAlpha(value int64) int64 { return value * 2 }\nfunc unrelatedBeta(value int64) int64 { return value - 3 }\nfunc unrelatedGamma(enabled bool) int64 { if enabled { return 7 }; return 9 }"
        return f'package main\n\nimport "fmt"\n\n{noise}\n\n{body}\n\nfunc main() {{ fmt.Println({call}) }}\n'
    if language == "rust":
        noise = "fn unrelated_alpha(value: i64) -> i64 { value * 2 }\nfn unrelated_beta(value: i64) -> i64 { value - 3 }\nfn unrelated_gamma(enabled: bool) -> i64 { if enabled { 7 } else { 9 } }"
        return f'{noise}\n\n{body}\n\nfn main() {{ println!("{{}}", {call}); }}\n'
    noise = "fn unrelated_alpha(value: Int) -> Int {\n  value * 2\n}\n\nfn unrelated_beta(value: Int) -> Int {\n  value - 3\n}\n\nfn unrelated_gamma(enabled: Bool) -> Int {\n  if enabled { 7 } else { 9 }\n}"
    return f"{noise}\n\n{body}\n\nfn main() -> Int {{\n  {call}\n}}\n"


def unified(before: str, after: str, filename: str) -> str:
    return "".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile=filename, tofile=filename))


def design(index: int) -> tuple[str, dict[str, str], dict[str, str], int]:
    name = f"solve_sp_{index:02d}"
    value = 30 + index
    old = 1 + index % 4
    new = 6 + index % 7
    kind = index % 4
    if kind == 0:
        task = f"Change `{name}` to add {new} instead of {old}. Keep the caller unchanged; it must print {value + new}."
        bodies = {
            "python": (f"def {name}(value: int) -> int:\n    return value + {old}", f"def {name}(value: int) -> int:\n    return value + {new}"),
            "go": (f"func {name}(value int64) int64 {{ return value + {old} }}", f"func {name}(value int64) int64 {{ return value + {new} }}"),
            "rust": (f"fn {name}(value: i64) -> i64 {{ value + {old} }}", f"fn {name}(value: i64) -> i64 {{ value + {new} }}"),
            "tacitra": (f"fn {name}(value: Int) -> Int {{\n  value + {old}\n}}", f"fn {name}(value: Int) -> Int {{\n  value + {new}\n}}"),
        }
        replacement = f"{{ value + {new} }}"
        expected = value + new
    elif kind == 1:
        task = f"Change `{name}` so the boundary is inclusive and the accepted branch adds {new}. The exact-boundary caller must print {value + new}."
        bodies = {
            "python": (f"def {name}(value: int, limit: int) -> int:\n    return 0 if value >= limit else value + {old}", f"def {name}(value: int, limit: int) -> int:\n    return value + {new} if value <= limit else 0"),
            "go": (f"func {name}(value int64, limit int64) int64 {{ if value >= limit {{ return 0 }}; return value + {old} }}", f"func {name}(value int64, limit int64) int64 {{ if value <= limit {{ return value + {new} }}; return 0 }}"),
            "rust": (f"fn {name}(value: i64, limit: i64) -> i64 {{ if value >= limit {{ 0 }} else {{ value + {old} }} }}", f"fn {name}(value: i64, limit: i64) -> i64 {{ if value <= limit {{ value + {new} }} else {{ 0 }} }}"),
            "tacitra": (f"fn {name}(value: Int, limit: Int) -> Int {{\n  if value >= limit {{ 0 }} else {{ value + {old} }}\n}}", f"fn {name}(value: Int, limit: Int) -> Int {{\n  if value <= limit {{ value + {new} }} else {{ 0 }}\n}}"),
        }
        replacement = f"{{ if value <= limit {{ value + {new} }} else {{ 0 }} }}"
        expected = value + new
    elif kind == 2:
        record = f"PacketSp{index:02d}"
        task = f"Change record-based `{name}` so an enabled packet adds {new} instead of {old}. It must print {value + new}."
        declarations = {
            "python": f"class {record}:\n    def __init__(self, value: int, enabled: bool):\n        self.value = value\n        self.enabled = enabled",
            "go": f"type {record} struct {{ value int64; enabled bool }}",
            "rust": f"struct {record} {{ value: i64, enabled: bool }}",
            "tacitra": f"record {record} {{\n  value: Int,\n  enabled: Bool,\n}}",
        }
        functions = {
            "python": (f"def {name}(packet: {record}) -> int:\n    return packet.value + {old} if packet.enabled else packet.value", f"def {name}(packet: {record}) -> int:\n    return packet.value + {new} if packet.enabled else packet.value"),
            "go": (f"func {name}(packet {record}) int64 {{ if packet.enabled {{ return packet.value + {old} }}; return packet.value }}", f"func {name}(packet {record}) int64 {{ if packet.enabled {{ return packet.value + {new} }}; return packet.value }}"),
            "rust": (f"fn {name}(packet: {record}) -> i64 {{ if packet.enabled {{ packet.value + {old} }} else {{ packet.value }} }}", f"fn {name}(packet: {record}) -> i64 {{ if packet.enabled {{ packet.value + {new} }} else {{ packet.value }} }}"),
            "tacitra": (f"fn {name}(packet: {record}) -> Int {{\n  if packet.enabled {{ packet.value + {old} }} else {{ packet.value }}\n}}", f"fn {name}(packet: {record}) -> Int {{\n  if packet.enabled {{ packet.value + {new} }} else {{ packet.value }}\n}}"),
        }
        calls = {"python": f"{name}({record}({value}, True))", "go": f"{name}({record}{{value: {value}, enabled: true}})", "rust": f"{name}({record} {{ value: {value}, enabled: true }})", "tacitra": f"{name}(new {record} {{ value: {value}, enabled: true }})"}
        before = {language: wrap(language, declarations[language] + "\n\n" + functions[language][0], calls[language]) for language in LANGUAGES}
        after = {language: wrap(language, declarations[language] + "\n\n" + functions[language][1], calls[language]) for language in LANGUAGES}
        return task, before, after, value + new
    else:
        task = f"Change `{name}` so zero is the only error and value {value} with divisor one returns {value}."
        bodies = {
            "python": (f"def {name}(value: int, divisor: int) -> tuple[bool, int]:\n    if divisor <= 1: return False, 0\n    return True, value // divisor\n\ndef consume(result: tuple[bool, int]) -> int:\n    ok, value = result\n    return value if ok else -1", f"def {name}(value: int, divisor: int) -> tuple[bool, int]:\n    if divisor == 0: return False, 0\n    return True, value // divisor\n\ndef consume(result: tuple[bool, int]) -> int:\n    ok, value = result\n    return value if ok else -1"),
            "go": (f"func {name}(value int64, divisor int64) (int64, bool) {{ if divisor <= 1 {{ return 0, false }}; return value / divisor, true }}\nfunc consume(value int64, ok bool) int64 {{ if ok {{ return value }}; return -1 }}", f"func {name}(value int64, divisor int64) (int64, bool) {{ if divisor == 0 {{ return 0, false }}; return value / divisor, true }}\nfunc consume(value int64, ok bool) int64 {{ if ok {{ return value }}; return -1 }}"),
            "rust": (f"fn {name}(value: i64, divisor: i64) -> Result<i64, &'static str> {{ if divisor <= 1 {{ Err(\"zero\") }} else {{ Ok(value / divisor) }} }}\nfn consume(result: Result<i64, &'static str>) -> i64 {{ match result {{ Ok(value) => value, Err(_) => -1 }} }}", f"fn {name}(value: i64, divisor: i64) -> Result<i64, &'static str> {{ if divisor == 0 {{ Err(\"zero\") }} else {{ Ok(value / divisor) }} }}\nfn consume(result: Result<i64, &'static str>) -> i64 {{ match result {{ Ok(value) => value, Err(_) => -1 }} }}"),
            "tacitra": (f"fn {name}(value: Int, divisor: Int) -> Result[Int, String] {{\n  if divisor <= 1 {{ Err(\"zero\") }} else {{ Ok(value / divisor) }}\n}}\n\nfn consume(result: Result[Int, String]) -> Int {{\n  match result {{ Ok(value) => value, Err(message) => -1, }}\n}}", f"fn {name}(value: Int, divisor: Int) -> Result[Int, String] {{\n  if divisor == 0 {{ Err(\"zero\") }} else {{ Ok(value / divisor) }}\n}}\n\nfn consume(result: Result[Int, String]) -> Int {{\n  match result {{ Ok(value) => value, Err(message) => -1, }}\n}}"),
        }
        replacement = '{ if divisor == 0 { Err("zero") } else { Ok(value / divisor) } }'
        expected = value
    if kind != 2:
        calls = {language: f"{name}({value})" for language in LANGUAGES}
        if kind == 1:
            calls = {language: f"{name}({value}, {value})" for language in LANGUAGES}
        elif kind == 3:
            calls = {language: f"consume({name}({value}, 1))" for language in LANGUAGES}
        before = {language: wrap(language, bodies[language][0], calls[language]) for language in LANGUAGES}
        after = {language: wrap(language, bodies[language][1], calls[language]) for language in LANGUAGES}
    return task, before, after, expected


def commands(language: str, target: str) -> tuple[list[list[str]], list[list[str]]]:
    if language == "python": return [["python3", "-m", "py_compile", target]], [["python3", target]]
    if language == "go": return [["go", "build", "-o", "{work}/program", target]], [["{work}/program"]]
    if language == "rust": return [["{rustc}", "--edition=2021", "--crate-name", "program", "-o", "{work}/program", target]], [["{work}/program"]]
    return [["{repo}/target/debug/tacitra", "check", target]], [["{repo}/target/debug/tacitra", "run", target]]


def build() -> None:
    if PREREG.exists(): raise RuntimeError("semantic-protocol-v1 is frozen")
    if CASES.exists(): shutil.rmtree(CASES)
    definitions = []
    indices = [*range(1, 7), *range(101, 161)]
    for position, index in enumerate(indices, 1):
        task, before, after, expected = design(index)
        value, old, kind = 30 + index, 1 + index % 4, index % 4
        phase = "dev" if position <= 6 else "heldout"
        category = "repository-change" if position % 2 else "debug-repair"
        case_dir = CASES / f"sp-{phase}-{category.replace('-', '')}-{index:03d}"
        write(case_dir / "task.md", task + "\n")
        representations = []
        for language in LANGUAGES:
            extension = EXT[language]
            write(case_dir / f"base.{language}.{extension}", before[language])
            write(case_dir / f"reference.{language}.patch", unified(before[language], after[language], f"program.{extension}"))
            compile_commands, test_commands = commands(language, f"{{work}}/program.{extension}")
            diagnostic = []
            if category == "debug-repair":
                actual = value + old if kind in (0, 2) else 0 if kind == 1 else -1
                write_json(case_dir / f"diagnostic.{language}.json", {"phase": "test", "expected": expected, "actual": actual})
                diagnostic = [f"diagnostic.{language}.json"]
            representations.append({"id": f"{language}-ordinary", "language": language, "surface": "human-source", "artifact": f"reference.{language}.patch", "artifact_kind": "patch", "specification": [SPECS[language]], "repository_context": [f"base.{language}.{extension}"], "diagnostic_context": diagnostic, "setup_files": [{"source": f"base.{language}.{extension}", "target": f"program.{extension}"}], "prepare_commands": [["patch", "--silent", f"{{work}}/program.{extension}", "{artifact}"]], "compile_commands": compile_commands, "test_commands": test_commands, "result_kind": "integer"})
        tacitra_hash = json.loads(subprocess.run([str(ROOT / "target/debug/tacitra"), "module.summary", str(case_dir / "base.tacitra.taci")], capture_output=True, text=True, check=True).stdout)["content_hash"]
        name = f"solve_sp_{index:02d}"
        new = 6 + index % 7
        replacement = f"{{ value + {new} }}" if kind == 0 else f"{{ if value <= limit {{ value + {new} }} else {{ 0 }} }}" if kind == 1 else f"{{ if packet.enabled {{ packet.value + {new} }} else {{ packet.value }} }}" if kind == 2 else '{ if divisor == 0 { Err("zero") } else { Ok(value / divisor) } }'
        edit = {"v": 1, "h": tacitra_hash, "cap": [], "ops": [["body", f"sym:fn:{name}", replacement]]}
        write(case_dir / "reference.tacitra.edit.json", json.dumps(edit, sort_keys=True, separators=(",", ":")) + "\n")
        capsule = subprocess.run([str(ROOT / "target/debug/tacitra"), "ai.context", str(case_dir / "base.tacitra.taci"), name, "--success", task], capture_output=True, text=True, check=True).stdout
        write(case_dir / "capsule.json", capsule)
        diagnostic = ["diagnostic.tacitra.json"] if category == "debug-repair" else []
        representations.append({"id": "tacitra-semantic", "language": "tacitra", "surface": "semantic-query", "artifact": "reference.tacitra.edit.json", "artifact_kind": "patch", "specification": ["../../protocol-profile-v1.md"], "repository_context": ["capsule.json"], "diagnostic_context": diagnostic, "setup_files": [{"source": "base.tacitra.taci", "target": "program.taci"}], "prepare_commands": [["{repo}/target/debug/tacitra", "ai.edit.apply", "{work}/program.taci", "{artifact}"]], "compile_commands": [["{repo}/target/debug/tacitra", "check", "{work}/program.taci"]], "test_commands": [["{repo}/target/debug/tacitra", "run", "{work}/program.taci"]], "result_kind": "integer"})
        case = {"schema_version": 2, "id": case_dir.name, "category": category, "prompt": "task.md", "acceptance": {"description": "program prints expected integer", "expected_integer": expected}, "max_repair_rounds": 2, "representations": representations}
        write_json(case_dir / "case.json", case)
        definitions.append({"id": case_dir.name, "phase": phase, "category": category, "task": task, "expected": expected})
    write_json(BASE / "definitions-v1.json", {"schema_version": 1, "suite": "semantic-protocol-v1", "cases": definitions})


def validate() -> None:
    STATIC.BENCHMARKS = BASE
    cases = STATIC.discover_cases()
    if len(cases) != 66: raise RuntimeError(f"expected 66 cases, found {len(cases)}")
    accepted = 0
    for path, case in cases:
        if len(case["representations"]) != 5: raise RuntimeError("expected five representations")
        for representation in case["representations"]:
            row = STATIC.run_representation(path, case, representation, "semantic-reference", 1, 30)
            if not row["accepted"]: raise RuntimeError(f"reference failed {case['id']}/{representation['id']}: {row['failure']}")
            accepted += 1
    print(json.dumps({"valid": True, "cases": len(cases), "accepted_references": accepted}))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("build", "validate"))
    args = parser.parse_args()
    if args.command == "build": build()
    validate()
    return 0


if __name__ == "__main__": raise SystemExit(main())
