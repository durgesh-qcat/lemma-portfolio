# Follow-up evaluation evidence

The [final submitted paper](../paper/LemmaPortfolio.pdf) incorporates the seven
completed CLI/API runs and the Astra target-wise diagnostic. Its exact submitted
reproducibility archive is in [submission/](../submission/); the repository-wide
summary is [RESULTS.md](../RESULTS.md).

- [2026-09-05](2026-09-05/README.md) preserves the completed experimental export,
  including five Codex runs, two Anthropic API runs, raw responses, receipts,
  calling code, and the separate twenty-episode diagnostic.
- [2026-09-04](2026-09-04/README.md) preserves the earlier partial workflow
  snapshot. Its pending-run statements describe the time of that export.

The snapshots contain overlapping runs on the same sixty test episodes. Do not
pool them as additional experiments. The six preliminary web-interface response
sets remain separate from the seven completed follow-up runs.

From the repository root, verify the richer historical evidence without network
access or inference:

```sh
python3 -B followups/2026-09-04/verify.py
python3 -B followups/2026-09-05/verify.py
```

Both commands verify the original frozen release inventories as well as responses
and scores. [PRE_SUBMISSION_FILES.json](../provenance/PRE_SUBMISSION_FILES.json)
records explicit locations for the original documentation, manuscript, and
tooling bytes replaced during submission synchronization. Every original hash is
still required; unchanged benchmark evidence is checked at its original path.

The old [paper-writing handoff](2026-09-05/PAPER_HANDOFF.md) and exploratory
comparison reports document preparation before submission. The submitted paper
defines the current result presentation and interpretation.
