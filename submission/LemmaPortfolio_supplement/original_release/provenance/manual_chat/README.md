# Manual-chat protocol provenance

`MANUAL_CHAT_PROTOCOL.frozen.json` preserves the intended pre-inference V3
core protocol. `MANUAL_CHAT_PROTOCOL_V3_SUPERSESSION_2026-09-01T100540Z.json`
records the pre-capture correction from V2 to V3.

These records tell us what was planned. They do not show that every control was
followed for the archived responses. The archived response PDFs contain no provider logs,
per-call timestamps, screenshots, account-tier evidence, or complete panel
record. We can check their alignment and scores from the released files, but
not their serving conditions.

There is a separate issue with the occurrence-first responses. The optional arm in the
V3 protocol named a hash-selected, scattered set of 20 episode IDs. The
archived response PDFs instead contain four contiguous blocks: D04, D05, D06,
and D12. The released `SOL_EXTRA_PROMPTS` reproduce those four blocks. We use
their results only to compare the occurrence-first procedure with direct
prompting. They do not complete the optional arm, and we draw no causal
conclusion from them.

Project records state that the twelve released direct prompts have the same
bytes as the retained V3 packet. The original prompt manifest is not in this
compact archive, so that statement cannot be checked here alone. The PDFs also
do not identify the exact prompt bytes or interface controls which produced the
historical responses.
