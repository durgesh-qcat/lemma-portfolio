# Manual-chat protocol provenance

`MANUAL_CHAT_PROTOCOL.frozen.json` preserves the intended pre-inference V3
core protocol. `MANUAL_CHAT_PROTOCOL_V3_SUPERSESSION_2026-09-01T100540Z.json`
records the pre-capture correction from V2 to V3.

These records must not be read as proof that the supplied consumer captures
completed every planned control. The response PDFs omit provider logs,
per-call timestamps, screenshots, account-tier evidence, and a complete
frozen-panel closure. The release therefore treats the visible responses as
externally supplied captures and makes only their alignment and scores fully
auditable.

There is also a specific structured-support distinction. The V3 protocol's
optional arm precommitted a hash-selected, scattered set of 20 episode IDs.
The supplied response captures instead contain four contiguous support blocks:
D04, D05, D06, and D12. The released `SOL_EXTRA_PROMPTS` reproduce those four
captured blocks. Their results are reported only as a descriptive pipeline
diagnostic, not as completion of the protocol's optional arm or as a causal
prompting experiment.

Project records state that the twelve released direct prompts are byte-identical
to the retained V3 direct packet. The retained prompt manifest itself is not in
this compact release, so that identity claim cannot be re-derived from this
repository alone. The supplied PDFs likewise do not independently authenticate
which exact prompt bytes or interface controls produced the historical
responses.
