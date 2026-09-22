# Results accompanying the paper

This overview brings together the final paper's model results, exact oracle,
construction controls, and supplementary analyses. Model and baseline values
come from the [submitted results](submission/LemmaPortfolio_supplement/RESULTS.md)
and [paper_results.json](results/paper_results.json); each additional analysis
links to its submitted records. The submitted PDF, ZIP, and extracted records
are preserved unchanged.

## Scores and verification

All direct model rows use the same 60 test episodes. Missing or malformed answers
receive zero and stay in the denominators. **Optimal /60** counts selections
that achieve the maximum coverage for their episode; all tied maximizing
triples are accepted. **Mean coverage /8** counts targets whose stored proof
directly references at least one selected candidate. The two additional scores
defined in the technical supplement are reported below as percentages:

- Share of maximum coverage: mean of achieved coverage / episode maximum.
- Occurrence recall: selected recorded candidate-target pairs / all recorded pairs,
  pooled over the evaluated episodes (814 pairs in the complete test set).

From the repository root, run:

```sh
python3 -B verify_release.py
```

This recomputes the underlying scientific records, verifies their repository
mirrors and submitted hashes, rebuilds the original response transcriptions,
independently scores the raw follow-up answers, and runs the oracle and
supplementary checks. For just the submitted checks and paper pairing, use
`python3 -B tools/verify_submission.py --paper paper/LemmaPortfolio.pdf`.
This wrapper handles the archived verifier's documented
[Python 3.10 rounding issue](docs/VERIFICATION.md).

## Main CLI/API results

The seven runs below are the main paper evaluations. The oracle is the scoring
ceiling computed from true proof-use annotations. It is not a model run.

| Model / baseline | Optimal /60 | Mean coverage /8 | Valid /60 | Share of maximum (%) | Occurrence recall (%) |
|---|---:|---:|---:|---:|---:|
| Exact oracle (true annotations) | 60 | 6.25 | 60 | 100.00 | — |
| Uniform random (expectation) | 0.14 | 2.35 | 60 | 37.62 | 18.75 |
| Character TF-IDF | 0 | 3.77 | 60 | 60.40 | 29.48 |
| GPT-6 Astra / xhigh / 1 | 27 | 5.47 | 60 | 87.42 | 42.14 |
| GPT-6 Astra / xhigh / 2 | 30 | 5.53 | 60 | 88.41 | 42.87 |
| GPT-5.6 Sol / xhigh / 1 | 20 | 5.03 | 60 | 80.48 | 39.19 |
| GPT-5.6 Sol / xhigh / 2 | 15 | 5.00 | 60 | 80.00 | 39.19 |
| GPT-6 Astra / max / 1 | 30 | 5.58 | 60 | 89.37 | 43.24 |
| Claude Fable 5 / xhigh | 26 | 5.52 | 60 | 88.29 | 42.87 |
| Claude Fable 5.1 / xhigh / context | 26 | 5.58 | 60 | 89.44 | 43.24 |

**The highest observed exact score is 30/60 (50%).** The oracle's occurrence
recall is left unreported: this row specifies maximum union coverage without
selecting a particular tied optimum for an occurrence-based score. An optimal
coverage score does not mean that all recorded candidate-target pairs were
selected.

The uniform-random row is an exact expectation over all 560 portfolios, not
a sampled response set. The saved deterministic hash draw in the original
results is a different baseline and is not the random row in the paper.

Astra and Sol used Codex CLI; Fable used the Anthropic Messages API. Fable 5.1
received a disclosed benchmark-context system prompt after bare-prompt
refusals. Repetitions share the same episodes, interfaces differ, and effort
labels do not establish equal compute. These runs do not establish a stable
model ranking. See the [evaluation records](submission/LemmaPortfolio_supplement/evaluation/README.md)
and [provenance](docs/PROVENANCE.md).

## Preliminary web results

These six response sets are reported separately in the technical supplement.
Their capture and execution records differ from the main CLI/API runs.

| Visible consumer label | Optimal /60 | Mean coverage /8 | Valid /60 | Share of maximum (%) | Occurrence recall (%) |
|---|---:|---:|---:|---:|---:|
| GPT SOL 5.6 Pro | 25 | 4.98 | 55 | 79.64 | 38.94 |
| GPT SOL 5.6 xhigh | 18 | 5.08 | 60 | 81.39 | 39.80 |
| DeepSeek Instant + DeepThink | 1 | 4.20 | 60 | 67.06 | 34.89 |
| DeepSeek Expert + DeepThink | 7 | 4.60 | 60 | 73.41 | 36.86 |
| Qwen 3.8 Max-Thinking | 12 | 4.32 | 55 | 68.93 | 34.03 |
| Qwen 3.7 Plus-Thinking | 6 | 4.05 | 60 | 64.64 | 31.82 |

Five missing Pro answers and five malformed Qwen 3.8 answers score zero.
The response PDFs preserve the answers and alignment, but lack provider logs
sufficient to authenticate the historical execution settings.

## Exact oracle and construction controls

For each episode, the oracle enumerates all **560** three-candidate portfolios
from sixteen candidates and maximizes coverage of eight targets. Independent
verification enumerates **50,400 portfolios across all 90 episodes** (30
development and 60 test) and checks every maximizing triple. The test split
has **78 distinct optimal triples**: the maximum coverage is six targets on
45 episodes and seven on 15, so the oracle mean is
`(45 × 6 + 15 × 7) / 60 = 6.25`, or **375/480 target instances**.

The following annotation-aware controls count episodes attaining that maximum:

| Control | Development /30 | Test /60 |
|---|---:|---:|
| Exact exhaustive oracle | 30 | 60 |
| Greedy, ascending candidate-ID ties used in construction | 0 | 0 |
| Greedy, descending candidate-ID ties | 28 | 57 |
| At least one greedy tie path reaches an optimum | 29 | 59 |
| Greedy, uniform random choice at each tied step (expected count) | 551/30 ≈ 18.37 | 13469/360 ≈ 37.41 |
| An optimum exists among frequency-maximizing triples | 26 | 53 |

These controls use true annotations. Construction deliberately excluded
episodes solved by its fixed ascending-ID greedy rule; changing the tie rule
often succeeds. Uniform random greedy ties are sampled at each step, rather
than uniformly over distinct final triples. The existence of an optimum in a
tie set is an oracle upper bound, not a selection identified without labels.
These are retrospective construction checks, not statement-only model scores
or evidence of downstream proof success.

Run `python3 -B tools/verify_oracle.py --json` for the independently recomputed
totals. See the [oracle guide](oracle/README.md) and
[submitted per-episode mathematical audit](submission/LemmaPortfolio_supplement/original_release/results/posthoc_math_audit.json)
for definitions, tie distributions, and inputs.

## Paired target-wise comparison

Target-wise selection retains the first two predictions per target, then chooses
three candidates from all sixteen by maximizing predicted coverage. Predicted
ties use candidate-ID order. True annotations are used only for scoring.

| Response set | Paired episodes | Direct optima | Target-wise optima | Direct mean coverage | Target-wise mean coverage |
|---|---:|---:|---:|---:|---:|
| gpt_sol_5_6_pro | 15 | 4 | 1 | 5.00 | 4.40 |
| gpt_sol_5_6_xhigh | 20 | 1 | 0 | 4.65 | 3.90 |
| astra_diagnostic | 20 | 8 | 4 | 5.30 | 5.00 |

The JSON also gives both additional scores and the exact paired episode IDs.
Pro has only 15 complete pairs; its fixed 20-ID scores remain in the original
results with the five missing direct answers scored zero. These are not the
full 60-episode direct results.

The submitted predicted-support tie audit asks a different question: whether
any predicted maximizing triple is also truly optimal. It finds such a triple
on 9/20 Pro, 9/20 Sol, and 13/20 Astra episodes, while the fixed candidate-ID
selection rule achieves 1/20, 0/20, and 4/20. These are the fixed 20-ID subsets;
Pro's matched comparison above contains only 15 complete pairs. The existence
counts use true labels after prediction and are upper bounds, not achieved
pipeline results. See the [original predicted-tie audit](submission/LemmaPortfolio_supplement/original_release/results/posthoc_predicted_tie_audit.json)
and [Astra diagnostic](submission/LemmaPortfolio_supplement/followups/2026-09-05/astra_diagnostic/score.json).

## Masking-exclusion sensitivity

The submitted name-prefix scan identifies six test episodes with residual
source-name prefixes. Excluding those episodes leaves **54**; exclusions depend
on prompt content, not model outcomes. All thirteen saved response sets remain
at or below **27/54 optimal portfolios (50%)**. The retained oracle is **54/54**
with mean coverage **6.26/8**. Missing and malformed answers still score zero.

The [complete sensitivity table and excluded IDs](submission/LemmaPortfolio_supplement/results/masking_sensitivity.md)
and [machine-readable results](results/masking_sensitivity.json) include all
thirteen response sets and the baselines. This is a post-hoc subset analysis
of saved answers; the subset also differs in episode composition. It does not
estimate a causal masking effect or establish absence of training exposure.

## Selection patterns, frequency ties, and uncertainty

The submitted audit checks all **780 answer slots** (13 response sets × 60
episodes): 243 optimal answers, 527 valid non-optimal answers, and 10 invalid
or missing answers. Frequency maximizes summed individual occurrence counts;
the coverage oracle maximizes the union of covered targets.

- The frequency-maximizing sets contain **408 triples**: mean 6.8 per episode,
  median 4, range 1–35. They contain an optimum on **53/60 episodes**, including
  **71 of the 78** distinct optimal triples.
- Across the seven main runs, the **246 valid errors** partition into 184
  selections outside the frequency-maximizing set, 52 inside a set containing
  an optimum, and 10 inside a set containing none.
- Across all thirteen response sets, **143 valid errors** have a better
  portfolio with the same multiset of individual candidate occurrence counts.

These are descriptive comparisons using true labels. They do not identify a
model's internal strategy or evaluate a repair procedure. A selection outside
the frequency-maximizing set is not necessarily a usage-estimation error:
seven episodes require such a selection to reach the coverage optimum.

The [full selection-pattern audit](submission/LemmaPortfolio_supplement/results/selection_patterns.md)
gives per-run counts, definitions, tie geometry, and nominal 95% Wilson
intervals. For example, **30/60** has an interval of **37.7–62.3%** under an
independent-episode binomial approximation. Five-episode prompt blocks may
induce dependence; these intervals do not measure run-level or deployment
uncertainty. Repeated responses on the same episodes are not independent
problems. [selection_patterns.json](results/selection_patterns.json) preserves
the complete submitted record.

## Coverage shortfall and candidate replacements

Across the seven follow-up runs, 163 answers are exactly one target short.
Reaching an optimum requires one replacement for 134, two for 26, and three
for 3. Of each portfolio's 39 single-replacement neighbors, the number that
is optimal is zero for 29 answers, one for 122, two for 10, and three for 2.
These are repeated responses on the same episodes and retrospective checks
using the true labels, not results of a model repair experiment. Per-answer
records are in [the submitted per-answer records](submission/LemmaPortfolio_supplement/descriptive/one_short_replacement_audit.json).
