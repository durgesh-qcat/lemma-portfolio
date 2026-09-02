#!/usr/bin/env python3
"""Score external LemmaPortfolio V4 structured-support predictions.

Each input JSON file is either a raw mapping from episode IDs to per-target
ranked support lists, or an object containing that mapping under
``predicted_support``.  The scorer retains the first two candidates per target,
uses the paper's deterministic exhaustive portfolio optimizer, and scores the
exact 20 episodes represented by ``prompts/SOL_EXTRA_PROMPTS``.

Missing or malformed episode values receive zero.  Unknown and duplicated
episode IDs are rejected because they cannot be aligned unambiguously.  This
command intentionally uses only the Python standard library.  Strict JSON
parsing is the default; ``--invalid-as-missing`` records and skips unusable raw
response files, leaving their absent episodes at zero.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Iterable, Sequence

try:  # Support both ``python tools/...`` and package-style imports in tests.
    from .score_release import (
        BENCHMARK_ID,
        incidence_counts,
        load_benchmark,
        score_predictions as score_benchmark_predictions,
        solve_support,
    )
except ImportError:  # pragma: no cover - exercised by direct CLI invocation.
    from score_release import (  # type: ignore[no-redef]
        BENCHMARK_ID,
        incidence_counts,
        load_benchmark,
        score_predictions as score_benchmark_predictions,
        solve_support,
    )


SCHEMA_VERSION = "lemma-portfolio.external-support-score.v1"
SUPPORT_PREFIX_WIDTH = 2
MAX_SUPPORT_LENGTH = 4


class SupportInputError(ValueError):
    """Raised when structured-support files cannot be scored unambiguously."""


class InvalidSupportFileError(SupportInputError):
    """Raised for a source file that cannot supply a support mapping."""


def _report_path(path: Path) -> str:
    """Use a portable filename in reports instead of leaking a local path."""

    return path.name


def _report_error(path: Path, error: Exception) -> str:
    return str(error).replace(str(path), _report_path(path))


def _object_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise SupportInputError(f"duplicate JSON key {key!r}")
        value[key] = item
    return value


def _read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle, object_pairs_hook=_object_without_duplicate_keys)
    except SupportInputError as error:
        raise SupportInputError(f"{path}: {error}") from error
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise InvalidSupportFileError(f"cannot read {path}: {error}") from error
    if not isinstance(value, dict):
        raise InvalidSupportFileError(
            f"{path}: top-level JSON value must be an object"
        )
    return value


def _optional_text(wrapper: dict[str, Any], key: str, path: Path) -> str | None:
    if key not in wrapper:
        return None
    value = wrapper[key]
    if not isinstance(value, str) or not value.strip():
        raise SupportInputError(f"{path}: {key} must be a non-empty string")
    return value.strip()


def read_support_shard(path: Path) -> tuple[dict[str, Any], dict[str, str]]:
    """Read a raw episode map or a ``predicted_support`` wrapper."""

    value = _read_json(path)
    if "predicted_support" not in value:
        return value, {}

    support = value["predicted_support"]
    if not isinstance(support, dict):
        raise InvalidSupportFileError(
            f"{path}: predicted_support must be a JSON object"
        )
    metadata: dict[str, str] = {}
    for key in ("benchmark_id", "system_id", "display_label"):
        item = _optional_text(value, key, path)
        if item is not None:
            metadata[key] = item
    return support, metadata


def _consistent_metadata(
    metadata_rows: Iterable[tuple[Path, dict[str, str]]], key: str
) -> str | None:
    observed: dict[str, list[str]] = {}
    for path, metadata in metadata_rows:
        if key in metadata:
            observed.setdefault(metadata[key], []).append(str(path))
    if len(observed) > 1:
        rendered = "; ".join(
            f"{value!r} in {', '.join(paths)}" for value, paths in observed.items()
        )
        raise SupportInputError(f"conflicting {key} values across shards: {rendered}")
    return next(iter(observed), None)


def merge_support_shards(
    paths: Sequence[Path],
    known_episode_ids: set[str],
    *,
    invalid_as_missing: bool = False,
) -> tuple[dict[str, Any], dict[str, str], list[dict[str, str]]]:
    """Merge support shards, rejecting unknown or duplicated episode IDs."""

    if not paths:
        raise SupportInputError("at least one support file is required")
    merged: dict[str, Any] = {}
    source_for_episode: dict[str, Path] = {}
    metadata_rows: list[tuple[Path, dict[str, str]]] = []
    invalid_source_files: list[dict[str, str]] = []
    for path in paths:
        try:
            support, metadata = read_support_shard(path)
        except InvalidSupportFileError as error:
            if not invalid_as_missing:
                raise
            invalid_source_files.append(
                {"path": _report_path(path), "error": _report_error(path, error)}
            )
            continue
        metadata_rows.append((path, metadata))
        for episode_id, prediction in support.items():
            if episode_id not in known_episode_ids:
                raise SupportInputError(
                    f"{path}: unknown structured-support episode ID {episode_id!r}"
                )
            if episode_id in merged:
                raise SupportInputError(
                    f"duplicate episode ID {episode_id!r} in "
                    f"{source_for_episode[episode_id]} and {path}"
                )
            merged[episode_id] = prediction
            source_for_episode[episode_id] = path

    metadata = {
        key: value
        for key in ("benchmark_id", "system_id", "display_label")
        if (value := _consistent_metadata(metadata_rows, key)) is not None
    }
    benchmark_id = metadata.get("benchmark_id")
    if benchmark_id is not None and benchmark_id != BENCHMARK_ID:
        raise SupportInputError(
            f"support benchmark_id is {benchmark_id!r}; expected {BENCHMARK_ID!r}"
        )
    return merged, metadata, invalid_source_files


def expected_support_episode_ids(
    release_root: Path, public: dict[str, dict[str, Any]]
) -> list[str]:
    """Read the fixed 20-item support subset from the released prompt packet."""

    prompt_paths = sorted((release_root / "prompts/SOL_EXTRA_PROMPTS").glob("*.txt"))
    if len(prompt_paths) != 4:
        raise SupportInputError("expected exactly four structured-support prompt files")

    episode_ids: list[str] = []
    for path in prompt_paths:
        text = path.read_text(encoding="utf-8")
        try:
            payload = text.split("<episodes>\n", 1)[1].split("\n</episodes>", 1)[0]
            rows = json.loads(payload)
        except (IndexError, json.JSONDecodeError) as error:
            raise SupportInputError(
                f"cannot parse episode payload in {path}"
            ) from error
        if not isinstance(rows, list) or len(rows) != 5:
            raise SupportInputError(f"{path}: expected exactly five episodes")
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("episode_id"), str):
                raise SupportInputError(f"{path}: invalid episode row")
            episode_id = row["episode_id"]
            if episode_id not in public:
                raise SupportInputError(f"{path}: unknown episode {episode_id!r}")
            episode_ids.append(episode_id)

    if len(episode_ids) != 20 or len(set(episode_ids)) != 20:
        raise SupportInputError(
            "structured-support prompts must contain 20 distinct episodes"
        )
    return episode_ids


def valid_support_value(
    value: Any, expected_targets: list[str], allowed_candidates: set[str]
) -> bool:
    """Apply the paper pipeline's per-episode support validity rules."""

    if not isinstance(value, dict) or set(value) != set(expected_targets):
        return False
    for target in expected_targets:
        ranked = value[target]
        if (
            not isinstance(ranked, list)
            or len(ranked) > MAX_SUPPORT_LENGTH
            or not all(isinstance(candidate, str) for candidate in ranked)
            or len(ranked) != len(set(ranked))
            or not set(ranked).issubset(allowed_candidates)
        ):
            return False
    return True


def _edge_summary(counts: list[int]) -> dict[str, float | int]:
    true_positive, false_positive, false_negative = counts
    precision = (
        true_positive / (true_positive + false_positive)
        if true_positive + false_positive
        else 0.0
    )
    recall = (
        true_positive / (true_positive + false_negative)
        if true_positive + false_negative
        else 0.0
    )
    return {
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "micro_precision": precision,
        "micro_recall": recall,
        "micro_f1": (
            2 * precision * recall / (precision + recall)
            if precision + recall
            else 0.0
        ),
    }


def score_external_support(
    paths: Sequence[Path],
    release_root: Path,
    *,
    system_id: str | None = None,
    display_label: str | None = None,
    invalid_as_missing: bool = False,
) -> dict[str, Any]:
    """Load, optimize, and score support predictions on the fixed 20 episodes."""

    public, labels = load_benchmark(release_root)
    episode_ids = expected_support_episode_ids(release_root, public)
    merged, metadata, invalid_source_files = merge_support_shards(
        paths,
        set(episode_ids),
        invalid_as_missing=invalid_as_missing,
    )
    source_system_id = system_id or metadata.get("system_id") or "external_support"
    source_display_label = (
        display_label or metadata.get("display_label") or source_system_id
    )

    optimized_predictions: dict[str, Any] = {}
    input_status: dict[str, str] = {}
    full_counts = [0, 0, 0]
    q2_counts = [0, 0, 0]
    for episode_id in episode_ids:
        expected_targets = public[episode_id]["target_ids"]
        empty_support = {target: [] for target in expected_targets}
        if episode_id not in merged:
            input_status[episode_id] = "missing"
            support = empty_support
        else:
            value = merged[episode_id]
            if valid_support_value(
                value,
                expected_targets,
                set(public[episode_id]["candidate_ids"]),
            ):
                input_status[episode_id] = "valid"
                support = value
                optimized_predictions[episode_id] = solve_support(
                    public[episode_id]["candidate_ids"],
                    support,
                    SUPPORT_PREFIX_WIDTH,
                )
            else:
                input_status[episode_id] = "malformed"
                support = empty_support
                optimized_predictions[episode_id] = None

        for index, count in enumerate(
            incidence_counts(support, labels[episode_id]["dependencies"], None)
        ):
            full_counts[index] += count
        for index, count in enumerate(
            incidence_counts(
                support,
                labels[episode_id]["dependencies"],
                SUPPORT_PREFIX_WIDTH,
            )
        ):
            q2_counts[index] += count

    summary, scored_rows = score_benchmark_predictions(
        f"{source_system_id}_support_q2",
        f"{source_display_label} support q=2",
        optimized_predictions,
        public,
        labels,
        episode_ids,
    )
    per_item = [
        {**row, "input_status": input_status[row["episode_id"]]}
        for row in scored_rows
    ]
    missing_ids = [
        episode_id for episode_id in episode_ids if episode_id not in merged
    ]
    malformed_ids = [
        episode_id
        for episode_id in episode_ids
        if input_status[episode_id] == "malformed"
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "benchmark_id": BENCHMARK_ID,
        "condition": "ordered_support_then_exhaustive_optimizer",
        "support_prefix_width": SUPPORT_PREFIX_WIDTH,
        "expected_episode_ids": episode_ids,
        "support_files": [_report_path(path) for path in paths],
        "invalid_source_file_count": len(invalid_source_files),
        "invalid_source_files": invalid_source_files,
        "submitted_episode_count": len(merged),
        "missing_episode_count": len(missing_ids),
        "missing_episode_ids": missing_ids,
        "malformed_episode_count": len(malformed_ids),
        "malformed_episode_ids": malformed_ids,
        "summary": summary,
        "support_full": _edge_summary(full_counts),
        "support_q2": _edge_summary(q2_counts),
        "per_item": per_item,
    }


def readable_summary(report: dict[str, Any]) -> str:
    summary = report["summary"]
    return "\n".join(
        [
            f"LemmaPortfolio V4 structured-support score: {summary['display_label']}",
            (
                "Exact optimal portfolios: "
                f"{summary['exact_optimal']}/{summary['total']} "
                f"({summary['exact_optimal_percentage']:.1f}%)"
            ),
            (
                "Target coverage: "
                f"{summary['achieved_target_coverage']}/{summary['target_count']} "
                f"({summary['target_coverage_percentage']:.1f}%)"
            ),
            (
                "Valid support episodes: "
                f"{summary['valid']}/{summary['total']} "
                f"({summary['valid_percentage']:.1f}%)"
            ),
            (
                "Support q=2 micro F1: "
                f"{100 * report['support_q2']['micro_f1']:.1f}%"
            ),
            f"Missing episodes (scored zero): {report['missing_episode_count']}",
            f"Malformed episodes (scored zero): {report['malformed_episode_count']}",
            f"Invalid source files skipped: {report['invalid_source_file_count']}",
        ]
    )


def _write_json(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Score one or more LemmaPortfolio V4 structured-support JSON shards. "
            "Missing or malformed episodes score zero out of the fixed 20."
        )
    )
    parser.add_argument(
        "support_files",
        nargs="*",
        type=Path,
        help="JSON file(s): an episode map or a predicted_support wrapper",
    )
    parser.add_argument(
        "--supports",
        "--predicted-support",
        dest="support_groups",
        nargs="+",
        action="append",
        type=Path,
        metavar="PATH",
        help="JSON support shard(s); may be supplied more than once",
    )
    parser.add_argument(
        "--release-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root (default: inferred from this script)",
    )
    parser.add_argument("--system-id", help="machine-readable model/run identifier")
    parser.add_argument("--display-label", help="human-readable model/run label")
    parser.add_argument(
        "--invalid-as-missing",
        action="store_true",
        help=(
            "record and skip unreadable, unparseable, or non-object source files; "
            "episodes absent from the remaining shards score zero"
        ),
    )
    parser.add_argument(
        "--json-output",
        "--output-json",
        "--json",
        "--output",
        dest="json_output",
        type=Path,
        metavar="PATH",
        help="also write the complete score report as JSON (use - for stdout)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    support_files = list(args.support_files)
    for group in args.support_groups or []:
        support_files.extend(group)
    if not support_files:
        parser.error("at least one support file is required")
    try:
        report = score_external_support(
            support_files,
            args.release_root.resolve(),
            system_id=args.system_id,
            display_label=args.display_label,
            invalid_as_missing=args.invalid_as_missing,
        )
    except SupportInputError as error:
        parser.error(str(error))

    summary = readable_summary(report)
    if args.json_output is not None and str(args.json_output) == "-":
        print(summary, file=sys.stderr)
        json.dump(report, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        print(summary)
        if args.json_output is not None:
            _write_json(args.json_output, report)
            print(f"JSON report: {args.json_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
