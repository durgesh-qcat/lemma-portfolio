# Coverage shortfall is not replacement distance

Two different quantities must be kept separate:

- Coverage shortfall is the maximum achievable target count minus the count
  achieved by the submitted triple.
- Replacement distance is the minimum number of selected candidates that must
  be replaced to reach any optimal triple. For a submitted set S and an optimal
  set O, this is the minimum of 3 - |S intersect O| over all optimal triples O.

The covered target sets can change: gaining one target in total need not mean
keeping every previously covered target and adding just one.

## Concrete stored-answer example

Episode `MLP4B_0005` comes from `Mathlib.Dynamics.PeriodicPts.Defs`. Each of the
three saved Astra runs selected the first portfolio below:

| Portfolio | Covered targets | Coverage |
|---|---|---:|
| C05, C12, C14 | T01, T02, T03, T05, T08 | 5 |
| C02, C09, C10 (the unique optimum) | T01, T02, T04, T06, T07, T08 | 6 |

The optimum loses T03 and T05 while gaining T04, T06, and T07: a net increase of
one covered target. But its candidate set is disjoint from the submitted set.
Reaching the unique optimum therefore requires three replacements, not one.
None of the submitted triple's 39 one-replacement neighbors is optimal.

## Which answers are being counted?

The historical "within one target" diagnostic means shortfall at most one:
it includes already optimal answers. The new replacement-distance audit instead
examines answers with shortfall exactly one, excluding all optimal answers.

Across the seven saved follow-up runs, there are 174 optimal response instances
and 163 exactly-one-target-short instances: together, 337 are at most one target
short. The distance audit concerns only those 163 nonoptimal instances. Of them,
134 need one replacement, 26 need two, and 3 need three. Their numbers of optimal
one-replacement neighbors are zero in 29 cases, one in 122, two in 10, and three
in 2.

These pooled counts describe repeated responses on the same 60 episodes, not
420 independent benchmark questions. They are retrospective measurements using
true labels. The existence of a successful replacement does not show that a
model can identify it without those labels; no repair experiment was performed.
