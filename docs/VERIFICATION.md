# Verification and Python compatibility

Use `python3 -B verify_release.py` from the repository root. It verifies the
published hashes, exact final paper and ZIP, all 309 extracted supplementary
files, final results, oracle, original scores, and historical follow-up receipts.

For only the submitted scientific checks and paper pairing:

```sh
python3 -B tools/verify_submission.py --paper paper/LemmaPortfolio.pdf
```

## Archived Python 3.10 rounding comparison

The exact submitted supplement's `verify_followups.py` applies its existing
`1e-10` tolerance when an expected JSON value is a float, but compares integer
JSON values exactly. The saved normalized-coverage percentage for Sol xhigh run
2 is the integer `80`; Python 3.10 can recompute it as
`79.99999999999999`. Its score is unchanged, but the original comparison fails.
This was observed in the first GitHub CI run of the synchronized repository.

`tools/verify_submission.py` runs the same seven submitted checks. It applies
an in-memory comparison adapter only to the continuous
`mean_oracle_normalized_coverage_percentage` metric when the archived value is
an integer and the recomputed value is a float. The adapter uses the archived
numeric tolerance. Counts, episode IDs, selections, keys, and invalid-answer
flags retain exact comparison; booleans cannot substitute for numeric values.
Regression tests cover the rounding case, substantive metric changes, and
near-integer count errors.

The adapter does not edit, regenerate, or repair any submitted file, response,
label, score, or hash. The exact archived `verify_all.py` remains available for
historical reproduction, with this limitation documented. The repository
wrapper is the portable entry point for Python 3.10 and later.
