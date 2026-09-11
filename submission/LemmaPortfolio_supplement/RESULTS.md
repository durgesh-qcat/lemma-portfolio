# Results accompanying the paper

All direct model rows use the same 60 test episodes. Missing or malformed answers
receive zero and stay in the denominators. The two additional scores defined in
the technical supplement are reported below as percentages:

- Share of maximum coverage: mean of achieved coverage / episode maximum.
- Occurrence recall: selected recorded candidate-target pairs / all recorded pairs,
  pooled over the evaluated episodes (814 pairs in the complete test set).

Run `python3 -B verify_results.py` to recompute and check both this table and
`results/paper_results.json`. The full verification also rebuilds the original
response transcriptions and independently scores the raw follow-up answers.

| Model / baseline | Optimal /60 | Mean coverage /8 | Valid /60 | Share of maximum (%) | Occurrence recall (%) |
|---|---:|---:|---:|---:|---:|
| Uniform random (expectation) | 0.14 | 2.35 | 60 | 37.62 | 18.75 |
| Character TF-IDF | 0 | 3.77 | 60 | 60.40 | 29.48 |
| GPT SOL 5.6 Pro | 25 | 4.98 | 55 | 79.64 | 38.94 |
| GPT SOL 5.6 xhigh | 18 | 5.08 | 60 | 81.39 | 39.80 |
| DeepSeek Instant + DeepThink | 1 | 4.20 | 60 | 67.06 | 34.89 |
| DeepSeek Expert + DeepThink | 7 | 4.60 | 60 | 73.41 | 36.86 |
| Qwen 3.8 Max-Thinking | 12 | 4.32 | 55 | 68.93 | 34.03 |
| Qwen 3.7 Plus-Thinking | 6 | 4.05 | 60 | 64.64 | 31.82 |
| GPT-6 Astra / xhigh / 1 | 27 | 5.47 | 60 | 87.42 | 42.14 |
| GPT-6 Astra / xhigh / 2 | 30 | 5.53 | 60 | 88.41 | 42.87 |
| GPT-5.6 Sol / xhigh / 1 | 20 | 5.03 | 60 | 80.48 | 39.19 |
| GPT-5.6 Sol / xhigh / 2 | 15 | 5.00 | 60 | 80.00 | 39.19 |
| GPT-6 Astra / max / 1 | 30 | 5.58 | 60 | 89.37 | 43.24 |
| Claude Fable 5 / xhigh | 26 | 5.52 | 60 | 88.29 | 42.87 |
| Claude Fable 5.1 / xhigh / context | 26 | 5.58 | 60 | 89.44 | 43.24 |

The uniform-random row is an exact expectation over all 560 portfolios, not
a sampled response set. The saved deterministic hash draw in the original
results is a different baseline and is not the random row in the paper.

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

## Coverage shortfall and candidate replacements

Across the seven follow-up runs, 163 answers are exactly one target short.
Reaching an optimum requires one replacement for 134, two for 26, and three
for 3. Of each portfolio's 39 single-replacement neighbors, the number that
is optimal is zero for 29 answers, one for 122, two for 10, and three for 2.
These are repeated responses on the same episodes and retrospective checks
using the true labels, not results of a model repair experiment. Per-answer
records are in `descriptive/one_short_replacement_audit.json`.
