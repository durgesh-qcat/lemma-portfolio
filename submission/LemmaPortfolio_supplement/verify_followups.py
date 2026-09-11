#!/usr/bin/env python3
"""Independently check archived final-answer arithmetic; no model calls or imports.

This verifies bytes and mathematics, not the identity of a remote serving model,
the inference interface, or omitted operational logs. Python standard library only.
"""

import hashlib
import itertools
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def same(actual, expected, location):
    if isinstance(expected, dict):
        require(isinstance(actual, dict) and actual.keys() == expected.keys(),
                f"Different keys: {location}")
        for key in expected:
            same(actual[key], expected[key], f"{location}/{key}")
    elif isinstance(expected, list):
        require(isinstance(actual, list) and len(actual) == len(expected),
                f"Different lengths: {location}")
        for index, (a, e) in enumerate(zip(actual, expected)):
            same(a, e, f"{location}/{index}")
    elif isinstance(expected, float):
        require(isinstance(actual, (int, float)) and
                math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-10),
                f"Numerical mismatch: {location}")
    else:
        require(actual == expected, f"Value mismatch: {location}")


def load_jsonl(path):
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    require(len({r["episode_id"] for r in rows}) == len(rows), "Duplicate data ID")
    return {r["episode_id"]: r for r in rows}


def count_coverage(portfolio, supports):
    selected = set(portfolio)
    return sum(bool(selected.intersection(support)) for support in supports.values())


def score(predictions, ids, episodes):
    items = []
    for episode_id in ids:
        episode = episodes[episode_id]
        raw = predictions.get(episode_id)
        valid = (isinstance(raw, list) and len(raw) == 3 and
                 all(isinstance(c, str) for c in raw) and len(set(raw)) == 3 and
                 set(raw).issubset(episode["candidates"]))
        require(valid, f"Unexpected invalid answer: {episode_id}")
        selected = sorted(raw)
        coverage = count_coverage(selected, episode["supports"])
        items.append({
            "episode_id": episode_id,
            "selected": selected,
            "valid": valid,
            "optimal": coverage == episode["optimum"],
            "coverage": coverage,
            "optimal_coverage": episode["optimum"],
            "normalized_coverage": coverage / episode["optimum"],
            "selected_edges": sum(len(set(selected).intersection(s))
                                  for s in episode["supports"].values()),
            "hidden_edges": sum(map(len, episode["supports"].values())),
        })
    total = len(items)
    exact = sum(row["optimal"] for row in items)
    covered = sum(row["coverage"] for row in items)
    summary = {
        "exact_optimal": exact,
        "total": total,
        "exact_optimal_percentage": 100 * exact / total,
        "valid": total,
        "valid_percentage": 100.0,
        "achieved_target_coverage": covered,
        "target_count": 8 * total,
        "target_coverage_percentage": 100 * covered / (8 * total),
        "mean_oracle_normalized_coverage_percentage":
            100 * sum(row["normalized_coverage"] for row in items) / total,
        "selected_edge_recall_percentage":
            100 * sum(row["selected_edges"] for row in items) /
            sum(row["hidden_edges"] for row in items),
    }
    return {"summary": summary, "per_item": items}


def read_calls(phase, kind):
    merged = {}
    for call in phase["calls"]:
        if call["kind"] != kind:
            continue
        path = ROOT / call["response"]
        require(sha(path) == call["response_sha256"], "Changed raw final answer")
        prompt = ROOT / call["prompt"]
        require(sha(prompt) == call["prompt_sha256"], "Changed released prompt")
        payload = prompt.read_text().split("<episodes>\n", 1)[1].split("\n</episodes>", 1)[0]
        prompt_ids = [row["episode_id"] for row in json.loads(payload)]
        same(prompt_ids, call["episode_ids"], "Prompt episode mapping")
        envelope = read(path)
        key = "predictions" if kind == "direct" else "predicted_support"
        require(set(envelope) == {key}, "Unexpected final-answer envelope")
        predictions = envelope[key]
        require(set(predictions) == set(prompt_ids), "Answer/prompt episode mismatch")
        require(not (merged.keys() & predictions.keys()), "Duplicate answer ID")
        merged.update(predictions)
    return merged


def verify():
    inventory = ROOT / "SHA256SUMS"
    require(inventory.is_file(), "Missing package inventory")
    if inventory.exists():
        declared = {}
        for line in inventory.read_text().splitlines():
            digest, relative = line.split("  ", 1)
            require(relative not in declared and not relative.startswith("/") and
                    ".." not in Path(relative).parts, "Unsafe or duplicate inventory path")
            declared[relative] = digest
        actual = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*")
                  if p.is_file() and p != inventory and
                  "__pycache__" not in p.relative_to(ROOT).parts and p.suffix != ".pyc"}
        require(actual == set(declared), "Package inventory differs")
        for relative, digest in declared.items():
            require(sha(ROOT / relative) == digest, f"Package hash mismatch: {relative}")
    manifest = read(ROOT / "MANIFEST.json")
    for relative, digest in manifest["preserved_original_files"].items():
        require(sha(ROOT / relative) == digest, f"Historical file changed: {relative}")
    for relative, digest in manifest["data_sha256"].items():
        require(sha(ROOT / relative) == digest, f"Changed data: {relative}")
    public = load_jsonl(ROOT / "original_release/data/test.public.jsonl")
    labels = load_jsonl(ROOT / "original_release/data/test.labels.jsonl")
    require(public.keys() == labels.keys() and len(public) == 60, "Wrong test split")
    episodes = {}
    for episode_id, row in public.items():
        candidates = sorted(c["id"] for c in row["candidates"])
        supports = {t["id"]: set(t["direct_candidates"])
                    for t in labels[episode_id]["targets"]}
        require(len(candidates) == 16 and len(supports) == 8 and
                row["selection_budget"] == 3, "Wrong episode dimensions")
        require(all(s.issubset(candidates) for s in supports.values()), "Unknown true candidate")
        triples = list(itertools.combinations(candidates, 3))
        require(len(triples) == 560, "Wrong enumeration size")
        coverage = [count_coverage(p, supports) for p in triples]
        optimum = max(coverage)
        all_optima = sorted([list(p) for p, c in zip(triples, coverage) if c == optimum])
        require(optimum == labels[episode_id]["optimal_coverage"], "Wrong stored maximum")
        same(all_optima, sorted(labels[episode_id]["optimal_portfolios"]), "All true optima")
        episodes[episode_id] = {"candidates": candidates, "supports": supports,
                                "triples": triples, "optimum": optimum}
    direct_count = 0
    for phase in manifest["phases"]:
        if phase.get("system_context"):
            context = phase["system_context"]
            require(sha(ROOT / context["file"]) == context["sha256"], "Changed system context")
        expected = read(ROOT / phase["score_file"])
        predictions = read_calls(phase, "direct")
        ids = sorted(predictions)
        computed = score(predictions, ids, episodes)
        if phase["kind"] == "direct":
            require(set(ids) == set(public), "Full direct run does not cover all 60 episodes")
            same(computed, expected, phase["id"])
            direct_count += 1
            print(f"PASS {phase['id']}: {computed['summary']['exact_optimal']}/60 exact, "
                  f"{computed['summary']['achieved_target_coverage']}/480 coverage")
            continue
        require(len(ids) == 20, "Diagnostic does not contain 20 episodes")
        same(computed, expected["direct"], "Diagnostic direct")
        support = read_calls(phase, "support")
        require(set(support) == set(ids), "Unmatched diagnostic arms")
        for episode_id, predicted in support.items():
            require(set(predicted) == set(episodes[episode_id]["supports"]), "Wrong support targets")
            for ranking in predicted.values():
                require(isinstance(ranking, list) and len(ranking) <= 4 and
                        all(isinstance(c, str) for c in ranking) and
                        len(set(ranking)) == len(ranking) and
                        set(ranking).issubset(episodes[episode_id]["candidates"]),
                        "Malformed candidate ranking")
        for expected_width in expected["sweep"]:
            width = expected_width["q"]
            chosen = {}
            multiple = contains_true = 0
            total_ties = 0
            expected_exact = expected_coverage = 0.0
            for episode_id in ids:
                episode = episodes[episode_id]
                retained = {t: set(cs[:width]) for t, cs in support[episode_id].items()}
                predicted_values = [count_coverage(p, retained) for p in episode["triples"]]
                maximum = max(predicted_values)
                ties = [p for p, n in zip(episode["triples"], predicted_values) if n == maximum]
                chosen[episode_id] = list(ties[0])  # Lexicographic; no true labels consulted.
                # Only AFTER selection, inspect true labels for offline tie diagnostics.
                true_values = [count_coverage(p, episode["supports"]) for p in ties]
                exact_ties = sum(c == episode["optimum"] for c in true_values)
                multiple += len(ties) > 1
                contains_true += exact_ties > 0
                total_ties += len(ties)
                expected_exact += exact_ties / len(ties)
                expected_coverage += sum(true_values) / len(ties)
            result = score(chosen, ids, episodes)
            result["q"] = width
            result["tie_summary"] = {
                "valid_episodes": len(ids),
                "episodes_with_multiple_predicted_optima": multiple,
                "mean_predicted_optimum_tie_count": total_ties / len(ids),
                "episodes_with_a_true_optimum_among_predicted_ties": contains_true,
                "expected_exact_count_under_uniform_predicted_tie_break": expected_exact,
                "expected_total_coverage_under_uniform_predicted_tie_break": expected_coverage,
            }
            same(result, expected_width, f"Diagnostic q={width}")
            print(f"PASS diagnostic q={width}: {result['summary']['exact_optimal']}/20 exact, "
                  f"{result['summary']['achieved_target_coverage']}/160 coverage")
    require(direct_count == 7, "Expected seven complete direct runs")
    print("ALL FOLLOW-UP MATHEMATICAL CHECKS PASSED; no inference calls were made.")
    print("This does not independently establish inference interfaces or serving provenance.")


if __name__ == "__main__":
    verify()
