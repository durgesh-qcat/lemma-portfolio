# LemmaPortfolio V4 data card

## Purpose

LemmaPortfolio measures a closed-pool, shared-budget premise-selection task for
Lean.  It is intended for studying set-level retrieval and diagnostic reasoning,
not for claiming proof success or logical necessity.

## Contents

- 30 development and 60 test episodes from Mathlib v4.33.0 at commit
  `db584cd6d46c92f209a44c0f1c829460d327499d`;
- 16 name-masked candidate declarations, eight name-masked targets, and budget
  three per episode;
- released direct-dependency incidence rows, exhaustive optimum coverage, and
  every maximizing portfolio; and
- aggregate construction and pinned-Lean audit receipts.

The public episode exposes candidate types and target statements.  Its released
label row contains source-declaration provenance and the intersection between
each target's historical direct proof-value constants and the displayed pool.

## Construction and splits

Episodes are module-disjoint across development, test, and earlier prototypes.
Deterministic structural filters select a deliberately difficult stress set and
reject instances solved by fixed construction diagnostics.  The distribution is
therefore not representative of the frequency of hard modules across Mathlib.
See the paper supplement and `provenance/generation_receipt.json` for the complete
criteria and source-file inventory.

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
- The included consumer captures are a convenience sample, not a ranking of
  providers, architectures, or stable checkpoints.

## Privacy, licensing, and maintenance

The benchmark contains formal-library text and model-output captures, not human
subject data.  File-category licensing is described in `../LICENSES.md`, with
Mathlib attribution in `../NOTICE`.  Corrections should be reported through the
repository's issue tracker and accompanied by the affected file hash and episode
ID; published V4 files should not be silently replaced.
