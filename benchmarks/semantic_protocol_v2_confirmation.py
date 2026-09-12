#!/usr/bin/env python3
"""Preregister, preflight, run, and retain semantic-protocol-v2 confirmation."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "benchmarks/semantic-protocol-v2"
MANIFEST = BASE / "confirmation-case-manifest-v1.json"
PREREG = BASE / "confirmation-preregistration-v2.json"
RESULTS = ROOT / "benchmarks/results/semantic-protocol-v2"
RAW = RESULTS / "raw.jsonl"
EVENTS = RESULTS / "raw.jsonl.events.jsonl"
PREFLIGHT = RESULTS / "preflight.json"
PHASE_TOKEN_LIMIT = 542_715
TOTAL_TOKEN_LIMIT = 750_000
PILOT_TOKENS = 207_285
SELECTED = "capsule-fragment"
BOOTSTRAP_SEED = 20260917


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


H = load("semantic_v2_confirmation_harness", ROOT / "benchmarks/semantic_protocol_v2.py")
COMPARE = load("semantic_v2_confirmation_compare", ROOT / "benchmarks/semantic_protocol_v2_compare.py")
REPORTER = load("semantic_v2_confirmation_report", ROOT / "benchmarks/semantic_protocol_v2_report.py")
MODEL = H.MODEL
RUNTIME = H.RUNTIME


def digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def file_digest(path: Path) -> str:
    return digest(path.read_bytes())


def canonical_digest(value: object) -> str:
    return digest(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def relative_file(case_dir: Path, name: str) -> Path:
    return MODEL.STATIC.relative_file(case_dir, name)


def component_record(path: Path, case: dict) -> dict:
    directory = path.parent
    by_name = {item["id"]: item for item in case["representations"]}
    ordinary = by_name["ordinary"]
    fragment = by_name[SELECTED]
    for field in ("base_hash", "compile_commands", "test_commands", "setup_files"):
        if ordinary.get(field) != fragment.get(field):
            raise MODEL.ModelBenchmarkError(f"paired conditions differ in {field}: {case['id']}")
    if case.get("max_repair_rounds") != 2:
        raise MODEL.ModelBenchmarkError(f"repair limit differs from preregistration: {case['id']}")
    components = {
        "task": file_digest(relative_file(directory, case["prompt"])),
        "initial_source": file_digest(directory / "base.tacitra.taci"),
        "ordinary_reference": file_digest(relative_file(directory, ordinary["artifact"])),
        "fragment_reference": file_digest(relative_file(directory, fragment["artifact"])),
        "acceptance": canonical_digest({
            "compile": ordinary["compile_commands"],
            "test": ordinary["test_commands"],
            "expected": case["acceptance"],
        }),
    }
    return {
        "case_id": case["id"],
        "category": case["category"],
        "case_revision": MODEL.STATIC.case_revision(path, case),
        "components": components,
        "composite_revision": canonical_digest(components),
    }


def existing_case_records() -> list[dict]:
    records = []
    confirmation_ids = {case["id"] for _, case in H.cases("confirmation")}
    for path in sorted((ROOT / "benchmarks").rglob("case.json")):
        try:
            case = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if case.get("id") in confirmation_ids:
            continue
        task_hash = None
        if isinstance(case.get("prompt"), str):
            try:
                task_hash = file_digest(relative_file(path.parent, case["prompt"]))
            except (OSError, ValueError):
                pass
        initial_hashes = []
        artifact_hashes = []
        acceptance_hashes = []
        composite_revisions = []
        for rep in case.get("representations", []):
            rep_initial_hashes = []
            for setup in rep.get("setup_files", []):
                try:
                    value = file_digest(relative_file(path.parent, setup["source"]))
                    initial_hashes.append(value)
                    rep_initial_hashes.append(value)
                except (OSError, ValueError, KeyError):
                    pass
            artifact_hash = None
            try:
                artifact_hash = file_digest(relative_file(path.parent, rep["artifact"]))
                artifact_hashes.append(artifact_hash)
            except (OSError, ValueError, KeyError):
                pass
            acceptance_hash = canonical_digest({
                "compile": rep.get("compile_commands"),
                "test": rep.get("test_commands"),
                "expected": case.get("acceptance"),
            })
            acceptance_hashes.append(acceptance_hash)
            if task_hash and artifact_hash:
                for initial_hash in rep_initial_hashes or [None]:
                    composite_revisions.append(canonical_digest({
                        "task": task_hash,
                        "initial_source": initial_hash,
                        "reference": artifact_hash,
                        "acceptance": acceptance_hash,
                    }))
        records.append({
            "case_id": case.get("id"),
            "task": task_hash,
            "initial_sources": sorted(set(initial_hashes)),
            "artifacts": sorted(set(artifact_hashes)),
            "acceptance": sorted(set(acceptance_hashes)),
            "composite_revisions": sorted(set(composite_revisions)),
        })
    return records


def build_manifest() -> dict:
    confirmation = [component_record(path, case) for path, case in H.cases("confirmation")]
    prior = existing_case_records()
    task_hashes = {item["task"] for item in prior if item["task"]}
    source_hashes = {value for item in prior for value in item["initial_sources"]}
    artifact_hashes = {value for item in prior for value in item["artifacts"]}
    full_revisions = {value for item in prior for value in item["composite_revisions"]}
    duplicate_components = {
        name: sorted({value for value in values if values.count(value) > 1})
        for name, values in {
            "case_ids": [item["case_id"] for item in confirmation],
            "task_hashes": [item["components"]["task"] for item in confirmation],
            "initial_source_hashes": [item["components"]["initial_source"] for item in confirmation],
            "ordinary_reference_hashes": [item["components"]["ordinary_reference"] for item in confirmation],
            "fragment_reference_hashes": [item["components"]["fragment_reference"] for item in confirmation],
            "composite_revisions": [item["composite_revision"] for item in confirmation],
        }.items()
    }
    # A short function body may intentionally be the correct edit for several
    # distinct tasks. Independence is established by unique task, initial-state,
    # and whole-case revisions rather than by fragment text alone.
    if any(duplicate_components[name] for name in (
        "case_ids", "task_hashes", "initial_source_hashes", "composite_revisions"
    )):
        raise MODEL.ModelBenchmarkError("confirmation cases are not mutually independent by content hash")
    overlaps = {
        "case_ids": sorted({item["case_id"] for item in confirmation} & {item["case_id"] for item in prior}),
        "task_hashes": sorted({item["components"]["task"] for item in confirmation} & task_hashes),
        "initial_source_hashes": sorted({item["components"]["initial_source"] for item in confirmation} & source_hashes),
        "reference_hashes": sorted(
            ({item["components"]["ordinary_reference"] for item in confirmation}
             | {item["components"]["fragment_reference"] for item in confirmation})
            & artifact_hashes
        ),
        "acceptance_hashes": sorted(
            {item["components"]["acceptance"] for item in confirmation}
            & {value for item in prior for value in item["acceptance"]}
        ),
        "composite_revisions": sorted({item["composite_revision"] for item in confirmation} & full_revisions),
        "interpretation": "component matches are retained for audit; a case is previously used only when its ID, task, initial state, or full composite revision matches",
        "acceptance_command_note": "command templates are intentionally shared; expected values participate in each acceptance hash and composite revision",
    }
    if any(overlaps[name] for name in ("case_ids", "task_hashes", "initial_source_hashes", "composite_revisions")):
        raise MODEL.ModelBenchmarkError("confirmation cases overlap prior real-model cases")
    return {
        "schema_version": 1,
        "experiment": "semantic-protocol-v2-confirmation",
        "cases": confirmation,
        "counts": {"total": 60, "repository-change": 30, "debug-repair": 30},
        "prior_case_records_checked": len(prior),
        "within_confirmation_duplicates": duplicate_components,
        "overlaps": overlaps,
    }


def pins() -> dict:
    paths = {
        "case_manifest_revision": MANIFEST,
        "pilot_preregistration_revision": BASE / "pilot-preregistration-v3.json",
        "pilot_comparison_revision": ROOT / "benchmarks/results/semantic-protocol-v2-pilot/comparison.json",
        "pilot_evidence_manifest_revision": ROOT / "benchmarks/results/semantic-protocol-v2-pilot/evidence.sha256",
        "runner_revision": Path(__file__),
        "pilot_harness_revision": ROOT / "benchmarks/semantic_protocol_v2.py",
        "comparator_revision": ROOT / "benchmarks/semantic_protocol_v2_compare.py",
        "report_generator_revision": ROOT / "benchmarks/semantic_protocol_v2_report.py",
        "provider_adapter_revision": ROOT / "benchmarks/model_harness.py",
        "subprocess_runtime_revision": ROOT / "benchmarks/runtime_environment.py",
        "prompt_revision": BASE / "prompt-v1.md",
        "provider_instructions_revision": BASE / "persistent-instructions-v1.md",
        "task_profile_revision": BASE / "task-profile-v1.md",
        "fragment_contract_revision": BASE / "output-fragment-v1.md",
        "budget_revision": BASE / "confirmation-budget-v1.json",
        "capsule_generation_revision": ROOT / "crates/tacitra-agent/src/ai.rs",
        "fragment_binding_revision": ROOT / "crates/tacitra-agent/src/candidate.rs",
        "cli_revision": ROOT / "crates/tacitra-cli/src/main.rs",
        "confirmation_tests_revision": ROOT / "benchmarks/tests/test_semantic_protocol_v2_confirmation.py",
    }
    result = {name: file_digest(path) for name, path in paths.items()}
    result["schedule_revision"] = canonical_digest(H.schedule_document("confirmation", SELECTED))
    return result


def preregistration() -> dict:
    cfg = H.config()
    pilot = json.loads((ROOT / "benchmarks/results/semantic-protocol-v2-pilot/comparison.json").read_text(encoding="utf-8"))
    if pilot.get("selected_candidate") != SELECTED or pilot.get("best_eligible_candidate") != SELECTED or not pilot.get("proceed_to_confirmation"):
        raise MODEL.ModelBenchmarkError("pilot selection evidence does not select capsule-fragment")
    return {
        "schema_version": 1,
        "id": "semantic-protocol-v2-confirmation",
        "status": "frozen-before-run",
        "selected_by_pilot": SELECTED,
        "selected_candidate": SELECTED,
        "pilot_preregistration_revision": "sha256:a888e06939a625fcd047fe649fbf7f0a79a4e7df27d3c51329d80b2965c55d85",
        "pilot_evidence_revision": file_digest(ROOT / "benchmarks/results/semantic-protocol-v2-pilot/evidence.sha256"),
        "design": {
            "independent_cases": 60,
            "categories": {"repository-change": 30, "debug-repair": 30},
            "conditions": ["ordinary", SELECTED],
            "trials": 120,
            "maximum_repairs_per_trial": 2,
            "maximum_api_calls": 360,
            "timeout_seconds": 30,
            "schedule_seed": cfg["confirmation_seed"],
            "bootstrap_seed": BOOTSTRAP_SEED,
            "stateless": True,
        },
        "model_condition": {"provider": cfg["provider"], "model": cfg["model"], "settings": cfg["settings"], "substitution_allowed": False},
        "prompt_roles": {
            "system": None,
            "developer": None,
            "provider_instructions": "persistent-instructions-v1.md",
            "user_template": "prompt-v1.md for capsule-fragment; frozen model-prompt-v1.md for ordinary",
        },
        "processing": {
            "capsule": "task_context_capsule plus frozen task-packet.json",
            "fragment": "function_body_edit then checked ai.fragment.apply",
            "ordinary": "GNU patch unified diff then identical Tacitra check/run",
            "repair": "ordinary retains its frozen repair context; fragment receives only the frozen minimal repair document and not the initial prompt",
            "token_formula": "sum provider total_tokens over successful and failed initial/repair attempts divided by accepted trials",
            "cached_tokens": "recorded subset; never subtracted",
            "provider_retry": "none; provider failure aborts and is retained as an event",
            "confidence_interval": "20000-draw paired case bootstrap, two-sided 95%; decision uses upper endpoint",
        },
        "decision_rule": {
            "difference": "capsule-fragment minus ordinary",
            "supports_semantic_protocol_v2_requires": [
                "one-sided 95% optimized-loss upper <= 0.05",
                "paired-bootstrap total-token difference 95% upper < 0",
                "observed total-token reduction >= 0.05",
                "optimized acceptance in both categories",
                "no material environment, provider, validator, or fixture anomaly",
            ],
            "classifications": ["supports_semantic_protocol_v2", "does_not_support_semantic_protocol_v2", "inconclusive", "not_estimable_environment_failure"],
        },
        "budgets": {"pilot_tokens": PILOT_TOKENS, "phase_3_provider_tokens": PHASE_TOKEN_LIMIT, "combined_provider_tokens": TOTAL_TOKEN_LIMIT},
        "interruptions": {"retain_completed_rows": True, "resume_skips_completed_trial_ids": True, "stop_on_model_mismatch": True, "stop_on_provider_failure": True, "stop_before_next_call_at_token_limit": True},
        "pins": pins(),
    }


def validate_preregistration() -> tuple[dict, str]:
    document = json.loads(PREREG.read_text(encoding="utf-8"))
    if document != preregistration():
        raise MODEL.ModelBenchmarkError("confirmation preregistration no longer matches frozen inputs")
    return document, file_digest(PREREG)


class ExactModelClient:
    provider = "openai-responses"

    def __init__(self, cfg: dict, key: str):
        self.model = cfg["model"]
        self.settings = cfg["settings"]
        self.timeout = cfg["request_timeout_seconds"]
        base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        parsed = urllib.parse.urlsplit(base)
        if parsed.scheme not in {"https", "http"} or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise MODEL.ModelBenchmarkError("invalid credential-safe OPENAI_BASE_URL")
        if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise MODEL.ModelBenchmarkError("OPENAI_BASE_URL must use HTTPS")
        self.endpoint = f"{base}/responses"
        self.key = key
        self.observer = None
        self.identity = None

    def generate(self, instructions: str, input_text: str):
        body = {"model": self.model, "instructions": instructions, "input": input_text, "store": False, **self.settings}
        request = urllib.request.Request(
            self.endpoint,
            data=MODEL.canonical_json(body),
            headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                document = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            error.read(4096)
            raise MODEL.ModelBenchmarkError(f"provider HTTP status {error.code}") from error
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise MODEL.ModelBenchmarkError(type(error).__name__) from error
        if document.get("model") != self.model:
            raise MODEL.ModelBenchmarkError("provider model identifier does not match preregistration")
        reply = MODEL.parse_openai_response(document)
        if self.observer is not None:
            self.observer(self.identity, instructions, input_text, reply)
        return reply


def reference_prevalidation(runtime) -> int:
    accepted = 0
    for path, case in H.cases("confirmation"):
        for name in ("ordinary", SELECTED):
            rep = next(item for item in case["representations"] if item["id"] == name)
            artifact = relative_file(path.parent, rep["artifact"]).read_text(encoding="utf-8")
            result = H.validate_artifact(runtime, path, case, rep, artifact, 30)
            if not result["accepted"]:
                raise RUNTIME.EnvironmentFailure("fixture_prevalidation_failure", None, f"reference failed: {case['id']}/{name}")
            accepted += 1
    return accepted


def credential_check(env_file: Path | None) -> str:
    key = MODEL.load_api_key(env_file)
    if not key:
        raise RUNTIME.EnvironmentFailure("environment_preflight_failure", None, "OPENAI_API_KEY is required")
    for root in (BASE, RESULTS, ROOT / "docs"):
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path != env_file and key.encode() in path.read_bytes():
                raise RUNTIME.EnvironmentFailure("environment_preflight_failure", None, "credential value found in retained files")
    return key


def preflight(env_file: Path | None, *, resume: bool) -> tuple[object, dict, str, list, str]:
    document, revision = validate_preregistration()
    planned = H.schedule("confirmation", SELECTED)
    if len(planned) != 120 or len(planned) * 3 != 360:
        raise RUNTIME.EnvironmentFailure("environment_preflight_failure", None, "frozen trial budget mismatch")
    unused = () if resume else (RAW, EVENTS)
    runtime = RUNTIME.preflight(
        root=ROOT,
        required_files=(MANIFEST, PREREG, H.CONFIG, H.PERSISTENT, H.PROMPT, ROOT / "Cargo.lock"),
        unused_outputs=unused,
    )
    references = reference_prevalidation(runtime)
    key = credential_check(env_file)
    fake_items = planned[:2]
    fake = H.FakeClient([json.dumps({"artifact": relative_file(path.parent, rep["artifact"]).read_text(encoding="utf-8")}) for path, _, rep, _ in fake_items])
    for path, case, rep, repetition in fake_items:
        if not H.run_trial(runtime, fake, H.config(), "confirmation", path, case, rep, repetition, revision)["accepted"]:
            raise RUNTIME.EnvironmentFailure("environment_preflight_failure", None, "fake-provider smoke failed")
    return runtime, document, revision, planned, key


def completed_ids() -> set[str]:
    return set() if not RAW.exists() else {row["trial_id"] for row in MODEL.read_rows(RAW)}


def run(env_file: Path | None, resume: bool) -> None:
    runtime, _, revision, planned, key = preflight(env_file, resume=resume)
    complete = completed_ids() if resume else set()
    remaining = [item for item in planned if f"semantic-protocol-v2-confirmation:{item[1]['id']}:{item[2]['id']}:{item[3]:03d}" not in complete]
    phase_tokens = sum(row["metrics"]["total_tokens"] for row in MODEL.read_rows(RAW)) if RAW.exists() else 0
    if phase_tokens >= PHASE_TOKEN_LIMIT or PILOT_TOKENS + phase_tokens >= TOTAL_TOKEN_LIMIT:
        raise MODEL.ModelBenchmarkError("provider token limit already reached")
    client = ExactModelClient(H.config(), key)
    RESULTS.mkdir(parents=True, exist_ok=True)
    mode = "a" if resume else "x"
    with RAW.open(mode, encoding="utf-8") as stream, EVENTS.open(mode, encoding="utf-8") as journal:
        def retain_provider_call(identity, instructions, input_text, reply):
            journal.write(json.dumps({
                "event": "provider_call_completed",
                **(identity or {}),
                "instructions": instructions,
                "input_text": input_text,
                "response_id": reply.response_id,
                "response_text": reply.text,
                "usage": {
                    "input_tokens": reply.input_tokens,
                    "output_tokens": reply.output_tokens,
                    "total_tokens": reply.total_tokens,
                    "cached_input_tokens": reply.cached_input_tokens,
                    "reasoning_tokens": reply.reasoning_tokens,
                },
            }, sort_keys=True, separators=(",", ":")) + "\n")
            journal.flush()

        client.observer = retain_provider_call
        journal.write(json.dumps({"event": "run_resumed" if resume else "run_started", "remaining": len(remaining), "preregistration_revision": revision, "maximum_api_calls": len(remaining) * 3}, sort_keys=True) + "\n")
        journal.flush()
        for path, case, rep, repetition in remaining:
            if phase_tokens >= PHASE_TOKEN_LIMIT or PILOT_TOKENS + phase_tokens >= TOTAL_TOKEN_LIMIT:
                journal.write(json.dumps({"event": "budget_stopped", "phase_tokens": phase_tokens}, sort_keys=True) + "\n"); journal.flush()
                raise MODEL.ModelBenchmarkError("provider token limit reached")
            identity = {"case_id": case["id"], "representation": rep["id"], "repetition": repetition}
            client.identity = identity
            journal.write(json.dumps({"event": "trial_started", **identity}, sort_keys=True) + "\n"); journal.flush()
            try:
                row = H.run_trial(runtime, client, H.config(), "confirmation", path, case, rep, repetition, revision)
            except BaseException as error:
                journal.write(json.dumps({"event": "trial_interrupted", **identity, "classification": "provider_failure", "error_type": type(error).__name__}, sort_keys=True) + "\n"); journal.flush()
                raise
            stream.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"); stream.flush()
            for attempt in row["attempts"]:
                journal.write(json.dumps({"event": "attempt_completed", **identity, "attempt": attempt["attempt"], "accepted": attempt["validation"]["accepted"], "usage": attempt["usage"], "response_hash": attempt["response_hash"]}, sort_keys=True) + "\n")
            phase_tokens += row["metrics"]["total_tokens"]
            journal.write(json.dumps({"event": "trial_completed", **identity, "accepted": row["accepted"], "attempts": len(row["attempts"]), "phase_tokens": phase_tokens}, sort_keys=True) + "\n"); journal.flush()


def postrun(output: Path) -> None:
    rows = MODEL.read_rows(RAW)
    if len(rows) != 120:
        raise MODEL.ModelBenchmarkError(f"expected 120 completed trials, found {len(rows)}")
    output.mkdir(parents=True, exist_ok=True)
    aggregate = output / "aggregate.json"
    comparison = output / "comparison.json"
    breakdown = output / "category-breakdown.json"
    report = output / "report.md"
    for path in (aggregate, comparison, breakdown, report):
        if path.exists():
            raise MODEL.ModelBenchmarkError(f"refusing to overwrite {path.name}")
    H.aggregate(RAW, aggregate)
    prereg, _ = validate_preregistration()
    comparison_document = COMPARE.confirmation(rows, prereg)
    comparison.write_text(json.dumps(comparison_document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    aggregate_document = json.loads(aggregate.read_text(encoding="utf-8"))
    breakdown.write_text(json.dumps({"schema_version": 1, "evidence": "measured-confirmatory", "categories": aggregate_document["categories"]}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report.write_text(REPORTER.render(aggregate_document, comparison_document), encoding="utf-8")


def evidence_manifest() -> str:
    paths = (PREREG, MANIFEST, PREFLIGHT, RAW, EVENTS, RESULTS / "aggregate.json", RESULTS / "comparison.json", RESULTS / "category-breakdown.json", RESULTS / "report.md")
    return "\n".join(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(ROOT)}" for path in paths) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build-manifest")
    sub.add_parser("freeze")
    preflight_parser = sub.add_parser("preflight"); preflight_parser.add_argument("--env-file", type=Path)
    run_parser = sub.add_parser("run"); run_parser.add_argument("--env-file", type=Path); run_parser.add_argument("--resume", action="store_true")
    post = sub.add_parser("postrun"); post.add_argument("--output", type=Path, default=RESULTS)
    sub.add_parser("evidence")
    args = parser.parse_args()
    try:
        if args.command == "build-manifest":
            if MANIFEST.exists(): raise MODEL.ModelBenchmarkError("refusing to overwrite case manifest")
            MANIFEST.write_text(json.dumps(build_manifest(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(json.dumps({"case_manifest_revision": file_digest(MANIFEST)})); return 0
        if args.command == "freeze":
            if PREREG.exists(): raise MODEL.ModelBenchmarkError("refusing to overwrite confirmation preregistration")
            if json.loads(MANIFEST.read_text(encoding="utf-8")) != build_manifest(): raise MODEL.ModelBenchmarkError("case manifest mismatch")
            PREREG.write_text(json.dumps(preregistration(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(json.dumps({"preregistration_revision": file_digest(PREREG)})); return 0
        if args.command == "preflight":
            runtime, _, revision, planned, _ = preflight(args.env_file, resume=False)
            if PREFLIGHT.exists(): raise MODEL.ModelBenchmarkError("refusing to overwrite preflight manifest")
            document = {"schema_version": 1, "evidence": "measured-local", "preregistration_revision": revision, "trials": len(planned), "maximum_api_calls": len(planned) * 3, "reference_fixtures": 120, "fake_provider_calls": 2, "real_provider_calls": 0, "phase_token_limit": PHASE_TOKEN_LIMIT, "combined_token_limit": TOTAL_TOKEN_LIMIT, "runtime": runtime.public_record()}
            RESULTS.mkdir(parents=True, exist_ok=True); PREFLIGHT.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(json.dumps(document, indent=2, sort_keys=True)); return 0
        if args.command == "run": run(args.env_file, args.resume); return 0
        if args.command == "postrun": postrun(args.output); return 0
        manifest = RESULTS / "evidence.sha256"
        if manifest.exists(): raise MODEL.ModelBenchmarkError("refusing to overwrite evidence manifest")
        manifest.write_text(evidence_manifest(), encoding="utf-8"); print(file_digest(manifest)); return 0
    except (MODEL.ModelBenchmarkError, RUNTIME.EnvironmentFailure, OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        classification = error.classification if isinstance(error, RUNTIME.EnvironmentFailure) else "confirmation_failure"
        print(json.dumps({"classification": classification, "error_type": type(error).__name__}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
