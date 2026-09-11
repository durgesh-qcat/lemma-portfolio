# Construction and pinned-Lean audit

This directory contains the V4 builder, the construction filters, the
pinned-Lean and static checks, and their tests. The small files from earlier
splits are included only to check that no old statement was reused. Everything
needed to import the builder and run its tests is in this archive.

The historical `name_visible_in_type` check rejects exact source-name tokens.
It does not reject every generated or dotted identifier which begins with a
source declaration name. In the test split, a post-hoc prefix scan found 33
such occurrences in 25 source-name/statement pairs involving 24 source
declarations across 6/60 episodes. In development it found 5 occurrences in 5
pairs involving 5 source declarations across 2/30 episodes. This
limitation is documented in `../docs/DATA_CARD.md`;
the frozen construction files and receipts are preserved unchanged.

Run the standard-library unit tests from this directory:

```sh
python3 -m unittest apibench.hard_blind_v4.test_hard_blind_v4 -v
```

To repeat the aggregate test-label extraction, use a clean Mathlib checkout at
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
`../provenance/blind.pinned_lean_audit.json`.  The wrapper sends declaration
names only through Lean's standard input and does not write them to its log.

To check development, use the same command with
`--public ../data/development.public.jsonl`,
`--labels ../data/development.labels.jsonl`, and `--split calibration`, and
write its output to a separate file. Compare with
`../provenance/calibration.pinned_lean_audit.json`. The compiler commit must be
`d8b18978322de05a8f3dba51ef03cf5461676c17`; the wrapper checks this as well as
Lean 4.33.0 and the Mathlib commit. The Mathlib checkout must have its matching
dependencies and built imports available; the audit does not install them.

Repeating the original mining search additionally requires DuckDB and the exact
256 Parquet shards named, sized, and hashed in the generation receipt.  Those
256 shards total 220,228,123 bytes (about 210 MiB) and are not included in this
submission archive. They come from these upstream v4.33.0 dataset revisions:

| Upstream repository | Immutable revision | Local filename mapping |
| --- | --- | --- |
| [mathlib-const-dep](https://huggingface.co/datasets/mathlib-initiative/mathlib-const-dep/tree/e9d0e67a523ab6f233d3bae11af92392bf1e2947) | `e9d0e67a523ab6f233d3bae11af92392bf1e2947` | `part-NNN.parquet` → `dep-NNN.parquet` |
| [mathlib-types](https://huggingface.co/datasets/mathlib-initiative/mathlib-types/tree/8df32d8a696e51e4850382f9efc2e6ab12651422) | `8df32d8a696e51e4850382f9efc2e6ab12651422` | `part-NNN.parquet` → `types-NNN.parquet` |

In each row `NNN` runs from `000` to `127`. The original source receipt did
not save immutable Hugging Face repository revisions. The mapping above was
resolved from the upstream v4.33.0 upload history for this submission; it does
not alter or backdate that receipt. As a cross-check, the upstream SHA-256
values for [dependency part-000](https://huggingface.co/datasets/mathlib-initiative/mathlib-const-dep/blob/e9d0e67a523ab6f233d3bae11af92392bf1e2947/part-000.parquet)
and [type part-000](https://huggingface.co/datasets/mathlib-initiative/mathlib-types/blob/8df32d8a696e51e4850382f9efc2e6ab12651422/part-000.parquet)
match their local receipt entries. Every downloaded shard must still pass the
full check below. Do not substitute the current `main`: it has advanced beyond
v4.33.0.

One download recipe, using the [Hugging Face CLI](https://huggingface.co/docs/huggingface_hub/guides/cli),
is below. Run it from this construction directory in your chosen Python
environment. It creates a fresh temporary download directory and leaves the
submission files unchanged. `huggingface_hub` is needed only for this download
recipe, not for scoring or mining once the shards are present.

```sh
python3 -m pip install -r requirements-construction.txt
python3 -m pip install huggingface_hub
PARQUET_WORK=$(mktemp -d)
hf download mathlib-initiative/mathlib-const-dep --repo-type dataset \
  --revision e9d0e67a523ab6f233d3bae11af92392bf1e2947 \
  --include 'part-*.parquet' --local-dir "$PARQUET_WORK/dependencies"
hf download mathlib-initiative/mathlib-types --repo-type dataset \
  --revision 8df32d8a696e51e4850382f9efc2e6ab12651422 \
  --include 'part-*.parquet' --local-dir "$PARQUET_WORK/types"
mkdir "$PARQUET_WORK/shards"
for shard in "$PARQUET_WORK/dependencies"/part-*.parquet; do
  shard_name=${shard##*/}
  cp "$shard" "$PARQUET_WORK/shards/dep-${shard_name#part-}"
done
for shard in "$PARQUET_WORK/types"/part-*.parquet; do
  shard_name=${shard##*/}
  cp "$shard" "$PARQUET_WORK/shards/types-${shard_name#part-}"
done
python3 -c 'import sys; from pathlib import Path; from apibench.hard_blind_v4.build_hard_blind_v4 import verified_parquet_inventory; print(len(verified_parquet_inventory(Path(sys.argv[1]))), "verified shards")' "$PARQUET_WORK/shards"
```

The last command must report `256 verified shards`; it checks the exact file
inventory, byte sizes, and SHA-256 digests against the frozen source receipt.
Stop on any error, rather than running the search on substitute inputs. If the
shards are already available elsewhere, pass that directory to the same check.
After it succeeds, repeat the deterministic mining search:

```sh
python3 -m apibench.hard_blind_v4.build_hard_blind_v4 \
  --parquet-dir "$PARQUET_WORK/shards" \
  --dry-run
```

The requirements file pins `duckdb==1.5.5`, which is the version used for the
released construction.  The full mining pass is much slower than score
verification and is not needed to check the model scores in the paper.

The dry run reconstructs the development/test records in memory and checks their
frozen public and label hashes without writing replacement release files. Full
construction rules, tokenization, all 20 selectors, and the scope of the Lean
checks are documented in [REPRODUCIBILITY.md](../../REPRODUCIBILITY.md).
