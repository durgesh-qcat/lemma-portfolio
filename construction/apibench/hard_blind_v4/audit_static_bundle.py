#!/usr/bin/env python3
"""Fail-closed static byte replay for a materialized LemmaPortfolio v4 bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import stat
import sys
from typing import Any, Sequence

try:
    from apibench.hard_blind_v4 import build_hard_blind_v4 as build
    from apibench.hard_blind_v4 import construction_diagnostics
    from apibench.scripts import build_mathlib_release_v2 as common
except ImportError:  # Direct execution from this directory.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from apibench.hard_blind_v4 import build_hard_blind_v4 as build
    from apibench.hard_blind_v4 import construction_diagnostics
    from apibench.scripts import build_mathlib_release_v2 as common


class StaticBundleAuditError(RuntimeError):
    """A provenance-free static-bundle invariant failed."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise StaticBundleAuditError(message)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise StaticBundleAuditError("JSON artifact unreadable") from error
    require(isinstance(value, dict), "JSON artifact must be an object")
    return value


def _mode(path: Path) -> str:
    return f"{stat.S_IMODE(path.stat().st_mode):04o}"


def audit(*, public_dir: Path, private_dir: Path, parquet_dir: Path) -> dict[str, Any]:
    public_dir = public_dir.resolve(strict=True)
    private_dir = private_dir.resolve(strict=True)
    require(public_dir != private_dir, "public/private directories coincide")
    paths = {
        "manifest": public_dir / "manifest.preinference.json",
        "receipt": public_dir / "generation_receipt.json",
        "diagnostics": public_dir / "gated_construction_diagnostics.json",
        "calibration_public": public_dir / "calibration.public.jsonl",
        "calibration_a_public": public_dir / "calibration_a.public.jsonl",
        "calibration_b_public": public_dir / "calibration_b.public.jsonl",
        "calibration_labels": public_dir / "calibration.labels.jsonl",
        "calibration_a_labels": public_dir / "calibration_a.labels.jsonl",
        "calibration_b_labels": public_dir / "calibration_b.labels.jsonl",
        "blind_public": public_dir / "blind.public.jsonl",
        "blind_labels": private_dir / "blind.labels.jsonl",
        "private_manifest": private_dir / "private_manifest.json",
    }
    require(all(path.is_file() for path in paths.values()), "materialized artifact missing")
    for key, path in paths.items():
        expected_mode = "0600" if key in {"blind_labels", "private_manifest"} else "0644"
        require(_mode(path) == expected_mode, "artifact permission mismatch")
    require(not (public_dir / "blind.labels.jsonl").exists(), "blind labels in public directory")

    manifest = _load_json(paths["manifest"])
    receipt = _load_json(paths["receipt"])
    private_manifest = _load_json(paths["private_manifest"])
    require(
        manifest.get("schema_version")
        == "lemma-portfolio.dependency-compression-manifest.v4",
        "manifest schema mismatch",
    )
    require(
        receipt.get("schema_version")
        == "lemma-portfolio.dependency-compression-generation.v4",
        "receipt schema mismatch",
    )
    require(
        manifest.get("generation_receipt", {}).get("sha256")
        == build.sha256_path(paths["receipt"]),
        "receipt commitment mismatch",
    )
    require(
        receipt.get("builder_identity", {}).get("content_sha256")
        == build.sha256_path(Path(build.__file__).resolve()),
        "builder content mismatch",
    )
    require(
        receipt.get("construction_diagnostics_script_sha256")
        == build.sha256_path(Path(construction_diagnostics.__file__).resolve()),
        "construction-diagnostics script mismatch",
    )
    require(
        receipt.get("pinned_lean_audit_script_sha256")
        == build.sha256_path(Path(build.__file__).with_name("audit_pinned_lean.py")),
        "pinned-Lean audit script mismatch",
    )
    require(
        receipt.get("static_bundle_audit_script_sha256")
        == build.sha256_path(Path(__file__).resolve()),
        "static audit script mismatch",
    )
    config = build.construction_config()
    require(receipt.get("construction_config") == config, "construction config mismatch")
    require(
        receipt.get("construction_config_sha256")
        == build.sha256_bytes(build.canonical_json_bytes(config)),
        "construction config hash mismatch",
    )
    source = receipt.get("source")
    require(isinstance(source, dict), "source receipt missing")
    require(
        source.get("source_generation_receipt_sha256")
        == build.sha256_path(common.V1_RECEIPT_PATH),
        "source manifest mismatch",
    )
    inventory = build.verified_parquet_inventory(parquet_dir)
    require(source.get("parquet_inputs") == inventory, "bound Parquet inventory mismatch")
    require(
        source.get("recomputed_parquet_inventory_sha256")
        == build.sha256_bytes(build.canonical_json_bytes({"parquet_inputs": inventory})),
        "Parquet inventory hash mismatch",
    )

    payloads = {key: path.read_bytes() for key, path in paths.items() if key not in {"manifest", "receipt", "private_manifest"}}
    outputs = receipt.get("outputs")
    require(isinstance(outputs, dict), "output commitments missing")
    expected_output_hashes = {
        "calibration_public_sha256": "calibration_public",
        "calibration_a_public_sha256": "calibration_a_public",
        "calibration_b_public_sha256": "calibration_b_public",
        "calibration_labels_commitment_sha256": "calibration_labels",
        "calibration_a_labels_sha256": "calibration_a_labels",
        "calibration_b_labels_sha256": "calibration_b_labels",
        "blind_public_sha256": "blind_public",
        "blind_labels_commitment_sha256": "blind_labels",
        "gated_construction_diagnostics_sha256": "diagnostics",
    }
    for receipt_key, payload_key in expected_output_hashes.items():
        require(
            outputs.get(receipt_key) == build.sha256_bytes(payloads[payload_key]),
            "output hash mismatch",
        )
    require(
        payloads["calibration_a_public"] + payloads["calibration_b_public"]
        == payloads["calibration_public"],
        "calibration public views mismatch",
    )
    require(
        payloads["calibration_a_labels"] + payloads["calibration_b_labels"]
        == payloads["calibration_labels"],
        "calibration label views mismatch",
    )

    calibration_public = build.load_jsonl(paths["calibration_public"])
    calibration_labels = build.load_jsonl(paths["calibration_labels"])
    blind_public = build.load_jsonl(paths["blind_public"])
    blind_labels = build.load_jsonl(paths["blind_labels"])
    diagnostics = construction_diagnostics.render_bundle(
        calibration_public,
        blind_public,
        calibration_bytes=payloads["calibration_public"],
        blind_bytes=payloads["blind_public"],
    )
    require(
        build.canonical_json_bytes(diagnostics) == payloads["diagnostics"],
        "construction diagnostics replay mismatch",
    )
    selection_ledger = {
        split_name: [
            {
                "episode_id": row["episode_id"],
                "source_module": row["source_module"],
                "candidate_sources": row["candidate_sources"],
                "target_sources": row["target_sources"],
            }
            for row in rows
        ]
        for split_name, rows in (
            ("calibration", calibration_labels),
            ("blind", blind_labels),
        )
    }
    selection_hash = build.sha256_bytes(build.canonical_json_bytes(selection_ledger))
    require(
        receipt.get("private_selection_ledger_sha256") == selection_hash,
        "selection ledger mismatch",
    )
    require(
        private_manifest.get("private_selection_ledger_sha256") == selection_hash,
        "private selection ledger mismatch",
    )
    require(
        private_manifest.get("public_manifest_sha256") == build.sha256_path(paths["manifest"]),
        "private/public manifest binding mismatch",
    )
    require(
        private_manifest.get("blind_labels_sha256") == build.sha256_path(paths["blind_labels"]),
        "private blind-label binding mismatch",
    )

    rebuilt = build.build_bundle(parquet_dir)
    expected_rows = rebuilt[:4]
    actual_rows = (calibration_public, calibration_labels, blind_public, blind_labels)
    require(expected_rows == actual_rows, "full deterministic byte-content replay mismatch")
    require(receipt.get("summary") == rebuilt[4], "receipt summary replay mismatch")
    require(manifest.get("summary") == rebuilt[4], "manifest summary replay mismatch")
    require(
        receipt.get("evaluated_blind_predictions_read_or_used_by_builder") == 0,
        "blind prediction-use disclosure mismatch",
    )
    return {
        "schema_version": "lemma-portfolio.static-bundle-audit.v4",
        "status": "pass",
        "public_manifest_sha256": build.sha256_path(paths["manifest"]),
        "generation_receipt_sha256": build.sha256_path(paths["receipt"]),
        "calibration_public_sha256": build.sha256_path(paths["calibration_public"]),
        "calibration_labels_sha256": build.sha256_path(paths["calibration_labels"]),
        "blind_public_sha256": build.sha256_path(paths["blind_public"]),
        "blind_labels_sha256": build.sha256_path(paths["blind_labels"]),
        "private_selection_ledger_sha256": selection_hash,
        "calibration_episodes": len(calibration_public),
        "blind_episodes": len(blind_public),
        "parquet_shards_rehashed": len(inventory),
        "blind_labels_mode": _mode(paths["blind_labels"]),
        "private_names_emitted": 0,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-dir", type=Path, required=True)
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--parquet-dir", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = audit(
            public_dir=args.public_dir,
            private_dir=args.private_dir,
            parquet_dir=args.parquet_dir,
        )
    except Exception:
        parser = _parser()
        parser.exit(2, "error: v4 static bundle audit failed closed\n")
    sys.stdout.write(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
