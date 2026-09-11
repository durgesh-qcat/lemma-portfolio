"""Guard the narrow float compatibility fix without changing submitted files."""

import importlib.util
from pathlib import Path
import unittest

from tools.verify_submission import compatible_comparison, CONTINUOUS_METRIC


ROOT = Path(__file__).resolve().parents[1]


class SubmissionComparisonTests(unittest.TestCase):
    def setUp(self):
        path = ROOT / "submission/LemmaPortfolio_supplement/verify_followups.py"
        spec = importlib.util.spec_from_file_location("archived_comparison_test", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.same = compatible_comparison(module.same)
        self.same = module.same

    def test_roundoff_at_integer_encoded_continuous_metric_is_accepted(self):
        self.same(79.99999999999999, 80, "run/summary/" + CONTINUOUS_METRIC)

    def test_original_recursive_comparison_uses_the_fix(self):
        self.same({"rows": [{CONTINUOUS_METRIC: 79.99999999999999, "total": 60}]},
                  {"rows": [{CONTINUOUS_METRIC: 80, "total": 60}]}, "runs")

    def test_material_metric_change_is_rejected(self):
        with self.assertRaises(RuntimeError):
            self.same(79.999, 80, "run/summary/" + CONTINUOUS_METRIC)

    def test_near_integer_count_is_not_tolerated(self):
        with self.assertRaises(RuntimeError):
            self.same(59.99999999999999, 60, "run/summary/total")

    def test_near_match_on_other_integer_encoded_metric_is_not_tolerated(self):
        with self.assertRaises(RuntimeError):
            self.same(79.99999999999999, 80, "run/summary/target_coverage_percentage")

    def test_metric_name_must_be_the_terminal_key(self):
        with self.assertRaises(RuntimeError):
            self.same(79.99999999999999, 80, CONTINUOUS_METRIC + "/total")

    def test_boolean_numeric_equivalence_is_rejected(self):
        for actual, expected in ((True, 1), (1, True), (False, 0.0), (1.0, True)):
            with self.subTest(actual=actual, expected=expected), self.assertRaises(RuntimeError):
                self.same(actual, expected, "row/valid")
        with self.assertRaises(RuntimeError):
            self.same(True, 1, "row/" + CONTINUOUS_METRIC)

    def test_matching_booleans_and_existing_exact_metric_equality_pass(self):
        self.same({"valid": True, "valid_percentage": 100.0},
                  {"valid": True, "valid_percentage": 100}, "row")

    def test_nonfinite_or_wrong_type_metric_is_rejected(self):
        for actual in (float("nan"), float("inf"), "80"):
            with self.subTest(actual=actual), self.assertRaises(RuntimeError):
                self.same(actual, 80, "row/" + CONTINUOUS_METRIC)

    def test_ids_and_integer_counts_stay_exact(self):
        for actual, expected in (("MLP4B_0001", "MLP4B_0000"), (59, 60)):
            with self.subTest(actual=actual), self.assertRaises(RuntimeError):
                self.same(actual, expected, "row/field")


if __name__ == "__main__":
    unittest.main()
