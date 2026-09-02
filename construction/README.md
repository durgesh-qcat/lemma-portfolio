# Construction and pinned-Lean audit

This directory supplies the exact V4 builder, construction diagnostics,
pinned-Lean wrapper, static audit, and their unit tests.  Small prior-split
files used only for overlap exclusion are included so the builder imports and
tests remain self-contained.

Run the standard-library unit tests from this directory:

```sh
python3 -m unittest apibench.hard_blind_v4.test_hard_blind_v4 -v
```

To repeat the aggregate blind-label extraction, use a clean Mathlib checkout at
commit `db584cd6d46c92f209a44c0f1c829460d327499d`, Lean 4.33.0, and a `lake`
binary that resolves that checkout.  The clean Mathlib checkout itself may be
used as the Lean project.  From this directory run:

```sh
python3 -m apibench.hard_blind_v4.audit_pinned_lean \
  --manifest ../provenance/manifest.preinference.json \
  --generation-receipt ../provenance/generation_receipt.json \
  --public ../data/test.public.jsonl \
  --labels ../data/test.labels.jsonl \
  --split blind \
  --mathlib-checkout /absolute/path/to/mathlib4 \
  --lean-project /absolute/path/to/mathlib4 \
  --lake /absolute/path/to/lake \
  --timeout 600 > /tmp/blind.pinned_lean_audit.json
```

Compare the resulting aggregate JSON with
`../provenance/blind.pinned_lean_audit.json`.  The wrapper deliberately sends
private declaration names only through Lean's standard input and emits no names.

Repeating the original mining search additionally requires DuckDB and the exact
256 Parquet shards named, sized, and hashed in the generation receipt.  Those
211 MiB of source shards are intentionally outside ordinary Git history.  With
them in one directory:

```sh
python3 -m pip install -r requirements-construction.txt
python3 -m apibench.hard_blind_v4.build_hard_blind_v4 \
  --parquet-dir /absolute/path/to/parquet-shards \
  --dry-run
```

The requirements file pins `duckdb==1.5.5`, matching the released construction
receipt.  This full mining pass is substantially slower than score verification
and is not required to validate the reported model scores.

The receipt's per-file hashes, rather than a mutable hosting branch, are the
authoritative source identity.
