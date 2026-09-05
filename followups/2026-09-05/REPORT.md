# LemmaPortfolio follow-up evaluation

Updated: 2026-09-05T09:51:15.516456+00:00

Status: all core phases and the retained second repeat pair completed and audited; third runs cancelled at user request. No inference remains queued.


These are separately disclosed post-release follow-up experiments, not additions to the original frozen blind consumer panel. Original data, consumer scores, and paper artifacts are unchanged. See PAPER_HANDOFF.md for integration guidance.

## Complete direct runs

| Run | Exact optimal | Target coverage | Valid | Inference minutes | Output tokens (including reasoning) |
|---|---:|---:|---:|---:|---:|
| astra_xhigh_r1_prior | 27/60 (45.0%) | 328/480 (68.3%) | 60/60 | 78.6 | 138,274 |
| sol_xhigh_r1 | 20/60 (33.3%) | 302/480 (62.9%) | 60/60 | 80.7 | 213,575 |
| astra_max_r1 | 30/60 (50.0%) | 335/480 (69.8%) | 60/60 | 147.2 | 208,798 |
| sol_xhigh_r2 | 15/60 (25.0%) | 300/480 (62.5%) | 60/60 | 78.6 | 219,441 |
| astra_xhigh_r2 | 30/60 (50.0%) | 332/480 (69.2%) | 60/60 | 114.6 | 141,011 |

The prior Astra xhigh run is included for comparison, not counted as a new execution. Invalid or missing outputs retain the full denominator and score zero. No answers are repaired and no best run is selected.

## Matched-harness comparisons

GPT-6 Astra (Codex CLI, xhigh) minus sol xhigh r1: exact accuracy +11.7 percentage points (paired prompt-block bootstrap 95% interval +3.3 to +20.0); target coverage +5.4 points. Discordant exact counts: 11 versus 4.

astra max r1 minus GPT-6 Astra (Codex CLI, xhigh): exact accuracy +5.0 percentage points (paired prompt-block bootstrap 95% interval -6.7 to +16.7); target coverage +1.5 points. Discordant exact counts: 6 versus 3.

astra max r1 minus sol xhigh r1: exact accuracy +16.7 percentage points (paired prompt-block bootstrap 95% interval +1.7 to +31.7); target coverage +6.9 points. Discordant exact counts: 15 versus 5.

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

- sol_xhigh: 2 complete run(s), mean exact accuracy 29.17%, sample SD 5.89 pp.
- astra_xhigh: 2 complete run(s), mean exact accuracy 47.50%, sample SD 3.54 pp.

The original plan allowed two additional Sol/Astra xhigh pairs. At user request, only the already-started second pair is retained; the third Sol and Astra runs are cancelled before starting. This time-saving amendment was made after core scores were known, not under a predeclared stopping rule. All started runs are retained, with no best-run selection. See USER_QUEUE_CHANGE.json.

## Protocol and limitations

The exact prompts, model settings, call order, 2400-second per-call ceiling, no-retry policy, and analysis plan are in `PROTOCOL_EXPORT.json` (path-redacted; original hash in `EXPORT_MANIFEST.json`). Each call uses the prior Astra capture harness, a new process and empty temporary working directory, user configuration ignored, and tools, web, memory, skills, project instructions and delegation disabled. Raw responses are frozen before phase scoring. CLI source/configuration and model-catalog snapshots remain in the local archive and are not included in this GitHub export.

The analyst had already seen released labels and historical results. Evaluated processes receive only the original prompt bytes. The prompts retain their historical word "unreleased" solely for byte-identical matching; this is not a new blind test. CLI model labels and settings are recorded, but underlying checkpoints, hidden serving behavior, numerical reasoning budgets, and monetary charges are not independently authenticated. Effort labels are not equal compute budgets.

Each scored phase has a `capture_audit.json` checking fresh sessions, one turn, prompt equality, raw response/event agreement and zero observed tool use. Intentional startup diagnostics report that Code Mode is disabled and skill descriptions are removed. The original release verifier and 23 scorer tests passed during setup. Per-item scores, ties, comparisons, token counts and timings are saved in JSON for inspection.

## Implications for writing

Keep the consumer panel and Codex follow-up visibly separate. Describe structured results as performance of the complete support-prediction, truncation and tie-breaking pipeline. The historical q sweep rules out a simple rescue by changing only q under the same tie-break, but does not isolate the cause of every failure. Report measured effort/latency tradeoffs without assuming max is better, and avoid a stable-model-ranking claim without repeated runs.

## Export boundary

Raw final answers are byte-identical to the frozen captures. Full Codex event streams, readiness probes, model catalogs, machine-local paths, and account allowance details remain local. Audit receipts are author-reported; the exported verifier independently reproduces the mathematical scores, not the omitted operational logs or serving weights. VALIDATION.json is the original local Codex completion receipt, not proof of a later GitHub CI run. The earlier September 4 snapshot remains unchanged.

## Separate Claude direct-API captures

Two completed direct Anthropic Messages API runs of the same twelve released prompts are included outside the Codex tables above, scored with the released scorer. They used a separate harness (one stateless request per prompt, no tools, no fallback, xhigh effort).

| Run | Exact optimal | Target coverage | Valid | Inference minutes | Output tokens (including reasoning) |
|---|---:|---:|---:|---:|---:|
| claude_fable_5_xhigh_r1 | 26/60 (43.3%) | 331/480 (69.0%) | 60/60 | 74.3 | 423,618 |
| claude_fable_5_1_xhigh_ctx_r1 (system prompt) | 26/60 (43.3%) | 335/480 (69.8%) | 60/60 | 87.5 | 495,842 |

The Fable 5.1 row carries a disclosed deviation: without a system prompt, `claude-fable-5-1` refused every bare released prompt before generation (provider category `reasoning_extraction`, reproduced at two times), so that row ran with a short, truthful operator system prompt while the released user-message bytes stayed unchanged. The Fable 5 row needed no system prompt. Paired against the Codex rows, both Claude rows are within the block-bootstrap interval of every Astra run and above both Sol runs; see [CLAUDE_RUNS.md](CLAUDE_RUNS.md) for the system prompt text, classifier diagnostics, the one provider-overload retry, and all paired comparisons, and `CLAUDE_RESULTS.json` for machine-readable rows. Single runs; not a stable ranking. No OpenRouter result is included.
