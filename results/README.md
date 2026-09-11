# Result files

The final submitted paper is documented in [RESULTS.md](../RESULTS.md) and
[paper_results.json](paper_results.json). The JSON is an exact copy of
the submitted record and its byte equality is verified. The Markdown tables
preserve the same values with paths adapted for the repository root.

- [Selection patterns and frequency-tie geometry](../submission/LemmaPortfolio_supplement/results/selection_patterns.md)
- [Masking-exclusion sensitivity for all thirteen response sets](../submission/LemmaPortfolio_supplement/results/masking_sensitivity.md)
- [Candidate-replacement analysis](../submission/LemmaPortfolio_supplement/descriptive/README.md)
- [Exact oracle and greedy controls](../oracle/README.md)

`selection_patterns.json` and `masking_sensitivity.json` also mirror the final
submitted records. Other existing files here (`scores.json`, `per_item.jsonl`,
`structured_comparison.json`, and related outputs) preserve the original six
preliminary web rows and their original diagnostics. They do not contain the
seven later runs; those appear in the consolidated final results and under
`followups/2026-09-05/`.

The model-free expectation for uniform random choice differs from the original
single SHA-256-seeded random draw. Oracle scores use hidden proof-use labels and
are an upper bound, not model performance. Repeated model runs use the same
60 test episodes.
