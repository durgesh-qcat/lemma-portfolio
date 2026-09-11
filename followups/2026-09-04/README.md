# Completed follow-up snapshot — 4 September 2026 (Pacific)

This is an earlier workflow snapshot. The completed export is
[2026-09-05](../2026-09-05/README.md), and the
[final submitted paper](../../paper/LemmaPortfolio.pdf) incorporates those results.
Pending-run statements below describe the time of this historical export.

This versioned addition is separate from the original frozen V4 consumer panel.
It contains one complete Astra xhigh run, one complete matched Sol xhigh run,
and a fresh Astra direct-versus-structured diagnostic. All raw final answers
are copied byte-for-byte from completed, frozen local capture archives.
See [REPORT.md](REPORT.md) for results, limitations, and implications for writing.

## Included evidence

- `astra_xhigh_r1_prior/`: 12 direct response blocks, 27/60 exact, 328/480 coverage.
- `sol_xhigh_r1/`: 12 direct response blocks, 20/60 exact, 302/480 coverage.
- `astra_diagnostic/`: eight calls on D04, D05, D06, D12; fresh direct 8/20
  versus structured `q=2` 4/20. These 20-item conditions are not full repetitions.
- `historical_q_sweep.json` and `HISTORICAL_Q_SWEEP.md`: exploratory re-scoring
  of both original GPT support captures at all four prefix widths.
- `FOLLOWUP_RESULTS.json`: summaries, per-block comparisons, usage, and diagnostic.
- `PROTOCOL_EXPORT.json`: frozen follow-up plan with absolute local paths redacted.
  `EXPORT_MANIFEST.json` records its original SHA-256 and export transformations.
- Each phase includes raw `responses/`, per-item `score.json`, the original
  `OUTPUTS_FROZEN.json` and `RUN_COMPLETED.json`, path-redacted run metadata,
  `CALL_RECEIPTS.json`, and an author-reported `capture_audit.json`.

The original protocol hash is
`86a867af264a392f875a3a97474a74ec171acf7bfec79926aed9adb52df9c0fc`.
The unredacted protocol remains in the local capture archive; the exported
version intentionally has a different hash. Source and export hashes are
recorded separately. The original Astra run predates this follow-up protocol;
it was not rerun or retroactively covered by that freeze.

## Reproduce without inference

From the repository root, using Python 3.10 or newer and the standard library:

```sh
python3 verify_release.py
python3 followups/2026-09-04/verify.py
```

The first command checks repository file integrity and original V4 scores. The
second checks frozen answer hashes and prompt hashes, independently re-scores
all exported answers with the existing scorers, reproduces all four support
widths and tie diagnostics, and checks the paired block comparisons and usage
aggregates. It creates no files and invokes no models. `analysis.py` preserves
the original offline comparison and support-sweep functions with portable imports.

The direct scorer can also be used independently, for example:

```sh
python3 tools/score_predictions.py \
  --predictions followups/2026-09-04/sol_xhigh_r1/responses/*.json \
  --invalid-as-missing \
  --system-id sol_xhigh_r1 --display-label "sol xhigh r1" \
  --output /tmp/lemma-sol-followup-score.json
```

## Evidence boundaries and pending work

The analyst had already seen released labels; evaluated processes received only
the original prompts, not labels or earlier answers. These are not new blind
consumer rows. Model identifiers, effort settings, and CLI version are recorded,
but serving weights, hidden routing, and numerical reasoning budgets cannot be
independently authenticated. There is one complete run per xhigh model here;
the block-bootstrap intervals do not estimate run-to-run variability.

Operational audit receipts report fresh sessions, one turn per call, exact prompt
matching, and zero observed tools. Full event streams, model catalogs, local
execution files, and account information are **not** uploaded. Thus independent
readers can reproduce the mathematical results but cannot replay the full
operational audit from this export alone. Raw archives remain local. Two initial
Astra readiness probes (one older-CLI rejection, one app-CLI success) are retained
locally and excluded from the 12 benchmark calls, scores, and timings.

At export, Astra max was running and the four optional repeat runs were pending.
No incomplete answers or partial scores are included; future completed results
require an explicit new snapshot/update. This directory is not a live dashboard.

Original data, prompts, response captures, and numerical results remain unchanged.
`BASE_RELEASE_SHA256SUMS.txt` preserves the previous inventory at commit
`1503aa03bc6fb4e9c27890eae46141137496eea0`. The verifier checks every original
hash, including the historical README. The
[relocation map](../../provenance/PRE_SUBMISSION_FILES.json) binds the original
documentation and tooling to exact archived copies; the preceding manuscript
is under [paper/historical/2026-09-05/](../../paper/historical/2026-09-05/).
The submitted paper has integrated the completed follow-up results.
Keep the named repository private during double-blind review; this export is not
an independently prepared anonymous review artifact.
