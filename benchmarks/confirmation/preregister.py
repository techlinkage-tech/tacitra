#!/usr/bin/env python3
"""Freeze the confirmation-v1 design and all inputs before model execution."""

import argparse
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = ROOT / "benchmarks/model_harness.py"
SPEC = importlib.util.spec_from_file_location("confirmation_model_harness", MODEL_PATH)
MODEL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODEL
SPEC.loader.exec_module(MODEL)


def case_metadata(suite: str) -> list[dict]:
    MODEL.configure_suite(suite)
    return [
        {
            "id": case["id"],
            "category": case["category"],
            "representation": case["representations"][0]["id"],
            "max_repair_rounds": case["max_repair_rounds"],
        }
        for _, case in MODEL.STATIC.discover_cases()
    ]


def document(config: dict) -> dict:
    baseline = case_metadata("confirmation-baseline")
    optimized = case_metadata("confirmation-optimized")
    if baseline != optimized or len(baseline) != 20:
        raise MODEL.ModelBenchmarkError("confirmation suites are not paired at 20 cases")
    categories = Counter(item["category"] for item in baseline)
    if set(categories.values()) != {4} or set(categories) != MODEL.STATIC.CATEGORIES:
        raise MODEL.ModelBenchmarkError("confirmation suite must contain four cases per category")
    if {item["max_repair_rounds"] for item in baseline} != {2}:
        raise MODEL.ModelBenchmarkError("confirmation repair budget must be two")
    repetitions = 3
    paired_trials = len(baseline) * repetitions
    return {
        "schema_version": 1,
        "id": "confirmation-v1",
        "status": "frozen-before-run",
        "date": "2026-09-11",
        "hypothesis": "Milestone 6 context projections reduce total provider tokens without losing more than 5% of baseline-accepted changes.",
        "model_condition": {
            "provider": config["provider"],
            "model": config["model"],
            "settings": config["settings"],
            "config_revision": MODEL.sha256(MODEL.canonical_json(config)),
        },
        "design": {
            "case_count": len(baseline),
            "cases_per_category": dict(sorted(categories.items())),
            "repetitions": repetitions,
            "paired_trials": paired_trials,
            "total_trials": paired_trials * 2,
            "max_repair_rounds": 2,
            "schedule_seed": config["schedule_seed"],
            "cases": baseline,
        },
        "decision_rule": {
            "primary_metric": "total_tokens_per_accepted_solution",
            "token_difference": "optimized_minus_baseline",
            "token_bootstrap_samples": 10000,
            "token_bootstrap_seed": 20260911,
            "require_token_interval_upper_below": 0,
            "accepted_loss_definition": "optimized failure among pairs accepted by baseline",
            "max_accepted_loss_rate": 0.05,
            "accepted_loss_confidence": 0.95,
            "require_every_category_has_accepted_optimized_trial": True,
        },
        "pins": {
            "harness_revision": MODEL.sha256(
                MODEL.MODEL_HARNESS_BYTES + MODEL.HARNESS_PATH.read_bytes()),
            "prompt_revision": MODEL.sha256(MODEL.PROMPT_PATH.read_bytes()),
            "builder_revision": MODEL.sha256((Path(__file__).parent / "build_cases.py").read_bytes()),
            "comparison_revision": MODEL.sha256((ROOT / "benchmarks/model_compare.py").read_bytes()),
            "report_revision": MODEL.sha256((ROOT / "benchmarks/model_report.py").read_bytes()),
            "baseline_case_revisions": MODEL.suite_revisions("confirmation-baseline"),
            "optimized_case_revisions": MODEL.suite_revisions("confirmation-optimized"),
        },
        "interpretation": "A passing decision supports these projections on the frozen suite and model condition; it does not establish other-model or other-task generality.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise MODEL.ModelBenchmarkError(f"refusing to overwrite preregistration: {args.output}")
        config = MODEL.load_config(args.config)
        value = document(config)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({
            "frozen": True,
            "paired_trials": value["design"]["paired_trials"],
            "total_trials": value["design"]["total_trials"],
            "revision": MODEL.sha256(args.output.read_bytes()),
        }, separators=(",", ":")))
    except (MODEL.ModelBenchmarkError, OSError) as error:
        print(f"preregistration error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
