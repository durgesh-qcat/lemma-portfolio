# Benchmark review checklist

To inspect the benchmark design and reproduce its results:

- Read the [data card](DATA_CARD.md) for the task, splits, and limitations.
- Follow the [construction guide](../construction/README.md) for the builder
  and pinned Lean annotation audit.
- Read the [technical write-up](../paper/LemmaPortfolio.pdf).
- Inspect the [supporting materials](../submission/README.md) and
  [consolidated results](../RESULTS.md).
- Run `python3 -B verify_release.py` from the repository root and check that
  it ends with `ALL CHECKS PASSED`.

For new model evaluations, follow the [rerun guide](RERUN_MODELS.md) and retain
raw responses and execution settings. Keep new experiments separate from the
existing evidence. The [write-up guide](../paper/README.md) explains source
availability and earlier versions.
