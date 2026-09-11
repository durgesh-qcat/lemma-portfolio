# LemmaPortfolio V4 data card

## What the data are for

LemmaPortfolio was made to study premise selection when several Lean goals
share one small budget.  It is a closed-pool task: in each episode, a system
chooses three of 16 displayed candidates for eight targets. We count how many
stored target proofs refer directly to at least one selected candidate.

The task separates optimal-portfolio recovery from partial target coverage and
can therefore be used to study set-level retrieval.  It is not a direct test of
proof success or logical necessity.

## What is included

The release contains 30 development episodes and 60 test episodes mined from
Mathlib v4.33.0 at commit
`db584cd6d46c92f209a44c0f1c829460d327499d`.  Every episode has:

- 16 candidate declarations shown under local IDs;
- eight target statements shown under local IDs;
- a budget of three candidates;
- the released direct-dependency incidence rows; and
- the maximum coverage and every portfolio attaining it.

The public row shows candidate types and target statements.  The label row maps
the local identifiers back to their source declarations and records which
displayed candidates occur directly in each target's stored elaborated proof
term. Aggregate construction records and a separate pinned-Lean check are
also included.

## Known masking limitation

The local IDs replace the top-level source names, but the original construction
check tested exact name tokens rather than every possible generated or dotted
identifier prefix. In the test split, a post-hoc scan found 33 residual source-name-prefix
occurrences in 25 source-name/statement pairs involving 24 source declarations
across 6/60 episodes. In development it found 5 occurrences in 5 pairs involving
5 source declarations across 2/30 episodes. The strings do not themselves print
the occurrence table, but they make exact declaration recovery easier. The
frozen episodes and reported scores were not altered after this finding.

## How episodes were chosen

Development, test, and earlier prototype episodes use disjoint modules.  We
also exclude exact statement repeats and repeats obtained by renaming leading
displayed binders.  A fixed collection of structural filters removes simple instances and retains a
deliberately difficult test set.  In particular, 20 construction methods
must all miss the optimum before an episode is accepted.

This conditioning is part of the dataset definition.  It means that the test
set is suitable for comparing declared methods on these episodes, but it does
not estimate how often difficult modules occur across Mathlib.  The supplement
and `../provenance/generation_receipt.json` give the full thresholds and source
inventory.

## Appropriate uses

- evaluating optimal shared-budget portfolio selection;
- comparing an optimal-portfolio choice with target-level partial coverage;
- developing set-level or incidence-aware retrieval methods; and
- reproducing the scores reported in the paper.

## Limits of the labels

A direct historical dependency can be replaced, and a useful declaration can
be absent from the stored proof.  Selecting a recorded dependency also does not
show that a new prover will succeed when it is added to the context.  The pool
is small and closed, and every candidate has the same cost. The archive
contains six response sets under visible deployment labels; their
scores are not a ranking of stable model families or providers.

## Privacy, licensing, and corrections

The dataset contains formal-library text and model-output captures, not human
subject data.  `../LICENSES.md` explains the licenses for each file category,
and `../NOTICE` gives the Mathlib attribution.  A correction should name the
affected episode and file hash; published V4 files should not be replaced
silently.
