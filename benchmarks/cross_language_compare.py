#!/usr/bin/env python3
"""Case-clustered, family-wise comparison for cross-language-v1."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import random
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


CROSS = load_module("cross_language_runner_for_compare", ROOT / "benchmarks/cross_language.py")
MODEL = CROSS.MODEL
COMPARATORS = ("python", "go", "rust")
FAMILY_ALPHA = 0.05
ADJUSTED_ALPHA = FAMILY_ALPHA / len(COMPARATORS)
NONINFERIORITY_LIMIT = 0.05


def percentile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * probability)))
    return ordered[index]


def binomial_cdf(events: int, trials: int, probability: float) -> float:
    return sum(
        math.comb(trials, index) * probability**index * (1 - probability) ** (trials - index)
        for index in range(events + 1)
    )


def one_sided_binomial_upper(events: int, trials: int, alpha: float) -> float | None:
    if trials == 0:
        return None
    if events == trials:
        return 1.0
    low, high = 0.0, 1.0
    for _ in range(80):
        middle = (low + high) / 2
        if binomial_cdf(events, trials, middle) > alpha:
            low = middle
        else:
            high = middle
    return high


def primary(rows: list[dict]) -> float | None:
    accepted = sum(row["accepted"] for row in rows)
    return None if accepted == 0 else sum(row["metrics"]["total_tokens"] for row in rows) / accepted


def rate(rows: list[dict], field: str = "accepted") -> float:
    return sum(bool(row[field]) for row in rows) / len(rows)


def row_summary(rows: list[dict]) -> dict:
    return {
        "trials": len(rows),
        "accepted": sum(row["accepted"] for row in rows),
        "acceptance_rate": rate(rows),
        "compile_at_1_rate": rate(rows, "compile_at_1"),
        "pass_at_1_rate": rate(rows, "pass_at_1"),
        "total_tokens_per_accepted_solution": primary(rows),
        "repair_rounds": CROSS.metric([row["repair_rounds"] for row in rows]),
        "input_tokens": CROSS.metric([row["metrics"]["input_tokens"] for row in rows]),
        "output_tokens": CROSS.metric([row["metrics"]["output_tokens"] for row in rows]),
        "reasoning_tokens": CROSS.metric([row["metrics"]["reasoning_tokens"] for row in rows]),
        "cached_input_tokens": CROSS.metric([row["metrics"]["cached_input_tokens"] for row in rows]),
        "patch_size": CROSS.metric([row["patch_size"] for row in rows if row["patch_size"] is not None]) if any(row["patch_size"] is not None for row in rows) else None,
        "wall_clock_time": CROSS.metric([row["wall_clock_time"] for row in rows]),
    }


def compare_one(by_case: dict[str, dict[str, dict]], comparator: str,
                samples: int, seed: int) -> dict:
    case_ids = sorted(by_case)
    tacitra = [by_case[case_id]["tacitra"] for case_id in case_ids]
    other = [by_case[case_id][comparator] for case_id in case_ids]
    observed_tacitra = primary(tacitra)
    observed_other = primary(other)
    observed_difference = None if observed_tacitra is None or observed_other is None else observed_tacitra - observed_other
    rng = random.Random(seed)
    token_differences = []
    acceptance_differences = []
    for _ in range(samples):
        sampled = [case_ids[rng.randrange(len(case_ids))] for _ in case_ids]
        left = [by_case[case_id]["tacitra"] for case_id in sampled]
        right = [by_case[case_id][comparator] for case_id in sampled]
        left_primary, right_primary = primary(left), primary(right)
        if left_primary is not None and right_primary is not None:
            token_differences.append(left_primary - right_primary)
        acceptance_differences.append(rate(left) - rate(right))
    comparator_accepted = [case_id for case_id in case_ids if by_case[case_id][comparator]["accepted"]]
    losses = sum(not by_case[case_id]["tacitra"]["accepted"] for case_id in comparator_accepted)
    loss_rate = None if not comparator_accepted else losses / len(comparator_accepted)
    loss_upper = one_sided_binomial_upper(losses, len(comparator_accepted), ADJUSTED_ALPHA)
    categories = []
    for category in sorted({by_case[case_id]["tacitra"]["category"] for case_id in case_ids}):
        left = [row for row in tacitra if row["category"] == category]
        right = [row for row in other if row["category"] == category]
        categories.append({
            "category": category,
            "tacitra": row_summary(left),
            "comparator": row_summary(right),
            "token_difference": None if primary(left) is None or primary(right) is None else primary(left) - primary(right),
        })
    every_category = all(any(row["accepted"] for row in tacitra if row["category"] == category["category"]) for category in categories)
    adjusted_lower = percentile(token_differences, ADJUSTED_ALPHA)
    adjusted_upper = percentile(token_differences, 1 - ADJUSTED_ALPHA)
    supports = (
        adjusted_upper is not None and adjusted_upper < 0
        and loss_upper is not None and loss_upper <= NONINFERIORITY_LIMIT
        and every_category
    )
    contradicts = (
        (loss_rate is not None and loss_rate > NONINFERIORITY_LIMIT)
        or (adjusted_lower is not None and adjusted_lower >= 0)
    )
    status = "supports_advantage" if supports else "does_not_support" if contradicts else "inconclusive"
    return {
        "comparator": comparator,
        "tacitra": row_summary(tacitra),
        "comparator_result": row_summary(other),
        "difference": {
            "total_tokens_per_accepted_solution": observed_difference,
            "acceptance_rate": rate(tacitra) - rate(other),
            "case_cluster_bootstrap_95_percent_interval": {
                "total_tokens_per_accepted_solution": [percentile(token_differences, 0.025), percentile(token_differences, 0.975)],
                "acceptance_rate": [percentile(acceptance_differences, 0.025), percentile(acceptance_differences, 0.975)],
                "samples": samples,
                "seed": seed,
            },
            "familywise_one_sided_interval": {
                "alpha": ADJUSTED_ALPHA,
                "lower": adjusted_lower,
                "upper": adjusted_upper,
                "method": "Bonferroni-adjusted percentile case-cluster bootstrap",
            },
        },
        "noninferiority": {
            "comparator_accepted_cases": len(comparator_accepted),
            "tacitra_losses": losses,
            "observed_loss_rate": loss_rate,
            "familywise_one_sided_upper": loss_upper,
            "limit": NONINFERIORITY_LIMIT,
            "alpha": ADJUSTED_ALPHA,
            "method": "Bonferroni-adjusted exact Clopper-Pearson",
        },
        "every_category_has_tacitra_acceptance": every_category,
        "categories": categories,
        "status": status,
    }


def compare(rows: list[dict], samples: int, seed: int) -> dict:
    if len(rows) != 340:
        raise MODEL.ModelBenchmarkError(f"expected 340 trials, found {len(rows)}")
    by_case: dict[str, dict[str, dict]] = {}
    for row in rows:
        if row["case_id"] in by_case and row["language"] in by_case[row["case_id"]]:
            raise MODEL.ModelBenchmarkError("duplicate case/language trial")
        by_case.setdefault(row["case_id"], {})[row["language"]] = row
    if len(by_case) != 85 or any(set(values) != set(CROSS.LANGUAGES) for values in by_case.values()):
        raise MODEL.ModelBenchmarkError("result is not one complete trial per case and language")
    conditions = {
        (row["pins"]["provider"], row["pins"]["endpoint"], row["pins"]["model"],
         json.dumps(row["pins"]["model_settings"], sort_keys=True), row["pins"]["config_revision"],
         row["pins"].get("preregistration_revision"))
        for row in rows
    }
    if len(conditions) != 1:
        raise MODEL.ModelBenchmarkError("trials mix model conditions or preregistrations")
    comparisons = [compare_one(by_case, comparator, samples, seed + index) for index, comparator in enumerate(COMPARATORS)]
    supported = [value["comparator"] for value in comparisons if value["status"] == "supports_advantage"]
    contradicted = [value["comparator"] for value in comparisons if value["status"] == "does_not_support"]
    if len(supported) == 3:
        classification = "supports_language_advantage"
    elif supported:
        classification = "supports_partial_advantage"
    elif len(contradicted) == 3:
        classification = "does_not_support_advantage"
    else:
        classification = "inconclusive"
    provider, endpoint, model, settings, config_revision, preregistration_revision = next(iter(conditions))
    return {
        "schema_version": 1,
        "evidence": "measured",
        "measurement_mode": "cross_language_comparison",
        "provider": provider,
        "endpoint": endpoint,
        "model": model,
        "model_settings": json.loads(settings),
        "config_revision": config_revision,
        "preregistration_revision": preregistration_revision,
        "independent_cases": len(by_case),
        "total_trials": len(rows),
        "multiple_comparison": {"method": "Bonferroni", "familywise_alpha": FAMILY_ALPHA, "comparisons": 3, "per_comparison_alpha": ADJUSTED_ALPHA},
        "comparisons": comparisons,
        "decision": {"classification": classification, "supported_against": supported, "contradicted_by": contradicted},
        "limitations": [
            "Case-cluster bootstrap treats each case as the resampling unit and does not treat repeated attempts as independent.",
            "The cases are fixed benchmark tasks rather than a random sample of all programming work.",
            "Differences in pretrained familiarity and native type systems are intentionally part of the language effect.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bootstrap-samples", type=int, default=20000)
    parser.add_argument("--seed", type=int, default=20260912)
    args = parser.parse_args()
    try:
        if args.bootstrap_samples < 1:
            raise MODEL.ModelBenchmarkError("bootstrap samples must be positive")
        document = compare(MODEL.read_rows(args.raw), args.bootstrap_samples, args.seed)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (MODEL.ModelBenchmarkError, OSError) as error:
        print(f"cross-language comparison error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
