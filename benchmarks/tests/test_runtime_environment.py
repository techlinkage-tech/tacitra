import importlib.util
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


RUNTIME = load("runtime_environment_test", ROOT / "benchmarks/runtime_environment.py")
RECOVERY = load("semantic_recovery_test", ROOT / "benchmarks/semantic_protocol_recovery.py")
COMPARE = load("semantic_compare_v2_test", ROOT / "benchmarks/semantic_protocol_compare_v2.py")
AGGREGATE = load("semantic_aggregate_v2_test", ROOT / "benchmarks/semantic_protocol_aggregate_v2.py")


class RuntimeEnvironmentTest(unittest.TestCase):
    def executable(self, directory: Path, name: str, output: str) -> Path:
        path = directory / name
        path.write_text(f"#!/bin/sh\necho '{output}'\n", encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
        return path

    def test_rustc_is_resolved_from_path_and_absolute_path_works_in_temp_dir(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rustc = self.executable(root, "rustc", "rustc 1.85.1 (test)")
            tool = RUNTIME.resolve_tool("rustc", {"PATH": str(root)}, expected_version="1.85.1")
            self.assertEqual(tool.executable, rustc.resolve())
            result = RUNTIME._run_version(tool.executable, ("--version",), {"PATH": ""})
            self.assertIn("1.85.1", result)

    def test_missing_rustc_and_version_mismatch_are_classified(self):
        with self.assertRaises(RUNTIME.EnvironmentFailure) as missing:
            RUNTIME.resolve_tool("rustc", {"PATH": ""}, expected_version="1.85.1")
        self.assertEqual(missing.exception.classification, "tool_not_found")
        with tempfile.TemporaryDirectory() as directory:
            self.executable(Path(directory), "rustc", "rustc 1.84.0 (test)")
            with self.assertRaises(RUNTIME.EnvironmentFailure) as mismatch:
                RUNTIME.resolve_tool("rustc", {"PATH": directory}, expected_version="1.85.1")
            self.assertEqual(mismatch.exception.classification, "tool_version_mismatch")

    def test_env_file_does_not_change_path(self):
        before = os.environ.get("PATH")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env.local"
            path.write_text("OPENAI_API_KEY=test-only\nPATH=/forbidden\n", encoding="utf-8")
            self.assertEqual(RECOVERY.FROZEN.MODEL.load_api_key(path), "test-only")
        self.assertEqual(os.environ.get("PATH"), before)

    def test_child_environment_preserves_path_and_removes_credentials(self):
        child = RUNTIME.safe_child_environment({
            "PATH": "/safe/bin", "OPENAI_API_KEY": "secret", "OTHER_API_KEY": "secret2",
            "RUSTC": "/safe/bin/rustc",
        })
        self.assertEqual(child["PATH"], "/safe/bin")
        self.assertEqual(child["RUSTC"], "/safe/bin/rustc")
        self.assertNotIn("OPENAI_API_KEY", child)
        self.assertNotIn("OTHER_API_KEY", child)

    def test_preflight_failure_constructs_no_provider_client(self):
        calls = []
        def factory(config):
            calls.append(config)
            return object()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "raw.jsonl"
            with self.assertRaises(RECOVERY.RUNTIME.EnvironmentFailure):
                RECOVERY.client_after_preflight(factory, environment={"PATH": ""}, output=output)
            self.assertFalse(output.exists())
            self.assertFalse(Path(str(output) + ".events.jsonl").exists())
        self.assertEqual(calls, [])

    def test_timeout_has_explicit_classification(self):
        python = RUNTIME.ResolvedTool("python3", Path(sys.executable).resolve(), sys.version)
        runtime = RUNTIME.RuntimeEnvironment(
            {"python3": python, "go": python, "patch": python, "rustc": python, "cargo": python},
            RUNTIME.safe_child_environment(dict(os.environ)), "test",
        )
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            ok, result = RUNTIME.execute_commands(
                [["python3", "-c", "import time; time.sleep(30)"]], work, work / "artifact", work,
                1, runtime,
            )
        self.assertFalse(ok)
        self.assertTrue(result.timed_out)
        self.assertEqual(result.classification, "timeout")

    def test_credentials_are_not_visible_to_acceptance_subprocess(self):
        python = RUNTIME.ResolvedTool("python3", Path(sys.executable).resolve(), sys.version)
        child = RUNTIME.safe_child_environment({**os.environ, "OPENAI_API_KEY": "must-not-escape"})
        runtime = RUNTIME.RuntimeEnvironment(
            {"python3": python, "go": python, "patch": python, "rustc": python, "cargo": python},
            child, "test",
        )
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            ok, result = RUNTIME.execute_commands(
                [["python3", "-c", "import os; print('OPENAI_API_KEY' in os.environ)"]],
                work, work / "artifact", work, 5, runtime,
            )
        self.assertTrue(ok)
        self.assertEqual(result.stdout.strip(), "False")
        self.assertNotIn("must-not-escape", json.dumps(runtime.public_record()))

    def test_zero_accepted_is_not_estimable_and_other_comparisons_remain(self):
        rows = []
        for case_no in range(2):
            for representation in COMPARE.LEGACY.RUN.REPRESENTATIONS:
                accepted = representation != "rust-ordinary"
                rows.append({
                    "case_id": f"case-{case_no}", "category": "debug-repair",
                    "representation": representation, "accepted": accepted,
                    "compile_at_1": accepted, "pass_at_1": accepted, "repair_rounds": 0 if accepted else 2,
                    "patch_size": 10, "wall_clock_time": 1.0,
                    "metrics": {"total_tokens": 100, "input_tokens": 70, "output_tokens": 30,
                                "cached_input_tokens": 0, "reasoning_tokens": 10},
                })
        document = COMPARE.compare(rows, 100, 1)
        rust = document["exploratory"][2]
        self.assertEqual(rust["status"], "not_estimable")
        self.assertEqual(rust["difference"]["not_estimable_reason"], "zero_accepted_trials")
        self.assertEqual(rust["total_tokens_retained"], 400)
        self.assertEqual(rust["failed_trial_tokens_retained"], 200)
        self.assertNotEqual(document["exploratory"][0]["status"], "not_estimable")
        report = COMPARE.render(document)
        self.assertIn("not estimable", report)
        aggregate = AGGREGATE.aggregate_rows(rows)
        rust_group = next(value for value in aggregate["representations"] if value["representation"] == "rust-ordinary")
        self.assertIsNone(rust_group["total_tokens_per_accepted_solution"])
        self.assertEqual(rust_group["not_estimable_reason"], "zero_accepted_trials")
        self.assertEqual(rust_group["total_provider_tokens"], 200)

    def test_reference_prevalidation_uses_replication_validation_path(self):
        runtime, _, cases, _ = RECOVERY.run_preflight()
        document = RECOVERY.prevalidate_rust(runtime, cases[:1], 30)
        self.assertEqual(document["accepted"], 1)
        self.assertEqual(document["provider_api_calls"], 0)
        self.assertEqual(
            document["same_execution_function_as_replication"],
            "semantic_protocol_recovery.validate_artifact",
        )


if __name__ == "__main__":
    unittest.main()
