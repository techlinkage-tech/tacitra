#!/usr/bin/env python3
"""Verify frozen confirmation inputs and retained results without model access."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    base = ROOT / "benchmarks/confirmation"
    prereg_path = base / "preregistration-v1.json"
    prereg = json.loads(prereg_path.read_text(encoding="utf-8"))
    pins = prereg["pins"]
    files = {
        "builder_revision": ROOT / "benchmarks/confirmation/build_cases.py",
        "comparison_revision": ROOT / "benchmarks/model_compare.py",
        "prompt_revision": ROOT / "benchmarks/model/prompts/artifact-v1.md",
        "report_revision": ROOT / "benchmarks/model_report.py",
    }
    for key, path in files.items():
        if pins[key] != digest(path.read_bytes()):
            raise RuntimeError(f"frozen confirmation pin changed: {key}")

    model_harness_path = ROOT / "benchmarks/model_harness.py"
    static_harness_path = ROOT / "benchmarks/harness.py"
    harness_revision = digest(model_harness_path.read_bytes() + static_harness_path.read_bytes())
    if pins["harness_revision"] != harness_revision:
        raise RuntimeError("frozen confirmation pin changed: harness_revision")

    harness = load_module("release_confirmation_harness", static_harness_path)
    for suite, pin_name in (
        ("baseline", "baseline_case_revisions"),
        ("optimized", "optimized_case_revisions"),
    ):
        harness.BENCHMARKS = base / suite
        revisions = {
            case["id"]: harness.case_revision(path, case)
            for path, case in harness.discover_cases()
        }
        if revisions != pins[pin_name]:
            raise RuntimeError(f"frozen confirmation {suite} cases changed")

    expected_prereg = digest(prereg_path.read_bytes())
    results = ROOT / "benchmarks/results/model-confirmation-v1"
    comparison = json.loads((results / "comparison.json").read_text(encoding="utf-8"))
    if comparison["preregistration_revision"] != expected_prereg:
        raise RuntimeError("comparison does not identify the retained preregistration")
    rows = [json.loads(line) for line in (results / "raw.jsonl").read_text(encoding="utf-8").splitlines()]
    if len(rows) != prereg["design"]["total_trials"]:
        raise RuntimeError("retained confirmation trial count changed")
    if any(row.get("pins", {}).get("preregistration_revision") != expected_prereg for row in rows):
        raise RuntimeError("one or more raw rows do not identify the preregistration")
    if len({row["trial_id"] for row in rows}) != len(rows):
        raise RuntimeError("retained confirmation has duplicate trial IDs")
    print(json.dumps({"valid": True, "frozen_cases": 20, "retained_trials": len(rows)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
