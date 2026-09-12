#!/usr/bin/env python3
"""Build or validate the language-neutral cross-language-v1 fixtures."""

from __future__ import annotations

import argparse
import difflib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "benchmarks/cross-language"
CASES = BASE / "cases"
DEFINITIONS = BASE / "definitions-v1.json"
PREREGISTRATION = BASE / "preregistration-v1.json"
LANGUAGES = ("python", "go", "rust", "tacitra")
EXTENSIONS = {"python": "py", "go": "go", "rust": "rs", "tacitra": "taci"}
SPECS = {language: f"../../../specs/{language}-v1.md" for language in LANGUAGES}
SPECS["tacitra"] = "../../tacitra-source-profile-v1.md"

spec = importlib.util.spec_from_file_location("cross_language_static", ROOT / "benchmarks/harness.py")
assert spec is not None and spec.loader is not None
STATIC = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = STATIC
spec.loader.exec_module(STATIC)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, value: object) -> None:
    write(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def names(index: int) -> tuple[str, str]:
    return f"step_{index:03d}", f"solve_{index:03d}"


def wrap(language: str, declarations: str, main_expression: str) -> str:
    if language == "python":
        return f"{declarations}\n\ndef main() -> int:\n    return {main_expression}\n\n\nif __name__ == \"__main__\":\n    print(main())\n"
    if language == "go":
        return f'package main\n\nimport "fmt"\n\n{declarations}\n\nfunc main() {{\n\tfmt.Println({main_expression})\n}}\n'
    if language == "rust":
        return f"{declarations}\n\nfn main() {{\n    println!(\"{{}}\", {main_expression});\n}}\n"
    return f"{declarations}\n\nfn main() -> Int {{\n  {main_expression}\n}}\n"


def generation(index: int) -> tuple[str, str, dict[str, str], int]:
    first, solve = names(index)
    kind = index % 8
    a = 5 + index
    b = 2 + index % 7
    if kind == 0:
        expected = a * 2 + b
        task = f"Define `{first}(value)` to double an integer and `{solve}(value)` to add {b} after calling `{first}`. The complete program must print `{expected}` for input `{a}`."
        sources = {
            "python": wrap("python", f"def {first}(value: int) -> int:\n    return value * 2\n\n\ndef {solve}(value: int) -> int:\n    return {first}(value) + {b}", f"{solve}({a})"),
            "go": wrap("go", f"func {first}(value int64) int64 {{ return value * 2 }}\n\nfunc {solve}(value int64) int64 {{ return {first}(value) + {b} }}", f"{solve}({a})"),
            "rust": wrap("rust", f"fn {first}(value: i64) -> i64 {{ value * 2 }}\n\nfn {solve}(value: i64) -> i64 {{ {first}(value) + {b} }}", f"{solve}({a})"),
            "tacitra": wrap("tacitra", f"fn {first}(value: Int) -> Int {{\n  value * 2\n}}\n\nfn {solve}(value: Int) -> Int {{\n  {first}(value) + {b}\n}}", f"{solve}({a})"),
        }
        return "composition", task, sources, expected
    if kind == 1:
        expected = a + b
        task = f"Define `{solve}(value, enabled)` with an explicit boolean condition: add {b} when enabled and subtract {b} otherwise. The complete program must print `{expected}` for value `{a}` and enabled `true`."
        bodies = {
            "python": f"def {solve}(value: int, enabled: bool) -> int:\n    if enabled:\n        return value + {b}\n    return value - {b}",
            "go": f"func {solve}(value int64, enabled bool) int64 {{\n\tif enabled {{ return value + {b} }}\n\treturn value - {b}\n}}",
            "rust": f"fn {solve}(value: i64, enabled: bool) -> i64 {{\n    if enabled {{ value + {b} }} else {{ value - {b} }}\n}}",
            "tacitra": f"fn {solve}(value: Int, enabled: Bool) -> Int {{\n  if enabled {{\n    value + {b}\n  }} else {{\n    value - {b}\n  }}\n}}",
        }
        calls = {
            language: f"{solve}({a}, {'True' if language == 'python' else 'true'})"
            for language in LANGUAGES
        }
        return "condition", task, {lang: wrap(lang, body, calls[lang]) for lang, body in bodies.items()}, expected
    if kind == 2:
        expected = a + b + 3
        task = f"Define `{solve}(value)` using immutable local variables `offset = {b}` and `bonus = 3`; return their sum with the input. The complete program must print `{expected}` for input `{a}`."
        bodies = {
            "python": f"def {solve}(value: int) -> int:\n    offset = {b}\n    bonus = 3\n    return value + offset + bonus",
            "go": f"func {solve}(value int64) int64 {{\n\toffset := int64({b})\n\tbonus := int64(3)\n\treturn value + offset + bonus\n}}",
            "rust": f"fn {solve}(value: i64) -> i64 {{\n    let offset = {b};\n    let bonus = 3;\n    value + offset + bonus\n}}",
            "tacitra": f"fn {solve}(value: Int) -> Int {{\n  let offset = {b};\n  let bonus = 3;\n  value + offset + bonus\n}}",
        }
        return "locals", task, {lang: wrap(lang, body, f"{solve}({a})") for lang, body in bodies.items()}, expected
    if kind == 3:
        expected = a
        label = f"ready_{index}"
        task = f"Define `{solve}(label)` over strings; return {a} for the exact label `{label}` and {b} otherwise. The complete program must print `{expected}` for that label."
        bodies = {
            "python": f'def {solve}(label: str) -> int:\n    return {a} if label == "{label}" else {b}',
            "go": f'func {solve}(label string) int64 {{\n\tif label == "{label}" {{ return {a} }}\n\treturn {b}\n}}',
            "rust": f'fn {solve}(label: &str) -> i64 {{\n    if label == "{label}" {{ {a} }} else {{ {b} }}\n}}',
            "tacitra": f'fn {solve}(label: String) -> Int {{\n  if label == "{label}" {{\n    {a}\n  }} else {{\n    {b}\n  }}\n}}',
        }
        calls = {"python": f'{solve}("{label}")', "go": f'{solve}("{label}")', "rust": f'{solve}("{label}")', "tacitra": f'{solve}("{label}")'}
        return "string", task, {lang: wrap(lang, body, calls[lang]) for lang, body in bodies.items()}, expected
    if kind == 4:
        expected = a + b
        record = f"Packet{index:03d}"
        task = f"Define a record-like `{record}` with integer `value` and boolean `enabled`, plus `{solve}(packet)` that adds {b} only when enabled. Construct an enabled value `{a}` and print `{expected}`."
        sources = {
            "python": wrap("python", f"class {record}:\n    def __init__(self, value: int, enabled: bool):\n        self.value = value\n        self.enabled = enabled\n\n\ndef {solve}(packet: {record}) -> int:\n    return packet.value + {b} if packet.enabled else packet.value", f"{solve}({record}({a}, True))"),
            "go": wrap("go", f"type {record} struct {{ value int64; enabled bool }}\n\nfunc {solve}(packet {record}) int64 {{\n\tif packet.enabled {{ return packet.value + {b} }}\n\treturn packet.value\n}}", f"{solve}({record}{{value: {a}, enabled: true}})"),
            "rust": wrap("rust", f"struct {record} {{ value: i64, enabled: bool }}\n\nfn {solve}(packet: {record}) -> i64 {{\n    if packet.enabled {{ packet.value + {b} }} else {{ packet.value }}\n}}", f"{solve}({record} {{ value: {a}, enabled: true }})"),
            "tacitra": wrap("tacitra", f"record {record} {{\n  value: Int,\n  enabled: Bool,\n}}\n\nfn {solve}(packet: {record}) -> Int {{\n  if packet.enabled {{\n    packet.value + {b}\n  }} else {{\n    packet.value\n  }}\n}}", f"{solve}(new {record} {{ value: {a}, enabled: true }})"),
        }
        return "record", task, sources, expected
    if kind == 5:
        expected = a
        task = f"Define `{solve}(value, divisor)` with an explicit recoverable error for divisor zero and integer division otherwise. Handle success and failure in the caller, and print `{expected}` for value `{a * b}` and divisor `{b}`."
        sources = {
            "python": wrap("python", f"def {solve}(value: int, divisor: int) -> tuple[bool, int]:\n    if divisor == 0:\n        return False, 0\n    return True, value // divisor\n\n\ndef consume(result: tuple[bool, int]) -> int:\n    ok, value = result\n    return value if ok else -1", f"consume({solve}({a * b}, {b}))"),
            "go": wrap("go", f"func {solve}(value int64, divisor int64) (int64, bool) {{\n\tif divisor == 0 {{ return 0, false }}\n\treturn value / divisor, true\n}}\n\nfunc consume(value int64, ok bool) int64 {{\n\tif ok {{ return value }}\n\treturn -1\n}}", f"consume({solve}({a * b}, {b}))"),
            "rust": wrap("rust", f"fn {solve}(value: i64, divisor: i64) -> Result<i64, &'static str> {{\n    if divisor == 0 {{ Err(\"zero\") }} else {{ Ok(value / divisor) }}\n}}\n\nfn consume(result: Result<i64, &'static str>) -> i64 {{\n    match result {{ Ok(value) => value, Err(_) => -1 }}\n}}", f"consume({solve}({a * b}, {b}))"),
            "tacitra": wrap("tacitra", f"fn {solve}(value: Int, divisor: Int) -> Result[Int, String] {{\n  if divisor == 0 {{\n    Err(\"zero\")\n  }} else {{\n    Ok(value / divisor)\n  }}\n}}\n\nfn consume(result: Result[Int, String]) -> Int {{\n  match result {{\n    Ok(value) => value,\n    Err(message) => -1,\n  }}\n}}", f"consume({solve}({a * b}, {b}))"),
        }
        return "error", task, sources, expected
    if kind == 6:
        limit = 9_000_000_000_000_000_000 - index
        expected = a
        task = f"Define `{solve}(value, limit)` using an inclusive integer boundary check. Return {a} when value is within the limit and {b} otherwise. Print `{expected}` for value and limit both `{limit}`."
        bodies = {
            "python": f"def {solve}(value: int, limit: int) -> int:\n    return {a} if value <= limit else {b}",
            "go": f"func {solve}(value int64, limit int64) int64 {{\n\tif value <= limit {{ return {a} }}\n\treturn {b}\n}}",
            "rust": f"fn {solve}(value: i64, limit: i64) -> i64 {{\n    if value <= limit {{ {a} }} else {{ {b} }}\n}}",
            "tacitra": f"fn {solve}(value: Int, limit: Int) -> Int {{\n  if value <= limit {{\n    {a}\n  }} else {{\n    {b}\n  }}\n}}",
        }
        return "boundary", task, {lang: wrap(lang, body, f"{solve}({limit}, {limit})") for lang, body in bodies.items()}, expected
    expected = a + b
    task = f"Define `{solve}(left, right, enabled)` using both a boolean conjunction and an integer comparison. Return left plus right only when enabled and left is positive; otherwise return zero. Print `{expected}` for `{a}`, `{b}`, and true."
    bodies = {
        "python": f"def {solve}(left: int, right: int, enabled: bool) -> int:\n    return left + right if enabled and left > 0 else 0",
        "go": f"func {solve}(left int64, right int64, enabled bool) int64 {{\n\tif enabled && left > 0 {{ return left + right }}\n\treturn 0\n}}",
        "rust": f"fn {solve}(left: i64, right: i64, enabled: bool) -> i64 {{\n    if enabled && left > 0 {{ left + right }} else {{ 0 }}\n}}",
        "tacitra": f"fn {solve}(left: Int, right: Int, enabled: Bool) -> Int {{\n  if enabled && left > 0 {{\n    left + right\n  }} else {{\n    0\n  }}\n}}",
    }
    calls = {
        language: f"{solve}({a}, {b}, {'True' if language == 'python' else 'true'})"
        for language in LANGUAGES
    }
    return "boolean", task, {lang: wrap(lang, body, calls[lang]) for lang, body in bodies.items()}, expected


def modification(index: int) -> tuple[str, str, dict[str, str], dict[str, str], int]:
    first, solve = names(index)
    a, old, new = 20 + index, 2 + index % 5, 8 + index % 7
    kind = index % 6
    if kind == 0:
        expected = (a * new) + new
        task = f"Modify both `{first}` and `{solve}`: `{first}` must multiply by {new} instead of {old}, and `{solve}` must add {new} instead of {old} after calling `{first}`. Keep the caller unchanged; it must print `{expected}`. Return one unified diff."
        before = {
            "python": wrap("python", f"def {first}(value: int) -> int:\n    return value * {old}\n\n\ndef {solve}(value: int) -> int:\n    return {first}(value) + {old}", f"{solve}({a})"),
            "go": wrap("go", f"func {first}(value int64) int64 {{ return value * {old} }}\n\nfunc {solve}(value int64) int64 {{ return {first}(value) + {old} }}", f"{solve}({a})"),
            "rust": wrap("rust", f"fn {first}(value: i64) -> i64 {{ value * {old} }}\n\nfn {solve}(value: i64) -> i64 {{ {first}(value) + {old} }}", f"{solve}({a})"),
            "tacitra": wrap("tacitra", f"fn {first}(value: Int) -> Int {{\n  value * {old}\n}}\n\nfn {solve}(value: Int) -> Int {{\n  {first}(value) + {old}\n}}", f"{solve}({a})"),
        }
        after = {language: source.replace(f"* {old}", f"* {new}").replace(f"+ {old}", f"+ {new}") for language, source in before.items()}
        return "multi-function", task, before, after, expected
    if kind == 1:
        expected = a + new
        task = f"Change `{solve}` so its boundary is inclusive and its enabled branch adds {new} instead of subtracting {old}. Keep the caller at the exact boundary `{a}`; it must print `{expected}`. Return one unified diff."
        bodies = {
            "python": (f"def {solve}(value: int, limit: int) -> int:\n    return value - {old} if value > limit else 0", f"def {solve}(value: int, limit: int) -> int:\n    return value + {new} if value >= limit else 0"),
            "go": (f"func {solve}(value int64, limit int64) int64 {{\n\tif value > limit {{ return value - {old} }}\n\treturn 0\n}}", f"func {solve}(value int64, limit int64) int64 {{\n\tif value >= limit {{ return value + {new} }}\n\treturn 0\n}}"),
            "rust": (f"fn {solve}(value: i64, limit: i64) -> i64 {{\n    if value > limit {{ value - {old} }} else {{ 0 }}\n}}", f"fn {solve}(value: i64, limit: i64) -> i64 {{\n    if value >= limit {{ value + {new} }} else {{ 0 }}\n}}"),
            "tacitra": (f"fn {solve}(value: Int, limit: Int) -> Int {{\n  if value > limit {{\n    value - {old}\n  }} else {{\n    0\n  }}\n}}", f"fn {solve}(value: Int, limit: Int) -> Int {{\n  if value >= limit {{\n    value + {new}\n  }} else {{\n    0\n  }}\n}}"),
        }
        return "condition-boundary", task, {lang: wrap(lang, pair[0], f"{solve}({a}, {a})") for lang, pair in bodies.items()}, {lang: wrap(lang, pair[1], f"{solve}({a}, {a})") for lang, pair in bodies.items()}, expected
    if kind == 2:
        label = f"active_{index}"
        previous = f"ready_{index}"
        expected = a + new
        task = f"Change `{solve}` to recognize the exact string `{label}` instead of `{previous}` and return value plus {new} instead of plus {old}. Keep the caller unchanged; it must print `{expected}`. Return one unified diff."
        bodies = {
            "python": (f'def {solve}(label: str, value: int) -> int:\n    return value + {old} if label == "{previous}" else 0', f'def {solve}(label: str, value: int) -> int:\n    return value + {new} if label == "{label}" else 0'),
            "go": (f'func {solve}(label string, value int64) int64 {{\n\tif label == "{previous}" {{ return value + {old} }}\n\treturn 0\n}}', f'func {solve}(label string, value int64) int64 {{\n\tif label == "{label}" {{ return value + {new} }}\n\treturn 0\n}}'),
            "rust": (f'fn {solve}(label: &str, value: i64) -> i64 {{\n    if label == "{previous}" {{ value + {old} }} else {{ 0 }}\n}}', f'fn {solve}(label: &str, value: i64) -> i64 {{\n    if label == "{label}" {{ value + {new} }} else {{ 0 }}\n}}'),
            "tacitra": (f'fn {solve}(label: String, value: Int) -> Int {{\n  if label == "{previous}" {{\n    value + {old}\n  }} else {{\n    0\n  }}\n}}', f'fn {solve}(label: String, value: Int) -> Int {{\n  if label == "{label}" {{\n    value + {new}\n  }} else {{\n    0\n  }}\n}}'),
        }
        calls = {language: f'{solve}("{label}", {a})' for language in LANGUAGES}
        return "string-change", task, {lang: wrap(lang, pair[0], calls[lang]) for lang, pair in bodies.items()}, {lang: wrap(lang, pair[1], calls[lang]) for lang, pair in bodies.items()}, expected
    if kind == 3:
        record = f"Packet{index:03d}"
        expected = a + new
        task = f"In the record-based `{solve}`, change the enabled result from value minus {old} to value plus {new}. Keep the enabled `{record}` caller unchanged; it must print `{expected}`. Return one unified diff."
        before = {
            "python": wrap("python", f"class {record}:\n    def __init__(self, value: int, enabled: bool):\n        self.value = value\n        self.enabled = enabled\n\n\ndef {solve}(packet: {record}) -> int:\n    return packet.value - {old} if packet.enabled else packet.value", f"{solve}({record}({a}, True))"),
            "go": wrap("go", f"type {record} struct {{ value int64; enabled bool }}\n\nfunc {solve}(packet {record}) int64 {{\n\tif packet.enabled {{ return packet.value - {old} }}\n\treturn packet.value\n}}", f"{solve}({record}{{value: {a}, enabled: true}})"),
            "rust": wrap("rust", f"struct {record} {{ value: i64, enabled: bool }}\n\nfn {solve}(packet: {record}) -> i64 {{\n    if packet.enabled {{ packet.value - {old} }} else {{ packet.value }}\n}}", f"{solve}({record} {{ value: {a}, enabled: true }})"),
            "tacitra": wrap("tacitra", f"record {record} {{\n  value: Int,\n  enabled: Bool,\n}}\n\nfn {solve}(packet: {record}) -> Int {{\n  if packet.enabled {{\n    packet.value - {old}\n  }} else {{\n    packet.value\n  }}\n}}", f"{solve}(new {record} {{ value: {a}, enabled: true }})"),
        }
        after = {language: source.replace(f"- {old}", f"+ {new}") for language, source in before.items()}
        return "record-change", task, before, after, expected
    if kind == 4:
        expected = a
        task = f"Change `{solve}` so only divisor zero is an error; divisor one must succeed. Keep the caller using value `{a}` and divisor one unchanged, and print `{expected}`. Return one unified diff."
        bodies = {
            "python": (f"def {solve}(value: int, divisor: int) -> tuple[bool, int]:\n    if divisor <= 1:\n        return False, 0\n    return True, value // divisor\n\n\ndef consume(result: tuple[bool, int]) -> int:\n    ok, value = result\n    return value if ok else -1", f"def {solve}(value: int, divisor: int) -> tuple[bool, int]:\n    if divisor == 0:\n        return False, 0\n    return True, value // divisor\n\n\ndef consume(result: tuple[bool, int]) -> int:\n    ok, value = result\n    return value if ok else -1"),
            "go": (f"func {solve}(value int64, divisor int64) (int64, bool) {{\n\tif divisor <= 1 {{ return 0, false }}\n\treturn value / divisor, true\n}}\n\nfunc consume(value int64, ok bool) int64 {{\n\tif ok {{ return value }}\n\treturn -1\n}}", f"func {solve}(value int64, divisor int64) (int64, bool) {{\n\tif divisor == 0 {{ return 0, false }}\n\treturn value / divisor, true\n}}\n\nfunc consume(value int64, ok bool) int64 {{\n\tif ok {{ return value }}\n\treturn -1\n}}"),
            "rust": (f"fn {solve}(value: i64, divisor: i64) -> Result<i64, &'static str> {{\n    if divisor <= 1 {{ Err(\"zero\") }} else {{ Ok(value / divisor) }}\n}}\n\nfn consume(result: Result<i64, &'static str>) -> i64 {{\n    match result {{ Ok(value) => value, Err(_) => -1 }}\n}}", f"fn {solve}(value: i64, divisor: i64) -> Result<i64, &'static str> {{\n    if divisor == 0 {{ Err(\"zero\") }} else {{ Ok(value / divisor) }}\n}}\n\nfn consume(result: Result<i64, &'static str>) -> i64 {{\n    match result {{ Ok(value) => value, Err(_) => -1 }}\n}}"),
            "tacitra": (f"fn {solve}(value: Int, divisor: Int) -> Result[Int, String] {{\n  if divisor <= 1 {{\n    Err(\"zero\")\n  }} else {{\n    Ok(value / divisor)\n  }}\n}}\n\nfn consume(result: Result[Int, String]) -> Int {{\n  match result {{\n    Ok(value) => value,\n    Err(message) => -1,\n  }}\n}}", f"fn {solve}(value: Int, divisor: Int) -> Result[Int, String] {{\n  if divisor == 0 {{\n    Err(\"zero\")\n  }} else {{\n    Ok(value / divisor)\n  }}\n}}\n\nfn consume(result: Result[Int, String]) -> Int {{\n  match result {{\n    Ok(value) => value,\n    Err(message) => -1,\n  }}\n}}"),
        }
        return "error-change", task, {lang: wrap(lang, pair[0], f"consume({solve}({a}, 1))") for lang, pair in bodies.items()}, {lang: wrap(lang, pair[1], f"consume({solve}({a}, 1))") for lang, pair in bodies.items()}, expected
    limit = 9_000_000_000_000_000_000 - index
    expected = a + new
    task = f"Change `{solve}` from an exclusive to an inclusive check at the large integer boundary `{limit}`, and change the successful result to value plus {new}. Keep the exact-boundary caller unchanged; it must print `{expected}`. Return one unified diff."
    bodies = {
        "python": (f"def {solve}(value: int, limit: int) -> int:\n    return {old} if value < limit else 0", f"def {solve}(value: int, limit: int) -> int:\n    return {a + new} if value <= limit else 0"),
        "go": (f"func {solve}(value int64, limit int64) int64 {{\n\tif value < limit {{ return {old} }}\n\treturn 0\n}}", f"func {solve}(value int64, limit int64) int64 {{\n\tif value <= limit {{ return {a + new} }}\n\treturn 0\n}}"),
        "rust": (f"fn {solve}(value: i64, limit: i64) -> i64 {{\n    if value < limit {{ {old} }} else {{ 0 }}\n}}", f"fn {solve}(value: i64, limit: i64) -> i64 {{\n    if value <= limit {{ {a + new} }} else {{ 0 }}\n}}"),
        "tacitra": (f"fn {solve}(value: Int, limit: Int) -> Int {{\n  if value < limit {{\n    {old}\n  }} else {{\n    0\n  }}\n}}", f"fn {solve}(value: Int, limit: Int) -> Int {{\n  if value <= limit {{\n    {a + new}\n  }} else {{\n    0\n  }}\n}}"),
    }
    return "boundary-change", task, {lang: wrap(lang, pair[0], f"{solve}({limit}, {limit})") for lang, pair in bodies.items()}, {lang: wrap(lang, pair[1], f"{solve}({limit}, {limit})") for lang, pair in bodies.items()}, expected


def diagnostic(index: int) -> tuple[str, str, dict[str, str], dict[str, str], int]:
    first, solve = names(index)
    a, b = 30 + index, 2 + index % 6
    expected = a + b
    kind = index % 4
    good = {
        "python": wrap("python", f"def {solve}(value: int) -> int:\n    offset = {b}\n    return value + offset", f"{solve}({a})"),
        "go": wrap("go", f"func {solve}(value int64) int64 {{\n\toffset := int64({b})\n\treturn value + offset\n}}", f"{solve}({a})"),
        "rust": wrap("rust", f"fn {solve}(value: i64) -> i64 {{\n    let offset = {b};\n    value + offset\n}}", f"{solve}({a})"),
        "tacitra": wrap("tacitra", f"fn {solve}(value: Int) -> Int {{\n  let offset = {b};\n  value + offset\n}}", f"{solve}({a})"),
    }
    if kind == 0:
        task = f"Fix the undefined local name in `{solve}` with the smallest change so the program prints `{expected}`. Return one unified diff."
        bad = {language: source.replace(f"offset = {b}", "offset = missing") if language == "python" else source.replace(f"offset := int64({b})", "offset := missing") if language == "go" else source.replace(f"let offset = {b};", "let offset = missing;") for language, source in good.items()}
        return "undefined-name", task, bad, good, expected
    if kind == 1:
        task = f"Fix the undefined function call in `{solve}` with the smallest change so the program prints `{expected}`. Return one unified diff."
        bad = {language: source.replace("value + offset", f"{first}(value) + offset") for language, source in good.items()}
        return "undefined-function", task, bad, good, expected
    if kind == 2:
        task = f"Fix the string/integer type error in `{solve}` with the smallest change so the program prints `{expected}`. Return one unified diff."
        bad = {language: source.replace(f"offset = {b}", f'offset = "{b}"') if language == "python" else source.replace(f"offset := int64({b})", f'offset := "{b}"') if language == "go" else source.replace(f"let offset = {b};", f'let offset = "{b}";') for language, source in good.items()}
        return "type-error", task, bad, good, expected
    task = f"Fix the wrong-arity call to `{solve}` with the smallest change so the program prints `{expected}`. Return one unified diff."
    bad = {language: source.replace(f"{solve}({a})", f"{solve}({a}, {b})") for language, source in good.items()}
    return "wrong-arity", task, bad, good, expected


def commands(language: str, target: str) -> tuple[list[list[str]], list[list[str]]]:
    if language == "python":
        return [["python3", "-m", "py_compile", target]], [["python3", target]]
    if language == "go":
        return [["go", "build", "-o", "{work}/program", target]], [["{work}/program"]]
    if language == "rust":
        return [["{rustc}", "--edition=2021", "--crate-name", "program", "-o", "{work}/program", target]], [["{work}/program"]]
    return [["{repo}/target/debug/tacitra", "check", target]], [["{repo}/target/debug/tacitra", "run", target]]


def unified(before: str, after: str, filename: str) -> str:
    return "".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile=filename, tofile=filename))


def capture_diagnostic(language: str, source: str, extension: str) -> dict:
    with tempfile.TemporaryDirectory(prefix="tacitra-cross-language-diagnostic-") as directory:
        work = Path(directory)
        target = work / f"program.{extension}"
        target.write_text(source, encoding="utf-8")
        compile_commands, test_commands = commands(language, str(target))
        environment = dict(**__import__("os").environ)
        environment["GOCACHE"] = str(work / "go-cache")
        for phase, phase_commands in (("compile", compile_commands), ("test", test_commands)):
            for command in phase_commands:
                expanded = STATIC.expand(command, target.parent, target, work)
                result = subprocess.run(expanded, cwd=work, env=environment, capture_output=True, text=True, timeout=30, check=False)
                if result.returncode != 0:
                    def normalize(value: str) -> str:
                        return value.replace(str(target), target.name).replace(str(work), "<work>")

                    return {
                        "phase": phase,
                        "exit_code": result.returncode,
                        "stdout": normalize(result.stdout)[-4096:],
                        "stderr": normalize(result.stderr)[-4096:],
                    }
    raise RuntimeError(f"invalid fixture unexpectedly succeeds: {language}")


def representation(case_dir: Path, category: str, language: str) -> dict:
    extension = EXTENSIONS[language]
    artifact = f"reference.{language}.{extension}" if category == "generation" else f"reference.{language}.patch"
    compile_target = "{artifact}" if category == "generation" else f"{{work}}/program.{extension}"
    compile_commands, test_commands = commands(language, compile_target)
    return {
        "id": f"{language}-source" if category == "generation" else f"{language}-unified-diff",
        "language": language,
        "surface": "human-source",
        "artifact": artifact,
        "artifact_kind": "source" if category == "generation" else "patch",
        "specification": [SPECS[language]],
        "repository_context": [] if category == "generation" else [f"base.{language}.{extension}"],
        "diagnostic_context": [f"diagnostic.{language}.json"] if category == "debug-repair" else [],
        "setup_files": [] if category == "generation" else [{"source": f"base.{language}.{extension}", "target": f"program.{extension}"}],
        "prepare_commands": [] if category == "generation" else [["patch", "--silent", f"{{work}}/program.{extension}", "{artifact}"]],
        "compile_commands": compile_commands,
        "test_commands": test_commands,
        "result_kind": "integer",
    }


def build() -> None:
    if PREREGISTRATION.exists():
        raise RuntimeError("cross-language-v1 is frozen; remove no files and use `validate`")
    if CASES.exists():
        shutil.rmtree(CASES)
    definitions = []
    designs = []
    designs.extend(("generation", index, generation(index)) for index in range(1, 30))
    designs.extend(("repository-change", index, modification(index)) for index in range(30, 58))
    designs.extend(("debug-repair", index, diagnostic(index)) for index in range(58, 86))
    for category, index, design in designs:
        if category == "generation":
            family, task, references, expected = design
            before = after = None
        else:
            family, task, before, after, expected = design
            references = after
        case_id = f"xl-{category.replace('-','')}-{index:03d}"
        case_dir = CASES / case_id
        write(case_dir / "task.md", task + "\n")
        for language in LANGUAGES:
            extension = EXTENSIONS[language]
            if category == "generation":
                write(case_dir / f"reference.{language}.{extension}", references[language])
            else:
                filename = f"program.{extension}"
                write(case_dir / f"base.{language}.{extension}", before[language])
                write(case_dir / f"reference.{language}.patch", unified(before[language], after[language], filename))
                if category == "debug-repair":
                    write_json(case_dir / f"diagnostic.{language}.json", capture_diagnostic(language, before[language], extension))
        case = {
            "schema_version": 2,
            "id": case_id,
            "category": category,
            "prompt": "task.md",
            "acceptance": {"description": "the complete program prints the required integer", "expected_integer": expected},
            "max_repair_rounds": 2,
            "representations": [representation(case_dir, category, language) for language in LANGUAGES],
        }
        write_json(case_dir / "case.json", case)
        definitions.append({"id": case_id, "category": category, "family": family, "features": feature_set(family), "task": task, "expected_integer": expected})
    write_json(DEFINITIONS, {"schema_version": 1, "suite": "cross-language-v1", "language_neutral": True, "cases": definitions})


def feature_set(family: str) -> list[str]:
    mapping = {
        "composition": ["functions", "composition", "integers"],
        "condition": ["condition", "boolean", "integers"],
        "locals": ["locals", "integers"],
        "string": ["condition", "string", "integers"],
        "record": ["record", "condition", "boolean"],
        "error": ["error-handling", "condition", "integers"],
        "boundary": ["boundary", "condition", "integers"],
        "boolean": ["boolean", "condition", "integers"],
        "multi-function": ["multiple-functions", "composition", "integers"],
        "condition-boundary": ["condition", "boundary", "integers"],
        "string-change": ["string", "condition", "integers"],
        "record-change": ["record", "condition", "boolean"],
        "error-change": ["error-handling", "condition", "integers"],
        "boundary-change": ["boundary", "condition", "integers"],
        "undefined-name": ["name-diagnostic", "locals"],
        "undefined-function": ["name-diagnostic", "functions"],
        "type-error": ["type-diagnostic", "string", "integers"],
        "wrong-arity": ["type-diagnostic", "functions"],
    }
    return mapping[family]


def validate() -> None:
    STATIC.BENCHMARKS = BASE
    cases = STATIC.discover_cases()
    if len(cases) != 85:
        raise RuntimeError(f"expected 85 cases, found {len(cases)}")
    existing = {path.parent.name for path in (ROOT / "benchmarks/cases").glob("*/case.json")}
    existing.update(path.parent.name for path in (ROOT / "benchmarks/confirmation/baseline/cases").glob("*/case.json"))
    if existing & {case[1]["id"] for case in cases}:
        raise RuntimeError("cross-language case ID reuses an earlier experiment")
    accepted = 0
    for case_path, case in cases:
        languages = {value["language"] for value in case["representations"]}
        if languages != set(LANGUAGES):
            raise RuntimeError(f"{case['id']} does not contain all four languages")
        for value in case["representations"]:
            row = STATIC.run_representation(case_path, case, value, "cross-language-reference", 1, 30)
            if not row["accepted"]:
                raise RuntimeError(f"reference failed: {case['id']}/{value['language']}: {row['failure']}")
            accepted += 1
    print(json.dumps({"valid": True, "cases": len(cases), "accepted_references": accepted}))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "validate"))
    args = parser.parse_args()
    if args.command == "build":
        build()
    validate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
