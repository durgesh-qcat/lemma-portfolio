#!/usr/bin/env python3
"""Byte-replay the frozen LemmaPortfolio-30 v1 Mathlib generation.

The v1 corpus was generated before the miner acquired its stricter rejection
of obviously reflexive declarations.  This audit uses the explicit
``mathlib-30-v1`` compatibility profile, verifies every Parquet input against
the retrospective receipt, regenerates both JSONL files in memory, and requires
byte identity with the frozen release.  It also checks the documented two-item
difference from the stricter current profile and the corresponding exclusion
sensitivity.  The sensitivity is an audit only; it is not a benchmark metric.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

try:
    from . import mine_mathlib_portfolios as miner
except ImportError:  # Direct script execution.
    import mine_mathlib_portfolios as miner


APIBENCH_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECEIPT = APIBENCH_ROOT / "pilot/mathlib_generation_receipt_v1.json"
DEFAULT_PUBLIC = APIBENCH_ROOT / "pilot/mathlib_public.jsonl"
DEFAULT_LABELS = APIBENCH_ROOT / "pilot/mathlib_labels.jsonl"
DEFAULT_SOL = APIBENCH_ROOT / "pilot/model_gpt56sol_max_v2.json"
DEFAULT_TERRA = APIBENCH_ROOT / "pilot/model_gpt56terra_max_v1.json"
GENERATOR = APIBENCH_ROOT / "scripts/mine_mathlib_portfolios.py"


class AuditError(RuntimeError):
    """A generation replay or receipt invariant failed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_path(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    _require(all(isinstance(row, dict) for row in rows), f"{path}: non-object row")
    return rows


def _jsonl_bytes(rows: Iterable[dict[str, Any]]) -> bytes:
    return "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows
    ).encode("utf-8")


def load_receipt(path: Path = DEFAULT_RECEIPT) -> dict[str, Any]:
    value = _load_json(path)
    _require(isinstance(value, dict), "generation receipt must be an object")
    _require(
        value.get("schema_version") == "lemma-portfolio.generation-receipt.v1",
        "generation receipt schema mismatch",
    )
    return value


def verify_input_files(
    parquet_dir: Path,
    receipt: dict[str, Any],
) -> tuple[list[Path], list[Path]]:
    rows = receipt.get("parquet_inputs")
    _require(isinstance(rows, list), "receipt parquet_inputs must be a list")
    expected_names = [f"dep-{index:03d}.parquet" for index in range(128)] + [
        f"types-{index:03d}.parquet" for index in range(128)
    ]
    _require(
        [row.get("name") for row in rows if isinstance(row, dict)] == expected_names,
        "receipt must list dep-000--127 then types-000--127",
    )
    actual_names = sorted(path.name for path in parquet_dir.glob("*.parquet"))
    _require(actual_names == sorted(expected_names), "Parquet directory file set mismatch")
    total_bytes = 0
    for row in rows:
        _require(isinstance(row, dict), "invalid Parquet receipt row")
        path = parquet_dir / row["name"]
        _require(path.is_file(), f"missing Parquet input: {row['name']}")
        size = path.stat().st_size
        _require(size == row.get("bytes"), f"Parquet size mismatch: {row['name']}")
        _require(
            _sha256_path(path) == row.get("sha256"),
            f"Parquet SHA-256 mismatch: {row['name']}",
        )
        total_bytes += size
    _require(total_bytes == receipt.get("parquet_total_bytes"), "Parquet byte total mismatch")
    dependencies = [parquet_dir / name for name in expected_names[:128]]
    types = [parquet_dir / name for name in expected_names[128:]]
    return dependencies, types


def _source_pair(label: dict[str, Any]) -> frozenset[str]:
    sources = label["candidate_sources"]
    return frozenset(sources[item] for item in label["oracle_helpers"])


def compare_profiles(
    v1_public: list[dict[str, Any]],
    v1_labels: list[dict[str, Any]],
    strict_public: list[dict[str, Any]],
    strict_labels: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    _require(len(v1_public) == len(strict_public) == 30, "profile episode count mismatch")
    _require(len(v1_labels) == len(strict_labels) == 30, "profile label count mismatch")
    changes: list[dict[str, Any]] = []
    for old_public, old_label, new_public, new_label in zip(
        v1_public,
        v1_labels,
        strict_public,
        strict_labels,
        strict=True,
    ):
        episode_id = old_public["episode_id"]
        _require(new_public["episode_id"] == episode_id, "profile episode order changed")
        _require(
            old_label["source_module"] == new_label["source_module"],
            f"{episode_id}: profile module changed",
        )
        _require(
            list(old_label["target_sources"].values())
            == list(new_label["target_sources"].values()),
            f"{episode_id}: profile targets changed",
        )
        _require(
            _source_pair(old_label) == _source_pair(new_label),
            f"{episode_id}: profile gold source pair changed",
        )
        old_candidates = set(old_label["candidate_sources"].values())
        new_candidates = set(new_label["candidate_sources"].values())
        if old_candidates != new_candidates:
            changes.append(
                {
                    "episode_id": episode_id,
                    "removed_by_strict_profile": sorted(old_candidates - new_candidates),
                    "added_by_strict_profile": sorted(new_candidates - old_candidates),
                }
            )
    return changes


def exclusion_sensitivity(
    labels: Sequence[dict[str, Any]],
    responses: dict[str, Any],
    excluded: set[str],
) -> dict[str, Any]:
    retained = [row for row in labels if row["episode_id"] not in excluded]
    correct = sum(
        set(responses[row["episode_id"]]["selected"]) == set(row["oracle_helpers"])
        for row in retained
    )
    return {"correct": correct, "denominator": len(retained), "rate": correct / len(retained)}


def audit(
    parquet_dir: Path,
    *,
    receipt_path: Path = DEFAULT_RECEIPT,
    public_path: Path = DEFAULT_PUBLIC,
    labels_path: Path = DEFAULT_LABELS,
) -> dict[str, Any]:
    receipt = load_receipt(receipt_path)
    _require(
        _sha256_path(GENERATOR) == receipt.get("generator", {}).get("sha256"),
        "generator SHA-256 differs from receipt",
    )
    dependencies, types = verify_input_files(parquet_dir, receipt)
    declarations = miner.load_declarations(dependencies, types)
    parameters = receipt["parameters"]
    common = {
        "seed": parameters["seed"],
        "count": parameters["count"],
        "candidate_count": parameters["candidates"],
        "target_count": parameters["targets"],
        "budget": parameters["budget"],
    }
    v1_public, v1_labels = miner.mine(
        declarations,
        generation_profile=miner.V1_GENERATION_PROFILE,
        **common,
    )
    v1_public_bytes = _jsonl_bytes(v1_public)
    v1_label_bytes = _jsonl_bytes(v1_labels)
    frozen_public = public_path.read_bytes()
    frozen_labels = labels_path.read_bytes()
    _require(v1_public_bytes == frozen_public, "v1 public JSONL is not byte-identical")
    _require(v1_label_bytes == frozen_labels, "v1 label JSONL is not byte-identical")
    outputs = receipt["v1_replay_outputs"]
    _require(_sha256_bytes(v1_public_bytes) == outputs["public_sha256"], "public hash mismatch")
    _require(_sha256_bytes(v1_label_bytes) == outputs["labels_sha256"], "label hash mismatch")

    strict_public, strict_labels = miner.mine(
        declarations,
        generation_profile=miner.STRICT_GENERATION_PROFILE,
        **common,
    )
    strict_public_bytes = _jsonl_bytes(strict_public)
    strict_label_bytes = _jsonl_bytes(strict_labels)
    strict_receipt = receipt["strict_profile_crosscheck"]
    _require(
        _sha256_bytes(strict_public_bytes) == strict_receipt["public_sha256"],
        "strict-profile public hash mismatch",
    )
    _require(
        _sha256_bytes(strict_label_bytes) == strict_receipt["labels_sha256"],
        "strict-profile label hash mismatch",
    )
    changes = compare_profiles(v1_public, v1_labels, strict_public, strict_labels)
    _require(changes == strict_receipt["candidate_set_changes"], "profile delta mismatch")

    frozen_label_rows = _load_jsonl(labels_path)
    excluded = {row["episode_id"] for row in changes}
    sol = exclusion_sensitivity(frozen_label_rows, _load_json(DEFAULT_SOL), excluded)
    terra = exclusion_sensitivity(frozen_label_rows, _load_json(DEFAULT_TERRA), excluded)
    _require(sol == receipt["exclusion_sensitivity"]["gpt-5.6-sol_max"], "sol sensitivity mismatch")
    _require(
        terra == receipt["exclusion_sensitivity"]["gpt-5.6-terra_max"],
        "terra sensitivity mismatch",
    )
    return {
        "status": "ok",
        "declarations": len(declarations),
        "episodes": len(v1_public),
        "v1_public_sha256": _sha256_bytes(v1_public_bytes),
        "v1_labels_sha256": _sha256_bytes(v1_label_bytes),
        "strict_profile_changed_episodes": sorted(excluded),
        "exclusion_sensitivity_is_not_a_benchmark_metric": True,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parquet-dir", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    parser.add_argument("--public", type=Path, default=DEFAULT_PUBLIC)
    parser.add_argument("--labels", type=Path, default=DEFAULT_LABELS)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = audit(
            args.parquet_dir,
            receipt_path=args.receipt,
            public_path=args.public,
            labels_path=args.labels,
        )
    except (
        AuditError,
        OSError,
        RuntimeError,
        UnicodeError,
        ValueError,
        KeyError,
    ) as error:
        raise SystemExit(f"generation audit failed: {error}") from error
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
