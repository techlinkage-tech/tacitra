#!/usr/bin/env python3
"""Render semantic protocol v2 results from frozen aggregate/comparison JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def percent(value):
    return "not estimable" if value is None else f"{value * 100:.2f}%"


def number(value):
    return "not estimable" if value is None else f"{value:.2f}"


def render(aggregate: dict, comparison: dict) -> str:
    lines = ["# Semantic protocol v2 results", "", f"Evidence: `{comparison['evidence']}`.", ""]
    if comparison.get("confirmatory"):
        lines += [f"Preregistered decision: `{comparison['classification']}`.", "", "| Condition | Accepted | compile@1 | pass@1 | Total / accepted | Input | Visible output | Reasoning | Cached | Repair output |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for name, result in ((comparison["candidate"], comparison["candidate_result"]), ("ordinary", comparison["ordinary_result"])):
            lines.append(f"| {name} | {result['accepted']}/{result['trials']} | {percent(result['compile_at_1'])} | {percent(result['pass_at_1'])} | {number(result['total_tokens_per_accepted_solution'])} | {result['input_tokens']} | {result['output_tokens']} | {result['reasoning_tokens']} | {result['cached_input_tokens']} | {result['repair_output_tokens']} |")
        difference = comparison["difference"]
        lines += ["", f"Candidate minus ordinary total-token difference: {number(difference['total_tokens_per_accepted_solution'])}; paired bootstrap 95% interval [{number(difference['paired_bootstrap_95_percent_interval'][0])}, {number(difference['paired_bootstrap_95_percent_interval'][1])}]. Observed reduction: {percent(difference['observed_token_reduction_rate'])}."]
    else:
        lines += [f"Selected candidate: `{comparison.get('selected_candidate')}`. Proceed: `{comparison['proceed_to_confirmation']}`.", "", "| Condition | Accepted | Total / accepted | Reasoning | Loss rate | Eligible |", "|---|---:|---:|---:|---:|---:|"]
        base = comparison["baseline"]
        lines.append(f"| ordinary | {base['accepted']}/{base['trials']} | {number(base['total_tokens_per_accepted_solution'])} | {base['reasoning_tokens']} | — | — |")
        for item in comparison["comparisons"]:
            result = item["result"]
            lines.append(f"| {item['candidate']} | {result['accepted']}/{result['trials']} | {number(result['total_tokens_per_accepted_solution'])} | {result['reasoning_tokens']} | {percent(item['observed_loss_rate'])} | {item['eligible']} |")
        lines += ["", "This pilot selected a workflow and is not confirmatory evidence."]
    lines += ["", "Provider totals include failed trials and every repair. Reasoning and cached tokens are informational subsets and are not added twice.", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aggregate", type=Path, required=True)
    parser.add_argument("--comparison", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    aggregate = json.loads(args.aggregate.read_text(encoding="utf-8"))
    comparison = json.loads(args.comparison.read_text(encoding="utf-8"))
    args.output.write_text(render(aggregate, comparison), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
