# Scientific verification

The submission was checked from the saved source data and responses. These
checks do not call a model or establish the identity of remote serving weights.

- Independent finite enumeration checked all 50,400 portfolios across the
  90 episodes, every optimal set, construction restrictions, all twenty fixed
  selectors, and development/test separation.
- The original response text was reparsed, and the follow-up responses were
  independently scored. All thirteen model rows, the baselines, both additional
  scores, invalid-answer handling, and target-wise comparisons agree.
- Exact-rational random coverage agrees with explicit enumeration for all
  720 targets. The replacement counts and biproduct example agree with the
  stored proof-use sets. Greedy and predicted-coverage tie checks agree.
- Fresh extraction in Lean 4.33.0 recovered all 720 target annotation rows:
  814 test and 386 development candidate-target pairs. There were no changed
  rows or added/removed pairs and no within-episode expression collisions.
  The new aggregate outputs equal the included original audit receipts.
- All 256 cached Parquet files matched the recorded filenames, byte sizes and
  SHA-256 hashes. A full deterministic mining replay with DuckDB 1.5.5 reproduced
  all nine recorded output hashes, the construction configuration, selection
  ledger and mining-summary counters. No replacement release was materialized.

The Lean check used an existing exact-version checkout with matching compiled
dependencies; it was not a clean rebuild of all Mathlib. The mining replay used
the hash-verified cached shards, not a fresh network download. Instructions for
repeating both checks are in `original_release/construction/README.md`.

For the self-contained saved-result checks, run `python3 -B verify_all.py` from
this archive. `RESULTS.md` and `results/paper_results.json` include all model-level
additional scores. The paper-to-file map is in `README.md`. The accompanying
PDF's hash is in `MANIFEST.json`; the PDF is submitted separately.
