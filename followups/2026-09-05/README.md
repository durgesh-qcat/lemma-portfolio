# Final completed follow-up snapshot — 5 September 2026

The [final submitted paper](../../paper/LemmaPortfolio.pdf) now incorporates
these completed runs. See [submission/](../../submission/) for the exact submitted
archive and [RESULTS.md](../../RESULTS.md) for its result presentation. This
directory preserves the richer experimental export. [REPORT.md](REPORT.md) and
[PAPER_HANDOFF.md](PAPER_HANDOFF.md) are historical preparation records;
machine-readable comparisons, usage, and diagnostics are in
[FOLLOWUP_RESULTS.json](FOLLOWUP_RESULTS.json).

All retained runs are complete. This snapshot supersedes the earlier September 4
snapshot for current reporting, without overwriting it. It adds Astra max and the
second Sol/Astra xhigh pair. The third Codex runs were cancelled. Two completed
direct Anthropic API captures (Claude Fable 5 and Claude Fable 5.1, both at xhigh
effort) are included outside the Codex evaluation; see [CLAUDE_RUNS.md](CLAUDE_RUNS.md).
No OpenRouter result is included. Original consumer responses and results remain
unchanged. The preceding manuscript is preserved under
[paper/historical/2026-09-05/](../../paper/historical/2026-09-05/).

## Contents

| Phase directory | Exact score | Target coverage |
|---|---:|---:|
| `astra_xhigh_r1_prior/` | 27/60 | 328/480 |
| `astra_xhigh_r2/` | 30/60 | 332/480 |
| `sol_xhigh_r1/` | 20/60 | 302/480 |
| `sol_xhigh_r2/` | 15/60 | 300/480 |
| `astra_max_r1/` | 30/60 | 335/480 |
| `claude_fable_5_xhigh_r1/` (direct API) | 26/60 | 331/480 |
| `claude_fable_5_1_xhigh_ctx_r1/` (direct API, disclosed system prompt) | 26/60 | 335/480 |
| `astra_diagnostic/` direct | 8/20 | 106/160 |
| `astra_diagnostic/` structured q=2 | 4/20 | 100/160 |

Every direct run has 60/60 valid answers; both diagnostic arms have 20/20 valid.
Each phase contains byte-identical raw final `responses/`, `score.json` with
per-item results, frozen answer hashes, completion records, path-redacted run
metadata, per-call timing/usage receipts, and author-reported capture audits.
The two Claude phases come from a separate direct-API harness and carry raw API
response bodies, per-attempt receipts, harness source, and run notes instead of
Codex capture audits.

- `historical_q_sweep.json`: all q=1,2,3,4 historical support and tie analyses.
- `PROTOCOL_EXPORT.json`: the original plan with local paths removed.
- `USER_QUEUE_CHANGE.json`: author's request to retain the second pair but skip
  the third pair; the original protocol is not retrospectively rewritten.
- `WORKFLOW_OUTCOME.json`: completed shortened queue, with account details removed.
- `VALIDATION.json`: original local completion verification receipt.
- `EXPORT_MANIFEST.json`: source/export hashes and redaction disclosure.
- `BASE_RELEASE_SHA256SUMS.txt`: repository inventory immediately before this
  final addition, at commit `dacbef9e1fd59f1e5c30f9078a4f531a7fcf25fe`.
- `claude_fable_5_xhigh_r1/`, `claude_fable_5_1_xhigh_ctx_r1/`, `CLAUDE_RUNS.md`,
  and `CLAUDE_RESULTS.json`: completed direct Anthropic API captures scored with
  the released scorer, kept outside `FOLLOWUP_RESULTS.json` (which describes the
  Codex workflow). The Fable 5.1 phase used a published system prompt because the
  bare released prompt was refused by that model; see `CLAUDE_RUNS.md`.

## Offline verification

From the repository root, with Python 3.10+ and no additional packages:

```sh
python3 verify_release.py
python3 followups/2026-09-05/verify.py
```

The first command checks repository integrity and the release results.
The second reproduces every completed follow-up score and per-item row,
all four support widths and tie diagnostics, the recorded paired comparisons,
repeated-run means/sample standard deviations, and usage aggregates. It also
checks raw answer/prompt hashes, final queue disposition, the two Claude phases'
answer/prompt hashes, receipts, usage, scores, and cross-run comparisons, and
preservation of every file in the original baseline inventory, including its
README. The explicit [historical relocation map](../../provenance/PRE_SUBMISSION_FILES.json)
identifies exact copies of documentation, manuscript files, and tooling that were
updated for the final submission. The original inventory is unchanged; no hash
requirement is skipped. Original benchmark evidence is still checked in place.
Neither command calls a model or writes generated results into the repository.
Run the release verifier from a clean clone: local ignored `.env` or
`scratch_runs/` files are intentionally not part of the published manifest and
will make its strict whole-directory inventory check fail. Do not publish or
delete credentials to satisfy that check; use a clean clone for verification.

For a standalone direct-score export, for example:

```sh
python3 tools/score_predictions.py \
  --predictions followups/2026-09-05/astra_max_r1/responses/*.json \
  --invalid-as-missing \
  --system-id astra_max_r1 --display-label "astra max r1" \
  --output /tmp/lemma-astra-max-score.json
```

## Evidence boundary

These are post-release Codex follow-ups, not additions to the original frozen
consumer panel. The analyst knew the released labels; the evaluated processes
received only original prompts, not labels or earlier answers. Fresh processes,
empty working directories, disabled tools, and one turn per call were audited
locally. Serving weights, hidden routing, and numerical reasoning budgets are
not independently authenticated.

Raw final answers are unchanged. Full event streams, model catalogs, machine-local
execution files, account details, and the two initial Astra readiness probes remain
in the local archive. The operational audit receipts are therefore author-reported;
the exported verifier reproduces mathematics, not the omitted operational logs.
The probes are not included in benchmark scores, call counts, or inference timings.

The original unredacted follow-up protocol has SHA-256
`86a867af264a392f875a3a97474a74ec171acf7bfec79926aed9adb52df9c0fc`.
Its exported form intentionally has a different hash. The first Astra xhigh run
predates that protocol; it was not retroactively covered by the freeze.

Keep the named GitHub repository private during double-blind review. This is a
co-author results package, not a newly prepared anonymous submission artifact.
