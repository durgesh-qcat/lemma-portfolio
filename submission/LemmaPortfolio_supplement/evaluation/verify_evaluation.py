#!/usr/bin/env python3
"""Check archived evaluation associations using only the Python standard library.

Read-only: no model calls, network access, imports of inference harnesses, or
output files. This checks record consistency, not hidden serving conditions.
"""
import ast
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def local(name):
    relative = Path(name)
    require(not relative.is_absolute() and '..' not in relative.parts,
            f'Non-local archive path: {name}')
    path = (ROOT / relative).resolve()
    require(path.is_relative_to(ROOT) and path.is_file(),
            f'Missing or out-of-tree file: {name}')
    return path


def read(name):
    return json.loads(local(name).read_text(encoding='utf-8'))


def check_hash(name, expected):
    actual = hashlib.sha256(local(name).read_bytes()).hexdigest()
    require(actual == expected, f'SHA-256 mismatch: {name}')


def valid_selection(value):
    return (isinstance(value, list) and len(value) == 3
            and all(isinstance(x, str) and x in CANDIDATES for x in value)
            and len(set(value)) == 3)


CANDIDATES = {f'C{i:02d}' for i in range(1, 17)}
EPISODES = {f'MLP4B_{i:04d}' for i in range(60)}


def main():
    settings = read('evaluation/settings.json')
    manifest = read('MANIFEST.json')
    phases = {p['id']: p for p in manifest['phases']}
    paper = {r['id']: r for r in read('results/paper_results.json')['direct_rows']}
    original = read('original_release/responses/direct_transcription.json')
    original_rows = settings['original_response_sets']
    require(len(original_rows) == len(original) == 6, 'Expected six original sets')
    require({r['system_id'] for r in original_rows} == set(original), 'Original IDs')
    for row in original_rows:
        saved = original[row['system_id']]
        local(row['source_capture'])
        require(row['display_label'] == saved['display_label'], 'Original label')
        require(set(saved['predictions']) <= EPISODES, 'Original episode alignment')
        valid = sum(valid_selection(v) for v in saved['predictions'].values())
        require(valid == row['valid_answers'] == paper[row['system_id']]['valid'],
                f'Original validity: {row["system_id"]}')
    followups = settings['followup_runs']
    require(len(followups) == 7, 'Expected seven full follow-up runs')
    rows = followups + [settings['astra_targetwise_diagnostic']]
    require({r['run_id'] for r in rows} == set(phases), 'Manifest run inventory')
    prompt_count = response_count = 0
    for row in rows:
        run_id = row['run_id']
        run = read(row['run_evidence'])
        phase = phases[run_id]
        require(run['run_id'] == run_id, 'Run evidence ID')
        require(run['responses_directory'] == row['responses_directory'], 'Response directory')
        require(run['metadata']['source_sha256'] == phase['source_metadata_sha256'],
                f'Source metadata association: {run_id}')
        reported = phase['reported_metadata']
        require(row['model_requested'] == reported['requested_model']
                and row['effort'] == reported['requested_effort'], 'Model/effort mapping')
        calls = {c['name']: c for c in run['prompt_calls']}
        mapped = {c['call']: c for c in phase['calls']}
        require(len(calls) == len(run['prompt_calls']) == row['call_count']
                and set(calls) == set(mapped), f'Call mapping: {run_id}')
        receipts = run['receipts']['record']
        successful = [r for r in receipts if r.get('response_sha256')]
        require(len(successful) == len(calls)
                and {r['call'] for r in successful} == set(calls), 'Receipt mapping')
        failed = [r for r in receipts if not r.get('response_sha256')]
        require(([r['call'] for r in failed] == ['10'])
                if run_id == 'claude_fable_5_xhigh_r1' else not failed, 'Failed-call inventory')
        for receipt in successful:
            name = receipt['call']
            call, entry = calls[name], mapped[name]
            require(call['prompt'] == entry['prompt'] and call['kind'] == entry['kind'],
                    f'Prompt association: {run_id}/{name}')
            require(call['prompt_sha256'] == receipt['prompt_sha256']
                    == entry['prompt_sha256'], 'Prompt hash associations')
            check_hash(call['prompt'], call['prompt_sha256'])
            header = local(call['prompt']).read_text(encoding='utf-8').split('<episodes>', 1)[0]
            ids = list(dict.fromkeys(re.findall(r'MLP4B_\d{4}', header)))
            require(ids == entry['episode_ids'] and set(ids) <= EPISODES, 'Prompt episode IDs')
            require(call.get('episode_ids', ids) == ids, 'Run episode IDs')
            response = f'{run["responses_directory"]}/{name}.json'
            require(response == entry['response'] and receipt['response_sha256']
                    == entry['response_sha256'], 'Response association')
            check_hash(response, receipt['response_sha256'])
            answer = read(response)
            key = 'predictions' if call['kind'] == 'direct' else 'predicted_support'
            require(set(answer[key]) == set(ids), 'Answer episode IDs')
            if key == 'predictions':
                require(all(valid_selection(v) for v in answer[key].values()), 'Direct validity')
            require(receipt.get('observed_tool_event_count',
                                receipt.get('tool_use_block_count', 0)) == 0, 'Tool events')
            prompt_count += 1
            response_count += 1
        if run_id != 'astra_diagnostic':
            require(row['valid_answers'] == paper[run_id]['valid'] == 60, 'Follow-up validity')
    require(prompt_count == response_count == 92, 'Expected 92 prompt/response pairs')
    prompts = settings['prompts']
    check_hash(prompts['prompt_manifest'], prompts['prompt_manifest_sha256'])
    codex = settings['codex_settings']
    plan = read(codex['source'])['codex_plan']['record']
    require(codex['cli_version'] == plan['cli_version']
            and codex['cli_binary_sha256'] == plan['cli_sha256']
            and codex['timeout_seconds'] == plan['timeout_seconds'], 'Codex settings')
    fable = settings['fable_settings']
    check_hash(fable['fable_5_1_system_context'], fable['fable_5_1_system_context_sha256'])
    context = local(fable['fable_5_1_system_context']).read_text(encoding='utf-8')
    require(len(fable['harnesses']) == 3, 'Expected three preserved harness versions')
    for harness in fable['harnesses']:
        check_hash(harness['file'], harness['sha256'])
        ast.parse(local(harness['file']).read_text(encoding='utf-8'))
    for run_id in ('claude_fable_5_xhigh_r1', 'claude_fable_5_1_xhigh_ctx_r1'):
        metadata = read(f'evaluation/runs/{run_id}.json')['metadata']['record']
        require(metadata['model_requested'] == phases[run_id]['reported_metadata']['requested_model'],
                'Fable requested model')
        require(metadata['sdk']['package'] == fable['sdk_package']
                and metadata['sdk']['version'] == fable['sdk_version']
                and metadata['sdk']['python'] == fable['python_version'], 'Fable SDK settings')
        require(metadata['request_params']['max_tokens'] == fable['max_tokens'] == 128000
                and metadata['request_params']['output_config'] == fable['output_config'],
                'Fable request settings')
        expected = context.strip() if run_id.endswith('_ctx_r1') else None
        require(metadata['system_prompt'] == expected, 'Fable system instructions')
    print('EVALUATION CHECKS PASSED: 13 response sets; 92 prompt/response pairs; '
          '3 harness hashes; SDK/context settings; archive-local paths.')


if __name__ == '__main__':
    main()
