# Rerunning LemmaPortfolio on another model

This guide accompanies the final 7 September 2026 submission,
*LemmaPortfolio: Shared-Budget Lemma Selection for Multiple Lean Goals*.
[RESULTS.md](../RESULTS.md) consolidates all thirteen saved direct-response
sets; the main paper reports seven CLI/API runs and the technical supplement
retains the six preliminary web-interface sets.

This guide separates two activities:

- **score reproduction**: deterministically recheck the numbers already in the
  paper; and
- **fresh inference**: present the released prompts to another model and score
  its new answers.

The first is deterministically reproducible (with a tiny tolerance only for
last-bit floating-point differences across Python/libm versions). The second
need not recreate an old consumer-chat output byte-for-byte because providers
may change routing,
checkpoints, system prompts, and decoding without exposing those changes.

## A. Validate the paper results

From the repository root:

```sh
python3 -B verify_release.py
```

The last line must be `ALL CHECKS PASSED`.  This verifies the release hashes,
reconstructs every optimal portfolio, reparses the preserved response sources,
regenerates the baselines, and checks every reported score. It also verifies
the exact submitted PDF/ZIP, all thirteen rows and final analyses, the oracle
benchmark, and parser/scorer/construction tests. It uses Python 3.10 or newer and no third-party package, model call, API key, Lean
installation, or paid service.

The submitted [evaluation records](../submission/LemmaPortfolio_supplement/evaluation/README.md)
list the actual CLI/API settings, available calling code, Fable 5.1 context
prompt and missing historical records. The original web-chat procedure below
is a reusable capture protocol, not a reconstruction of every historical
CLI/API invocation.

## B. Prepare a fresh model run

1. Choose the model or deployment before opening the test labels or existing
   result files.
2. Record:
   - product/provider;
   - exact visible model label;
   - exact visible reasoning or thinking mode, or `NO SELECTOR`;
   - API/CLI version and invocation, if applicable;
   - every system/developer prompt, including harness-supplied instructions;
   - account tier, or `unknown`;
   - local date/time and timezone; and
   - whether memory, browsing, search, tools, connectors, and file uploads are
     disabled.
3. Read [`prompts/START_HERE.txt`](../prompts/START_HERE.txt) completely.
4. Verify the prompt bytes:

   ```sh
   cd prompts
   shasum -a 256 -c PROMPT_SHA256SUMS.txt
   cd ..
   ```

5. Do not inspect `data/test.labels.jsonl`, `results/`, or another model's
   answers until the complete raw run has been saved.

For a CLI/API run, save the exact invocation and available execution logs, use
a fresh process or stateless request for each prompt, and disclose all additional
context. Preserve provider errors/refusals and predeclare retry handling. If
context or settings change after a refusal, report the changed condition as a
separate run and retain the original attempts. The Fable 5.1 submitted row is
explicitly context-conditioned; it does not claim success under a bare prompt.

The released labels are necessarily public for auditability, so this separation
is procedural rather than cryptographic. A new blind evaluation
requires a newly committed hidden split and an independent custodian.

## C. Run the twelve direct prompts

For every model:

1. Open a completely fresh chat.
2. Ensure browsing, tools, uploaded files, connectors, memory, and previous-chat
   context are unavailable.
3. Paste all of `prompts/DIRECT_PROMPTS/01.txt` as the only user message.
4. Save the complete raw response unchanged under
   `scratch_runs/my_model/responses/`. Use `01.json` only when the entire
   response is a valid JSON object; otherwise use `01.txt`. Preserve malformed
   responses, refusals, code fences, wrappers, and errors; never repair them.
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
The protocol's earlier optional arm named a different hash-selected 20-item
subset; the supplied D04/D05/D06/D12 support blocks are reported only as a
descriptive diagnostic. See `provenance/manual_chat/README.md`.

Save these four raw outputs unchanged under
`scratch_runs/my_model/support_responses/`, again using `.json` only when the
entire response is valid JSON. Score the fixed 20-episode `q=2` pipeline with:

```sh
python3 tools/score_support_predictions.py \
  --supports scratch_runs/my_model/support_responses/* \
  --invalid-as-missing \
  --display-label "Exact visible model and mode" \
  --system-id my_model_2026_09 \
  --output scratch_runs/my_model/support_score.json
```

This reproduces the prompt-defined support subset, truncation to two candidates
per target, lexicographically tie-broken exhaustive optimizer, 20-item exact
and coverage scores, and full/truncated support-edge metrics. For comparisons
with direct selection, report the common paired IDs and denominator separately;
the final paper uses 15 complete original Pro pairs and 20 pairs for original
Sol and the separate Astra diagnostic. The same strict alignment and explicit
invalid-file rules as the direct scorer apply. Smoke-test
it with `examples/support.example.json` if desired.

## E. Score the saved direct answers

Put only response files in the dedicated `responses/` directory; keep metadata
and score reports one level above it. Then run:

```sh
python3 tools/score_predictions.py \
  --predictions scratch_runs/my_model/responses/* \
  --invalid-as-missing \
  --display-label "Exact visible model and mode" \
  --system-id my_model_2026_09 \
  --output scratch_runs/my_model/score.json
```

The scorer merges valid JSON files by explicit episode ID. The opt-in
`--invalid-as-missing` mode records and skips whole files that are unreadable,
prose, code-fenced, or otherwise not parseable JSON; it does not alter them.
Their absent episodes remain zero in the 60-item denominator. Missing or
malformed selections, duplicate-candidate selections, wrong-budget selections,
and out-of-pool selections also receive zero. Unknown or duplicated episode IDs
remain hard errors because accepting them would make the alignment ambiguous.

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

Do not overwrite published `responses/`, `results/`, or `submission/` files. New
results should be reviewed independently before they are added to the paper or
released as another version.  Report consumer labels as observed deployments,
not as stable or reproducible model checkpoints unless provider-side evidence
supports that stronger claim.

The submitted ZIP and its unpacked contents are an immutable snapshot. Keep new
model calls and analysis outputs outside that snapshot, and record a new version
before incorporating them into a later paper. Follow the
[collaboration guide](COLLABORATING.md) for reviewing repository additions.
