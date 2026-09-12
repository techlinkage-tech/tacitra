#!/usr/bin/env python3
"""Semantic protocol v2 pilot and confirmatory real-model evaluation."""

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
BASE = ROOT / "benchmarks/semantic-protocol-v2"
CONFIG = BASE / "config-v1.json"
PERSISTENT = BASE / "persistent-instructions-v1.md"
PROMPT = BASE / "prompt-v1.md"
PILOT_PREREG = BASE / "pilot-preregistration-v3.json"
CONFIRMATION_PREREG = BASE / "confirmation-preregistration-v1.json"
PILOT_RAW = ROOT / "benchmarks/results/semantic-protocol-v2-pilot/raw.jsonl"
CONFIRMATION_RAW = ROOT / "benchmarks/results/semantic-protocol-v2/raw.jsonl"
REPRESENTATIONS = (
    "ordinary",
    "capsule-diff",
    "capsule-fragment",
    "capsule-named",
    "compact-control",
)
TOKEN_BUDGET = 750_000


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


MODEL = load("semantic_v2_model", ROOT / "benchmarks/model_harness.py")
RUNTIME = load("semantic_v2_runtime", ROOT / "benchmarks/runtime_environment.py")
MODEL.STATIC.BENCHMARKS = BASE


def sha(path: Path) -> str:
    return MODEL.sha256(path.read_bytes())


def config() -> dict:
    value = json.loads(CONFIG.read_text(encoding="utf-8"))
    if (
        value.get("model") != "gpt-5.6-luna"
        or value.get("settings", {}).get("reasoning", {}).get("effort") != "low"
        or value.get("settings", {}).get("max_output_tokens") != 2048
        or value.get("pilot_repetitions") != 2
    ):
        raise MODEL.ModelBenchmarkError("semantic protocol v2 model condition changed")
    return value


def cases(phase: str) -> list[tuple[Path, dict]]:
    found = []
    for path in sorted((BASE / "cases").glob("*/case.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("phase") == phase:
            found.append((path, value))
    expected = 12 if phase == "pilot" else 60
    if len(found) != expected:
        raise MODEL.ModelBenchmarkError(f"expected {expected} {phase} cases, found {len(found)}")
    return found


def schedule(phase: str, selected: str | None = None) -> list[tuple[Path, dict, dict, int]]:
    cfg = config()
    repetitions = cfg["pilot_repetitions"] if phase == "pilot" else 1
    names = REPRESENTATIONS if phase == "pilot" else ("ordinary", selected)
    if names[-1] is None:
        raise MODEL.ModelBenchmarkError("confirmation candidate is not selected")
    rows = []
    for repetition in range(1, repetitions + 1):
        for path, case in cases(phase):
            by_name = {item["id"]: item for item in case["representations"]}
            rows.extend((path, case, by_name[name], repetition) for name in names)
    seed = cfg["pilot_seed"] if phase == "pilot" else cfg["confirmation_seed"]
    random.Random(seed).shuffle(rows)
    return rows


def schedule_document(phase: str, selected: str | None = None) -> list[dict]:
    return [
        {"case_id": case["id"], "representation": rep["id"], "repetition": repetition}
        for _, case, rep, repetition in schedule(phase, selected)
    ]


def common_pins(phase: str) -> dict:
    paths = {
        "builder_revision": BASE / "build_cases.py",
        "definitions_revision": BASE / "definitions-v1.json",
        "config_revision": CONFIG,
        "persistent_instructions_revision": PERSISTENT,
        "prompt_revision": PROMPT,
        "task_profile_revision": BASE / "task-profile-v1.md",
        "budget_revision": BASE / "budget-v1.json",
        "diff_contract_revision": BASE / "output-diff-v1.md",
        "fragment_contract_revision": BASE / "output-fragment-v1.md",
        "named_contract_revision": BASE / "output-named-v1.md",
        "compact_contract_revision": BASE / "output-compact-v1.md",
        "harness_revision": Path(__file__),
        "runtime_revision": ROOT / "benchmarks/runtime_environment.py",
        "comparison_revision": ROOT / "benchmarks/semantic_protocol_v2_compare.py",
        "report_revision": ROOT / "benchmarks/semantic_protocol_v2_report.py",
        "ai_library_revision": ROOT / "crates/tacitra-agent/src/ai.rs",
        "candidate_library_revision": ROOT / "crates/tacitra-agent/src/candidate.rs",
        "cli_revision": ROOT / "crates/tacitra-cli/src/main.rs",
        "named_schema_revision": ROOT / "protocol/schema/named-edit-v1.schema.json",
        "tests_revision": ROOT / "benchmarks/tests/test_semantic_protocol_v2.py",
    }
    return {
        **{name: sha(path) for name, path in paths.items()},
        "case_revisions": {
            case["id"]: MODEL.STATIC.case_revision(path, case)
            for path, case in cases(phase)
        },
    }


def prereg_document(phase: str, selected: str | None = None) -> dict:
    cfg = config()
    trials = 120
    pins = common_pins(phase)
    pins["schedule_revision"] = MODEL.sha256(MODEL.canonical_json(schedule_document(phase, selected)))
    return {
        "schema_version": 1,
        "id": f"semantic-protocol-v2-{phase}",
        "status": "frozen-before-run",
        "phase": phase,
        "model_condition": {
            "provider": cfg["provider"],
            "model": cfg["model"],
            "settings": cfg["settings"],
            "substitution_allowed": False,
        },
        "design": {
            "cases": 12 if phase == "pilot" else 60,
            "categories": {"repository-change": 6 if phase == "pilot" else 30, "debug-repair": 6 if phase == "pilot" else 30},
            "repetitions": 2 if phase == "pilot" else 1,
            "conditions": list(REPRESENTATIONS) if phase == "pilot" else ["ordinary", selected],
            "total_trials": trials,
            "max_repairs": 2,
            "maximum_api_calls": 360,
            "token_budget_all_phases": TOKEN_BUDGET,
            "stateless": True,
        },
        "selection_rule" if phase == "pilot" else "decision_rule": (
            {
                "max_observed_candidate_loss_on_baseline_accepted": 0.05,
                "requires_acceptance_in_both_categories": True,
                "rank": ["total_provider_tokens_per_accepted_solution", "reasoning_tokens"],
                "stop_if_all_worse_than_baseline": True,
            }
            if phase == "pilot"
            else {
                "difference": f"{selected} minus ordinary",
                "classification": "supports_semantic_protocol_v2",
                "max_one_sided_95_loss_upper": 0.05,
                "paired_bootstrap_95_upper_below": 0,
                "minimum_observed_token_reduction": 0.05,
                "requires_both_categories": True,
                "environment_or_provider_failure": "not_estimable_environment_failure",
                "otherwise": ["inconclusive", "does_not_support_semantic_protocol_v2"],
            }
        ),
        "selected_candidate": selected,
        "pins": pins,
    }


def freeze(phase: str, selected: str | None = None) -> str:
    path = PILOT_PREREG if phase == "pilot" else CONFIRMATION_PREREG
    if path.exists():
        raise MODEL.ModelBenchmarkError(f"refusing to overwrite {path.name}")
    document = prereg_document(phase, selected)
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return sha(path)


def validate_prereg(phase: str) -> tuple[dict, str]:
    path = PILOT_PREREG if phase == "pilot" else CONFIRMATION_PREREG
    document = json.loads(path.read_text(encoding="utf-8"))
    selected = document.get("selected_candidate")
    if document != prereg_document(phase, selected):
        raise MODEL.ModelBenchmarkError(f"{phase} preregistration no longer matches inputs")
    return document, sha(path)


def prompt_for(path: Path, case: dict, rep: dict) -> tuple[str, dict]:
    if rep["id"] == "ordinary":
        return MODEL.base_prompt(path, case, {**rep, "artifact_kind": "patch"})
    directory = path.parent
    profile, profile_bytes, profile_hashes = MODEL.read_labeled(directory, rep["specification"])
    packet, packet_bytes, packet_hashes = MODEL.read_labeled(directory, rep["repository_context"])
    diagnostic, diagnostic_bytes, diagnostic_hashes = MODEL.read_labeled(directory, rep["diagnostic_context"])
    contract = MODEL.STATIC.relative_file(directory, rep["specification"][-1]).read_text(encoding="utf-8")
    shared_profile = MODEL.STATIC.relative_file(directory, rep["specification"][0]).read_text(encoding="utf-8")
    template = PROMPT.read_text(encoding="utf-8")
    text = template.format(
        output_contract=contract.strip(),
        task_profile=shared_profile.strip(),
        task_packet=packet,
        diagnostic=diagnostic or "(none)",
    )
    return text, {
        "instruction_bytes": PERSISTENT.stat().st_size,
        "prompt_template_bytes": len(template.encode()),
        "specification_bytes": profile_bytes,
        "repository_context_bytes": packet_bytes,
        "task_bytes": 0,
        "initial_diagnostic_bytes": diagnostic_bytes,
        "repair_context_bytes": 0,
        "hashes": {
            "prompt_template": MODEL.sha256(template.encode()),
            "task": "embedded-in-capsule",
            "specification": profile_hashes,
            "repository_context": packet_hashes,
            "initial_diagnostic": diagnostic_hashes,
        },
    }


def prepare_commands(rep: dict, artifact: Path, work: Path, runtime) -> tuple[bool, object]:
    program = work / "program.taci"
    kind = rep["artifact_kind"]
    if kind == "unified_diff":
        commands = [["patch", "--silent", str(program), str(artifact)]]
    elif kind == "source_fragment":
        commands = [[runtime.executable("tacitra"), "ai.fragment.apply", str(program), rep["target"], rep["base_hash"], str(artifact)]]
    elif kind == "named_edit":
        commands = [[runtime.executable("tacitra"), "ai.edit.named.apply", str(program), str(artifact)]]
    else:
        commands = [[runtime.executable("tacitra"), "ai.edit.apply", str(program), str(artifact)]]
    return RUNTIME.execute_commands(commands, artifact.parent, artifact, work, 30, runtime)


def validate_artifact(runtime, path: Path, case: dict, rep: dict, artifact_text: str, timeout: int) -> dict:
    with tempfile.TemporaryDirectory(prefix="tacitra-spv2-") as directory:
        work = Path(directory)
        program = work / "program.taci"
        program.write_text((path.parent / "base.tacitra.taci").read_text(encoding="utf-8"), encoding="utf-8")
        artifact = work / "candidate.out"
        artifact.write_text(artifact_text, encoding="utf-8")
        prepare_ok, result = prepare_commands(rep, artifact, work, runtime)
        compile_ok = tests_ok = False
        phase = "prepare"
        if prepare_ok:
            phase = "compile"
            compile_ok, result = RUNTIME.execute_commands(rep["compile_commands"], path.parent, artifact, work, timeout, runtime)
        if prepare_ok and compile_ok:
            phase = "test"
            tests_ok, result = RUNTIME.execute_commands(rep["test_commands"], path.parent, artifact, work, timeout, runtime)
            if tests_ok:
                try:
                    tests_ok = MODEL.STATIC.normalized_result(result.stdout, "integer") == case["acceptance"]["expected_integer"]
                except (ValueError, TypeError):
                    tests_ok = False
        accepted = prepare_ok and compile_ok and tests_ok
        failure = None
        if not accepted:
            classification = result.classification if result and result.classification else f"{phase}_failure"
            failure = {
                "phase": phase,
                "classification": classification,
                "exit_code": None if result is None else result.returncode,
                "stdout": "" if result is None else result.stdout[-4096:],
                "stderr": "" if result is None else result.stderr[-4096:],
            }
        return {"compile_ok": compile_ok, "tests_ok": tests_ok, "accepted": accepted, "failure": failure}


def repair_prompt(path: Path, case: dict, rep: dict, artifact: str | None, failure: dict) -> str:
    packet = json.loads((path.parent / "task-packet.json").read_text(encoding="utf-8"))
    repair = {}
    try:
        parsed = json.loads(failure.get("stdout") or "{}")
        repair = parsed.get("repair") or parsed.get("error") or {}
    except json.JSONDecodeError:
        pass
    document = {
        "error_code": repair.get("code", failure.get("classification", "validation_failure")),
        "failed_operation": repair.get("op", failure.get("phase")),
        "target": packet["capsule"]["target"]["id"],
        "expected_type": repair.get("expected", packet["capsule"]["target"]["return"]),
        "actual_type": repair.get("actual"),
        "content_hash": packet["capsule"]["hash"],
        "editable_fragment": packet["editable"]["source"],
        "previous_artifact": artifact,
        "output_format": rep["artifact_kind"],
    }
    return "REPAIR REQUIRED\n" + json.dumps(document, sort_keys=True, separators=(",", ":")) + '\nReturn only {"artifact":"..."}.'


@dataclass
class FakeClient:
    answers: list[str]
    provider: str = "fake-spv2"
    model: str = "fake-reference-v1"
    endpoint: str = "local://fake"
    settings: dict | None = None
    calls: int = 0

    def generate(self, instructions: str, input_text: str):
        self.calls += 1
        text = self.answers.pop(0)
        i = len((instructions + input_text).encode())
        o = len(text.encode())
        return MODEL.ModelReply(text, None, i, o, i + o, 0, 0)


def run_trial(runtime, client, cfg: dict, phase: str, path: Path, case: dict, rep: dict, repetition: int, revision: str) -> dict:
    started = time.monotonic()
    instructions = PERSISTENT.read_text(encoding="utf-8")
    initial, components = prompt_for(path, case, rep)
    attempts = []
    next_prompt = initial
    artifact = None
    for attempt_number in range(1, case["max_repair_rounds"] + 2):
        prompt = next_prompt
        request = {"model": client.model, "instructions": instructions, "input": prompt, "settings": client.settings}
        attempt_started = time.monotonic()
        reply = client.generate(instructions, prompt)
        try:
            artifact = MODEL.extract_artifact(reply.text, cfg["max_output_characters"])
            validation = validate_artifact(runtime, path, case, rep, artifact, 30)
        except MODEL.ModelBenchmarkError as error:
            validation = {"compile_ok": False, "tests_ok": False, "accepted": False, "failure": {"phase": "model_output", "classification": "model_generation_failure", "exit_code": None, "stdout": "", "stderr": str(error)}}
        attempt_components = dict(components)
        attempt_components["repair_context_bytes"] = 0 if attempt_number == 1 else len(prompt.encode())
        attempts.append({
            "attempt": attempt_number,
            "request_hash": MODEL.sha256(MODEL.canonical_json(request)),
            "input_text": prompt,
            "context_bytes": attempt_components,
            "response_id": reply.response_id,
            "response_text": reply.text,
            "response_hash": MODEL.sha256(reply.text.encode()),
            "artifact": artifact,
            "usage": {"input_tokens": reply.input_tokens, "output_tokens": reply.output_tokens, "total_tokens": reply.total_tokens, "cached_input_tokens": reply.cached_input_tokens, "reasoning_tokens": reply.reasoning_tokens},
            "validation": validation,
            "wall_clock_time": round(time.monotonic() - attempt_started, 6),
        })
        if validation["accepted"]:
            break
        next_prompt = MODEL.repair_context(artifact, validation["failure"]) if rep["id"] == "ordinary" else repair_prompt(path, case, rep, artifact, validation["failure"])
    totals = {name: sum(item["usage"][name] for item in attempts) for name in ("input_tokens", "output_tokens", "total_tokens", "cached_input_tokens", "reasoning_tokens")}
    totals["repair_output_tokens"] = sum(item["usage"]["output_tokens"] for item in attempts[1:])
    accepted = attempts[-1]["validation"]["accepted"]
    row = {
        "schema_version": 3,
        "evidence": "measured",
        "measurement_mode": "model",
        "run_id": f"semantic-protocol-v2-{phase}",
        "trial_id": f"semantic-protocol-v2-{phase}:{case['id']}:{rep['id']}:{repetition:03d}",
        "case_id": case["id"],
        "category": case["category"],
        "representation": rep["id"],
        "language": "tacitra",
        "surface": rep["surface"],
        "pins": {"suite": f"semantic-protocol-v2-{phase}", "case_revision": MODEL.STATIC.case_revision(path, case), "harness_revision": sha(Path(__file__)), "config_revision": MODEL.sha256(MODEL.canonical_json(cfg)), "preregistration_revision": revision, "provider": client.provider, "endpoint": client.endpoint, "model": client.model, "model_settings": client.settings, "usage_source": "provider_response", "environment": runtime.public_record()},
        "persistent_instructions": {"text": instructions, "hash": MODEL.sha256(instructions.encode())},
        "attempts": attempts,
        "metrics": totals,
        "compile_at_1": attempts[0]["validation"]["compile_ok"],
        "pass_at_1": attempts[0]["validation"]["tests_ok"],
        "repair_rounds": len(attempts) - 1,
        "max_repair_rounds": case["max_repair_rounds"],
        "patch_size": None if artifact is None else len(artifact.encode()),
        "accepted": accepted,
        "wall_clock_time": round(time.monotonic() - started, 6),
        "failure": None if accepted else attempts[-1]["validation"]["failure"],
    }
    MODEL.validate_model_result(row)
    return row


def preflight(phase: str, output: Path, resume: bool = False) -> tuple[object, dict, str, list]:
    document, revision = validate_prereg(phase)
    selected = document.get("selected_candidate")
    planned = schedule(phase, selected)
    if len(planned) != 120 or len(planned) * 3 > 360:
        raise RUNTIME.EnvironmentFailure("environment_preflight_failure", None, "trial or API-call limit mismatch")
    events = output.with_suffix(output.suffix + ".events.jsonl")
    unused = () if resume else (output, events)
    runtime = RUNTIME.preflight(
        root=ROOT,
        required_files=(CONFIG, PERSISTENT, PROMPT, PILOT_PREREG if phase == "pilot" else CONFIRMATION_PREREG, ROOT / "Cargo.lock"),
        unused_outputs=unused,
    )
    accepted = 0
    for path, case in cases(phase):
        for rep in case["representations"]:
            reference = (path.parent / rep["artifact"]).read_text(encoding="utf-8")
            outcome = validate_artifact(runtime, path, case, rep, reference, 30)
            if not outcome["accepted"]:
                raise RUNTIME.EnvironmentFailure("fixture_prevalidation_failure", None, f"reference failed: {case['id']}/{rep['id']}")
            accepted += 1
    fake_schedule = planned[: min(5, len(planned))]
    fake = FakeClient([json.dumps({"artifact": (path.parent / rep["artifact"]).read_text(encoding="utf-8")}) for path, _, rep, _ in fake_schedule])
    for path, case, rep, repetition in fake_schedule:
        row = run_trial(runtime, fake, config(), phase, path, case, rep, repetition, revision)
        if not row["accepted"]:
            raise RUNTIME.EnvironmentFailure("environment_preflight_failure", None, "fake-provider smoke test failed")
    return runtime, document, revision, planned


def existing_trials(output: Path) -> set[str]:
    if not output.exists():
        return set()
    return {row["trial_id"] for row in MODEL.read_rows(output)}


def run_phase(phase: str, env_file: Path | None, output: Path, resume: bool) -> None:
    runtime, document, revision, planned = preflight(phase, output, resume)
    completed = existing_trials(output) if resume else set()
    remaining = [item for item in planned if f"semantic-protocol-v2-{phase}:{item[1]['id']}:{item[2]['id']}:{item[3]:03d}" not in completed]
    key = MODEL.load_api_key(env_file)
    if not key:
        raise RUNTIME.EnvironmentFailure("environment_preflight_failure", None, "OPENAI_API_KEY is required")
    client = MODEL.OpenAIResponsesClient(config(), key)
    output.parent.mkdir(parents=True, exist_ok=True)
    events = output.with_suffix(output.suffix + ".events.jsonl")
    total = sum(row["metrics"]["total_tokens"] for row in MODEL.read_rows(output)) if output.exists() else 0
    if phase == "confirmation" and PILOT_RAW.exists():
        total += sum(row["metrics"]["total_tokens"] for row in MODEL.read_rows(PILOT_RAW))
    mode = "a" if resume else "x"
    with output.open(mode, encoding="utf-8") as stream, events.open(mode, encoding="utf-8") as journal:
        journal.write(json.dumps({"event": "run_resumed" if resume else "run_started", "phase": phase, "remaining": len(remaining), "maximum_api_calls": len(remaining) * 3}, sort_keys=True) + "\n")
        journal.flush()
        for path, case, rep, repetition in remaining:
            if total >= TOKEN_BUDGET:
                journal.write(json.dumps({"event": "budget_stopped", "retained_total_tokens": total}, sort_keys=True) + "\n")
                journal.flush()
                raise MODEL.ModelBenchmarkError("750000 provider-token budget reached")
            identity = {"case_id": case["id"], "representation": rep["id"], "repetition": repetition}
            journal.write(json.dumps({"event": "trial_started", **identity}, sort_keys=True) + "\n")
            journal.flush()
            try:
                row = run_trial(runtime, client, config(), phase, path, case, rep, repetition, revision)
            except BaseException as error:
                journal.write(json.dumps({"event": "trial_interrupted", **identity, "classification": "provider_failure", "error_type": type(error).__name__}, sort_keys=True) + "\n")
                journal.flush()
                raise
            stream.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
            stream.flush()
            total += row["metrics"]["total_tokens"]
            journal.write(json.dumps({"event": "trial_completed", **identity, "accepted": row["accepted"], "attempts": len(row["attempts"]), "retained_total_tokens": total}, sort_keys=True) + "\n")
            journal.flush()
            if total >= TOKEN_BUDGET:
                journal.write(json.dumps({"event": "budget_stopped", **identity, "retained_total_tokens": total}, sort_keys=True) + "\n")
                journal.flush()
                raise MODEL.ModelBenchmarkError("750000 provider-token budget reached after retaining completed trial")


def summarize(rows: list[dict]) -> dict:
    accepted = sum(row["accepted"] for row in rows)
    total = sum(row["metrics"]["total_tokens"] for row in rows)
    return {
        "trials": len(rows),
        "accepted": accepted,
        "acceptance_rate": accepted / len(rows) if rows else None,
        "compile_at_1": sum(row["compile_at_1"] for row in rows) / len(rows) if rows else None,
        "pass_at_1": sum(row["pass_at_1"] for row in rows) / len(rows) if rows else None,
        "total_tokens": total,
        "total_tokens_per_accepted_solution": total / accepted if accepted else None,
        "input_tokens": sum(row["metrics"]["input_tokens"] for row in rows),
        "output_tokens": sum(row["metrics"]["output_tokens"] for row in rows),
        "reasoning_tokens": sum(row["metrics"]["reasoning_tokens"] for row in rows),
        "cached_input_tokens": sum(row["metrics"]["cached_input_tokens"] for row in rows),
        "repair_output_tokens": sum(row["metrics"]["repair_output_tokens"] for row in rows),
        "repair_rounds": sum(row["repair_rounds"] for row in rows),
        "patch_size": MODEL.metric([row["patch_size"] for row in rows]),
        "wall_clock_time": sum(row["wall_clock_time"] for row in rows),
    }


def aggregate(raw: Path, output: Path) -> None:
    rows = MODEL.read_rows(raw)
    document = {
        "schema_version": 1,
        "evidence": "measured",
        "trials": len(rows),
        "representations": [{"representation": name, **summarize([row for row in rows if row["representation"] == name])} for name in sorted({row["representation"] for row in rows})],
        "categories": [{"category": category, "representation": name, **summarize([row for row in rows if row["category"] == category and row["representation"] == name])} for category in sorted({row["category"] for row in rows}) for name in sorted({row["representation"] for row in rows})],
    }
    output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    freeze_pilot = sub.add_parser("freeze-pilot")
    freeze_confirmation = sub.add_parser("freeze-confirmation")
    freeze_confirmation.add_argument("--candidate", choices=REPRESENTATIONS[1:-1], required=True)
    for name in ("preflight-pilot", "preflight-confirmation", "run-pilot", "run-confirmation"):
        item = sub.add_parser(name)
        item.add_argument("--env-file", type=Path)
        item.add_argument("--resume", action="store_true")
    dry = sub.add_parser("dry-run")
    dry.add_argument("--phase", choices=("pilot", "confirmation"), required=True)
    aggregate_parser = sub.add_parser("aggregate")
    aggregate_parser.add_argument("--raw", type=Path, required=True)
    aggregate_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "freeze-pilot":
            print(json.dumps({"preregistration_revision": freeze("pilot")})); return 0
        if args.command == "freeze-confirmation":
            print(json.dumps({"preregistration_revision": freeze("confirmation", args.candidate), "selected_candidate": args.candidate})); return 0
        if args.command == "aggregate":
            aggregate(args.raw, args.output); return 0
        if args.command == "dry-run":
            runtime, document, revision, planned = preflight(args.phase, Path(tempfile.gettempdir()) / f"spv2-{args.phase}-unused.jsonl")
            print(json.dumps({"valid": True, "phase": args.phase, "trials": len(planned), "reference_fixtures": (12 if args.phase == "pilot" else 60) * 5, "fake_provider_calls": 5, "real_provider_calls": 0, "preregistration_revision": revision, "environment": runtime.public_record()}, sort_keys=True)); return 0
        phase = "pilot" if args.command.endswith("pilot") else "confirmation"
        output = PILOT_RAW if phase == "pilot" else CONFIRMATION_RAW
        if args.command.startswith("preflight"):
            runtime, _, revision, planned = preflight(phase, output, args.resume)
            print(json.dumps({"valid": True, "phase": phase, "trials": len(planned), "maximum_api_calls": len(planned) * 3, "real_provider_calls": 0, "preregistration_revision": revision, "environment": runtime.public_record()}, indent=2, sort_keys=True)); return 0
        run_phase(phase, args.env_file, output, args.resume)
    except (MODEL.ModelBenchmarkError, RUNTIME.EnvironmentFailure, OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        classification = error.classification if isinstance(error, RUNTIME.EnvironmentFailure) else "environment_preflight_failure" if args.command.startswith(("preflight", "dry-run")) else "provider_failure"
        print(json.dumps({"classification": classification, "error_type": type(error).__name__}, sort_keys=True), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
