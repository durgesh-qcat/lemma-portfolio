# Claude Fable 5 (Claude API, xhigh) — run outcome, 2026-09-05

Twelve released direct prompts (exact bytes verified against
`prompts/PROMPT_SHA256SUMS.txt`) sent to `claude-fable-5` with
`output_config.effort=xhigh`, no system prompt, no tools, no fallbacks, one
stateless request per prompt, in numerical order. No protocol deviation.

Result (released scorer, `score.json`): 26/60 exact optimal portfolios (43.3%),
331/480 target coverage (69.0%), 60/60 valid predictions, 12/12 responses were
single JSON objects, zero tool-use blocks, every stop reason `end_turn`.

Provider incident: call 10's first attempt ended after ~1m46s with a
mid-stream `overloaded_error` from the API before any answer text
(request_id req_011Cekmz3nheg9fDo4NbotwN). The harness of that moment treated
the HTTP-200 stream error as fatal and exited; the failed attempt is preserved
as the first `call: "10"` entry in `CALL_RECEIPTS.json`. The harness was revised
to classify stream-delivered overload/rate-limit errors as retryable, and the
run was resumed 1m54s later from call 10 (see `run_metadata.json` → `resumes`,
and the two harness copies under `harness/`). Calls 01–09 were not touched.
Sum of per-call wall time: 74.3 min. Total usage: 221,049 input tokens,
423,618 output tokens (thinking included), no cache reads.

Readiness probe (trivial prompt) excluded from the twelve benchmark calls.
