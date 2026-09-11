"""Regression tests for binding the submitted PDF, ZIP, and usable copies."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from verify_release import check_submitted_artifacts


class SubmittedArtifactTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.supplement = self.root / "submission/LemmaPortfolio_supplement"
        self.paper = self.write("paper/LemmaPortfolio.pdf", b"%PDF-1.4\nfixture paper\n")
        self.write("submission/LemmaPortfolio_supplement/MANIFEST.json", json.dumps({
            "accompanying_paper": {"title": "Fixture paper", "sha256": self.sha(self.paper)}
        }).encode())
        for name, payload in {
            "data/test.public.jsonl": b'{"episode_id":"fixture"}\n',
            "data/test.labels.jsonl": b'{"episode_id":"fixture","optimal_coverage":7}\n',
            "prompts/DIRECT_PROMPTS/01.txt": b"fixture prompt\n",
            "responses/direct_transcription.json": b'{"fixture":["C01","C02","C03"]}\n',
        }.items():
            self.write(name, payload)
            self.write("submission/LemmaPortfolio_supplement/original_release/" + name, payload)
        result = b'{"optimal":30,"episodes":60}\n'
        self.write("submission/LemmaPortfolio_supplement/results/paper_results.json", result)
        self.write("results/paper_results.json", result)
        self.archive_path = self.root / "submission/LemmaPortfolio_supplement.zip"
        self.rebuild_archive()

    @staticmethod
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def write(self, name, payload):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return path

    def save_record(self):
        self.write("submission/SUBMITTED_ARTIFACTS.json", json.dumps({
            "title": "Fixture paper",
            "artifacts": [
                {"path": p.relative_to(self.root).as_posix(),
                 "size_bytes": p.stat().st_size, "sha256": self.sha(p)}
                for p in (self.paper, self.archive_path)
            ],
            "result_mirrors": {
                "results/paper_results.json":
                    "submission/LemmaPortfolio_supplement/results/paper_results.json"
            },
        }).encode())

    def rebuild_archive(self, omit=None, extra=None):
        with zipfile.ZipFile(self.archive_path, "w") as archive:
            for path in sorted(self.supplement.rglob("*")):
                if path.is_file() and path.relative_to(self.supplement).as_posix() != omit:
                    archive.write(path, "LemmaPortfolio_supplement/" + path.relative_to(self.supplement).as_posix())
            if extra:
                archive.writestr(*extra)
        self.save_record()

    def test_exact_downloads_and_mirrors_pass(self):
        check_submitted_artifacts(self.root)

    def test_same_size_pdf_change_fails_artifact_hash(self):
        self.paper.write_bytes(self.paper.read_bytes().replace(b"fixture", b"changed"))
        with self.assertRaisesRegex(RuntimeError, "submitted artifact differs"):
            check_submitted_artifacts(self.root)

    def test_paper_pairing_checked_even_if_artifact_record_is_updated(self):
        self.paper.write_bytes(b"%PDF-1.4\nother paper\n")
        self.save_record()
        with self.assertRaisesRegex(RuntimeError, "paper and supplement are not paired"):
            check_submitted_artifacts(self.root)

    def test_modified_extracted_file_fails(self):
        (self.supplement / "results/paper_results.json").write_bytes(b"{}\n")
        with self.assertRaisesRegex(RuntimeError, "extracted supplement differs"):
            check_submitted_artifacts(self.root)

    def test_extra_extracted_file_fails(self):
        (self.supplement / "unsubmitted.txt").write_text("extra", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "file set differs"):
            check_submitted_artifacts(self.root)

    def test_missing_archive_member_fails_even_with_updated_archive_hash(self):
        self.rebuild_archive(omit="results/paper_results.json")
        with self.assertRaisesRegex(RuntimeError, "file set differs"):
            check_submitted_artifacts(self.root)

    def test_result_mirror_difference_fails(self):
        (self.root / "results/paper_results.json").write_bytes(b'{"optimal":60}\n')
        with self.assertRaisesRegex(RuntimeError, "final result mirror differs"):
            check_submitted_artifacts(self.root)

    def test_root_benchmark_data_difference_fails(self):
        (self.root / "data/test.labels.jsonl").write_bytes(b'{"optimal_coverage":8}\n')
        with self.assertRaisesRegex(RuntimeError, "root benchmark evidence differs"):
            check_submitted_artifacts(self.root)

    def test_parent_traversal_in_zip_is_rejected(self):
        self.rebuild_archive(extra=("LemmaPortfolio_supplement/../outside.txt", b"outside"))
        with self.assertRaisesRegex(RuntimeError, "unsafe submitted ZIP entry"):
            check_submitted_artifacts(self.root)
        self.assertFalse((self.root / "submission/outside.txt").exists())

    def test_symbolic_link_in_zip_is_rejected(self):
        link = zipfile.ZipInfo("LemmaPortfolio_supplement/link")
        link.create_system = 3
        link.external_attr = 0o120777 << 16
        self.rebuild_archive(extra=(link, b"../outside.txt"))
        with self.assertRaisesRegex(RuntimeError, "unsafe submitted ZIP entry"):
            check_submitted_artifacts(self.root)


if __name__ == "__main__":
    unittest.main()
