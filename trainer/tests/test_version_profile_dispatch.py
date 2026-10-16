"""Lean old-reader caller proof only: saved inputs, no native battles."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from neural import pipeline_record as reader
from neural.version_profile import select_reader_profile, recognized_reader_revisions, HISTORICAL10, NATIVE11_REVISION as TARGET, HISTORICAL10_REVISION as OLD

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / 'docs/planning'
def load(name):
    return json.loads((DOC / ('perspective-fidelity-prompt31-' + name + '.json')).read_text(encoding='utf-8'))
def literal(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':')) + '\n'
def witness(name, **kwargs):
    print('P31_WITNESS ' + json.dumps(dict(name=name, **kwargs), sort_keys=True))

def test_historical_paths_and_literals():
    f, expected = load('reader-fixtures'), load('old-publication-goldens')
    cases = [('bundle', reader.validate_historical_pipeline_bundle), ('envelope', reader.validate_historical_pipeline_episode_evidence),
             ('result', reader.validate_historical_pipeline_episode_result), ('sweep', reader.validate_historical_pipeline_episode_publication_sweep)]
    for name, function in cases:
        value = f[name]; before = literal(value); actual = function(value)
        assert literal(actual) == expected[name]['api_literal']
        assert literal(value) == before
    assert reader.validate_historical_pipeline_episode_evidence(f['continuation'])['complete_capture'] is False
    empty = json.loads((ROOT / 'artifacts/validation/ce08b-independent-review-2026-10-09/valid-cancellation-control.json').read_text(encoding='utf-8'))
    assert select_reader_profile(empty, 'historical10') is HISTORICAL10
    assert reader.validate_historical_pipeline_episode_result(empty) == []
    with pytest.raises(ValueError, match='ambiguous-revision'): select_reader_profile(empty)
    witness('python-historical', entry_branches=4, old_literal_output_preserved=True, explicit_empty_historical=True, no_native_execution=True)

def test_revision_structure_negatives():
    f, negatives = load('reader-fixtures'), load('resealed-negatives')
    for name, pattern in [('target', 'native11-unadopted'), ('unknown', 'unknown-revision'), ('conflict', 'conflicting-revisions')]:
        with pytest.raises(ValueError, match=pattern): reader.validate_historical_pipeline_bundle(negatives[name])
    with pytest.raises(ValueError, match='native11-unadopted'): reader.validate_historical_pipeline_episode_evidence(negatives['predecessor'])
    bad_result = copy.deepcopy(f['result']); bad_result['records']['p1'][0] = negatives['target']
    with pytest.raises(ValueError, match='conflicting-revisions'): reader.validate_historical_pipeline_episode_result(bad_result)
    bad_sweep = copy.deepcopy(f['sweep']); bad_sweep['beliefs'][1]['fields']['transition_lineage']['simulator_revision'] = TARGET
    with pytest.raises(ValueError, match='conflicting-revisions'): reader.validate_historical_pipeline_episode_publication_sweep(bad_sweep)
    bad_evidence = copy.deepcopy(f['bundle']); bad_evidence['successor_belief']['evidence'] = [{'provenance': {'kind': 'simulator_only_truth', 'simulator_revision': TARGET}}]
    with pytest.raises(ValueError, match='conflicting-revisions'): reader.validate_pipeline_bundle(bad_evidence)
    assert recognized_reader_revisions({'schema_version': 'pipeline-linked-record/v1', 'transition': {'simulator_revision': OLD}, 'request': {'simulator_revision': TARGET}}) == (OLD,)
    for selection, pattern in [('native11', 'native11-unadopted'), ('alien', 'unknown-profile')]:
        with pytest.raises(ValueError, match=pattern): select_reader_profile(f['bundle'], selection)
    assert select_reader_profile(f['bundle']) is HISTORICAL10
    # Reserved calls never change the active singleton/default reader.
    assert reader.SIMULATOR_REVISION == OLD
    assert reader.validate_pipeline_bundle(f['bundle'])['record_id'] == json.loads(load('old-publication-goldens')['bundle']['api_literal'])['record_id']
    witness('python-negative', resealed_bundle_and_predecessor=True, actual_result_sweep_guards=True, singleton_unchanged=True)

def test_cli_dispatch_branches():
    f, goldens = load('reader-fixtures'), load('old-publication-goldens')
    env = dict(os.environ)
    for key in list(env):
        if key in ('PYTHONUTF8', 'PYTHONIOENCODING') or key.startswith(('REPORT_', 'PROMPT')): env.pop(key)
    env['PYTHONPATH'] = str(ROOT / 'trainer/src')
    def cli(value, *args):
        return subprocess.run([sys.executable, '-m', 'neural.pipeline_record', *args], input=json.dumps(value), text=True,
                              capture_output=True, cwd=ROOT, env=env, timeout=20)
    for name in ('bundle', 'envelope', 'result', 'sweep'):
        result = cli(f[name]); assert result.returncode == 0, result.stderr
        assert result.stdout == goldens[name]['cli_literal']
    empty = json.loads((ROOT / 'artifacts/validation/ce08b-independent-review-2026-10-09/valid-cancellation-control.json').read_text(encoding='utf-8'))
    result = cli(empty, '--reader-profile', 'historical10'); assert result.returncode == 0 and result.stdout == '[]\n', result.stderr
    failures = [(empty, ('--reader-profile=auto',), 'ambiguous-revision'),
                (f['bundle'], ('--reader-profile=native11',), 'native11-unadopted'),
                (f['bundle'], ('--reader-profile=alien',), 'unknown-profile'),
                (load('resealed-negatives')['unknown'], (), 'unknown-revision')]
    for value, args, pattern in failures:
        result = cli(value, *args); assert result.returncode == 2 and result.stdout == '', result.stdout
        assert pattern in result.stderr
    witness('cli', default_caller_branches=4, explicit_historical_empty=True, rejection_exit=2, rejection_stdout='')
