#!/usr/bin/env python3
"""One-command integrity and score check for the LemmaPortfolio V4 release."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parent
GENERATED = (
    "responses/direct_transcription.json",
    "responses/support_transcription.json",
    "responses/alignment_audit.json",
    "results/baseline_predictions.json",
    "results/scores.json",
    "results/structured_comparison.json",
    "results/per_item.jsonl",
    "results/development_score.json",
    "results/development_per_item.jsonl",
)
EXPECTED_EXACT = {
    "gpt_sol_5_6_pro": (25, 60, 55),
    "deepseek_instant_deepthink": (1, 60, 60),
    "deepseek_expert_deepthink": (7, 60, 60),
    "qwen_3_8_max_thinking": (12, 60, 55),
    "qwen_3_7_plus_thinking": (6, 60, 60),
}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def check_manifest() -> None:
    manifest = ROOT / "SHA256SUMS"
    if not manifest.is_file():
        raise RuntimeError("SHA256SUMS is missing")
    declared = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        if relative in declared or relative.startswith("/") or ".." in Path(relative).parts:
            raise RuntimeError(f"unsafe or duplicate manifest path: {relative}")
        declared[relative] = expected
    actual = {
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*")
        if path.is_file()
        and path.name != "SHA256SUMS"
        and ".git" not in path.relative_to(ROOT).parts
        and "__pycache__" not in path.relative_to(ROOT).parts
    }
    if set(declared) != actual:
        missing = sorted(actual - set(declared))
        extra = sorted(set(declared) - actual)
        raise RuntimeError(f"manifest file set differs; missing={missing}, extra={extra}")
    for relative, expected in declared.items():
        if digest(ROOT / relative) != expected:
            raise RuntimeError(f"hash mismatch: {relative}")


def check_hygiene() -> None:
    forbidden_names = re.compile(r"(^|[._-])(credential|secret|token|auth)([._-]|$)", re.I)
    secret_patterns = [
        re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        re.compile(rb"gh[opusr]_[A-Za-z0-9]{20,}"),
        re.compile(rb"sk-[A-Za-z0-9_-]{20,}"),
        re.compile(rb"AKIA[0-9A-Z]{16}"),
    ]
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.relative_to(ROOT).parts:
            continue
        if forbidden_names.search(path.name) and path.name != "dataset_commitment.json":
            raise RuntimeError(f"credential-like filename: {path.relative_to(ROOT)}")
        if path.suffix.lower() in {".pdf", ".zip", ".png", ".jpg", ".jpeg"}:
            continue
        payload = path.read_bytes()
        for pattern in secret_patterns:
            if pattern.search(payload):
                raise RuntimeError(f"possible secret in {path.relative_to(ROOT)}")


def regenerate_and_compare() -> None:
    with tempfile.TemporaryDirectory(prefix="lemma_portfolio_verify_") as temporary:
        output = Path(temporary)
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools/score_release.py"),
                "--release-root",
                str(ROOT),
                "--output-root",
                str(output),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        for relative in GENERATED:
            if (output / relative).read_bytes() != (ROOT / relative).read_bytes():
                raise RuntimeError(f"regenerated result differs: {relative}")


def check_construction_tests() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "unittest",
            "apibench.hard_blind_v4.test_hard_blind_v4",
        ],
        cwd=ROOT / "construction",
        text=True,
        capture_output=True,
    )
    if completed.returncode:
        detail = (completed.stderr or completed.stdout)[-2000:]
        raise RuntimeError(f"construction tests failed:\n{detail}")


def check_headlines() -> None:
    report = json.loads((ROOT / "results/scores.json").read_text(encoding="utf-8"))
    rows = {row["system_id"]: row for row in report["rows"]}
    for system_id, expected in EXPECTED_EXACT.items():
        row = rows[system_id]
        observed = (row["exact_optimal"], row["total"], row["valid"])
        if observed != expected:
            raise RuntimeError(f"headline differs for {system_id}: {observed}")
    structured = report["structured_row"]
    if (structured["exact_optimal"], structured["total"]) != (1, 20):
        raise RuntimeError("structured diagnostic headline differs")
    development = json.loads(
        (ROOT / "results/development_score.json").read_text(encoding="utf-8")
    )["row"]
    if (
        development["exact_optimal"],
        development["total"],
        development["valid"],
    ) != (6, 15, 15):
        raise RuntimeError("development-check headline differs")
    for tex in ROOT.glob("paper/**/*.tex"):
        if b"RESULTS PENDING" in tex.read_bytes():
            raise RuntimeError(f"pending-result sentinel in {tex.relative_to(ROOT)}")
    results_tex = (ROOT / "paper/source/generated/results_section.tex").read_text(
        encoding="utf-8"
    )
    for expected in (
        "25/60 (41.7)",
        "1/60 (1.7)",
        "7/60 (11.7)",
        "12/60 (20.0)",
        "6/60 (10.0)",
        "299 of the 480",
    ):
        if expected not in results_tex:
            raise RuntimeError(f"paper result is absent or stale: {expected}")
    body_tex = (ROOT / "paper/source/body.tex").read_text(encoding="utf-8")
    if "6/15 exact optima" not in body_tex:
        raise RuntimeError("paper development-check result is absent or stale")


def main() -> int:
    if sys.version_info < (3, 10):
        raise RuntimeError("Python 3.10 or newer is required")
    check_manifest()
    check_hygiene()
    check_construction_tests()
    regenerate_and_compare()
    check_headlines()
    report = json.loads((ROOT / "results/scores.json").read_text(encoding="utf-8"))
    print("Verified exact-optimum scores:")
    for row in report["rows"]:
        if row["system_id"] in EXPECTED_EXACT:
            print(
                f"  {row['display_label']}: {row['exact_optimal']}/{row['total']} "
                f"(valid {row['valid']}/{row['total']})"
            )
    print("  GPT SOL support q=2: 1/20")
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"VERIFICATION FAILED: {error}", file=sys.stderr)
        raise SystemExit(1)
