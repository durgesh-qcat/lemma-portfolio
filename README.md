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
2. **Evaluate another model** with the preserved released prompt packet and
   generic scorers.
3. **Reconstruct the benchmark** from the pinned Mathlib source snapshot and
   rerun the Lean audit.

These levels should not be conflated.  Score validation is deterministic.
Fresh model inference is not bit-for-bit reproducible because consumer systems
may change and do not expose every serving or decoding parameter.

## Original V4 consumer scores

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

## Final Codex follow-up results — 5 September 2026

The following are **post-release follow-up experiments**, separate from the
original frozen consumer evaluation above. Dates use Pacific time; the capture
receipts use UTC. The original data, consumer scores, and paper PDFs are unchanged.

| Recorded model / effort / run | Exact optimum | Target coverage | Valid | Inference time |
|---|---:|---:|---:|---:|
| GPT-6 Astra / xhigh / 1 | 27/60 (45.0%) | 328/480 (68.3%) | 60/60 | 78.6 min |
| GPT-6 Astra / xhigh / 2 | 30/60 (50.0%) | 332/480 (69.2%) | 60/60 | 114.6 min |
| GPT-5.6 Sol / xhigh / 1 | 20/60 (33.3%) | 302/480 (62.9%) | 60/60 | 80.7 min |
| GPT-5.6 Sol / xhigh / 2 | 15/60 (25.0%) | 300/480 (62.5%) | 60/60 | 78.6 min |
| GPT-6 Astra / max / 1 | 30/60 (50.0%) | 335/480 (69.8%) | 60/60 | 147.2 min |

These runs use the same Codex CLI 0.153.0 capture harness, identical released
prompts, and fresh sessions with tools disabled. Across two complete runs each,
mean exact accuracy was **47.5% for Astra xhigh** (sample SD 3.54 percentage points)
and **29.2% for Sol xhigh** (sample SD 5.89 points). Mean target coverage was 68.75%
and 62.71%, respectively. These are repeated evaluations of the same 60 episodes,
not 120 independent benchmark items. Two runs provide limited evidence about
generation variability; equal effort labels do not imply equal compute budgets.
These results are not an apples-to-apples comparison with the consumer rows.

Astra max scored 30/60, matching the second xhigh run's exact score at longer
runtime. The one max run does not establish a reliable accuracy advantage.

On a fresh, matched 20-episode Astra diagnostic, direct selection scored
**8/20 exact (106/160 targets)** versus **4/20 (100/160 targets)** for the primary
structured-support-plus-optimizer pipeline (`q=2`). Re-scoring the same support
rankings with `q=1,2,3,4` gave **2, 4, 4, 4 exact**, respectively. This is evidence
about the tested complete pipeline, not proof that decomposition generally fails.
The export also includes the historical GPT support-width and tie analyses.

**Final status:** all retained runs finished and passed local verification. The
third Sol/Astra pair was cancelled before starting at the author's request to
shorten the queue; this post-hoc operational amendment is disclosed. No inference
remains queued in the shortened Codex workflow. The paper has not yet
incorporated these follow-up results.

A separate completed **Claude Fable 5.1 direct-API capture returned refusals on
all 12 prompts** (0/60 valid). Its strict score is zero, but this is a refusal
outcome, not evidence of mathematical inability. The raw API receipts and
[refusal note](followups/2026-09-05/CLAUDE_REFUSAL.md) are included separately.
Two other Claude captures were incomplete at export and are not scored here.
No OpenRouter result is included.

- **[Start here for writing the paper: final results handoff](followups/2026-09-05/PAPER_HANDOFF.md)**
- [Detailed results and limitations](followups/2026-09-05/REPORT.md)
- [Raw answers, provenance, and reproduction instructions](followups/2026-09-05/README.md)
- [Machine-readable results](followups/2026-09-05/FOLLOWUP_RESULTS.json)
- [Earlier September 4 snapshot (preserved unchanged)](followups/2026-09-04/README.md)

Recompute the completed follow-up scores, support-width sweeps, and comparisons
offline (no model calls):

```sh
python3 followups/2026-09-05/verify.py
```

## One-command verification

From the repository folder, run:

```sh
python3 verify_release.py
```

On macOS, a nontechnical user may instead double-click `RUN_ME.command`.

This is free and offline.  It uses only the Python standard library, verifies
every published file hash, reconstructs every optimum from the released
incidence rows, reparses the response transcription, regenerates both baselines,
and recomputes every original V4 score. It does not call a model and does not need
Lean, an API key, or a paid account.  Python 3.10 or newer is required. It
recomputes the original V4 results; use the additional command above to recompute
the separately published follow-up results.

For a clean independent rerun of the scoring stage:

```sh
python3 tools/score_release.py --release-root . --output-root /tmp/lp-results
```

The generated files in `/tmp/lp-results` are byte-identical on the reference
environment.  `verify_release.py` also accepts harmless last-bit floating-point
differences across supported Python/libm versions while requiring every ID,
selection, count, and discrete result to match exactly.

## Evaluate another model

The preserved packet of twelve direct prompts and four structured-support
prompts corresponding to the supplied captures is in `prompts/`.  Start with
[`prompts/START_HERE.txt`](prompts/START_HERE.txt), which specifies fresh-chat
boundaries, order, disabled tools, retry policy, and what evidence to retain.
The files close exactly over the released public episodes.  The supplied PDFs
do not, however, contain provider logs that independently authenticate the
historical prompt bytes or operational settings.

Save each model response unchanged under a dedicated `responses/` directory.
Use a `.json` extension when the entire response is valid JSON and `.txt` for
prose, code fences, refusals, or errors. Then score all files at once:

```sh
python3 tools/score_predictions.py \
  --predictions scratch_runs/my_model/responses/* \
  --invalid-as-missing \
  --display-label "Exact model and mode shown by the provider" \
  --output scratch_runs/my_model/score.json
```

Missing, malformed, duplicate-ID, wrong-budget, or out-of-pool selections score
zero, exactly as in the paper.  The denominator remains 60.  The command calls
no model and uses no package outside the Python standard library. The opt-in
flag records and skips whole files that are not parseable JSON; it never repairs
them. Unknown or duplicated episode IDs remain hard errors.

If the optional four structured-support prompts were also run, score their
fixed 20-episode, `q=2` pipeline separately:

```sh
python3 tools/score_support_predictions.py \
  --supports scratch_runs/my_model/support_responses/* \
  --invalid-as-missing \
  --display-label "Exact model and mode shown by the provider" \
  --output scratch_runs/my_model/support_score.json
```

This second scorer reproduces the deterministic exhaustive optimizer and both
published GPT structured rows. It reports exact accuracy, target coverage, and
full and truncated support-edge metrics.

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
- `followups/2026-09-05/`: final Codex follow-up answers, repeated-run scores,
  diagnostics, writing handoff, provenance receipts, and offline verification;
- `followups/2026-09-04/`: unchanged earlier interim follow-up snapshot;
- `provenance/`: dataset commitment, generation receipt, and Lean/static audit
  receipts;
- `development_evidence/`: the frozen 15-item development check reported as
  6/15 in the paper;
- `prompts/`: the preserved 12 direct and four structured-support prompt files,
  checksum manifest, and capture instructions;
- `construction/`: the V4 builder, audit wrapper, tests, and reproduction notes;
- `examples/`: direct and structured-support scorer examples;
- `tools/`: published-result, new-model, structured-support, and manifest tools;
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
