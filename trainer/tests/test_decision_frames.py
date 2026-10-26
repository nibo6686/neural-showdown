import copy
import json
from pathlib import Path
import subprocess

import pytest
from neural.decision_frames import read_frames, validate_frame
from neural.perspective_knowledge import knowledge_identity
from neural.ts_identity import observation_digest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope='module')
def exported(tmp_path_factory):
    directory = tmp_path_factory.mktemp('decision-frames')
    subprocess.run(['node', 'sim-core/tests/helpers/export_frame_cases.cjs', str(directory)],
                   cwd=ROOT, check=True, capture_output=True, timeout=40)
    return directory


@pytest.mark.parametrize('replay', ['2695493840', '2695512325', '2695618222'])
def test_three_committed_replays_roundtrip(exported, replay):
    path = exported / (replay + '.jsonl')
    original = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
    loaded = list(read_frames(path))
    assert loaded == original
    assert {frame['owner'] for frame in loaded} == {'p1', 'p2'}
    assert all(frame['knowledge']['projection']['owned_moves']['schema'] == 'native-owner-moves/v1'
               for frame in loaded)
    assert all(('action' in a) == ('action' in b) for a, b in zip(original, loaded))


@pytest.mark.parametrize('owner', ['p1', 'p2'])
def test_hidden_bench_invariance_survives_reader(exported, owner):
    a, b = [list(read_frames(exported / f'{owner}-{i}.jsonl')) for i in (0, 1)]
    assert a[:2] == b[:2]
    assert a[2] != b[2]
    assert (exported / f'{owner}-0.jsonl').read_bytes().splitlines()[:2] == (exported / f'{owner}-1.jsonl').read_bytes().splitlines()[:2]


@pytest.mark.parametrize('mutation', ['foreign', 'fabricated', 'legal', 'version', 'unknown', 'future', 'extra', 'false-index', 'foreign-subject', 'nested-private', 'fabricated-hp'])
def test_reader_rejects_malformed_or_private_frames(exported, mutation):
    frame = copy.deepcopy(next(read_frames(exported / '2695493840.jsonl')))
    projection = frame['knowledge']['projection']
    if mutation == 'foreign':
        projection['current'][0]['owner'] = 'p2'
    elif mutation == 'fabricated':
        fact = next(f for f in projection['current'] if f['property'] == 'roster_species')
        fact.update(state='known', value={'type': 'text', 'data': 'pikachu'}, reason='none', precision='exact')
    elif mutation == 'legal':
        frame['legal_actions'].pop()
    elif mutation == 'version':
        frame['schema_version'] = 'decision-frame/v999'
    elif mutation == 'unknown':
        projection['owned_moves']['request']['emitted_flags']['trapped']['value'] = False
    elif mutation == 'future':
        projection['request']['cursor'] = frame['observation']['event_cursor'] + 1
    elif mutation == 'extra':
        frame['observation']['request']['foreign_request'] = {'player': 'p2'}
    elif mutation == 'false-index':
        frame['legal_actions'][0]['index'] = False
    elif mutation == 'foreign-subject':
        projection['owned_moves']['roster'][0]['subject'] = 'p2:roster:1'
    elif mutation == 'nested-private':
        frame['observation']['request']['side'][0]['stats']['atk'] = {'owner': 'p2', 'private': 42}
        frame['observation']['observation_id'] = observation_digest(frame['observation'])
        frame['knowledge']['binding']['observation_id'] = frame['observation']['observation_id']
    elif mutation == 'fabricated-hp':
        fact = next(f for f in projection['current'] if f['property'] == 'hp' and f['subject'] == projection['request']['subject'])
        fact['value']['data'] += 1
    projection['id'] = knowledge_identity(projection)
    with pytest.raises(ValueError):
        validate_frame(frame)


def test_reader_rejects_duplicate_json_key(exported, tmp_path):
    text = (exported / '2695493840.jsonl').read_text(encoding='utf-8').splitlines()[0]
    path = tmp_path / 'duplicate.jsonl'
    path.write_text(text.replace('{', '{"owner":"p2",', 1), encoding='utf-8')
    with pytest.raises(ValueError, match='duplicate-key'):
        list(read_frames(path))
