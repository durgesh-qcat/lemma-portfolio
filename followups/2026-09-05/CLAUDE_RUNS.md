# Claude direct-API captures — 5 September 2026 (Pacific)

Two completed captures of the twelve released LemmaPortfolio V4 direct prompts
through the Anthropic Messages API (`api.anthropic.com`), scored with the released
scorer. They were captured with a separate direct-API harness, not the Codex CLI
workflow, so they sit outside `FOLLOWUP_RESULTS.json` and its completion audit.
Machine-readable rows, usage, and paired comparisons are in `CLAUDE_RESULTS.json`.

| Phase directory | Recorded model / effort | Exact optimum | Target coverage | Valid | Inference time | System prompt |
|---|---|---:|---:|---:|---:|---|
| `claude_fable_5_xhigh_r1/` | `claude-fable-5` / xhigh | 26/60 (43.3%) | 331/480 (69.0%) | 60/60 | 74.3 min | none |
| `claude_fable_5_1_xhigh_ctx_r1/` | `claude-fable-5-1` / xhigh | 26/60 (43.3%) | 335/480 (69.8%) | 60/60 | 87.5 min | **yes, disclosed below** |

Inference time is the sum of per-call wall-clock durations for the twelve
benchmark calls (streaming requests, sequential, one process per run). Every
response was a single JSON object with no prose, every stop reason was
`end_turn`, and no tool-use block appeared. Block-bootstrap 95% intervals for
exact accuracy are 31.7–55.0% (Fable 5) and 33.3–55.0% (Fable 5.1).

## Common protocol

- One stateless request per released prompt file, `prompts/DIRECT_PROMPTS/01.txt`
  through `12.txt`, in numerical order; prompt bytes verified against
  `prompts/PROMPT_SHA256SUMS.txt` before sending and recorded per call.
- `output_config.effort = xhigh`; `max_tokens = 128000` with streaming; the
  `thinking` parameter omitted (always on for these models); no tools, no
  sampling parameters, no server-side fallback (a fallback model would not be a
  measurement of the requested model).
- Raw final answers saved unchanged as `responses/NN.json` (only because every
  answer parsed as one JSON object). Complete API response bodies in `raw_api/`,
  per-call receipts (timings, usage, request/message ids, every attempt) in
  `CALL_RECEIPTS.json`, run totals in `RUN_COMPLETED.json`, configuration in
  `run_metadata.json`, the harness source under `harness/`, and a narrative
  `RUN_NOTE.md` in each phase. Readiness probes, the local harness log, and the
  API credential are not included.

## Disclosure: the Fable 5.1 row used a system prompt

With no system prompt, `claude-fable-5-1` declined all twelve released prompts
before generating anything: HTTP 200, `stop_reason: "refusal"`, empty content,
zero output tokens, provider category `reasoning_extraction`. Anthropic's public
documentation describes that category as requests asking the model to reproduce
its internal reasoning in the response text, which the benchmark prompt does not
do, and documents no remedy other than falling back to a different model. The
refusal reproduced on prompts 01 and 07 about two and a half hours apart, so it
is systematic rather than transient. Those bare-prompt refusals are not reported
as a scored row.

The Fable 5.1 phase therefore ran with the following operator system prompt
(exact bytes in `claude_fable_5_1_xhigh_ctx_r1/harness/system_context.txt`,
SHA-256 `26ca2dde77fa98af25c4e3032f02911a7d369dcdd504d75ea2a1ea0cd7440b20`):

> You are being evaluated on LemmaPortfolio, a published academic benchmark for
> Lean/Mathlib premise selection. The user message is the benchmark's released
> prompt, sent unchanged. Your answer will be scored against historical Mathlib
> dependency records and preserved verbatim in the benchmark's public results.
> Follow the user message's output instructions exactly.

The released user-message bytes were unchanged. `run_metadata.json` records the
system prompt, its hash, and a `protocol_deviation` field. The
`classifier_diagnostics/` folder holds the 16-output-token checks that motivated
this: the bare prompt is refused by `claude-fable-5-1` (prompts 01 and 07, two
times), accepted by `claude-fable-5` and `claude-opus-5` without any system
prompt, and accepted by `claude-fable-5-1` under the system prompt above (prompts
01 and 07). The Fable 5 row needed no system prompt and has no deviation.

When comparing rows, note that the Codex CLI follow-up rows also ran under that
tool's own system prompt (its text is not part of this repository), while the
consumer rows ran under each product's undisclosed system prompt. The Fable 5.1
row is the only one whose system prompt is published here.

## Provider incident in the Fable 5 run

Call 10's first attempt ended after about 1 minute 46 seconds with a mid-stream
`overloaded_error` from the API before any answer text (request id
`req_011Cekmz3nheg9fDo4NbotwN`). The harness of that moment treated the error as
fatal and exited; the failed attempt is preserved as the first `"call": "10"`
entry in `CALL_RECEIPTS.json`. The harness was revised to classify stream-delivered
overload and rate-limit errors as retryable, and the run resumed from call 10 about
two minutes later without touching calls 01–09. `run_metadata.json` lists the
resume and both harness copies are under `harness/`.

## Paired comparisons (exploratory)

From `CLAUDE_RESULTS.json`, using the same paired prompt-block bootstrap as the
Codex comparisons. Positive values favour the Claude row.

| Claude row minus Codex row | Exact Δ (pp) | 95% block interval | Coverage Δ (pp) | Discordant exact (Claude only / Codex only) |
|---|---:|---|---:|---|
| Fable 5 − Astra xhigh r1 | −1.7 | −8.3 to +5.0 | +0.6 | 9 / 10 |
| Fable 5 − Astra xhigh r2 | −6.7 | −16.7 to +3.3 | −0.2 | 7 / 11 |
| Fable 5 − Astra max r1 | −6.7 | −16.7 to +3.3 | −0.8 | 7 / 11 |
| Fable 5 − Sol xhigh r1 | +10.0 | +1.7 to +18.3 | +6.0 | 11 / 5 |
| Fable 5 − Sol xhigh r2 | +18.3 | +6.7 to +28.3 | +6.5 | 14 / 3 |
| Fable 5.1 (sys) − Astra xhigh r1 | −1.7 | −11.7 to +10.0 | +1.5 | 11 / 12 |
| Fable 5.1 (sys) − Astra xhigh r2 | −6.7 | −18.3 to +5.0 | +0.6 | 10 / 14 |
| Fable 5.1 (sys) − Astra max r1 | −6.7 | −20.0 to +8.3 | 0.0 | 8 / 12 |
| Fable 5.1 (sys) − Sol xhigh r1 | +10.0 | 0.0 to +20.0 | +6.9 | 16 / 10 |
| Fable 5.1 (sys) − Sol xhigh r2 | +18.3 | +8.3 to +30.0 | +7.3 | 14 / 3 |

The two Claude rows agree on 16 exact episodes and each solves 10 the other
misses (Fable 5 − Fable 5.1: 0.0 pp, interval −8.3 to +8.3). Intervals resample
the twelve five-episode blocks, not repeated generations; there is one run per
Claude row. Equal effort labels do not imply equal compute budgets.

## Evidence boundary

The analyst had already seen the released labels; the evaluated model received
only the released prompt (and, for Fable 5.1, the system prompt above). Prompt
hashes, response hashes, usage, and scores are independently rechecked by
`verify.py`. Serving weights, hidden routing, and the classifier's behaviour
cannot be authenticated from this export. No billing figure is claimed.
