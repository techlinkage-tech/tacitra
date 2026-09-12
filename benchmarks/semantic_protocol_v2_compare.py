#!/usr/bin/env python3
"""Frozen selection and paired comparison rules for semantic protocol v2."""

from __future__ import annotations

import argparse
import importlib.util
import json
import random
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


HARNESS = load("semantic_v2_compare_harness", ROOT / "benchmarks/semantic_protocol_v2.py")
BASE_COMPARE = load("semantic_v2_compare_base", ROOT / "benchmarks/semantic_protocol_compare.py")
MODEL = HARNESS.MODEL
CANDIDATES = ("capsule-diff", "capsule-fragment", "capsule-named")


def percentile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    position = (len(values) - 1) * probability
    low = int(position)
    high = min(low + 1, len(values) - 1)
    fraction = position - low
    return values[low] * (1 - fraction) + values[high] * fraction


def primary(rows: list[dict]) -> float | None:
    accepted = sum(row["accepted"] for row in rows)
    return None if not accepted else sum(row["metrics"]["total_tokens"] for row in rows) / accepted


def compact(rows: list[dict]) -> dict:
    return HARNESS.summarize(rows)


def pilot(rows: list[dict]) -> dict:
    expected = 120
    if len(rows) != expected:
        raise MODEL.ModelBenchmarkError(f"expected {expected} pilot rows, found {len(rows)}")
    by_name = {name: [row for row in rows if row["representation"] == name] for name in HARNESS.REPRESENTATIONS}
    baseline = by_name["ordinary"]
    comparisons = []
    eligible_candidates = []
    for name in (*CANDIDATES, "compact-control"):
        candidate = by_name[name]
        baseline_by_key = {(row["case_id"], row["trial_id"].rsplit(":", 1)[-1]): row for row in baseline}
        losses = 0
        eligible = 0
        for row in candidate:
            key = (row["case_id"], row["trial_id"].rsplit(":", 1)[-1])
            base = baseline_by_key[key]
            if base["accepted"]:
                eligible += 1
                losses += not row["accepted"]
        categories = {row["category"] for row in candidate if row["accepted"]}
        candidate_primary = primary(candidate)
        baseline_primary = primary(baseline)
        loss_rate = losses / eligible if eligible else None
        valid = (
            name in CANDIDATES
            and loss_rate is not None
            and loss_rate <= 0.05
            and categories == {"repository-change", "debug-repair"}
            and candidate_primary is not None
        )
        if valid:
            eligible_candidates.append((candidate_primary, sum(row["metrics"]["reasoning_tokens"] for row in candidate), name))
        comparisons.append({
            "candidate": name,
            "result": compact(candidate),
            "baseline_accepted_trials": eligible,
            "candidate_losses": losses,
            "observed_loss_rate": loss_rate,
            "accepted_categories": sorted(categories),
            "token_difference": None if candidate_primary is None or baseline_primary is None else candidate_primary - baseline_primary,
            "eligible": valid,
        })
    eligible_candidates.sort()
    selected = eligible_candidates[0][2] if eligible_candidates else None
    selected_comparison = next((item for item in comparisons if item["candidate"] == selected), None)
    proceed = bool(selected_comparison and selected_comparison["token_difference"] < 0)
    return {
        "schema_version": 1,
        "evidence": "measured-development-pilot",
        "confirmatory": False,
        "baseline": compact(baseline),
        "comparisons": comparisons,
        "selected_candidate": selected if proceed else None,
        "best_eligible_candidate": selected,
        "proceed_to_confirmation": proceed,
        "stop_reason": None if proceed else "all_eligible_candidates_worse_than_baseline" if selected else "no_candidate_passed_selection_gates",
    }


def bootstrap(rows: list[dict], candidate: str, samples: int = 20_000, seed: int = 20260917) -> tuple[list[float | None], list[float | None]]:
    cases = sorted({row["case_id"] for row in rows})
    by_key = {(row["case_id"], row["representation"]): row for row in rows}
    rng = random.Random(seed)
    token_differences = []
    acceptance_differences = []
    for _ in range(samples):
        selected = [rng.choice(cases) for _ in cases]
        left = [by_key[(case, candidate)] for case in selected]
        right = [by_key[(case, "ordinary")] for case in selected]
        left_primary = primary(left)
        right_primary = primary(right)
        if left_primary is not None and right_primary is not None:
            token_differences.append(left_primary - right_primary)
        acceptance_differences.append(statistics.fmean(row["accepted"] for row in left) - statistics.fmean(row["accepted"] for row in right))
    return [percentile(token_differences, 0.025), percentile(token_differences, 0.975)], [percentile(acceptance_differences, 0.025), percentile(acceptance_differences, 0.975)]


def confirmation(rows: list[dict], preregistration: dict) -> dict:
    if len(rows) != 120:
        raise MODEL.ModelBenchmarkError(f"expected 120 confirmation rows, found {len(rows)}")
    candidate = preregistration["selected_candidate"]
    left = [row for row in rows if row["representation"] == candidate]
    right = [row for row in rows if row["representation"] == "ordinary"]
    if len(left) != 60 or len(right) != 60:
        raise MODEL.ModelBenchmarkError("confirmation representation counts differ from preregistration")
    interval, acceptance_interval = bootstrap(rows, candidate)
    by_case = {row["case_id"]: row for row in right}
    eligible = [row for row in left if by_case[row["case_id"]]["accepted"]]
    losses = sum(not row["accepted"] for row in eligible)
    loss_upper = BASE_COMPARE.upper(losses, len(eligible)) if eligible else None
    left_primary = primary(left)
    right_primary = primary(right)
    difference = None if left_primary is None or right_primary is None else left_primary - right_primary
    reduction = None if difference is None else -difference / right_primary
    both_categories = {row["category"] for row in left if row["accepted"]} == {"repository-change", "debug-repair"}
    supports = bool(
        loss_upper is not None and loss_upper <= 0.05
        and interval[1] is not None and interval[1] < 0
        and reduction is not None and reduction >= 0.05
        and both_categories
    )
    contradiction = bool(
        difference is not None and difference >= 0
        or loss_upper is not None and loss_upper > 0.05
        or not both_categories
    )
    classification = "supports_semantic_protocol_v2" if supports else "does_not_support_semantic_protocol_v2" if contradiction else "inconclusive"
    return {
        "schema_version": 1,
        "evidence": "measured-confirmatory",
        "confirmatory": True,
        "candidate": candidate,
        "candidate_result": compact(left),
        "ordinary_result": compact(right),
        "difference": {
            "total_tokens_per_accepted_solution": difference,
            "paired_bootstrap_95_percent_interval": interval,
            "acceptance_rate": compact(left)["acceptance_rate"] - compact(right)["acceptance_rate"],
            "acceptance_bootstrap_95_percent_interval": acceptance_interval,
            "observed_token_reduction_rate": reduction,
        },
        "noninferiority": {"ordinary_accepted_cases": len(eligible), "candidate_loss_cases": losses, "observed_loss_rate": losses / len(eligible) if eligible else None, "one_sided_95_upper": loss_upper, "limit": 0.05},
        "accepted_categories": sorted({row["category"] for row in left if row["accepted"]}),
        "classification": classification,
        "categories": [{"category": category, "candidate": compact([row for row in left if row["category"] == category]), "ordinary": compact([row for row in right if row["category"] == category])} for category in ("debug-repair", "repository-change")],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("pilot", "confirmation"), required=True)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        rows = MODEL.read_rows(args.raw)
        if args.phase == "pilot":
            document = pilot(rows)
        else:
            preregistration, _ = HARNESS.validate_prereg("confirmation")
            document = confirmation(rows, preregistration)
        args.output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (MODEL.ModelBenchmarkError, OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(json.dumps({"classification": "comparison_failure", "error_type": type(error).__name__}), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
