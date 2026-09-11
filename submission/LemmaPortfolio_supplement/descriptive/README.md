# Descriptive replacement distances for saved answers

This is an interpretation of existing selections, not a new model-improvement
experiment. No model inference, repair attempts, or changes to selection rules
were made. True labels are used retrospectively to measure distances, not to
produce improved model answers.

From the packet root:

```sh
python3 verify_descriptive.py
```

The wrapper verifies packet integrity and original follow-up arithmetic, then
runs the unchanged audit script against temporary copies of the archived inputs.
The complete report, including source hashes, is reproduced without another
repository checkout, external dependencies, or network access. Original complete
numeric score records are retained under `source_records/` for byte-identical
replay; these contain score/filename bookkeeping, not provider API payloads.

## Definitions

Only valid submitted triples whose actual coverage is exactly one target below
the episode's maximum enter this audit. This excludes already optimal answers.
The distance to optimality is the minimum number of candidate replacements
needed to reach any true optimal triple: three minus the largest overlap with
an optimal triple. A selected triple has exactly 39 one-replacement neighbors,
obtained by removing one of its three candidates and adding one of the thirteen
unselected candidates. The audit reconstructs all 560 triples and all optima.

## Results by saved run

| Recorded run | Exactly one target short | Need one replacement | Need two | Need three |
|---|---:|---:|---:|---:|
| Astra xhigh 1 | 22 | 18 | 3 | 1 |
| Astra xhigh 2 | 20 | 15 | 4 | 1 |
| Astra max 1 | 22 | 19 | 2 | 1 |
| Sol xhigh 1 | 18 | 15 | 3 | 0 |
| Sol xhigh 2 | 27 | 22 | 5 | 0 |
| Fable 5 xhigh 1 | 25 | 21 | 4 | 0 |
| Fable 5.1 xhigh 1, reported system context | 29 | 24 | 5 | 0 |

Across these seven runs, 163 response instances are exactly one target short:
134 admit an optimal one-replacement neighbor, 26 require two replacements, and
3 require three. Among the 39 possible one-replacement neighbors, the number
that is optimal is zero in 29 cases, one in 122 cases, two in 10 cases, and three
in 2 cases. Complete episode-level selections and counts are in the JSON report.

These are repeated response instances on the same 60 benchmark episodes, not
163 independent problems or 420 independent test items. Being one target short
does not imply being one candidate replacement away. Even where one replacement
suffices, its existence does not show that a model can identify it without the
hidden proof-use annotations. This audit reports no successful repair method.
