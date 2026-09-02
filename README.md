# LemmaPortfolio

LemmaPortfolio tests a joint premise-selection question for Lean: when one
three-lemma set must serve eight related goals, which set covers the most
historical direct dependencies?  Each episode contains 16 name-masked
candidates and eight name-masked targets.  The scorer enumerates all 560
three-candidate portfolios and accepts every maximizer.

This repository accompanies *LemmaPortfolio: Choosing One Small Lemma Set for
Many Lean Goals*.  It contains the 30 development and 60 test episodes, released
labels, the supplied response PDFs and their audited transcriptions, deterministic
baselines, scores, construction/audit receipts, and the complete paper source.

It supports three distinct reproducibility tasks:

1. **Validate the reported results** offline with one command.
2. **Evaluate another model** with the exact released prompts and the generic
   prediction scorer.
3. **Reconstruct the benchmark** from the pinned Mathlib source snapshot and
   rerun the Lean audit.

These levels should not be conflated.  Score validation is deterministic.
Fresh model inference is not bit-for-bit reproducible because consumer systems
may change and do not expose every serving or decoding parameter.

## Reported V4 scores

The headline is **exact optimal-portfolio accuracy out of 60**, not a score out
of 30 and not target-level partial credit.

| Visible consumer label | Exact optimum | Target coverage | Valid |
|---|---:|---:|---:|
| GPT SOL 5.6 Pro | 25/60 (41.7%) | 299/480 (62.3%) | 55/60 |
| GPT SOL 5.6 (xhigh) | 18/60 (30.0%) | 305/480 (63.5%) | 60/60 |
| DeepSeek Instant + DeepThink | 1/60 (1.7%) | 252/480 (52.5%) | 60/60 |
| DeepSeek Expert + DeepThink | 7/60 (11.7%) | 276/480 (57.5%) | 60/60 |
| Qwen 3.8 Max - Thinking | 12/60 (20.0%) | 259/480 (54.0%) | 55/60 |
| Qwen 3.7 Plus - Thinking | 6/60 (10.0%) | 243/480 (50.6%) | 60/60 |

“Target coverage” is partial credit: it counts how many of the eight targets a
selected triple touches.  “Exact optimum” asks whether no other triple covers
more targets.  The Pro row had the highest exact score, whereas xhigh had the
highest target coverage.  The two columns are intentionally not interchangeable.

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

## Evaluate another model

The exact twelve direct prompt files used for the 60 test episodes and the four
structured-support prompts are in `prompts/`.  Start with
[`prompts/START_HERE.txt`](prompts/START_HERE.txt), which specifies fresh-chat
boundaries, order, disabled tools, retry policy, and what evidence to retain.

Save each model's JSON-only response as a separate file and score all shards at
once.  For example:

```sh
python3 tools/score_predictions.py \
  --predictions scratch_runs/my_model/*.json \
  --display-label "Exact model and mode shown by the provider" \
  --output scratch_runs/my_model/score.json
```

Missing, malformed, duplicate-ID, wrong-budget, or out-of-pool selections score
zero, exactly as in the paper.  The denominator remains 60.  The command calls
no model and uses no package outside the Python standard library.

For a scientifically useful new row, record the exact visible product/model/mode,
date, chat boundaries, tool settings, raw responses, and every retry or error
*before* looking at `data/test.labels.jsonl` or the existing results.  Because
the labels are now public, this is an honor-system rerun rather than a newly
sealed blind evaluation.  See [`docs/RERUN_MODELS.md`](docs/RERUN_MODELS.md)
for the complete procedure and evidence boundary.

## Work on the paper

The checked anonymous review PDF, technical supplement, and author-check PDF
are in `paper/`.  Their editable LaTeX sources are in `paper/source/`.  A
co-author with repository access can clone the repository, edit the source on a
separate Git branch, and open a pull request.  Plain-language instructions are
in [`docs/COLLABORATING.md`](docs/COLLABORATING.md).

- [Anonymous review PDF with supplement](paper/LemmaPortfolio_MATHAI2026_anonymous_review_with_supplement.pdf)
- [Separate anonymous technical supplement](paper/LemmaPortfolio_MATHAI2026_anonymous_technical_supplement.pdf)
- [Named author-check preprint](paper/LemmaPortfolio_MATHAI2026_author_check_preprint.pdf)

## Repository map

- `data/`: public development/test episodes and released labels;
- `responses/`: both original response PDFs, extracted text, canonical transcriptions,
  and response-order audit;
- `results/`: baseline predictions, aggregate scores, item scores, and the
  structured-support comparisons;
- `provenance/`: dataset commitment, generation receipt, and Lean/static audit
  receipts;
- `development_evidence/`: the frozen 15-item development check reported as
  6/15 in the paper;
- `prompts/`: the exact 12 direct and four structured-support prompt files,
  checksum manifest, and capture instructions;
- `construction/`: the V4 builder, audit wrapper, tests, and reproduction notes;
- `examples/`: example input for scoring a new model;
- `tools/`: deterministic scorer and hash-manifest builder;
- `paper/`: MATH-AI 2026 source, official style file, and checked PDFs; and
- `docs/`: plain-language GitHub, Overleaf, evidence, and reproduction notes.

## Evidence boundary

The public test-file hash and the label-file digest were recorded on 1 September
2026 before the captured responses.  The two PDFs contain visible response text
but not provider-side logs, per-chat timestamps, account-tier evidence, or
screenshots.  Consequently, this release makes the
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

For review, use the separately prepared anonymous reproducibility ZIP as
supplementary material.  After acceptance, make the repository public, create a
versioned release, and add its permanent URL to the camera-ready paper.

## License and citation

Code and original documentation are released under Apache-2.0.  Mathlib-derived
statement text retains the attribution described in `NOTICE`; the paper,
official style file, and captured responses have separate terms summarized in
`LICENSES.md`.  Citation metadata is in `CITATION.cff`.
