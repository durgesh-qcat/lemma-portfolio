#!/usr/bin/env python3
"""Run the immutable submitted checks with a narrow Python float compatibility fix.

Python 3.10 can compute 79.99999999999999 for an archived continuous metric
serialized as integer 80. The archive's comparator tolerates float roundoff only
when the saved value is a float. This runner applies that existing tolerance to
that one metric in memory; submitted files and their hashes remain unchanged.
"""

import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import runpy
import subprocess
import sys


DEFAULT_SUPPLEMENT = Path(__file__).resolve().parents[1] / "submission/LemmaPortfolio_supplement"
CONTINUOUS_METRIC = "mean_oracle_normalized_coverage_percentage"
CHECKS = (
    "original_release/verify_release.py",
    "verify_followups.py",
    "evaluation/verify_evaluation.py",
    "verify_descriptive.py",
    "verify_results.py",
    "verify_masking_sensitivity.py",
    "verify_selection_patterns.py",
)


def compatible_comparison(original):
    """Keep the archive's comparison, except this one integer-encoded metric."""
    def same(actual, expected, location):
        if isinstance(actual, bool) or isinstance(expected, bool):
            if type(actual) is not type(expected) or actual != expected:
                raise RuntimeError(f"Boolean mismatch: {location}")
            return
        if (type(actual) is float and type(expected) is int
                and location.rsplit("/", 1)[-1] == CONTINUOUS_METRIC):
            if not math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-10):
                raise RuntimeError(f"Numerical mismatch: {location}")
            return
        return original(actual, expected, location)
    return same


def run_checks(supplement_root=DEFAULT_SUPPLEMENT, paper=None):
    if sys.version_info < (3, 10):
        raise RuntimeError("Python 3.10 or newer is required")
    root = Path(supplement_root).resolve()
    paper = Path(paper).resolve() if paper is not None else None
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    saved_path = list(sys.path)
    saved_argv = sys.argv
    saved_bytecode = sys.dont_write_bytecode
    module_names = ("verify_followups", "verify_results")
    saved_modules = {name: sys.modules.get(name) for name in module_names}
    try:
        sys.path.insert(0, str(root))
        sys.dont_write_bytecode = True
        for name in module_names:
            sys.modules.pop(name, None)
        spec = importlib.util.spec_from_file_location("verify_followups", root / "verify_followups.py")
        followups = importlib.util.module_from_spec(spec)
        sys.modules["verify_followups"] = followups
        spec.loader.exec_module(followups)
        # The original recursive function resolves `same` in this module's
        # globals, so nested comparisons also pass through the narrow wrapper.
        followups.same = compatible_comparison(followups.same)
        for script in CHECKS:
            print(f"\nChecking {script}", flush=True)
            if script in ("original_release/verify_release.py", "evaluation/verify_evaluation.py"):
                subprocess.run([sys.executable, "-B", str(root / script)],
                               cwd=root, env=environment, check=True)
            elif script == "verify_followups.py":
                followups.verify()
            else:
                sys.argv = [str(root / script)]
                runpy.run_path(str(root / script), run_name="__main__")
        if paper is not None:
            manifest = json.loads((root / "MANIFEST.json").read_text(encoding="utf-8"))
            if hashlib.sha256(paper.read_bytes()).hexdigest() != manifest["accompanying_paper"]["sha256"]:
                raise RuntimeError("The supplied PDF is not the paper paired with this archive")
            print("PASS accompanying paper PDF hash")
    finally:
        sys.path[:] = saved_path
        sys.argv = saved_argv
        sys.dont_write_bytecode = saved_bytecode
        for name, previous in saved_modules.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous
    print("\nALL SUBMISSION CHECKS PASSED. No network access or model calls were used.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--supplement-root", type=Path, default=DEFAULT_SUPPLEMENT)
    parser.add_argument("--paper", type=Path, help="also verify the accompanying PDF's SHA-256")
    args = parser.parse_args(argv)
    run_checks(args.supplement_root, args.paper)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
