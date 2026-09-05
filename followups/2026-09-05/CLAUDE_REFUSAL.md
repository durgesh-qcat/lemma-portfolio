# Claude Fable 5.1: preserved direct-API refusal outcome

This separate local capture was discovered during final results publication.
It is not a Codex run and was not covered by the Codex follow-up protocol.

Recorded configuration: Anthropic Messages API, requested model
`claude-fable-5-1`, `output_config.effort=xhigh`, `max_tokens=128000`, no system
prompt, no declared tools, no fallback, and one stateless request per released
prompt. Metadata and receipt prompt hashes match all 12 original direct prompts.

All 12 API responses report `stop_reason: refusal`, empty `content`, zero
output tokens, and the category `reasoning_extraction`. This is what the provider
reported; it is not an independent determination that the benchmark violates any
policy. No attempt is made in this export to modify prompts or bypass that refusal.

The empty answer files are preserved unchanged. Under the released strict
scorer, the capture has **0/60 exact, 0/480 covered targets, 0/60 valid answers,
and 12 invalid source files**. Report it as a refusal/availability outcome,
not as evidence of mathematical inability or a fair model-ranking observation.

Included: the original final-answer files, raw API response bodies, metadata,
call receipts, completion receipt, and score. No API key, `.env`, local harness
log, or diagnostic probe is included. No monetary billing claim is made.
The new snapshot verifier checks raw response hashes, refusal content, prompt
identity, and the strict zero score independently of the original Codex audit.

Other incomplete local Claude captures are excluded. This record is separate
from the numerical Codex summaries in `FOLLOWUP_RESULTS.json`.
