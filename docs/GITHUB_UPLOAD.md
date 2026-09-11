# Maintaining the submitted GitHub version

The working repository is
[durgesh-qcat/lemma-portfolio](https://github.com/durgesh-qcat/lemma-portfolio).
It remains private during double-blind review. Collaborators use their own
GitHub accounts and work on branches; see [COLLABORATING.md](COLLABORATING.md).

## Verify a checkout

```sh
git clone https://github.com/durgesh-qcat/lemma-portfolio.git
cd lemma-portfolio
python3 -B verify_release.py
```

The verifier must end with `ALL CHECKS PASSED`. It checks the submitted PDF and
archive, consolidated results, original records, follow-ups, oracle and tests.
Run it from a clean checkout, keeping local credentials and new experimental
outputs outside the release inventory.

## Submitted-version artifacts

The submitted-version artifact identifier is `v4.0.0-submitted-20260907`.
The files defining this version are:

- `paper/LemmaPortfolio.pdf`: exact final submitted PDF, including its technical
  supplement;
- `submission/LemmaPortfolio_supplement.zip`: exact anonymous reproducibility
  ZIP submitted with that PDF;
- `submission/LemmaPortfolio_supplement/`: unchanged unpacked archive, including
  its own `MANIFEST.json`, `SHA256SUMS`, and `verify_all.py`;
- `RESULTS.md` and `results/paper_results.json`: final result mirrors; and
- `SHA256SUMS`: the repository inventory, covering the additional GitHub oracle
  benchmark and preserved historical receipts as well.

The unpacked supplement's `MANIFEST.json` identifies its accompanying PDF by
SHA-256. The root verifier checks that the ZIP and unpacked files agree. The
[paper README](../paper/README.md) records source availability: the archived
editable source and older PDFs are historical, and no verified final Overleaf
source package is currently available.

Commit reviewed changes and verification results to a branch, then open a pull
request. Preserve the final submitted files and use a new version for later
scientific changes. A release of this submitted version should attach the exact
PDF and supplement ZIP, with their checksums, to the verified commit.

## Construction data and eventual public release

The pinned Parquet construction inputs are separately inventoried in
`provenance/generation_receipt.json`. They are not needed for any offline score
check; [construction/README.md](../construction/README.md) explains the additional
mining requirements. Keep large source archives out of ordinary Git history.

When the venue permits public release, the owner can publish the verified
version and its artifacts and add the permanent URL to the camera-ready paper.
The current private update does not require changing repository visibility.
