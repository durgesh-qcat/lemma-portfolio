#!/usr/bin/env python3
"""Replay the descriptive replacement-distance audit from packet files only."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from verify_followups import ROOT, read, same, verify


def main():
    verify()
    descriptive = ROOT / "descriptive"
    with tempfile.TemporaryDirectory(prefix="lemma-portfolio-distances-") as directory:
        repository = Path(directory) / "repo"
        repository.mkdir()
        shutil.copytree(ROOT / "original_release/data", repository / "data")
        shutil.copytree(ROOT / "followups", repository / "followups",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        for source in sorted((descriptive / "source_records").glob("*.json")):
            # Restore exact original numerical records in the temporary tree.
            # Final-answer bytes and this packet's projected scores stay unchanged.
            shutil.copyfile(source, repository / "followups/2026-09-05" /
                            source.stem / "score.json")
        completed = subprocess.run(
            [sys.executable, str(descriptive / "one_short_replacement_audit.py"),
             "--repo-root", str(repository)],
            check=True, capture_output=True, text=True,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        same(json.loads(completed.stdout),
             read(descriptive / "one_short_replacement_audit.json"),
             "Descriptive replacement-distance audit")
    print("PASS descriptive audit: all seven runs, distances, neighbor counts, source hashes, and per-item records reproduced")
    print("No repair rule, inference call, or improvement experiment was performed.")


if __name__ == "__main__":
    main()
