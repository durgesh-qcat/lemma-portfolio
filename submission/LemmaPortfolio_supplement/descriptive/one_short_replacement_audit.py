#!/usr/bin/env python3
"""Describe optimal-portfolio distances for frozen one-target-short answers.

No inference or repair rule is run. True labels are used retrospectively to
measure distances from saved answers, not to select improved model outputs.
The script is read-only and prints a deterministic JSON report to stdout.
"""

from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
import hashlib
from itertools import combinations
import json
from pathlib import Path
import statistics
from typing import Any


PUBLIC_SHA256 = "b54293b08bc7ddbb7110a50908049922f7cfd86f14cb49a4de4e28353aecc6d8"
LABELS_SHA256 = "d17c1fd5c6d87635daf8035fe4a0918d1eaa29708eae37cb797cae08c19ef887"
SOURCE_COMMIT = "83360eb6a43e1239af7eec4ad45b6e9f7ab7dbe5"
PHASES = (
    "astra_xhigh_r1_prior", "astra_xhigh_r2", "astra_max_r1",
    "sol_xhigh_r1", "sol_xhigh_r2",
    "claude_fable_5_xhigh_r1", "claude_fable_5_1_xhigh_ctx_r1",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def duplicate_safe(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=duplicate_safe)


def jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line, object_pairs_hook=duplicate_safe)
            for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def valid_selection(value: Any, allowed: set[str]) -> bool:
    return (isinstance(value, list) and len(value) == 3
            and all(isinstance(c, str) for c in value)
            and len(set(value)) == 3 and set(value) <= allowed)


def coverage(selected: set[str], label: dict[str, Any]) -> int:
    return sum(bool(selected & set(t["direct_candidates"])) for t in label["targets"])


def summarize_distances(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    distances = Counter(row["minimum_replacements_to_any_optimum"] for row in rows)
    neighbors = [row["optimal_one_swap_neighbor_count"] for row in rows]
    mean = Fraction(sum(neighbors), n) if n else Fraction()
    return {
        "exactly_one_target_short_count": n,
        "minimum_replacement_histogram": {str(d): distances[d] for d in (1, 2, 3)},
        "one_swap_reachable_count": distances[1],
        "one_swap_reachable_percentage_of_one_short": 100 * distances[1] / n if n else None,
        "optimal_one_swap_neighbor_histogram": {str(k): v for k, v in sorted(Counter(neighbors).items())},
        "optimal_one_swap_neighbors_total": sum(neighbors),
        "optimal_one_swap_neighbors_mean": float(mean),
        "optimal_one_swap_neighbors_mean_fraction": str(mean),
        "optimal_one_swap_neighbors_median": statistics.median(neighbors) if neighbors else None,
        "optimal_one_swap_neighbors_min": min(neighbors) if neighbors else None,
        "optimal_one_swap_neighbors_max": max(neighbors) if neighbors else None,
        "distinct_episode_ids_in_subset": len({row["episode_id"] for row in rows}),
    }


def run(root: Path) -> dict[str, Any]:
    public_path, label_path = root / "data/test.public.jsonl", root / "data/test.labels.jsonl"
    assert sha(public_path) == PUBLIC_SHA256 and sha(label_path) == LABELS_SHA256
    public = {r["episode_id"]: r for r in jsonl(public_path)}
    labels = {r["episode_id"]: r for r in jsonl(label_path)}
    assert len(public) == len(labels) == 60 and set(public) == set(labels)
    optima = {}
    allowed = {}
    for eid, item in public.items():
        allowed[eid] = {c["id"] for c in item["candidates"]}
        assert len(allowed[eid]) == 16 and len(item["targets"]) == 8
        scored = [(coverage(set(p), labels[eid]), p)
                  for p in combinations(sorted(allowed[eid]), 3)]
        assert len(scored) == 560
        best = max(score for score, _ in scored)
        assert best == labels[eid]["optimal_coverage"]
        best_triples = [p for score, p in scored if score == best]
        assert [list(p) for p in best_triples] == labels[eid]["optimal_portfolios"]
        optima[eid] = set(best_triples)
    sources = [public_path, label_path]
    reports = []
    pooled_rows = []
    for phase in PHASES:
        phase_root = root / "followups/2026-09-05" / phase
        score_path = phase_root / "score.json"
        saved = read(score_path)
        source_rows = {row["episode_id"]: row for row in saved["per_item"]}
        assert set(source_rows) == set(public) and len(saved["per_item"]) == 60
        raw = {}
        response_paths = sorted((phase_root / "responses").glob("*.json"))
        assert len(response_paths) == 12
        for path in response_paths:
            predictions = read(path)["predictions"]
            assert len(predictions) == 5 and not set(predictions) & set(raw)
            raw.update(predictions)
        assert set(raw) == set(public)
        sources.extend([score_path, *response_paths])
        count_valid = count_exact = count_within_one = total_coverage = 0
        rows = []
        for eid in public:
            submitted = raw[eid]
            valid = valid_selection(submitted, allowed[eid])
            selected = set(submitted) if valid else set()
            achieved = coverage(selected, labels[eid])
            best = labels[eid]["optimal_coverage"]
            exact = valid and achieved == best
            expected = source_rows[eid]
            assert expected["selected"] == (sorted(selected) if valid else None)
            assert expected["valid"] == valid and expected["coverage"] == achieved
            assert expected["optimal"] == exact and expected["optimal_coverage"] == best
            count_valid += valid
            count_exact += exact
            count_within_one += valid and achieved >= best - 1
            total_coverage += achieved
            if not valid or achieved != best - 1:
                continue
            # A replacement removes one of three selected candidates and adds
            # one of the thirteen unselected candidates: 3 * 13 = 39 neighbors.
            neighbors = {tuple(sorted((selected - {drop}) | {add}))
                         for drop in selected for add in allowed[eid] - selected}
            assert len(neighbors) == 39
            assert all(len(selected - set(p)) == 1 for p in neighbors)
            optimal_neighbors = neighbors & optima[eid]
            minimum = min(3 - len(selected & set(p)) for p in optima[eid])
            assert 1 <= minimum <= 3
            assert (minimum == 1) == bool(optimal_neighbors)
            # Verify the combinatorial membership calculation by true scoring.
            assert len(optimal_neighbors) == sum(coverage(set(p), labels[eid]) == best for p in neighbors)
            rows.append({
                "phase": phase, "episode_id": eid, "selected": sorted(selected),
                "coverage": achieved, "optimal_coverage": best, "target_shortfall": 1,
                "minimum_replacements_to_any_optimum": minimum,
                "one_swap_neighbor_count": len(neighbors),
                "optimal_one_swap_neighbor_count": len(optimal_neighbors),
                "total_true_optimal_portfolios": len(optima[eid]),
            })
        assert count_exact == saved["summary"]["exact_optimal"]
        assert count_valid == saved["summary"]["valid"] == 60
        assert total_coverage == saved["summary"]["achieved_target_coverage"]
        assert len(rows) == count_within_one - count_exact
        reports.append({
            "phase": phase, "display_label": saved["summary"]["display_label"],
            "test_episode_count": 60, "valid": count_valid, "exact_optimal": count_exact,
            "within_one_including_exact": count_within_one,
            "more_than_one_target_short": 60 - count_within_one,
            "achieved_target_coverage": total_coverage, "target_count": 480,
            "distance_summary": summarize_distances(rows), "one_short_per_item": rows,
        })
        pooled_rows.extend(rows)
    pooled = summarize_distances(pooled_rows)
    pooled.update({
        "number_of_runs": len(reports), "response_instance_denominator": 60 * len(reports),
        "unique_benchmark_episode_denominator": 60,
        "exact_optimal_response_instances": sum(r["exact_optimal"] for r in reports),
        "within_one_response_instances_including_exact": sum(r["within_one_including_exact"] for r in reports),
        "more_than_one_target_short_response_instances": sum(r["more_than_one_target_short"] for r in reports),
        "aggregation_caution": "Descriptive pooling of seven saved runs on the same 60 episodes; these are repeated response instances, not 420 independent benchmark problems or a representative model sample.",
    })
    return {
        "schema_version": "lemma-portfolio.one-short-replacement-audit.v1",
        "source_commit": SOURCE_COMMIT,
        "script_sha256": sha(Path(__file__)),
        "source_sha256": {p.relative_to(root).as_posix(): sha(p) for p in sources},
        "new_inference_calls": 0, "changed_selection_rules": False,
        "definition": "Analyze only valid saved triples with true coverage exactly one below the episode maximum. Replacement distance is 3 minus the largest intersection with any true optimal triple. The 39 one-swap neighbors replace one selected candidate by one unselected candidate.",
        "interpretation": "Retrospective, true-label-assisted diagnosis of existing answers. An optimal neighbor's existence does not show that a model can identify the replacement, repair its answer, or attain the oracle score. Within-one is the existing post-hoc coverage diagnostic and includes exact optima only where explicitly stated.",
        "runs": reports, "pooled_response_instances": pooled,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path,
                        default=Path(__file__).resolve().parents[1] / "repo")
    args = parser.parse_args()
    print(json.dumps(run(args.repo_root.resolve()), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
