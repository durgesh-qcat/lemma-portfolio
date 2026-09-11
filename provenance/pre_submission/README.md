# Historical documentation and tooling

These files preserve exact bytes from the releases preceding the final paper.
They are provenance records, not current documentation or executable entrypoints.
The source commits and SHA-256 values are recorded in
[PRE_SUBMISSION_FILES.json](../PRE_SUBMISSION_FILES.json).

Files shared by the September 4 and September 5 baseline inventories are stored
once at their original relative paths. Their root READMEs differed, so those
copies are stored under the corresponding abbreviated commit IDs. Earlier paper
PDFs and LaTeX files are preserved in `paper/historical/2026-09-05/` instead of
duplicating them here.

The frozen baseline inventories are unchanged. Run
`python3 -B tools/verify_historical_baseline.py` from the repository root to check
every baseline entry. The richer follow-up verifiers run these checks as well.
Changed current files need an explicitly mapped historical copy with exactly
the original digest. Original evidence remains checked in place.
