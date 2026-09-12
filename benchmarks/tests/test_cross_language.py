import importlib.util
import json
import math
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


CROSS = load_module("test_cross_language_runner", ROOT / "benchmarks/cross_language.py")
COMPARE = load_module("test_cross_language_compare", ROOT / "benchmarks/cross_language_compare.py")


def synthetic_row(case_id, category, language, tokens, accepted=True):
    return {
        "case_id": case_id,
        "category": category,
        "language": language,
        "accepted": accepted,
        "compile_at_1": accepted,
        "pass_at_1": accepted,
        "repair_rounds": 0,
        "patch_size": 20 if category != "generation" else None,
        "wall_clock_time": 0.1,
        "metrics": {
            "input_tokens": tokens - 10,
            "output_tokens": 10,
            "total_tokens": tokens,
            "cached_input_tokens": 0,
            "reasoning_tokens": 0,
        },
        "pins": {
            "provider": "fake",
            "endpoint": "local://fake",
            "model": "fake",
            "model_settings": {},
            "config_revision": "sha256:config",
            "preregistration_revision": "sha256:prereg",
        },
    }


class CrossLanguageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        CROSS.MODEL.STATIC.BENCHMARKS = CROSS.BASE_DIR
        cls.config = CROSS.MODEL.load_config(CROSS.CONFIG)
        cls.cases = CROSS.MODEL.STATIC.discover_cases()

    def test_sample_size_is_familywise_and_case_based(self):
        alpha = 0.05 / 3
        required = math.ceil(math.log(alpha) / math.log(0.95))
        self.assertEqual(required, 80)
        self.assertGreater(COMPARE.one_sided_binomial_upper(0, 79, alpha), 0.05)
        self.assertLessEqual(COMPARE.one_sided_binomial_upper(0, 80, alpha), 0.05)

    def test_suite_has_85_unique_four_language_cases(self):
        self.assertEqual(len(self.cases), 85)
        self.assertEqual(len({case["id"] for _, case in self.cases}), 85)
        counts = {}
        for _, case in self.cases:
            counts[case["category"]] = counts.get(case["category"], 0) + 1
            self.assertEqual({value["language"] for value in case["representations"]}, set(CROSS.LANGUAGES))
        self.assertEqual(counts, {"generation": 29, "repository-change": 28, "debug-repair": 28})

    def test_configuration_and_preregistration_schemas_are_versioned(self):
        base = ROOT / "benchmarks/cross-language"
        config_schema = json.loads((base / "config-v1.schema.json").read_text())
        prereg_schema = json.loads((base / "preregistration-v1.schema.json").read_text())
        self.assertEqual(config_schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(prereg_schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(config_schema["properties"]["model"]["const"], "gpt-5.6-luna")
        self.assertEqual(prereg_schema["properties"]["id"]["const"], "cross-language-v1")
        self.assertFalse(config_schema["additionalProperties"])
        self.assertFalse(prereg_schema["additionalProperties"])

    def test_schedule_is_deterministic_and_language_interleaved(self):
        first = CROSS.schedule_document(self.config, self.cases)
        self.assertEqual(first, CROSS.schedule_document(self.config, self.cases))
        self.assertEqual(len(first), 340)
        for index in range(0, len(first), 4):
            block = first[index : index + 4]
            self.assertEqual(len({item["case_id"] for item in block}), 1)
            self.assertEqual({item["language"] for item in block}, set(CROSS.LANGUAGES))

    def test_primary_inputs_do_not_leak_references_or_use_tacitra_protocols(self):
        for case_path, case in self.cases:
            scopes = []
            for representation in case["representations"]:
                prompt, components = CROSS.base_prompt(case_path, case, representation)
                reference = CROSS.MODEL.STATIC.relative_file(case_path.parent, representation["artifact"]).read_text(encoding="utf-8")
                self.assertNotIn(reference, prompt)
                self.assertNotIn("symbol.edit-context", prompt)
                self.assertNotIn("replace_function_body", prompt)
                self.assertEqual(representation["surface"], "human-source")
                self.assertEqual(len(representation["repository_context"]), 0 if case["category"] == "generation" else 1)
                self.assertEqual(len(representation["diagnostic_context"]), 1 if case["category"] == "debug-repair" else 0)
                scopes.append((len(representation["repository_context"]), len(representation["diagnostic_context"])))
                self.assertEqual(components["instruction_bytes"], CROSS.PERSISTENT.stat().st_size)
            self.assertEqual(len(set(scopes)), 1)

    def test_fake_model_uses_common_validation_for_each_category_and_language(self):
        selected = []
        for category in ("generation", "repository-change", "debug-repair"):
            case_path, case = next(value for value in self.cases if value[1]["category"] == category)
            for representation in case["representations"]:
                selected.append((case_path, case, representation))
        responses = []
        for case_path, _, representation in selected:
            artifact = CROSS.MODEL.STATIC.relative_file(case_path.parent, representation["artifact"]).read_text(encoding="utf-8")
            responses.append(json.dumps({"artifact": artifact}, separators=(",", ":")))
        client = CROSS.FakeClient(responses)
        for case_path, case, representation in selected:
            row = CROSS.run_trial(client, self.config, case_path, case, representation,
                                  "fake-test", "sha256:preregistered", 30)
            self.assertTrue(row["accepted"], (case["id"], representation["language"], row["failure"]))

    def test_comparison_classification_and_failure_cost(self):
        rows = []
        categories = ("generation", "repository-change", "debug-repair")
        for index in range(85):
            case_id = f"synthetic-{index:03d}"
            category = categories[index % 3]
            rows.append(synthetic_row(case_id, category, "tacitra", 100))
            for language in ("python", "go", "rust"):
                rows.append(synthetic_row(case_id, category, language, 200))
        result = COMPARE.compare(rows, 200, 7)
        self.assertEqual(result["decision"]["classification"], "supports_language_advantage")
        self.assertEqual([value["comparator"] for value in result["comparisons"]], ["python", "go", "rust"])

        rows[0]["accepted"] = False
        rows[0]["compile_at_1"] = False
        rows[0]["pass_at_1"] = False
        rows[0]["metrics"]["total_tokens"] = 900
        changed = COMPARE.compare(rows, 200, 7)
        self.assertGreater(changed["comparisons"][0]["tacitra"]["total_tokens_per_accepted_solution"], 100)

    def test_frozen_preregistration_matches_every_pin(self):
        document, revision = CROSS.validate_preregistration(self.config, self.cases)
        self.assertEqual(document["design"]["total_trials"], 340)
        self.assertTrue(revision.startswith("sha256:"))


if __name__ == "__main__":
    unittest.main()
