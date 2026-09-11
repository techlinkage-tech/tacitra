#!/usr/bin/env python3
"""Reproducible real-model benchmark runner for Tacitra case-v2 suites."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import random
import shutil
import statistics
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


ROOT = Path(__file__).resolve().parents[1]
HARNESS_PATH = ROOT / "benchmarks/harness.py"
SPEC = importlib.util.spec_from_file_location("tacitra_static_harness", HARNESS_PATH)
assert SPEC is not None and SPEC.loader is not None
STATIC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(STATIC)
PROMPT_PATH = ROOT / "benchmarks/model/prompts/artifact-v1.md"


class ModelBenchmarkError(Exception):
    pass


@dataclass(frozen=True)
class ModelReply:
    text: str
    response_id: str | None
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cached_input_tokens: int
    reasoning_tokens: int


class ModelClient(Protocol):
    provider: str
    model: str
    settings: dict
    endpoint: str

    def generate(self, instructions: str, input_text: str) -> ModelReply: ...


def sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def require_count(value: object, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ModelBenchmarkError(f"OpenAI response has invalid {field}")
    return value


def response_text(document: dict) -> str:
    direct = document.get("output_text")
    if isinstance(direct, str):
        return direct
    parts = []
    for item in document.get("output", []):
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if isinstance(content, dict) and content.get("type") == "output_text":
                text = content.get("text")
                if isinstance(text, str):
                    parts.append(text)
    if not parts:
        raise ModelBenchmarkError("OpenAI response contains no output text")
    return "".join(parts)


def parse_openai_response(document: object) -> ModelReply:
    if not isinstance(document, dict):
        raise ModelBenchmarkError("OpenAI response is not an object")
    usage = document.get("usage")
    if not isinstance(usage, dict):
        raise ModelBenchmarkError("OpenAI response has no usage object")
    input_details = usage.get("input_tokens_details") or {}
    output_details = usage.get("output_tokens_details") or {}
    if not isinstance(input_details, dict) or not isinstance(output_details, dict):
        raise ModelBenchmarkError("OpenAI response has invalid usage details")
    input_tokens = require_count(usage.get("input_tokens"), "input_tokens")
    output_tokens = require_count(usage.get("output_tokens"), "output_tokens")
    total_tokens = require_count(usage.get("total_tokens"), "total_tokens")
    if total_tokens < input_tokens + output_tokens:
        raise ModelBenchmarkError("OpenAI total_tokens is smaller than input plus output")
    cached = require_count(input_details.get("cached_tokens", 0), "cached_tokens")
    reasoning = require_count(output_details.get("reasoning_tokens", 0), "reasoning_tokens")
    identifier = document.get("id")
    if identifier is not None and not isinstance(identifier, str):
        raise ModelBenchmarkError("OpenAI response id is invalid")
    return ModelReply(
        response_text(document), identifier, input_tokens, output_tokens, total_tokens,
        cached, reasoning,
    )


class OpenAIResponsesClient:
    provider = "openai-responses"

    def __init__(self, config: dict, api_key: str):
        self.model = config["model"]
        self.settings = config["settings"]
        self.timeout = config["request_timeout_seconds"]
        base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        parsed = urllib.parse.urlsplit(base)
        if parsed.scheme not in {"https", "http"} or not parsed.netloc:
            raise ModelBenchmarkError("OPENAI_BASE_URL must be an HTTP(S) URL")
        if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ModelBenchmarkError("OPENAI_BASE_URL must use HTTPS except for localhost")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ModelBenchmarkError("OPENAI_BASE_URL must not contain credentials, query, or fragment")
        self.endpoint = f"{base}/responses"
        self.api_key = api_key

    def generate(self, instructions: str, input_text: str) -> ModelReply:
        body = {
            "model": self.model,
            "instructions": instructions,
            "input": input_text,
            "store": False,
            **self.settings,
        }
        request = urllib.request.Request(
            self.endpoint,
            data=canonical_json(body),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                document = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = error.read(4096).decode("utf-8", errors="replace")
            raise ModelBenchmarkError(f"OpenAI HTTP {error.code}: {detail}") from error
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise ModelBenchmarkError(f"OpenAI request failed: {error}") from error
        return parse_openai_response(document)


def load_config(path: Path) -> dict:
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ModelBenchmarkError(f"invalid model config: {error}") from error
    required = {
        "schema_version", "provider", "model", "settings", "request_timeout_seconds",
        "max_output_characters", "schedule_seed",
    }
    if not isinstance(config, dict) or set(config) != required or config["schema_version"] != 1:
        raise ModelBenchmarkError("model config does not conform to version 1")
    if config["provider"] != "openai-responses":
        raise ModelBenchmarkError("unsupported model provider")
    if not isinstance(config["model"], str) or not config["model"] or config["model"].startswith("SET_"):
        raise ModelBenchmarkError("config must pin a real model identifier")
    if not isinstance(config["settings"], dict):
        raise ModelBenchmarkError("model settings must be an object")
    reserved = {"model", "instructions", "input", "store"} & config["settings"].keys()
    if reserved:
        raise ModelBenchmarkError(f"reserved model setting: {sorted(reserved)[0]}")
    secret_fields = {"api_key", "authorization"} & {key.lower() for key in config["settings"]}
    if secret_fields:
        raise ModelBenchmarkError("credentials are forbidden in model settings")
    for field in ("request_timeout_seconds", "max_output_characters"):
        if not isinstance(config[field], int) or isinstance(config[field], bool) or config[field] < 1:
            raise ModelBenchmarkError(f"{field} must be a positive integer")
    if not isinstance(config["schedule_seed"], int) or isinstance(config["schedule_seed"], bool):
        raise ModelBenchmarkError("schedule_seed must be an integer")
    return config


def load_api_key(env_file: Path | None) -> str | None:
    key = os.environ.get("OPENAI_API_KEY")
    if key or env_file is None:
        return key
    try:
        lines = env_file.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise ModelBenchmarkError(f"cannot read env file: {error}") from error
    found = None
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped[7:].lstrip()
        name, separator, value = stripped.partition("=")
        if not separator or name.strip() != "OPENAI_API_KEY":
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        if found is not None:
            raise ModelBenchmarkError("env file defines OPENAI_API_KEY more than once")
        found = value
    return found or None


def read_labeled(case_dir: Path, names: list[str]) -> tuple[str, int, dict[str, str]]:
    parts = []
    size = 0
    hashes = {}
    for name in names:
        path = STATIC.relative_file(case_dir, name)
        data = path.read_bytes()
        size += len(data)
        hashes[str(path.relative_to(ROOT))] = sha256(data)
        parts.append(f"--- {path.relative_to(ROOT)} ---\n{data.decode('utf-8')}")
    return "\n".join(parts), size, hashes


def artifact_contract(representation: dict) -> str:
    kind = representation["artifact_kind"]
    if kind == "source":
        return "a complete compilable source file"
    if kind == "patch" and representation["surface"] == "semantic-query":
        return "one Tacitra structural patch JSON document"
    if kind == "patch":
        return "one unified diff applicable to the provided program.* file"
    if kind == "arguments":
        return "one JSON object containing the external call arguments"
    return "one complete manifest JSON document"


def base_prompt(case_path: Path, case: dict, representation: dict) -> tuple[str, dict]:
    case_dir = case_path.parent
    template = PROMPT_PATH.read_text(encoding="utf-8")
    specification, specification_bytes, specification_hashes = read_labeled(
        case_dir, representation["specification"])
    repository, repository_bytes, repository_hashes = read_labeled(
        case_dir, representation["repository_context"])
    diagnostics, diagnostic_bytes, diagnostic_hashes = read_labeled(
        case_dir, representation["diagnostic_context"])
    prompt_path = STATIC.relative_file(case_dir, case["prompt"])
    task = prompt_path.read_text(encoding="utf-8")
    values = {
        "language": representation["language"],
        "surface": representation["surface"],
        "artifact_contract": artifact_contract(representation),
        "task": task,
        "specification": specification or "(none)",
        "repository_context": repository or "(none)",
        "diagnostic_context": diagnostics or "(none)",
    }
    text = template.format(**values)
    components = {
        "instruction_bytes": (ROOT / "AGENTS.md").stat().st_size,
        "prompt_template_bytes": len(template.encode()),
        "specification_bytes": specification_bytes,
        "repository_context_bytes": repository_bytes,
        "task_bytes": len(task.encode()),
        "initial_diagnostic_bytes": diagnostic_bytes,
        "repair_context_bytes": 0,
        "hashes": {
            "prompt_template": sha256(template.encode()),
            "task": sha256(task.encode()),
            "specification": specification_hashes,
            "repository_context": repository_hashes,
            "initial_diagnostic": diagnostic_hashes,
        },
    }
    return text, components


def extract_artifact(text: str, maximum: int) -> str:
    if len(text) > maximum:
        raise ModelBenchmarkError("model output exceeds max_output_characters")
    try:
        document = json.loads(text)
    except json.JSONDecodeError as error:
        raise ModelBenchmarkError(f"model output is not artifact JSON: {error.msg}") from error
    if not isinstance(document, dict) or set(document) != {"artifact"} or not isinstance(document["artifact"], str):
        raise ModelBenchmarkError('model output must be exactly {"artifact":"..."}')
    if not document["artifact"]:
        raise ModelBenchmarkError("model artifact is empty")
    return document["artifact"]


def validate_artifact(case_path: Path, case: dict, representation: dict, artifact: str,
                      timeout: int) -> dict:
    case_dir = case_path.parent
    suffix = Path(representation["artifact"]).suffix
    with tempfile.TemporaryDirectory(prefix="tacitra-model-benchmark-") as directory:
        work = Path(directory)
        artifact_path = work / f"candidate{suffix}"
        artifact_path.write_text(artifact, encoding="utf-8")
        for setup in representation["setup_files"]:
            shutil.copyfile(STATIC.relative_file(case_dir, setup["source"]), work / setup["target"])
        prepare_ok, result = STATIC.execute_commands(
            representation["prepare_commands"], case_dir, artifact_path, work, timeout)
        compile_ok = False
        tests_ok = False
        phase = "prepare"
        if prepare_ok:
            phase = "compile"
            compile_ok, result = STATIC.execute_commands(
                representation["compile_commands"], case_dir, artifact_path, work, timeout)
            if not representation["compile_commands"]:
                compile_ok = True
        if prepare_ok and compile_ok:
            phase = "test"
            tests_ok, result = STATIC.execute_commands(
                representation["test_commands"], case_dir, artifact_path, work, timeout)
            if tests_ok:
                try:
                    actual = STATIC.normalized_result(result.stdout, representation["result_kind"])
                    tests_ok = actual == case["acceptance"]["expected_integer"]
                except (ValueError, KeyError, TypeError, json.JSONDecodeError):
                    tests_ok = False
        accepted = prepare_ok and compile_ok and tests_ok
        failure = None
        if not accepted:
            failure = {
                "phase": phase,
                "exit_code": None if result is None else result.returncode,
                "stdout": "" if result is None else result.stdout[-4096:],
                "stderr": "" if result is None else result.stderr[-4096:],
            }
        return {
            "compile_ok": compile_ok,
            "tests_ok": tests_ok,
            "accepted": accepted,
            "failure": failure,
        }


def repair_context(artifact: str | None, failure: dict) -> str:
    previous = "(response did not contain a usable artifact)" if artifact is None else artifact
    return (
        "\n\nREPAIR REQUIRED\nPrevious artifact:\n"
        + previous
        + "\nValidation feedback:\n"
        + json.dumps(failure, sort_keys=True, separators=(",", ":"))
        + "\nReturn a corrected artifact using the same exact JSON envelope."
    )


def run_trial(client: ModelClient, config: dict, suite: str, case_path: Path, case: dict,
              representation: dict, run_id: str, trial: int, command_timeout: int,
              preregistration_revision: str | None = None) -> dict:
    started = time.monotonic()
    instructions = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
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
            artifact = extract_artifact(reply.text, config["max_output_characters"])
            validation = validate_artifact(
                case_path, case, representation, artifact, command_timeout)
        except ModelBenchmarkError as error:
            validation = {
                "compile_ok": False,
                "tests_ok": False,
                "accepted": False,
                "failure": {"phase": "model_output", "message": str(error)},
            }
        attempts.append({
            "attempt": attempt_index,
            "request_hash": sha256(canonical_json(request_document)),
            "input_text": prompt,
            "context_bytes": components,
            "response_id": reply.response_id,
            "response_text": reply.text,
            "response_hash": sha256(reply.text.encode()),
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
        repair = repair_context(artifact, validation["failure"])

    accepted = attempts[-1]["validation"]["accepted"]
    totals = {
        field: sum(attempt["usage"][field] for attempt in attempts)
        for field in (
            "input_tokens", "output_tokens", "total_tokens", "cached_input_tokens",
            "reasoning_tokens",
        )
    }
    totals["repair_output_tokens"] = sum(
        attempt["usage"]["output_tokens"] for attempt in attempts[1:])
    artifact_bytes = None if final_artifact is None else len(final_artifact.encode())
    return {
        "schema_version": 3,
        "evidence": "measured",
        "measurement_mode": "model",
        "run_id": run_id,
        "trial_id": f"{run_id}:{suite}:{case['id']}:{representation['id']}:{trial:03d}",
        "case_id": case["id"],
        "category": case["category"],
        "representation": representation["id"],
        "language": representation["language"],
        "surface": representation["surface"],
        "pins": {
            "suite": suite,
            "case_revision": STATIC.case_revision(case_path, case),
            "harness_revision": sha256(MODEL_HARNESS_BYTES + HARNESS_PATH.read_bytes()),
            "config_revision": sha256(canonical_json(config)),
            "preregistration_revision": preregistration_revision,
            "provider": client.provider,
            "endpoint": client.endpoint,
            "model": client.model,
            "model_settings": client.settings,
            "usage_source": "provider_response",
            "environment": environment_snapshot(),
        },
        "persistent_instructions": {
            "text": instructions,
            "hash": sha256(instructions.encode()),
        },
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


def environment_snapshot() -> dict:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "go": STATIC.tool_version(["go", "version"]),
        "rustc": STATIC.tool_version([os.environ.get("RUSTC", "rustc"), "--version"]),
        "tacitra_cli": sha256((ROOT / "target/debug/tacitra").read_bytes()),
        "cargo_lock": sha256((ROOT / "Cargo.lock").read_bytes()),
    }


MODEL_HARNESS_BYTES = Path(__file__).read_bytes()


def validate_model_result(row: dict) -> None:
    if row.get("schema_version") != 3 or row.get("measurement_mode") != "model":
        raise ModelBenchmarkError("not a model result v3")
    if not row.get("attempts"):
        raise ModelBenchmarkError("model result has no attempts")
    persistent = row.get("persistent_instructions")
    if not isinstance(persistent, dict) or set(persistent) != {"text", "hash"}:
        raise ModelBenchmarkError("model result has invalid persistent instructions")
    if persistent["hash"] != sha256(persistent["text"].encode()):
        raise ModelBenchmarkError("persistent instruction hash is inconsistent")
    summed = {
        field: sum(attempt["usage"][field] for attempt in row["attempts"])
        for field in (
            "input_tokens", "output_tokens", "total_tokens", "cached_input_tokens",
            "reasoning_tokens",
        )
    }
    for field, value in summed.items():
        if row["metrics"].get(field) != value:
            raise ModelBenchmarkError(f"inconsistent {field}")
    repair = sum(attempt["usage"]["output_tokens"] for attempt in row["attempts"][1:])
    if row["metrics"].get("repair_output_tokens") != repair:
        raise ModelBenchmarkError("inconsistent repair_output_tokens")
    if row["repair_rounds"] != len(row["attempts"]) - 1:
        raise ModelBenchmarkError("inconsistent repair rounds")
    if row["accepted"] != row["attempts"][-1]["validation"]["accepted"]:
        raise ModelBenchmarkError("inconsistent accepted flag")
    if (row["failure"] is None) != row["accepted"]:
        raise ModelBenchmarkError("inconsistent failure detail")


def selected_schedule(suite: str, cases: list[tuple[Path, dict]], repetitions: int,
                      representations: list[str] | None, seed: int) -> list[tuple]:
    schedule = []
    matched = set()
    for trial in range(1, repetitions + 1):
        for case_path, case in cases:
            for representation in case["representations"]:
                if representations and representation["id"] not in representations:
                    continue
                matched.add(representation["id"])
                schedule.append((suite, case_path, case, representation, trial))
    if representations and matched != set(representations):
        raise ModelBenchmarkError("one or more selected representations do not exist")
    random.Random(seed).shuffle(schedule)
    return schedule


def write_schedule(client: ModelClient, config: dict, output: Path, run_id: str,
                   schedule: list[tuple], command_timeout: int,
                   preregistration_revision: str | None = None) -> None:
    if output.exists():
        raise ModelBenchmarkError(f"refusing to overwrite raw result: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        for item in schedule:
            suite, case_path, case, representation, trial = item
            row = run_trial(
                client, config, suite, case_path, case, representation, run_id, trial,
                command_timeout, preregistration_revision,
            )
            validate_model_result(row)
            stream.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
            stream.flush()
            state = "accepted" if row["accepted"] else "failed"
            print(f"{suite}/{case['id']}/{representation['id']}/{trial}: {state}", flush=True)


def run(client: ModelClient, config: dict, suite: str, output: Path, run_id: str,
        repetitions: int, selected_cases: list[str] | None,
        selected_representations: list[str] | None, command_timeout: int) -> None:
    cases = STATIC.discover_cases(selected_cases)
    schedule = selected_schedule(
        suite, cases, repetitions, selected_representations, config["schedule_seed"])
    write_schedule(client, config, output, run_id, schedule, command_timeout)


def paired_run(client: ModelClient, config: dict, output: Path, run_id: str,
               repetitions: int, selected_cases: list[str] | None,
               selected_representations: list[str] | None, command_timeout: int,
               pair: str = "development", preregistration_revision: str | None = None) -> None:
    schedules = []
    suites = {
        "development": ("baseline", "optimized"),
        "confirmation": ("confirmation-baseline", "confirmation-optimized"),
    }[pair]
    for suite in suites:
        configure_suite(suite)
        cases = STATIC.discover_cases(selected_cases)
        schedules.extend(selected_schedule(
            suite, cases, repetitions, selected_representations, config["schedule_seed"]))
    random.Random(config["schedule_seed"]).shuffle(schedules)
    write_schedule(
        client, config, output, run_id, schedules, command_timeout,
        preregistration_revision)


def read_rows(path: Path) -> list[dict]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            row = json.loads(line)
            validate_model_result(row)
            rows.append(row)
        except (json.JSONDecodeError, ModelBenchmarkError) as error:
            raise ModelBenchmarkError(f"{path}:{line_number}: {error}") from error
    if not rows:
        raise ModelBenchmarkError("raw model result is empty")
    return rows


def metric(values: list[float]) -> dict:
    return {
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "population_variance": statistics.pvariance(values),
    }


def aggregate_rows(rows: list[dict]) -> dict:
    pins = {
        (
            row["pins"]["provider"], row["pins"]["endpoint"], row["pins"]["model"],
            json.dumps(row["pins"]["model_settings"], sort_keys=True),
            row["pins"]["config_revision"],
            row["pins"].get("preregistration_revision"),
        )
        for row in rows
    }
    if len(pins) != 1:
        raise ModelBenchmarkError("cannot aggregate different model conditions")
    grouped = {}
    for row in rows:
        key = (row["pins"]["suite"], row["category"], row["representation"])
        grouped.setdefault(key, []).append(row)
    groups = []
    for (suite, category, representation), values in sorted(grouped.items()):
        accepted = sum(row["accepted"] for row in values)
        totals = [row["metrics"]["total_tokens"] for row in values]
        groups.append({
            "suite": suite,
            "category": category,
            "representation": representation,
            "language": values[0]["language"],
            "surface": values[0]["surface"],
            "trials": len(values),
            "accepted": accepted,
            "failed": len(values) - accepted,
            "acceptance_rate": accepted / len(values),
            "compile_at_1_rate": sum(row["compile_at_1"] for row in values) / len(values),
            "pass_at_1_rate": sum(row["pass_at_1"] for row in values) / len(values),
            "repair_rounds": metric([row["repair_rounds"] for row in values]),
            "total_tokens": metric(totals),
            "input_tokens": metric([row["metrics"]["input_tokens"] for row in values]),
            "output_tokens": metric([row["metrics"]["output_tokens"] for row in values]),
            "cached_input_tokens": metric([
                row["metrics"]["cached_input_tokens"] for row in values]),
            "reasoning_tokens": metric([row["metrics"]["reasoning_tokens"] for row in values]),
            "total_tokens_per_accepted_solution": sum(totals) / accepted if accepted else None,
            "wall_clock_time": metric([row["wall_clock_time"] for row in values]),
        })
    provider, endpoint, model, settings, config_revision, preregistration_revision = next(iter(pins))
    accepted = sum(row["accepted"] for row in rows)
    total = sum(row["metrics"]["total_tokens"] for row in rows)
    return {
        "schema_version": 1,
        "evidence": "measured",
        "measurement_mode": "model",
        "provider": provider,
        "endpoint": endpoint,
        "model": model,
        "model_settings": json.loads(settings),
        "config_revision": config_revision,
        "preregistration_revision": preregistration_revision,
        "raw_trials": len(rows),
        "accepted": accepted,
        "acceptance_rate": accepted / len(rows),
        "total_tokens": total,
        "total_tokens_per_accepted_solution": total / accepted if accepted else None,
        "groups": groups,
    }


def aggregate(raw: Path, output: Path) -> None:
    document = aggregate_rows(read_rows(raw))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def configure_suite(suite: str) -> None:
    roots = {
        "baseline": ROOT / "benchmarks",
        "optimized": ROOT / "benchmarks/optimized",
        "confirmation-baseline": ROOT / "benchmarks/confirmation/baseline",
        "confirmation-optimized": ROOT / "benchmarks/confirmation/optimized",
    }
    try:
        STATIC.BENCHMARKS = roots[suite]
    except KeyError:
        raise ModelBenchmarkError(f"unknown suite: {suite}")


def suite_revisions(suite: str) -> dict[str, str]:
    configure_suite(suite)
    return {
        case["id"]: STATIC.case_revision(path, case)
        for path, case in STATIC.discover_cases()
    }


def validate_confirmation_preregistration(path: Path, config: dict, repetitions: int) -> str:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ModelBenchmarkError(f"invalid preregistration: {error}") from error
    try:
        valid = (
            document["schema_version"] == 1
            and document["status"] == "frozen-before-run"
            and document["model_condition"]["config_revision"] == sha256(canonical_json(config))
            and document["design"]["repetitions"] == repetitions
            and document["design"]["schedule_seed"] == config["schedule_seed"]
            and document["design"]["paired_trials"] == 60
            and document["design"]["total_trials"] == 120
            and document["pins"]["harness_revision"] == sha256(
                MODEL_HARNESS_BYTES + HARNESS_PATH.read_bytes())
            and document["pins"]["prompt_revision"] == sha256(PROMPT_PATH.read_bytes())
            and document["pins"]["builder_revision"] == sha256(
                (ROOT / "benchmarks/confirmation/build_cases.py").read_bytes())
            and document["pins"]["comparison_revision"] == sha256(
                (ROOT / "benchmarks/model_compare.py").read_bytes())
            and document["pins"]["report_revision"] == sha256(
                (ROOT / "benchmarks/model_report.py").read_bytes())
            and document["pins"]["baseline_case_revisions"]
            == suite_revisions("confirmation-baseline")
            and document["pins"]["optimized_case_revisions"]
            == suite_revisions("confirmation-optimized")
        )
    except (KeyError, TypeError):
        valid = False
    if not valid:
        raise ModelBenchmarkError("preregistration no longer matches the frozen experiment")
    return sha256(path.read_bytes())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate_parser = subparsers.add_parser("validate")
    suite_choices = ("baseline", "optimized", "confirmation-baseline", "confirmation-optimized")
    validate_parser.add_argument("--suite", choices=suite_choices, required=True)
    validate_parser.add_argument("--config", type=Path, required=True)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--suite", choices=suite_choices, required=True)
    run_parser.add_argument("--config", type=Path, required=True)
    run_parser.add_argument("--output", type=Path, required=True)
    run_parser.add_argument("--run-id", required=True)
    run_parser.add_argument("--repetitions", type=int, default=1)
    run_parser.add_argument("--case", action="append")
    run_parser.add_argument("--representation", action="append")
    run_parser.add_argument("--command-timeout", type=int, default=30)
    run_parser.add_argument("--env-file", type=Path)
    paired_parser = subparsers.add_parser("paired-run")
    paired_parser.add_argument("--config", type=Path, required=True)
    paired_parser.add_argument("--output", type=Path, required=True)
    paired_parser.add_argument("--run-id", required=True)
    paired_parser.add_argument("--repetitions", type=int, default=1)
    paired_parser.add_argument("--case", action="append")
    paired_parser.add_argument("--representation", action="append")
    paired_parser.add_argument("--command-timeout", type=int, default=30)
    paired_parser.add_argument("--env-file", type=Path)
    paired_parser.add_argument("--pair", choices=("development", "confirmation"), default="development")
    paired_parser.add_argument("--preregistration", type=Path)
    aggregate_parser = subparsers.add_parser("aggregate")
    aggregate_parser.add_argument("--raw", type=Path, required=True)
    aggregate_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "aggregate":
            aggregate(args.raw, args.output)
            return 0
        config = load_config(args.config)
        if args.command != "paired-run":
            configure_suite(args.suite)
            cases = STATIC.discover_cases(args.case if args.command == "run" else None)
        if args.command == "validate":
            print(json.dumps({
                "valid": True,
                "suite": args.suite,
                "cases": len(cases),
                "model": config["model"],
            }, separators=(",", ":")))
            return 0
        if args.repetitions < 1 or args.command_timeout < 1:
            raise ModelBenchmarkError("repetitions and command timeout must be positive")
        api_key = load_api_key(args.env_file)
        if not api_key:
            raise ModelBenchmarkError("OPENAI_API_KEY is required and is never stored")
        client = OpenAIResponsesClient(config, api_key)
        if args.command == "paired-run":
            preregistration_revision = None
            if args.pair == "confirmation":
                if args.case or args.representation:
                    raise ModelBenchmarkError("confirmation run cannot select a case or representation")
                if args.preregistration is None:
                    raise ModelBenchmarkError("confirmation run requires --preregistration")
                preregistration_revision = validate_confirmation_preregistration(
                    args.preregistration, config, args.repetitions)
            elif args.preregistration is not None:
                raise ModelBenchmarkError("development run does not accept --preregistration")
            paired_run(
                client, config, args.output, args.run_id, args.repetitions,
                args.case, args.representation, args.command_timeout, args.pair,
                preregistration_revision,
            )
        else:
            run(
                client, config, args.suite, args.output, args.run_id, args.repetitions,
                args.case, args.representation, args.command_timeout,
            )
    except (ModelBenchmarkError, STATIC.BenchmarkError, OSError) as error:
        print(f"model benchmark error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
