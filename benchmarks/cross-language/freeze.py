#!/usr/bin/env python3
"""Validate and freeze the cross-language-v1 preregistration exactly once."""

from __future__ import annotations

import importlib.util
import json
import math
import statistics
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "benchmarks/cross-language"
OUTPUT = BASE / "preregistration-v1.json"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


BUILDER = load_module("cross_language_builder_for_freeze", BASE / "build_cases.py")
CROSS = load_module("cross_language_runner_for_freeze", ROOT / "benchmarks/cross_language.py")


def sample_size(alpha: float, limit: float) -> int:
    return math.ceil(math.log(alpha) / math.log(1 - limit))


def estimate_budget(config: dict, cases: list[tuple[Path, dict]]) -> dict:
    calibration_path = ROOT / "benchmarks/results/model-confirmation-v1/raw.jsonl"
    calibration = [json.loads(line) for line in calibration_path.read_text(encoding="utf-8").splitlines()]
    input_ratios = []
    output_ratios = []
    for row in calibration:
        attempt = row["attempts"][0]
        input_bytes = len(row["persistent_instructions"]["text"].encode()) + len(attempt["input_text"].encode())
        response_bytes = len(attempt["response_text"].encode())
        input_ratios.append(attempt["usage"]["input_tokens"] / input_bytes)
        if response_bytes:
            output_ratios.append(attempt["usage"]["output_tokens"] / response_bytes)
    input_ratio = statistics.median(input_ratios)
    output_ratio = statistics.median(output_ratios)
    first_attempt_input = 0.0
    first_attempt_output = 0.0
    for case_path, case, representation in CROSS.resolve_schedule(config, cases):
        prompt, _ = CROSS.base_prompt(case_path, case, representation)
        instructions = CROSS.PERSISTENT.read_text(encoding="utf-8")
        artifact = CROSS.MODEL.STATIC.relative_file(case_path.parent, representation["artifact"]).read_text(encoding="utf-8")
        response = json.dumps({"artifact": artifact}, separators=(",", ":"))
        first_attempt_input += (len(instructions.encode()) + len(prompt.encode())) * input_ratio
        first_attempt_output += len(response.encode()) * output_ratio
    first_attempt_total = round(first_attempt_input + first_attempt_output)
    projected_ceiling = round(first_attempt_total * 3 + 2 * 340 * config["settings"]["max_output_tokens"])
    return {
        "evidence": "estimated",
        "calibration": "confirmation-v1 first-attempt median provider-token/UTF-8-byte ratios",
        "calibration_trials": len(calibration),
        "input_tokens_per_byte_median": input_ratio,
        "output_tokens_per_byte_median": output_ratio,
        "expected_api_calls_if_no_repairs": 340,
        "maximum_api_calls": 1020,
        "estimated_first_attempt_provider_tokens": first_attempt_total,
        "projected_three_attempt_token_ceiling": projected_ceiling,
        "estimated_cost_usd": None,
        "cost_formula": "(provider_input_tokens * account_input_USD_per_million + provider_output_tokens * account_output_USD_per_million) / 1000000",
        "cost_note": "No official public price was found for the exact pinned gpt-5.6-luna identifier; obtain account-specific rates before Phase B rather than substituting another model price.",
    }


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("refusing to overwrite frozen preregistration-v1.json")
    BUILDER.validate()
    config = CROSS.MODEL.load_config(CROSS.CONFIG)
    CROSS.MODEL.STATIC.BENCHMARKS = BASE
    cases = CROSS.MODEL.STATIC.discover_cases()
    family_alpha = 0.05
    comparisons = 3
    adjusted_alpha = family_alpha / comparisons
    required = sample_size(adjusted_alpha, 0.05)
    assert required == 80
    category_counts = {}
    for _, case in cases:
        category_counts[case["category"]] = category_counts.get(case["category"], 0) + 1
    document = {
        "schema_version": 1,
        "id": "cross-language-v1",
        "status": "frozen-before-run",
        "research_question": "Under common task, context-selection, retry, and model conditions, how does source language affect provider tokens and accepted correctness?",
        "design": {
            "primary": "source-language comparison",
            "languages": list(CROSS.LANGUAGES),
            "comparators": ["python", "go", "rust"],
            "categories": category_counts,
            "independent_cases": len(cases),
            "repetitions": 1,
            "trials_per_case": 4,
            "total_trials": len(cases) * 4,
            "max_repair_rounds": 2,
            "maximum_attempts_per_trial": 3,
            "output_contract": {"generation": "complete source", "repository-change": "unified diff", "debug-repair": "unified diff"},
            "secondary_protocol_assisted": "not_run_no_equivalent_cross_language_semantic_protocol",
        },
        "fairness": {
            "same_language_neutral_task_per_case": True,
            "same_information_selection_rule": True,
            "same_prompt_template": True,
            "same_persistent_instructions": True,
            "same_diagnostic_selection": "first failing compiler/check/test result; last 4096 bytes of stdout and stderr; deterministic JSON field order",
            "same_repair_feedback": "previous artifact plus bounded validation failure JSON",
            "reference_solutions_in_model_input": False,
            "tacitra_semantic_queries": False,
            "tacitra_structural_patches": False,
            "external_packages": False,
            "language_specific_type_systems_retained": True,
            "known_language_extra_specification": False,
            "tacitra_minimum_specification_counted": True,
            "schedule": "seeded case shuffle with rotating/reversed four-language blocks",
        },
        "statistics": {
            "primary_metric": "total_tokens_per_accepted_solution including failed trials and all attempts in numerator",
            "pairing": "case",
            "bootstrap_unit": "case",
            "bootstrap_samples": 20000,
            "bootstrap_seed": 20260912,
            "comparisons": ["tacitra-minus-python", "tacitra-minus-go", "tacitra-minus-rust"],
            "multiple_comparison_method": "Bonferroni family-wise one-sided alpha",
            "familywise_alpha": family_alpha,
            "per_comparison_alpha": adjusted_alpha,
            "noninferiority_limit": 0.05,
            "zero_loss_required_comparator_accepted_cases": required,
            "sample_size_formula": "ceil(log(0.05/3) / log(1-0.05)) = 80",
            "planned_cases_formula": "ceil(80 / 0.95) = 85 to tolerate up to 5% comparator nonacceptance",
        },
        "decision_rule": {
            "supports_language_advantage": "all three comparisons have adjusted token upper < 0, adjusted exact loss upper <= 0.05, and every category has a Tacitra acceptance",
            "supports_partial_advantage": "one or two comparisons meet every advantage gate; name them",
            "does_not_support_advantage": "no comparison passes and all three show adjusted evidence against token advantage or observed loss above 0.05",
            "inconclusive": "all other outcomes",
            "per_comparison_support": "adjusted token upper < 0 and adjusted exact loss upper <= 0.05 and every category has Tacitra acceptance",
            "per_comparison_contradiction": "adjusted token lower >= 0 or observed Tacitra loss rate > 0.05",
        },
        "model_condition": {
            "provider": config["provider"],
            "model": config["model"],
            "settings": config["settings"],
            "request_timeout_seconds": config["request_timeout_seconds"],
            "max_output_characters": config["max_output_characters"],
            "schedule_seed": config["schedule_seed"],
            "config_revision": CROSS.MODEL.sha256(CROSS.MODEL.canonical_json(config)),
            "substitution_allowed": False,
        },
        "budget": estimate_budget(config, cases),
        "pins": CROSS.expected_pins(config, cases),
    }
    OUTPUT.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"frozen": True, "path": str(OUTPUT.relative_to(ROOT)), "revision": CROSS.MODEL.sha256(OUTPUT.read_bytes()), "cases": len(cases), "trials": len(cases) * 4, "budget": document["budget"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
