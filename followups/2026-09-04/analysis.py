"""Offline analysis functions from the captured follow-up analysis; no inference."""
from collections import Counter
from itertools import combinations
from pathlib import Path
import statistics
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import score_release as release
import score_predictions as direct
import score_support_predictions as support

def interval(deltas, denominator):
    distribution = Counter({0: 1})
    for _ in deltas:
        updated = Counter()
        for subtotal, count in distribution.items():
            for delta in deltas:
                updated[subtotal + delta] += count
        distribution = updated
    total = len(deltas) ** len(deltas)
    def quantile(q):
        cumulative = 0
        for value, count in sorted(distribution.items()):
            cumulative += count
            if cumulative >= q * total:
                return 100 * value / denominator
    return [quantile(.025), quantile(.975)]

def comparison(a, b):
    aa = {r['episode_id']: r for r in a['per_item']}
    bb = {r['episode_id']: r for r in b['per_item']}
    assert set(aa) == set(bb)
    exact, coverage = Counter(), Counter()
    for eid, row in aa.items():
        exact[row['block_id']] += int(row['optimal']) - int(bb[eid]['optimal'])
        coverage[row['block_id']] += row['coverage'] - bb[eid]['coverage']
    return {'a': a['summary']['display_label'], 'b': b['summary']['display_label'], 'n': len(aa),
            'exact_delta_pp': 100 * sum(exact.values()) / len(aa),
            'coverage_delta_pp': 100 * sum(coverage.values()) / (8 * len(aa)),
            'exact_paired_block_bootstrap_95_pp': interval(list(exact.values()), len(aa)),
            'coverage_paired_block_bootstrap_95_pp': interval(list(coverage.values()), 8 * len(aa)),
            'a_only_optimal': sum(r['optimal'] and not bb[eid]['optimal'] for eid, r in aa.items()),
            'b_only_optimal': sum(not r['optimal'] and bb[eid]['optimal'] for eid, r in aa.items()),
            'note': 'Resamples prompt blocks, not independent model repetitions. Small-sample descriptive uncertainty; not corrected for multiple comparisons.'}

def sweep(values, system_id, display, public, labels, ids):
    output = []
    for q in range(1, 5):
        predictions, counts, diagnostics = {}, [0, 0, 0], []
        for eid in ids:
            value = values.get(eid)
            valid = support.valid_support_value(value, public[eid]['target_ids'], set(public[eid]['candidate_ids']))
            if not valid:
                predictions[eid] = None
                value = {t: [] for t in public[eid]['target_ids']}
            else:
                predictions[eid] = release.solve_support(public[eid]['candidate_ids'], value, q)
                portfolios = list(combinations(sorted(public[eid]['candidate_ids']), 3))
                predicted_scores = [sum(bool(set(p) & set(ranks[:q])) for ranks in value.values()) for p in portfolios]
                predicted_best = max(predicted_scores)
                ties = [p for p, score in zip(portfolios, predicted_scores) if score == predicted_best]
                assert list(ties[0]) == predictions[eid], 'Independent enumeration disagrees with release optimizer'
                true_scores = [sum(bool(set(p) & deps) for deps in labels[eid]['dependencies'].values()) for p in ties]
                diagnostics.append({'episode_id': eid, 'tie_count': len(ties), 'predicted_max_coverage': predicted_best,
                                    'lex_chosen_true_coverage': true_scores[0], 'min_true_coverage_among_ties': min(true_scores),
                                    'max_true_coverage_among_ties': max(true_scores),
                                    'mean_true_coverage_among_ties': statistics.mean(true_scores),
                                    'contains_true_optimum': max(true_scores) == labels[eid]['optimal_coverage'],
                                    'uniform_tie_exact_probability': sum(s == labels[eid]['optimal_coverage'] for s in true_scores) / len(ties)})
            for j, count in enumerate(release.incidence_counts(value, labels[eid]['dependencies'], q)):
                counts[j] += count
        summary, per_item = release.score_predictions(f'{system_id}_q{q}', f'{display} support q={q}', predictions, public, labels, ids)
        tie_summary = {'valid_episodes': len(diagnostics),
                       'episodes_with_multiple_predicted_optima': sum(r['tie_count'] > 1 for r in diagnostics),
                       'mean_predicted_optimum_tie_count': statistics.mean(r['tie_count'] for r in diagnostics) if diagnostics else 0,
                       'episodes_with_a_true_optimum_among_predicted_ties': sum(r['contains_true_optimum'] for r in diagnostics),
                       'expected_exact_count_under_uniform_predicted_tie_break': sum(r['uniform_tie_exact_probability'] for r in diagnostics),
                       'expected_total_coverage_under_uniform_predicted_tie_break': sum(r['mean_true_coverage_among_ties'] for r in diagnostics),
                       'note': 'Offline diagnostic only. All reported pipeline selections use original lexicographic tie break; true labels never select a portfolio.'}
        output.append({'q': q, 'summary': summary, 'support_edges': support._edge_summary(counts),
                       'tie_summary': tie_summary, 'tie_per_item': diagnostics, 'per_item': per_item})
    return output
