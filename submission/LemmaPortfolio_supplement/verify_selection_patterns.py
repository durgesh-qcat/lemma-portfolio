#!/usr/bin/env python3
"""Recompute post-hoc selection-pattern audits and nominal Wilson intervals.

Python 3.10+, standard library only. Default verifies saved derived outputs;
--write regenerates them. No inference, network access, or response repair.
"""

import argparse
from collections import Counter
from functools import lru_cache
import hashlib
from itertools import permutations
import json
from math import sqrt
from statistics import NormalDist, median

from verify_followups import ROOT, read, require, same
from verify_results import ORIGINAL, FOLLOWUP, episodes, summarize


def wilson(k, n):
    require(0 <= k <= n and n > 0, "Invalid binomial counts")
    z = NormalDist().inv_cdf(0.975)
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [0.0 if k == 0 else centre - half,
            1.0 if k == n else centre + half]


def graph_audit(e):
    cs = sorted(e["candidates"])
    supports = [e["supports"][t] for t in sorted(e["supports"])]
    masks = {c: sum(1 << i for i, s in enumerate(supports) if c in s) for c in cs}
    degree = {c: masks[c].bit_count() for c in cs}

    def mask(q):
        result = 0
        for c in q:
            result |= masks[c]
        return result

    @lru_cache(None)
    def tied_next(q):
        m = mask(q)
        gains = {c: (m | masks[c]).bit_count() - m.bit_count() for c in cs if c not in q}
        best = max(gains.values())
        return tuple(c for c in cs if c in gains and gains[c] == best)

    @lru_cache(None)
    def greedy_finals(q):
        if len(q) == 3:
            return frozenset([q])
        return frozenset().union(*(greedy_finals(tuple(sorted(q + (c,)))) for c in tied_next(q)))

    fixed_frequency = tuple(sorted(sorted(cs, key=lambda c: (-degree[c], c))[:3]))
    maximum_sum = sum(degree[c] for c in fixed_frequency)
    frequency_ties = {q for q in e["triples"] if sum(degree[c] for c in q) == maximum_sum}
    fixed_greedy = ()
    for _ in range(3):
        fixed_greedy = tuple(sorted(fixed_greedy + (tied_next(fixed_greedy)[0],)))
    all_greedy = greedy_finals(())
    profile_best = {}
    for q, value in zip(e["triples"], e["values"]):
        require(mask(q).bit_count() == value, "Independent bit-mask coverage disagrees")
        profile = tuple(sorted(degree[c] for c in q))
        profile_best[profile] = max(value, profile_best.get(profile, -1))
        reachable = any(all(order[j] in tied_next(tuple(sorted(order[:j])))
                            for j in range(3)) for order in permutations(q))
        require(reachable == (q in all_greedy), "Greedy path and permutation checks disagree")
    require(mask(fixed_frequency).bit_count() < e["maximum"], "Frequency filter not satisfied")
    require(mask(fixed_greedy).bit_count() == e["maximum"] - 1, "Greedy filter differs")
    return {"degree": degree, "profile_best": profile_best,
            "fixed_frequency": fixed_frequency, "frequency_ties": frequency_ties,
            "fixed_greedy": fixed_greedy, "all_greedy": all_greedy}


def calculate():
    eps = episodes()["test"]
    graphs = {eid: graph_audit(e) for eid, e in eps.items()}
    original_path = ROOT / "original_release/results/per_item.jsonl"
    original = [json.loads(line) for line in original_path.read_text().splitlines()]
    sources = [original_path, ROOT / "original_release/data/test.public.jsonl",
               ROOT / "original_release/data/test.labels.jsonl"]
    rows, records = [], []
    totals = {p: Counter() for p in ("preliminary_web", "followup", "all")}
    flags = ("fixed_frequency", "any_frequency", "fixed_greedy", "any_greedy",
             "same_degree_profile_improvable")
    for phase, roster in (("preliminary_web", ORIGINAL), ("followup", FOLLOWUP)):
        for entry in roster:
            sid, label, exact, covered = entry[:4]
            if phase == "preliminary_web":
                items = [x for x in original if x["system_id"] == sid]
                expected_valid = entry[4]
            else:
                path = ROOT / f"followups/2026-09-05/{sid}/score.json"
                sources.append(path)
                items = read(path)["per_item"]
                expected_valid = 60
            require({x["episode_id"] for x in items} == set(eps), "Incomplete run")
            score = summarize(items, eps, label, sid)
            require((score["exact_optimal"], score["covered_targets"], score["valid"]) ==
                    (exact, covered, expected_valid), "Score roster mismatch")
            counts = Counter(dict.fromkeys(("answers", "valid", "invalid", "optimal", "errors") +
                                            tuple(f + "_all" for f in flags) +
                                            tuple("error_" + f for f in flags), 0))
            for x in sorted(items, key=lambda x: x["episode_id"]):
                eid = x["episode_id"]
                counts["answers"] += 1
                counts["valid" if x["valid"] else "invalid"] += 1
                record = {"run_id": sid, "episode_id": eid, "valid": x["valid"],
                          "selected": x["selected"], "coverage": x["coverage"],
                          "optimal": x["optimal"], "patterns": None}
                if x["valid"]:
                    g = graphs[eid]
                    q = tuple(sorted(x["selected"]))
                    profile = tuple(sorted(g["degree"][c] for c in q))
                    best = g["profile_best"][profile]
                    patterns = dict(zip(flags, (q == g["fixed_frequency"], q in g["frequency_ties"],
                                                q == g["fixed_greedy"], q in g["all_greedy"],
                                                best > x["coverage"])))
                    error = not x["optimal"]
                    counts["errors" if error else "optimal"] += 1
                    for flag, matches in patterns.items():
                        counts[flag + "_all"] += matches
                        counts["error_" + flag] += error and matches
                    record.update(patterns=patterns, degree_profile=list(profile),
                                  best_coverage_same_degree_profile=best)
                records.append(record)
            rows.append({"id": sid, "label": label, "phase": phase, "counts": dict(counts),
                         "wilson_95_exact_rate": wilson(exact, 60)})
            totals[phase].update(counts)
            totals["all"].update(counts)
    follow = totals["followup"]
    require(tuple(follow[k] for k in ("errors", "error_fixed_frequency", "error_any_frequency",
                                     "error_fixed_greedy", "error_same_degree_profile_improvable")) ==
            (246, 21, 62, 19, 71), "Follow-up pattern counts differ")
    require((totals["all"]["answers"], totals["all"]["valid"], totals["all"]["errors"]) ==
            (780, 770, 527), "Answer denominators differ")
    z = NormalDist().inv_cdf(0.975)
    for k in range(61):
        lo, hi = wilson(k, 60)
        require(0 <= lo <= k / 60 <= hi <= 1, "Wilson range or centre error")
        other_lo, other_hi = wilson(60 - k, 60)
        require(abs(lo - (1 - other_hi)) < 1e-12 and abs(hi - (1 - other_lo)) < 1e-12,
                "Wilson symmetry error")
        for p in (lo, hi):
            if 0 < p < 1:
                require(abs((k - 60 * p) ** 2 - z * z * 60 * p * (1 - p)) < 1e-10,
                        "Wilson endpoint fails independent score-test inversion")
    require(wilson(0, 60)[0] == 0 and wilson(60, 60)[1] == 1, "Wilson boundary error")
    graph_rows = {eid: {"fixed_frequency": list(g["fixed_frequency"]), "fixed_greedy": list(g["fixed_greedy"]),
                        "frequency_tie_portfolios": len(g["frequency_ties"]),
                        "greedy_tie_portfolios": len(g["all_greedy"]),
                        "frequency_maximizing_triples": [list(q) for q in sorted(g["frequency_ties"])],
                        "frequency_maximizing_optima": [list(q) for q in sorted(g["frequency_ties"] & set(eps[eid]["optima"]))],
                        "best_frequency_coverage": max(value for q, value in zip(eps[eid]["triples"], eps[eid]["values"])
                                                       if q in g["frequency_ties"])} for eid, g in graphs.items()}
    tie_sizes = [g["frequency_tie_portfolios"] for g in graph_rows.values()]
    has_optimum = {eid for eid, g in graph_rows.items() if g["frequency_maximizing_optima"]}
    # Independent threshold construction of every tied top-three portfolio.
    from itertools import combinations
    for eid, e in eps.items():
        degrees = {c: sum(c in s for s in e["supports"].values()) for c in e["candidates"]}
        threshold = sorted(degrees.values(), reverse=True)[2]
        above = {c for c, d in degrees.items() if d > threshold}
        at = sorted(c for c, d in degrees.items() if d == threshold)
        threshold_triples = {tuple(sorted(above | set(q))) for q in combinations(at, 3 - len(above))}
        require(threshold_triples == graphs[eid]["frequency_ties"], "Independent frequency threshold audit differs")
    geometry = {"episodes": len(eps), "episodes_with_frequency_optimum": len(has_optimum),
                "episodes_without_frequency_optimum": sorted(set(eps) - has_optimum),
                "total_frequency_ties": sum(tie_sizes), "mean_frequency_ties": sum(tie_sizes) / len(eps),
                "median_frequency_ties": median(tie_sizes), "min_frequency_ties": min(tie_sizes),
                "max_frequency_ties": max(tie_sizes),
                "frequency_tie_histogram": {str(k): v for k, v in sorted(Counter(tie_sizes).items())},
                "optimal_triples": sum(len(e["optima"]) for e in eps.values()),
                "frequency_maximizing_optimal_triples": sum(len(g["frequency_maximizing_optima"]) for g in graph_rows.values())}
    follow_ids = {entry[0] for entry in FOLLOWUP}
    follow_errors = [r for r in records if r["run_id"] in follow_ids and r["valid"] and not r["optimal"]]
    decomposition = Counter(dict.fromkeys(("outside_frequency_set", "inside_set_with_optimum",
                                           "inside_set_without_optimum", "outside_on_frequency_feasible_episode",
                                           "outside_on_frequency_infeasible_episode",
                                           "profile_improvable_inside_frequency_set",
                                           "profile_improvable_outside_frequency_set"), 0))
    for r in follow_errors:
        feasible = r["episode_id"] in has_optimum
        inside = r["patterns"]["any_frequency"]
        decomposition["inside_set_with_optimum" if feasible else "inside_set_without_optimum"] += inside
        decomposition["outside_frequency_set"] += not inside
        decomposition["outside_on_frequency_feasible_episode" if feasible else
                      "outside_on_frequency_infeasible_episode"] += not inside
        decomposition["profile_improvable_inside_frequency_set" if inside else
                      "profile_improvable_outside_frequency_set"] += r["patterns"]["same_degree_profile_improvable"]
    require((geometry["episodes_with_frequency_optimum"], sum(tie_sizes), median(tie_sizes),
             min(tie_sizes), max(tie_sizes)) == (53, 408, 4, 1, 35), "Frequency geometry differs")
    require(tuple(decomposition[k] for k in ("outside_frequency_set", "inside_set_with_optimum",
                                            "inside_set_without_optimum", "profile_improvable_inside_frequency_set",
                                            "profile_improvable_outside_frequency_set")) == (184, 52, 10, 52, 19),
            "Descriptive error decomposition differs")
    require(decomposition["outside_frequency_set"] + decomposition["inside_set_with_optimum"] +
            decomposition["inside_set_without_optimum"] == follow["errors"], "Error partition fails")
    return {"schema": "lemma-portfolio-selection-patterns-v2", "post_hoc": True,
            "definitions": {
                "frequency": "Rank candidates by the number of target proofs directly referencing them; no overlap correction.",
                "greedy": "Sequentially select the largest marginal union coverage, recomputing after each pick.",
                "fixed": "Ascending candidate-ID tie breaking, as in the construction filters.",
                "any_frequency": "Accept every triple maximizing the sum of individual occurrence counts.",
                "any_greedy": "Accept every triple reachable by any sequence of marginal-coverage greedy ties.",
                "same_degree_profile_improvable": "A triple with the same multiset of individual occurrence counts has larger union coverage.",
                "pattern_denominator": "Valid non-optimal answer instances; repeated episodes are not independent problems.",
                "interpretation": "Hidden-label descriptive comparisons, not identified internal model strategies or evaluated repairs.",
                "frequency_geometry": "Distinct test episodes and all tied frequency-maximizing triples; not weighted by model success.",
                "error_decomposition": "Outside-frequency, inside-with-optimum, and inside-without-optimum partition valid follow-up errors; these are not causal error labels.",
                "wilson_95": "Nominal two-sided 95% Wilson score interval, no continuity correction, n=60 per run including invalid answers.",
                "uncertainty_scope": "Independent-episode binomial approximation; five-episode prompt blocks may induce dependence. Not deployment or run-level uncertainty."},
            "input_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in sorted(set(sources))},
            "phase_totals": {p: dict(c) for p, c in totals.items()},
            "frequency_geometry": geometry, "followup_error_decomposition": dict(decomposition),
            "rows": rows, "episode_heuristics": graph_rows, "per_item": records}


def markdown(data):
    lines = ["# Post-hoc selection-pattern audit", "",
             "All counts are recomputed offline from saved selections and hidden direct-use annotations.", "",
             "| Run | Valid errors | Fixed freq. | Any freq. tie | Fixed greedy | Any greedy tie | Same-profile improvement |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    keys = ("errors", "error_fixed_frequency", "error_any_frequency", "error_fixed_greedy",
            "error_any_greedy", "error_same_degree_profile_improvable")
    for row in data["rows"]:
        lines.append("| " + row["label"] + " | " + " | ".join(str(row["counts"][k]) for k in keys) + " |")
    for phase, counts in data["phase_totals"].items():
        lines.append("| " + phase + " TOTAL | " + " | ".join(str(counts[k]) for k in keys) + " |")
    lines += ["", "## Nominal Wilson 95% intervals", "",
              "| Run | Exact /60 | 95% interval (%) |", "|---|---:|---:|"]
    for row in data["rows"]:
        lo, hi = row["wilson_95_exact_rate"]
        lines.append(f"| {row['label']} | {row['counts']['optimal']} | {100*lo:.1f}--{100*hi:.1f} |")
    g = data["frequency_geometry"]
    lines += ["", "## Frequency-tie geometry", "",
              f"- Episodes with at least one optimum among frequency maximizers: {g['episodes_with_frequency_optimum']}/{g['episodes']}.",
              f"- Tied triples: total {g['total_frequency_ties']}; mean {g['mean_frequency_ties']:.1f}; median {g['median_frequency_ties']:.0f}; range {g['min_frequency_ties']}--{g['max_frequency_ties']}.",
              f"- Frequency-maximizing optima: {g['frequency_maximizing_optimal_triples']}/{g['optimal_triples']} distinct optimal triples.",
              "- Episodes without a frequency-maximizing optimum: " + ", ".join(g["episodes_without_frequency_optimum"]) + ".",
              "", "## Follow-up error partition (descriptive, not causal)", ""]
    lines.extend(f"- {k}: {v}" for k, v in data["followup_error_decomposition"].items())
    lines += ["", "A non-frequency-maximizing selection is not necessarily a usage-estimation error: seven episodes require such a selection, and overlap improvements also exist outside frequency-maximizing sets.",
              "", "## Definitions and interpretation", ""]
    lines.extend(f"- {key}: {value}" for key, value in data["definitions"].items())
    lines += ["", "Run python3 -B verify_selection_patterns.py to reproduce.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    data = calculate()
    json_path = ROOT / "results/selection_patterns.json"
    md_path = ROOT / "results/selection_patterns.md"
    if args.write:
        json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        md_path.write_text(markdown(data), encoding="utf-8")
    else:
        same(data, read(json_path), "Selection-pattern audit")
        require(md_path.read_text(encoding="utf-8") == markdown(data), "Pattern Markdown differs")
    print("PASS: 780 answers, frequency/greedy ties, tie-set geometry, descriptive error partition, matched-degree comparisons, and Wilson intervals")


if __name__ == "__main__":
    main()
