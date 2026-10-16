"""Prompt32 immutable old reader context; no native execution in Python."""
import json
import os
import subprocess
import sys
from pathlib import Path
import pytest
from neural import pipeline_record as reader, protocol_contract as protocol
from neural import typed_state, public_boosts
from neural.version_profile import HISTORICAL10_CONTEXT as C, reader_context, NATIVE11
ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / 'docs/planning'
def load(s): return json.loads((DOC / ('perspective-fidelity-prompt31-' + s + '.json')).read_text(encoding='utf-8'))
def literal(v): return json.dumps(v, ensure_ascii=True, sort_keys=True, separators=(',', ':')) + '\n'
def emit(name, **kwargs): print('P32_WITNESS ' + json.dumps(dict(name=name, **kwargs), sort_keys=True))

def test_recursive_context_and_literal_outputs(monkeypatch):
    f, old = load('reader-fixtures'), load('old-publication-goldens')
    observed = []
    original = reader.validate_pipeline_episode_evidence
    def tap(*args, **kwargs):
        observed.append(kwargs.get('reader_rules'))
        return original(*args, **kwargs)
    monkeypatch.setattr(reader, 'validate_pipeline_episode_evidence', tap)
    monkeypatch.setattr(protocol, 'SUPPORTED_COMMANDS', frozenset())
    monkeypatch.setattr(protocol, 'VALIDATION_RULES', {})
    monkeypatch.setattr(typed_state, '_ENTRIES', {})
    cases = [('bundle', reader.validate_historical_pipeline_bundle), ('envelope', reader.validate_historical_pipeline_episode_evidence),
             ('result', reader.validate_historical_pipeline_episode_result), ('sweep', reader.validate_historical_pipeline_episode_publication_sweep)]
    for name, fn in cases:
        before = literal(f[name]); actual = fn(f[name]); assert literal(actual) == old[name]['api_literal']; assert literal(f[name]) == before
    reader.validate_pipeline_episode_evidence(f['continuation'], reader_rules=C)
    assert len(observed) >= 5 and all(c is C for c in observed)
    for line in ['|turn|1', '|-singlemove|p1a: A|Destiny Bond', '|-anim|p1a: A|Spectral Thief|p2a: B']:
        protocol.validate_protocol_record(line, reader_rules=C)
    prefix = ['|switch|p1a: A|Pikachu|100/100', '|-start|p1a: A|Substitute', '|-boost|p1a: A|atk|1']
    assert typed_state.project_public_typed_state(prefix, reader_rules=C)['volatiles_by_ident']['p1: A'] == ['substitute']
    assert public_boosts.public_boost_evidence(prefix, reader_rules=C)['p1: A']['atk'] == 1
    emit('python-recursive', branches=4, nested_evidence_calls=len(observed), exact_context=True, old_literals=True, singleton_mutation_isolated=True)

def test_immutable_and_unsupported_contexts():
    f = load('reader-fixtures')
    with pytest.raises(TypeError): C.protocol['validation_rules']['player_ident']['side_ids'][0] = 'p9'
    copied = C._replace()
    with pytest.raises(ValueError, match='unsupported-context'): reader_context(copied)
    target = C._replace(profile=NATIVE11)
    for fn, value in [(reader.validate_pipeline_bundle, f['bundle']), (reader.validate_pipeline_episode_evidence, f['continuation']),
                      (reader.validate_pipeline_episode_result, f['result']), (reader.validate_pipeline_episode_publication_sweep, f['sweep'])]:
        with pytest.raises(ValueError, match='native11-unadopted'): fn(value, reader_rules=target)
    assert reader.validate_historical_pipeline_bundle(f['bundle'])['record_id'] == json.loads(load('old-publication-goldens')['bundle']['api_literal'])['record_id']
    emit('python-context-negatives', immutable=True, unsupported_before_semantics=True, interleaved_historical_unchanged=True, target_semantics_unproved=True)

def test_cli_compact_and_negative():
    env = dict(os.environ)
    for k in list(env):
        if k in ('PYTHONUTF8', 'PYTHONIOENCODING') or k.startswith(('REPORT_', 'PROMPT')): env.pop(k)
    env['PYTHONPATH'] = str(ROOT / 'trainer/src')
    def cli(v, *args): return subprocess.run([sys.executable, '-m', 'neural.pipeline_record', *args], input=json.dumps(v), text=True,
                                           capture_output=True, cwd=ROOT, env=env, timeout=20)
    valid = cli(load('reader-fixtures')['sweep'], '--reader-profile=historical10')
    assert valid.returncode == 0 and valid.stdout == load('old-publication-goldens')['sweep']['cli_literal'], valid.stderr
    invalid = cli(load('resealed-negatives')['target'])
    assert invalid.returncode == 2 and invalid.stdout == '' and 'native11-unadopted' in invalid.stderr
    emit('python-cli', compact_literal=True, invalid_exit=2, invalid_stdout='')
