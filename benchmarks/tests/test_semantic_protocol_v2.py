from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    import sys
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


HARNESS = load("test_semantic_protocol_v2_harness", ROOT / "benchmarks/semantic_protocol_v2.py")


class SemanticProtocolV2Test(unittest.TestCase):
    def test_cases_are_independent_balanced_and_do_not_leak_references(self):
        pilot = HARNESS.cases("pilot")
        confirmation = HARNESS.cases("confirmation")
        old = {path.parent.name for path in (ROOT / "benchmarks/semantic-protocol/cases").glob("*/case.json")}
        self.assertEqual(len(pilot), 12)
        self.assertEqual(len(confirmation), 60)
        self.assertFalse(({case["id"] for _, case in pilot + confirmation}) & old)
        for values, per_category in ((pilot, 6), (confirmation, 30)):
            counts = {name: sum(case["category"] == name for _, case in values) for name in ("repository-change", "debug-repair")}
            self.assertEqual(counts, {"repository-change": per_category, "debug-repair": per_category})
        for path, case in pilot + confirmation:
            for representation in case["representations"]:
                prompt, _ = HARNESS.prompt_for(path, case, representation)
                self.assertNotIn("reference.", prompt)

    def test_all_candidate_references_use_one_checked_execution_path(self):
        runtime = HARNESS.RUNTIME.preflight(
            root=ROOT,
            required_files=(ROOT / "Cargo.lock",),
        )
        for path, case in HARNESS.cases("pilot"):
            for representation in case["representations"]:
                artifact = (path.parent / representation["artifact"]).read_text(encoding="utf-8")
                result = HARNESS.validate_artifact(runtime, path, case, representation, artifact, 30)
                self.assertTrue(result["accepted"], f"{case['id']}/{representation['id']}: {result}")

    def test_output_is_deterministic_and_credentials_do_not_reach_children(self):
        environment = dict(os.environ)
        environment["OPENAI_API_KEY"] = "test-secret-not-for-child"
        runtime = HARNESS.RUNTIME.preflight(environment=environment, root=ROOT)
        self.assertNotIn("OPENAI_API_KEY", runtime.child_environment)
        path, case = HARNESS.cases("pilot")[0]
        representation = next(item for item in case["representations"] if item["id"] == "capsule-fragment")
        artifact = (path.parent / representation["artifact"]).read_text(encoding="utf-8")
        first = HARNESS.validate_artifact(runtime, path, case, representation, artifact, 30)
        second = HARNESS.validate_artifact(runtime, path, case, representation, artifact, 30)
        self.assertEqual(first, second)

    def test_schedule_and_budget_are_fixed(self):
        self.assertEqual(len(HARNESS.schedule("pilot")), 120)
        self.assertLessEqual(len(HARNESS.schedule("pilot")) * 3, 360)
        self.assertEqual(HARNESS.TOKEN_BUDGET, 750_000)


if __name__ == "__main__":
    unittest.main()
