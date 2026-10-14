# Maintaining the benchmark repository

The public repository is
[durgesh-qcat/lemma-portfolio](https://github.com/durgesh-qcat/lemma-portfolio).
Contributors can work on branches and open pull requests; see the
[collaboration guide](COLLABORATING.md).

## Verify a checkout

```sh
git clone https://github.com/durgesh-qcat/lemma-portfolio.git
cd lemma-portfolio
python3 -B verify_release.py
```

The verifier must end with `ALL CHECKS PASSED`. It checks the write-up PDF,
supporting archive, consolidated results, original records, follow-ups,
oracle, and tests. Keep credentials and new experimental outputs outside
the release inventory.

## Artifact maintenance

The [technical write-up](../paper/README.md),
[supporting materials](../submission/README.md), and
[result files](../results/README.md) describe the current benchmark.
`SHA256SUMS` inventories the repository files. The verifier checks that the
supporting ZIP agrees with its unpacked contents and recorded PDF hash.

Preserve raw responses and original evidence. Use a new version for scientific
changes and document the inputs and protocol for new experiments. After
intentional documentation edits, regenerate the root manifest and verify:

```sh
python3 -B tools/build_sha256s.py
python3 -B verify_release.py
```

## Construction inputs

The pinned Parquet inputs are inventoried in `provenance/generation_receipt.json`.
They are not needed for offline score checks. The
[construction guide](../construction/README.md) explains the additional mining
requirements. Keep large source archives outside ordinary Git history.
