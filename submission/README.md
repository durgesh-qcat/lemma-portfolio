# Supporting materials

This directory contains the reproducibility materials for
[the technical write-up](../paper/LemmaPortfolio.pdf),
**LemmaPortfolio: Shared-Budget Lemma Selection for Multiple Lean Goals**.

[Download the ZIP](LemmaPortfolio_supplement.zip) or
[browse its contents](LemmaPortfolio_supplement/README.md).
The original PDF, ZIP, and all 309 unpacked files are preserved byte for byte.

From the repository root, run:

```sh
python3 -B verify_release.py
```

The verifier checks the file hashes, PDF/archive pairing, seven CLI/API
evaluations, six preliminary web response sets, target-wise diagnostics,
construction and greedy-tie checks, replacement analysis, masking sensitivity,
and the 780-answer selection-pattern audit. It includes the documented
[Python 3.10 compatibility adjustment](../docs/VERIFICATION.md).

The full repository also preserves detailed evaluation receipts and an
independent oracle check. The ZIP contains two original model-response PDFs;
the current write-up's technical notes are appended to its PDF.

Keep the original evidence intact and save later experiments separately.
After intentional repository edits, regenerate the root inventory with
`python3 -B tools/build_sha256s.py`, then rerun the complete verifier.
