"""Independent, read-only arithmetic and predicted-tie audit."""
import argparse
import collections
import itertools
import json
from fractions import Fraction
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    'release_root',
    nargs='?',
    type=Path,
    default=Path(__file__).resolve().parents[1],
    help='Release directory containing data, responses, and results (default: parent of tools).',
)
ROOT = parser.parse_args().release_root
labels = {x['episode_id']: x for x in map(json.loads, (ROOT/'data/test.labels.jsonl').read_text().splitlines())}
details = list(map(json.loads, (ROOT/'results/per_item.jsonl').read_text().splitlines()))
support = json.loads((ROOT/'responses/support_transcription.json').read_text())
direct = json.loads((ROOT/'responses/direct_transcription.json').read_text())
all_triples = list(itertools.combinations([f'C{i:02}' for i in range(1,17)],3))

def actual(eid, triple):
    chosen=set(triple or [])
    deps=[set(t['direct_candidates']) for t in labels[eid]['targets']]
    return sum(bool(chosen & d) for d in deps),sum(len(chosen & d) for d in deps)

summary={}
report={'scores':summary,'predicted_optimizer_audit':{},'incidence':[]}
for row in details:
    cv,edge=actual(row['episode_id'],row['selected'])
    assert (cv,edge)==(row['coverage'],row['selected_edges'])
    assert row['optimal']==(cv==labels[row['episode_id']]['optimal_coverage'])
for sys in sorted({r['system_id'] for r in details}):
    rows=[r for r in details if r['system_id']==sys]
    summary[sys]={
        'n':len(rows), 'valid':sum(r['valid'] for r in rows),
        'exact':sum(r['optimal'] for r in rows),
        'within_one':sum(r['valid'] and r['coverage']>=r['optimal_coverage']-1 for r in rows),
        'coverage':sum(r['coverage'] for r in rows),
        'selected_edges':sum(r['selected_edges'] for r in rows),
        'all_edges':sum(r['hidden_edges'] for r in rows),
        'mean_ratios_pct':100*sum(r['coverage']/r['optimal_coverage'] for r in rows)/len(rows),
        'ratio_sums_pct':100*sum(r['coverage'] for r in rows)/sum(r['optimal_coverage'] for r in rows),
        'recall_pct':100*sum(r['selected_edges'] for r in rows)/sum(r['hidden_edges'] for r in rows),
        'coverage_hist':dict(sorted(collections.Counter(r['coverage'] for r in rows).items())),
        'shortfall_hist':dict(sorted(collections.Counter(r['optimal_coverage']-r['coverage'] for r in rows).items())),
    }

for sys,episodes in support.items():
    tie_rows=[]
    for eid,targets in episodes.items():
        predicted={t:set(v[:2]) for t,v in targets.items()}
        predicted_scores=[sum(bool(set(p)&s) for s in predicted.values()) for p in all_triples]
        best=max(predicted_scores)
        ties=[p for p,score in zip(all_triples,predicted_scores) if score==best]
        cvs=[actual(eid,p)[0] for p in ties]
        recorded=next(r for r in details if r['system_id']==sys+'_support_q2' and r['episode_id']==eid)
        assert list(ties[0])==recorded['selected']
        assert cvs[0]==recorded['coverage']
        oracle=labels[eid]['optimal_coverage']
        submitted=direct[sys]['predictions'].get(eid)
        dcov=actual(eid,submitted)[0]
        tie_rows.append({
            'episode_id':eid,'ties':len(ties),'predicted_max':best,
            'lexicographic_choice':list(ties[0]),
            'actual_chosen':cvs[0],'actual_oracle':oracle,
            'true_optima_retained':sum(c==oracle for c in cvs),
            'actual_tie_min':min(cvs),'actual_tie_max':max(cvs),
            'uniform_tie_expected_coverage':sum(cvs)/len(cvs),
            'uniform_tie_optimal_probability':sum(c==oracle for c in cvs)/len(cvs),
            'direct_valid':submitted is not None,'direct_coverage':dcov,
        })
    matched=[r for r in tie_rows if r['direct_valid']]
    def aggregates(rs):
        return {
            'n':len(rs),'direct_coverage':sum(r['direct_coverage'] for r in rs),
            'selected_coverage':sum(r['actual_chosen'] for r in rs),
            'selected_exact':sum(r['actual_chosen']==r['actual_oracle'] for r in rs),
            'direct_exact':sum(r['direct_coverage']==r['actual_oracle'] for r in rs),
            'selected_within_one':sum(r['actual_chosen']>=r['actual_oracle']-1 for r in rs),
            'direct_within_one':sum(r['direct_coverage']>=r['actual_oracle']-1 for r in rs),
            'episodes_with_ties':sum(r['ties']>1 for r in rs),
            'episodes_with_optimum_among_ties':sum(r['true_optima_retained']>0 for r in rs),
            'episodes_with_optimum_among_multiple_ties':sum(r['true_optima_retained']>0 and r['ties']>1 for r in rs),
            'episodes_where_all_true_optima_excluded':sum(r['true_optima_retained']==0 for r in rs),
            'best_coverage_if_oracle_ties':sum(r['actual_tie_max'] for r in rs),
            'uniform_tie_expected_coverage':sum(r['uniform_tie_expected_coverage'] for r in rs),
            'uniform_tie_expected_exact':sum(r['uniform_tie_optimal_probability'] for r in rs),
            'uniform_tie_expected_exact_fraction':str(sum((Fraction(r['true_optima_retained'],r['ties']) for r in rs),Fraction(0))),
            'tie_count_min_median_max':[min(r['ties'] for r in rs),sorted(r['ties'] for r in rs)[len(rs)//2],max(r['ties'] for r in rs)],
        }
    report['predicted_optimizer_audit'][sys]={'all':aggregates(tie_rows),'matched':aggregates(matched),'rows':tie_rows}
    for match_only in [False, True]:
        for prefix in [None,2]:
            tp=fp=fn=cap_ceiling=0
            for eid,targets in episodes.items():
                if match_only and eid not in direct[sys]['predictions']:
                    continue
                for t in labels[eid]['targets']:
                    truth=set(t['direct_candidates'])
                    guess=set(targets[t['id']][:prefix])
                    tp+=len(guess&truth)
                    fp+=len(guess-truth)
                    fn+=len(truth-guess)
                    cap_ceiling+=min(len(truth),2)
            report['incidence'].append({'system':sys,'matched':match_only,'prefix':prefix,'tp':tp,'fp':fp,'fn':fn,'precision':tp/(tp+fp),'recall':tp/(tp+fn),'f1':2*tp/(2*tp+fp+fn),'q2_oracle_recall_ceiling':cap_ceiling/(tp+fn)})

expected_exact=expected_within=expected_coverage=expected_normalized=0
edges=0
for eid,label in labels.items():
    cv=[actual(eid,p)[0] for p in all_triples]
    m=max(cv)
    assert m==label['optimal_coverage']
    assert [list(p) for p,c in zip(all_triples,cv) if c==m]==label['optimal_portfolios']
    expected_exact+=sum(c==m for c in cv)/560
    expected_within+=sum(c>=m-1 for c in cv)/560
    expected_coverage+=sum(cv)/560
    expected_normalized+=sum(cv)/560/m
    edges+=sum(len(t['direct_candidates']) for t in label['targets'])
report['uniform_random']={'exact':expected_exact,'within_one':expected_within,'total_coverage':expected_coverage,'mean_coverage':expected_coverage/60,'mean_normalized':expected_normalized/60,'all_edges':edges}
report['interpretation']={
    'oracle_existence_count':'episodes_with_optimum_among_ties counts ALL predicted maximizers, including singleton maximizing sets; this is an upper bound achievable only by an oracle that can use the hidden true labels to break predicted ties.',
    'uniform_tie_expectation':'For each episode, select uniformly from its complete set of predicted maximizers, then sum its true-optimal probability. This is an analytic expectation, not a run, optimized rule, or inference about model quality.',
    'matched':'Matched excludes Pro D12, for which the direct selections are missing. xhigh has all 20 direct answers.',
}
print(json.dumps(report,indent=2,sort_keys=True))
