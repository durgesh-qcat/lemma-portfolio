# Result files

Start with [RESULTS.md](../RESULTS.md) for the main CLI/API results, preliminary
web results, exact oracle, construction controls, and supplementary analyses.
Its model and baseline values come from [consolidated results](paper_results.json),
an exact copy of the archived record whose byte equality is verified.
The overview also summarizes the separate archived analyses linked below.

The exact test oracle achieves **60/60 optimal portfolios** with mean coverage
**6.25/8**. `paper_results.json` records its coverage distribution in
`test_maximum_histogram` (45 episodes at six targets and 15 at seven), its 78
optimal triples in `test_optimal_portfolios`, and 560 portfolios per episode.
It does not encode the oracle as a model entry in `direct_rows`. Independently
verify all 90 episodes and the control totals with
`python3 -B tools/verify_oracle.py --json` from the repository root.

- [Selection patterns and frequency-tie geometry](../submission/LemmaPortfolio_supplement/results/selection_patterns.md)
- [Masking-exclusion sensitivity for all thirteen response sets](../submission/LemmaPortfolio_supplement/results/masking_sensitivity.md)
- [Candidate-replacement analysis](../submission/LemmaPortfolio_supplement/descriptive/README.md)
- [Exact oracle and greedy controls](../oracle/README.md)

`selection_patterns.json` and `masking_sensitivity.json` also mirror the final
archived records. Other existing files here (`scores.json`, `per_item.jsonl`,
`structured_comparison.json`, and related outputs) preserve the original six
preliminary web rows and their original diagnostics. They do not contain the
seven later runs; those appear in the consolidated final results and under
`followups/2026-09-05/`.

The model-free expectation for uniform random choice differs from the original
single SHA-256-seeded random draw. Oracle scores use hidden proof-use labels and
are an upper bound, not model performance. Repeated model runs use the same
60 test episodes.
