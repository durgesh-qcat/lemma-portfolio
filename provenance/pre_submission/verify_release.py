#!/usr/bin/env python3
"""One-command integrity and score check for the LemmaPortfolio V4 release."""

from __future__ import annotations

import hashlib
import json
import math
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
    "results/xhigh_structured_comparison.json",
    "results/per_item.jsonl",
    "results/development_score.json",
    "results/development_per_item.jsonl",
)
EXPECTED_EXACT = {
    "gpt_sol_5_6_pro": (25, 60, 55),
    "gpt_sol_5_6_xhigh": (18, 60, 60),
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


def check_prompt_packet() -> None:
    """Verify exact prompt bytes and their closure over the released public rows."""

    prompt_root = ROOT / "prompts"
    manifest = prompt_root / "PROMPT_SHA256SUMS.txt"
    declared: dict[str, str] = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        if relative in declared or relative.startswith("/") or ".." in Path(relative).parts:
            raise RuntimeError(f"unsafe or duplicate prompt-manifest path: {relative}")
        declared[relative] = expected
    actual = {
        path.relative_to(prompt_root).as_posix()
        for directory in ("DIRECT_PROMPTS", "SOL_EXTRA_PROMPTS")
        for path in (prompt_root / directory).glob("*.txt")
    }
    if set(declared) != actual:
        raise RuntimeError("prompt checksum manifest does not cover the prompt packet exactly")
    for relative, expected in declared.items():
        if digest(prompt_root / relative) != expected:
            raise RuntimeError(f"prompt hash mismatch: {relative}")

    public_rows = [
        json.loads(line)
        for line in (ROOT / "data/test.public.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    direct_rows = []
    for path in sorted((prompt_root / "DIRECT_PROMPTS").glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        try:
            payload = text.split("<episodes>\n", 1)[1].split("\n</episodes>", 1)[0]
            rows = json.loads(payload)
        except (IndexError, json.JSONDecodeError) as error:
            raise RuntimeError(f"cannot parse episode payload in {path.name}") from error
        if not isinstance(rows, list) or len(rows) != 5:
            raise RuntimeError(f"direct prompt {path.name} does not contain five episodes")
        direct_rows.extend(rows)
    if direct_rows != public_rows:
        raise RuntimeError("the twelve direct prompts differ from the 60 public rows")

    structured_rows = []
    for path in sorted((prompt_root / "SOL_EXTRA_PROMPTS").glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        try:
            payload = text.split("<episodes>\n", 1)[1].split("\n</episodes>", 1)[0]
            rows = json.loads(payload)
        except (IndexError, json.JSONDecodeError) as error:
            raise RuntimeError(f"cannot parse episode payload in {path.name}") from error
        if not isinstance(rows, list) or len(rows) != 5:
            raise RuntimeError(f"structured prompt {path.name} does not contain five episodes")
        structured_rows.extend(rows)
    structured_ids = [row.get("episode_id") for row in structured_rows]
    if len(structured_ids) != 20 or len(set(structured_ids)) != 20:
        raise RuntimeError("the four structured prompts do not contain 20 unique episodes")
    public_by_id = {row["episode_id"]: row for row in public_rows}
    for row in structured_rows:
        public_row = public_by_id.get(row.get("episode_id"))
        if public_row is None:
            raise RuntimeError("a structured prompt contains an unknown episode")
        prompt_copy = dict(row)
        public_copy = dict(public_row)
        prompt_task = prompt_copy.pop("task", None)
        public_copy.pop("task", None)
        if prompt_copy != public_copy or not isinstance(prompt_task, str):
            raise RuntimeError(
                "a structured prompt row differs from the public row beyond its task"
            )


def equivalent_generated(left: object, right: object) -> bool:
    """Compare generated JSON exactly except for harmless last-bit floats."""

    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if isinstance(left, int) or isinstance(right, int):
        return type(left) is type(right) and left == right
    if isinstance(left, float) and isinstance(right, float):
        return math.isfinite(left) and math.isfinite(right) and math.isclose(
            left, right, rel_tol=1e-12, abs_tol=1e-12
        )
    if isinstance(left, dict) and isinstance(right, dict):
        return set(left) == set(right) and all(
            equivalent_generated(left[key], right[key]) for key in left
        )
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(
            equivalent_generated(left_item, right_item)
            for left_item, right_item in zip(left, right)
        )
    return type(left) is type(right) and left == right


def load_generated(path: Path) -> object:
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    return json.loads(path.read_text(encoding="utf-8"))


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
            regenerated = output / relative
            released = ROOT / relative
            if regenerated.read_bytes() == released.read_bytes():
                continue
            if not equivalent_generated(
                load_generated(regenerated), load_generated(released)
            ):
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


def check_external_scorer_tests() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if completed.returncode:
        detail = (completed.stderr or completed.stdout)[-2000:]
        raise RuntimeError(f"external prediction scorer tests failed:\n{detail}")


def check_headlines() -> None:
    report = json.loads((ROOT / "results/scores.json").read_text(encoding="utf-8"))
    rows = {row["system_id"]: row for row in report["rows"]}
    for system_id, expected in EXPECTED_EXACT.items():
        row = rows[system_id]
        observed = (row["exact_optimal"], row["total"], row["valid"])
        if observed != expected:
            raise RuntimeError(f"headline differs for {system_id}: {observed}")
    structured = {row["system_id"]: row for row in report["structured_rows"]}
    expected_structured = {
        "gpt_sol_5_6_pro_support_q2": (1, 20),
        "gpt_sol_5_6_xhigh_support_q2": (0, 20),
    }
    for system_id, expected in expected_structured.items():
        observed = (structured[system_id]["exact_optimal"], structured[system_id]["total"])
        if observed != expected:
            raise RuntimeError(f"structured diagnostic headline differs: {system_id}")
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
        "18/60 (30.0)",
        "1/60 (1.7)",
        "7/60 (11.7)",
        "12/60 (20.0)",
        "6/60 (10.0)",
        "299 of the 480",
        "305 of 480",
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
    check_prompt_packet()
    check_construction_tests()
    check_external_scorer_tests()
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
    print("  GPT SOL 5.6 Pro support q=2: 1/20")
    print("  GPT SOL 5.6 (xhigh) support q=2: 0/20")
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"VERIFICATION FAILED: {error}", file=sys.stderr)
        raise SystemExit(1)
