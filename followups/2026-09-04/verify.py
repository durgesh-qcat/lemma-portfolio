#!/usr/bin/env python3
"""Read-only, standard-library verification of this completed follow-up snapshot."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from verify_release import equivalent_generated
from tools.verify_historical_baseline import verify_historical_baseline
from analysis import comparison, direct, release, support, sweep


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, description):
    if not condition:
        raise RuntimeError(description)


def same(actual, expected, description):
    require(equivalent_generated(actual, expected), description)


def verify():
    export = read(HERE / 'EXPORT_MANIFEST.json')
    plan = read(HERE / 'PROTOCOL_EXPORT.json')
    combined = read(HERE / 'FOLLOWUP_RESULTS.json')
    for row in export['source_records']:
        require(sha(HERE / row['exported_file']) == row['exported_sha256'],
                f"Export hash mismatch: {row['exported_file']}")
        if not row['transformed']:
            require(row['source_sha256'] == row['exported_sha256'], 'Raw source changed')
    verify_historical_baseline(ROOT, HERE / 'BASE_RELEASE_SHA256SUMS.txt')

    public, labels = release.load_benchmark(ROOT)
    ids = support.expected_support_episode_ids(ROOT, public)
    scores = {}
    for name in export['included_complete_phases']:
        phase = HERE / name
        paths = sorted((phase / 'responses').iterdir())
        frozen = read(phase / 'OUTPUTS_FROZEN.json')
        require({p.name for p in paths} == {r['file'] for r in frozen['responses']},
                f'{name}: response file set mismatch')
        for row in frozen['responses']:
            require(sha(phase / 'responses' / row['file']) == row['sha256'],
                    f"{name}: frozen response changed: {row['file']}")
        receipts = read(phase / 'CALL_RECEIPTS.json')
        require(len(receipts) == len(paths), f'{name}: call count mismatch')
        require(len({r['call'] for r in receipts}) == len(receipts), 'Duplicate call receipt')
        completion = read(phase / 'RUN_COMPLETED.json')
        tokens = Counter()
        for row in receipts:
            require(row['exit_code'] == 0 and not row['timed_out']
                    and row['inference_error_count'] == row['observed_tool_event_count'] == 0,
                    f"{name}: unsuccessful benchmark call {row['call']}")
            response = next(p for p in paths if p.stem == row['call'])
            require(sha(response) == row['response_sha256'], 'Receipt response mismatch')
            if name == 'astra_xhigh_r1_prior':
                prompt = ROOT / 'prompts/DIRECT_PROMPTS' / (row['call'] + '.txt')
            else:
                call = next(c for c in plan['phases'][name] if c['name'] == row['call'])
                prompt = ROOT / call['prompt']
                require(call['prompt_sha256'] == row['prompt_sha256'], 'Protocol prompt mismatch')
            require(sha(prompt) == row['prompt_sha256'], 'Released prompt mismatch')
            for usage in row['usage']:
                tokens.update(usage)
        same([r['usage'] for r in receipts], completion['usage'], 'Completion usage mismatch')
        same(dict(tokens), combined['usage'][name]['tokens'], 'Aggregated usage mismatch')
        same(completion['wall_seconds'], combined['usage'][name]['wall_seconds'], 'Duration mismatch')
        require(abs(sum(r['wall_seconds'] for r in receipts) - completion['wall_seconds']) < 1,
                'Call durations do not sum to the reported duration')

        expected = read(phase / 'score.json')
        if name != 'astra_diagnostic':
            s = expected['summary']
            actual = direct.score_external_predictions(paths, ROOT, system_id=s['system_id'],
                        display_label=s['display_label'], invalid_as_missing=True)
            same(actual, expected, f'{name}: recomputed direct score differs')
            same(actual['summary'], combined['direct_rows'][name], 'Combined direct row differs')
        else:
            dpaths = [p for p in paths if '_direct_' in p.stem]
            spaths = [p for p in paths if '_support_' in p.stem]
            full = direct.score_external_predictions(dpaths, ROOT, system_id=name+'_direct',
                        display_label='Astra xhigh fresh direct20', invalid_as_missing=True)
            predictions = {r['episode_id']: r['selected'] for r in full['per_item'] if r['episode_id'] in ids}
            summary, items = release.score_predictions(name+'_direct', 'Astra xhigh fresh direct20',
                                                        predictions, public, labels, ids)
            ds = {'summary': summary, 'per_item': items, 'invalid_source_files': full['invalid_source_files']}
            ss = support.score_external_support(spaths, ROOT, system_id=name,
                                                display_label='Astra xhigh', invalid_as_missing=True)
            values, _, invalids = support.merge_support_shards(spaths, set(ids), invalid_as_missing=True)
            actual = {'direct': ds, 'support_q2': ss,
                      'sweep': sweep(values, name, 'Astra xhigh', public, labels, ids),
                      'comparison_q2_minus_direct': comparison(ss, ds), 'invalid_support_files': invalids}
            same(actual, expected, 'Recomputed diagnostic score/sweep differs')
            same(actual, combined['diagnostic'], 'Combined diagnostic differs')
        scores[name] = actual
        print(f'PASS: {name} frozen hashes, scores, prompt receipts, and usage')

    same(combined['comparisons'], [comparison(scores['astra_xhigh_r1_prior'], scores['sol_xhigh_r1'])],
         'Matched-harness comparison differs')
    for family, summary in combined['repeats'].items():
        rows = [s['summary'] for name, s in scores.items() if name.startswith(family)]
        require(summary['complete_runs'] == len(rows) == 1, 'Unexpected complete repeat count')
        same(summary['exact_mean_percentage'], statistics.mean(r['exact_optimal_percentage'] for r in rows),
             'Repeat exact mean differs')
        same(summary['coverage_mean_percentage'], statistics.mean(r['target_coverage_percentage'] for r in rows),
             'Repeat coverage mean differs')
        require(summary['exact_sample_sd_pp'] is None and summary['coverage_sample_sd_pp'] is None,
                'A single run cannot estimate generation SD')

    historical = read(HERE / 'historical_q_sweep.json')
    source = ROOT / 'responses/support_transcription.json'
    require(sha(source) == historical['source_sha256'], 'Historical support source changed')
    for system_id, values in read(source).items():
        actual = sweep(values, system_id, system_id, public, labels, ids)
        same(actual, historical['results'][system_id], f'{system_id}: historical sweep differs')
        oldfile = 'structured_comparison.json' if system_id == 'gpt_sol_5_6_pro' else 'xhigh_structured_comparison.json'
        old = read(ROOT / 'results' / oldfile)
        for key in ('exact_optimal', 'achieved_target_coverage', 'valid', 'exact_by_block'):
            same(actual[1]['summary'][key], old['structured_summary'][key], 'Original q=2 score changed')
        same(actual[1]['support_edges'], old['support_q2'], 'Original q=2 edges changed')
    require(combined['core_complete'] is False and combined['pending_core'] == ['astra_max_r1'],
            'This snapshot must not claim the pending max run is complete')
    print('PASS: historical q=1..4 sweeps, ties, paired comparisons, and original release preservation')
    print('ALL FOLLOW-UP CHECKS PASSED (mathematical reproduction; omitted operational logs are not re-audited)')


if __name__ == '__main__':
    verify()
