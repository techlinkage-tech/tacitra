from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


CONFIRMATION = load(
    "test_semantic_protocol_v2_confirmation_runner",
    ROOT / "benchmarks/semantic_protocol_v2_confirmation.py",
)


class Response:
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return json.dumps({
            "id": "response-test",
            "model": "different-model",
            "output": [],
            "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
        }).encode()


class SemanticProtocolV2ConfirmationTest(unittest.TestCase):
    def test_case_manifest_is_balanced_and_disjoint(self):
        document = CONFIRMATION.build_manifest()
        self.assertEqual(document["counts"], {
            "total": 60,
            "repository-change": 30,
            "debug-repair": 30,
        })
        for field in (
            "case_ids",
            "task_hashes",
            "initial_source_hashes",
            "composite_revisions",
        ):
            self.assertEqual(document["overlaps"][field], [])
        self.assertIn("reference_hashes", document["overlaps"])
        self.assertIn("acceptance_hashes", document["overlaps"])

    def test_schedule_and_limits_are_exact(self):
        schedule = CONFIRMATION.H.schedule("confirmation", CONFIRMATION.SELECTED)
        self.assertEqual(len(schedule), 120)
        self.assertEqual({item[2]["id"] for item in schedule}, {"ordinary", "capsule-fragment"})
        self.assertEqual(CONFIRMATION.PHASE_TOKEN_LIMIT, 542_715)
        self.assertEqual(CONFIRMATION.PILOT_TOKENS, 207_285)

    def test_preregistration_uses_frozen_pilot_selection(self):
        document = CONFIRMATION.preregistration()
        self.assertEqual(document["selected_candidate"], "capsule-fragment")
        self.assertEqual(document["design"]["trials"], 120)
        self.assertEqual(document["design"]["maximum_api_calls"], 360)

    def test_provider_model_substitution_is_rejected(self):
        client = CONFIRMATION.ExactModelClient(CONFIRMATION.H.config(), "not-retained")
        with patch("urllib.request.urlopen", return_value=Response()):
            with self.assertRaisesRegex(
                CONFIRMATION.MODEL.ModelBenchmarkError,
                "model identifier does not match",
            ):
                client.generate("instructions", "input")


if __name__ == "__main__":
    unittest.main()
