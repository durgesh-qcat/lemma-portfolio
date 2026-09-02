#!/usr/bin/env python3
"""Score external LemmaPortfolio V4 predictions.

The input may be one or more JSON shards.  Each shard is either a raw mapping
from episode IDs to three selected candidate IDs, or an object containing that
mapping under ``predictions``.  Missing and malformed predictions receive zero;
the denominator is always the complete 60-episode released test set.

This command intentionally uses only the Python standard library.
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
        SELECTION_BUDGET,
        load_benchmark,
        score_predictions as score_benchmark_predictions,
    )
except ImportError:  # pragma: no cover - exercised by direct CLI invocation.
    from score_release import (  # type: ignore[no-redef]
        BENCHMARK_ID,
        SELECTION_BUDGET,
        load_benchmark,
        score_predictions as score_benchmark_predictions,
    )


SCHEMA_VERSION = "lemma-portfolio.external-prediction-score.v1"


class PredictionInputError(ValueError):
    """Raised when prediction files cannot be merged unambiguously."""


def _object_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise PredictionInputError(f"duplicate JSON key {key!r}")
        value[key] = item
    return value


def _read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle, object_pairs_hook=_object_without_duplicate_keys)
    except PredictionInputError as error:
        raise PredictionInputError(f"{path}: {error}") from error
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PredictionInputError(f"cannot read {path}: {error}") from error
    if not isinstance(value, dict):
        raise PredictionInputError(f"{path}: top-level JSON value must be an object")
    return value


def _optional_text(wrapper: dict[str, Any], key: str, path: Path) -> str | None:
    if key not in wrapper:
        return None
    value = wrapper[key]
    if not isinstance(value, str) or not value.strip():
        raise PredictionInputError(f"{path}: {key} must be a non-empty string")
    return value.strip()


def read_prediction_shard(
    path: Path,
) -> tuple[dict[str, Any], dict[str, str]]:
    """Read a raw episode map or a ``predictions`` wrapper from ``path``."""

    value = _read_json(path)
    if "predictions" not in value:
        return value, {}

    predictions = value["predictions"]
    if not isinstance(predictions, dict):
        raise PredictionInputError(f"{path}: predictions must be a JSON object")
    metadata: dict[str, str] = {}
    for key in ("benchmark_id", "system_id", "display_label"):
        item = _optional_text(value, key, path)
        if item is not None:
            metadata[key] = item
    return predictions, metadata


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
        raise PredictionInputError(f"conflicting {key} values across shards: {rendered}")
    return next(iter(observed), None)


def merge_prediction_shards(
    paths: Sequence[Path], known_episode_ids: set[str]
) -> tuple[dict[str, Any], dict[str, str]]:
    """Merge shards, rejecting duplicate or non-benchmark episode IDs."""

    if not paths:
        raise PredictionInputError("at least one prediction file is required")
    merged: dict[str, Any] = {}
    source_for_episode: dict[str, Path] = {}
    metadata_rows: list[tuple[Path, dict[str, str]]] = []
    for path in paths:
        predictions, metadata = read_prediction_shard(path)
        metadata_rows.append((path, metadata))
        for episode_id, prediction in predictions.items():
            if episode_id not in known_episode_ids:
                raise PredictionInputError(
                    f"{path}: unknown episode ID {episode_id!r}"
                )
            if episode_id in merged:
                raise PredictionInputError(
                    f"duplicate episode ID {episode_id!r} in {source_for_episode[episode_id]} "
                    f"and {path}"
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
        raise PredictionInputError(
            f"prediction benchmark_id is {benchmark_id!r}; expected {BENCHMARK_ID!r}"
        )
    return merged, metadata


def _valid_external_prediction(value: Any, allowed: set[str]) -> bool:
    """Guard the release scorer from arbitrary malformed JSON values."""

    return (
        isinstance(value, list)
        and len(value) == SELECTION_BUDGET
        and all(isinstance(item, str) for item in value)
        and len(set(value)) == SELECTION_BUDGET
        and set(value).issubset(allowed)
    )


def score_external_predictions(
    paths: Sequence[Path],
    release_root: Path,
    *,
    system_id: str | None = None,
    display_label: str | None = None,
) -> dict[str, Any]:
    """Load, merge, and score files against all 60 released test episodes."""

    public, labels = load_benchmark(release_root)
    merged, metadata = merge_prediction_shards(paths, set(public))
    resolved_system_id = system_id or metadata.get("system_id") or "external_predictions"
    resolved_display_label = (
        display_label
        or metadata.get("display_label")
        or resolved_system_id
    )

    sanitized: dict[str, Any] = {}
    input_status: dict[str, str] = {}
    for episode_id in public:
        if episode_id not in merged:
            input_status[episode_id] = "missing"
            continue
        value = merged[episode_id]
        allowed = set(public[episode_id]["candidate_ids"])
        if _valid_external_prediction(value, allowed):
            sanitized[episode_id] = value
            input_status[episode_id] = "valid"
        else:
            # The canonical scorer maps None to zero exact and target coverage.
            sanitized[episode_id] = None
            input_status[episode_id] = "malformed"

    summary, scored_rows = score_benchmark_predictions(
        resolved_system_id,
        resolved_display_label,
        sanitized,
        public,
        labels,
    )
    per_item = [
        {**row, "input_status": input_status[row["episode_id"]]}
        for row in scored_rows
    ]
    missing_ids = [episode_id for episode_id in public if episode_id not in merged]
    malformed_ids = [
        episode_id
        for episode_id in public
        if input_status[episode_id] == "malformed"
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "benchmark_id": BENCHMARK_ID,
        "prediction_files": [str(path) for path in paths],
        "submitted_episode_count": len(merged),
        "missing_episode_count": len(missing_ids),
        "missing_episode_ids": missing_ids,
        "malformed_episode_count": len(malformed_ids),
        "malformed_episode_ids": malformed_ids,
        "summary": summary,
        "per_item": per_item,
    }


def readable_summary(report: dict[str, Any]) -> str:
    summary = report["summary"]
    return "\n".join(
        [
            f"LemmaPortfolio V4 score: {summary['display_label']}",
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
                "Mean oracle-normalized coverage: "
                f"{summary['mean_oracle_normalized_coverage_percentage']:.1f}%"
            ),
            (
                "Valid predictions: "
                f"{summary['valid']}/{summary['total']} "
                f"({summary['valid_percentage']:.1f}%)"
            ),
            f"Missing predictions (scored zero): {report['missing_episode_count']}",
            f"Malformed predictions (scored zero): {report['malformed_episode_count']}",
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
            "Score one or more LemmaPortfolio V4 JSON prediction shards. "
            "Missing or malformed rows score zero out of the fixed 60 episodes."
        )
    )
    parser.add_argument(
        "prediction_files",
        nargs="*",
        type=Path,
        help="JSON file(s): an episode map or an object with a predictions map",
    )
    parser.add_argument(
        "--predictions",
        dest="prediction_groups",
        nargs="+",
        action="append",
        type=Path,
        metavar="PATH",
        help="JSON prediction shard(s); may be supplied more than once",
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
    prediction_files = list(args.prediction_files)
    for group in args.prediction_groups or []:
        prediction_files.extend(group)
    if not prediction_files:
        parser.error("at least one prediction file is required")
    try:
        report = score_external_predictions(
            prediction_files,
            args.release_root.resolve(),
            system_id=args.system_id,
            display_label=args.display_label,
        )
    except PredictionInputError as error:
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
