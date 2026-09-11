# Collaborating on LemmaPortfolio

The repository contains the exact **7 September 2026 submitted paper and
supplement**. Start with [the final PDF](../paper/LemmaPortfolio.pdf),
[consolidated results](../RESULTS.md), and [paper provenance](../paper/README.md).
The seven CLI/API runs are incorporated in the final paper; the historical
September 5 handoff is retained as evidence of the earlier workflow.

## Clone and verify

The repository is public. Anyone can clone and verify the submitted artifacts:

```sh
git clone https://github.com/durgesh-qcat/lemma-portfolio.git
cd lemma-portfolio
python3 -B verify_release.py
```

The verification must end with `ALL CHECKS PASSED`. It checks the final submitted
packet and oracle as well as the preserved original and follow-up records.

For contributions, fork the repository and create a branch for edits. Maintainers
with write access can create a branch directly:

```sh
git switch -c name/short-description
```

## Paper edits and source availability

The final submitted paper's editable source is unavailable. The LaTeX files in
`paper/historical/2026-09-05/source/` build the earlier manuscript, not the final
submitted PDF. Do not use them as a starting point for final-paper edits without
reconciling them against the submitted paper. See [Overleaf status](OVERLEAF.md).

Record proposed edits against `paper/LemmaPortfolio.pdf` with page and section
references. Any future reconstruction of editable source should be clearly
labeled and checked against the submitted PDF. Keep the submitted PDF and
`submission/` snapshot intact; save later revisions under a new version.

## Benchmark and documentation changes

Never hand-edit a published score. Preserve raw model answers, run the scorer,
review the item-level results, and document the new run's protocol before adding
it to a later version. Keep new outputs under `scratch_runs/` or a separate
versioned run directory. The original data, response evidence, final submitted
ZIP and its unpacked files are archival records.

After reviewing intentional repository changes, regenerate the repository
manifest and run all checks:

```sh
python3 -B tools/build_sha256s.py
python3 -B verify_release.py
```

Do not regenerate the embedded submission manifest to disguise a change to the
submitted archive. The root `RESULTS.md` and `results/paper_results.json` mirror
the corresponding submitted files and must stay synchronized with them.

Commit the reviewed files on your branch and open a pull request. Describe what
changed and the verification result. GitHub Desktop supports the same workflow.

## Submitted artifacts

The submitted artifacts are [the exact submitted PDF](../paper/LemmaPortfolio.pdf)
and [anonymous reproducibility ZIP](../submission/LemmaPortfolio_supplement.zip).
The public repository also preserves historical GitHub receipts and the
additional oracle benchmark, with their provenance recorded separately from
the submitted packet.
