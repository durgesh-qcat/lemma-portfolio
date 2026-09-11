# Exact oracle and construction controls

The submitted benchmark has 30 development episodes and 60 test episodes. Each
episode offers 16 candidate lemmas, eight targets, and a budget of three lemmas.
The exact oracle enumerates all 560 triples and maximizes the number of targets
whose recorded proof-use set intersects the selected triple. Every maximizing
triple is accepted. This is an annotation-based coverage score; it does not run
a prover or establish that a selected lemma set can prove a target.

From the repository root, independently reconstruct all 50,400 portfolios:

```sh
python3 -B tools/verify_oracle.py
python3 -B tools/verify_oracle.py --json
```

The check uses Python 3.10+ and the standard library. It verifies the complete
optimum sets and coverage histograms, public/label alignment, proof-use counts,
development/test module separation, greedy tie probabilities, and all submitted
test frequency-maximizing sets. It imports no release scorer and changes no
files. The repository's full verification also runs this check.

| Annotation-aware control | Development /30 | Test /60 |
|---|---:|---:|
| Exact exhaustive oracle | 30 | 60 |
| Greedy, ascending candidate-ID ties used in construction | 0 | 0 |
| Greedy, descending candidate-ID ties | 28 | 57 |
| At least one greedy tie path reaches an optimum | 29 | 59 |
| Greedy, uniform random choice at each tied step (expected count) | 551/30 ≈ 18.37 | 13469/360 ≈ 37.41 |
| An optimum exists among frequency-maximizing triples | 26 | 53 |

These controls use the true proof-use annotations. They are post-hoc checks of
the benchmark construction, not statement-only model baselines. Construction
deliberately excluded episodes solved by its fixed greedy rule; reversing its
tie order often succeeds. An optimum existing within a tie set is an oracle
upper bound, not an answer identified without labels. Uniform random greedy
ties are sampled at each step, not uniformly over distinct final triples.

The test episodes have 78 optimal triples in total. The frequency-maximizing
sets contain 408 triples (mean 6.8, median 4, range 1–35); they contain an optimum
on 53 of the 60 episodes. Frequency maximizes summed individual occurrences;
the exact oracle maximizes their union coverage. The final paper's answer-level
pattern analysis and error partition are reproduced by
[`verify_selection_patterns.py`](../submission/LemmaPortfolio_supplement/verify_selection_patterns.py).

All inputs come from the exact submitted supplement:

- [Released public episodes and labels](../submission/LemmaPortfolio_supplement/original_release/data/).
- [Independent mathematical audit and per-episode greedy distributions](../submission/LemmaPortfolio_supplement/original_release/results/posthoc_math_audit.json).
- [Frequency tie sets and saved-answer selection patterns](../submission/LemmaPortfolio_supplement/results/selection_patterns.md).
- [Construction settings and interpretation](../submission/LemmaPortfolio_supplement/REPRODUCIBILITY.md).
- [Predicted-support optimizer tie audit](../submission/LemmaPortfolio_supplement/original_release/results/posthoc_predicted_tie_audit.json).

The predicted-support diagnostic is separate from the true-label construction
controls. Among its predicted maximizers, an actual optimum exists on 9/20 Pro,
9/20 Sol, and 13/20 Astra episodes; the fixed selection rule achieves 1/20,
0/20, and 4/20 respectively. The first two use the original fixed 20-ID subsets;
Pro's complete matched direct/target-wise comparison has only 15 pairs. See the
[submitted results](../submission/LemmaPortfolio_supplement/RESULTS.md) and
[Astra diagnostic](../submission/LemmaPortfolio_supplement/followups/2026-09-05/astra_diagnostic/score.json).
