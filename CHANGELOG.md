# Changes

## Results documentation — September 22, 2026

Expand [RESULTS.md](RESULTS.md) with the exact oracle row, exhaustive-search
counts, greedy and frequency controls, predicted-support tie bounds, masking
sensitivity, selection patterns, and uncertainty notes. Separate the main
CLI/API runs from preliminary web captures, link each analysis to its archived
records, and use the compatible verification entry point. Update the result-file
and oracle guides to explain where the oracle values are recorded.

This documentation update preserves the archived PDF, ZIP, all 309 extracted
files, saved responses, labels, and machine-readable scientific results.

## 4.0.1: Python 3.10 verification compatibility

GitHub CI exposed an integer-versus-float comparison in the archived verifier:
a recorded normalized-coverage percentage of `80` can recompute as
`79.99999999999999` on Python 3.10. The repository wrapper applies the existing
numeric tolerance only to this continuous metric, while preserving exact
counts and the complete supporting archive. It runs the same seven checks.
See [verification details](docs/VERIFICATION.md).

## Benchmark materials synchronization — September 11, 2026

This update synchronizes the repository with the technical write-up,
**LemmaPortfolio: Shared-Budget Lemma Selection for Multiple Lean Goals**.

- Preserve the author's final PDF and supplementary ZIP byte for byte, record
  their archived hashes, and expose all 309 supplementary files for browsing.
- Update the main README, citation, write-up guide, collaboration and Overleaf
  instructions, provenance, data card, and evaluation instructions.
- Present the seven CLI/API runs used in the main write-up separately from the
  six preliminary web response sets, with consolidated machine-readable results.
- Include final masking sensitivity, all 780 direct-answer selection patterns,
  frequency-tie geometry, target-wise diagnostics, and replacement analyses.
- Add an independent oracle verifier for all 50,400 portfolios across 90
  episodes, all maximizing portfolios, greedy tie controls, and frequency ties.
- Extend the one-command verifier and CI to check the exact PDF/ZIP pairing,
  extracted files, archived analyses, result mirrors, original scores, richer
  historical follow-up receipts, and regression tests.
- Retain older write-up PDFs and LaTeX under `paper/historical/2026-09-05/` and
  preserve original manifest-bound files with explicit historical mappings.

No new model inference was performed. Existing raw responses and benchmark
labels retain their provenance. The final LaTeX source was not supplied;
the archived earlier source is not represented as the source of the final PDF.

The earlier `v4.0.0-rc1` release remains a historical working release.
