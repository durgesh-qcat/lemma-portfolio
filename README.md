# LemmaPortfolio

**LemmaPortfolio: Shared-Budget Lemma Selection for Multiple Lean Goals**
asks which three lemmas from a pool of sixteen jointly cover the most historical
direct dependencies across eight Lean goals. There are 30 development and 60
test episodes. The scorer enumerates all 560 triples and accepts every maximizer.

This repository now accompanies the **7 September 2026 submitted paper**:

- [Final submitted paper, including its technical supplement](paper/LemmaPortfolio.pdf)
- [Exact submitted reproducibility ZIP](submission/LemmaPortfolio_supplement.zip)
- [Unpacked submitted supplement and verification instructions](submission/LemmaPortfolio_supplement/README.md)
- [All paper results](RESULTS.md) and [machine-readable results](results/paper_results.json)
- [Paper file provenance and source availability](paper/README.md)

The final PDF is definitive. The editable source for that exact PDF has not yet
been recovered; the [archived source and PDFs](paper/historical/2026-09-05/)
belong to the earlier manuscript and do not build the final submission.

## Verify everything offline

From a clean repository checkout, with Python 3.10 or newer:

```sh
python3 -B verify_release.py
```

This checks repository hashes and the exact submitted PDF/archive, runs the
submitted supplement's complete verification, verifies the oracle benchmark,
and rechecks the richer historical follow-up receipts. It reconstructs every
optimum, reparses the original responses, checks all thirteen direct model rows,
rebuilds the baselines and target-wise comparisons, repeats the masking,
selection-pattern, construction-tie and replacement analyses, and runs the
parser, scorer and construction tests. It ends with `ALL CHECKS PASSED`.
The checks use only the Python standard library and make no model or network
calls. Lean and API credentials are not needed. On macOS, `RUN_ME.command`
provides the same verification by double-click.

The submitted archive can also be checked independently:

```sh
python3 -B tools/verify_submission.py --paper paper/LemmaPortfolio.pdf
```

The repository wrapper handles a [Python 3.10 rounding-comparison defect](docs/VERIFICATION.md)
in the archived verifier; the submitted PDF, ZIP, and extracted files remain unchanged.

## Results in the submitted paper

Exact optimality counts episodes whose selected triple reaches the episode's
maximum coverage. Mean coverage counts covered targets out of eight; it is a
different metric. Every direct row retains all 60 episodes in its denominator.

The main paper reports these seven CLI/API runs:

| Recorded model / effort / run | Exact optimum | Mean coverage /8 | Valid |
|---|---:|---:|---:|
| GPT-6 Astra / xhigh / 1 | 27/60 (45.0%) | 5.47 | 60/60 |
| GPT-6 Astra / xhigh / 2 | 30/60 (50.0%) | 5.53 | 60/60 |
| GPT-5.6 Sol / xhigh / 1 | 20/60 (33.3%) | 5.03 | 60/60 |
| GPT-5.6 Sol / xhigh / 2 | 15/60 (25.0%) | 5.00 | 60/60 |
| GPT-6 Astra / max / 1 | 30/60 (50.0%) | 5.58 | 60/60 |
| Claude Fable 5 / xhigh | 26/60 (43.3%) | 5.52 | 60/60 |
| Claude Fable 5.1 / xhigh / context | 26/60 (43.3%) | 5.58 | 60/60 |

Astra/Sol used Codex CLI 0.153.0; Fable used the Anthropic Messages API.
Fable 5.1 used a disclosed benchmark-context system prompt after bare-prompt
refusals. The unchanged user prompts, available settings, calling code and
execution-record limitations are in the [evaluation records](submission/LemmaPortfolio_supplement/evaluation/README.md).
The first Astra xhigh run preceded the follow-up protocol freeze, and planned
third xhigh runs were cancelled after completed scores were known. Both completed
repetitions are reported. Repeated runs reuse the same 60 episodes, and effort
labels do not establish equal compute or a stable model ranking.

| Reference | Exact optimum /60 | Mean coverage /8 |
|---|---:|---:|
| Uniform random (exact expectation) | 0.14 | 2.35 |
| Character TF-IDF | 0 | 3.77 |
| Exhaustive true-label oracle | 60 | 6.25 |

The random expectation averages uniformly over all 560 portfolios; it differs from
the single
deterministic hash draw preserved in the original results. The
[oracle benchmark](oracle/README.md) uses the released true labels to establish
the scoring ceiling. It is a label-informed reference, with a maximum of six
targets on 45 test episodes and seven on 15.

The technical supplement retains the six original web-interface response sets
as preliminary evidence:

| Visible consumer label | Exact optimum | Mean coverage /8 | Valid |
|---|---:|---:|---:|
| GPT SOL 5.6 Pro | 25/60 (41.7%) | 4.98 | 55/60 |
| GPT SOL 5.6 xhigh | 18/60 (30.0%) | 5.08 | 60/60 |
| DeepSeek Instant + DeepThink | 1/60 (1.7%) | 4.20 | 60/60 |
| DeepSeek Expert + DeepThink | 7/60 (11.7%) | 4.60 | 60/60 |
| Qwen 3.8 Max-Thinking | 12/60 (20.0%) | 4.32 | 55/60 |
| Qwen 3.7 Plus-Thinking | 6/60 (10.0%) | 4.05 | 60/60 |

Five missing Pro answers and five malformed Qwen 3.8 answers score zero.
The response PDFs establish the saved answers and their alignment, but lack the
provider logs needed to authenticate historical settings. These captures and
the CLI/API runs have different evidence and execution protocols; see
[provenance](docs/PROVENANCE.md).

## Diagnostics and additional checks

- [Target-wise comparison and replacement counts](RESULTS.md): fresh Astra
  direct selection scores 8/20 versus 4/20 for the target-wise `q=2` pipeline.
  The original matched comparisons are Pro 4 versus 1 on 15 complete pairs and
  Sol xhigh 1 versus 0 on 20. These evaluate the complete tested pipelines.
- [Masking sensitivity](submission/LemmaPortfolio_supplement/results/masking_sensitivity.md):
  excludes the six episodes identified by the source-name-prefix audit and
  re-scores all thirteen response sets on 54 episodes. No run exceeds 27/54.
- [Selection patterns and nominal Wilson intervals](submission/LemmaPortfolio_supplement/results/selection_patterns.md):
  checks all 780 answer slots and enumerates frequency-maximizing tie sets.
  Such a set contains an optimum on 53/60 episodes. The 246 follow-up errors
  partition into 184 outside these sets, 52 inside sets containing an optimum,
  and 10 inside sets containing none.
- [Construction ties, baseline definitions and Lean annotations](submission/LemmaPortfolio_supplement/REPRODUCIBILITY.md)
  and [per-answer replacement records](submission/LemmaPortfolio_supplement/descriptive/README.md).

The tie and replacement analyses use true labels retrospectively. They do not
identify models' internal reasoning or test a repair procedure. The replacement
analysis finds that 134 of 163 one-target-short follow-up answers have an optimal
single-replacement neighbor; the remaining 29 need at least two replacements.

## Evaluate another model or reconstruct the benchmark

Use the twelve released direct prompts in [prompts/](prompts/START_HERE.txt),
preserve every response unchanged, and score them with:

```sh
python3 -B tools/score_predictions.py \
  --predictions scratch_runs/my_model/responses/* \
  --invalid-as-missing \
  --display-label "Exact model and mode shown by the provider" \
  --output scratch_runs/my_model/score.json
```

Malformed files are recorded and skipped without repair; their absent answers
remain zero. Unknown or duplicate episode IDs are hard errors. The
[rerun guide](docs/RERUN_MODELS.md) covers fresh sessions, tools, retries,
metadata and the optional target-wise scorer. Public labels must be withheld
from evaluated processes. Fresh inference need not reproduce saved outputs.

The [construction guide](construction/README.md) describes rebuilding with
Lean 4.33.0 and Mathlib commit `db584cd6d46c92f209a44c0f1c829460d327499d`.
The additional mining inputs and DuckDB are needed only for reconstructing the
benchmark, not for offline score verification.

## Repository map

| Location | Contents |
|---|---|
| `paper/` | Exact final submitted PDF, provenance, and earlier paper files under `historical/` |
| `submission/` | Exact submitted ZIP and an unchanged unpacked copy with all final checks |
| `data/`, `prompts/`, `responses/` | Original episodes, labels, prompts, response PDFs and transcriptions |
| `RESULTS.md`, `results/paper_results.json` | Final consolidated paper results, mirrored from the submission |
| Other files under `results/` | Preserved original scores, baselines and audits |
| `oracle/` | Reproducible exhaustive oracle and true-label diagnostic references |
| `followups/2026-09-05/` | Richer original follow-up receipts, API captures and historical reporting handoff; these runs are now incorporated in the submitted paper |
| `followups/2026-09-04/` | Earlier interim snapshot |
| `provenance/`, `development_evidence/` | Data commitments, Lean audits and the frozen 6/15 development check |
| `construction/`, `tools/`, `examples/` | Builder, scorer, verifier, tests and input examples |
| `docs/` | Data card, evidence boundaries, collaboration and rerun instructions |

## Scope, collaboration and citation

The labels record direct constants in historical elaborated proof values.
They establish neither logical necessity nor downstream prover success.
The closed candidate pool, uniform costs, incomplete masking and deliberately
conditioned stress set limit generalization; see the [data card](docs/DATA_CARD.md).

This named repository remains private during double-blind review. Use the exact
anonymous submitted ZIP for review. [Collaboration](docs/COLLABORATING.md) and
[paper source/Overleaf status](docs/OVERLEAF.md) explain how to work from the
current artifacts without confusing the archived manuscript with the final PDF.

Code and original documentation are Apache-2.0. Mathlib text, paper/style files
and response captures have the attribution and terms in [NOTICE](NOTICE) and
[LICENSES.md](LICENSES.md). Cite the final title and artifact version recorded
in [CITATION.cff](CITATION.cff).
