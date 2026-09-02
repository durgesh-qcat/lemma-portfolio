# Response provenance and alignment

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
