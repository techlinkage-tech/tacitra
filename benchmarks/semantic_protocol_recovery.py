#!/usr/bin/env python3
"""API-free preflight and Rust fixture validation for a future replication."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "benchmarks/semantic-protocol"
PROPOSED_RAW = ROOT / "benchmarks/results/semantic-protocol-replication-v1/raw.jsonl"
REPORT = ROOT / "benchmarks/results/rust-environment-recovery-v1/prevalidation.json"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


FROZEN = load("semantic_recovery_frozen", ROOT / "benchmarks/semantic_protocol.py")
RUNTIME = load("semantic_recovery_runtime", ROOT / "benchmarks/runtime_environment.py")


def frozen_inputs() -> tuple[dict, list[tuple[Path, dict]], str]:
    config = FROZEN.load_config()
    cases = FROZEN.heldout_cases()
    _, revision = FROZEN.validate_prereg(config, cases)
    expected = "sha256:65d7e426a0f5264c0c3307707ca1431f1135da3c6af9be8459b4dcaa9573cee4"
    if revision != expected:
        raise RUNTIME.EnvironmentFailure(
            "environment_preflight_failure", None, "frozen preregistration hash changed",
        )
    return config, cases, revision


def run_preflight(environment: dict[str, str] | None = None,
                  output: Path = PROPOSED_RAW) -> tuple[object, dict, list, str]:
    config, cases, revision = frozen_inputs()
    events = output.with_suffix(output.suffix + ".events.jsonl")
    runtime = RUNTIME.preflight(
        environment=environment,
        root=ROOT,
        required_files=(
            BASE / "config-v1.json", BASE / "prompt-v1.md",
            BASE / "preregistration-v1.json", ROOT / "Cargo.lock",
        ),
        unused_outputs=(output, events),
    )
    return runtime, config, cases, revision


def client_after_preflight(factory, *, environment: dict[str, str] | None = None,
                           output: Path = PROPOSED_RAW):
    """Construct a provider client only after every local prerequisite succeeds."""
    runtime, config, cases, revision = run_preflight(environment, output)
    return runtime, config, cases, revision, factory(config)


def classify_failure(phase: str, result) -> str:
    if result is not None and result.classification:
        return result.classification
    if phase in {"setup", "prepare"}:
        return "model_generation_failure"
    if phase == "compile":
        return "compile_failure"
    if phase == "test":
        return "test_failure"
    return "fixture_prevalidation_failure"


def validate_artifact(runtime, case_path: Path, case: dict, representation: dict,
                      artifact: Path, timeout: int) -> dict:
    case_dir = case_path.parent
    with tempfile.TemporaryDirectory(prefix="tacitra-replication-validation-") as directory:
        work = Path(directory)
        candidate = work / f"candidate{artifact.suffix}"
        shutil.copyfile(artifact, candidate)
        for setup in representation["setup_files"]:
            shutil.copyfile(FROZEN.MODEL.STATIC.relative_file(case_dir, setup["source"]), work / setup["target"])
        phase = "prepare"
        ok, result = RUNTIME.execute_commands(
            representation["prepare_commands"], case_dir, candidate, work, timeout, runtime,
        )
        compile_ok = tests_ok = False
        if ok:
            phase = "compile"
            compile_ok, result = RUNTIME.execute_commands(
                representation["compile_commands"], case_dir, candidate, work, timeout, runtime,
            )
        if ok and compile_ok:
            phase = "test"
            tests_ok, result = RUNTIME.execute_commands(
                representation["test_commands"], case_dir, candidate, work, timeout, runtime,
            )
            if tests_ok:
                try:
                    actual = FROZEN.MODEL.STATIC.normalized_result(result.stdout, representation["result_kind"])
                    tests_ok = actual == case["acceptance"]["expected_integer"]
                except (ValueError, KeyError, TypeError, json.JSONDecodeError):
                    tests_ok = False
        accepted = ok and compile_ok and tests_ok
        return {
            "accepted": accepted,
            "compile_ok": compile_ok,
            "tests_ok": tests_ok,
            "failure_classification": None if accepted else classify_failure(phase, result),
            "phase": None if accepted else phase,
            "exit_code": None if result is None else result.returncode,
            "timed_out": False if result is None else result.timed_out,
            "stdout": "" if result is None or accepted else result.stdout[-4096:],
            "stderr": "" if result is None or accepted else result.stderr[-4096:],
        }


def prevalidate_rust(runtime, cases: list[tuple[Path, dict]], timeout: int) -> dict:
    rows = []
    for case_path, case in cases:
        representation = next(value for value in case["representations"] if value["id"] == "rust-ordinary")
        artifact = FROZEN.MODEL.STATIC.relative_file(case_path.parent, representation["artifact"])
        outcome = validate_artifact(runtime, case_path, case, representation, artifact, timeout)
        rows.append({"case_id": case["id"], **outcome})
    accepted = sum(row["accepted"] for row in rows)
    return {
        "schema_version": 1,
        "evidence": "measured-local",
        "classification": "fixture_prevalidation_success" if accepted == len(rows) else "fixture_prevalidation_failure",
        "provider_api_calls": 0,
        "runtime": runtime.public_record(),
        "cases": len(rows),
        "accepted": accepted,
        "failed": len(rows) - accepted,
        "isolated_temporary_directory_per_case": True,
        "same_execution_function_as_replication": "semantic_protocol_recovery.validate_artifact",
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("preflight")
    validate = sub.add_parser("prevalidate-rust")
    validate.add_argument("--output", type=Path, default=REPORT)
    validate.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    try:
        runtime, _, cases, revision = run_preflight()
        if args.command == "preflight":
            print(json.dumps({
                **runtime.public_record(), "preregistration_revision": revision,
                "heldout_cases": len(cases), "planned_trials": 300,
            }, indent=2, sort_keys=True))
            return 0
        document = prevalidate_rust(runtime, cases, args.timeout)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        if args.output.exists():
            raise RUNTIME.EnvironmentFailure(
                "environment_preflight_failure", None, "prevalidation output already exists",
            )
        args.output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({
            "classification": document["classification"], "cases": document["cases"],
            "accepted": document["accepted"], "provider_api_calls": 0,
        }, sort_keys=True))
        return 0 if document["failed"] == 0 else 2
    except RUNTIME.EnvironmentFailure as error:
        print(RUNTIME.public_error(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
