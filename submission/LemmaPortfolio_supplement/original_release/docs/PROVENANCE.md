# Response files and alignment

The six response-set rows were transcribed from two source PDFs preserved in
`responses/`:

- `responses/source_responses.pdf` contains five rows.  Its SHA-256 is
  `2f20fbc4b3eb3b87c4b693058fc5744a947de04e19a2eca70f0ea5c0d54dde3f`.
  The extracted text has SHA-256
  `3cd354ccb7f8533e3709a11a785748c7d09735b41f6f97930a4247d17a8f3c40`.
- `responses/sol_xhigh_source_responses.pdf` contains the xhigh row.  Its
  SHA-256 is
  `02abb92d1e3fd6d59dca5faa191a7fec214dffae7c4f023ce5cbb5d02b517afa`.
  The extracted text has SHA-256
  `ac3bfc8cac5db47000f5d42b29fb798fcbb4dd8184a4f6bf2b3e6190f7555ca3`.

Ghostscript 10.03.0 reproduces the two text files with:

```sh
gs -q -dNOPAUSE -dBATCH -sDEVICE=txtwrite \
  -sOutputFile=/tmp/source_extracted.txt responses/source_responses.pdf
gs -q -dNOPAUSE -dBATCH -sDEVICE=txtwrite \
  -sOutputFile=/tmp/sol_xhigh_extracted.txt responses/sol_xhigh_source_responses.pdf
```

## Post-hoc name-prefix scan

The construction receipts preserve the original exact-token name check. In the
test split, a later, broader prefix scan found 33 source-name-prefix occurrences
in 25 source-name/statement pairs involving 24 source declarations across 6/60
episodes. In development it found 5 occurrences in 5 pairs involving 5 source
declarations across 2/30 episodes. The strings occur inside generated or dotted
identifiers. They do not themselves print the occurrence table, but they make
exact source-declaration recovery easier. The frozen public files and scores
were not retrospectively changed.

Responses are matched by the episode ID written in the response, not by their
page position.  Direct block D01 covers `MLP4B_0000` through `MLP4B_0004`, D02
covers `0005` through `0009`, and so on, ending with D12 (`0055` through
`0059`).

The observed orders are as follows:

- GPT SOL gives D01 through D11, followed by a second D11; D12 is absent.  We
  retain the first D11.  The two D11 copies differ only on `MLP4B_0053`, and
  that difference leaves all reported scores unchanged.
- DeepSeek Instant gives D01 through D12.
- DeepSeek Expert gives D01 through D12.
- Qwen 3.8 Max gives
  D01,D03,D02,D04,D06,D05,D08,D07,D09,D10,D12,D11.  Its D12 response lacks
  the outer opening brace and is invalid under the stated no-repair rule.
- Qwen 3.7 Plus gives
  D02,D01,D03,D04,D08,D07,D10,D09,D05,D06,D12,D11.
- The separate GPT SOL 5.6 xhigh PDF gives D01 through D12, with no missing,
  repeated, or malformed direct block.

A missing or malformed whole block leaves five zeroes in the 60-episode
denominator.  For this reason the reported Qwen 3.8 score is 12/60.  Inserting
the missing brace would make it 15/60, but that repaired number is not used.

According to `../provenance/dataset_commitment.json`, the public-test hash and
label digest were recorded on 1 September 2026 before the responses were
collected.  The PDFs have no independent timestamps or provider logs, so this
ordering cannot be verified from the captures alone.  The released files do
allow the response alignment and every reported score to be checked.  They do
not identify the serving checkpoint or confirm how the chats were run.

The intended V3 protocol is preserved in `../provenance/manual_chat/`.  Its
optional arm named a hash-selected set of 20 episodes.  The archived response
PDFs instead contain the contiguous blocks D04, D05, D06, and D12.  We use
these four blocks only to compare the occurrence-first procedure with direct prompting.
They do not complete the optional protocol, and we draw no causal conclusion
from them.
