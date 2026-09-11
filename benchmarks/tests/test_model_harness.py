import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


MODEL = load_module("tacitra_test_model_harness", ROOT / "benchmarks/model_harness.py")
COMPARE = load_module("tacitra_test_model_compare", ROOT / "benchmarks/model_compare.py")
PREREGISTER = load_module(
    "tacitra_test_preregister", ROOT / "benchmarks/confirmation/preregister.py"
)


CONFIG = {
    "schema_version": 1,
    "provider": "openai-responses",
    "model": "test-model-pinned",
    "settings": {"temperature": 0},
    "request_timeout_seconds": 10,
    "max_output_characters": 10000,
    "schedule_seed": 7,
}


class FakeClient:
    provider = "fake-responses"
    model = "test-model-pinned"
    settings = {"temperature": 0}
    endpoint = "https://invalid.example/v1/responses"

    def __init__(self, artifacts):
        self.artifacts = iter(artifacts)
        self.inputs = []

    def generate(self, instructions, input_text):
        self.inputs.append((instructions, input_text))
        artifact = next(self.artifacts)
        text = json.dumps({"artifact": artifact})
        return MODEL.ModelReply(text, "response-test", 100, 20, 120, 0, 3)


def python_generation_case():
    MODEL.configure_suite("baseline")
    case_path, case = next(
        item for item in MODEL.STATIC.discover_cases(["integer-arithmetic"])
    )
    representation = next(
        item for item in case["representations"] if item["id"] == "python-source"
    )
    return case_path, case, representation


class ModelHarnessTests(unittest.TestCase):
    def test_openai_response_parser_keeps_provider_usage(self):
        reply = MODEL.parse_openai_response({
            "id": "resp_1",
            "output": [{"type": "message", "content": [
                {"type": "output_text", "text": '{"artifact":"print(42)"}'},
            ]}],
            "usage": {
                "input_tokens": 11,
                "output_tokens": 7,
                "total_tokens": 18,
                "input_tokens_details": {"cached_tokens": 4},
                "output_tokens_details": {"reasoning_tokens": 2},
            },
        })
        self.assertEqual(reply.text, '{"artifact":"print(42)"}')
        self.assertEqual(reply.total_tokens, 18)
        self.assertEqual(reply.cached_input_tokens, 4)
        self.assertEqual(reply.reasoning_tokens, 2)

    def test_reference_solution_is_not_sent_and_valid_artifact_passes(self):
        case_path, case, representation = python_generation_case()
        client = FakeClient(["print(42)\n"])
        result = MODEL.run_trial(
            client, CONFIG, "baseline", case_path, case, representation,
            "pilot", 1, 10,
        )
        MODEL.validate_model_result(result)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["repair_rounds"], 0)
        reference = MODEL.STATIC.relative_file(
            case_path.parent, representation["artifact"]
        ).read_text(encoding="utf-8")
        self.assertNotIn(reference, client.inputs[0][1])

    def test_failed_attempt_is_repaired_and_all_usage_is_counted(self):
        case_path, case, representation = python_generation_case()
        client = FakeClient(["print(41)\n", "print(42)\n"])
        result = MODEL.run_trial(
            client, CONFIG, "baseline", case_path, case, representation,
            "pilot", 1, 10,
        )
        self.assertTrue(result["accepted"])
        self.assertEqual(result["repair_rounds"], 1)
        self.assertEqual(result["metrics"]["total_tokens"], 240)
        self.assertEqual(result["metrics"]["repair_output_tokens"], 20)
        self.assertIn("REPAIR REQUIRED", result["attempts"][1]["input_text"])

    def test_aggregate_keeps_failure_cost_and_paired_compare_is_seeded(self):
        case_path, case, representation = python_generation_case()
        accepted = MODEL.run_trial(
            FakeClient(["print(42)\n"]), CONFIG, "baseline", case_path, case,
            representation, "left", 1, 10,
        )
        failed = MODEL.run_trial(
            FakeClient(["print(41)\n"] * 3), CONFIG, "baseline", case_path, case,
            representation, "left", 2, 10,
        )
        aggregate = MODEL.aggregate_rows([accepted, failed])
        self.assertEqual(aggregate["accepted"], 1)
        self.assertEqual(aggregate["total_tokens"], 480)
        self.assertEqual(aggregate["total_tokens_per_accepted_solution"], 480)

        optimized = []
        for row in (accepted, failed):
            copied = json.loads(json.dumps(row))
            copied["pins"]["suite"] = "optimized"
            copied["trial_id"] = copied["trial_id"].replace(":baseline:", ":optimized:")
            copied["metrics"]["total_tokens"] -= 10
            for attempt in copied["attempts"]:
                attempt["usage"]["total_tokens"] -= 10 // len(copied["attempts"])
            optimized.append(copied)
        comparison = COMPARE.compare([accepted, failed], optimized, 100, 9, -0.5)
        self.assertEqual(comparison["paired_trials"], 2)
        self.assertEqual(
            comparison["difference"]["bootstrap_95_percent_interval"]["seed"], 9)
        self.assertIn(
            comparison["decision"]["classification"],
            {"supports_adoption", "reject", "inconclusive"},
        )

    def test_placeholder_config_and_invalid_output_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            config = dict(CONFIG)
            config["model"] = "SET_PINNED_MODEL_ID"
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaises(MODEL.ModelBenchmarkError):
                MODEL.load_config(path)
        with self.assertRaises(MODEL.ModelBenchmarkError):
            MODEL.extract_artifact("```python\nprint(42)\n```", 1000)

    def test_confirmation_sample_supports_five_percent_zero_loss_bound(self):
        upper = COMPARE.one_sided_binomial_upper(0, 60)
        self.assertIsNotNone(upper)
        self.assertLess(upper, 0.05)
        self.assertGreater(upper, 0.048)

    def test_confirmation_suite_and_preregistration_are_frozen_and_paired(self):
        for suite in ("confirmation-baseline", "confirmation-optimized"):
            MODEL.configure_suite(suite)
            cases = MODEL.STATIC.discover_cases()
            self.assertEqual(len(cases), 20)
            categories = [case["category"] for _, case in cases]
            self.assertEqual({name: categories.count(name) for name in set(categories)}, {
                "syntax": 4,
                "generation": 4,
                "repository-change": 4,
                "debug-repair": 4,
                "interop": 4,
            })
        document = PREREGISTER.document(CONFIG)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "preregistration.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            revision = MODEL.validate_confirmation_preregistration(path, CONFIG, 3)
            self.assertTrue(revision.startswith("sha256:"))

    def test_cli_validates_without_a_key_and_refuses_to_run_without_one(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            config = directory / "config.json"
            output = directory / "raw.jsonl"
            config.write_text(json.dumps(CONFIG), encoding="utf-8")
            validate = subprocess.run(
                [
                    "python3", str(ROOT / "benchmarks/model_harness.py"), "validate",
                    "--suite", "optimized", "--config", str(config),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(validate.returncode, 0, validate.stderr)
            environment = os.environ.copy()
            environment.pop("OPENAI_API_KEY", None)
            run = subprocess.run(
                [
                    "python3", str(ROOT / "benchmarks/model_harness.py"), "paired-run",
                    "--config", str(config), "--output", str(output),
                    "--run-id", "test-no-key", "--case", "integer-arithmetic",
                    "--representation", "tacitra-source",
                ],
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(run.returncode, 2)
            self.assertIn("OPENAI_API_KEY is required", run.stderr)
            self.assertFalse(output.exists())

    def test_env_file_reads_only_the_key_without_shell_evaluation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env.local"
            path.write_text(
                "IGNORED=$(false)\nexport OPENAI_API_KEY='test-secret'\n",
                encoding="utf-8",
            )
            previous = os.environ.pop("OPENAI_API_KEY", None)
            try:
                self.assertEqual(MODEL.load_api_key(path), "test-secret")
            finally:
                if previous is not None:
                    os.environ["OPENAI_API_KEY"] = previous


if __name__ == "__main__":
    unittest.main()
