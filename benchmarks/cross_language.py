#!/usr/bin/env python3
"""Validate, dry-run, execute, and aggregate cross-language-v1."""

from __future__ import annotations

import argparse
import importlib.util
import json
import random
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_DIR = ROOT / "benchmarks/cross-language"
CONFIG = BASE_DIR / "config-v1.json"
PREREGISTRATION = BASE_DIR / "preregistration-v1.json"
PERSISTENT = BASE_DIR / "persistent-instructions-v1.md"
RESULT = ROOT / "benchmarks/results/cross-language-v1/raw.jsonl"
LANGUAGES = ("python", "go", "rust", "tacitra")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


MODEL = load_module("cross_language_model_base", ROOT / "benchmarks/model_harness.py")
MODEL.STATIC.BENCHMARKS = BASE_DIR


def schedule_document(config: dict, cases: list[tuple[Path, dict]]) -> list[dict]:
    rng = random.Random(config["schedule_seed"])
    ordered_cases = list(cases)
    rng.shuffle(ordered_cases)
    base_languages = list(LANGUAGES)
    rng.shuffle(base_languages)
    result = []
    for index, (case_path, case) in enumerate(ordered_cases):
        by_language = {value["language"]: value for value in case["representations"]}
        language_order = base_languages[index % 4 :] + base_languages[: index % 4]
        if index % 2:
            language_order = list(reversed(language_order))
        for language in language_order:
            representation = by_language[language]
            result.append({
                "case_id": case["id"],
                "category": case["category"],
                "language": language,
                "representation": representation["id"],
                "case_path": str(case_path.relative_to(ROOT)),
            })
    return result


def schedule_hash(config: dict, cases: list[tuple[Path, dict]]) -> str:
    return MODEL.sha256(MODEL.canonical_json(schedule_document(config, cases)))


def case_revisions(cases: list[tuple[Path, dict]]) -> dict[str, str]:
    return {case["id"]: MODEL.STATIC.case_revision(path, case) for path, case in cases}


def expected_pins(config: dict, cases: list[tuple[Path, dict]]) -> dict[str, object]:
    paths = {
        "builder_revision": BASE_DIR / "build_cases.py",
        "case_definitions_revision": BASE_DIR / "definitions-v1.json",
        "comparison_revision": ROOT / "benchmarks/cross_language_compare.py",
        "config_revision": CONFIG,
        "config_schema_revision": BASE_DIR / "config-v1.schema.json",
        "harness_revision": Path(__file__),
        "persistent_instructions_revision": PERSISTENT,
        "prompt_revision": ROOT / "benchmarks/model/prompts/artifact-v1.md",
        "preregistration_schema_revision": BASE_DIR / "preregistration-v1.schema.json",
        "report_revision": ROOT / "benchmarks/cross_language_report.py",
    }
    pins = {name: MODEL.sha256(path.read_bytes()) for name, path in paths.items()}
    pins["case_revisions"] = case_revisions(cases)
    pins["schedule_revision"] = schedule_hash(config, cases)
    return pins


def validate_preregistration(config: dict, cases: list[tuple[Path, dict]]) -> tuple[dict, str]:
    try:
        document = json.loads(PREREGISTRATION.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise MODEL.ModelBenchmarkError(f"invalid cross-language preregistration: {error}") from error
    valid = (
        document.get("schema_version") == 1
        and document.get("id") == "cross-language-v1"
        and document.get("status") == "frozen-before-run"
        and document.get("design", {}).get("independent_cases") == 85
        and document.get("design", {}).get("repetitions") == 1
        and document.get("design", {}).get("total_trials") == 340
        and document.get("model_condition", {}).get("config_revision")
        == MODEL.sha256(MODEL.canonical_json(config))
        and document.get("pins") == expected_pins(config, cases)
    )
    if not valid:
        raise MODEL.ModelBenchmarkError("cross-language preregistration no longer matches frozen inputs")
    return document, MODEL.sha256(PREREGISTRATION.read_bytes())


def base_prompt(case_path: Path, case: dict, representation: dict) -> tuple[str, dict]:
    prompt, components = MODEL.base_prompt(case_path, case, representation)
    components["instruction_bytes"] = PERSISTENT.stat().st_size
    return prompt, components


def run_trial(client, config: dict, case_path: Path, case: dict, representation: dict,
              run_id: str, preregistration_revision: str, command_timeout: int) -> dict:
    started = time.monotonic()
    instructions = PERSISTENT.read_text(encoding="utf-8")
    initial_prompt, initial_components = base_prompt(case_path, case, representation)
    repair = ""
    attempts = []
    final_artifact = None
    for attempt_index in range(1, case["max_repair_rounds"] + 2):
        prompt = initial_prompt + repair
        components = dict(initial_components)
        components["repair_context_bytes"] = len(repair.encode())
        request_document = {
            "model": client.model,
            "instructions": instructions,
            "input": prompt,
            "settings": client.settings,
        }
        attempt_started = time.monotonic()
        reply = client.generate(instructions, prompt)
        artifact = None
        try:
            artifact = MODEL.extract_artifact(reply.text, config["max_output_characters"])
            validation = MODEL.validate_artifact(
                case_path, case, representation, artifact, command_timeout
            )
        except MODEL.ModelBenchmarkError as error:
            validation = {
                "compile_ok": False,
                "tests_ok": False,
                "accepted": False,
                "failure": {"phase": "model_output", "message": str(error)},
            }
        attempts.append({
            "attempt": attempt_index,
            "request_hash": MODEL.sha256(MODEL.canonical_json(request_document)),
            "input_text": prompt,
            "context_bytes": components,
            "response_id": reply.response_id,
            "response_text": reply.text,
            "response_hash": MODEL.sha256(reply.text.encode()),
            "artifact": artifact,
            "usage": {
                "input_tokens": reply.input_tokens,
                "output_tokens": reply.output_tokens,
                "total_tokens": reply.total_tokens,
                "cached_input_tokens": reply.cached_input_tokens,
                "reasoning_tokens": reply.reasoning_tokens,
            },
            "validation": validation,
            "wall_clock_time": round(time.monotonic() - attempt_started, 6),
        })
        final_artifact = artifact
        if validation["accepted"]:
            break
        repair = MODEL.repair_context(artifact, validation["failure"])
    accepted = attempts[-1]["validation"]["accepted"]
    totals = {
        field: sum(attempt["usage"][field] for attempt in attempts)
        for field in ("input_tokens", "output_tokens", "total_tokens", "cached_input_tokens", "reasoning_tokens")
    }
    totals["repair_output_tokens"] = sum(attempt["usage"]["output_tokens"] for attempt in attempts[1:])
    artifact_bytes = None if final_artifact is None else len(final_artifact.encode())
    row = {
        "schema_version": 3,
        "evidence": "measured",
        "measurement_mode": "model",
        "run_id": run_id,
        "trial_id": f"{run_id}:{case['id']}:{representation['language']}",
        "case_id": case["id"],
        "category": case["category"],
        "representation": representation["id"],
        "language": representation["language"],
        "surface": representation["surface"],
        "pins": {
            "suite": "cross-language-v1",
            "case_revision": MODEL.STATIC.case_revision(case_path, case),
            "harness_revision": MODEL.sha256(Path(__file__).read_bytes()),
            "base_harness_revision": MODEL.sha256(MODEL.MODEL_HARNESS_BYTES + MODEL.HARNESS_PATH.read_bytes()),
            "config_revision": MODEL.sha256(MODEL.canonical_json(config)),
            "preregistration_revision": preregistration_revision,
            "provider": client.provider,
            "endpoint": client.endpoint,
            "model": client.model,
            "model_settings": client.settings,
            "usage_source": "provider_response",
            "environment": MODEL.environment_snapshot(),
        },
        "persistent_instructions": {"text": instructions, "hash": MODEL.sha256(instructions.encode())},
        "attempts": attempts,
        "metrics": totals,
        "compile_at_1": attempts[0]["validation"]["compile_ok"],
        "pass_at_1": attempts[0]["validation"]["tests_ok"],
        "repair_rounds": len(attempts) - 1,
        "max_repair_rounds": case["max_repair_rounds"],
        "patch_size": artifact_bytes if representation["artifact_kind"] == "patch" else None,
        "accepted": accepted,
        "wall_clock_time": round(time.monotonic() - started, 6),
        "failure": None if accepted else attempts[-1]["validation"]["failure"],
    }
    MODEL.validate_model_result(row)
    return row


@dataclass
class FakeClient:
    responses: list[str]
    provider: str = "fake-cross-language"
    model: str = "fake-reference-v1"
    endpoint: str = "local://fake"
    settings: dict = None

    def __post_init__(self) -> None:
        self.settings = {} if self.settings is None else self.settings

    def generate(self, instructions: str, input_text: str):
        if not self.responses:
            raise RuntimeError("fake response queue is empty")
        text = self.responses.pop(0)
        input_tokens = len((instructions + input_text).encode())
        output_tokens = len(text.encode())
        return MODEL.ModelReply(text, None, input_tokens, output_tokens, input_tokens + output_tokens, 0, 0)


def resolve_schedule(config: dict, cases: list[tuple[Path, dict]]) -> list[tuple[Path, dict, dict]]:
    lookup = {case["id"]: (path, case) for path, case in cases}
    result = []
    for item in schedule_document(config, cases):
        path, case = lookup[item["case_id"]]
        representation = next(value for value in case["representations"] if value["language"] == item["language"])
        result.append((path, case, representation))
    return result


def write_run(client, config: dict, cases: list[tuple[Path, dict]], output: Path,
              run_id: str, preregistration_revision: str, command_timeout: int) -> None:
    if output.exists():
        raise MODEL.ModelBenchmarkError(f"refusing to overwrite raw result: {output}")
    events = output.with_suffix(output.suffix + ".events.jsonl")
    if events.exists():
        raise MODEL.ModelBenchmarkError(f"refusing to overwrite event journal: {events}")
    output.parent.mkdir(parents=True, exist_ok=True)
    scheduled = resolve_schedule(config, cases)
    with output.open("x", encoding="utf-8") as stream, events.open("x", encoding="utf-8") as journal:
        journal.write(json.dumps({"event": "run_started", "run_id": run_id,
                                  "preregistration_revision": preregistration_revision,
                                  "schedule_revision": schedule_hash(config, cases),
                                  "trials": len(scheduled)}, sort_keys=True, separators=(",", ":")) + "\n")
        journal.flush()
        for case_path, case, representation in scheduled:
            identity = {"case_id": case["id"], "language": representation["language"]}
            journal.write(json.dumps({"event": "trial_started", **identity}, sort_keys=True, separators=(",", ":")) + "\n")
            journal.flush()
            try:
                row = run_trial(client, config, case_path, case, representation, run_id,
                                preregistration_revision, command_timeout)
            except BaseException as error:
                journal.write(json.dumps({"event": "trial_interrupted", **identity,
                                          "error_type": type(error).__name__},
                                         sort_keys=True, separators=(",", ":")) + "\n")
                journal.flush()
                raise
            stream.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
            stream.flush()
            state = "accepted" if row["accepted"] else "failed"
            journal.write(json.dumps({"event": "trial_completed", **identity,
                                      "accepted": row["accepted"],
                                      "attempts": len(row["attempts"])}, sort_keys=True, separators=(",", ":")) + "\n")
            journal.flush()
            print(f"{case['id']}/{representation['language']}: {state}", flush=True)


def dry_run(config: dict, cases: list[tuple[Path, dict]], preregistration_revision: str) -> None:
    scheduled = resolve_schedule(config, cases)
    responses = []
    for case_path, _, representation in scheduled:
        artifact = MODEL.STATIC.relative_file(case_path.parent, representation["artifact"]).read_text(encoding="utf-8")
        responses.append(json.dumps({"artifact": artifact}, separators=(",", ":")))
    with tempfile.TemporaryDirectory(prefix="tacitra-cross-language-dry-run-") as directory:
        output = Path(directory) / "raw.jsonl"
        write_run(FakeClient(responses), config, cases, output, "cross-language-v1-dry-run",
                  preregistration_revision, 30)
        rows = MODEL.read_rows(output)
        if len(rows) != 340 or not all(row["accepted"] for row in rows):
            raise MODEL.ModelBenchmarkError("cross-language fake-model dry run failed")
    print(json.dumps({"valid": True, "fake_trials": 340, "accepted": 340}))


def aggregate(raw: Path, output: Path) -> None:
    rows = MODEL.read_rows(raw)
    preregistrations = {row["pins"].get("preregistration_revision") for row in rows}
    if len(rows) != 340 or len(preregistrations) != 1:
        raise MODEL.ModelBenchmarkError("cross-language result is incomplete or mixes preregistrations")
    grouped = []
    for language in LANGUAGES:
        language_rows = [row for row in rows if row["language"] == language]
        grouped.append(summary(language_rows, language=language))
    categories = []
    for category in sorted({row["category"] for row in rows}):
        for language in LANGUAGES:
            values = [row for row in rows if row["category"] == category and row["language"] == language]
            categories.append(summary(values, language=language, category=category))
    document = {
        "schema_version": 1,
        "evidence": "measured",
        "measurement_mode": "cross_language_model",
        "preregistration_revision": next(iter(preregistrations)),
        "trials": len(rows),
        "languages": grouped,
        "categories": categories,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def metric(values: list[float]) -> dict:
    return MODEL.metric(values)


def summary(rows: list[dict], **labels) -> dict:
    accepted = sum(row["accepted"] for row in rows)
    totals = [row["metrics"]["total_tokens"] for row in rows]
    result = {
        **labels,
        "trials": len(rows),
        "accepted": accepted,
        "acceptance_rate": accepted / len(rows),
        "compile_at_1_rate": sum(row["compile_at_1"] for row in rows) / len(rows),
        "pass_at_1_rate": sum(row["pass_at_1"] for row in rows) / len(rows),
        "repair_rounds": metric([row["repair_rounds"] for row in rows]),
        "input_tokens": metric([row["metrics"]["input_tokens"] for row in rows]),
        "output_tokens": metric([row["metrics"]["output_tokens"] for row in rows]),
        "reasoning_tokens": metric([row["metrics"]["reasoning_tokens"] for row in rows]),
        "cached_input_tokens": metric([row["metrics"]["cached_input_tokens"] for row in rows]),
        "total_tokens": metric(totals),
        "total_tokens_per_accepted_solution": sum(totals) / accepted if accepted else None,
        "patch_size": metric([row["patch_size"] for row in rows if row["patch_size"] is not None]) if any(row["patch_size"] is not None for row in rows) else None,
        "wall_clock_time": metric([row["wall_clock_time"] for row in rows]),
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate")
    subparsers.add_parser("dry-run")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--env-file", type=Path)
    run_parser.add_argument("--output", type=Path, default=RESULT)
    run_parser.add_argument("--command-timeout", type=int, default=30)
    aggregate_parser = subparsers.add_parser("aggregate")
    aggregate_parser.add_argument("--raw", type=Path, required=True)
    aggregate_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "aggregate":
            aggregate(args.raw, args.output)
            return 0
        config = MODEL.load_config(CONFIG)
        MODEL.STATIC.BENCHMARKS = BASE_DIR
        cases = MODEL.STATIC.discover_cases()
        preregistration, revision = validate_preregistration(config, cases)
        if args.command == "validate":
            print(json.dumps({"valid": True, "cases": len(cases), "trials": 340,
                              "model": config["model"], "preregistration_revision": revision}))
        elif args.command == "dry-run":
            dry_run(config, cases, revision)
        else:
            if args.command_timeout < 1:
                raise MODEL.ModelBenchmarkError("command timeout must be positive")
            key = MODEL.load_api_key(args.env_file)
            if not key:
                raise MODEL.ModelBenchmarkError("OPENAI_API_KEY is required and is never stored")
            client = MODEL.OpenAIResponsesClient(config, key)
            write_run(client, config, cases, args.output, "cross-language-v1", revision,
                      args.command_timeout)
    except (MODEL.ModelBenchmarkError, MODEL.STATIC.BenchmarkError, OSError, RuntimeError) as error:
        print(f"cross-language error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
