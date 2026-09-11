# LemmaPortfolio data card — final submitted version

The 7 September 2026 paper is *LemmaPortfolio: Shared-Budget Lemma Selection
for Multiple Lean Goals*. Its benchmark is the unchanged V4 dataset; the final
submission adds evaluation records and analyses, not a new test split. See
[the final PDF](../paper/LemmaPortfolio.pdf) and [submitted reproducibility specification](../submission/LemmaPortfolio_supplement/REPRODUCIBILITY.md).

## Purpose

LemmaPortfolio measures a closed-pool, shared-budget premise-selection task for
Lean.  It is intended for studying set-level retrieval and diagnostic reasoning,
not for claiming proof success or logical necessity.

## Contents

- 30 development and 60 test episodes from Mathlib v4.33.0 at commit
  `db584cd6d46c92f209a44c0f1c829460d327499d`;
- 16 candidate declarations and eight targets with local-ID masking, and budget
  three per episode;
- released direct-dependency incidence rows, exhaustive optimum coverage, and
  every maximizing portfolio (78 optimal triples across the 60 test episodes); and
- aggregate construction and pinned-Lean audit receipts.

The public episode exposes candidate types and target statements.  Its released
label row contains source-declaration provenance and the intersection between
each target's historical direct proof-value constants and the displayed pool.

## Construction and splits

Episodes are module-disjoint across development, test, and earlier prototypes.
Deterministic structural filters select a deliberately difficult stress set and
reject instances solved by fixed construction diagnostics.  The distribution is
therefore not representative of the frequency of hard modules across Mathlib.
The fixed construction selectors use a specific tie order; their failure is
an admission condition. Alternative tie orders can succeed. See the
[submitted construction specification](../submission/LemmaPortfolio_supplement/REPRODUCIBILITY.md)
and `provenance/generation_receipt.json` for the complete criteria and inventory.

The 60 test episodes contain 480 target instances and 814 recorded
candidate–target occurrences. The optimum is six targets on 45 episodes and
seven on 15, for an oracle mean of 6.25/8. The
[oracle benchmark](../oracle/README.md) independently enumerates these ceilings.

## Masking and exposure

Local-ID masking is incomplete. The source-name-prefix audit identifies
6/60 test and 2/30 development episodes with residual names; the construction
check missed some generated or dotted identifiers beginning with a source name.
The final [masking sensitivity](../submission/LemmaPortfolio_supplement/results/masking_sensitivity.md)
re-scores all thirteen direct-response sets after excluding those same six test
episodes. No run exceeds 27/54 exact optima. This changes the evaluated episode
composition; it does not isolate a causal masking effect or establish absence
of model training exposure. Public Mathlib statements and the released labels
are available, so new evaluated processes must be kept separate from the labels.

## Appropriate uses

- evaluating exact shared-budget portfolio selection;
- comparing exact optimality with partial target coverage;
- developing set-level or incidence-aware retrievers; and
- reproducing the reported paper scores.

## Out-of-scope interpretations

- A direct historical dependency need not be logically necessary.
- Selecting a dependency does not establish that a prover would succeed when it
  is placed in context.
- Scores on this conditioned, closed-pool sample do not estimate performance on
  all of Mathlib or open-library retrieval.
- The six preliminary web-interface captures and seven CLI/API runs have
  different execution records and controls. They do not establish a stable
  ranking of providers, architectures, or checkpoints.
- The repeated runs share the same 60 episodes; pooled answer counts are not
  additional independent benchmark problems.
- Frequency, greedy, tie and replacement audits use true labels retrospectively;
  they do not establish a model's internal strategy or a successful repair method.

## Privacy, licensing, and maintenance

The benchmark contains formal-library text and model-output captures, not human
subject data.  File-category licensing is described in `../LICENSES.md`, with
Mathlib attribution in `../NOTICE`.  Corrections should be reported through the
repository's issue tracker and accompanied by the affected file hash and episode
ID; published V4 files should not be silently replaced.
