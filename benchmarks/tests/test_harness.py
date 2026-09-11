import copy
import importlib.util
import subprocess
import unittest
from pathlib import Path


HARNESS_PATH = Path(__file__).resolve().parents[1] / "harness.py"
SPEC = importlib.util.spec_from_file_location("tacitra_benchmark_harness", HARNESS_PATH)
HARNESS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HARNESS)


def row(accepted, total):
    value = {
        "schema_version": 2,
        "evidence": "measured",
        "measurement_mode": "static_reference",
        "run_id": "test",
        "trial_id": f"test:{accepted}:{total}",
        "case_id": "case",
        "category": "generation",
        "representation": "python-source",
        "language": "python",
        "surface": "human-source",
        "pins": {
            "case_revision": "sha256:x", "harness_revision": "sha256:y",
            "model": None, "model_settings": {},
            "tokenizer_name": "utf8-bytes", "tokenizer_version": "1", "environment": {},
        },
        "tokens": {
            "instruction_tokens": total - 3, "specification_tokens": 1,
            "repository_context_tokens": 0, "task_tokens": 1,
            "input_tokens": total - 1, "output_tokens": 1,
            "diagnostic_tokens": 0, "repair_tokens": 0, "total_tokens": total,
        },
        "compile_at_1": accepted, "pass_at_1": accepted,
        "repair_rounds": 0, "max_repair_rounds": 2, "patch_size": None,
        "accepted": accepted, "wall_clock_time": 0.1,
        "failure": None if accepted else {"phase": "compile"}, "artifacts": {},
    }
    return value


class HarnessTests(unittest.TestCase):
    def test_byte_tokenizer_is_exact_and_versioned(self):
        self.assertEqual(HARNESS.tokens("Tacitra".encode()), 7)
        self.assertEqual(HARNESS.tokens("型".encode()), 3)
        self.assertEqual(HARNESS.TOKENIZER_NAME, "utf8-bytes")
        self.assertEqual(HARNESS.TOKENIZER_VERSION, "1")

    def test_all_cases_validate(self):
        cases = HARNESS.discover_cases()
        self.assertEqual({case[1]["category"] for case in cases}, HARNESS.CATEGORIES)

    def test_bounded_query_fixture_matches_current_semantics(self):
        case = HARNESS.BENCHMARKS / "cases/repository-increment"
        output = subprocess.run(
            [
                str(HARNESS.ROOT / "target/debug/tacitra"),
                "symbol.describe",
                str(case / "base.taci"),
                "sym:fn:increment",
            ],
            capture_output=True,
            check=True,
        ).stdout
        self.assertEqual(output, (case / "query.json").read_bytes())

    def test_optimized_cases_and_compact_fixtures_validate(self):
        previous = HARNESS.BENCHMARKS
        try:
            HARNESS.BENCHMARKS = HARNESS.ROOT / "benchmarks/optimized"
            cases = HARNESS.discover_cases()
            self.assertEqual({case[1]["category"] for case in cases}, HARNESS.CATEGORIES)
        finally:
            HARNESS.BENCHMARKS = previous

        source = HARNESS.ROOT / "benchmarks/cases/repository-increment/base.taci"
        edit_context = HARNESS.ROOT / "benchmarks/optimized/cases/repository-increment/edit-context.json"
        output = subprocess.run(
            [str(HARNESS.ROOT / "target/debug/tacitra"), "symbol.edit-context", str(source), "sym:fn:increment"],
            capture_output=True,
            check=True,
        ).stdout
        self.assertEqual(output, edit_context.read_bytes())
        self.assertLess(edit_context.stat().st_size, (source.parent / "query.json").stat().st_size)

        manifest = HARNESS.ROOT / "examples/interop/python/manifest.json"
        call_context = HARNESS.ROOT / "benchmarks/optimized/cases/interop-add/call-context.json"
        output = subprocess.run(
            [str(HARNESS.ROOT / "target/debug/tacitra"), "external.call-context", str(manifest), "add"],
            capture_output=True,
            check=True,
        ).stdout
        self.assertEqual(output, call_context.read_bytes())
        self.assertLess(call_context.stat().st_size, manifest.stat().st_size)

    def test_primary_metric_keeps_failed_trial_tokens(self):
        accepted = row(True, 100)
        failed = row(False, 300)
        HARNESS.validate_result(accepted)
        HARNESS.validate_result(failed)
        group = HARNESS.aggregate_rows([accepted, failed])["groups"][0]
        self.assertEqual(group["accepted"], 1)
        self.assertEqual(group["failed"], 1)
        self.assertEqual(group["total_tokens_per_accepted_solution"], 400)
        self.assertEqual(group["total_tokens"]["median"], 200)
        self.assertEqual(group["total_tokens"]["population_variance"], 10000)

    def test_inconsistent_or_mixed_results_are_rejected(self):
        invalid = row(True, 100)
        invalid["tokens"]["total_tokens"] += 1
        with self.assertRaises(HARNESS.BenchmarkError):
            HARNESS.validate_result(invalid)
        different = copy.deepcopy(row(True, 100))
        different["pins"]["tokenizer_version"] = "2"
        with self.assertRaises(HARNESS.BenchmarkError):
            HARNESS.aggregate_rows([row(True, 100), different])


if __name__ == "__main__":
    unittest.main()
