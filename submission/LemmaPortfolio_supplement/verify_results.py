#!/usr/bin/env python3
"""Recompute the paper's numerical claims and additional-score tables, offline.

Python 3.10+, standard library only. --write regenerates the two derived tables;
the default checks them without changing the archive. No model calls.
"""

import argparse
from collections import Counter
from fractions import Fraction
from itertools import combinations
import json
from math import comb, isclose
from pathlib import Path

from verify_followups import ROOT, load_jsonl, read, require, same


ORIGINAL = [
    ("gpt_sol_5_6_pro", "GPT SOL 5.6 Pro", 25, 299, 55),
    ("gpt_sol_5_6_xhigh", "GPT SOL 5.6 xhigh", 18, 305, 60),
    ("deepseek_instant_deepthink", "DeepSeek Instant + DeepThink", 1, 252, 60),
    ("deepseek_expert_deepthink", "DeepSeek Expert + DeepThink", 7, 276, 60),
    ("qwen_3_8_max_thinking", "Qwen 3.8 Max-Thinking", 12, 259, 55),
    ("qwen_3_7_plus_thinking", "Qwen 3.7 Plus-Thinking", 6, 243, 60),
]
FOLLOWUP = [
    ("astra_xhigh_r1_prior", "GPT-6 Astra / xhigh / 1", 27, 328),
    ("astra_xhigh_r2", "GPT-6 Astra / xhigh / 2", 30, 332),
    ("sol_xhigh_r1", "GPT-5.6 Sol / xhigh / 1", 20, 302),
    ("sol_xhigh_r2", "GPT-5.6 Sol / xhigh / 2", 15, 300),
    ("astra_max_r1", "GPT-6 Astra / max / 1", 30, 335),
    ("claude_fable_5_xhigh_r1", "Claude Fable 5 / xhigh", 26, 331),
    ("claude_fable_5_1_xhigh_ctx_r1", "Claude Fable 5.1 / xhigh / context", 26, 335),
]


def coverage(selected, supports):
    return sum(bool(set(selected) & s) for s in supports.values())


def episodes():
    result, source_names, source_modules, statement_text = {}, {}, {}, {}
    for split, count in (("development", 30), ("test", 60)):
        public = load_jsonl(ROOT / f"original_release/data/{split}.public.jsonl")
        labels = load_jsonl(ROOT / f"original_release/data/{split}.labels.jsonl")
        require(len(public) == count and public.keys() == labels.keys(), "Split IDs")
        result[split] = {}
        source_names[split], source_modules[split], statement_text[split] = set(), set(), set()
        for eid, p in public.items():
            label = labels[eid]
            cs = [c["id"] for c in p["candidates"]]
            ts = [t["id"] for t in p["targets"]]
            require(len(cs) == len(set(cs)) == 16 and len(ts) == len(set(ts)) == 8,
                    f"Dimensions: {eid}")
            require(p["selection_budget"] == 3, f"Budget: {eid}")
            supports = {t["id"]: set(t["direct_candidates"]) for t in label["targets"]}
            require(set(supports) == set(ts), f"Target IDs: {eid}")
            require(all(s <= set(cs) for s in supports.values()), f"Unknown candidate: {eid}")
            triples = list(combinations(sorted(cs), 3))
            values = [coverage(q, supports) for q in triples]
            maximum = max(values)
            optima = [q for q, v in zip(triples, values) if v == maximum]
            require(len(triples) == 560 and maximum == label["optimal_coverage"], f"Maximum: {eid}")
            require(sorted(map(tuple, label["optimal_portfolios"])) == optima,
                    f"Complete optimum set: {eid}")
            counts = {c: sum(c in s for s in supports.values()) for c in cs}
            active = {c for c, n in counts.items() if n}
            in_optima = set().union(*map(set, optima))
            require(maximum >= 6 and len(optima) <= 32 and max(counts.values()) <= 4,
                    f"Construction bounds: {eid}")
            require(len(active) >= 7 and len(active - in_optima) >= 4,
                    f"Active/distractor constraints: {eid}")
            require(sum(len(s) >= 2 for s in supports.values()) >= 2 and
                    values.count(maximum - 1) >= 2 and
                    all(counts[c] >= 2 for c in in_optima), f"Overlap constraints: {eid}")
            result[split][eid] = {"candidates": set(cs), "supports": supports,
                                  "triples": triples, "values": values,
                                  "maximum": maximum, "optima": optima}
            source_names[split].update(label["candidate_sources"].values())
            source_names[split].update(label["target_sources"].values())
            source_modules[split].add(label["source_module"])
            statement_text[split].update(x["statement"] for x in p["candidates"] + p["targets"])
        require(len(source_modules[split]) == count, "Repeated module within split")
    require(not (source_modules["development"] & source_modules["test"]), "Module overlap")
    require(not (source_names["development"] & source_names["test"]), "Source declaration overlap")
    require(not (statement_text["development"] & statement_text["test"]), "Statement overlap")
    return result


def summarize(items, eps, label, run_id):
    require(len({x["episode_id"] for x in items}) == len(items), f"Duplicate score ID: {run_id}")
    n = len(items)
    valid = exact = covered = selected_edges = hidden_edges = 0
    shares = Fraction()
    for x in items:
        e = eps[x["episode_id"]]
        require(type(x["valid"]) is bool, "Invalid validity type")
        s = x["selected"]
        if x["valid"]:
            require(len(s) == len(set(s)) == 3 and set(s) <= e["candidates"], "Invalid valid portfolio")
        value = coverage(s, e["supports"]) if x["valid"] else 0
        edges = sum(len(set(s) & t) for t in e["supports"].values()) if x["valid"] else 0
        total_edges = sum(map(len, e["supports"].values()))
        correct = x["valid"] and value == e["maximum"]
        require(x["coverage"] == value and x["optimal"] == correct and
                x["selected_edges"] == edges and x["hidden_edges"] == total_edges,
                f"Per-item score mismatch: {run_id}/{x['episode_id']}")
        require(x["optimal_coverage"] == e["maximum"] and
                isclose(x["normalized_coverage"], value / e["maximum"], abs_tol=1e-12),
                "Normalized per-item score mismatch")
        valid += x["valid"]
        exact += correct
        covered += value
        selected_edges += edges
        hidden_edges += total_edges
        shares += Fraction(value, e["maximum"])
    return {"id": run_id, "label": label, "episodes": n, "valid": valid,
            "exact_optimal": exact, "covered_targets": covered, "target_instances": 8 * n,
            "mean_coverage": covered / n,
            "share_of_maximum_coverage_percent": float(100 * shares / n),
            "occurrence_recall_percent": 100 * selected_edges / hidden_edges,
            "selected_occurrences": selected_edges, "recorded_occurrences": hidden_edges}


def compare_summary(actual, saved):
    mapping = {"exact_optimal": "exact_optimal", "valid": "valid", "episodes": "total",
               "covered_targets": "achieved_target_coverage", "target_instances": "target_count",
               "share_of_maximum_coverage_percent": "mean_oracle_normalized_coverage_percentage",
               "occurrence_recall_percent": "selected_edge_recall_percentage"}
    for a, b in mapping.items():
        require(isclose(actual[a], saved[b], rel_tol=1e-12, abs_tol=1e-12),
                f"Aggregate mismatch: {actual['id']}/{a}")


def calculate():
    all_eps = episodes()
    eps = all_eps["test"]
    require(Counter(e["maximum"] for e in eps.values()) == {6: 45, 7: 15}, "Maximum profile")
    require(sum(len(e["optima"]) for e in eps.values()) == 78, "Optimal portfolio count")
    original = read(ROOT / "original_release/results/scores.json")
    records = [json.loads(x) for x in (ROOT / "original_release/results/per_item.jsonl").read_text().splitlines()]
    grouped = {sid: [x for x in records if x["system_id"] == sid]
               for sid in {x["system_id"] for x in records}}
    saved = {x["system_id"]: x for x in original["rows"]}
    rows = []
    tfid = "public_text_char_tfidf_facility"
    for sid, label, exact, cov, valid in [(tfid, "Character TF-IDF", 0, 226, 60)] + ORIGINAL:
        require({x["episode_id"] for x in grouped[sid]} == set(eps), "Full 60-episode denominator")
        row = summarize(grouped[sid], eps, label, sid)
        require((row["exact_optimal"], row["covered_targets"], row["valid"]) == (exact, cov, valid),
                f"Paper table differs: {sid}")
        compare_summary(row, saved[sid])
        rows.append(row)
    follows = {}
    for sid, label, exact, cov in FOLLOWUP:
        report = read(ROOT / f"followups/2026-09-05/{sid}/score.json")
        require({x["episode_id"] for x in report["per_item"]} == set(eps), "Incomplete follow-up")
        row = summarize(report["per_item"], eps, label, sid)
        require((row["exact_optimal"], row["covered_targets"], row["valid"]) == (exact, cov, 60),
                f"Follow-up table differs: {sid}")
        compare_summary(row, report["summary"])
        rows.append(row)
        follows[sid] = report["per_item"]
    random_exact, random_cov, random_share = Fraction(), Fraction(), Fraction()
    for e in eps.values():
        analytic = sum((1 - Fraction(comb(16 - len(s), 3), 560)
                        for s in e["supports"].values()), Fraction())
        enumerated = Fraction(sum(e["values"]), 560)
        require(analytic == enumerated, "Random coverage formula differs from enumeration")
        random_exact += Fraction(len(e["optima"]), 560)
        random_cov += analytic
        random_share += analytic / e["maximum"]
    random = {"expected_optimal_answers": float(random_exact),
              "expected_optimal_answers_fraction": str(random_exact),
              "expected_mean_coverage": float(random_cov / 60),
              "expected_mean_coverage_fraction": str(random_cov / 60),
              "share_of_maximum_coverage_percent": float(100 * random_share / 60),
              "occurrence_recall_percent": 18.75}
    for a, b in (("expected_optimal_answers", "expected_exact_episodes"),
                 ("expected_mean_coverage", "mean_expected_coverage_out_of_8"),
                 ("share_of_maximum_coverage_percent", "mean_oracle_normalized_coverage_percentage"),
                 ("occurrence_recall_percent", "expected_edge_recall_percentage")):
        require(isclose(random[a], original["uniform_random_analytic"][b], abs_tol=1e-12), "Random summary differs")
    distances, neighbors = Counter(), Counter()
    for items in follows.values():
        for x in items:
            e = eps[x["episode_id"]]
            if x["coverage"] != e["maximum"] - 1:
                continue
            selected = set(x["selected"])
            distances[min(3 - len(selected & set(q)) for q in e["optima"])] += 1
            adjacent = {tuple(sorted((selected - {old}) | {new}))
                        for old in selected for new in e["candidates"] - selected}
            require(len(adjacent) == 39, "Single-swap neighborhood size")
            neighbors[len(adjacent & set(e["optima"]))] += 1
    require(distances == {1: 134, 2: 26, 3: 3}, "Replacement distances differ")
    require(neighbors == {0: 29, 1: 122, 2: 10, 3: 2}, "Successful replacement counts differ")
    paired = []
    for sid, expected_n, expected_direct, expected_support in (
            ("gpt_sol_5_6_pro", 15, 4, 1), ("gpt_sol_5_6_xhigh", 20, 1, 0)):
        direct = {x["episode_id"]: x for x in grouped[sid + "_matched_direct"]}
        support = {x["episode_id"]: x for x in grouped[sid + "_support_q2"]}
        ids = sorted(k for k in direct if direct[k]["valid"] and support[k]["valid"])
        d = summarize([direct[k] for k in ids], eps, sid + " paired direct", sid + "_paired_direct")
        s = summarize([support[k] for k in ids], eps, sid + " paired target-wise", sid + "_paired_q2")
        require((len(ids), d["exact_optimal"], s["exact_optimal"]) ==
                (expected_n, expected_direct, expected_support), "Original paired result differs")
        paired.append({"id": sid, "episode_ids": ids, "direct": d, "target_wise_q2": s})
    diag = read(ROOT / "followups/2026-09-05/astra_diagnostic/score.json")
    d = summarize(diag["direct"]["per_item"], eps, "Astra paired direct", "astra_diagnostic_direct")
    q2 = next(x for x in diag["sweep"] if x["q"] == 2)
    s = summarize(q2["per_item"], eps, "Astra paired target-wise", "astra_diagnostic_q2")
    require((d["episodes"], d["exact_optimal"], d["covered_targets"],
             s["episodes"], s["exact_optimal"], s["covered_targets"]) == (20, 8, 106, 20, 4, 100),
            "Astra paired result differs")
    paired.append({"id": "astra_diagnostic", "episode_ids": sorted(x["episode_id"] for x in diag["direct"]["per_item"]),
                   "direct": d, "target_wise_q2": s})
    e = eps["MLP4B_0003"]
    initial, improved = ["C05", "C08", "C16"], ["C05", "C13", "C16"]
    by_candidate = {c: sorted(t for t, support in e["supports"].items() if c in support)
                    for c in set(initial + improved)}
    require(by_candidate == {"C05": ["T01", "T08"], "C08": ["T04", "T08"],
                             "C13": ["T02", "T06"], "C16": ["T05", "T07"]}, "Biproduct supports")
    for sid in ("gpt_sol_5_6_pro", "gpt_sol_5_6_xhigh"):
        actual = next(x for x in grouped[sid] if x["episode_id"] == "MLP4B_0003")
        require(actual["selected"] == initial, "Biproduct saved selection differs")
    require(coverage(initial, e["supports"]) == 5 and coverage(improved, e["supports"]) == e["maximum"] == 6,
            "Biproduct improvement differs")
    return {"schema_version": "lemma-portfolio.submission-results.v1", "development_episodes": 30,
            "test_episodes": 60, "portfolios_per_episode": 560, "test_optimal_portfolios": 78,
            "test_maximum_histogram": {"6": 45, "7": 15}, "uniform_random": random,
            "direct_rows": rows, "paired_target_wise": paired,
            "one_target_short": {"answers": 163, "minimum_replacements": {str(k): v for k, v in sorted(distances.items())},
                                 "optimal_single_swap_neighbors": {str(k): v for k, v in sorted(neighbors.items())}},
            "biproduct_example": {"episode_id": "MLP4B_0003", "candidate_targets": by_candidate,
                                  "initial": initial, "improved": improved}}


def markdown(data):
    lines = ["# Results accompanying the paper", "",
             "All direct model rows use the same 60 test episodes. Missing or malformed answers",
             "receive zero and stay in the denominators. The two additional scores defined in",
             "the technical supplement are reported below as percentages:", "",
             "- Share of maximum coverage: mean of achieved coverage / episode maximum.",
             "- Occurrence recall: selected recorded candidate-target pairs / all recorded pairs,",
             "  pooled over the evaluated episodes (814 pairs in the complete test set).", "",
             "Run `python3 -B verify_results.py` to recompute and check both this table and",
             "`results/paper_results.json`. The full verification also rebuilds the original",
             "response transcriptions and independently scores the raw follow-up answers.", "",
             "| Model / baseline | Optimal /60 | Mean coverage /8 | Valid /60 | Share of maximum (%) | Occurrence recall (%) |",
             "|---|---:|---:|---:|---:|---:|"]
    r = data["uniform_random"]
    lines.append(f"| Uniform random (expectation) | {r['expected_optimal_answers']:.2f} | {r['expected_mean_coverage']:.2f} | 60 | {r['share_of_maximum_coverage_percent']:.2f} | {r['occurrence_recall_percent']:.2f} |")
    for r in data["direct_rows"]:
        lines.append(f"| {r['label']} | {r['exact_optimal']} | {r['mean_coverage']:.2f} | {r['valid']} | {r['share_of_maximum_coverage_percent']:.2f} | {r['occurrence_recall_percent']:.2f} |")
    lines += ["", "The uniform-random row is an exact expectation over all 560 portfolios, not",
              "a sampled response set. The saved deterministic hash draw in the original",
              "results is a different baseline and is not the random row in the paper.", "",
              "## Paired target-wise comparison", "",
              "Target-wise selection retains the first two predictions per target, then chooses",
              "three candidates from all sixteen by maximizing predicted coverage. Predicted",
              "ties use candidate-ID order. True annotations are used only for scoring.", "",
              "| Response set | Paired episodes | Direct optima | Target-wise optima | Direct mean coverage | Target-wise mean coverage |",
              "|---|---:|---:|---:|---:|---:|"]
    for p in data["paired_target_wise"]:
        d, s = p["direct"], p["target_wise_q2"]
        lines.append(f"| {p['id']} | {d['episodes']} | {d['exact_optimal']} | {s['exact_optimal']} | {d['mean_coverage']:.2f} | {s['mean_coverage']:.2f} |")
    lines += ["", "The JSON also gives both additional scores and the exact paired episode IDs.",
              "Pro has only 15 complete pairs; its fixed 20-ID scores remain in the original",
              "results with the five missing direct answers scored zero. These are not the",
              "full 60-episode direct results.", "",
              "## Coverage shortfall and candidate replacements", "",
              "Across the seven follow-up runs, 163 answers are exactly one target short.",
              "Reaching an optimum requires one replacement for 134, two for 26, and three",
              "for 3. Of each portfolio's 39 single-replacement neighbors, the number that",
              "is optimal is zero for 29 answers, one for 122, two for 10, and three for 2.",
              "These are repeated responses on the same episodes and retrospective checks",
              "using the true labels, not results of a model repair experiment. Per-answer",
              "records are in `descriptive/one_short_replacement_audit.json`.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="regenerate the two derived result files")
    args = parser.parse_args()
    data = calculate()
    target = ROOT / "results/paper_results.json"
    table = ROOT / "RESULTS.md"
    if args.write:
        target.parent.mkdir(exist_ok=True)
        target.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        table.write_text(markdown(data), encoding="utf-8")
        print("Wrote derived results; refresh inventories before running the full verification.")
    else:
        same(data, read(target), "Consolidated paper results")
        require(table.read_text(encoding="utf-8") == markdown(data), "RESULTS.md differs")
        print("PASS all 90 optimum sets, 13 model rows, both baselines and additional scores,")
        print("paired comparisons, replacement counts, and the biproduct example.")


if __name__ == "__main__":
    main()
