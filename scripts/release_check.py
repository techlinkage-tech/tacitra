#!/usr/bin/env python3
"""Run the complete, offline Tacitra 0.1.0 release-readiness check."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def run(label: str, *command: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
    print(f"[{label}] {' '.join(command)}", flush=True)
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    if result.returncode != expected:
        raise RuntimeError(
            f"{label} failed with {result.returncode}\n{result.stdout[-4000:]}\n{result.stderr[-4000:]}"
        )
    return result


def identical(label: str, actual: Path, expected: Path) -> None:
    if actual.read_bytes() != expected.read_bytes():
        raise RuntimeError(f"{label} is not reproducible: {expected}")


def validate_schemas() -> None:
    identifiers: set[str] = set()
    paths = sorted((ROOT / "protocol/schema").glob("*.json"))
    paths += sorted((ROOT / "benchmarks/schema").glob("*.json"))
    for path in paths:
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            raise RuntimeError(f"schema draft is not pinned: {path}")
        identifier = value.get("$id")
        if not isinstance(identifier, str) or identifier in identifiers:
            raise RuntimeError(f"schema $id is missing or duplicated: {path}")
        identifiers.add(identifier)
    print(f"[schemas] {len(paths)} versioned schemas parsed", flush=True)


def validate_dependency_licenses() -> None:
    result = run(
        "licenses", "cargo", "metadata", "--locked", "--offline", "--format-version", "1"
    )
    metadata = json.loads(result.stdout)
    missing = sorted(
        f"{package['name']} {package['version']}"
        for package in metadata["packages"]
        if package.get("source") is not None and not package.get("license")
    )
    if missing:
        raise RuntimeError("dependencies without declared license metadata: " + ", ".join(missing))


def main() -> int:
    try:
        run("format", "cargo", "fmt", "--all", "--", "--check")
        run(
            "clippy", "cargo", "clippy", "--locked", "--offline", "--workspace",
            "--all-targets", "--", "-D", "warnings",
        )
        run(
            "rust-tests", "cargo", "test", "--locked", "--offline", "--workspace",
            "--all-targets",
        )
        run("python-tests", PYTHON, "-m", "unittest", "discover", "-s", "benchmarks/tests", "-v")
        validate_schemas()
        validate_dependency_licenses()

        cli = ROOT / "target/debug/tacitra"
        sample = ROOT / "examples/sample-project/main.taci"
        run("sample-parse", str(cli), "parse", str(sample))
        run("sample-format", str(cli), "fmt", "--check", str(sample))
        run("sample-check", str(cli), "check", str(sample))
        executed = run("sample-run", str(cli), "run", str(sample))
        if executed.stdout.strip() != "42":
            raise RuntimeError("sample program did not return 42")
        run("sample-query", str(cli), "symbol.edit-context", str(sample), "sym:fn:increment")
        run(
            "sample-patch-dry-run",
            str(cli), "patch.validate", str(sample),
            str(ROOT / "examples/sample-project/increment-by-two.patch.json"),
        )
        manifest = ROOT / "examples/interop/python/manifest.json"
        run("python-interop-inspect", str(cli), "interop.inspect", str(manifest))
        interop = run(
            "python-interop-call", str(cli), "interop.call", str(manifest), "add",
            str(ROOT / "examples/interop/python/add.arguments.json"),
        )
        if json.loads(interop.stdout)["result"] != 42:
            raise RuntimeError("Python interop sample did not return 42")

        run("benchmark-cases", PYTHON, "benchmarks/harness.py", "validate")
        run("optimized-cases", PYTHON, "benchmarks/run_optimized.py", "validate")
        run("confirmation-pins", PYTHON, "scripts/check_confirmation.py")
        run("confirmation-references", PYTHON, "scripts/validate_confirmation_references.py")

        with tempfile.TemporaryDirectory(prefix="tacitra-release-check-") as directory:
            temporary = Path(directory)
            static_aggregate = temporary / "static.aggregate.json"
            after_aggregate = temporary / "after.aggregate.json"
            comparison = temporary / "comparison.json"
            model_aggregate = temporary / "model.aggregate.json"
            model_comparison = temporary / "model.comparison.json"
            model_report = temporary / "model.report.md"
            run(
                "static-reaggregate", PYTHON, "benchmarks/harness.py", "aggregate", "--raw",
                "benchmarks/results/static-reference-v1/raw.jsonl", "--output", str(static_aggregate),
            )
            identical("static aggregate", static_aggregate, ROOT / "benchmarks/results/static-reference-v1/aggregate.json")
            run(
                "m6-reaggregate", PYTHON, "benchmarks/run_optimized.py", "aggregate", "--raw",
                "benchmarks/results/m6-optimization-v1/after.raw.jsonl", "--output", str(after_aggregate),
            )
            identical("M6 aggregate", after_aggregate, ROOT / "benchmarks/results/m6-optimization-v1/after.aggregate.json")
            run(
                "m6-recompare", PYTHON, "benchmarks/compare.py", "--before",
                "benchmarks/results/m6-optimization-v1/before.aggregate.json", "--after",
                str(after_aggregate), "--output", str(comparison),
            )
            identical("M6 comparison", comparison, ROOT / "benchmarks/results/m6-optimization-v1/comparison.json")
            raw = "benchmarks/results/model-confirmation-v1/raw.jsonl"
            run("model-reaggregate", PYTHON, "benchmarks/model_harness.py", "aggregate", "--raw", raw, "--output", str(model_aggregate))
            identical("model aggregate", model_aggregate, ROOT / "benchmarks/results/model-confirmation-v1/aggregate.json")
            run(
                "model-recompare", PYTHON, "benchmarks/model_compare.py", "--paired", raw,
                "--output", str(model_comparison), "--bootstrap-samples", "10000",
                "--seed", "20260911", "--max-accepted-loss-rate", "0.05",
            )
            identical("model comparison", model_comparison, ROOT / "benchmarks/results/model-confirmation-v1/comparison.json")
            run(
                "model-rereport", PYTHON, "benchmarks/model_report.py", "--aggregate",
                str(model_aggregate), "--comparison", str(model_comparison), "--output", str(model_report),
            )
            identical("model report", model_report, ROOT / "benchmarks/results/model-confirmation-v1/report.md")

        if (ROOT / ".env.local").exists():
            run("credential-ignore", "git", "check-ignore", "-q", ".env.local")
        run("diff-whitespace", "git", "diff", "--check")
    except (OSError, ValueError, KeyError, RuntimeError, json.JSONDecodeError) as error:
        print(f"release check failed: {error}", file=sys.stderr)
        return 1
    print("release check passed", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
