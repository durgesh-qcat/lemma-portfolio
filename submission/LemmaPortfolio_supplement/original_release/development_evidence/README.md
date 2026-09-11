# Development difficulty evidence

The archive preserves one model-based check on the development set. We sent the
first 15 episodes, in three blocks of five, to a fixed Codex CLI Sol
configuration.  All 15 outputs were valid and 6 selected an optimal portfolio.

- `frozen/` contains the protocol and prompts, the saved responses in
  machine-readable form, the item records, the run manifest, and the receipt
  made before the labels were opened.
- `original_results/` contains the original score, item rows, analytic random
  reference, and the decision made from the development result.
- `decision_rule.json` contains the rule fixed before this calibration.

Running `python3 verify_release.py` from the archive directory checks these
files, reconstructs all 15 optima from the released labels, and reproduces the
6/15 score.  This result was used only as a development difficulty check and
does not enter the 60-episode model results.
