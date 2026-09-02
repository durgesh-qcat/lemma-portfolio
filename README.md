# LemmaPortfolio

LemmaPortfolio tests a joint premise-selection question for Lean: when one
three-lemma set must serve eight related goals, which set covers the most
historical direct dependencies?  Each episode contains 16 name-masked
candidates and eight name-masked targets.  The scorer enumerates all 560
three-candidate portfolios and accepts every maximizer.

This repository accompanies *LemmaPortfolio: Choosing One Small Lemma Set for
Many Lean Goals*.  It contains the 30 development and 60 test episodes, released
labels, the supplied response PDF and its audited transcription, deterministic
baselines, scores, construction/audit receipts, and the complete paper source.

## Reported V4 scores

The headline is **exact optimal-portfolio accuracy out of 60**, not a score out
of 30 and not target-level partial credit.

| Visible consumer label | Exact optimum | Target coverage | Valid |
|---|---:|---:|---:|
| GPT SOL 5.6 Pro | 25/60 (41.7%) | 299/480 (62.3%) | 55/60 |
| DeepSeek Instant + DeepThink | 1/60 (1.7%) | 252/480 (52.5%) | 60/60 |
| DeepSeek Expert + DeepThink | 7/60 (11.7%) | 276/480 (57.5%) | 60/60 |
| Qwen 3.8 Max - Thinking | 12/60 (20.0%) | 259/480 (54.0%) | 55/60 |
| Qwen 3.7 Plus - Thinking | 6/60 (10.0%) | 243/480 (50.6%) | 60/60 |

“Target coverage” is partial credit: it counts how many of the eight targets a
selected triple touches.  “Exact optimum” asks whether no other triple covers
more targets.  GPT SOL therefore covered 62.3% of all targets while selecting a
maximizing triple on 41.7% of episodes.  The two columns are intentionally not
interchangeable.

## One-command verification

From the repository folder, run:

```sh
python3 verify_release.py
```

On macOS, a nontechnical user may instead double-click `RUN_ME.command`.

This is free and offline.  It uses only the Python standard library, verifies
every published file hash, reconstructs every optimum from the released
incidence rows, reparses the response transcription, regenerates both baselines,
and recomputes every reported score.  It does not call a model and does not need
Lean, an API key, or a paid account.  Python 3.10 or newer is required.

For a clean independent rerun of the scoring stage:

```sh
python3 tools/score_release.py --release-root . --output-root /tmp/lp-results
```

The generated files in `/tmp/lp-results` should be byte-identical to the
corresponding `responses/*.json` and `results/*` files in this repository.

## Repository map

- `data/`: public development/test episodes and released labels;
- `responses/`: original response PDF, extracted text, canonical transcription,
  and response-order audit;
- `results/`: baseline predictions, aggregate scores, item scores, and the
  structured-support comparison;
- `provenance/`: dataset commitment, generation receipt, and Lean/static audit
  receipts;
- `development_evidence/`: the frozen 15-item development check reported as
  6/15 in the paper;
- `construction/`: the V4 builder, audit wrapper, tests, and reproduction notes;
- `tools/`: deterministic scorer and hash-manifest builder;
- `paper/`: MATH-AI 2026 source, official style file, and checked PDFs; and
- `docs/`: plain-language GitHub, Overleaf, evidence, and reproduction notes.

## Evidence boundary

The public test-file hash and the label-file digest were recorded on 1 September
2026.  The evaluator received the response PDF on 2 September 2026.  The PDF
contains visible response text but not provider-side logs, per-chat timestamps,
account-tier evidence, or screenshots.  Consequently, this release makes the
scores and response alignment independently checkable, but it does not claim
that the serving checkpoint or fresh-chat procedure can be independently
verified.  See `docs/PROVENANCE.md` for the exact anomalies and policy.

## What this benchmark does not measure

The labels record direct constants in historical elaborated proof values.  They
do not establish logical necessity or show that adding a selected lemma causes a
new prover to succeed.  The candidate pool is closed, costs are uniform, and the
test set is a deliberately conditioned stress set.

## Review anonymity

Keep this named repository private during double-blind review and do not put its
URL in the anonymous manuscript.  The separate anonymous Overleaf ZIP contains
only submission-safe paper material.  Public release should wait until the
venue's anonymity policy permits it.

## License and citation

Code and original documentation are released under Apache-2.0.  Mathlib-derived
statement text retains the attribution described in `NOTICE`; the paper,
official style file, and captured responses have separate terms summarized in
`LICENSES.md`.  Citation metadata is in `CITATION.cff`.
