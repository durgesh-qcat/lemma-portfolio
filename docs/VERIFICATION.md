# Verification and Python compatibility

Use `python3 -B verify_release.py` from the repository root. It verifies the
published hashes, exact final paper and ZIP, all 309 extracted supplementary
files, final results, oracle, original scores, and historical follow-up receipts.

For only the submitted scientific checks and paper pairing:

```sh
python3 -B tools/verify_submission.py --paper paper/LemmaPortfolio.pdf
```

## Why earlier GitHub checks are red

GitHub records each workflow run against the commit or tag it tested. Fixing a
later commit does not change the result of an earlier run. The README badge
tracks `main`; use the [main-branch workflow history](https://github.com/durgesh-qcat/lemma-portfolio/actions/workflows/verify.yml?query=branch%3Amain)
to check the current version. The workflow tests Python 3.10 and 3.12.

The historical failures have two documented causes:

| Earlier failure | Cause | Fix |
|---|---|---|
| [September 2, commit `632aaaa`](https://github.com/durgesh-qcat/lemma-portfolio/actions/runs/33665482646) | Generated score JSON differed by insignificant floating-point rounding across Python versions. | Commit `44e52b4` introduced structural comparison with a narrow float tolerance; the next run passed. |
| [September 11, commit `beaae69`](https://github.com/durgesh-qcat/lemma-portfolio/actions/runs/34602797639), also tested by the old `v4.0.0-submitted-20260907` tag | The archived verifier compared a saved integer percentage of `80` with a recomputed `79.99999999999999` exactly. | Commit `9f9af38` added the metric-specific compatibility wrapper described below. |

Both fixes retain exact counts, selections, and identifiers. The submitted PDF,
ZIP, and scientific records are unchanged. The superseding
[`v4.0.1-submitted-20260907` release check](https://github.com/durgesh-qcat/lemma-portfolio/actions/runs/34603216054)
passed on both Python versions. Old red entries describe those earlier versions,
rather than a failure of the current benchmark results.

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
