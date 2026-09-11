#!/usr/bin/env python3
"""Verify frozen release inventories using explicit, hash-bound relocations."""

import hashlib
import json
from pathlib import Path, PurePosixPath
import re


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def repository_path(root, relative):
    """Reject paths that leave the repository, including through a symlink."""
    path = PurePosixPath(relative)
    require(not path.is_absolute() and path.parts and ".." not in path.parts,
            f"Invalid historical path: {relative}")
    result = root / path
    require(result.resolve().is_relative_to(root.resolve()),
            f"Historical path leaves repository: {relative}")
    return result


def verify_historical_baseline(root, manifest_path):
    """Check every baseline row at its original or explicitly archived location.

    Archived copies are checked even when the current file still has the old
    bytes. A changed file without a declared, matching historical copy fails.
    The frozen inventory itself is never rewritten and no row is skipped.
    """
    root = Path(root).resolve()
    manifest_path = Path(manifest_path).resolve()
    relative_manifest = manifest_path.relative_to(root).as_posix()
    index = json.loads((root / "provenance/PRE_SUBMISSION_FILES.json").read_text())
    require(index["schema_version"] == "lemma-portfolio.historical-relocations.v1",
            "Unknown historical relocation schema")
    require(relative_manifest in index["baselines"],
            f"Unregistered historical inventory: {relative_manifest}")
    baseline = index["baselines"][relative_manifest]
    require(sha256(manifest_path) == baseline["manifest_sha256"],
            f"Frozen baseline inventory changed: {relative_manifest}")
    require(re.fullmatch(r"[0-9a-f]{40}", baseline["source_commit"]) is not None,
            "Historical source commit must be a full Git object ID")

    expected_files = {}
    for line in manifest_path.read_text().splitlines():
        expected, relative = line.split("  ", 1)
        require(re.fullmatch(r"[0-9a-f]{64}", expected) is not None,
                f"Invalid baseline hash: {relative}")
        require(relative not in expected_files, f"Duplicate baseline path: {relative}")
        expected_files[relative] = expected

    relocations = baseline["relocations"]
    require(set(relocations) <= set(expected_files),
            f"Relocation absent from frozen inventory: {relative_manifest}")
    current_count = archived_count = 0
    for relative, expected in expected_files.items():
        current = repository_path(root, relative)
        archived = relocations.get(relative)
        if archived:
            require(archived["sha256"] == expected,
                    f"Relocation hash differs from original inventory: {relative}")
            location = archived["path"]
            require(location.startswith(("provenance/pre_submission/", "paper/historical/")),
                    f"Historical copy must have an explicit archive location: {relative}")
            snapshot = repository_path(root, location)
            require(snapshot.is_file() and sha256(snapshot) == expected,
                    f"Historical baseline copy missing or changed: {location}")
        if current.is_file() and sha256(current) == expected:
            current_count += 1
        else:
            require(archived is not None,
                    f"Original release changed without a matching historical copy: {relative}")
            archived_count += 1

    print(f"PASS: {relative_manifest}: all {len(expected_files)} original hashes "
          f"({current_count} current, {archived_count} relocated; "
          f"{len(relocations)} historical copies verified)")
    return {"files": len(expected_files), "current": current_count,
            "relocated": archived_count, "historical_copies": len(relocations)}


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    index = json.loads((root / "provenance/PRE_SUBMISSION_FILES.json").read_text())
    for manifest in sorted(index["baselines"]):
        verify_historical_baseline(root, root / manifest)
