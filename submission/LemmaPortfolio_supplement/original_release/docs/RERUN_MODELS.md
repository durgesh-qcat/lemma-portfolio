# Running LemmaPortfolio on another model

If you only want to check the published numbers, no model call is needed: rerun
the offline scorer.  To test another deployment, use the preserved prompts and
keep its responses separate.  Providers may change a deployment without
changing its displayed name, so record the date and do not expect to reproduce
old output byte for byte.

## Checking the published scores

Run the commands in this guide from the `original_release/` directory.
The complete submission check, including follow-ups, is `python3 -B ../verify_all.py`.
To check only these original records, run:

```sh
python3 verify_release.py
```

The last line should be `ALL CHECKS PASSED`.  This command verifies the file
hashes, reconstructs every optimal portfolio, reparses the saved response
transcriptions, regenerates the two baselines, and checks every reported score.
It requires Python 3.10 or newer.  It does not require Lean, a model, an API
key, a paid service, or a third-party Python package.

## Before a new model run

Choose the deployment before opening `data/test.labels.jsonl`, `results/`, or
another model's answers.  Record the following information in a short metadata
file:

- the product or provider;
- the exact model label shown by the interface;
- the visible reasoning or thinking mode, or `NO SELECTOR`;
- the account tier, if known;
- local date, time, and timezone; and
- whether memory, browsing, search, tools, connectors, or file uploads were
  available.

Next, read [`prompts/START_HERE.txt`](../prompts/START_HERE.txt) in full and
check the prompt files:

```sh
cd prompts
shasum -a 256 -c PROMPT_SHA256SUMS.txt
cd ..
```

The labels are public in this archive because readers need them to check the
paper.  Avoiding them during a rerun is therefore only a procedural separation.
A new blind experiment would require another committed hidden test set held by
an independent custodian.

## Direct prompts

Choose a new output directory outside the checksummed submission archive.
Replace `/absolute/path/to/new-run/` below with that directory's actual path.

There are twelve direct prompt files.  For each one:

1. Open a new chat with no previous context.
2. Make sure browsing, tools, memory, connectors, and uploaded files are not
   available.
3. Paste the whole contents of `prompts/DIRECT_PROMPTS/01.txt` as the only user
   message.
4. Save the complete response, unchanged, under
   `/absolute/path/to/new-run/responses/`.
5. Repeat with `02.txt` through `12.txt`, in order, using a new chat each time.

Use a `.json` extension only when the complete response is valid JSON.  Use
`.txt` for prose, code fences, wrappers, refusals, or malformed output.  Do not
repair a response.  Do not retry merely because an answer looks wrong.  If the
provider fails before returning substantive output, preserve the error; make at
most one retry in a fresh chat and record it explicitly.

A valid direct response is one JSON object with a `predictions` field.  The
field maps each of the five episode IDs in the prompt to three candidate IDs:

```json
{
  "predictions": {
    "MLP4B_0000": ["C01", "C02", "C03"],
    "MLP4B_0001": ["C04", "C05", "C06"]
  }
}
```

This snippet shows the format only.  The real response must include all five
episodes in its prompt.

## Scoring the direct responses

Keep only raw response files in the `responses/` directory; place metadata and
score reports one level above it.  Then run:

```sh
python3 tools/score_predictions.py \
  --predictions /absolute/path/to/new-run/responses/* \
  --invalid-as-missing \
  --display-label "Exact visible model and mode" \
  --system-id my_model_run_01 \
  --output /absolute/path/to/new-run/score.json
```

The scorer combines responses by episode ID.  With
`--invalid-as-missing`, a whole file which is not parseable JSON is recorded
and skipped; its episodes receive zero in the fixed denominator of 60.  The
file itself is never changed.  A missing selection, duplicate candidate, wrong
budget, or candidate outside the pool also receives zero.  An unknown or
repeated episode ID remains an error, since it would make alignment ambiguous.

The score report includes the optimal-portfolio count, the valid response count,
total target coverage, mean normalized coverage, edge recall, and item-level
results with their prompt blocks.  One can check the command before a real run
with:

```sh
python3 tools/score_predictions.py \
  --predictions examples/predictions.example.json \
  --display-label "Example only"
```

## Occurrence-first prompts

The four files under `prompts/SOL_EXTRA_PROMPTS/` ask for an ordered candidate
list for every target. They implement the occurrence-first procedure: predict
target–candidate occurrences, then choose the best triple from that predicted
table. They are optional for a new direct row. If they are used, follow the
16-chat order and adjacency instructions in `prompts/START_HERE.txt`, and save
the four responses unchanged under
`/absolute/path/to/new-run/support_responses/`.

Score them with:

```sh
python3 tools/score_support_predictions.py \
  --supports /absolute/path/to/new-run/support_responses/* \
  --invalid-as-missing \
  --display-label "Exact visible model and mode" \
  --system-id my_model_run_01 \
  --output /absolute/path/to/new-run/support_score.json
```

This command truncates each predicted-occurrence list to its first two
candidates, solves
the induced three-candidate problem by exhaustive enumeration, and reports the
20-episode portfolio, coverage, and support-edge scores.  The strict alignment
and invalid-file rules are the same as for direct scoring.  The example file
`examples/support.example.json` can be used for a quick check.

The original intended protocol is preserved in
`provenance/manual_chat/MANUAL_CHAT_PROTOCOL.frozen.json`. The archived response
PDFs do not contain the logs, timestamps, or screenshots needed to show that it
was followed in full.  The protocol also names a different hash-selected
optional subset, whereas the archived occurrence-first responses cover D04,
D05, D06, and D12. `provenance/manual_chat/README.md` explains the difference.

## Keeping a new run

Preserve the raw response files, the metadata noted above, the scorer's JSON
output, and a SHA-256 manifest of the run directory.  Screenshots can be
useful when they do not expose private account information.  Do not overwrite
the published `responses/` or `results/` directories.  A new row should be
reviewed independently before it is added to a later paper or release, and its
label should describe the dated deployment which was actually observed.
