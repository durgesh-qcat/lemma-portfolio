# Provenance and reproducibility

## What is preserved

The public episodes, proof-use labels, released prompts, original response PDFs
and transcriptions, and all 92 follow-up final-answer files retain their original
bytes. The 92 files contain 84 five-episode direct answers from seven complete
runs, plus eight direct/target-wise files for the Astra diagnostic. The manifest
maps each follow-up answer to its prompt and episode IDs and records its hash.
The added Fable 5.1 system prompt is preserved separately from the unchanged
user prompts.

The original scoring and construction implementations are retained. Packaging
changes concern documentation, inventories, and verification entry points:
the verifier no longer depends on manuscript drafts. `preserved_original_files`
in `MANIFEST.json` lists only files whose bytes really were retained unchanged.
All current files are covered by `SHA256SUMS`.

The all-panel masking sensitivity is derived from the same saved answers and
the preserved source-name-prefix audit. The six test IDs are excluded on the
basis of that audit, not model outcomes. `verify_masking_sensitivity.py` records
input hashes and reproduces the original six sensitivity rows before extending
the calculation to the seven follow-up runs. This adds no inference calls and
does not alter the main 60-episode scores.

## Original and follow-up evaluations

The original six response sets were collected through chat/web interfaces.
Their source PDFs and parsing/alignment records are under `original_release/`.
The PDFs alone do not establish hidden system prompts, serving checkpoints or
independent execution timestamps. The preserved protocol and the observed
response order are distinguished in `original_release/docs/PROVENANCE.md`.
Missing and malformed answers are not repaired.

Astra and Sol follow-ups used Codex CLI 0.153.0; Fable used the Anthropic Messages
API. The retained execution records describe fresh, tool-free calls using the
released five-episode prompts. `evaluation/` supplies the available settings,
receipts, protocols and Fable calling code, and identifies missing records.
These are execution records, not independent attestations of a provider's hidden
weights. No new inference calls were made to prepare or verify this submission.

The first Astra xhigh run preceded the follow-up protocol freeze. The evaluator
had seen the public test labels, but the records state that these were withheld
from evaluated processes. Planned third xhigh runs were cancelled after scores
from the completed runs were known. Both completed repetitions for each model
are retained; no best-of-two selection is used.

Fable 5.1 used an additional benchmark-context system prompt after bare-prompt
refusals. The context-conditioned run is reported separately; refusals are not
merged into its answers. Available refusal diagnostics and the extent of the
missing bare-prompt records are documented in `evaluation/`. The Fable 5 run
also had an operational overload retry; this was not a mathematical-answer
repair. The recorded interfaces and effort labels do not imply matched compute.

## Target-wise and retrospective analyses

The original target-wise response blocks differ from the optional hash-selected
arm named in the original protocol. They cover D04, D05, D06 and D12, and are
an exploratory paired comparison. Pro has 15 complete pairs; original Sol xhigh
has 20. The Astra diagnostic covers the same four blocks in separate fresh
sessions, alternating direct-first and target-wise-first order across blocks.

For target-wise selection, the first two predictions for each target are kept.
All 560 three-candidate portfolios are evaluated against these predicted uses,
with candidate-ID order resolving ties. True proof-use labels are used only
after selection. Other prediction widths and uniform-tie expectations are
offline diagnostics, not additional model runs or observed improvements.

Construction-tie and candidate-replacement analyses use true labels
retrospectively. They neither test a model repair procedure nor establish
prover success. Repeated responses concern the same 60 episodes; pooled response
counts are not independent samples of mathematical problems.

The selection-pattern audit is a post-hoc analysis of all 780 saved answer slots.
It compares valid portfolios with hidden-frequency and marginal-coverage greedy
selectors under fixed and unrestricted ties, and with better portfolios having
the same multiset of individual occurrence counts. Invalid answers are excluded
from these pattern comparisons but retained as failures in exact-rate intervals.
The audit also enumerates all frequency-maximizing triples independently of model
success. It finds an optimum in those sets on 53/60 episodes, with 6.8 tied
triples per episode on average. Its error partition distinguishes departures
from these sets from suboptimal selections inside them, including the seven
episodes where frequency maximization cannot attain optimal coverage. These
labels describe portfolios, not measured usage-estimation or overlap errors.
The accompanying nominal Wilson intervals use 60 episodes per run, not pooled
repeats. These calculations add no model calls and identify neither internal
reasoning strategies nor the success of a repair procedure. The preserved
responses, construction decisions, and historical scores remain unchanged.

## Source and authorship records

Mathlib version, construction settings, data commitments and original scientific
protocols remain available. The exact data are public and local-ID masking is
not complete; details and the corresponding sensitivity checks are in
`REPRODUCIBILITY.md`.

No manuscript drafts or revision logs are included. Frozen scientific protocols
retain their original assistance declarations; these are provenance records,
not records of manuscript edits. Human authorship and responsibility do not
assert that no tools assisted the work.
