"""Tests for cross-version comparison in the release verifier."""

import unittest

from verify_release import equivalent_generated


class GeneratedResultComparisonTests(unittest.TestCase):
    def test_accepts_only_tiny_float_differences(self) -> None:
        left = {"metric": [0.30000000000000004, 25], "label": "same"}
        right = {"metric": [0.3, 25], "label": "same"}
        self.assertTrue(equivalent_generated(left, right))

    def test_rejects_material_float_difference(self) -> None:
        self.assertFalse(equivalent_generated(0.3, 0.300001))

    def test_keeps_discrete_values_and_types_exact(self) -> None:
        self.assertFalse(equivalent_generated({"count": 25}, {"count": 25.0}))
        self.assertFalse(equivalent_generated({"valid": True}, {"valid": 1}))
        self.assertFalse(equivalent_generated(["a", "b"], ["b", "a"]))

    def test_rejects_nonfinite_floats(self) -> None:
        self.assertFalse(equivalent_generated(float("nan"), float("nan")))
        self.assertFalse(equivalent_generated(float("inf"), float("inf")))


if __name__ == "__main__":
    unittest.main()
