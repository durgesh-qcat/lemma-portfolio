# LemmaPortfolio

**Shared-Budget Lemma Selection for Multiple Lean Goals**

[![Verification on main](https://github.com/durgesh-qcat/lemma-portfolio/actions/workflows/verify.yml/badge.svg?branch=main)](https://github.com/durgesh-qcat/lemma-portfolio/actions/workflows/verify.yml?query=branch%3Amain)

[Paper](paper/LemmaPortfolio.pdf) · [Submitted supplement](submission/LemmaPortfolio_supplement.zip) · [Latest release](https://github.com/durgesh-qcat/lemma-portfolio/releases/latest) · [Full results](RESULTS.md) · [Evaluate a model](docs/RERUN_MODELS.md) · [Citation](CITATION.cff)

> Which three lemmas should you choose when the same small set must serve eight Lean goals?

LemmaPortfolio benchmarks **joint premise selection under a shared budget**.
A model reads candidate and target statements, then selects one portfolio of
three candidates. The portfolio is scored against direct references in the
targets' existing elaborated Lean proofs. Selecting useful candidates individually
is only part of the task: their coverage can overlap.

This public repository accompanies the final submitted paper and contains the
episodes, released labels, prompts, saved model responses, scoring tools,
oracle, supplementary analyses, and reproducibility checks.

| Benchmark | Specification |
|---|---|
| Source | Mathlib v4.33.0; annotations checked with Lean 4.33.0 |
| Splits | 30 development episodes and 60 test episodes, from disjoint source modules |
| Per episode | 16 candidate declarations, 8 targets, budget of 3 candidates |
| Scoring | Exhaustive comparison with all 560 possible portfolios; every maximizer is accepted |
| Evidence | 7 main CLI/API runs, 6 preliminary web response sets, and target-wise diagnostics |

## Quickstart

Python **3.10 or newer** is sufficient for offline verification. No additional
Python packages, Lean installation, API keys, or model calls are needed.

```sh
git clone https://github.com/durgesh-qcat/lemma-portfolio.git
cd lemma-portfolio
python3 -B verify_release.py
```

Alternatively, download `LemmaPortfolio_full_repository.zip` from the
[latest release](https://github.com/durgesh-qcat/lemma-portfolio/releases/latest),
unzip it, and run the same command from its `lemma-portfolio` folder.
On macOS, you can also double-click `RUN_ME.command`.

A successful run ends with **`ALL CHECKS PASSED`**. It verifies the exact submitted
paper and ZIP, file hashes, all 13 model rows, baseline and oracle calculations,
supplementary analyses, historical run receipts, and regression tests.

The badge above tracks **`main`**. Older red runs in the Actions history belong
to earlier commits. The submitted verifier's Python 3.10 rounding-comparison
bug is handled by the current repository wrapper; the original submission
files remain unchanged. See [verification and check history](docs/VERIFICATION.md).

## What the score means

For each target, the labels record which displayed candidates occur directly in
its stored elaborated proof. A target is **covered** if at least one selected
candidate appears in that record; selecting several candidates used by the same
target still counts that target once.

- **Exact optimality** counts episodes where the selected triple attains the
  largest possible coverage. Tied optimal portfolios receive equal credit.
- **Mean coverage** is the average number of covered targets, out of eight.
- Missing or malformed answers receive zero and remain in the denominator.

The [exhaustive oracle](oracle/README.md) uses the true annotations. Across the
60 test episodes, the maximum is six targets in 45 episodes and seven in 15,
giving an oracle mean of **6.25/8**. It provides the scoring ceiling, rather than
an evaluated model prediction. The labels describe historical proof use;
coverage does not establish logical necessity or success on a new proof.

## Main results

The submitted paper reports seven CLI/API runs on the same 60 test episodes.
Every model run below returned 60 valid portfolios.

| Model / effort / run | Optimal portfolios /60 | Accuracy | Mean coverage /8 |
|---|---:|---:|---:|
| Oracle — true annotations | 60 | 100% | 6.25 |
| Uniform random — exact expectation | 0.14 | 0.23% | 2.35 |
| Character TF-IDF | 0 | 0.0% | 3.77 |
| GPT-6 Astra / xhigh / 1 | 27 | 45.0% | 5.47 |
| GPT-6 Astra / xhigh / 2 | 30 | 50.0% | 5.53 |
| GPT-5.6 Sol / xhigh / 1 | 20 | 33.3% | 5.03 |
| GPT-5.6 Sol / xhigh / 2 | 15 | 25.0% | 5.00 |
| GPT-6 Astra / max / 1 | 30 | 50.0% | 5.58 |
| Claude Fable 5 / xhigh | 26 | 43.3% | 5.52 |
| Claude Fable 5.1 / xhigh / additional context | 26 | 43.3% | 5.58 |

**No tested run selects an optimal portfolio on more than half the episodes.**
The uniform-random row is an expectation over all portfolios, not a sampled run.
It differs from the single deterministic hash draw retained in the original
result files.

Astra and Sol used Codex CLI; Fable used the Anthropic Messages API. Fable 5.1
received a disclosed benchmark-context system prompt after bare-prompt refusals.
Repeated runs use the same episodes, interfaces differ, and effort labels do
not establish equal compute. These results do not establish a stable model
ranking. [Evaluation records](submission/LemmaPortfolio_supplement/evaluation/README.md)
and [provenance](docs/PROVENANCE.md) document settings, the earlier Astra run,
cancelled third repetitions, and limitations of the available capture records.

<details>
<summary><strong>Preliminary web-interface results — six additional response sets</strong></summary>

These original captures appear separately in the paper's technical supplement.
Their interface and execution records differ from the main CLI/API runs.

| Visible consumer label | Optimal portfolios /60 | Mean coverage /8 | Valid /60 |
|---|---:|---:|---:|
| GPT SOL 5.6 Pro | 25 | 4.98 | 55 |
| GPT SOL 5.6 xhigh | 18 | 5.08 | 60 |
| DeepSeek Instant + DeepThink | 1 | 4.20 | 60 |
| DeepSeek Expert + DeepThink | 7 | 4.60 | 60 |
| Qwen 3.8 Max-Thinking | 12 | 4.32 | 55 |
| Qwen 3.7 Plus-Thinking | 6 | 4.05 | 60 |

Five missing Pro answers and five malformed Qwen 3.8 answers score zero.
The response PDFs preserve the answers and their alignment, but lack provider
logs sufficient to authenticate the historical execution settings.

</details>

See [all result tables](RESULTS.md) and
[machine-readable results](results/paper_results.json) for exact counts,
additional metrics, and paired comparisons. The paper and
[selection-pattern audit](submission/LemmaPortfolio_supplement/results/selection_patterns.md)
report nominal Wilson intervals and their limitations.

## Diagnostics and supplementary analyses

| Analysis | Finding and evidence |
|---|---|
| Target-wise prediction followed by optimization | Fresh Astra: **8/20** direct optima versus **4/20** with the target-wise `q=2` pipeline. [Paired comparisons](RESULTS.md#paired-target-wise-comparison) |
| Masking sensitivity | Excluding six episodes with residual source-name prefixes leaves all 13 response sets at or below **27/54** optima. [Results](submission/LemmaPortfolio_supplement/results/masking_sensitivity.md) |
| Frequency ties and selection patterns | A frequency-maximizing set contains an optimum on **53/60** episodes. The audit checks all **780 answer slots**. [Definitions and per-run counts](submission/LemmaPortfolio_supplement/results/selection_patterns.md) |
| Candidate replacements | **134/163** one-target-short follow-up answers have an optimal single-replacement neighbor; the other 29 need at least two replacements. [Records](submission/LemmaPortfolio_supplement/descriptive/README.md) |
| Oracle and greedy controls | Independent enumeration of **50,400 portfolios** across all 90 episodes, including complete optimal sets and greedy tie behavior. [Oracle guide](oracle/README.md) |

These are retrospective analyses of saved responses and true labels. They do
not identify a model's internal strategy or constitute a model repair experiment.

## Evaluate your own model

Start with the [prompt instructions](prompts/START_HERE.txt). Use the twelve
direct prompts in fresh, tool-free sessions and preserve every raw response
under `scratch_runs/my_model/responses/`. Keep labels out of the evaluated process.

```sh
python3 -B tools/score_predictions.py \
  --predictions scratch_runs/my_model/responses/* \
  --invalid-as-missing \
  --display-label "Exact model and mode shown by the provider" \
  --output scratch_runs/my_model/score.json
```

Unparseable files are recorded without repair; their absent answers score zero.
Unknown or duplicate episode IDs are errors. Record the interface, model, mode,
date, tools, and retries before scoring. The [rerun guide](docs/RERUN_MODELS.md)
includes the optional target-wise diagnostic and capture requirements.

To regenerate the benchmark or re-extract Lean annotations, follow the
[construction guide](construction/README.md). Those optional checks require the
pinned Mathlib/Lean environment; mining also requires the recorded external
source shards and DuckDB.

## Repository guide

| Location | What you will find |
|---|---|
| [paper/](paper/README.md) | Final submitted PDF, with its technical supplement appended |
| [submission/](submission/README.md) | Exact submitted ZIP and all 309 unpacked files |
| [data/](data/), [prompts/](prompts/START_HERE.txt), [responses/](responses/) | Episodes, released labels, prompt packet, saved answers and transcriptions |
| [results/](results/README.md), [oracle/](oracle/README.md) | Consolidated scores, additional analyses, and oracle verification |
| [followups/](followups/README.md) | Detailed run receipts, API captures, and historical evaluation snapshots |
| [construction/](construction/README.md), [tools/](tools/), [tests/](tests/) | Builder, scorers, verifiers, and regression tests |
| [docs/](docs/), [provenance/](provenance/) | Data card, reproducibility instructions, evidence boundaries and audit receipts |

## Scope and citation

This is a conditioned stress set with a closed candidate pool and uniform
selection costs. Direct proof references do not establish logical necessity or
downstream prover success. Residual masking, possible public-library exposure,
and the limited repeated runs constrain interpretation. See the
[data card](docs/DATA_CARD.md) and [provenance](docs/PROVENANCE.md).

The **exact final PDF is the authoritative paper**. Its editable LaTeX source
is unavailable. Earlier sources and PDFs are preserved as clearly labeled
[historical drafts](paper/historical/2026-09-05/).

If you use this benchmark, please cite Aishwarya Praveen Das and Durgesh Kumar:

```bibtex
@misc{das2026lemmaportfolio,
  title  = {LemmaPortfolio: Shared-Budget Lemma Selection for Multiple Lean Goals},
  author = {Das, Aishwarya Praveen and Kumar, Durgesh},
  year   = {2026},
  note   = {Submitted manuscript},
  url    = {https://github.com/durgesh-qcat/lemma-portfolio}
}
```

[CITATION.cff](CITATION.cff) provides machine-readable artifact metadata.
Code and original documentation are licensed under Apache-2.0. See
[LICENSE](LICENSE), [NOTICE](NOTICE), and [LICENSES.md](LICENSES.md) for the terms
covering Mathlib text, paper/style files, and captured responses.
