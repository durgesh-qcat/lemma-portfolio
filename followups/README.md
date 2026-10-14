# Follow-up evaluation evidence

The [technical write-up](../paper/LemmaPortfolio.pdf) describes seven completed
CLI/API runs and the Astra target-wise diagnostic. Supporting reproducibility
materials are in the [archive directory](../submission/README.md); the
repository-wide summary is [RESULTS.md](../RESULTS.md).

- [2026-09-05](2026-09-05/README.md) preserves the completed experimental export,
  including five Codex runs, two Anthropic API runs, raw responses, receipts,
  calling code, and a separate twenty-episode diagnostic.
- [2026-09-04](2026-09-04/README.md) preserves an earlier partial workflow
  snapshot. Its pending-run statements describe the time of that export.

The snapshots overlap on the same sixty test episodes. Do not pool them as
additional experiments. The six preliminary web-interface response sets remain
separate from the seven completed follow-up runs.

From the repository root, verify the historical evidence without network
access or inference:

```sh
python3 -B followups/2026-09-04/verify.py
python3 -B followups/2026-09-05/verify.py
```

Both commands verify the original frozen inventories, responses, and scores.
Historical documentation and tooling retain their original bytes so their
recorded hashes remain reproducible. The current write-up and results overview
describe the consolidated evaluation.
