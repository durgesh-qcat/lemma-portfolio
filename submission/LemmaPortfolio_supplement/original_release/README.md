# Original benchmark and response evidence

This directory contains the 30 development and 60 test episodes, construction
code, released prompts, original six model response sets, and scoring tools.
For the complete submission, including the seven follow-up runs, start with
`../README.md`. The full construction settings and diagnostics are in
`../REPRODUCIBILITY.md`; there are no manuscript drafts in this archive.

With Python 3.10 or newer, run from this directory:

```sh
python3 -B verify_release.py
```

This checks the inventory, prompt-to-episode correspondence, parser and scorer
tests, and construction tests. It regenerates the transcriptions, baselines,
scores, and post-hoc mathematical diagnostics in temporary directories and
compares them with the saved results. It needs no Lean installation, third-party
Python package, API key, or model call. Counts and selections must match exactly;
only negligible floating-point differences are allowed.

- `data/`: public statements and released proof-use labels.
- `prompts/`: twelve direct and four target-wise prompts, their hashes, and
  fresh-chat and response-format instructions in `START_HERE.txt`.
- `responses/`: original model-answer PDFs, extracted text, transcriptions,
  and episode-alignment records. These PDFs are response evidence, not papers.
- `results/`: original scores, baselines, paired comparisons and tie diagnostics.
- `provenance/`: dataset commitment, construction receipt, Lean checks and
  frozen evaluation protocol.
- `development_evidence/`: the saved 15-episode development check.
- `construction/`: builder, Lean audit wrapper, requirements and tests.
- `tools/`: scorers for saved and new responses.
- `docs/`: data description, original response provenance and rerun instructions.

To evaluate new responses, follow `docs/RERUN_MODELS.md` and keep the new outputs
outside this checksummed archive. Missing or malformed answers receive zero;
unknown or duplicate episode IDs are errors because alignment is ambiguous.
The labels here are public evaluation data and must not be passed to a model.
New responses may differ from the saved ones as deployments and sampling change.

The external 256 Parquet shards are needed only to rerun mining, not to reproduce
the reported scores. Their names, sizes and hashes are in
`provenance/generation_receipt.json`. See `construction/README.md` for source and
Lean requirements. Licenses and Mathlib attribution are in `LICENSES.md` and
`NOTICE`.
