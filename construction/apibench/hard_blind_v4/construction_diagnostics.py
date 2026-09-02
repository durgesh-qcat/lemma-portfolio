#!/usr/bin/env python3
"""Deterministic public-text construction diagnostics for LemmaPortfolio v4.

This module accepts only public JSONL rows. It has no label-path argument and
does not import the v4 builder. Fifteen rank rules use shallow public candidate
features; three lexical set-cover rules infer target/candidate edges by token
Jaccard before greedy selection. Every method here is an item-admission gate:
these forced misses MUST NOT be reported as independent benchmark baselines.
"""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Sequence

try:
    from apibench.scripts import build_mathlib_release_v2 as common
except ImportError:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from apibench.scripts import build_mathlib_release_v2 as common


BUDGET = 3
TOKEN = re.compile(
    r"[A-Za-z_\u0080-\uffff][A-Za-z0-9_\u0080-\uffff'.]*|:=|=>|[^\s]"
)
CONNECTIVES = ("=", "≠", "→", "↔", "∧", "∨", "¬", "≤", "≥", "<", ">")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def tokens(statement: str) -> frozenset[str]:
    return common.public_type_tokens(statement)


def jaccard(left: frozenset[str], right: frozenset[str]) -> Fraction:
    union = left | right
    return Fraction(len(left & right), len(union)) if union else Fraction()


def _rank_pick(
    ids: Sequence[str], values: dict[str, Fraction], *, largest: bool
) -> list[str]:
    order = {candidate: index for index, candidate in enumerate(ids)}
    return sorted(
        ids,
        key=lambda candidate: (
            -values[candidate] if largest else values[candidate],
            order[candidate],
        ),
    )[:BUDGET]


def _central_pick(ids: Sequence[str], values: dict[str, Fraction]) -> list[str]:
    ordered = sorted(values.values())
    median = (ordered[len(ordered) // 2 - 1] + ordered[len(ordered) // 2]) / 2
    order = {candidate: index for index, candidate in enumerate(ids)}
    return sorted(
        ids,
        key=lambda candidate: (abs(values[candidate] - median), order[candidate]),
    )[:BUDGET]


def _greedy(ids: Sequence[str], incidence: Sequence[frozenset[str]]) -> list[str]:
    order = {candidate: index for index, candidate in enumerate(ids)}
    selected: list[str] = []
    covered: set[int] = set()
    while len(selected) < BUDGET:
        choice = max(
            (candidate for candidate in ids if candidate not in selected),
            key=lambda candidate: (
                sum(
                    target_index not in covered and candidate in direct
                    for target_index, direct in enumerate(incidence)
                ),
                -order[candidate],
            ),
        )
        selected.append(choice)
        covered.update(
            target_index
            for target_index, direct in enumerate(incidence)
            if choice in direct
        )
    return sorted(selected)


def predict_episode(episode: dict[str, Any]) -> dict[str, list[str]]:
    candidates = episode["candidates"]
    targets = episode["targets"]
    ids = [row["id"] for row in candidates]
    statements = {row["id"]: row["statement"] for row in candidates}
    target_statements = [row["statement"] for row in targets]
    features: dict[str, tuple[Fraction, ...]] = {}
    for candidate_id in ids:
        statement = statements[candidate_id]
        features[candidate_id] = (
            Fraction(len(statement)),
            Fraction(len(TOKEN.findall(statement))),
            Fraction(statement.count("∀") + statement.count("fun") + statement.count(":")),
            Fraction(sum(statement.count(marker) for marker in CONNECTIVES)),
            common.public_type_portfolio_similarity(statement, target_statements),
        )

    predictions: dict[str, list[str]] = {}
    labels = ("characters", "tokens", "binders", "connectives", "target_similarity")
    for feature_index, label in enumerate(labels):
        values = {
            candidate_id: feature[feature_index]
            for candidate_id, feature in features.items()
        }
        predictions[f"{label}_largest"] = sorted(
            _rank_pick(ids, values, largest=True)
        )
        predictions[f"{label}_smallest"] = sorted(
            _rank_pick(ids, values, largest=False)
        )
        predictions[f"{label}_central"] = sorted(_central_pick(ids, values))

    order = {candidate: index for index, candidate in enumerate(ids)}
    for width in (1, 2, 3):
        inferred: list[frozenset[str]] = []
        for target in target_statements:
            target_tokens = tokens(target)
            ranked = sorted(
                ids,
                key=lambda candidate_id: (
                    -jaccard(tokens(statements[candidate_id]), target_tokens),
                    order[candidate_id],
                ),
            )
            inferred.append(frozenset(ranked[:width]))
        predictions[f"lexical_greedy_top{width}"] = _greedy(ids, inferred)
    assert len(predictions) == 18
    return dict(sorted(predictions.items()))


def render_bundle(
    calibration_rows: Sequence[dict[str, Any]],
    blind_rows: Sequence[dict[str, Any]],
    *,
    calibration_bytes: bytes,
    blind_bytes: bytes,
) -> dict[str, Any]:
    def split(rows: Sequence[dict[str, Any]], public_bytes: bytes) -> dict[str, Any]:
        return {
            "benchmark_id": rows[0]["benchmark_id"] if rows else None,
            "episodes": len(rows),
            "public_sha256": sha256_bytes(public_bytes),
            "predictions": {
                row["episode_id"]: predict_episode(row) for row in rows
            },
        }

    return {
        "schema_version": "lemma-portfolio.gated-public-construction-diagnostics.v4",
        "budget": BUDGET,
        "method_count": 18,
        "labels_read": 0,
        "evaluated_blind_predictions_read": 0,
        "methods": sorted(predict_episode(calibration_rows[0])) if calibration_rows else [],
        "splits": {
            "calibration": split(calibration_rows, calibration_bytes),
            "blind": split(blind_rows, blind_bytes),
        },
    }


def _load(path: Path) -> tuple[list[dict[str, Any]], bytes]:
    payload = path.read_bytes()
    rows = [json.loads(line) for line in payload.decode("utf-8").splitlines()]
    return rows, payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calibration-public", type=Path, required=True)
    parser.add_argument("--blind-public", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    calibration, calibration_bytes = _load(args.calibration_public)
    blind, blind_bytes = _load(args.blind_public)
    result = render_bundle(
        calibration,
        blind,
        calibration_bytes=calibration_bytes,
        blind_bytes=blind_bytes,
    )
    payload = (
        json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("ascii")
    descriptor = args.output.open("xb")
    with descriptor:
        descriptor.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
