from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from tools.score_release import BENCHMARK_ID, load_benchmark
from tools.score_support_predictions import (
    InvalidSupportFileError,
    SupportInputError,
    expected_support_episode_ids,
    main,
    merge_support_shards,
    score_external_support,
)


ROOT = Path(__file__).resolve().parents[1]


class ExternalSupportScorerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.public, cls.labels = load_benchmark(ROOT)
        cls.episode_ids = expected_support_episode_ids(ROOT, cls.public)
        cls.published_support = json.loads(
            (ROOT / "responses/support_transcription.json").read_text(encoding="utf-8")
        )

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.temp = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def write_json(self, name: str, value: object) -> Path:
        path = self.temp / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_prompt_packet_defines_fixed_twenty_episode_denominator(self) -> None:
        self.assertEqual(len(self.episode_ids), 20)
        self.assertEqual(len(set(self.episode_ids)), 20)
        self.assertEqual(self.episode_ids[:5], [f"MLP4B_{i:04d}" for i in range(15, 20)])
        self.assertEqual(self.episode_ids[-5:], [f"MLP4B_{i:04d}" for i in range(55, 60)])

    def test_reproduces_published_pro_structured_result(self) -> None:
        path = self.write_json(
            "pro-support.json",
            {
                "benchmark_id": BENCHMARK_ID,
                "system_id": "gpt_sol_5_6_pro",
                "display_label": "GPT SOL 5.6 Pro",
                "predicted_support": self.published_support["gpt_sol_5_6_pro"],
            },
        )

        report = score_external_support([path], ROOT)

        self.assertEqual(report["summary"]["exact_optimal"], 1)
        self.assertEqual(report["summary"]["achieved_target_coverage"], 92)
        self.assertEqual(report["summary"]["valid"], 20)
        self.assertEqual(report["summary"]["total"], 20)
        self.assertEqual(report["support_full"]["true_positive"], 208)
        self.assertEqual(report["support_q2"]["true_positive"], 189)
        self.assertEqual(report["support_q2"]["false_positive"], 57)
        self.assertEqual(report["support_q2"]["false_negative"], 86)

    def test_missing_and_malformed_episode_values_score_zero(self) -> None:
        first, second = self.episode_ids[:2]
        path = self.write_json(
            "partial.json",
            {
                first: self.published_support["gpt_sol_5_6_pro"][first],
                second: {"T01": ["C01"]},
            },
        )

        report = score_external_support([path], ROOT)

        self.assertEqual(report["summary"]["total"], 20)
        self.assertEqual(report["summary"]["valid"], 1)
        self.assertEqual(report["missing_episode_count"], 18)
        self.assertEqual(report["malformed_episode_count"], 1)
        rows = {row["episode_id"]: row for row in report["per_item"]}
        self.assertEqual(rows[second]["input_status"], "malformed")
        self.assertEqual(rows[second]["coverage"], 0)
        self.assertEqual(rows[self.episode_ids[-1]]["input_status"], "missing")

    def test_ranked_list_constraints_are_enforced_per_episode(self) -> None:
        episode_id = self.episode_ids[0]
        malformed = dict(self.published_support["gpt_sol_5_6_pro"][episode_id])
        malformed["T01"] = ["C01", "C01"]
        path = self.write_json("duplicate-candidate.json", {episode_id: malformed})

        report = score_external_support([path], ROOT)

        self.assertEqual(report["summary"]["valid"], 0)
        self.assertEqual(report["malformed_episode_ids"], [episode_id])

    def test_duplicate_and_unknown_episode_ids_are_rejected(self) -> None:
        episode_id = self.episode_ids[0]
        support = self.published_support["gpt_sol_5_6_pro"][episode_id]
        first = self.write_json("first.json", {episode_id: support})
        second = self.write_json("second.json", {episode_id: support})
        with self.assertRaisesRegex(SupportInputError, "duplicate episode ID"):
            merge_support_shards([first, second], set(self.episode_ids))

        unknown = self.write_json("unknown.json", {"MLP4B_0000": support})
        with self.assertRaisesRegex(SupportInputError, "unknown structured-support"):
            merge_support_shards([unknown], set(self.episode_ids))

    def test_invalid_source_files_are_strict_or_explicitly_skipped(self) -> None:
        episode_id = self.episode_ids[0]
        valid = self.write_json(
            "valid.json",
            {episode_id: self.published_support["gpt_sol_5_6_pro"][episode_id]},
        )
        invalid = self.temp / "raw-response.txt"
        invalid.write_text("```json\nnot valid JSON\n```", encoding="utf-8")
        non_object = self.write_json("array.json", ["C01", "C02"])
        bad_wrapper = self.write_json("bad-wrapper.json", {"predicted_support": []})
        unreadable = self.temp / "does-not-exist.json"
        with self.assertRaises(InvalidSupportFileError):
            score_external_support([invalid], ROOT)

        report = score_external_support(
            [valid, invalid, non_object, bad_wrapper, unreadable],
            ROOT,
            invalid_as_missing=True,
        )
        self.assertEqual(report["invalid_source_file_count"], 4)
        self.assertEqual(
            [row["path"] for row in report["invalid_source_files"]],
            [
                "raw-response.txt",
                "array.json",
                "bad-wrapper.json",
                "does-not-exist.json",
            ],
        )
        self.assertNotIn(str(self.temp), json.dumps(report))
        self.assertEqual(report["missing_episode_count"], 19)
        self.assertEqual(report["summary"]["valid"], 1)

    def test_invalid_as_missing_keeps_alignment_errors_hard(self) -> None:
        episode_id = self.episode_ids[0]
        support = self.published_support["gpt_sol_5_6_pro"][episode_id]

        duplicate_key = self.temp / "duplicate-key.json"
        duplicate_key.write_text(
            json.dumps({episode_id: support})[:-1]
            + ","
            + json.dumps(episode_id)
            + ":"
            + json.dumps(support)
            + "}",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(SupportInputError, "duplicate JSON key"):
            score_external_support(
                [duplicate_key], ROOT, invalid_as_missing=True
            )

        unknown = self.write_json("unknown-tolerant.json", {"MLP4B_0000": support})
        with self.assertRaisesRegex(SupportInputError, "unknown structured-support"):
            score_external_support([unknown], ROOT, invalid_as_missing=True)

        first = self.write_json("duplicate-first.json", {episode_id: support})
        second = self.write_json("duplicate-second.json", {episode_id: support})
        with self.assertRaisesRegex(SupportInputError, "duplicate episode ID"):
            score_external_support(
                [first, second], ROOT, invalid_as_missing=True
            )

    def test_cli_writes_complete_json_report(self) -> None:
        path = self.write_json(
            "support.json",
            {"predicted_support": self.published_support["gpt_sol_5_6_xhigh"]},
        )
        output = self.temp / "score.json"
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            status = main(
                [
                    "--supports",
                    str(path),
                    "--release-root",
                    str(ROOT),
                    "--display-label",
                    "Unit Test Support",
                    "--output",
                    str(output),
                ]
            )

        self.assertEqual(status, 0)
        self.assertIn("Exact optimal portfolios: 0/20", stdout.getvalue())
        report = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(report["summary"]["total"], 20)
        self.assertEqual(len(report["per_item"]), 20)


if __name__ == "__main__":
    unittest.main()
