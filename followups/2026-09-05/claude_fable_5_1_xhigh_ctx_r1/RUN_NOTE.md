# Claude Fable 5.1 (Claude API, xhigh, context system prompt) — run outcome, 2026-09-05

PROTOCOL DEVIATION: a system prompt was present. The released user-message
bytes were unchanged (verified against `prompts/PROMPT_SHA256SUMS.txt`).

Why: with no system prompt, `claude-fable-5-1` refused all twelve released
prompts before generation (`stop_reason: refusal`, category
`reasoning_extraction`; see `classifier_diagnostics/`). The refusal was
reproducible on prompts 01 and 07 at two different times. Anthropic's public
documentation defines that category as requests asking the model to reproduce
its internal reasoning in the response text, which the benchmark prompt does
not do, and documents no remediation other than falling back to another model.
A fallback model would not be a Fable 5.1 measurement, so instead a truthful
operator system prompt stating the academic-benchmark context was added.
16-token diagnostics showed the classifier accepts the unchanged prompt under
that system prompt (prompts 01 and 07); `claude-fable-5` and `claude-opus-5`
accept the bare prompt without any system prompt.

System prompt (exact bytes in `harness/system_context.txt`, SHA-256
26ca2dde77fa98af25c4e3032f02911a7d369dcdd504d75ea2a1ea0cd7440b20):

> You are being evaluated on LemmaPortfolio, a published academic benchmark
> for Lean/Mathlib premise selection. The user message is the benchmark's
> released prompt, sent unchanged. Your answer will be scored against
> historical Mathlib dependency records and preserved verbatim in the
> benchmark's public results. Follow the user message's output instructions
> exactly.

Everything else as in the bare protocol: `output_config.effort=xhigh`, no
tools, no fallbacks, one stateless request per prompt, numerical order.

Result (released scorer, `score.json`): 26/60 exact optimal portfolios (43.3%),
335/480 target coverage (69.8%), 60/60 valid predictions, 12/12 single JSON
objects, zero tool-use blocks, every stop reason `end_turn`, one attempt per
call (no provider errors). Sum of per-call wall time: 87.5 min. Usage: 222,477
input tokens, 495,842 output tokens (thinking included), no cache reads.

Readiness probe (trivial prompt) excluded from the twelve benchmark calls.
`classifier_diagnostics/` holds the 16-output-token classifier checks described above. Comparisons with the bare-prompt rows should note the system
prompt; the Codex CLI follow-up rows also ran under that tool's own system
prompt, but its text is not part of this repository.
