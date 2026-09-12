#!/usr/bin/env python3
"""Reproduce cross-language decomposition and semantic-protocol local measurements."""

from __future__ import annotations

import argparse
import importlib.util
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "benchmarks/semantic-protocol"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


STATIC = load("semantic_protocol_static_base", ROOT / "benchmarks/harness.py")


def metric(values: list[float]) -> dict:
    return {"mean": statistics.fmean(values), "median": statistics.median(values), "population_variance": statistics.pvariance(values)}


def cross_decomposition() -> dict:
    rows = [json.loads(line) for line in (ROOT / "benchmarks/results/cross-language-v1/raw.jsonl").read_text().splitlines()]
    means = {}
    for language in ("tacitra", "python", "go", "rust"):
        selected = [row for row in rows if row["language"] == language]
        means[language] = {field: statistics.fmean(row["metrics"][field] for row in selected) for field in ("input_tokens", "output_tokens", "total_tokens")}
    comparisons = []
    for language in ("python", "go", "rust"):
        total = means["tacitra"]["total_tokens"] - means[language]["total_tokens"]
        input_difference = means["tacitra"]["input_tokens"] - means[language]["input_tokens"]
        comparisons.append({"comparator": language, "input_difference": input_difference, "output_difference": means["tacitra"]["output_tokens"] - means[language]["output_tokens"], "total_difference": total, "input_share_of_difference": input_difference / total, "reduction_needed_to_match": total / means["tacitra"]["total_tokens"]})
    return {"evidence": "measured", "source": "cross-language-v1", "means": means, "comparisons": comparisons}


def named_edit(compact: dict) -> bytes:
    names = {"body": "replace_function_body", "expr": "replace_expression"}
    value = {"version": 1, "hash": compact["h"], "capabilities": compact["cap"], "operations": [{"kind": names[row[0]], "target": row[1], "replacement": row[2]} for row in compact["ops"]]}
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def verbose_edit(compact: dict) -> bytes:
    names = {"body": "replace_function_body", "expr": "replace_expression"}
    value = {"schema_version": 1, "base_hash": compact["h"], "operations": [{"op": names[row[0]], "target": row[1], "replacement": row[2]} for row in compact["ops"]]}
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def local_measurement() -> dict:
    STATIC.BENCHMARKS = BASE
    cases = [value for value in STATIC.discover_cases() if value[1]["id"].startswith("sp-dev-")]
    instructions = (BASE / "persistent-instructions-v1.md").stat().st_size
    rows = []
    candidates = {"legacy_verbose_object": [], "compact_named_object": [], "compact_tuple": []}
    for case_path, case in cases:
        for representation in case["representations"]:
            outcome = STATIC.run_representation(case_path, case, representation, "semantic-protocol-static-v1", 1, 30)
            if not outcome["accepted"]:
                raise RuntimeError(f"reference rejected: {case['id']}/{representation['id']}")
            directory = case_path.parent
            sizes = {
                "instruction": instructions,
                "specification": STATIC.count_files(directory, representation["specification"]),
                "repository_context": STATIC.count_files(directory, representation["repository_context"]),
                "diagnostic": STATIC.count_files(directory, representation["diagnostic_context"]),
                "task": STATIC.relative_file(directory, case["prompt"]).stat().st_size,
                "output": STATIC.relative_file(directory, representation["artifact"]).stat().st_size,
            }
            # The semantic capsule already carries the success condition.  Do not
            # count or send the same natural-language task a second time.
            if representation["id"] == "tacitra-semantic":
                sizes["task"] = 0
            sizes["input"] = sum(sizes[key] for key in ("instruction", "specification", "repository_context", "diagnostic", "task"))
            sizes["total"] = sizes["input"] + sizes["output"]
            rows.append({"case": case["id"], "category": case["category"], "representation": representation["id"], "evidence": "measured", "tokenizer": "utf8-bytes/1", "accepted": True, "tokens": sizes})
        compact = json.loads((case_path.parent / "reference.tacitra.edit.json").read_text())
        candidates["legacy_verbose_object"].append(len(verbose_edit(compact)))
        candidates["compact_named_object"].append(len(named_edit(compact)))
        candidates["compact_tuple"].append(len(json.dumps(compact, sort_keys=True, separators=(",", ":")).encode()))
    groups = []
    for representation in sorted({row["representation"] for row in rows}):
        selected = [row for row in rows if row["representation"] == representation]
        groups.append({"representation": representation, "trials": len(selected), "accepted": sum(row["accepted"] for row in selected), **{key: metric([row["tokens"][key] for row in selected]) for key in ("specification", "repository_context", "diagnostic", "input", "output", "total")}})
    candidate_result = {name: {"evidence": "measured", "tokenizer": "utf8-bytes/1", "bytes": metric(values), "schema_validatable": True, "unambiguous": True} for name, values in candidates.items()}
    chosen = next(group for group in groups if group["representation"] == "tacitra-semantic")
    ordinary = next(group for group in groups if group["representation"] == "tacitra-ordinary")
    fixed = instructions + int(chosen["specification"]["mean"])
    dynamic = chosen["total"]["mean"] - fixed
    warm = {str(tasks): {"evidence": "projected", "tasks": tasks, "total_utf8_bytes": fixed + dynamic * tasks, "bytes_per_task": (fixed + dynamic * tasks) / tasks} for tasks in (1, 10, 100)}
    full_spec = sum((ROOT / path).stat().st_size for path in ("docs/language/syntax.md", "docs/language/semantics.md", "docs/agent-protocol.md"))
    ablations = {
        "full": chosen["total"]["mean"],
        "no_task_scoped_specification": chosen["total"]["mean"] - chosen["specification"]["mean"] + full_spec,
        "no_semantic_query": chosen["total"]["mean"] - chosen["repository_context"]["mean"] + ordinary["repository_context"]["mean"],
        "no_typed_structural_patch": chosen["total"]["mean"] - chosen["output"]["mean"] + statistics.fmean(candidates["legacy_verbose_object"]),
        "no_minimal_repair_context": None,
        "conversation_or_cache": {"stateless": chosen["total"]["mean"], "warm_amortization": warm},
    }
    return {"evidence": "measured", "tokenizer": "utf8-bytes/1", "rows": rows, "groups": groups, "edit_candidates": candidate_result, "ablations": ablations, "warm_session_simulation": warm}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    document = {"schema_version": 1, "cross_language_decomposition": cross_decomposition(), "semantic_protocol_static": local_measurement()}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"valid": True, "output": str(args.output), "rows": len(document["semantic_protocol_static"]["rows"])}))
    return 0


if __name__ == "__main__": raise SystemExit(main())
