#!/usr/bin/env python3
"""Re-score all thirteen saved direct-response sets after a fixed masking exclusion.

The excluded IDs come from the preserved source-name-prefix audit, not from
model outcomes. No prompts or responses are modified and no inference is run.
The default is read-only; --write regenerates the two derived result files.
"""

import argparse
from fractions import Fraction
import hashlib
import importlib.util
import json
from math import comb

from verify_followups import ROOT, read, require, same
from verify_results import FOLLOWUP, ORIGINAL, episodes, summarize


def calculate():
    audit_path = ROOT / "original_release/verify_release.py"
    spec = importlib.util.spec_from_file_location("preserved_release_check", audit_path)
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    counts, flagged = audit.check_name_prefix_scan()
    excluded = flagged["test"]
    audit.check_masking_sensitivity(excluded)
    eps = episodes()["test"]
    retained_ids = set(eps) - excluded
    require(len(excluded) == 6 and len(retained_ids) == 54, "Masking subset dimensions")
    source = ROOT / "original_release/results/per_item.jsonl"
    records = [json.loads(line) for line in source.read_text().splitlines() if line.strip()]
    sources = [audit_path, source,
               ROOT / "original_release/data/test.public.jsonl",
               ROOT / "original_release/data/test.labels.jsonl",
               ROOT / "original_release/data/development.public.jsonl",
               ROOT / "original_release/data/development.labels.jsonl"]
    rows = []
    for sid, label, *_ in [("public_text_char_tfidf_facility", "Character TF-IDF")] + ORIGINAL + FOLLOWUP:
        if sid in {row[0] for row in FOLLOWUP}:
            path = ROOT / f"followups/2026-09-05/{sid}/score.json"
            sources.append(path)
            items = read(path)["per_item"]
        else:
            items = [row for row in records if row["system_id"] == sid]
        require(len(items) == 60 and {row["episode_id"] for row in items} == set(eps),
                f"Incomplete source response set: {sid}")
        subset = [row for row in items if row["episode_id"] in retained_ids]
        require(len(subset) == 54, f"Incomplete retained subset: {sid}")
        rows.append(summarize(subset, eps, label, sid))
    exact, covered = Fraction(), Fraction()
    for eid in retained_ids:
        e = eps[eid]
        exact += Fraction(len(e["optima"]), 560)
        covered += sum((1 - Fraction(comb(16 - len(s), 3), 560)
                        for s in e["supports"].values()), Fraction())
    return {
        "schema_version": "lemma-portfolio.masking-sensitivity.v1",
        "scope": "Post-hoc exclusion sensitivity on saved responses; not corrected prompts, new inference, or evidence of no training exposure.",
        "excluded_test_episode_ids": sorted(excluded),
        "retained_test_episode_ids": sorted(retained_ids),
        "name_prefix_scan_counts": {key: list(value) for key, value in counts.items()},
        "oracle_covered_targets": sum(eps[eid]["maximum"] for eid in retained_ids),
        "uniform_random": {"expected_optimal_answers": float(exact),
                           "expected_optimal_answers_fraction": str(exact),
                           "expected_mean_coverage": float(covered / 54),
                           "expected_mean_coverage_fraction": str(covered / 54)},
        "rows": rows,
        "input_sha256": {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in sorted(sources)},
    }


def markdown(data):
    lines = [
        "# Masking-exclusion sensitivity: all thirteen direct-response sets", "",
        data["scope"], "",
        "The preserved name-prefix scan identifies six test episodes. Exclusion is",
        "based on prompt content, not the outcomes of any model. Missing or malformed",
        "answers still receive zero and remain in the retained denominator of 54.", "",
        "Excluded IDs: " + ", ".join(f"\x60{x}\x60" for x in data["excluded_test_episode_ids"]) + ".", "",
        "| Model / baseline | Exact /54 | Coverage /8 | Valid /54 |",
        "|---|---:|---:|---:|",
        f"| Oracle (hidden annotations) | 54 | {data['oracle_covered_targets'] / 54:.2f} | 54 |",
        f"| Uniform random (expectation) | {data['uniform_random']['expected_optimal_answers']:.2f} | {data['uniform_random']['expected_mean_coverage']:.2f} | 54 |",
    ]
    for row in data["rows"]:
        lines.append(f"| {row['label']} | {row['exact_optimal']} | {row['mean_coverage']:.2f} | {row['valid']} |")
    lines += ["", "The original six model rows reproduce the previously archived sensitivity",
              "check. The seven follow-up rows extend that same exclusion to saved answers.",
              "The main 60-episode results are unchanged. No causal masking effect is",
              "estimated: this subset also differs in episode composition.",
              "", "Reproduce with \x60python3 -B verify_masking_sensitivity.py\x60.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    data = calculate()
    target = ROOT / "results/masking_sensitivity.json"
    table = ROOT / "results/masking_sensitivity.md"
    if args.write:
        target.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        table.write_text(markdown(data), encoding="utf-8")
    else:
        same(data, read(target), "All-panel masking sensitivity")
        require(table.read_text(encoding="utf-8") == markdown(data), "Masking table differs")
    print("PASS 54-episode masking sensitivity: 13 model sets, TF-IDF, random and oracle.")
    print("No new inference, prompt changes, or model-response changes.")


if __name__ == "__main__":
    main()
