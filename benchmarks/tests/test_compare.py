import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("tacitra_benchmark_compare", ROOT / "benchmarks/compare.py")
COMPARE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COMPARE)


class ComparisonTests(unittest.TestCase):
    def test_retained_m6_comparison_is_consistent(self):
        result_dir = ROOT / "benchmarks/results/m6-optimization-v1"
        result = COMPARE.compare(
            COMPARE.load(result_dir / "before.aggregate.json"),
            COMPARE.load(result_dir / "after.aggregate.json"),
        )
        self.assertEqual(result["before"]["trials"], 63)
        self.assertEqual(result["after"]["trials"], 63)
        self.assertEqual(result["before"]["accepted"], 63)
        self.assertEqual(result["after"]["accepted"], 63)
        self.assertEqual(result["overall"]["classification"], "improved")
        self.assertEqual(result["component_deltas"]["instruction_tokens"]["delta"], 0)
        self.assertLess(result["component_deltas"]["specification_tokens"]["delta"], 0)

    def test_incompatible_tokenizers_are_rejected(self):
        result_dir = ROOT / "benchmarks/results/m6-optimization-v1"
        before = COMPARE.load(result_dir / "before.aggregate.json")
        after = COMPARE.load(result_dir / "after.aggregate.json")
        after["tokenizer_version"] = "different"
        with self.assertRaises(ValueError):
            COMPARE.compare(before, after)


if __name__ == "__main__":
    unittest.main()
