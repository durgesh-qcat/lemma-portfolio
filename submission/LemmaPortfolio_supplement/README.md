# LemmaPortfolio: Shared-Budget Lemma Selection for Multiple Lean Goals

This is the anonymous reproducibility archive accompanying the paper PDF.
It contains the benchmark, prompts, saved model answers, scoring and construction
code, evaluation settings, and supporting checks. It contains no manuscript
drafts, revision history, or extra paper PDFs. The two PDFs under
`original_release/responses/` are original model-answer evidence.

## Reproduce the results

Unzip the archive. From the resulting `LemmaPortfolio_supplement` directory,
with Python 3.10 or newer, run:

```sh
python3 -B verify_all.py
```

This uses only the Python standard library. No network, model calls, credentials,
Lean installation, or third-party Python package is needed. It checks every file
hash; reconstructs the optimal portfolios; reparses the original responses;
rebuilds both baselines, all thirteen direct model rows and the target-wise
comparisons; and repeats the construction-tie and candidate-replacement analyses.
It also re-scores all thirteen direct-response sets after the fixed six-episode
masking exclusion, checks frequency and greedy matches for all 780 answer slots,
and recomputes per-run nominal Wilson intervals. It also enumerates the frequency
tie sets on all sixty test episodes and checks the descriptive follow-up error
partition (184 outside the sets, 52 inside sets containing an optimum, and 10
inside sets containing none). An optimum belongs to a frequency-maximizing set
on 53/60 episodes; these sets have mean size 6.8, median 4, and range 1--35.
It also runs the parser, scorer and construction unit tests. It ends with
`ALL SUBMISSION CHECKS PASSED`. Intermediate files are written to temporary
directories, leaving this archive unchanged.

To check that the PDF is the one paired with this archive, give its path:

```sh
python3 -B verify_all.py --paper /path/to/LemmaPortfolio.pdf
```

The PDF's SHA-256 is recorded in `MANIFEST.json`; its contents are not duplicated
in the archive. No previous manuscript version is needed by any verifier.

Individual checks, also run by the command above:

```sh
python3 -B original_release/verify_release.py
python3 -B verify_followups.py
python3 -B evaluation/verify_evaluation.py
python3 -B verify_descriptive.py
python3 -B verify_results.py
python3 -B verify_masking_sensitivity.py
python3 -B verify_selection_patterns.py
```

Counts, IDs, selections and optimal sets must match exactly. Comparisons allow
only negligible platform-dependent differences in floating-point calculations.

## Where the paper's supporting material is

| Material mentioned in the paper | Location in this archive |
|---|---|
| All 30 development and 60 test episodes, labels and optima | `original_release/data/` |
| Additional model-level scores: share of maximum coverage and occurrence recall | `RESULTS.md` and `results/paper_results.json` |
| All construction settings and twenty fixed selection rules | `REPRODUCIBILITY.md`, `original_release/construction/` |
| Greedy and predicted-coverage tie analyses | `REPRODUCIBILITY.md`, `original_release/results/posthoc_math_audit.json`, `original_release/results/posthoc_predicted_tie_audit.json`, and `followups/2026-09-05/astra_diagnostic/score.json` |
| Exact prompts and original six response sets | `original_release/prompts/`, `original_release/responses/` |
| Seven follow-up runs and the Astra target-wise diagnostic | `followups/2026-09-05/`; prompt-to-response mappings in `MANIFEST.json` |
| Model settings, execution procedure, available calling code and Fable 5.1 system prompt | `evaluation/`; original procedure in `original_release/provenance/manual_chat/` |
| Random and TF-IDF baselines | `REPRODUCIBILITY.md`, `original_release/tools/score_release.py`, `original_release/results/` |
| One-target-short replacement analysis and per-answer records | `descriptive/` |
| Masking-exclusion sensitivity on all thirteen direct-response sets | `results/masking_sensitivity.json`, `results/masking_sensitivity.md`, and `verify_masking_sensitivity.py` |
| Frequency/greedy tie-aware matches, matched-degree overlap comparisons, and nominal Wilson intervals | `results/selection_patterns.json`, `results/selection_patterns.md`, and `verify_selection_patterns.py` |
| Exact source versions and Lean annotation checks | `original_release/provenance/`, `original_release/construction/README.md` |
| Instructions for evaluating new responses | `evaluation/README.md`, `original_release/docs/RERUN_MODELS.md` |
| Licenses and source attribution | `original_release/LICENSE`, `original_release/LICENSES.md`, `original_release/NOTICE` |

The consolidated results distinguish the original six response sets from the
seven follow-up runs. Every direct row has a denominator of 60, including five
missing Pro answers and five malformed Qwen 3.8 answers. Repeated runs use the
same episodes; they are not additional independent benchmark problems. The main
paper table presents the seven CLI/API runs; all six original web-interface
rows remain in the technical supplement as preliminary evidence.

## Recheck Lean annotations or rerun mining

The offline score checks use the released proof-use annotations. To independently
re-extract them, follow `original_release/construction/README.md`: use Lean
4.33.0 and Mathlib commit `db584cd6d46c92f209a44c0f1c829460d327499d`.
The included extraction code checks all 720 target proofs and checks statement
expressions for collisions within each episode.

Rerunning the mining additionally needs DuckDB 1.5.5 and 256 external Parquet
shards (about 210 MiB), not bundled here. The construction README gives pinned
download locations; `original_release/provenance/generation_receipt.json`
records every required filename, size and SHA-256. The external shards are not
needed to reproduce any model score or to run the pinned-Lean annotation check.

## Evidence and scope

`PROVENANCE.md` and `evaluation/README.md` distinguish saved-answer verification
from rerunning model inference and identify unavailable execution records.
The archive preserves the frozen scientific protocols; it does not reconstruct
missing historical logs or guarantee identical outputs from a future deployment.
Test labels are included for verification and must not be supplied to evaluated
models. Save any new experimental outputs outside this checksummed archive.
