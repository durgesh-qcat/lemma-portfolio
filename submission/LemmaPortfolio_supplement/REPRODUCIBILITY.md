# Scientific reproducibility notes

The archive contains the released episodes and labels, saved responses, scoring
and construction code, and the numerical audit records. The [root README](README.md)
gives the commands for checking the submitted results. These notes specify the
scientific details needed to interpret or rebuild them; no earlier manuscript
is required.

## What can be reproduced

- **Scores and optimal portfolios:** use the included public/label JSONL files,
  saved responses, and Python scoring tools. No model call, Lean installation,
  or external mining dataset is needed.
- **Proof-use annotations:** additionally use the pinned Lean and Mathlib
  environment below. The included audit receipts record the original checks;
  checking a receipt is not a fresh extraction from Lean.
- **Episode mining:** additionally obtain and hash-check the 256 external
  Parquet shards and install DuckDB 1.5.5. The
  [construction README](original_release/construction/README.md) supplies the
  pinned download, verification, mining, and Lean re-extraction commands.

The Mathlib source is v4.33.0, commit
`db584cd6d46c92f209a44c0f1c829460d327499d`. The checker uses Lean 4.33.0,
compiler commit `d8b18978322de05a8f3dba51ef03cf5461676c17`.
The [generation receipt](original_release/provenance/generation_receipt.json)
records all 256 shard names, sizes, and SHA-256 digests: 128 dependency shards
and 128 type shards, totaling 220,228,123 bytes (about 210 MiB). Its
`source.recomputed_parquet_inventory_sha256` is
`b2bbf0bbb4bd3d59834024be349deb70f8b17e37738d98275e2f0740eca23695`.
The earlier source receipt explicitly records that an immutable dataset-repository
revision was not saved at original generation. The construction README therefore
identifies the upstream v4.33.0 revisions separately and requires byte-level
verification against the preserved receipt; using today's `main` is not sufficient.

## Task and scores

Each episode has 16 candidate declarations, eight targets, and one shared budget
of three candidates. Local IDs are episode-specific. Candidates are named Lean
declarations, usually theorems but sometimes definitions or constructors. The
public record contains statements and instructions; the label record also
contains source names, direct-use rows, coverage counts, and every optimal triple.
The label record is not part of the model prompt.

For target `t`, let `D_t` be the displayed candidates occurring directly in its
stored elaborated proof. A portfolio `P` covers `t` exactly when `P ∩ D_t` is
nonempty. Count each covered target once, even if several selected candidates
occur. The primary score counts episodes on which the answer attains the maximum
coverage among all `C(16,3) = 560` triples. All maximizing triples are accepted.
Mean coverage is the achieved target count averaged over episodes.

Two further scores are retained in the numerical records:

- **Share of maximum coverage:** average of achieved coverage divided by that
  episode's maximum.
- **Occurrence recall:** selected candidate–target occurrence pairs divided by
  all recorded candidate–target pairs, pooled across episodes. This is not an
  average of per-episode recall values.

A valid answer has exactly three distinct in-pool IDs. Missing or malformed
answers receive zero on every score and remain in the denominators; validity
is reported separately. A repeated candidate, unknown ID, or wrong-size
portfolio is invalid. See [the scorer](original_release/tools/score_release.py)
and the response provenance records for parsing and transcription rules.

For uniform random choice of a triple, with `d_t = |D_t|`,

```text
Pr(t is covered) = 1 - C(16-d_t,3) / 560.
Pr(an optimal triple) = number of optimal triples / 560.
```

Sum the first expression over eight targets for expected episode coverage and
average over episodes for expected mean coverage. Sum the second expression
over episodes for expected optimal-answer count. Expected occurrence recall is
`3/16`, since every fixed candidate has that inclusion probability. These are
exact expectations, not simulations, and require no independence assumption
between targets. The single SHA-256-based draw retained in the original result
records is a different baseline, not the uniform expectation.

## Construction

The frozen implementation is
[build_hard_blind_v4.py](original_release/construction/apibench/hard_blind_v4/build_hard_blind_v4.py),
with shared text functions in
[build_mathlib_release_v2.py](original_release/construction/apibench/scripts/build_mathlib_release_v2.py).
The source receipts preserve configuration and selection diagnostics.

### Eligibility, ordering, and separation

A declaration needs a nonempty parseable public type, source module, and
dependency record. Whitespace is collapsed before measuring statement length;
eligible statements have 16–240 syntax tokens and at most 1,400 characters and
pass the builder's reflexivity and prior-statement exclusions. Earlier prototype
modules and statements are excluded. Exact token signatures and signatures
normalizing leading bound-variable names reject repeated statements within and
across the new splits. This is a syntactic check, not a test of mathematical
equivalence.

All 24 declarations in an episode come from one module. Candidate eligibility
requires at least two consumers in the eligible module pool; these need not be
the final eight targets. Targets are outside the candidate pool and have one to
five dependencies among its candidates. No two selected targets have a direct
dependency on one another in the mined graph.

The fixed seed is
`lemma-portfolio-dependency-compression-v4-2026-09-01`. Hash ordering determines
module order, candidate cohorts, target trials, displayed order, and final
selection. There are at most 32 candidate-cohort trials per module and 32 target
seed trials per cohort. Development admission restricts both zero-based trial
indices to less than 28. The per-top-level-namespace caps are five development
episodes and ten test episodes. Development and test source modules are disjoint.
The construction does not use the evaluated test responses.

One initially selected test module failed the independent Lean preflight. Its
module hash, `f22caa542e02fac9b7c2bc447b23a9fa32f7f9d60c907904c99917c6873b5684`,
was excluded, and its replacement came from the same fixed eligible list,
without reranking.

### Structural requirements

Here an *active* candidate occurs in at least one of the eight target proofs.
Every admitted episode meets all the following conditions.

| Quantity | Requirement |
| --- | --- |
| Candidates / targets / budget | 16 / 8 / 3 |
| Active candidates | At least 7 |
| Active candidates outside every optimal portfolio | At least 4 |
| Targets with at least two displayed dependencies | At least 2 |
| Coverage of any single candidate | At most 4 |
| Use count of every member of every optimal portfolio | At least 2 |
| Coverage lost by removing any member of an optimal portfolio | At least 1 |
| Triples covering exactly one target fewer than the maximum | At least 2 |
| Maximum coverage | At least 6 |
| Number of optimal triples | At most 32 |
| Mean token-Jaccard similarity over the 28 target pairs | At most 0.6 |

### Text processing and the 20 selection rules

The syntax-token regex is the following Python expression:

```python
r"[A-Za-z_\u0080-\uffff][A-Za-z0-9_\u0080-\uffff'.]*|:=|=>|[^\s]"
```

Token-Jaccard uses a different token set. It first matches
`r"[A-Za-z_\u0080-\uffff][A-Za-z0-9_\u0080-\uffff'.]*"`, strips `.` and `'`
from each match's ends, and splits on dots. It drops empty pieces and the
case-sensitive stop words `Type`, `inst`, `fun`, `forall`, `Prop`, `Sort`,
`true`, and `false`, then lowercases the remaining pieces and removes duplicates.
Jaccard similarity is intersection size divided by union size, or zero for an
empty union.

Fifteen text rules combine five candidate features with three selection rules.
The features are canonical character length, syntax-token count, the sum of raw
occurrence counts of `∀`, `fun`, and `:`, the sum of raw counts of
`= ≠ → ↔ ∧ ∨ ¬ ≤ ≥ < >`, and similarity to the targets. For the last feature,
sort the eight candidate–target Jaccards as `j1 ≥ ... ≥ j8` and use
`(j1+j2)/2 + (j1+...+j8)/16`. This feature is distinct from the mean
target–target similarity filter above. For each feature, select the three
largest, three smallest, or three closest to the median of the 16 values
(the mean of the eighth and ninth sorted values).

Three more text rules rank candidates by Jaccard similarity separately for
each target and keep its first one, two, or three candidates, respectively.
Each resulting predicted-use table is passed to greedy selection: choose a
candidate covering the most additional predicted targets, repeated three times.
These are fixed lexical rules, not the language-model occurrence predictions.

The remaining two rules use the true occurrence table. One selects the three
most frequent candidates; the other greedily maximizes additional true target
coverage at each step. Every ranking and greedy tie in these 20 rules favors
the earlier displayed candidate. Reject an episode if any rule finds an optimum.
Their failures therefore follow from construction, not independent test results.

### Resulting splits

The 30 development episodes occupy 30 modules and 13 top-level namespaces;
the 60 test episodes occupy 60 modules and 15 namespaces. Development has
240 targets, 386 candidate–target pairs, and 30 optimal triples in total;
test has 480 targets, 814 pairs, and 78 optimal triples. Maximum coverage is
six in 25 development and 45 test episodes, and seven in the remaining five
and fifteen. Test namespace counts are Algebra 10, Data 7, RingTheory 7,
Analysis 5, Topology 5, AlgebraicGeometry 4, CategoryTheory 4, Combinatorics 3,
NumberTheory 3, Order 3, Dynamics 2, Geometry 2, GroupTheory 2,
LinearAlgebra 2, and MeasureTheory 1.

The mining diagnostics begin with 350,599 declarations; 186,680 declarations
in 7,089 modules remain after eligibility and prior exclusions. Fixed trials
produce 71,091 complete occurrence records; 165 defeat all 20 selectors,
121 pass the exact-token name check, and 103 pass repeated-statement checks,
before the Lean-preflight exclusion and final split selection. These are
construction-stage counts, not an estimate of difficulty across Mathlib.

## Character TF–IDF baseline

This baseline was added after construction and is not one of the 20 filters.
For each episode, form character 3-, 4-, and 5-gram counts from its 24 displayed
statements, without additional lowercasing or whitespace processing. For a gram
`g` appearing `n(g,s)` times in statement `s`, with document frequency `df(g)`,
the nonzero weight is

```text
w(g,s) = (1 + ln n(g,s)) (1 + ln(25 / (1 + df(g)))).
```

L2-normalize each vector. A target contributes its largest cosine similarity
to a selected candidate; sum these eight values to score a triple. Enumerate
all 560 triples in candidate-ID order and take the first maximum. The full
implementation is in [score_release.py](original_release/tools/score_release.py).

## Lean validation and scope of the labels

[audit_pinned_lean.py](original_release/construction/apibench/hard_blind_v4/audit_pinned_lean.py)
imports Mathlib, checks declaration existence and kind, then reads each target
with `ConstantInfo.value? (allowOpaque := true)` and applies
`Expr.getUsedConstantsAsSet`. Intersecting this set with the 16 displayed
candidates must recover the stored row. It does not recursively enter the
proof or definition of a referenced candidate. The wrapper first checks the
public and label hashes, generation-receipt commitment, Mathlib commit, Lean
version, and compiler commit against the preserved records.

The [development receipt](original_release/provenance/calibration.pinned_lean_audit.json)
records 240/240 matching target rows and 386/386 matching occurrences; the
[test receipt](original_release/provenance/blind.pinned_lean_audit.json) records
480/480 and 814/814. There are no changed rows, added/removed occurrences, or
targets with no displayed occurrence. The separate `Expr.eqv` check compares
candidate–candidate, candidate–target, and target–target statement expressions
**within each episode**; it finds no matches. It does not establish mathematical
inequivalence or compare every pair of statements across episodes.

These are direct references in one elaborated proof, including references in
type annotations and implicit arguments. They need not be explicit source-text
lemma applications or logically necessary premises. Alternative proofs can
have different uses. Four targets in the biproduct episode are reassociated
variants already generated in Mathlib by `reassoc`; they were not generated
by this benchmark or by a language model. Routine corollaries are consequently
part of the task. The fixed pool, equal selection cost, public-library exposure,
and construction filtering also limit interpretation as mathematical research
performance.

## Checks of construction bias and masking

The post-hoc name-prefix scan finds incomplete masking in 6/60 test and 2/30
development episodes. The construction check rejects complete source-name
tokens but misses some generated or dotted identifiers beginning with a source
name. Test has 33 occurrences in 25 source-name/statement pairs involving
24 declarations; development has five occurrences in five pairs involving
five declarations. See the [data card](original_release/docs/DATA_CARD.md)
and [post-hoc audit](original_release/results/posthoc_math_audit.json).
The original-panel sensitivity calculation excludes those six test episodes
and re-scores 54 episodes. The accompanying `verify_masking_sensitivity.py`
extends the identical exclusion to all thirteen saved direct-response sets,
reproduces the original six rows, and checks the derived table in
`results/masking_sensitivity.md`. No run exceeds 27/54 exact optima.
This does not repair masking, isolate a causal masking effect, or establish
absence of training exposure; the excluded subset changes episode composition.

True-label greedy selection with the construction tie order is exactly one
target short on all 60 test episodes. Reversing the tie order finds optima
on 57/60 test and 28/30 development episodes; some greedy tie path finds one
on 59/60 and 29/30. Choosing uniformly among tied candidates at each greedy
step gives expected test optimal count `13469/360` (about 37.41) and total
coverage `126869/360` (about 352.41). These probabilities are conditional at
each step, not uniform over reachable final triples; a separate subset dynamic
program checks the calculation. All these procedures use true hidden labels.
They are post-hoc construction checks, not statement-only model baselines,
and do not establish that optimal portfolios evade greedy selection generally.

## Saved-response analyses

[PROVENANCE.md](PROVENANCE.md) specifies the original/follow-up evidence
boundaries, interfaces, Fable 5.1 added context, repeats, and diagnostic order.
The recorded settings and model labels are not independent authentication of
remote serving identities. The original six response sets are preserved in
two response PDFs and their transcriptions. The released prompts are included;
unrecorded system/serving metadata cannot be recovered from the mathematical scorer.
The duplicate Pro D11 is resolved by keeping its first occurrence; both
versions have equal scores. Missing Pro D12 and malformed Qwen 3.8 D12 remain
invalid rather than being repaired. Explicit episode keys determine alignment.

In the occurrence-first diagnostic, retain each target's first two predicted
candidates, then maximize predicted coverage over **all 560 triples from the
original 16 candidates**, breaking ties lexicographically. True labels are
used only after selection. The original D04/D05/D06/D12 subset was not the
protocol's optional hash-selected arm; original run order and feedback are
unknown. The original paired counts are Pro 4 versus 1 optimum on 15 matched
episodes, and Sol xhigh 1 versus 0 on 20. The later Astra comparison has
20 matched episodes and gives direct 8 versus occurrence-first 4 optima.
It concerns prediction, truncation, optimization, and tie-breaking together,
not decomposition alone. Widths one through four in the retained diagnostics
are offline rescoring of the same predictions, not additional model calls.

The [predicted-tie audit](original_release/results/posthoc_predicted_tie_audit.json)
retains full original per-episode tie sets and exact expectations. A true
optimum exists among the predicted maximizers on 9/20 original Pro and 9/20
original Sol episodes, but the selected maximizers achieve only 1/20 and 0/20.
For Astra, the corresponding counts are 13/20 and 4/20. Existence among ties
is an oracle upper bound, not a result achieved without true labels.

[COVERAGE_AND_REPLACEMENTS.md](descriptive/COVERAGE_AND_REPLACEMENTS.md) and its
data files give the replacement analysis. For a submitted triple `P`, distance
to optimality is `min_Q (3 - |P ∩ Q|)` over optimal triples `Q`. There are
`3 × 13 = 39` single-replacement neighbors. Among 163 follow-up responses
covering exactly one target fewer than the maximum, 134 need one replacement,
26 need two, and three need three. Of the 134 with a successful single change,
122 have one such change, ten have two, and two have three. The 29 others have
none. Already optimal answers are excluded. These are repeated answer instances
on the same 60 episodes, not 163 independent problems, and no model repair
experiment was performed.

Any original Wilson intervals treat episode outcomes as independent Bernoulli
observations; the block bootstrap resamples twelve five-episode response blocks.
Neither quantifies between-generation variability or performance on a broader
population. The small occurrence-first comparisons carry no significance claim.
The follow-up repeats are reported separately, not as a best-of-two score.

## Post-hoc selection patterns and nominal intervals

The added selection-pattern audit checks all 780 direct answer slots, of which
770 are valid and 527 are non-optimal. In the seven CLI/API follow-ups, all 420
answers are valid and 246 are non-optimal. For every valid triple it compares:

- The three candidates with the largest individual historical-use counts,
  with ascending-ID tie breaking and with every tied maximizing triple.
- Sequential greedy marginal-coverage selection, under ascending-ID ties and
  every reachable sequence of ties. Frequency ranking is not sequential greedy.
- The best coverage among triples with the same sorted multiset of individual
  use counts. Improvement at a fixed count profile implies less repeated coverage.

Among the 246 follow-up errors, frequency matches number 21 under fixed ties
and 62 under all ties; greedy matches number 19 and 86. A same-degree-profile
improvement exists for 71 errors. These are overlapping descriptive comparisons
using hidden labels, not inferred internal model strategies or evaluated repairs.
Models could use inaccurate estimates of frequency and produce different triples.

The episode-level tie-set audit, independent of model outcomes, finds an optimum
among frequency-maximizing triples on 53/60 episodes. There are 408 such triples
in total (mean 6.8, median 4, range 1--35) and 71 of the 78 distinct optimal
triples are frequency-maximizing. The JSON retains every tied triple, every
intersection with the optimum set, and the complete tie-size histogram.
Independent enumeration from the third-largest occurrence count verifies all
frequency tie sets without using the summed-frequency maximization procedure.

The 246 follow-up errors partition into 184 outside these sets, 52 choosing a
suboptimal member where a set contains an optimum, and 10 where it contains none.
The outside-set errors comprise 151 on the 53 frequency-feasible episodes and
33 on the seven exceptions. Six optimal follow-up answers also lie outside the
sets, all on exceptional episodes. Of the 71 same-profile-improvable errors,
52 are inside and 19 outside the frequency-maximizing sets. Thus the statistics
neither identify a causal usage/overlap split nor bound the number of errors
caused by overlap. Correctly solving the seven exceptions requires departing
from frequency maximization, whether or not the model estimates frequency well.

The interval calculation uses the two-sided Wilson score formula without
continuity correction, z = NormalDist().inv_cdf(0.975), and n = 60 separately
for each run, including invalid answers as failures. It assumes independent
episode outcomes as an approximation despite the five-episode prompt blocks;
it does not quantify run-level uncertainty or support a population-wide ranking.
The original archived uncertainty calculations remain unchanged.

Run python3 -B verify_selection_patterns.py to recompute the per-answer checks
and intervals. The JSON and Markdown under results/selection_patterns record
input hashes, per-run counts, aggregate denominators, and interpretation limits.
