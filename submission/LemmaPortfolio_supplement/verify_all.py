#!/usr/bin/env python3
"""Verify the supplementary packet offline; optionally identify its paper PDF."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper", type=Path, help="also verify the accompanying final PDF's SHA-256")
    args = parser.parse_args()
    if sys.version_info < (3, 10):
        raise RuntimeError("Python 3.10 or newer is required")
    root = Path(__file__).resolve().parent
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    for script in ("original_release/verify_release.py", "verify_followups.py", "evaluation/verify_evaluation.py",
                   "verify_descriptive.py", "verify_results.py", "verify_masking_sensitivity.py",
                   "verify_selection_patterns.py"):
        print(f"\nChecking {script}", flush=True)
        subprocess.run([sys.executable, "-B", str(root / script)], cwd=root, env=env, check=True)
    if args.paper:
        manifest = json.loads((root / "MANIFEST.json").read_text(encoding="utf-8"))
        actual = hashlib.sha256(args.paper.read_bytes()).hexdigest()
        if actual != manifest["accompanying_paper"]["sha256"]:
            raise RuntimeError("The supplied PDF is not the paper paired with this archive")
        print("PASS accompanying paper PDF hash")
    print("\nALL SUBMISSION CHECKS PASSED. No network access or model calls were used.")


if __name__ == "__main__":
    main()
