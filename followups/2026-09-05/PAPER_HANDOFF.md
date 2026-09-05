# Paper-writing handoff: final follow-up results

This is the final completed experimental package for Aishwarya Das and Durgesh
Kumar. **The shortened Codex queue is complete.** The manuscript/PDFs still describe the
original results and need integration; this handoff does not claim they are updated.

## 1. Numbers to use

Each full run evaluates the same 60 unique episodes, with 480 target instances.
The primary metric is exact optimal-portfolio accuracy, not target coverage.

| Model / effort | Run | Exact optimum | Target coverage | Valid | Inference minutes |
|---|---:|---:|---:|---:|---:|
| GPT-6 Astra / xhigh | 1 | 27/60 (45.0%) | 328/480 (68.3%) | 60/60 | 78.6 |
| GPT-6 Astra / xhigh | 2 | 30/60 (50.0%) | 332/480 (69.2%) | 60/60 | 114.6 |
| GPT-5.6 Sol / xhigh | 1 | 20/60 (33.3%) | 302/480 (62.9%) | 60/60 | 80.7 |
| GPT-5.6 Sol / xhigh | 2 | 15/60 (25.0%) | 300/480 (62.5%) | 60/60 | 78.6 |
| GPT-6 Astra / max | 1 | 30/60 (50.0%) | 335/480 (69.8%) | 60/60 | 147.2 |

Across the two xhigh runs:

| Model | Mean exact accuracy | Sample SD (percentage points) | Mean target coverage |
|---|---:|---:|---:|
| Astra | 47.50% | 3.54 | 68.75% |
| Sol | 29.17% | 5.89 | 62.71% |

The mean exact-score gap is 18.33 percentage points. These are averages over two
complete runs, not best-of-two, pass@k, or 120 independent benchmark items. With
only two runs, standard deviations are descriptive and imprecisely estimated.
All five runs must remain visible; do not select only the highest-scoring run.

For every number, see `FOLLOWUP_RESULTS.json` (`direct_rows`, `repeats`, `usage`)
and the corresponding phase's `score.json` (`summary`, `per_item`). Timings are
summed observed call wall times, not a controlled throughput benchmark. Token
counts include reasoning where reported; no monetary cost was independently measured.

## 2. What the new evidence supports

- Astra xhigh had higher exact accuracy and target coverage than Sol xhigh in
  both observed runs under the matched Codex capture harness. This supports a
  bounded empirical comparison, not a universal model-family ranking.
- Max did not establish a reliable exact-accuracy gain: its 30/60 matches Astra
  xhigh run 2. Its 335 covered targets exceed 328 and 332 for xhigh, at longer
  observed runtime. Only one max run exists.
- On a fresh matched 20-episode Astra diagnostic, direct selection scored 8/20
  exact and covered 106/160 targets. Structured support prediction followed by
  the released q=2 exhaustive optimizer scored 4/20 and covered 100/160. Both
  arms were fully valid, so missing outputs do not explain this particular gap.

The Astra support-width sweep re-scores the same captured rankings:

| Retained candidates per target (q) | Exact /20 | Target coverage /160 |
|---|---:|---:|
| 1 | 2 | 91 |
| 2 (primary) | 4 | 100 |
| 3 | 4 | 96 |
| 4 | 4 | 96 |

Changing q alone did not close the direct-selection gap. At q=2, 16/20 episodes
have multiple predicted-optimal portfolios, and 13/20 tied sets contain a true
optimum. That **does not mean 13/20 was achieved**: the deployed lexicographic
tie-break gets 4/20. Uniform selection among predicted-optimal ties would have
an offline expected exact count of about 5.65/20. Choosing ties using true labels
would leak the answer and is not a legitimate alternative score.

Historical q sweeps also fail to rescue the original structured captures: Pro
scores 1,1,1,0 and Sol xhigh 0,0,0,0 exact at q=1,2,3,4. The historical sweeps
are retrospective; all four widths were specified before the new Astra diagnostic
but remain exploratory. The result concerns the complete support-prediction,
truncation, optimization, and tie-breaking pipeline; it does not isolate a single
cause or show that decomposition generally fails.

## 3. Suggested manuscript wording

> In a separately disclosed post-release evaluation using the same Codex capture
> harness and released prompts, GPT-6 Astra xhigh obtained 27/60 and 30/60 exact
> optima, while GPT-5.6 Sol xhigh obtained 20/60 and 15/60. Mean exact accuracy
> across two runs was 47.5% and 29.2%, respectively. All outputs were valid.
> These repeated measurements cover the same 60 episodes and provide limited
> evidence about generation variability, rather than a provider-family ranking.
> A single Astra max run obtained 30/60, matching the second xhigh run while
> taking longer. On a fresh 20-episode diagnostic, direct selection obtained
> 8/20 exact optima versus 4/20 for the structured-support-plus-optimizer pipeline;
> varying the retained support width from one to four did not close that gap.

Keep this paragraph/table visibly separate from the original consumer panel.
The original Pro 25/60 and Sol xhigh 18/60 rows remain unchanged and refer to
different consumer captures, not these Codex runs. Do not replace them with
new Codex scores or imply a controlled improvement over the consumer Pro row.

## 4. Methods and limitations that must accompany it

All full direct runs used the exact 12 released five-episode prompts and Codex
CLI 0.153.0. Calls had fresh processes/empty working directories; tools, web,
memory, skills, delegation, project documents, and previous conversations were
disabled. The new diagnostic used D04, D05, D06, D12, with direct/support order
counterbalanced across four blocks and separate fresh sessions. Complete raw
responses were frozen before scoring; no mathematical retries or answer repairs
were made. The analyst had seen the public labels, but the evaluated processes
were not given them. This is not a newly sealed blind evaluation.

Retain these qualifications:

- Equal effort names do not establish equal compute budgets. Hidden serving
  checkpoints/routing and monetary cost are not independently authenticated.
- The original first Astra run preceded the follow-up protocol freeze. Later
  calls follow its recorded plan, except for the disclosed queue reduction.
- Three runs per xhigh model were originally contemplated; the author shortened
  the queue after seeing core results, leaving two runs each. This was a time
  decision, not a predeclared stopping rule. The cancelled third runs never began.
- The recorded comparison intervals resample five-episode prompt blocks; they
  do not measure run-to-run uncertainty. They are exploratory and unadjusted for
  multiple comparisons. In particular, max minus first xhigh exact accuracy has
  a 95% block-bootstrap interval of about -6.7 to +16.7 percentage points.
- The structured contrast has only four blocks; its -20-point exact difference
  has a descriptive block-bootstrap interval of -45 to 0 points. Do not sell
  this small diagnostic as a general causal or statistical-superiority result.
- Historical dependencies are not proof-success labels or logical necessity.
  The 60-episode conditioned stress set does not represent all of Mathlib.
- GitHub has raw final answers and local-audit receipts, not full event streams;
  independent readers can reproduce scores but not authenticate omitted logs.

## 5. Integration checklist and source locations

1. In `paper/source/body.tex`, add a distinctly labeled post-release follow-up
   subsection and update the blanket claim that controlled repetitions are
   unavailable: it remains true for the original consumer panel, not this follow-up.
2. Add a separate follow-up table; preserve the original consumer table in
   `paper/source/generated/results_section.tex`. Do not hand-edit original scores.
3. Update the abstract/result wording in `paper/source/generated/results_macros.tex`
   as appropriate, keeping the original consumer range explicitly scoped.
4. Extend the structured diagnostic and limitations with the fresh 8/20 vs 4/20
   comparison, q sweep, and tie-breaking caveat. Keep causal claims narrow.
5. Add run-level provenance, timing/token details, repeat means/SDs, and the queue
   amendment to `paper/source/supplement/supplement_body.tex` or a separate included
   follow-up supplement file. Original generated supplement values remain unchanged.
6. Rebuild the anonymous review PDF, check the four-page main-body constraint,
   review anonymity and all numbers, then regenerate repository checksums and
   run both verification commands below. The named GitHub URL must not appear
   in the anonymous manuscript.

```sh
python3 verify_release.py
python3 followups/2026-09-05/verify.py
```

The first command verifies all current file hashes and original V4 scores; the
second independently reproduces this final follow-up package. Future intentional
paper edits will require updating the follow-up verifier's strict baseline-file
preservation policy with an explicit, reviewed allowlist; do not weaken checks
on data, prompts, responses, or numerical results.

## 6. Claude direct-API rows

Two completed direct Anthropic Messages API runs of `claude-fable-5` and
`claude-fable-5-1`, both at xhigh effort, cover all twelve released prompts with
60/60 valid answers each. Released-scorer results: Fable 5 **26/60 exact,
331/480 coverage** (74.3 min); Fable 5.1 **26/60 exact, 335/480 coverage**
(87.5 min). They are outside the Codex workflow and its audit, and are not in
`FOLLOWUP_RESULTS.json`; use `CLAUDE_RESULTS.json` and `CLAUDE_RUNS.md`.

**Report the Fable 5.1 row with its disclosure.** Without a system prompt that
model refused every released prompt before generation (provider category
`reasoning_extraction`; reproduced on two prompts at two times). The scored row
ran with a short, truthful operator system prompt stating that the user message
is a published academic benchmark prompt; the released user-message bytes were
unchanged. The exact system prompt, its hash, and 16-token classifier
diagnostics (bare prompt refused by Fable 5.1; accepted by Fable 5 and Opus 5;
accepted by Fable 5.1 under the system prompt) are published. The refused bare
run is not reported as a scored row. The Fable 5 row has no deviation.

Suggested wording: single direct-API runs, same released prompts, xhigh effort,
no tools; Fable 5.1 with a published system prompt. Both rows sit within the
paired block-bootstrap interval of every Astra run and above both Sol runs
(Fable 5 − Sol xhigh r1: +10.0 pp exact, +1.7 to +18.3). Do not rank the Claude
rows against the Codex rows as a stable ordering, and do not compare their
timings with Codex timings as compute budgets. The Fable 5 run had one
mid-stream provider overload on call 10 that was retried; both attempts are in
its receipts.

Use a clean clone for the whole-directory release verifier; ignored local
credentials or scratch captures are not published and deliberately fall outside
the release inventory. Preserve them locally rather than adding them to Git.
