# Post-hoc selection-pattern audit

All counts are recomputed offline from saved selections and hidden direct-use annotations.

| Run | Valid errors | Fixed freq. | Any freq. tie | Fixed greedy | Any greedy tie | Same-profile improvement |
|---|---:|---:|---:|---:|---:|---:|
| GPT SOL 5.6 Pro | 30 | 1 | 8 | 5 | 12 | 11 |
| GPT SOL 5.6 xhigh | 42 | 2 | 8 | 4 | 11 | 10 |
| DeepSeek Instant + DeepThink | 59 | 2 | 10 | 1 | 6 | 20 |
| DeepSeek Expert + DeepThink | 53 | 0 | 11 | 2 | 10 | 15 |
| Qwen 3.8 Max-Thinking | 43 | 2 | 3 | 2 | 7 | 8 |
| Qwen 3.7 Plus-Thinking | 54 | 1 | 2 | 1 | 4 | 8 |
| GPT-6 Astra / xhigh / 1 | 33 | 3 | 9 | 4 | 13 | 9 |
| GPT-6 Astra / xhigh / 2 | 30 | 3 | 6 | 3 | 11 | 9 |
| GPT-5.6 Sol / xhigh / 1 | 40 | 2 | 6 | 3 | 9 | 10 |
| GPT-5.6 Sol / xhigh / 2 | 45 | 2 | 10 | 3 | 13 | 11 |
| GPT-6 Astra / max / 1 | 30 | 3 | 11 | 3 | 14 | 11 |
| Claude Fable 5 / xhigh | 34 | 3 | 10 | 1 | 12 | 10 |
| Claude Fable 5.1 / xhigh / context | 34 | 5 | 10 | 2 | 14 | 11 |
| preliminary_web TOTAL | 281 | 8 | 42 | 15 | 50 | 72 |
| followup TOTAL | 246 | 21 | 62 | 19 | 86 | 71 |
| all TOTAL | 527 | 29 | 104 | 34 | 136 | 143 |

## Nominal Wilson 95% intervals

| Run | Exact /60 | 95% interval (%) |
|---|---:|---:|
| GPT SOL 5.6 Pro | 25 | 30.1--54.3 |
| GPT SOL 5.6 xhigh | 18 | 19.9--42.5 |
| DeepSeek Instant + DeepThink | 1 | 0.3--8.9 |
| DeepSeek Expert + DeepThink | 7 | 5.8--22.2 |
| Qwen 3.8 Max-Thinking | 12 | 11.8--31.8 |
| Qwen 3.7 Plus-Thinking | 6 | 4.7--20.1 |
| GPT-6 Astra / xhigh / 1 | 27 | 33.1--57.5 |
| GPT-6 Astra / xhigh / 2 | 30 | 37.7--62.3 |
| GPT-5.6 Sol / xhigh / 1 | 20 | 22.7--45.9 |
| GPT-5.6 Sol / xhigh / 2 | 15 | 15.8--37.2 |
| GPT-6 Astra / max / 1 | 30 | 37.7--62.3 |
| Claude Fable 5 / xhigh | 26 | 31.6--55.9 |
| Claude Fable 5.1 / xhigh / context | 26 | 31.6--55.9 |

## Frequency-tie geometry

- Episodes with at least one optimum among frequency maximizers: 53/60.
- Tied triples: total 408; mean 6.8; median 4; range 1--35.
- Frequency-maximizing optima: 71/78 distinct optimal triples.
- Episodes without a frequency-maximizing optimum: MLP4B_0000, MLP4B_0005, MLP4B_0022, MLP4B_0027, MLP4B_0035, MLP4B_0050, MLP4B_0051.

## Follow-up error partition (descriptive, not causal)

- outside_frequency_set: 184
- inside_set_with_optimum: 52
- inside_set_without_optimum: 10
- outside_on_frequency_feasible_episode: 151
- outside_on_frequency_infeasible_episode: 33
- profile_improvable_inside_frequency_set: 52
- profile_improvable_outside_frequency_set: 19

A non-frequency-maximizing selection is not necessarily a usage-estimation error: seven episodes require such a selection, and overlap improvements also exist outside frequency-maximizing sets.

## Definitions and interpretation

- frequency: Rank candidates by the number of target proofs directly referencing them; no overlap correction.
- greedy: Sequentially select the largest marginal union coverage, recomputing after each pick.
- fixed: Ascending candidate-ID tie breaking, as in the construction filters.
- any_frequency: Accept every triple maximizing the sum of individual occurrence counts.
- any_greedy: Accept every triple reachable by any sequence of marginal-coverage greedy ties.
- same_degree_profile_improvable: A triple with the same multiset of individual occurrence counts has larger union coverage.
- pattern_denominator: Valid non-optimal answer instances; repeated episodes are not independent problems.
- interpretation: Hidden-label descriptive comparisons, not identified internal model strategies or evaluated repairs.
- frequency_geometry: Distinct test episodes and all tied frequency-maximizing triples; not weighted by model success.
- error_decomposition: Outside-frequency, inside-with-optimum, and inside-without-optimum partition valid follow-up errors; these are not causal error labels.
- wilson_95: Nominal two-sided 95% Wilson score interval, no continuity correction, n=60 per run including invalid answers.
- uncertainty_scope: Independent-episode binomial approximation; five-episode prompt blocks may induce dependence. Not deployment or run-level uncertainty.

Run python3 -B verify_selection_patterns.py to reproduce.
