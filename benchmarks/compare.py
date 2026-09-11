#!/usr/bin/env python3
"""Compare two compatible Tacitra benchmark aggregates deterministically."""

import argparse
import json
from pathlib import Path


COMPONENTS = (
    "instruction_tokens",
    "specification_tokens",
    "repository_context_tokens",
    "task_tokens",
    "output_tokens",
    "diagnostic_tokens",
    "repair_tokens",
)


def load(path: Path) -> dict:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def percent(delta: float, before: float) -> float | None:
    return None if before == 0 else 100.0 * delta / before


def summarize(document: dict) -> dict:
    components = {name: 0.0 for name in COMPONENTS}
    total = 0.0
    for group in document["groups"]:
        trials = group["trials"]
        total += group["total_tokens"]["mean"] * trials
        for name in COMPONENTS:
            components[name] += group["token_components"][name]["mean"] * trials
    accepted = document["accepted"]
    return {
        "trials": document["raw_trials"],
        "accepted": accepted,
        "acceptance_rate": accepted / document["raw_trials"],
        "total_tokens": total,
        "total_tokens_per_accepted_solution": None if accepted == 0 else total / accepted,
        "components": components,
    }


def group_key(group: dict) -> tuple[str, str, str, str]:
    return group["category"], group["language"], group["surface"], group["representation"]


def classify(before: dict, after: dict) -> str:
    if after["acceptance_rate"] < before["acceptance_rate"]:
        return "regressed_accuracy"
    delta = after["total_tokens_per_accepted_solution"] - before["total_tokens_per_accepted_solution"]
    if delta < 0:
        return "improved"
    if delta > 0:
        return "regressed"
    return "unchanged"


def compare(before: dict, after: dict) -> dict:
    for key in ("tokenizer_name", "tokenizer_version", "measurement_mode"):
        if before[key] != after[key]:
            raise ValueError(f"incompatible {key}: {before[key]!r} != {after[key]!r}")
    before_summary = summarize(before)
    after_summary = summarize(after)
    group_before = {group_key(group): group for group in before["groups"]}
    group_after = {group_key(group): group for group in after["groups"]}
    if group_before.keys() != group_after.keys():
        raise ValueError("aggregate group sets differ")

    groups = []
    for key in sorted(group_before):
        left = group_before[key]
        right = group_after[key]
        left_value = left["total_tokens_per_accepted_solution"]
        right_value = right["total_tokens_per_accepted_solution"]
        left_rate = left["acceptance_rate"]
        right_rate = right["acceptance_rate"]
        row = {
            "category": key[0],
            "language": key[1],
            "surface": key[2],
            "representation": key[3],
            "before_total_tokens_per_accepted_solution": left_value,
            "after_total_tokens_per_accepted_solution": right_value,
            "delta_tokens": right_value - left_value,
            "delta_percent": percent(right_value - left_value, left_value),
            "before_acceptance_rate": left_rate,
            "after_acceptance_rate": right_rate,
            "classification": classify(left, right),
        }
        groups.append(row)

    component_deltas = {}
    for name in COMPONENTS:
        left = before_summary["components"][name]
        right = after_summary["components"][name]
        component_deltas[name] = {
            "before": left,
            "after": right,
            "delta": right - left,
            "delta_percent": percent(right - left, left),
        }

    left_total = before_summary["total_tokens_per_accepted_solution"]
    right_total = after_summary["total_tokens_per_accepted_solution"]
    return {
        "schema_version": 1,
        "evidence": "measured_static_reference",
        "tokenizer": {"name": before["tokenizer_name"], "version": before["tokenizer_version"]},
        "statistical_note": "Token counts are deterministic with zero within-group variance; model accuracy and model-token effects remain unmeasured.",
        "before": before_summary,
        "after": after_summary,
        "overall": {
            "delta_tokens_per_accepted_solution": right_total - left_total,
            "delta_percent": percent(right_total - left_total, left_total),
            "acceptance_rate_delta": after_summary["acceptance_rate"] - before_summary["acceptance_rate"],
            "classification": classify(before_summary, after_summary),
        },
        "component_deltas": component_deltas,
        "groups": groups,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", required=True, type=Path)
    parser.add_argument("--after", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = compare(load(args.before), load(args.after))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
