# Exact submitted artifacts

This directory preserves the supplementary material paired with
[the final submitted PDF](../paper/LemmaPortfolio.pdf),
**LemmaPortfolio: Shared-Budget Lemma Selection for Multiple Lean Goals**,
submission 88.

[Download the submitted ZIP](LemmaPortfolio_supplement.zip) or
[browse its exact contents](LemmaPortfolio_supplement/README.md).
The ZIP is byte-identical to the author's supplied download
`88_LemmaPortfolio_Shared_Budge_Supplementary Material (1).zip`.
The paper is byte-identical to the supplied `final paper.pdf`.
Their hashes match the copies downloaded on September 7.
[SUBMITTED_ARTIFACTS.json](SUBMITTED_ARTIFACTS.json) records their identities.

From the repository root:

```sh
python3 -B verify_release.py
```

For the submitted supplement alone:

```sh
python3 -B tools/verify_submission.py \
  --paper paper/LemmaPortfolio.pdf
```

The wrapper runs all seven submitted checks and handles the documented
[Python 3.10 rounding-comparison defect](../docs/VERIFICATION.md). The archived
`verify_all.py` is preserved exactly, including that original limitation.

The extracted 309 files are unchanged from the submitted ZIP. They include the
seven later CLI/API evaluations, six preliminary web response sets, target-wise
diagnostics, evaluation harnesses, construction and greedy-tie checks,
one-target-short replacement analysis, all-thirteen-row masking sensitivity,
and the 780-answer selection-pattern audit. The full repository additionally
preserves richer historical inference receipts and an independent oracle check.

The ZIP contains two original model-response PDFs but no manuscript source.
The main paper's technical supplement is already appended to the final paper;
the older standalone supplement under `paper/historical/` is not the final one.

Keep the submitted snapshots immutable. Put future changes outside this folder
and preserve their separate provenance. To reconstruct this repository's current
manifest after authorized edits, use `python3 tools/build_sha256s.py`, then rerun
the complete verifier. That command does not rewrite the submitted ZIP or its
internal manifests.
