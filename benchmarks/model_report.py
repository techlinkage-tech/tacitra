#!/usr/bin/env python3
"""Generate a human-readable report from retained model aggregate and comparison JSON."""

import argparse
import json
from pathlib import Path


def load(path: Path) -> dict:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def format_number(value: float | None) -> str:
    return "null" if value is None else f"{value:,.2f}"


def report(aggregate: dict, comparison: dict) -> str:
    before = comparison["baseline"]["total_tokens_per_accepted_solution"]
    after = comparison["optimized"]["total_tokens_per_accepted_solution"]
    reduction = None if before in {None, 0} or after is None else 100 * (before - after) / before
    interval = comparison["difference"]["bootstrap_95_percent_interval"]
    settings = json.dumps(aggregate["model_settings"], sort_keys=True, separators=(",", ":"))
    confirmation = comparison.get("preregistration_revision") is not None
    title = "Confirmatory real-model evaluation report" if confirmation else "Real-model paired pilot report"
    decision = comparison["decision"]
    lines = [
        f"# {title}",
        "",
        f"Evidence: `measured`; mode: `model`; provider: `{aggregate['provider']}`; "
        f"model: `{aggregate['model']}`; settings: `{settings}`.",
        "",
        "| Suite | Accepted | compile@1 | pass@1 | Repairs median | Input mean | Output mean | Total / accepted |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for group in aggregate["groups"]:
        lines.append(
            f"| {group['suite']} | {group['accepted']}/{group['trials']} | "
            f"{group['compile_at_1_rate']:.0%} | {group['pass_at_1_rate']:.0%} | "
            f"{group['repair_rounds']['median']} | {group['input_tokens']['mean']:,.2f} | "
            f"{group['output_tokens']['mean']:,.2f} | "
            f"{format_number(group['total_tokens_per_accepted_solution'])} |"
        )
    lines.extend([
        "",
        f"Complete run: {aggregate['accepted']}/{aggregate['raw_trials']} accepted; "
        f"{aggregate['total_tokens']:,} provider-reported total tokens.",
        "",
        f"Observed optimized-minus-baseline difference: "
        f"{format_number(comparison['difference']['total_tokens_per_accepted_solution'])} tokens "
        f"({format_number(reduction)}% reduction).",
        "",
        f"Seeded paired-bootstrap 95% interval for the token difference: "
        f"[{format_number(interval['total_tokens_per_accepted_solution'][0])}, "
        f"{format_number(interval['total_tokens_per_accepted_solution'][1])}].",
        "",
        f"Decision: `{decision['classification']}`.",
        "",
        "## Interpretation limits",
        "",
    ])
    lines.extend(f"- {item}" for item in comparison["limitations"])
    if confirmation:
        lines.append(
            f"- Accepted-loss one-sided 95% upper bound: "
            f"{format_number(100 * decision['accepted_loss_rate_one_sided_95_percent_upper'])}% "
            f"against a {format_number(100 * decision['max_accepted_loss_rate'])}% maximum."
        )
    else:
        lines.append("- The run covers one repository-change case and three paired repetitions; it is pilot evidence, not confirmatory proof.")
        lines.append("- No acceptance non-inferiority threshold was preregistered for this pilot.")
    lines.extend([
        "- Provider token totals are measured. Prompt-section byte fields are not model-token estimates.",
        "- Failed trials would remain in the numerator; this run had no failed or repair trials.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aggregate", type=Path, required=True)
    parser.add_argument("--comparison", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    content = report(load(args.aggregate), load(args.comparison))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
