# Rerunning LemmaPortfolio on another model

This guide separates two activities:

- **score reproduction**: deterministically recheck the numbers already in the
  paper; and
- **fresh inference**: present the released prompts to another model and score
  its new answers.

The first is deterministically reproducible (with a tiny tolerance only for
last-bit floating-point differences across Python/libm versions).  The second is not expected to recreate an
old consumer-chat output byte-for-byte because providers may change routing,
checkpoints, system prompts, and decoding without exposing those changes.

## A. Validate the paper results

From the repository root:

```sh
python3 verify_release.py
```

The last line must be `ALL CHECKS PASSED`.  This verifies the release hashes,
reconstructs every optimal portfolio, reparses the preserved response sources,
regenerates the deterministic baselines, and checks every reported score.  It
uses Python 3.10 or newer and no third-party package, model call, API key, Lean
installation, or paid service.

## B. Prepare a fresh model run

1. Choose the model or deployment before opening the test labels or existing
   result files.
2. Record:
   - product/provider;
   - exact visible model label;
   - exact visible reasoning or thinking mode, or `NO SELECTOR`;
   - account tier, or `unknown`;
   - local date/time and timezone; and
   - whether memory, browsing, search, tools, connectors, and file uploads are
     disabled.
3. Read `../prompts/START_HERE.txt` completely.
4. Verify the prompt bytes:

   ```sh
   cd prompts
   shasum -a 256 -c PROMPT_SHA256SUMS.txt
   cd ..
   ```

5. Do not inspect `data/test.labels.jsonl`, `results/`, or another model's
   answers until the complete raw run has been saved.

The released labels are necessarily public for auditability, so this separation
is procedural rather than cryptographic.  A genuinely new blind evaluation
requires a newly committed hidden split and an independent custodian.

## C. Run the twelve direct prompts

For every model:

1. Open a completely fresh chat.
2. Ensure browsing, tools, uploaded files, connectors, memory, and previous-chat
   context are unavailable.
3. Paste all of `prompts/DIRECT_PROMPTS/01.txt` as the only user message.
4. Save the complete raw response unchanged as `01.json`.  Preserve malformed
   responses, refusals, wrappers, and errors; never repair them silently.
5. Repeat in fresh chats for `02.txt` through `12.txt`, in numerical order.
6. Do not regenerate or retry because an answer appears mathematically wrong.
   If a provider error occurs before any substantive output, preserve it and
   record any retry explicitly.

Each valid direct response is one root JSON object with a `predictions` field
that maps five episode IDs directly to three-candidate arrays, for example:

```json
{
  "predictions": {
    "MLP4B_0000": ["C01", "C02", "C03"],
    "MLP4B_0001": ["C04", "C05", "C06"]
  }
}
```

The real prompt requires all five listed episodes.  The snippet above illustrates
the schema only and is not a benchmark answer.

## D. Optional structured-support diagnostic

The four files in `prompts/SOL_EXTRA_PROMPTS/` request ordered per-target
support lists.  They reproduce the diagnostic input format reported for the GPT
SOL rows; they are not required for an ordinary direct-score row.  Follow the
special 16-chat order and adjacency rules in `prompts/START_HERE.txt` when using
them.

`provenance/manual_chat/MANUAL_CHAT_PROTOCOL.frozen.json` records the original
pre-inference intended core protocol.  The final supplied consumer-response PDFs
do not contain provider logs, timestamps, screenshots, or complete closure
evidence.  Therefore, neither that protocol nor this repository proves that all
six reported convenience captures followed every intended operational control.

## E. Score the saved direct answers

Put the twelve JSON responses in one directory, then run:

```sh
python3 tools/score_predictions.py \
  --predictions scratch_runs/my_model/*.json \
  --display-label "Exact visible model and mode" \
  --system-id my_model_2026_09 \
  --output scratch_runs/my_model/score.json
```

The scorer merges the files by explicit episode ID.  It rejects unknown or
duplicated episode keys.  Missing, malformed, duplicate-candidate, wrong-budget,
or out-of-pool selections remain in the 60-item denominator and receive zero on
every metric, matching the paper's rule.

The output reports:

- exact optimal-portfolio accuracy;
- valid response count;
- total target coverage;
- mean normalized target coverage;
- selected-edge recall;
- item-level results and block membership.

To smoke-test the scorer before a real run:

```sh
python3 tools/score_predictions.py \
  --predictions examples/predictions.example.json \
  --display-label "Example only"
```

## F. Preserve and report a new run

Keep the following together:

- all raw response files exactly as received;
- a short metadata file containing the information from section B;
- screenshots only if they can be shared without exposing private account data;
- the scorer's JSON output; and
- a SHA-256 manifest of the run directory.

Do not overwrite the published `responses/` or `results/` directories.  New
results should be reviewed independently before they are added to the paper or
released as another version.  Report consumer labels as observed deployments,
not as stable or reproducible model checkpoints unless provider-side evidence
supports that stronger claim.
