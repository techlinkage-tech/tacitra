#!/usr/bin/env python3
"""Generate independent pilot and confirmation fixtures for semantic protocol v2."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "benchmarks/semantic-protocol-v2"
CASES = BASE / "cases"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


OLD = load("semantic_v2_case_source", ROOT / "benchmarks/semantic-protocol/build_cases.py")


def write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def write_json(path: Path, value: object) -> None:
    write(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def current_fragment(index: int) -> str:
    old = 1 + index % 4
    kind = index % 4
    if kind == 0:
        return f"{{ value + {old} }}"
    if kind == 1:
        return f"{{ if value >= limit {{ 0 }} else {{ value + {old} }} }}"
    if kind == 2:
        return f"{{ if packet.enabled {{ packet.value + {old} }} else {{ packet.value }} }}"
    return '{ if divisor <= 1 { Err("zero") } else { Ok(value / divisor) } }'


def build_case(index: int, phase: str, position: int) -> dict:
    task, before, after, expected = OLD.design(index)
    category = "repository-change" if position % 2 else "debug-repair"
    case_id = f"spv2-{phase}-{category.replace('-', '')}-{index:03d}"
    directory = CASES / case_id
    source = before["tacitra"]
    changed = after["tacitra"]
    function = f"solve_sp_{index:02d}"
    target = f"sym:fn:{function}"
    summary = subprocess.run(
        [str(ROOT / "target/debug/tacitra"), "module.summary", "-"],
        input=source,
        text=True,
        capture_output=True,
        check=False,
    )
    if summary.returncode == 0:
        content_hash = json.loads(summary.stdout)["content_hash"]
    else:
        temporary = directory / "base.tacitra.taci"
        write(temporary, source)
        output = subprocess.run(
            [str(ROOT / "target/debug/tacitra"), "module.summary", str(temporary)],
            text=True,
            capture_output=True,
            check=True,
        )
        content_hash = json.loads(output.stdout)["content_hash"]
    reference_patch = OLD.unified(source, changed, "program.taci")
    kind = index % 4
    new = 6 + index % 7
    replacement = (
        f"{{ value + {new} }}"
        if kind == 0
        else f"{{ if value <= limit {{ value + {new} }} else {{ 0 }} }}"
        if kind == 1
        else f"{{ if packet.enabled {{ packet.value + {new} }} else {{ packet.value }} }}"
        if kind == 2
        else '{ if divisor == 0 { Err("zero") } else { Ok(value / divisor) } }'
    )
    capsule_result = subprocess.run(
        [
            str(ROOT / "target/debug/tacitra"),
            "ai.context",
            str(directory / "base.tacitra.taci"),
            function,
            "--success",
            task,
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if capsule_result.returncode != 0:
        write(directory / "base.tacitra.taci", source)
        capsule_result = subprocess.run(
            [str(ROOT / "target/debug/tacitra"), "ai.context", str(directory / "base.tacitra.taci"), function, "--success", task],
            text=True,
            capture_output=True,
            check=True,
        )
    capsule = json.loads(capsule_result.stdout)
    packet = {
        "schema_version": 1,
        "capsule": capsule,
        "editable": {"kind": "function_body", "source": current_fragment(index)},
    }
    compact = {"v": 1, "h": content_hash, "cap": [], "ops": [["body", target, replacement]]}
    named = {
        "version": 1,
        "base_hash": content_hash,
        "capabilities": [],
        "operations": [
            {"operation": "replace_function_body", "target": target, "replacement": replacement}
        ],
    }
    write(directory / "task.md", task + "\n")
    write(directory / "base.tacitra.taci", source)
    write(directory / "reference.diff", reference_patch)
    write(directory / "reference.fragment.taci", replacement + "\n")
    write_json(directory / "reference.named.json", named)
    write(directory / "reference.compact.json", json.dumps(compact, sort_keys=True, separators=(",", ":")) + "\n")
    write_json(directory / "task-packet.json", packet)
    diagnostics = []
    if category == "debug-repair":
        value = 30 + index
        old = 1 + index % 4
        actual = value + old if kind in (0, 2) else 0 if kind == 1 else -1
        write_json(directory / "diagnostic.json", {"phase": "test", "expected": expected, "actual": actual})
        diagnostics = ["diagnostic.json"]
    common = {
        "language": "tacitra",
        "setup_files": [{"source": "base.tacitra.taci", "target": "program.taci"}],
        "compile_commands": [["{repo}/target/debug/tacitra", "check", "{work}/program.taci"]],
        "test_commands": [["{repo}/target/debug/tacitra", "run", "{work}/program.taci"]],
        "result_kind": "integer",
        "target": target,
        "base_hash": content_hash,
    }
    representations = [
        {
            **common,
            "id": "ordinary",
            "surface": "human-source",
            "artifact": "reference.diff",
            "artifact_kind": "unified_diff",
            "specification": ["../../../cross-language/tacitra-source-profile-v1.md"],
            "repository_context": ["base.tacitra.taci"],
            "diagnostic_context": diagnostics,
        },
        *[
            {
                **common,
                "id": identifier,
                "surface": "task-capsule",
                "artifact": artifact,
                "artifact_kind": artifact_kind,
                "specification": ["../../task-profile-v1.md", f"../../{contract}"],
                "repository_context": ["task-packet.json"],
                "diagnostic_context": diagnostics,
            }
            for identifier, artifact, artifact_kind, contract in (
                ("capsule-diff", "reference.diff", "unified_diff", "output-diff-v1.md"),
                ("capsule-fragment", "reference.fragment.taci", "source_fragment", "output-fragment-v1.md"),
                ("capsule-named", "reference.named.json", "named_edit", "output-named-v1.md"),
                ("compact-control", "reference.compact.json", "compact_edit", "output-compact-v1.md"),
            )
        ],
    ]
    write_json(
        directory / "case.json",
        {
            "schema_version": 1,
            "id": case_id,
            "phase": phase,
            "category": category,
            "prompt": "task.md",
            "acceptance": {"expected_integer": expected},
            "max_repair_rounds": 2,
            "representations": representations,
        },
    )
    return {"id": case_id, "phase": phase, "category": category, "expected": expected}


def main() -> int:
    definitions = []
    for position, index in enumerate(range(201, 213), 1):
        definitions.append(build_case(index, "pilot", position))
    for position, index in enumerate(range(301, 361), 1):
        definitions.append(build_case(index, "confirmation", position))
    write_json(BASE / "definitions-v1.json", {"schema_version": 1, "cases": definitions})
    print(json.dumps({"cases": len(definitions), "pilot": 12, "confirmation": 60}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
