"""Check the independent oracle against one pinned episode and corrupted inputs."""

from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import unittest

from tools.verify_oracle import greedy_distribution, verify_episode


ROOT = Path(__file__).resolve().parents[1]


class OracleRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        original = ROOT / "submission/LemmaPortfolio_supplement/original_release"
        cls.public_source = json.loads((original / "data/test.public.jsonl").read_text().splitlines()[0])
        cls.label_source = json.loads((original / "data/test.labels.jsonl").read_text().splitlines()[0])
        audit = json.loads((original / "results/posthoc_math_audit.json").read_text())
        cls.audit_source = audit["test"]["greedy_details"][0]

    def setUp(self):
        self.public = deepcopy(self.public_source)
        self.label = deepcopy(self.label_source)
        self.audit = deepcopy(self.audit_source)

    def test_pinned_episode_optimum_and_random_greedy_control(self):
        result = verify_episode(self.public, self.label, self.audit)
        self.assertEqual(result["optimal_portfolios"], 1)
        self.assertEqual(result["optimal_coverage"], 7)
        self.assertEqual(result["random_greedy_optimal"], Fraction(1, 3))
        self.assertEqual(result["random_greedy_coverage"], Fraction(19, 3))
        self.assertEqual(result["frequency_optima"], [])

    def test_omitted_optimum_is_rejected(self):
        self.label["optimal_portfolios"] = []
        with self.assertRaisesRegex(RuntimeError, "optimal portfolio set differs"):
            verify_episode(self.public, self.label, self.audit)

    def test_duplicate_optimum_is_rejected(self):
        self.label["optimal_portfolios"] *= 2
        with self.assertRaisesRegex(RuntimeError, "optimal portfolio set differs"):
            verify_episode(self.public, self.label, self.audit)

    def test_wrong_coverage_histogram_is_rejected(self):
        self.label["coverage_histogram"]["0"] += 1
        with self.assertRaisesRegex(RuntimeError, "coverage histogram differs"):
            verify_episode(self.public, self.label, self.audit)

    def test_unknown_proof_use_candidate_is_rejected(self):
        self.label["targets"][0]["direct_candidates"] = ["C99"]
        with self.assertRaisesRegex(RuntimeError, "invalid proof-use edges"):
            verify_episode(self.public, self.label, self.audit)

    def test_duplicate_proof_use_edge_is_rejected(self):
        self.label["targets"][0]["direct_candidates"] *= 2
        with self.assertRaisesRegex(RuntimeError, "invalid proof-use edges"):
            verify_episode(self.public, self.label, self.audit)

    def test_misaligned_public_target_is_rejected(self):
        self.public["targets"][0]["id"] = "T99"
        with self.assertRaisesRegex(RuntimeError, "target inventory differs"):
            verify_episode(self.public, self.label, self.audit)

    def test_wrong_saved_greedy_probabilities_are_rejected(self):
        self.audit["random_tie_coverage_probabilities"] = {"6": "1/2", "7": "1/2"}
        with self.assertRaisesRegex(RuntimeError, "random_tie_coverage_probabilities"):
            verify_episode(self.public, self.label, self.audit)

    def test_uniform_step_ties_use_exact_rational_probabilities(self):
        ids = [candidate["id"] for candidate in self.public["candidates"]]
        masks = {c: sum(1 << i for i, target in enumerate(self.label["targets"])
                        if c in target["direct_candidates"]) for c in ids}
        self.assertEqual(greedy_distribution(ids, masks), {6: Fraction(2, 3), 7: Fraction(1, 3)})


if __name__ == "__main__":
    unittest.main()
