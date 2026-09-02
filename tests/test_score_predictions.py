from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from tools.score_predictions import (
    PredictionInputError,
    main,
    merge_prediction_shards,
    score_external_predictions,
)
from tools.score_release import BENCHMARK_ID, load_benchmark


ROOT = Path(__file__).resolve().parents[1]


class ExternalPredictionScorerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.public, cls.labels = load_benchmark(ROOT)
        cls.episode_ids = list(cls.public)

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.temp = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def write_json(self, name: str, value: object) -> Path:
        path = self.temp / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def optimum(self, episode_id: str) -> list[str]:
        return list(sorted(next(iter(self.labels[episode_id]["optimal_portfolios"]))))

    def test_raw_and_wrapped_shards_merge_with_fixed_denominator(self) -> None:
        first, second = self.episode_ids[:2]
        raw = self.write_json("raw.json", {first: self.optimum(first)})
        wrapped = self.write_json(
            "wrapped.json",
            {
                "benchmark_id": BENCHMARK_ID,
                "system_id": "unit_test_model",
                "display_label": "Unit Test Model",
                "predictions": {second: self.optimum(second)},
            },
        )

        report = score_external_predictions([raw, wrapped], ROOT)

        self.assertEqual(report["summary"]["total"], 60)
        self.assertEqual(report["summary"]["exact_optimal"], 2)
        self.assertEqual(report["summary"]["valid"], 2)
        self.assertEqual(report["missing_episode_count"], 58)
        self.assertEqual(report["malformed_episode_count"], 0)
        self.assertEqual(report["summary"]["system_id"], "unit_test_model")

    def test_malformed_rows_are_zero_and_never_crash(self) -> None:
        first, second, third, fourth = self.episode_ids[:4]
        predictions = self.write_json(
            "malformed.json",
            {
                first: self.optimum(first),
                second: [["C01"], "C02", "C03"],
                third: ["C01", "C01", "C02"],
                fourth: ["C01", "C02", "C99"],
            },
        )

        report = score_external_predictions([predictions], ROOT)

        self.assertEqual(report["summary"]["total"], 60)
        self.assertEqual(report["summary"]["exact_optimal"], 1)
        self.assertEqual(report["summary"]["valid"], 1)
        self.assertEqual(report["malformed_episode_count"], 3)
        self.assertEqual(report["missing_episode_count"], 56)
        rows = {row["episode_id"]: row for row in report["per_item"]}
        self.assertEqual(rows[second]["coverage"], 0)
        self.assertEqual(rows[second]["input_status"], "malformed")
        self.assertEqual(rows[self.episode_ids[-1]]["input_status"], "missing")

    def test_duplicate_episode_across_shards_is_rejected(self) -> None:
        episode_id = self.episode_ids[0]
        first = self.write_json("first.json", {episode_id: ["C01", "C02", "C03"]})
        second = self.write_json(
            "second.json",
            {"predictions": {episode_id: ["C04", "C05", "C06"]}},
        )
        with self.assertRaisesRegex(PredictionInputError, "duplicate episode ID"):
            merge_prediction_shards([first, second], set(self.episode_ids))

    def test_unknown_episode_is_rejected(self) -> None:
        path = self.write_json("unknown.json", {"MLP4B_9999": ["C01", "C02", "C03"]})
        with self.assertRaisesRegex(PredictionInputError, "unknown episode ID"):
            merge_prediction_shards([path], set(self.episode_ids))

    def test_duplicate_json_key_is_rejected(self) -> None:
        episode_id = self.episode_ids[0]
        path = self.temp / "duplicate-key.json"
        path.write_text(
            '{"%s":["C01","C02","C03"],"%s":["C04","C05","C06"]}'
            % (episode_id, episode_id),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(PredictionInputError, "duplicate JSON key"):
            merge_prediction_shards([path], set(self.episode_ids))

    def test_invalid_source_files_are_strict_by_default(self) -> None:
        path = self.temp / "prose.txt"
        path.write_text("The model selected C01, C02, and C03.", encoding="utf-8")

        with self.assertRaisesRegex(PredictionInputError, "cannot read"):
            score_external_predictions([path], ROOT)

    def test_invalid_as_missing_records_and_skips_unusable_sources(self) -> None:
        episode_id = self.episode_ids[0]
        valid = self.write_json("valid.json", {episode_id: self.optimum(episode_id)})
        prose = self.temp / "prose.txt"
        prose.write_text(
            '```json\n{"predictions": {"MLP4B_0001": ["C01", "C02", "C03"]}}\n```',
            encoding="utf-8",
        )
        non_object = self.write_json("array.json", ["C01", "C02", "C03"])
        unreadable = self.temp / "does-not-exist.json"

        report = score_external_predictions(
            [valid, prose, non_object, unreadable],
            ROOT,
            invalid_as_missing=True,
        )

        self.assertEqual(report["summary"]["exact_optimal"], 1)
        self.assertEqual(report["summary"]["valid"], 1)
        self.assertEqual(report["summary"]["total"], 60)
        self.assertEqual(report["missing_episode_count"], 59)
        self.assertEqual(report["invalid_source_file_count"], 3)
        self.assertEqual(
            [row["path"] for row in report["invalid_source_files"]],
            ["prose.txt", "array.json", "does-not-exist.json"],
        )
        self.assertNotIn(str(self.temp), json.dumps(report))

    def test_invalid_as_missing_keeps_unknown_and_duplicate_ids_hard(self) -> None:
        episode_id = self.episode_ids[0]
        unknown = self.write_json(
            "unknown-tolerant.json", {"MLP4B_9999": ["C01", "C02", "C03"]}
        )
        with self.assertRaisesRegex(PredictionInputError, "unknown episode ID"):
            score_external_predictions([unknown], ROOT, invalid_as_missing=True)

        first = self.write_json(
            "duplicate-first.json", {episode_id: ["C01", "C02", "C03"]}
        )
        second = self.write_json(
            "duplicate-second.json", {episode_id: ["C04", "C05", "C06"]}
        )
        with self.assertRaisesRegex(PredictionInputError, "duplicate episode ID"):
            score_external_predictions([first, second], ROOT, invalid_as_missing=True)

    def test_cli_invalid_as_missing_writes_audited_zero_score(self) -> None:
        source = self.temp / "raw-response.txt"
        source.write_text("I choose C01, C02, C03.", encoding="utf-8")
        output = self.temp / "invalid-score.json"
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            status = main(
                [
                    "--predictions",
                    str(source),
                    "--release-root",
                    str(ROOT),
                    "--invalid-as-missing",
                    "--output",
                    str(output),
                ]
            )

        self.assertEqual(status, 0)
        self.assertIn("Invalid source files skipped: 1", stdout.getvalue())
        report = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(report["invalid_source_file_count"], 1)
        self.assertEqual(report["missing_episode_count"], 60)
        self.assertEqual(report["summary"]["exact_optimal"], 0)

    def test_cli_writes_full_json_report(self) -> None:
        episode_id = self.episode_ids[0]
        predictions = self.write_json(
            "predictions.json", {episode_id: self.optimum(episode_id)}
        )
        output = self.temp / "nested" / "score.json"
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            status = main(
                [
                    "--predictions",
                    str(predictions),
                    "--release-root",
                    str(ROOT),
                    "--output",
                    str(output),
                ]
            )

        self.assertEqual(status, 0)
        self.assertIn("Exact optimal portfolios: 1/60", stdout.getvalue())
        report = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(report["summary"]["total"], 60)
        self.assertEqual(len(report["per_item"]), 60)

    def test_reproduces_published_pro_score_from_canonical_transcription(self) -> None:
        transcriptions = json.loads(
            (ROOT / "responses/direct_transcription.json").read_text(encoding="utf-8")
        )
        predictions = self.write_json(
            "published-pro.json", transcriptions["gpt_sol_5_6_pro"]
        )

        report = score_external_predictions([predictions], ROOT)

        self.assertEqual(report["summary"]["exact_optimal"], 25)
        self.assertEqual(report["summary"]["achieved_target_coverage"], 299)
        self.assertEqual(report["summary"]["valid"], 55)
        self.assertEqual(report["summary"]["total"], 60)


if __name__ == "__main__":
    unittest.main()
