#!/usr/bin/env python3
"""Run the unchanged benchmark harness against the Milestone 6 case set."""

import importlib.util
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HARNESS_PATH = ROOT / "benchmarks" / "harness.py"
SPEC = importlib.util.spec_from_file_location("tacitra_benchmark_harness", HARNESS_PATH)
assert SPEC is not None and SPEC.loader is not None
HARNESS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HARNESS)
PROFILE = os.environ.get("TACITRA_BENCHMARK_PROFILE", "final")
if PROFILE not in {"stage1", "final"}:
    raise SystemExit(f"unknown TACITRA_BENCHMARK_PROFILE: {PROFILE}")
HARNESS.BENCHMARKS = ROOT / "benchmarks" / "optimized"
if PROFILE == "stage1":
    HARNESS.BENCHMARKS /= "stage1"


if __name__ == "__main__":
    raise SystemExit(HARNESS.main())
