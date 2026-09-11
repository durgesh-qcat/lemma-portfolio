#!/usr/bin/env python3
"""Create SHA256SUMS for the release, excluding Git metadata and itself."""

from pathlib import Path
import hashlib


root = Path(__file__).resolve().parents[1]
rows = []
for path in sorted(root.rglob("*")):
    relative = path.relative_to(root)
    if (
        not path.is_file()
        or path.name == "SHA256SUMS"
        or ".git" in relative.parts
        or "__pycache__" in relative.parts
    ):
        continue
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    rows.append(f"{digest}  {relative.as_posix()}\n")
(root / "SHA256SUMS").write_text("".join(rows), encoding="utf-8")
print(f"Wrote {len(rows)} hashes")
