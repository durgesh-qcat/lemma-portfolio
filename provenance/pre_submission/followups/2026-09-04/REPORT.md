# LemmaPortfolio follow-up evaluation

Updated: 2026-09-05T04:12:59.405602+00:00

Status: in progress; pending core phases: astra_max_r1.

These are separately disclosed post-release follow-up experiments, not additions to the original frozen blind consumer panel. The original benchmark data, consumer scores, and paper have not been edited; the repository README now links this separate follow-up.

## Complete direct runs

| Run | Exact optimal | Target coverage | Valid | Inference minutes | Output tokens (including reasoning) |
|---|---:|---:|---:|---:|---:|
| astra_xhigh_r1_prior | 27/60 (45.0%) | 328/480 (68.3%) | 60/60 | 78.6 | 138,274 |
| sol_xhigh_r1 | 20/60 (33.3%) | 302/480 (62.9%) | 60/60 | 80.7 | 213,575 |

The prior Astra xhigh run is included for comparison, not counted as a new execution. Invalid or missing outputs retain the full denominator and score zero. No answers are repaired and no best run is selected.

## Matched-harness comparisons

GPT-6 Astra (Codex CLI, xhigh) minus sol xhigh r1: exact accuracy +11.7 percentage points (paired prompt-block bootstrap 95% interval +3.3 to +20.0); target coverage +5.4 points. Discordant exact counts: 11 versus 4.

Intervals resample the twelve five-episode blocks; they do not measure run-to-run generation variability or establish a causal effect of model weights. Comparisons are exploratory and not multiplicity-adjusted.

## Astra structured diagnostic

Fresh direct20: 8/20 exact, 106/160 covered targets, 20/20 valid.

| Support prefix | Exact /20 | Coverage /160 | Edge F1 | Mean tied predicted optima |
|---|---:|---:|---:|---:|
| q=1 | 2 | 91 | 62.6% | 7.5 |
| q=2 | 4 | 100 | 77.9% | 6.5 |
| q=3 | 4 | 96 | 79.7% | 6.8 |
| q=4 | 4 | 96 | 79.1% | 6.2 |

q=2 is the primary released pipeline. The entire q sweep was specified before this Astra diagnostic but remains secondary/exploratory; no width is chosen by its test score. The two conditions use fresh sessions, identical episodes and counterbalanced call order across four blocks. This small controlled comparison is not a general causal claim about decomposition.

The primary support pipeline minus fresh direct selection has an exact-score difference of -20.0 percentage points (four-block bootstrap 95% interval -45.0 to +0.0). The pipeline alone is exact on 0 episodes; direct selection alone is exact on 4. The interval is descriptive and the four-block sample is too small for a broad superiority claim.

At q=2, 16/20 episodes have multiple predicted-optimal portfolios, and 13/20 tied sets contain a true optimum. Uniform tie-breaking would have expected exact count 5.65/20. These are offline ambiguity diagnostics, not label-assisted alternative selections. The q sweep re-scores the same captured rankings; it is not a sweep of differently worded prompts.

## Historical support-prefix sensitivity


Exploratory post-hoc analysis; no new inference. Original q=2 scores and edge counts reproduce exactly.

| Historical row | q | Exact /20 | Coverage /160 | Edge F1 | Mean tied optima | True optimum among ties /20 |
|---|---:|---:|---:|---:|---:|---:|
| gpt_sol_5_6_pro | 1 | 1 | 86 | 59.3% | 7.2 | 8 |
| gpt_sol_5_6_pro | 2 | 1 | 92 | 72.6% | 5.3 | 9 |
| gpt_sol_5_6_pro | 3 | 1 | 91 | 74.2% | 5.0 | 10 |
| gpt_sol_5_6_pro | 4 | 0 | 86 | 74.0% | 5.9 | 11 |
| gpt_sol_5_6_xhigh | 1 | 0 | 78 | 56.6% | 8.3 | 8 |
| gpt_sol_5_6_xhigh | 2 | 0 | 78 | 69.1% | 9.7 | 9 |
| gpt_sol_5_6_xhigh | 3 | 0 | 81 | 71.9% | 9.8 | 9 |
| gpt_sol_5_6_xhigh | 4 | 0 | 80 | 72.7% | 10.1 | 11 |

The tie diagnostics use labels only to measure ambiguity after selection. They are not an alternative deployable optimizer. The actual pipeline always uses the original lexicographic tie break.


At q=2, the tied predicted-best sets contain a true optimum on 9/20 episodes for each historical GPT row. Lexicographic tie-breaking attains 1/20 for Pro and 0/20 for xhigh; exhaustive expectations under uniform tie-breaking are approximately 2.65/20 and 1.28/20, not nine. Choosing the true-best member of each tie set would leak labels and is not a deployable score.

## Repeatability

- sol_xhigh: 1 complete run(s), mean exact accuracy 33.33%, SD unavailable from one run.
- astra_xhigh: 1 complete run(s), mean exact accuracy 45.00%, SD unavailable from one run.

Two additional complete Sol/Astra xhigh pairs are conditionally planned. Each pair starts only with at least 25% weekly allowance remaining and within 20 hours of the initial protocol freeze. Capacity decisions are independent of observed scores; all started runs and any failures are retained. Partial direct20 diagnostics are not spliced into 60-episode repetitions.

## Protocol and limitations

The exact prompts, model settings, call order, 2400-second per-call ceiling, no-retry policy, and analysis plan are in `PROTOCOL_EXPORT.json` (a path-redacted export; original digest in `EXPORT_MANIFEST.json`). Each call uses the prior Astra capture harness, a new process and empty temporary working directory, user configuration ignored, and tools, web, memory, skills, project instructions and delegation disabled. Raw responses are frozen before phase scoring. CLI source/configuration and model-catalog snapshots are retained in the local capture archive, not this GitHub export.

The analyst had already seen released labels and historical results. Evaluated processes receive only the original prompt bytes. The prompts retain their historical word "unreleased" solely for byte-identical matching; this is not a new blind test. CLI model labels and settings are recorded, but underlying checkpoints, hidden serving behavior, numerical reasoning budgets, and monetary charges are not independently authenticated. Effort labels are not equal compute budgets.

Each scored phase has a `capture_audit.json` checking fresh sessions, one turn, prompt equality, raw response/event agreement and zero observed tool use. Intentional startup diagnostics report that Code Mode is disabled and skill descriptions are removed. The original release verifier and 23 scorer tests passed during setup. Per-item scores, ties, comparisons, token counts and timings are saved in JSON for inspection.

## Implications for writing

Keep the consumer panel and Codex follow-up visibly separate. Describe structured results as performance of the complete support-prediction, truncation and tie-breaking pipeline. The historical q sweep rules out a simple rescue by changing only q under the same tie-break, but does not isolate the cause of every failure. Report measured effort/latency tradeoffs without assuming max is better, and avoid a stable-model-ranking claim without repeated runs.

## Export evidence boundary

This is a fixed snapshot of completed phases, not a live dashboard. Raw final answers are byte-identical to their frozen captures. Scores, per-item analyses, audit receipts, and per-call usage/timing are included. Full event streams, readiness probes, model catalogs, account information, and machine-local execution files remain in the local archive; the supplied capture audits are therefore author-reported receipts, not independently replayable operational logs. `verify.py` independently recomputes the mathematical scores, sweeps, and comparisons from the exported answers. It cannot authenticate the serving model or audit the omitted event streams.
