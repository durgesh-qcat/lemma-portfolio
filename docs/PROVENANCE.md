# Provenance of the final submitted paper and evaluations

The definitive paper is [LemmaPortfolio.pdf](../paper/LemmaPortfolio.pdf),
submitted on 7 September 2026 as *LemmaPortfolio: Shared-Budget Lemma Selection
for Multiple Lean Goals*. The [exact submitted ZIP](../submission/LemmaPortfolio_supplement.zip)
and [unchanged unpacked supplement](../submission/LemmaPortfolio_supplement/README.md)
preserve the final supporting evidence. Its `MANIFEST.json` records the paired
PDF hash and every follow-up answer/prompt association. Root result mirrors
are `RESULTS.md` and `results/paper_results.json`.

The final editable source has not yet been recovered. Earlier paper PDFs and
LaTeX source are under `paper/historical/2026-09-05/`; they do not reproduce the
final PDF. See [paper provenance](../paper/README.md). No new model calls were
made to assemble or verify the submitted packet.

## Seven CLI/API runs in the main paper

The paper incorporates all seven retained follow-up runs: two Astra xhigh, two
Sol xhigh, one Astra max, and the Fable 5 and context-conditioned Fable 5.1 runs.
Each has 60 valid answers. The submitted supplement preserves 92 final-answer
files: 84 five-episode answers across the seven runs and eight files for the
separate Astra direct/target-wise diagnostic. The richer original GitHub
receipts remain under [followups/2026-09-05/](../followups/2026-09-05/README.md).

Astra and Sol used Codex CLI 0.153.0 with recorded fresh sessions and no tools.
The first Astra xhigh run preceded the follow-up protocol freeze. The evaluator
had seen the public labels, but the records state they were withheld from the
evaluated processes. Planned third xhigh runs were cancelled after completed
scores were known. Both completed repetitions are reported separately; their
120 answers per model concern the same 60 episodes.

Fable used a separate Anthropic Messages API harness. Fable 5.1 received a
disclosed benchmark-context system prompt after bare-prompt refusals; the
released user-message bytes remained unchanged. The refused attempts are not
merged into the scored context-conditioned row. Fable 5 had an operational
overload retry, which was not a mathematical-answer repair. Available refusal
diagnostics and missing bare-prompt records are identified in the
[evaluation records](../submission/LemmaPortfolio_supplement/evaluation/README.md).

The submitted evaluation inventory supplies available settings, receipts and
Fable calling code. Exact historical CLI runner/invocation files were absent
from the supplied export; their recorded hashes do not supply the missing code.
The richer GitHub capture audits likewise summarize omitted full event streams.
Neither these records nor visible model/effort labels authenticate hidden
serving weights or establish matched compute.

## Six preliminary web-interface response sets

The original six rows remain in the final technical supplement. Their data,
answers, alignment rules and scores are preserved below.

The score sources for the six consumer rows are:

- `responses/source_responses.pdf`, containing five rows (SHA-256
  `2f20fbc4b3eb3b87c4b693058fc5744a947de04e19a2eca70f0ea5c0d54dde3f`),
  with extracted-text SHA-256
  `3cd354ccb7f8533e3709a11a785748c7d09735b41f6f97930a4247d17a8f3c40`;
- `responses/sol_xhigh_source_responses.pdf`, containing the separate xhigh row
  (SHA-256
  `02abb92d1e3fd6d59dca5faa191a7fec214dffae7c4f023ce5cbb5d02b517afa`),
  with extracted-text SHA-256
  `ac3bfc8cac5db47000f5d42b29fb798fcbb4dd8184a4f6bf2b3e6190f7555ca3`.

Ghostscript 10.03.0 reproduces both extracted files byte-for-byte:

```sh
gs -q -dNOPAUSE -dBATCH -sDEVICE=txtwrite \
  -sOutputFile=/tmp/source_extracted.txt responses/source_responses.pdf
gs -q -dNOPAUSE -dBATCH -sDEVICE=txtwrite \
  -sOutputFile=/tmp/sol_xhigh_extracted.txt responses/sol_xhigh_source_responses.pdf
```

The response order is recovered from explicit episode IDs, never inferred from
page position.  Direct block D01 covers `MLP4B_0000`--`MLP4B_0004`, D02 covers
`0005`--`0009`, and so on through D12=`0055`--`0059`.

Observed direct-block orders:

- GPT SOL: D01--D11, followed by a second D11; D12 is absent.  The first D11 is
  canonical.  The sole changed episode in the alternative has identical exact,
  coverage, normalized-coverage, and edge-recall scores.
- DeepSeek Instant: D01--D12.
- DeepSeek Expert: D01--D12.
- Qwen 3.8 Max: D01,D03,D02,D04,D06,D05,D08,D07,D09,D10,D12,D11.  D12 lacks
  the outer opening brace and is invalid under the strict no-repair rule.
- Qwen 3.7 Plus: D02,D01,D03,D04,D08,D07,D10,D09,D05,D06,D12,D11.
- GPT SOL 5.6 xhigh (separate PDF): D01--D12, with no missing, duplicate, or
  malformed direct block.

Missing or malformed whole blocks remain five zeroes in the 60-item denominator.
The strict Qwen 3.8 score is 12/60.  Silently adding the missing brace would make
it 15/60, but that repaired number is not reported.

The public test file and label digest were recorded before the captured
responses.  The source documents do not include provider-side
logs, per-call timestamps, account-tier evidence, deployment screenshots, or a
complete frozen-panel closure.  We therefore report externally captured visible
consumer labels, not reproducible checkpoints or a cryptographically escrowed
evaluation.

The intended V3 protocol and its scope note are retained under
`provenance/manual_chat/`.  In particular, the supplied structured-support
blocks D04, D05, D06, and D12 differ from the protocol's earlier optional-arm
subset.  They are therefore treated only as a descriptive diagnostic, never as
completion of that precommitted optional arm.

## Target-wise and retrospective analyses

The original target-wise blocks are a descriptive diagnostic rather than the
optional subset in the frozen protocol. Pro has 15 complete direct/target-wise
pairs (4 versus 1 optima); original Sol xhigh has 20 (1 versus 0). Their original
fixed-20-ID outputs remain preserved, including zeroes for missing direct Pro
answers. The fresh Astra diagnostic has 20 complete pairs (8 versus 4), with
alternating direct-first and target-wise-first order across the four blocks.

The primary target-wise pipeline keeps the first two predictions per target,
then optimizes over all 560 triples with candidate-ID tie breaking. True labels
are used only for scoring. Width sweeps and predicted-tie expectations are
rescoring of saved predictions, not additional inference runs.

The final packet also contains all-panel masking sensitivity, selection-pattern
and frequency-tie audits, nominal per-run Wilson intervals, and replacement
analyses. They use released labels retrospectively. The six masking exclusions
come from the preserved source-name-prefix audit, not model outcomes. Frequency
and greedy matches describe selected portfolios; they do not recover internal
reasoning strategies. Replacement neighbors are mathematical possibilities, not
observed repairs. Repeated response counts do not add independent test episodes.
See the submitted [provenance record](../submission/LemmaPortfolio_supplement/PROVENANCE.md)
and [reproducibility specification](../submission/LemmaPortfolio_supplement/REPRODUCIBILITY.md)
for definitions, input hashes and interpretation limits.

The additional GitHub [oracle benchmark](../oracle/README.md) recomputes the
exhaustive ceiling and label-informed diagnostics from the unchanged benchmark.
It is outside the exact submitted ZIP and introduces no model inference.
