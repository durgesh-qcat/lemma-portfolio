"""Independent arithmetic checks; never imports the release scorer or changes data."""
from collections import Counter, defaultdict
from fractions import Fraction
from itertools import combinations
from pathlib import Path
import argparse
import hashlib
import json
import math
import re

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('release_root',nargs='?',type=Path,default=Path(__file__).resolve().parents[1])
ROOT=parser.parse_args().release_root
REPORT = {'method': 'Independent coverage enumeration, sequential greedy tie-branch enumeration with exact rational probabilities, separate subset-state dynamic-programming check, and independent TF-IDF rebuild. No model inference or Lean re-extraction.'}
REPORT['input_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [*(ROOT/'data').glob('*.jsonl'),ROOT/'responses/direct_transcription.json',ROOT/'results/baseline_predictions.json',ROOT/'results/scores.json']}

def read_json(path):
    return json.loads((ROOT / path).read_text())

def rows(path):
    return [json.loads(line) for line in (ROOT / path).read_text().splitlines() if line]

def cov(chosen, edges):
    return sum(not set(chosen).isdisjoint(edge) for edge in edges)

def target_tokens(statement):
    token_regex=r"[A-Za-z_\u0080-\uffff][A-Za-z0-9_\u0080-\uffff'.]*"
    stop={'Type','inst','fun','forall','Prop','Sort','true','false'}
    return {p.lower() for t in re.findall(token_regex,statement) for p in t.strip(".'").split('.') if p and p not in stop}

def greedy_paths(ids, edges, prefix=(), probability=Fraction(1)):
    if len(prefix) == 3:
        return [(prefix, cov(prefix, edges), probability)]
    candidates = [c for c in ids if c not in prefix]
    values = {c: cov((*prefix, c), edges) for c in candidates}
    best = max(values.values())
    tied = [c for c in candidates if values[c] == best]
    return [result for c in tied for result in greedy_paths(ids, edges, (*prefix,c), probability / len(tied))]

def greedy_subset_probabilities(ids, edges):
    # A separate computation: aggregate probability mass at unordered subsets,
    # using target bitmasks and marginal newly covered targets, not cov().
    masks = [sum(1 << t for t, edge in enumerate(edges) if c in edge) for c in ids]
    states = {0:Fraction(1)}
    for _ in range(3):
        next_states = defaultdict(Fraction)
        for chosen,p in states.items():
            covered = 0
            for c in range(16):
                if chosen & (1 << c):
                    covered |= masks[c]
            gains = {c:(masks[c] & ~covered).bit_count() for c in range(16) if not chosen & (1 << c)}
            maximum = max(gains.values())
            ties = [c for c,gain in gains.items() if gain==maximum]
            for c in ties:
                next_states[chosen | (1 << c)] += p/len(ties)
        states=next_states
    histogram=defaultdict(Fraction)
    for chosen,p in states.items():
        covered=0
        for c in range(16):
            if chosen & (1 << c):
                covered |= masks[c]
        histogram[covered.bit_count()] += p
    return dict(histogram)

all_data = {}
for split in ('development','test'):
    public = {p['episode_id']: p for p in rows(f'data/{split}.public.jsonl')}
    labels = {p['episode_id']: p for p in rows(f'data/{split}.labels.jsonl')}
    all_data[split] = (public,labels)
    greedy_any_optimal = []
    frequency_any_optimal = []
    greedy_summary = []
    expected = Counter()
    optimal_hist = Counter()
    near_total = 0
    all_target_names = []
    for episode_id, lab in labels.items():
        ids = [c['id'] for c in public[episode_id]['candidates']]
        edges = [set(t['direct_candidates']) for t in lab['targets']]
        assert len(ids)==16 and len(set(ids))==16 and len(edges)==8
        triples = [(p,cov(p,edges)) for p in combinations(sorted(ids),3)]
        hist = Counter(v for p,v in triples)
        maximum = max(hist)
        optima = [p for p,v in triples if v==maximum]
        assert maximum == lab['optimal_coverage']
        assert set(optima) == {tuple(p) for p in lab['optimal_portfolios']}
        assert hist == {int(k):v for k,v in lab['coverage_histogram'].items()}
        optimal_hist[maximum] += 1
        counts = {c:sum(c in e for e in edges) for c in ids}
        assert counts == lab['candidate_displayed_use_counts']
        active = {c for c,n in counts.items() if n}
        union = set().union(*(set(p) for p in optima))
        assert all(edges) and len(active)>=7 and len(active-union)>=4
        assert sum(len(e)>=2 for e in edges)>=2 and max(counts.values())<=4
        assert all(counts[c]>=2 for c in union)
        assert all(cov(set(p)-{c},edges)<maximum for p in optima for c in p)
        assert hist[maximum-1]>=2 and maximum>=6 and len(optima)<=32
        assert min(lab['candidate_recurrent_corpus_use_counts'].values())>=2
        token_sets=[target_tokens(t['statement']) for t in public[episode_id]['targets']]
        similarity=sum((Fraction(len(a&b),len(a|b)) if a|b else Fraction() for a,b in combinations(token_sets,2)),Fraction())/28
        assert similarity<=Fraction(3,5)
        assert len(lab['construction_gate_predictions'])==20
        assert all(cov(p,edges)<maximum for p in lab['construction_gate_predictions'].values())
        enumerated_expected = Fraction(sum(v for p,v in triples),560)
        formula_expected = sum((1-Fraction(math.comb(16-len(e),3),560) for e in edges),Fraction())
        assert formula_expected == enumerated_expected
        expected['coverage'] += enumerated_expected
        expected['normalized'] += enumerated_expected/maximum
        expected['optimal'] += Fraction(len(optima),560)
        expected['within_one'] += Fraction(hist[maximum]+hist[maximum-1],560)
        near_total += hist[maximum]+hist[maximum-1]
        paths = greedy_paths(ids,edges)
        path_prob = defaultdict(Fraction)
        for path,value,prob in paths:
            path_prob[value] += prob
        assert sum(path_prob.values())==1
        assert dict(path_prob) == greedy_subset_probabilities(ids,edges)
        first=[]
        last=[]
        for _ in range(3):
            first.append(max((c for c in ids if c not in first),key=lambda c:cov([*first,c],edges)))
            last.append(max((c for c in reversed(ids) if c not in last),key=lambda c:cov([*last,c],edges)))
        assert set(first)==set(lab['construction_gate_predictions']['true_greedy_set_cover'])
        expected['reverse_display_greedy_optimal'] += Fraction(int(cov(last,edges)==maximum))
        expected['reverse_display_greedy_coverage'] += Fraction(cov(last,edges))
        if maximum in path_prob:
            greedy_any_optimal.append(episode_id)
        expected['random_tie_greedy_optimal'] += path_prob.get(maximum,Fraction())
        expected['random_tie_greedy_coverage'] += sum(v*p for v,p in path_prob.items())
        greedy_summary.append({'episode_id':episode_id,'optimum':maximum,'fixed_greedy':cov(lab['construction_gate_predictions']['true_greedy_set_cover'],edges),'reverse_display_greedy':cov(last,edges),'possible_scores':sorted(path_prob),'random_tie_coverage_probabilities':{str(v):str(p) for v,p in sorted(path_prob.items())},'random_tie_optimal_probability':float(path_prob.get(maximum,Fraction())),'paths':len(paths)})
        cutoff = sorted(counts.values(),reverse=True)[2]
        high = {c for c,n in counts.items() if n>cutoff}
        tied = [c for c,n in counts.items() if n==cutoff]
        freq_sets = [high|set(p) for p in combinations(tied,3-len(high))]
        freq_optimal=sum(cov(p,edges)==maximum for p in freq_sets)
        expected['uniform_boundary_tie_frequency_optimal'] += Fraction(freq_optimal,len(freq_sets))
        if freq_optimal:
            frequency_any_optimal.append(episode_id)
        all_target_names.extend(lab['target_sources'].values())
    REPORT[split]={'episodes':len(labels),'all_numeric_structural_filters_pass':True,'optimal_coverage_histogram':dict(optimal_hist),'total_optimal_portfolios':int(expected['optimal']*560),'analytic':{k:{'fraction':str(v),'value':float(v)} for k,v in expected.items()},'means':{k:{'fraction':str(v/len(labels)),'value':float(v/len(labels))} for k,v in expected.items()},'greedy_optimal_under_some_tie_paths':len(greedy_any_optimal),'greedy_always_suboptimal_ids':[eid for eid in labels if eid not in greedy_any_optimal],'frequency_optimal_under_some_tie_paths':len(frequency_any_optimal),'greedy_possible_score_histogram':dict(Counter(','.join(map(str,r['possible_scores'])) for r in greedy_summary)),'greedy_details':greedy_summary,'source_names_ending_assoc':[n for n in all_target_names if n.endswith('_assoc')]}

public, labels = all_data['test']
assert set(lab['source_module'] for lab in labels.values()).isdisjoint(lab['source_module'] for lab in all_data['development'][1].values())
predictions = {k:v['predictions'] for k,v in read_json('responses/direct_transcription.json').items()}
predictions.update(read_json('results/baseline_predictions.json'))
reported = {r['system_id']:r for r in read_json('results/scores.json')['rows']}
model_results=[]
for system,answers in predictions.items():
    count=Counter()
    normalized=Fraction()
    for episode_id,lab in labels.items():
        ids=set(lab['candidate_sources'])
        chosen=answers.get(episode_id)
        edges=[set(t['direct_candidates']) for t in lab['targets']]
        count['hidden_edges'] += sum(map(len,edges))
        valid = isinstance(chosen,list) and len(chosen)==3 and len(set(chosen))==3 and set(chosen)<=ids
        if not valid:
            continue
        count['valid']+=1
        coverage=cov(chosen,edges)
        count['coverage']+=coverage
        count['optimal']+=coverage==lab['optimal_coverage']
        count['within_one']+=coverage>=lab['optimal_coverage']-1
        count['selected_edges']+=sum(len(set(chosen)&e) for e in edges)
        normalized+=Fraction(coverage,lab['optimal_coverage'])
    r=reported[system]
    assert (count['valid'],count['coverage'],count['optimal'])==(r['valid'],r['achieved_target_coverage'],r['exact_optimal'])
    assert math.isclose(100*float(normalized/60),r['mean_oracle_normalized_coverage_percentage'])
    assert math.isclose(100*count['selected_edges']/count['hidden_edges'],r['selected_edge_recall_percentage'])
    model_results.append({'system':system,**count})
REPORT['independent_model_rescoring']=model_results

tfidf_mismatches=[]
for episode_id,item in public.items():
    texts=[c['statement'] for c in item['candidates']]+[t['statement'] for t in item['targets']]
    counts=[Counter(text[i:i+n] for n in (3,4,5) for i in range(len(text)-n+1)) for text in texts]
    vocab=set().union(*(set(c) for c in counts))
    idf={token:1+math.log(25/(1+sum(token in c for c in counts))) for token in vocab}
    vectors=[]
    for c in counts:
        weighted={token:(1+math.log(n))*idf[token] for token,n in c.items()}
        length=math.sqrt(math.fsum(v*v for v in weighted.values()))
        vectors.append({token:v/length for token,v in weighted.items()} if length else {})
    sim=[[math.fsum(v*target.get(token,0) for token,v in candidate.items()) for candidate in vectors[:16]] for target in vectors[16:]]
    options=list(combinations(range(16),3))
    best=max(options,key=lambda p:math.fsum(max(target[c] for c in p) for target in sim))
    answer=[item['candidates'][c]['id'] for c in best]
    if answer != predictions['public_text_char_tfidf_facility'][episode_id]:
        tfidf_mismatches.append(episode_id)
assert not tfidf_mismatches
REPORT['tfidf_independent_rebuild_mismatches']=tfidf_mismatches
print(json.dumps(REPORT,sort_keys=True,indent=2))
