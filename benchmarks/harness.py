#!/usr/bin/env python3
"""Dependency-free Tacitra static benchmark harness."""

from __future__ import annotations

import argparse
import functools
import hashlib
import json
import os
import platform
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BENCHMARKS = ROOT / "benchmarks"
TOKENIZER_NAME = "utf8-bytes"
TOKENIZER_VERSION = "1"
CATEGORIES = {"syntax", "generation", "repository-change", "debug-repair", "interop"}
LANGUAGES = {"python", "go", "rust", "tacitra"}
SURFACES = {"human-source", "semantic-query", "structural-patch", "interop-manifest"}
ARTIFACT_KINDS = {"source", "patch", "arguments", "manifest"}
RESULT_KINDS = {"integer", "json-result"}
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class BenchmarkError(Exception):
    pass


def tokens(data: bytes) -> int:
    """Pinned utf8-bytes/v1: one token per retained byte."""
    return len(data)


def read_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as error:
        raise BenchmarkError(f"cannot read {path}: {error}") from error


def sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise BenchmarkError(f"invalid JSON {path}: {error}") from error
    if not isinstance(value, dict):
        raise BenchmarkError(f"expected JSON object: {path}")
    return value


def relative_file(case_dir: Path, name: str) -> Path:
    path = (case_dir / name).resolve()
    if not path.is_relative_to(ROOT):
        raise BenchmarkError(f"path leaves repository: {name}")
    if not path.is_file():
        raise BenchmarkError(f"missing benchmark input: {path}")
    return path


def validate_case(path: Path) -> dict:
    case = load_json(path)
    required = {
        "schema_version", "id", "category", "prompt", "acceptance",
        "max_repair_rounds", "representations",
    }
    if set(case) != required or case["schema_version"] != 2:
        raise BenchmarkError(f"{path}: invalid case-v2 fields or version")
    if case["category"] not in CATEGORIES:
        raise BenchmarkError(f"{path}: invalid category")
    if not isinstance(case["id"], str) or not ID_PATTERN.fullmatch(case["id"]):
        raise BenchmarkError(f"{path}: invalid case id")
    if not isinstance(case["max_repair_rounds"], int) or case["max_repair_rounds"] < 0:
        raise BenchmarkError(f"{path}: invalid repair budget")
    case_dir = path.parent
    relative_file(case_dir, case["prompt"])
    acceptance = case["acceptance"]
    if set(acceptance) != {"description", "expected_integer"}:
        raise BenchmarkError(f"{path}: invalid acceptance contract")
    if not isinstance(acceptance["expected_integer"], int):
        raise BenchmarkError(f"{path}: expected integer is not an integer")
    seen = set()
    for representation in case["representations"]:
        validate_representation(case_dir, representation)
        if representation["id"] in seen:
            raise BenchmarkError(f"{path}: duplicate representation id")
        seen.add(representation["id"])
    return case


def validate_representation(case_dir: Path, representation: dict) -> None:
    required = {
        "id", "language", "surface", "artifact", "artifact_kind",
        "specification", "repository_context", "diagnostic_context", "setup_files",
        "prepare_commands", "compile_commands", "test_commands", "result_kind",
    }
    if set(representation) != required:
        raise BenchmarkError("invalid representation fields")
    if representation["language"] not in LANGUAGES:
        raise BenchmarkError("invalid representation language")
    if representation["surface"] not in SURFACES:
        raise BenchmarkError("invalid representation surface")
    if not ID_PATTERN.fullmatch(representation["id"]):
        raise BenchmarkError("invalid representation id")
    if representation["artifact_kind"] not in ARTIFACT_KINDS:
        raise BenchmarkError("invalid artifact kind")
    if representation["result_kind"] not in RESULT_KINDS:
        raise BenchmarkError("invalid result kind")
    names = [
        representation["artifact"], *representation["specification"],
        *representation["repository_context"], *representation["diagnostic_context"],
    ]
    for name in names:
        relative_file(case_dir, name)
    for setup in representation["setup_files"]:
        if set(setup) != {"source", "target"}:
            raise BenchmarkError("invalid setup file")
        target = Path(setup["target"])
        if target.is_absolute() or ".." in target.parts:
            raise BenchmarkError("invalid setup file")
        relative_file(case_dir, setup["source"])
    for phase in ("prepare_commands", "compile_commands", "test_commands"):
        commands = representation[phase]
        if phase == "test_commands" and not commands:
            raise BenchmarkError("test command is required")
        valid = all(
            isinstance(command, list) and command
            and all(isinstance(part, str) for part in command)
            for command in commands
        )
        if not valid:
            raise BenchmarkError(f"invalid {phase}")


def discover_cases(selected: list[str] | None = None) -> list[tuple[Path, dict]]:
    found = []
    for path in sorted((BENCHMARKS / "cases").glob("*/case.json")):
        case = validate_case(path)
        if not selected or case["id"] in selected:
            found.append((path, case))
    if selected and {case[1]["id"] for case in found} != set(selected):
        raise BenchmarkError("one or more selected cases do not exist")
    if not found:
        raise BenchmarkError("no benchmark cases found")
    return found


def case_revision(case_path: Path, case: dict) -> str:
    case_dir = case_path.parent
    paths = {case_path, relative_file(case_dir, case["prompt"])}
    for representation in case["representations"]:
        names = [
            representation["artifact"], *representation["specification"],
            *representation["repository_context"], *representation["diagnostic_context"],
        ]
        names.extend(item["source"] for item in representation["setup_files"])
        paths.update(relative_file(case_dir, name) for name in names)
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(str(path.relative_to(ROOT)).encode())
        digest.update(b"\0")
        digest.update(read_bytes(path))
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def count_files(case_dir: Path, names: list[str]) -> int:
    return sum(tokens(read_bytes(relative_file(case_dir, name))) for name in names)


def expand(command: list[str], case_dir: Path, artifact: Path, work: Path) -> list[str]:
    values = {
        "repo": str(ROOT), "case": str(case_dir), "artifact": str(artifact),
        "work": str(work), "rustc": os.environ.get("RUSTC", shutil.which("rustc") or "rustc"),
    }
    return [part.format(**values) for part in command]


def execute_commands(commands: list[list[str]], case_dir: Path, artifact: Path,
                     work: Path, timeout: int) -> tuple[bool, subprocess.CompletedProcess | None]:
    environment = os.environ.copy()
    environment["PYTHONPYCACHEPREFIX"] = str(work / "pycache")
    environment["GOCACHE"] = str(work / "go-cache")
    last = None
    for command in commands:
        try:
            last = subprocess.run(
                expand(command, case_dir, artifact, work), cwd=work, env=environment,
                capture_output=True, text=True, timeout=timeout, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            last = subprocess.CompletedProcess(command, 124, "", str(error))
        if last.returncode != 0:
            return False, last
    return True, last


def normalized_result(output: str, kind: str) -> int:
    if kind == "integer":
        return int(output.strip())
    if kind == "json-result":
        return int(json.loads(output)["result"])
    raise BenchmarkError(f"unknown result kind: {kind}")


def tool_version(command: list[str]) -> str | None:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    text = (result.stdout or result.stderr).strip()
    return text if result.returncode == 0 else None


@functools.lru_cache(maxsize=1)
def environment_snapshot() -> dict:
    rustc = os.environ.get("RUSTC", shutil.which("rustc") or "rustc")
    tacitra = ROOT / "target/debug/tacitra"
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "go": tool_version(["go", "version"]),
        "rustc": tool_version([rustc, "--version"]),
        "tacitra_cli": sha256(read_bytes(tacitra)) if tacitra.is_file() else None,
        "cargo_lock": sha256(read_bytes(ROOT / "Cargo.lock")),
    }


def run_representation(case_path: Path, case: dict, representation: dict,
                       run_id: str, trial: int, timeout: int) -> dict:
    case_dir = case_path.parent
    artifact = relative_file(case_dir, representation["artifact"])
    started = time.monotonic()
    phase = "setup"
    failure = None
    result = None
    compile_ok = False
    tests_ok = False
    with tempfile.TemporaryDirectory(prefix="tacitra-benchmark-") as directory:
        work = Path(directory)
        for setup in representation["setup_files"]:
            shutil.copyfile(relative_file(case_dir, setup["source"]), work / setup["target"])
        phase = "prepare"
        prepare_ok, result = execute_commands(
            representation["prepare_commands"], case_dir, artifact, work, timeout)
        if prepare_ok:
            phase = "compile"
            compile_ok, result = execute_commands(
                representation["compile_commands"], case_dir, artifact, work, timeout)
            if not representation["compile_commands"]:
                compile_ok = True
        if prepare_ok and compile_ok:
            phase = "test"
            tests_ok, result = execute_commands(
                representation["test_commands"], case_dir, artifact, work, timeout)
            if tests_ok:
                try:
                    actual = normalized_result(result.stdout, representation["result_kind"])
                    tests_ok = actual == case["acceptance"]["expected_integer"]
                except (ValueError, KeyError, TypeError, json.JSONDecodeError):
                    tests_ok = False
        accepted = prepare_ok and compile_ok and tests_ok
        if not accepted:
            failure = {
                "phase": phase,
                "exit_code": None if result is None else result.returncode,
                "stdout": "" if result is None else result.stdout[-4096:],
                "stderr": "" if result is None else result.stderr[-4096:],
            }
    wall = time.monotonic() - started
    instruction_tokens = tokens(read_bytes(ROOT / "AGENTS.md"))
    specification_tokens = count_files(case_dir, representation["specification"])
    repository_tokens = count_files(case_dir, representation["repository_context"])
    diagnostic_tokens = count_files(case_dir, representation["diagnostic_context"])
    task_tokens = tokens(read_bytes(relative_file(case_dir, case["prompt"])))
    output_tokens = tokens(read_bytes(artifact))
    input_tokens = (
        instruction_tokens + specification_tokens + repository_tokens
        + diagnostic_tokens + task_tokens
    )
    total_tokens = input_tokens + output_tokens
    source_paths = [artifact, relative_file(case_dir, case["prompt"])]
    return {
        "schema_version": 2,
        "evidence": "measured",
        "measurement_mode": "static_reference",
        "run_id": run_id,
        "trial_id": f"{run_id}:{case['id']}:{representation['id']}:{trial:03d}",
        "case_id": case["id"], "category": case["category"],
        "representation": representation["id"], "language": representation["language"],
        "surface": representation["surface"],
        "pins": {
            "case_revision": case_revision(case_path, case),
            "harness_revision": sha256(read_bytes(Path(__file__))),
            "model": None, "model_settings": {},
            "tokenizer_name": TOKENIZER_NAME, "tokenizer_version": TOKENIZER_VERSION,
            "environment": environment_snapshot(),
        },
        "tokens": {
            "instruction_tokens": instruction_tokens,
            "specification_tokens": specification_tokens,
            "repository_context_tokens": repository_tokens,
            "task_tokens": task_tokens,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "diagnostic_tokens": diagnostic_tokens,
            "repair_tokens": 0,
            "total_tokens": total_tokens,
        },
        "compile_at_1": compile_ok, "pass_at_1": tests_ok,
        "repair_rounds": 0, "max_repair_rounds": case["max_repair_rounds"],
        "patch_size": len(read_bytes(artifact)) if representation["artifact_kind"] == "patch" else None,
        "accepted": accepted, "wall_clock_time": round(wall, 6), "failure": failure,
        "artifacts": {str(path.relative_to(ROOT)): sha256(read_bytes(path)) for path in source_paths},
    }


def run(output: Path, run_id: str, repetitions: int, selected: list[str] | None,
        timeout: int) -> None:
    rows = []
    for case_path, case in discover_cases(selected):
        for trial in range(1, repetitions + 1):
            for representation in case["representations"]:
                row = run_representation(case_path, case, representation, run_id, trial, timeout)
                validate_result(row)
                rows.append(row)
                state = "accepted" if row["accepted"] else "failed"
                print(f"{case['id']}/{representation['id']}/{trial}: {state}", file=sys.stderr)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def metric(values: list[float]) -> dict:
    return {
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "population_variance": statistics.pvariance(values),
    }


def read_rows(raw: Path) -> list[dict]:
    rows = []
    for index, line in enumerate(raw.read_text(encoding="utf-8").splitlines(), 1):
        try:
            row = json.loads(line)
            validate_result(row)
            rows.append(row)
        except json.JSONDecodeError as error:
            raise BenchmarkError(f"{raw}:{index}: {error}") from error
    if not rows:
        raise BenchmarkError("raw result file is empty")
    return rows


def validate_result(row: dict) -> None:
    required = {
        "schema_version", "evidence", "measurement_mode", "run_id", "trial_id",
        "case_id", "category", "representation", "language", "surface", "pins",
        "tokens", "compile_at_1", "pass_at_1", "repair_rounds", "max_repair_rounds",
        "patch_size", "accepted", "wall_clock_time", "failure", "artifacts",
    }
    if set(row) != required or row["schema_version"] != 2 or row["evidence"] != "measured":
        raise BenchmarkError("raw result does not conform to result-v2")
    counts = row["tokens"]
    input_sum = (
        counts["instruction_tokens"] + counts["specification_tokens"]
        + counts["repository_context_tokens"] + counts["task_tokens"]
        + counts["diagnostic_tokens"]
    )
    if counts["input_tokens"] != input_sum:
        raise BenchmarkError("input token component sum is inconsistent")
    if counts["total_tokens"] != counts["input_tokens"] + counts["output_tokens"]:
        raise BenchmarkError("total token sum is inconsistent")
    if row["measurement_mode"] == "static_reference" and row["pins"]["model"] is not None:
        raise BenchmarkError("static reference results must not claim a model")
    if row["accepted"] != (row["compile_at_1"] and row["pass_at_1"]):
        raise BenchmarkError("accepted flag is inconsistent")
    if (row["failure"] is None) != row["accepted"]:
        raise BenchmarkError("failure detail is inconsistent")


def aggregate_rows(rows: list[dict]) -> dict:
    modes = {
        (row["evidence"], row["measurement_mode"], row["pins"]["tokenizer_name"],
         row["pins"]["tokenizer_version"])
        for row in rows
    }
    if len(modes) != 1:
        raise BenchmarkError("aggregate inputs mix evidence modes or tokenizers")
    grouped = {}
    for row in rows:
        grouped.setdefault((row["category"], row["representation"]), []).append(row)
    groups = []
    for (category, representation), values in sorted(grouped.items()):
        accepted = sum(row["accepted"] for row in values)
        totals = [row["tokens"]["total_tokens"] for row in values]
        patches = [row["patch_size"] for row in values if row["patch_size"] is not None]
        component_names = values[0]["tokens"].keys()
        groups.append({
            "category": category, "representation": representation,
            "language": values[0]["language"], "surface": values[0]["surface"],
            "trials": len(values), "accepted": accepted, "failed": len(values) - accepted,
            "acceptance_rate": accepted / len(values),
            "compile_at_1_rate": sum(row["compile_at_1"] for row in values) / len(values),
            "pass_at_1_rate": sum(row["pass_at_1"] for row in values) / len(values),
            "total_tokens": metric(totals),
            "token_components": {
                name: metric([row["tokens"][name] for row in values])
                for name in component_names
            },
            "total_tokens_per_accepted_solution": sum(totals) / accepted if accepted else None,
            "patch_size": metric(patches) if patches else None,
            "wall_clock_time": metric([row["wall_clock_time"] for row in values]),
        })
    return {
        "schema_version": 1, "evidence": "measured",
        "measurement_mode": rows[0]["measurement_mode"],
        "tokenizer_name": rows[0]["pins"]["tokenizer_name"],
        "tokenizer_version": rows[0]["pins"]["tokenizer_version"],
        "raw_trials": len(rows), "accepted": sum(row["accepted"] for row in rows),
        "groups": groups,
    }


def aggregate(raw: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(aggregate_rows(read_rows(raw)), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def report(aggregate_path: Path, output: Path) -> None:
    data = load_json(aggregate_path)
    lines = [
        "# Static reference benchmark report", "",
        f"Evidence: `{data['evidence']}`; mode: `{data['measurement_mode']}`; "
        f"tokenizer: `{data['tokenizer_name']}/{data['tokenizer_version']}`.", "",
        "This report measures retained reference artifacts with a local byte tokenizer. "
        "It is not a model-generation or LLM-token benchmark.", "",
        "| Category | Representation | Success | total / accepted | Input median | Output median | Variance |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for group in data["groups"]:
        primary = group["total_tokens_per_accepted_solution"]
        lines.append(
            f"| {group['category']} | {group['representation']} | "
            f"{group['accepted']}/{group['trials']} | "
            f"{'null' if primary is None else round(primary, 2)} | "
            f"{group['token_components']['input_tokens']['median']} | "
            f"{group['token_components']['output_tokens']['median']} | "
            f"{round(group['total_tokens']['population_variance'], 2)} |"
        )
    lines.extend(["", "Failed trials remain in raw data and in the numerator of the primary metric.", ""])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--case", action="append")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--output", type=Path, required=True)
    run_parser.add_argument("--run-id", default="static-reference-v1")
    run_parser.add_argument("--repetitions", type=int, default=1)
    run_parser.add_argument("--case", action="append")
    run_parser.add_argument("--timeout", type=int, default=30)
    aggregate_parser = subparsers.add_parser("aggregate")
    aggregate_parser.add_argument("--raw", type=Path, required=True)
    aggregate_parser.add_argument("--output", type=Path, required=True)
    report_parser = subparsers.add_parser("report")
    report_parser.add_argument("--aggregate", type=Path, required=True)
    report_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "validate":
            cases = discover_cases(args.case)
            print(json.dumps({"valid": True, "cases": len(cases)}, separators=(",", ":")))
        elif args.command == "run":
            if args.repetitions < 1 or args.timeout < 1:
                raise BenchmarkError("repetitions and timeout must be positive")
            run(args.output, args.run_id, args.repetitions, args.case, args.timeout)
        elif args.command == "aggregate":
            aggregate(args.raw, args.output)
        elif args.command == "report":
            report(args.aggregate, args.output)
    except (BenchmarkError, OSError) as error:
        print(f"benchmark error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
