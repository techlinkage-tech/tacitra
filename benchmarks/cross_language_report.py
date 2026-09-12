#!/usr/bin/env python3
"""Render the preregistered cross-language-v1 results."""

import argparse
import json
from pathlib import Path


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def number(value) -> str:
    return "null" if value is None else f"{value:,.2f}"


def render(aggregate: dict, comparison: dict) -> str:
    by_language = {value["language"]: value for value in aggregate["languages"]}
    lines = [
        "# Cross-language-v1 real-model results",
        "",
        f"Evidence: `measured`; model: `{comparison['model']}`; decision: "
        f"`{comparison['decision']['classification']}`.",
        "",
        "| Language | Accepted | compile@1 | pass@1 | Repairs median | Input mean | Output mean | Total / accepted |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for language in ("tacitra", "python", "go", "rust"):
        value = by_language[language]
        lines.append(
            f"| {language} | {value['accepted']}/{value['trials']} | "
            f"{value['compile_at_1_rate']:.1%} | {value['pass_at_1_rate']:.1%} | "
            f"{number(value['repair_rounds']['median'])} | {number(value['input_tokens']['mean'])} | "
            f"{number(value['output_tokens']['mean'])} | {number(value['total_tokens_per_accepted_solution'])} |"
        )
    lines.extend(["", "## Preregistered comparisons", "",
                  "Differences are Tacitra minus comparator. Negative token differences favor Tacitra.", "",
                  "| Comparator | Acceptance Δ | Token Δ | Adjusted upper | Tacitra losses | FWER upper | Status |",
                  "|---|---:|---:|---:|---:|---:|---|"])
    for value in comparison["comparisons"]:
        lines.append(
            f"| {value['comparator']} | {value['difference']['acceptance_rate']:.3f} | "
            f"{number(value['difference']['total_tokens_per_accepted_solution'])} | "
            f"{number(value['difference']['familywise_one_sided_interval']['upper'])} | "
            f"{value['noninferiority']['tacitra_losses']}/{value['noninferiority']['comparator_accepted_cases']} | "
            f"{number(value['noninferiority']['familywise_one_sided_upper'])} | {value['status']} |"
        )
    lines.extend(["", "## Interpretation limits", ""])
    lines.extend(f"- {item}" for item in comparison["limitations"])
    lines.extend([
        "- Provider usage is authoritative; cached and reasoning tokens are informational subsets and are not added twice.",
        "- Failed trials and every repair attempt remain in the primary token numerator.",
        "- This primary evaluation does not use semantic queries or structural patches for any language.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aggregate", type=Path, required=True)
    parser.add_argument("--comparison", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(load(args.aggregate), load(args.comparison)), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
