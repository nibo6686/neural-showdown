import copy
import json
from pathlib import Path
import subprocess
import numpy as np
import pytest
from neural.feature_v1 import featurize, UNKNOWN, ABSENT, KN, VOCAB_SHA256
from test_decision_frames import exported

ROOT = Path(__file__).resolve().parents[2]


def frames(directory, name):
    return [json.loads(line) for line in (directory / (name + '.jsonl')).read_text(encoding='utf-8').splitlines()]


def identical(a, b):
    assert set(a) == set(b)
    for key in a:
        assert a[key].dtype == b[key].dtype and a[key].shape == b[key].shape
        assert a[key].tobytes() == b[key].tobytes(), key


@pytest.mark.parametrize('name', ['2695493840', '2695512325', '2695618222'])
def test_exact_golden_arrays_and_mask(exported, name):
    frame = frames(exported, name)[0]
    actual = featurize(frame['observation'], frame['observation']['request'])
    golden = json.loads((ROOT / 'trainer/tests/fixtures/feature-v1' / (name + '.json')).read_text())
    assert set(actual) == set(golden)
    for key, expected in golden.items():
        assert list(actual[key].shape) == expected['shape']
        assert str(actual[key].dtype) == expected['dtype']
        np.testing.assert_array_equal(actual[key], np.asarray(expected['values'], dtype=expected['dtype']))
    np.testing.assert_array_equal(actual['action_indices'], frame['observation']['request']['legal_actions']['available_indices'])
    assert actual['action_mask'].all()
    identical(actual, featurize(frame['observation'], frame['observation']['request']))
    for index, action in enumerate(frame['legal_actions']):
        if action['kind'] == 'switch':
            assert 0 <= actual['action_target'][index] < 6


@pytest.mark.parametrize('owner', ['p1', 'p2'])
def test_born_hidden_bench_feature_invariance(exported, owner):
    a, b = [frames(exported, f'{owner}-{i}') for i in (0, 1)]
    for i in (0, 1):
        identical(featurize(a[i]['observation'], a[i]['observation']['request']),
                  featurize(b[i]['observation'], b[i]['observation']['request']))
    x, y = [featurize(f[2]['observation'], f[2]['observation']['request']) for f in (a, b)]
    assert any(x[k].tobytes() != y[k].tobytes() for k in x)


def test_unknown_absent_known_zero_and_no_history_reads(exported):
    frame = frames(exported, '2695493840')[0]
    obs = copy.deepcopy(frame['observation'])
    # Neither protocol history nor any additive K payload may be inspected.
    obs['protocol_prefix'] = object()
    obs['knowledge'] = object()
    pokemon = next(p for p in obs['view']['self_team'] if p['active'])
    pokemon.update(item=None, item_state='removed')
    obs['request']['active']['moves'][0]['pp'] = 0
    x = featurize(obs, obs['request'])
    assert x['pokemon_cat'][pokemon['slot']-1, 1] == ABSENT
    assert x['pokemon_cat'][6, 1] == UNKNOWN
    assert x['pokemon_presence'][7] == 1  # unrevealed, never zero padding
    assert x['pokemon_num'][pokemon['slot']-1, 7] == 0
    assert x['pokemon_num_state'][pokemon['slot']-1, 7] == KN
    assert x['action_num'][0, 3] == 0 and x['action_num_state'][0, 3] == KN


def test_real_knock_off_absence(exported):
    found = False
    for frame in frames(exported, '2695512325'):
        for p in frame['observation']['view']['self_team']:
            if p['item_state'] == 'removed':
                x = featurize(frame['observation'], frame['observation']['request'])
                assert x['pokemon_cat'][p['slot']-1, 1] == ABSENT
                found = True
    assert found


def test_explicit_public_weather_clear_is_absent(exported):
    obs = copy.deepcopy(frames(exported, '2695493840')[0]['observation'])
    obs['view']['field'].update(weather='none', terrain='none')
    x = featurize(obs, obs['request'])
    np.testing.assert_array_equal(x['field_cat'], [ABSENT, ABSENT])
    obs['view']['opponent_team'][0]['types'] = ['???', 'Fighting']
    x = featurize(obs, obs['request'])
    from neural.feature_v1 import category
    np.testing.assert_array_equal(x['pokemon_cat'][6, 4:6], [ABSENT, category('types', 'Fighting')])


def test_reject_foreign_request_and_mask_mismatch(exported):
    obs = copy.deepcopy(frames(exported, '2695493840')[0]['observation'])
    request = copy.deepcopy(obs['request']);request['player'] = 'p2'
    with pytest.raises(ValueError, match='owner-request'):
        featurize(obs, request)
    obs['request']['legal_actions']['mask'][0] = False
    with pytest.raises(ValueError, match='legal-mask'):
        featurize(obs, obs['request'])


@pytest.mark.parametrize('name', ['recharge', 'struggle'])
def test_synthetic_request_pp_stays_unknown(exported, name):
    obs = copy.deepcopy(frames(exported, '2695493840')[0]['observation'])
    for move in obs['request']['active']['moves']:
        move.update(id=name, pp=0, maxpp=1)
    x = featurize(obs, obs['request'])
    assert x['action_num_state'][0, 3] == 0
    own = next(p['slot']-1 for p in obs['view']['self_team'] if p['active'])
    assert x['pokemon_num_state'][own, 7] == 0


def test_copied_request_pp_is_not_attached_to_base_roster_moves(exported):
    obs = copy.deepcopy(frames(exported, '2695493840')[0]['observation'])
    pokemon = next(p for p in obs['view']['self_team'] if p['active'])
    pokemon['transformed'] = True
    x = featurize(obs, obs['request'])
    assert x['pokemon_num_state'][pokemon['slot']-1, 7] == 0
    assert x['action_num_state'][0, 3] == KN  # current option PP is still visible


def test_generated_vocabulary_bytes_and_special_ids():
    result = subprocess.run(['node', 'tools/engine/generate_vocab.cjs', '--check'], cwd=ROOT,
                            check=True, capture_output=True, timeout=15)
    assert result.stdout.decode().strip() == VOCAB_SHA256
    from neural.feature_v1 import VOCAB
    assert VOCAB['special'] == {'PAD': 0, 'UNKNOWN': 1, 'ABSENT': 2}
    assert {'unownb', 'furfroudandy'} <= set(VOCAB['categories']['species'])
    from neural.feature_v1 import category
    assert category('species', 'Flab\u00e9b\u00e9') == VOCAB['categories']['species'].index('flabebe')


def test_stellar_defensive_types_do_not_invent_opponent_tera_identity(exported):
    obs = copy.deepcopy(frames(exported, '2695493840')[0]['observation'])
    obs['view']['opponent_team'][0]['terastallized'] = True
    x = featurize(obs, obs['request'])
    assert x['pokemon_cat'][6, 6] == UNKNOWN


def test_locked_and_recharge_defaults_are_not_known_false(exported):
    obs = copy.deepcopy(frames(exported, '2695493840')[0]['observation'])
    for move in obs['request']['active']['moves']:
        move.update(pp=0, maxpp=0, disabled=False)
    x = featurize(obs, obs['request'])
    assert x['action_num_state'][0, 4] == 0
    legal = obs['request']['legal_actions']
    legal['mask'] = [True] + [False]*12;legal['available_indices'] = [0]
    legal['actions'][0].update(choice='default')
    obs['request']['active']['moves'][0]['id'] = 'recharge'
    x = featurize(obs, obs['request'])
    assert x['action_num_state'][0, 3] == x['action_num_state'][0, 4] == 0
