from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from apibench.hard_blind_v4 import audit_pinned_lean as lean_v4
from apibench.hard_blind_v4 import build_hard_blind_v4 as build
from apibench.hard_blind_v4 import construction_diagnostics
from apibench.scripts import audit_static_direct_value_labels as lean_common


def _jsonl_bytes(rows: list[dict[str, object]]) -> bytes:
    return "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows).encode()


class ConstructionTests(unittest.TestCase):
    def test_exhaustive_optima_is_complete_and_histogram_has_560(self) -> None:
        candidates = [f"C{index:02d}" for index in range(1, 17)]
        incidence = [
            frozenset({"C01", "C07"}),
            frozenset({"C01", "C07"}),
            frozenset({"C02", "C08"}),
            frozenset({"C02", "C08"}),
            frozenset({"C03", "C09"}),
            frozenset({"C03", "C09"}),
            frozenset({"C04", "C10"}),
            frozenset({"C04", "C10"}),
        ]
        optimum, optimal, histogram = build.exhaustive_optima(candidates, incidence)
        self.assertEqual(sum(histogram.values()), 560)
        self.assertEqual(optimum, 6)
        self.assertGreater(len(optimal), 1)
        self.assertEqual(optimal, tuple(sorted(optimal)))
        self.assertTrue(
            all(build.incidence_coverage(frozenset(row), incidence) == optimum for row in optimal)
        )

    def test_public_construction_diagnostics_are_public_shape_only(self) -> None:
        episode = {
            "episode_id": "E0",
            "candidates": [
                {"id": f"C{index:02d}", "statement": f"∀ (x : Nat), x + {index} = {index} + x"}
                for index in range(1, 17)
            ],
            "targets": [
                {"id": f"T{index:02d}", "statement": f"∀ (x : Nat), x + {index} ≥ x"}
                for index in range(1, 9)
            ],
        }
        predictions = construction_diagnostics.predict_episode(episode)
        self.assertEqual(len(predictions), 18)
        self.assertFalse(any(name.startswith("true_") for name in predictions))
        for prediction in predictions.values():
            self.assertEqual(len(prediction), 3)
            self.assertEqual(len(set(prediction)), 3)
            self.assertTrue(set(prediction) <= {f"C{index:02d}" for index in range(1, 17)})


class PinnedLeanAuditTests(unittest.TestCase):
    def _fixture(self, root: Path) -> tuple[Path, Path, Path, Path]:
        candidate_ids = [f"C{index:02d}" for index in range(1, 17)]
        target_ids = [f"T{index:02d}" for index in range(1, 9)]
        incidence = [frozenset({candidate_ids[index % 4]}) for index in range(8)]
        optimum, optimal, histogram = build.exhaustive_optima(candidate_ids, incidence)
        public_row = {
            "benchmark_id": "fixture.v4",
            "candidates": [
                {"id": candidate_id, "statement": f"CandidateStatement{index}"}
                for index, candidate_id in enumerate(candidate_ids)
            ],
            "episode_id": "MLP4B_0000",
            "schema_version": build.PUBLIC_SCHEMA,
            "selection_budget": 3,
            "targets": [
                {"id": target_id, "statement": f"TargetStatement{index}"}
                for index, target_id in enumerate(target_ids)
            ],
        }
        use_counts = {
            candidate_id: sum(candidate_id in direct for direct in incidence)
            for candidate_id in candidate_ids
        }
        label_row = {
            "active_candidates": sorted(candidate for candidate, count in use_counts.items() if count),
            "benchmark_id": "fixture.v4",
            "candidate_displayed_use_counts": use_counts,
            "candidate_sources": {
                candidate_id: f"Fixture.candidate{index}"
                for index, candidate_id in enumerate(candidate_ids)
            },
            "coverage_histogram": {
                str(score): count for score, count in sorted(histogram.items())
            },
            "episode_id": "MLP4B_0000",
            "optimal_coverage": optimum,
            "optimal_portfolios": [list(row) for row in optimal],
            "schema_version": build.LABEL_SCHEMA,
            "target_sources": {
                target_id: f"Fixture.target{index}"
                for index, target_id in enumerate(target_ids)
            },
            "targets": [
                {"id": target_id, "direct_candidates": sorted(direct)}
                for target_id, direct in zip(target_ids, incidence, strict=True)
            ],
        }
        public_path = root / "blind.public.jsonl"
        labels_path = root / "blind.labels.jsonl"
        public_bytes = _jsonl_bytes([public_row])
        labels_bytes = _jsonl_bytes([label_row])
        public_path.write_bytes(public_bytes)
        labels_path.write_bytes(labels_bytes)
        receipt = {
            "schema_version": "lemma-portfolio.dependency-compression-generation.v4",
            "source": {
                "dataset_version": "v4.33.0",
                "mathlib_commit": lean_common.PINNED_MATHLIB_COMMIT,
            },
            "outputs": {
                "blind_public_sha256": hashlib.sha256(public_bytes).hexdigest(),
                "blind_labels_commitment_sha256": hashlib.sha256(labels_bytes).hexdigest(),
            },
        }
        receipt_path = root / "generation_receipt.json"
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        manifest = {
            "schema_version": "lemma-portfolio.dependency-compression-manifest.v4",
            "generation_receipt": {
                "sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest()
            },
            "splits": {
                "blind": {
                    "benchmark_id": "fixture.v4",
                    "episodes": 1,
                    "public_sha256": hashlib.sha256(public_bytes).hexdigest(),
                    "label_commitment_sha256": hashlib.sha256(labels_bytes).hexdigest(),
                }
            },
        }
        manifest_path = root / "manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        return manifest_path, receipt_path, public_path, labels_path

    def test_hash_bound_corpus_and_mutated_label_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = self._fixture(Path(directory))
            corpus = lean_v4.load_corpus(
                manifest_path=paths[0], generation_receipt_path=paths[1],
                public_path=paths[2], labels_path=paths[3], split="blind",
            )
            self.assertEqual(len(corpus.labels), 1)
            paths[3].write_bytes(paths[3].read_bytes() + b"\n")
            with self.assertRaises(lean_v4.V4PinnedLeanAuditError):
                lean_v4.load_corpus(
                    manifest_path=paths[0], generation_receipt_path=paths[1],
                    public_path=paths[2], labels_path=paths[3], split="blind",
                )

    def test_mutated_commitment_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = self._fixture(Path(directory))
            manifest = json.loads(paths[0].read_text())
            manifest["splits"]["blind"]["public_sha256"] = "0" * 64
            paths[0].write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(lean_v4.V4PinnedLeanAuditError):
                lean_v4.load_corpus(
                    manifest_path=paths[0], generation_receipt_path=paths[1],
                    public_path=paths[2], labels_path=paths[3], split="blind",
                )

    def test_mutated_edge_aggregate_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = self._fixture(Path(directory))
            corpus = lean_v4.load_corpus(
                manifest_path=paths[0], generation_receipt_path=paths[1],
                public_path=paths[2], labels_path=paths[3], split="blind",
            )
            aggregate = {key: 0 for key in lean_v4.AGGREGATE_KEYS}
            aggregate.update(
                {
                    "reports": 8,
                    "candidate_declarations": 16,
                    "target_declarations": 8,
                    "old_edges": 8,
                    "direct_value_edges": 9,
                    "added_edges": 1,
                    "candidate_theorem_declarations": 16,
                    "target_theorem_declarations": 8,
                }
            )
            with self.assertRaises(lean_v4.V4PinnedLeanAuditError):
                lean_v4.verify_aggregate(corpus, aggregate)

    def test_invalid_environment_fails_closed(self) -> None:
        missing = Path("/definitely/missing/lemma-portfolio-v4")
        with self.assertRaises(lean_common.AuditError):
            lean_v4.verify_environment(
                mathlib_checkout=missing,
                lean_project=missing,
                lake=missing,
                elan_home=None,
            )


if __name__ == "__main__":
    unittest.main()
