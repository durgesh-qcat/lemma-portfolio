#!/usr/bin/env python3
"""Independently verify the submitted optimum and true-label controls offline."""

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
from itertools import combinations
import json
from pathlib import Path


DEFAULT_SUPPLEMENT = Path(__file__).resolve().parents[1] / "submission/LemmaPortfolio_supplement"
EXPECTED = {
    "development": (30, 30, 28, 29, 26, "551/30", "5201/30"),
    "test": (60, 78, 57, 59, 53, "13469/360", "126869/360"),
}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def read_rows(path):
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    result = {row["episode_id"]: row for row in rows}
    require(len(rows) == len(result), f"Duplicate episode ID in {path.name}")
    return result


def coverage(selected, masks):
    covered = 0
    for candidate in selected:
        covered |= masks[candidate]
    return covered.bit_count()


def greedy(ids, masks):
    selected = []
    for _ in range(3):
        selected.append(max((c for c in ids if c not in selected),
                            key=lambda c: coverage([*selected, c], masks)))
    return tuple(sorted(selected))


def greedy_distribution(ids, masks):
    """Aggregate exact path probability at subsets, with uniform ties per step."""
    states = {frozenset(): Fraction(1)}
    for _ in range(3):
        following = defaultdict(Fraction)
        for selected, probability in states.items():
            values = {c: coverage(selected | {c}, masks) for c in ids if c not in selected}
            best = max(values.values())
            tied = [c for c, value in values.items() if value == best]
            for candidate in tied:
                following[selected | {candidate}] += probability / len(tied)
        states = following
    scores = defaultdict(Fraction)
    for selected, probability in states.items():
        scores[coverage(selected, masks)] += probability
    require(sum(scores.values()) == 1, "Greedy path probabilities do not sum to one")
    return scores


def verify_episode(public, label, recorded):
    eid = label["episode_id"]
    ids = [candidate["id"] for candidate in public["candidates"]]
    require(ids == sorted(set(ids)) and len(ids) == 16, f"{eid}: expected 16 ordered candidates")
    require(set(ids) == set(label["candidate_sources"]), f"{eid}: candidate inventory differs")
    targets = label["targets"]
    target_ids = [target["id"] for target in targets]
    require(len(targets) == len(set(target_ids)) == 8, f"{eid}: expected eight unique targets")
    require(target_ids == [target["id"] for target in public["targets"]], f"{eid}: target inventory differs")
    require(all(len(t["direct_candidates"]) == len(set(t["direct_candidates"])) and
                set(t["direct_candidates"]) <= set(ids) for t in targets), f"{eid}: invalid proof-use edges")
    masks = {c: sum(1 << i for i, target in enumerate(targets)
                    if c in target["direct_candidates"]) for c in ids}
    options = {p: coverage(p, masks) for p in combinations(ids, 3)}
    require(len(options) == 560, f"{eid}: expected 560 portfolios")
    optimum = max(options.values())
    optima = {p for p, value in options.items() if value == optimum}
    saved_optima = [tuple(p) for p in label["optimal_portfolios"]]
    require(len(saved_optima) == len(set(saved_optima)) and set(saved_optima) == optima,
            f"{eid}: optimal portfolio set differs")
    require(label["optimal_coverage"] == optimum, f"{eid}: optimal coverage differs")
    require(Counter(options.values()) == {int(k): v for k, v in label["coverage_histogram"].items()},
            f"{eid}: coverage histogram differs")
    degrees = {c: mask.bit_count() for c, mask in masks.items()}
    require(degrees == label["candidate_displayed_use_counts"], f"{eid}: occurrence counts differ")

    first = greedy(ids, masks)
    reverse = greedy(list(reversed(ids)), masks)
    require(first == tuple(sorted(label["construction_gate_predictions"]["true_greedy_set_cover"])),
            f"{eid}: fixed greedy portfolio differs")
    fixed_score, reverse_score = coverage(first, masks), coverage(reverse, masks)
    require(fixed_score == optimum - 1, f"{eid}: fixed greedy is not exactly one target short")
    distribution = greedy_distribution(ids, masks)
    reconstructed = {
        "optimum": optimum,
        "fixed_greedy": fixed_score,
        "reverse_display_greedy": reverse_score,
        "possible_scores": sorted(distribution),
        "random_tie_coverage_probabilities": {str(k): str(v) for k, v in sorted(distribution.items())},
    }
    for key, value in reconstructed.items():
        require(recorded[key] == value, f"{eid}: saved greedy audit differs at {key}")
    best_frequency = max(sum(degrees[c] for c in p) for p in options)
    frequency = {p for p in options if sum(degrees[c] for c in p) == best_frequency}
    return {
        "optimal_portfolios": len(optima),
        "optimal_coverage": optimum,
        "reverse_greedy_optimal": int(reverse_score == optimum),
        "some_greedy_path_optimal": int(optimum in distribution),
        "some_frequency_tie_optimal": int(bool(frequency & optima)),
        "random_greedy_optimal": distribution.get(optimum, Fraction()),
        "random_greedy_coverage": sum(value * probability for value, probability in distribution.items()),
        "frequency_portfolios": sorted(frequency),
        "frequency_optima": sorted(frequency & optima),
    }


def verify(supplement_root=DEFAULT_SUPPLEMENT):
    root = Path(supplement_root)
    original = root / "original_release"
    audit = json.loads((original / "results/posthoc_math_audit.json").read_text(encoding="utf-8"))
    selection = json.loads((root / "results/selection_patterns.json").read_text(encoding="utf-8"))
    report = {}
    modules = {}
    for split, expected in EXPECTED.items():
        public = read_rows(original / f"data/{split}.public.jsonl")
        labels = read_rows(original / f"data/{split}.labels.jsonl")
        require(public.keys() == labels.keys() and len(labels) == expected[0], f"{split}: split inventory differs")
        recorded = {row["episode_id"]: row for row in audit[split]["greedy_details"]}
        require(recorded.keys() == labels.keys(), f"{split}: greedy audit inventory differs")
        rows = {eid: verify_episode(public[eid], label, recorded[eid]) for eid, label in labels.items()}
        totals = {key: sum(row[key] for row in rows.values()) for key in (
            "optimal_portfolios", "reverse_greedy_optimal", "some_greedy_path_optimal",
            "some_frequency_tie_optimal", "random_greedy_optimal", "random_greedy_coverage")}
        actual = (len(labels), totals["optimal_portfolios"], totals["reverse_greedy_optimal"],
                  totals["some_greedy_path_optimal"], totals["some_frequency_tie_optimal"],
                  str(totals["random_greedy_optimal"]), str(totals["random_greedy_coverage"]))
        require(actual == expected, f"{split}: submitted oracle controls changed: {actual}")
        if split == "test":
            require(selection["episode_heuristics"].keys() == rows.keys(), "Frequency audit inventory differs")
            for eid, row in rows.items():
                saved = selection["episode_heuristics"][eid]
                for key, saved_key in (("frequency_portfolios", "frequency_maximizing_triples"),
                                       ("frequency_optima", "frequency_maximizing_optima")):
                    require(row[key] == [tuple(p) for p in saved[saved_key]],
                            f"{eid}: submitted frequency tie sets differ")
            require(sum(len(row["frequency_portfolios"]) for row in rows.values()) == 408,
                    "Test frequency tie count differs")
        report[split] = {"episodes": len(labels), "enumerated_portfolios": len(labels) * 560,
                         "exact_oracle_optimal_episodes": len(labels),
                         "fixed_greedy_optimal_episodes": 0,
                         **{key: str(value) if isinstance(value, Fraction) else value
                            for key, value in totals.items()}}
        modules[split] = {label["source_module"] for label in labels.values()}
    require(modules["test"].isdisjoint(modules["development"]), "Development/test modules overlap")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--supplement-root", type=Path, default=DEFAULT_SUPPLEMENT)
    parser.add_argument("--json", action="store_true", help="print the reconstructed control totals")
    args = parser.parse_args(argv)
    report = verify(args.supplement_root)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("PASS oracle: all 50,400 portfolios, 90 complete optimum sets, greedy controls, and test frequency ties")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
