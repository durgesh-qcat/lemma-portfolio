# Collaborating on LemmaPortfolio

Start with the [benchmark construction guide](../construction/README.md),
[technical write-up](../paper/LemmaPortfolio.pdf),
[data card](DATA_CARD.md), and [consolidated results](../RESULTS.md).

## Clone and verify

```sh
git clone https://github.com/durgesh-qcat/lemma-portfolio.git
cd lemma-portfolio
python3 -B verify_release.py
```

The verification must end with `ALL CHECKS PASSED`. It checks the benchmark
data, supporting archive, oracle, saved responses, and follow-up records.
Fork the repository and create a branch for edits; maintainers with write
access can create a branch directly:

```sh
git switch -c name/short-description
```

## Write-up edits

The current PDF's editable source is unavailable. Earlier LaTeX files are
preserved in the [historical source directory](../paper/historical/2026-09-05/).
Record proposed changes by page and section against the current PDF. Label
any source reconstruction and check it against that PDF. See
[source availability](OVERLEAF.md).

## Benchmark and documentation changes

Never hand-edit a published score. Preserve raw answers, run the scorer,
inspect item-level results, and document each new run's protocol. Keep new
outputs under `scratch_runs/` or a separate versioned run directory.
The original data, response evidence, ZIP, and unpacked files are archival
records and should remain intact.

After intentional repository changes, regenerate the root manifest and run:

```sh
python3 -B tools/build_sha256s.py
python3 -B verify_release.py
```

Preserve the embedded archive manifests. Machine-readable result mirrors must
stay synchronized with their original records. Commit reviewed changes on a
branch and open a pull request describing the change and verification result.
