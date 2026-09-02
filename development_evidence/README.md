# Development difficulty evidence

This directory preserves the sole model-facing development check reported in
the paper.  The first 15 released development episodes were sent in three fixed
five-item calls to a controlled Codex CLI Sol configuration.  All 15 selections
were valid and 6 were exact optima.

- `frozen/` contains the frozen protocol, prompts, response projections,
  per-item events, run manifest, and pre-label-unseal panel receipt.
- `original_results/` contains the original score, per-item rows, analytic
  random reference, and development-gate decision.
- `decision_rule.json` contains the rule fixed before this calibration.

The root `python3 verify_release.py` command checks the frozen capture inventory,
reconstructs all 15 optima from the released labels, and independently reproduces
the 6/15 score.  This is development evidence only; it is not part of the
60-item consumer table.
