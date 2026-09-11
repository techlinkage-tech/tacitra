#!/usr/bin/env python3
"""Paired comparison and bootstrap interval for model benchmark raw JSONL."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import random
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "benchmarks/model_harness.py"
SPEC = importlib.util.spec_from_file_location("tacitra_model_harness", MODEL_PATH)
assert SPEC is not None and SPEC.loader is not None
MODEL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODEL
SPEC.loader.exec_module(MODEL)


def pair_key(row: dict) -> tuple[str, str, str]:
    trial = row["trial_id"].rsplit(":", 1)[-1]
    return row["case_id"], row["representation"], trial


def condition(row: dict) -> str:
    suite = row["pins"]["suite"]
    if suite.endswith("optimized"):
        return "optimized"
    if suite.endswith("baseline"):
        return "baseline"
    raise MODEL.ModelBenchmarkError(f"unknown paired condition: {suite}")


def binomial_cdf(successes: int, trials: int, probability: float) -> float:
    return sum(
        math.comb(trials, index)
        * probability**index
        * (1 - probability) ** (trials - index)
        for index in range(successes + 1)
    )


def one_sided_binomial_upper(successes: int, trials: int, alpha: float = 0.05) -> float | None:
    if trials == 0:
        return None
    if successes == trials:
        return 1.0
    low, high = 0.0, 1.0
    for _ in range(80):
        middle = (low + high) / 2
        if binomial_cdf(successes, trials, middle) > alpha:
            low = middle
        else:
            high = middle
    return high


def rate(rows: list[dict]) -> float:
    return sum(row["accepted"] for row in rows) / len(rows)


def primary(rows: list[dict]) -> float | None:
    accepted = sum(row["accepted"] for row in rows)
    total = sum(row["metrics"]["total_tokens"] for row in rows)
    return None if not accepted else total / accepted


def percentile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = round((len(ordered) - 1) * probability)
    return ordered[index]


def compare(baseline: list[dict], optimized: list[dict], samples: int, seed: int,
            noninferiority_margin: float | None = None,
            max_accepted_loss_rate: float | None = None) -> dict:
    left = {pair_key(row): row for row in baseline}
    right = {pair_key(row): row for row in optimized}
    if len(left) != len(baseline) or len(right) != len(optimized) or left.keys() != right.keys():
        raise MODEL.ModelBenchmarkError("raw runs are not one-to-one paired")
    conditions = {
        (
            row["pins"]["provider"], row["pins"]["endpoint"], row["pins"]["model"],
            json.dumps(row["pins"]["model_settings"], sort_keys=True),
            row["pins"]["config_revision"],
            row["pins"].get("preregistration_revision"),
        )
        for row in baseline + optimized
    }
    if len(conditions) != 1:
        raise MODEL.ModelBenchmarkError("paired runs use different model conditions")
    keys = sorted(left)
    baseline_rows = [left[key] for key in keys]
    optimized_rows = [right[key] for key in keys]
    left_primary = primary(baseline_rows)
    right_primary = primary(optimized_rows)
    observed_delta = None if left_primary is None or right_primary is None else right_primary - left_primary

    rng = random.Random(seed)
    token_deltas = []
    rate_deltas = []
    for _ in range(samples):
        indexes = [rng.randrange(len(keys)) for _ in keys]
        sample_left = [baseline_rows[index] for index in indexes]
        sample_right = [optimized_rows[index] for index in indexes]
        left_value = primary(sample_left)
        right_value = primary(sample_right)
        if left_value is not None and right_value is not None:
            token_deltas.append(right_value - left_value)
        rate_deltas.append(rate(sample_right) - rate(sample_left))

    groups = []
    group_names = sorted({(row["category"], row["representation"]) for row in baseline_rows})
    for category, representation in group_names:
        group_left = [
            row for row in baseline_rows
            if row["category"] == category and row["representation"] == representation
        ]
        group_right = [
            right[pair_key(row)] for row in group_left
        ]
        before = primary(group_left)
        after = primary(group_right)
        groups.append({
            "category": category,
            "representation": representation,
            "trials": len(group_left),
            "baseline_acceptance_rate": rate(group_left),
            "optimized_acceptance_rate": rate(group_right),
            "baseline_total_tokens_per_accepted_solution": before,
            "optimized_total_tokens_per_accepted_solution": after,
            "delta": None if before is None or after is None else after - before,
        })

    provider, endpoint, model, settings, config_revision, preregistration_revision = next(iter(conditions))
    token_interval = [percentile(token_deltas, 0.025), percentile(token_deltas, 0.975)]
    rate_interval = [percentile(rate_deltas, 0.025), percentile(rate_deltas, 0.975)]
    baseline_successes = [key for key in keys if left[key]["accepted"]]
    accepted_losses = sum(not right[key]["accepted"] for key in baseline_successes)
    loss_rate = None if not baseline_successes else accepted_losses / len(baseline_successes)
    loss_upper = one_sided_binomial_upper(accepted_losses, len(baseline_successes))
    optimized_category_acceptance = {
        category: any(row["accepted"] for row in optimized_rows if row["category"] == category)
        for category in sorted({row["category"] for row in optimized_rows})
    }
    every_category_accepted = all(optimized_category_acceptance.values())
    decision = "not_preregistered"
    if max_accepted_loss_rate is not None and None not in token_interval and loss_upper is not None:
        if token_interval[1] < 0 and loss_upper <= max_accepted_loss_rate and every_category_accepted:
            decision = "supports_adoption"
        elif loss_rate is not None and (
            loss_rate > max_accepted_loss_rate or not every_category_accepted
        ):
            decision = "reject"
        else:
            decision = "inconclusive"
    elif noninferiority_margin is not None and None not in token_interval + rate_interval:
        if token_interval[1] < 0 and rate_interval[0] >= noninferiority_margin:
            decision = "supports_adoption"
        elif token_interval[0] >= 0 or rate_interval[1] < noninferiority_margin:
            decision = "reject"
        else:
            decision = "inconclusive"
    return {
        "schema_version": 1,
        "evidence": "measured",
        "measurement_mode": "model_paired_comparison",
        "provider": provider,
        "endpoint": endpoint,
        "model": model,
        "model_settings": json.loads(settings),
        "config_revision": config_revision,
        "preregistration_revision": preregistration_revision,
        "paired_trials": len(keys),
        "baseline": {
            "accepted": sum(row["accepted"] for row in baseline_rows),
            "acceptance_rate": rate(baseline_rows),
            "total_tokens_per_accepted_solution": left_primary,
        },
        "optimized": {
            "accepted": sum(row["accepted"] for row in optimized_rows),
            "acceptance_rate": rate(optimized_rows),
            "total_tokens_per_accepted_solution": right_primary,
        },
        "difference": {
            "total_tokens_per_accepted_solution": observed_delta,
            "acceptance_rate": rate(optimized_rows) - rate(baseline_rows),
            "bootstrap_95_percent_interval": {
                "total_tokens_per_accepted_solution": token_interval,
                "acceptance_rate": rate_interval,
                "samples": samples,
                "seed": seed,
            },
        },
        "decision": {
            "acceptance_noninferiority_margin": noninferiority_margin,
            "max_accepted_loss_rate": max_accepted_loss_rate,
            "baseline_accepted_pairs": len(baseline_successes),
            "optimized_losses_on_baseline_successes": accepted_losses,
            "observed_accepted_loss_rate": loss_rate,
            "accepted_loss_rate_one_sided_95_percent_upper": loss_upper,
            "optimized_category_has_acceptance": optimized_category_acceptance,
            "every_category_has_optimized_acceptance": every_category_accepted,
            "classification": decision,
        },
        "limitations": [
            "The paired bootstrap is conditional on the observed cases and repetitions.",
            "An all-success run produces a degenerate empirical acceptance-difference bootstrap interval; the separate one-sided accepted-loss bound is used for non-inferiority.",
        ],
        "groups": groups,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paired", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--optimized", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20260911)
    parser.add_argument("--acceptance-noninferiority-margin", type=float)
    parser.add_argument("--max-accepted-loss-rate", type=float)
    args = parser.parse_args()
    try:
        if args.bootstrap_samples < 1:
            raise MODEL.ModelBenchmarkError("bootstrap samples must be positive")
        if args.acceptance_noninferiority_margin is not None and not (
            -1.0 <= args.acceptance_noninferiority_margin <= 0.0
        ):
            raise MODEL.ModelBenchmarkError("noninferiority margin must be between -1 and 0")
        if args.max_accepted_loss_rate is not None and not (0.0 < args.max_accepted_loss_rate < 1.0):
            raise MODEL.ModelBenchmarkError("max accepted loss rate must be between 0 and 1")
        if args.max_accepted_loss_rate is not None and args.acceptance_noninferiority_margin is not None:
            raise MODEL.ModelBenchmarkError("choose only one acceptance noninferiority rule")
        if args.paired:
            if args.baseline or args.optimized:
                raise MODEL.ModelBenchmarkError("use --paired or separate raw files, not both")
            rows = MODEL.read_rows(args.paired)
            baseline = [row for row in rows if condition(row) == "baseline"]
            optimized = [row for row in rows if condition(row) == "optimized"]
        else:
            if not args.baseline or not args.optimized:
                raise MODEL.ModelBenchmarkError("both --baseline and --optimized are required")
            baseline = MODEL.read_rows(args.baseline)
            optimized = MODEL.read_rows(args.optimized)
        result = compare(
            baseline, optimized, args.bootstrap_samples, args.seed,
            args.acceptance_noninferiority_margin, args.max_accepted_loss_rate,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (MODEL.ModelBenchmarkError, OSError) as error:
        print(f"model comparison error: {error}", file=__import__("sys").stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
