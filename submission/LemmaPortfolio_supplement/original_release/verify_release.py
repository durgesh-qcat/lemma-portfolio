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
EXPECTED_OPTIMAL = {
    "gpt_sol_5_6_pro": (25, 60, 55),
    "gpt_sol_5_6_xhigh": (18, 60, 60),
    "deepseek_instant_deepthink": (1, 60, 60),
    "deepseek_expert_deepthink": (7, 60, 60),
    "qwen_3_8_max_thinking": (12, 60, 55),
    "qwen_3_7_plus_thinking": (6, 60, 60),
}
EXPECTED_WITHIN_ONE = {
    "sha256_random_portfolio": (1, 60, 60),
    "public_text_char_tfidf_facility": (18, 60, 60),
    "gpt_sol_5_6_pro": (44, 60, 55),
    "gpt_sol_5_6_xhigh": (43, 60, 60),
    "deepseek_instant_deepthink": (19, 60, 60),
    "deepseek_expert_deepthink": (33, 60, 60),
    "qwen_3_8_max_thinking": (30, 60, 55),
    "qwen_3_7_plus_thinking": (23, 60, 60),
    "gpt_sol_5_6_pro_matched_direct": (11, 20, 15),
    "gpt_sol_5_6_pro_support_q2": (11, 20, 20),
    "gpt_sol_5_6_xhigh_matched_direct": (13, 20, 20),
    "gpt_sol_5_6_xhigh_support_q2": (7, 20, 20),
}
EXPECTED_MASKING_SENSITIVITY = {
    "gpt_sol_5_6_pro": (22, 274, 54),
    "gpt_sol_5_6_xhigh": (15, 277, 54),
    "deepseek_instant_deepthink": (1, 230, 54),
    "deepseek_expert_deepthink": (7, 252, 54),
    "qwen_3_8_max_thinking": (10, 238, 54),
    "qwen_3_7_plus_thinking": (3, 215, 54),
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
    if (ROOT / "paper/source/preprint.tex").exists():
        raise RuntimeError("named preprint entry point in anonymous review archive")
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


def check_name_prefix_scan() -> tuple[
    dict[str, tuple[int, int, int, int, int, int]], dict[str, set[str]]
]:
    """Recompute the disclosed post-hoc scan for residual source-name prefixes."""

    expected = {
        "test": (33, 25, 24, 6, 29, 4),
        "development": (5, 5, 5, 2, 4, 1),
    }
    observed: dict[str, tuple[int, int, int, int, int, int]] = {}
    affected: dict[str, set[str]] = {}
    for split in expected:
        public_rows = [
            json.loads(line)
            for line in (ROOT / f"data/{split}.public.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
        label_rows = {
            row["episode_id"]: row
            for row in (
                json.loads(line)
                for line in (ROOT / f"data/{split}.labels.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
                if line.strip()
            )
        }
        occurrences = 0
        source_statement_pairs: set[tuple[str, str, str]] = set()
        affected_source_names: set[str] = set()
        affected_episodes: set[str] = set()
        self_occurrences = 0
        cross_occurrences = 0
        for public in public_rows:
            episode_id = public["episode_id"]
            labels = label_rows[episode_id]
            sources = labels["candidate_sources"] | labels["target_sources"]
            statements = {
                row["id"]: row["statement"]
                for field in ("candidates", "targets")
                for row in public[field]
            }
            for source_id, source_name in sources.items():
                prefix = f"{source_name}."
                for statement_id, statement in statements.items():
                    count = statement.count(prefix)
                    if not count:
                        continue
                    occurrences += count
                    source_statement_pairs.add((episode_id, source_id, statement_id))
                    affected_source_names.add(source_name)
                    affected_episodes.add(episode_id)
                    if source_id == statement_id:
                        self_occurrences += count
                    else:
                        cross_occurrences += count
        result = (
            occurrences,
            len(source_statement_pairs),
            len(affected_source_names),
            len(affected_episodes),
            self_occurrences,
            cross_occurrences,
        )
        if result != expected[split]:
            raise RuntimeError(
                f"post-hoc source-name-prefix scan differs for {split}: "
                f"observed={result}, expected={expected[split]}"
            )
        observed[split] = result
        affected[split] = affected_episodes
    return observed, affected


def check_masking_sensitivity(excluded_episodes: set[str]) -> None:
    """Recompute the six reported 54-episode masking-sensitivity rows."""

    records = [
        json.loads(line)
        for line in (ROOT / "results/per_item.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    for system_id, expected in EXPECTED_MASKING_SENSITIVITY.items():
        retained = [
            row
            for row in records
            if row["system_id"] == system_id
            and row["episode_id"] not in excluded_episodes
        ]
        if len({row["episode_id"] for row in retained}) != len(retained):
            raise RuntimeError(f"duplicate sensitivity row for {system_id}")
        observed = (
            sum(bool(row["optimal"]) for row in retained),
            sum(int(row["coverage"]) for row in retained),
            len(retained),
        )
        if observed != expected:
            raise RuntimeError(
                f"masking sensitivity differs for {system_id}: "
                f"observed={observed}, expected={expected}"
            )


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


def check_posthoc_audits() -> None:
    """Recompute both independent audits without changing release files."""
    for script_name, report_name in (
        ("independent_math_audit.py", "posthoc_math_audit.json"),
        ("adversarial_metrics.py", "posthoc_predicted_tie_audit.json"),
    ):
        completed = subprocess.run(
            [sys.executable, "-B", str(ROOT / "tools" / script_name), str(ROOT)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=180,
        )
        regenerated = json.loads(completed.stdout)
        released = load_generated(ROOT / "results" / report_name)
        if not equivalent_generated(regenerated, released):
            raise RuntimeError(f"post-hoc audit differs: {report_name}")


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


def check_within_one() -> dict[str, int]:
    """Recompute the post-hoc within-one-target counts from item records."""

    records = load_generated(ROOT / "results/per_item.jsonl")
    if not isinstance(records, list):
        raise RuntimeError("per-item result file is not a list")
    grouped: dict[str, list[dict[str, object]]] = {}
    seen: set[tuple[str, str]] = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise RuntimeError(f"per-item row {index} is not an object")
        system_id = record.get("system_id")
        episode_id = record.get("episode_id")
        valid = record.get("valid")
        coverage = record.get("coverage")
        optimal_coverage = record.get("optimal_coverage")
        optimal = record.get("optimal")
        if not isinstance(system_id, str) or not isinstance(episode_id, str):
            raise RuntimeError(f"per-item row {index} has an invalid key")
        if type(valid) is not bool or type(optimal) is not bool:
            raise RuntimeError(f"per-item row {index} has an invalid Boolean field")
        if type(coverage) is not int or type(optimal_coverage) is not int:
            raise RuntimeError(f"per-item row {index} has an invalid coverage field")
        if not 0 <= coverage <= optimal_coverage <= 8:
            raise RuntimeError(f"per-item row {index} has impossible coverage")
        if optimal != (valid and coverage == optimal_coverage):
            raise RuntimeError(f"per-item row {index} has an inconsistent optimum flag")
        key = (system_id, episode_id)
        if key in seen:
            raise RuntimeError(f"duplicate per-item result: {system_id}/{episode_id}")
        seen.add(key)
        grouped.setdefault(system_id, []).append(record)

    if set(grouped) != set(EXPECTED_WITHIN_ONE):
        missing = sorted(set(EXPECTED_WITHIN_ONE) - set(grouped))
        extra = sorted(set(grouped) - set(EXPECTED_WITHIN_ONE))
        raise RuntimeError(
            f"unexpected per-item system set; missing={missing}, extra={extra}"
        )

    counts: dict[str, int] = {}
    for system_id, expected in EXPECTED_WITHIN_ONE.items():
        items = grouped[system_id]
        within_one = sum(
            record["valid"]
            and record["coverage"] >= record["optimal_coverage"] - 1
            for record in items
        )
        observed = (
            within_one,
            len(items),
            sum(record["valid"] for record in items),
        )
        if observed != expected:
            raise RuntimeError(
                f"post-hoc within-one-target count differs for {system_id}: "
                f"observed={observed}, expected={expected}"
            )
        counts[system_id] = within_one
    return counts


def check_headlines() -> dict[str, int]:
    report = json.loads((ROOT / "results/scores.json").read_text(encoding="utf-8"))
    rows = {row["system_id"]: row for row in report["rows"]}
    for system_id, expected in EXPECTED_OPTIMAL.items():
        row = rows[system_id]
        observed = (row["exact_optimal"], row["total"], row["valid"])
        if observed != expected:
            raise RuntimeError(f"optimal-portfolio headline differs for {system_id}: {observed}")
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
    # Numerical checks and independent post-hoc audits do not need manuscript
    # source. The submission packet intentionally contains no drafts. Its root
    # verify_results.py also checks the consolidated final-paper tables.
    return check_within_one()


def main() -> int:
    if sys.version_info < (3, 10):
        raise RuntimeError("Python 3.10 or newer is required")
    check_manifest()
    check_hygiene()
    prefix_scan, prefix_episodes = check_name_prefix_scan()
    check_masking_sensitivity(prefix_episodes["test"])
    check_prompt_packet()
    check_construction_tests()
    check_external_scorer_tests()
    regenerate_and_compare()
    check_posthoc_audits()
    within_one = check_headlines()
    report = json.loads((ROOT / "results/scores.json").read_text(encoding="utf-8"))
    print("Verified optimal-portfolio and post-hoc within-one-target counts:")
    for row in report["rows"]:
        if row["system_id"] in EXPECTED_OPTIMAL:
            print(
                f"  {row['display_label']}: optimal {row['exact_optimal']}/{row['total']}; "
                f"within one target {within_one[row['system_id']]}/{row['total']} "
                f"(valid {row['valid']}/{row['total']})"
            )
    print("  Fixed 20-ID Pro direct/support q=2 within one target: 11/20, 11/20")
    print("  Fixed 20-ID xhigh direct/support q=2 within one target: 13/20, 7/20")
    print(
        "Verified post-hoc source-name-prefix scan: "
        f"test {prefix_scan['test'][0]} occurrences in "
        f"{prefix_scan['test'][1]} source-name/statement pairs across "
        f"{prefix_scan['test'][2]} source declarations and "
        f"{prefix_scan['test'][3]}/60 episodes; development "
        f"{prefix_scan['development'][0]} occurrences in "
        f"{prefix_scan['development'][1]} pairs across "
        f"{prefix_scan['development'][2]} source declarations and "
        f"{prefix_scan['development'][3]}/30 episodes"
    )
    print("Verified six 54-episode masking-sensitivity rows")
    print("Verified independent construction-tie and predicted-optimizer audits")
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"VERIFICATION FAILED: {error}", file=sys.stderr)
        raise SystemExit(1)
