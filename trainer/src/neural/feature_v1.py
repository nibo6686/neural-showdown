"""feature-v1: addressed v2 view/request only. No history, K or labels."""
import hashlib
import json
import re
import unicodedata
from pathlib import Path
import numpy as np

FEATURE_VERSION = 'feature-v1'
VOCAB_SHA256 = '15508f3539c26d338c5b206a979842f1f1007d670a1ea237016941fbde54dd08'
_bytes = Path(__file__).with_name('vocab_b8f23c99.json').read_bytes()
if hashlib.sha256(_bytes).hexdigest() != VOCAB_SHA256:
    raise ValueError('feature-v1/vocabulary-pin')
VOCAB = json.loads(_bytes)
IDS = {k: {name: i for i, name in enumerate(v)} for k, v in VOCAB['categories'].items()}
PAD, UNKNOWN, ABSENT = 0, 1, 2
UN, KN, NO, PA = 0, 1, 2, 3
BOOSTS = ('atk', 'def', 'spa', 'spd', 'spe', 'accuracy', 'evasion')
NUMERICS = ('hp', 'level', 'atk', 'def', 'spa', 'spd', 'spe', 'pp1', 'pp2', 'pp3', 'pp4',
            *('boost_' + k for k in BOOSTS), 'active', 'fainted', 'terastallized', 'appearance_uncertain')


def key(value):
    return re.sub('[^a-z0-9]', '', re.sub(r'^(move|ability|item):\s*', '', unicodedata.normalize('NFKD', value).lower()))


def category(domain, value, *, absent=False):
    if domain == 'types' and value == '???':
        return ABSENT  # Explicitly removed type, e.g. Double Shock's ???/Fighting.
    if value is None or value == '':
        return ABSENT if absent else UNKNOWN
    name = key(value)
    if name not in IDS[domain]:
        raise ValueError('feature-v1/unlisted-' + domain + ':' + name)
    return IDS[domain][name]


def featurize(observation, request):
    if observation['schema_version'] != 'observable-battle-state/v2':
        raise ValueError('feature-v1/observation-version')
    owner, view = observation['perspective'], observation['view']
    if view['player'] != owner or request != observation['request'] or (request is not None and request['player'] != owner):
        raise ValueError('feature-v1/owner-request')
    cats = np.full((12, 11), UNKNOWN, dtype=np.int32)
    nums = np.zeros((12, len(NUMERICS)), dtype=np.float32)
    states = np.full(nums.shape, UN, dtype=np.uint8)
    presence = np.zeros(12, dtype=np.uint8)  # 0 padding, 1 unrevealed, 2 observed
    effects = np.zeros((12, len(IDS['volatiles'])), dtype=np.bool_)
    def number(i, column, value, scale=1):
        if value is not None:
            nums[i, column] = float(value) / scale
            states[i, column] = KN
    for side, team in enumerate(('self_team', 'opponent_team')):
        player = owner if side == 0 else view['opponent']
        size = view['team_size'][player]
        if type(size) is not int or not 1 <= size <= 6:
            raise ValueError('feature-v1/team-size')
        presence[side*6:side*6+size] = 1
        cats[side*6+size:side*6+6] = PAD
        states[side*6+size:side*6+6] = PA
        for p in view[team]:
            slot = p['slot'] - 1
            if not 0 <= slot < size:
                raise ValueError('feature-v1/slot')
            i = side*6+slot
            presence[i] = 2
            cats[i, 0] = category('species', p['displayed_species'] or p['species'])
            if side == 0:
                cats[i, 1] = category('items', p['item'], absent=p['item_state'] in ('none', 'removed', 'consumed'))
                cats[i, 2] = category('abilities', p['ability'], absent=p['ability_state'] == 'none')
                moves = p['moves']
                cats[i, 7:11] = [category('moves', moves[j]) if j < len(moves) else ABSENT for j in range(4)]
                for n, stat in enumerate(BOOSTS[:5]):
                    number(i, 2+n, p['stats'].get(stat), 500)
                boosts = p['boosts']
                if request and p['active'] and request['active']:
                    for move in request['active']['moves']:
                        slot = move['slot'] - 1
                        aligned = slot < len(moves) and key(moves[slot]) == move['id'] and not p['transformed']
                        if aligned and move['maxpp'] > 0 and move['id'] not in ('recharge', 'struggle'):
                            number(i, 6+move['slot'], move['pp']/move['maxpp'])
            else:
                # Public v2 publishes only an item-presence marker, no identity or
                # absent marker. Never reconstruct either from history here.
                boosts = p.get('public_boosts', {})
            cats[i, 3] = category('status', p['status'], absent=p['status_source'] != 'unknown')
            for j in range(2):
                cats[i, 4+j] = category('types', p['types'][j]) if j < len(p['types']) else (ABSENT if p['types'] else UNKNOWN)
            # Stellar preserves defensive typing; v2 omits opponent Tera identity.
            tera = p.get('tera_type') if side == 0 else None
            cats[i, 6] = category('types', tera)
            number(i, 0, p['hp_ratio'])
            number(i, 1, p['level'], 100)
            for j, stat in enumerate(BOOSTS):
                number(i, 11+j, boosts.get(stat), 6)
            for j, field in enumerate(('active', 'fainted', 'terastallized', 'displayed_species_uncertain')):
                number(i, 18+j, p[field])
            for effect in p['volatiles']:
                effects[i, category('volatiles', effect)] = True
    field = view['field']
    field_cat = np.array([category('weather', None if field['weather'] == 'none' else field['weather'], absent=True),
                          category('terrain', None if field['terrain'] == 'none' else field['terrain'], absent=True)], dtype=np.int32)
    field_effects = np.zeros((3, len(IDS['side_conditions'])), dtype=np.float32)
    for name in field['pseudo_weather']:
        field_effects[0, category('pseudo_weather', name)] = 1
    for side, label in enumerate(('self', 'opponent'), 1):
        for name, layers in field['side_conditions'][label].items():
            field_effects[side, category('side_conditions', name)] = layers/3
    legal = request['legal_actions'] if request else {'actions': [], 'mask': [], 'available_indices': []}
    indices = legal['available_indices']
    if indices != [i for i, enabled in enumerate(legal['mask']) if enabled is True]:
        raise ValueError('feature-v1/legal-mask')
    acat = np.full((len(indices), 4), UNKNOWN, dtype=np.int32)
    anum = np.zeros((len(indices), 6), dtype=np.float32)
    astate = np.full(anum.shape, UN, dtype=np.uint8)
    targets = np.full(len(indices), -1, dtype=np.int32)
    for j, index in enumerate(indices):
        action = legal['actions'][index]
        if action['index'] != index:
            raise ValueError('feature-v1/legal-index')
        kind = 'default' if action['choice'] == 'default' else action['kind']
        acat[j, 0] = category('action_kinds', kind)
        if kind in ('switch', 'revive'):
            target = next(p for p in request['side'] if p['slot'] == action['slot'])
            token = next(p['slot']-1 for p in view['self_team'] if p['ident'] == target['ident'])
            targets[j] = token
            acat[j, 1:] = ABSENT
            astate[j] = NO
        elif kind == 'default':
            active = request['active']
            acat[j, 1] = category('moves', active['moves'][0]['id']) if active else ABSENT
            acat[j, 2:] = ABSENT
            astate[j, :3] = NO  # canonical default is not an attack
            astate[j, 5] = KN
        else:
            slot = action['slot']
            move = next(m for m in request['active']['moves'] if m['slot'] == slot)
            data = VOCAB['move_data'].get(move['id'])
            acat[j, 1] = category('moves', move['id'])
            acat[j, 2] = category('types', move['type'])
            acat[j, 3] = category('damage_categories', move['category'])
            anum[j, [0, 5]] = [move['base_power']/250, float(kind == 'move_tera')]
            astate[j, [0, 5]] = KN
            if move['maxpp'] > 0 or move['id'] == 'struggle':
                anum[j, 4] = float(move['disabled'])
                astate[j, 4] = KN
            if data:
                anum[j, 1:3] = [data['priority']/7, data['accuracy']]
                astate[j, 1:3] = KN
            if move['maxpp'] > 0 and move['id'] not in ('recharge', 'struggle'):
                anum[j, 3] = move['pp']/move['maxpp']
                astate[j, 3] = KN
    return {'pokemon_cat': cats, 'pokemon_num': nums, 'pokemon_num_state': states,
            'pokemon_presence': presence, 'pokemon_mask': presence != 0, 'pokemon_effects': effects,
            'field_cat': field_cat, 'field_num': np.array([view['turn']/100], np.float32),
            'field_effects': field_effects, 'action_cat': acat, 'action_num': anum,
            'action_num_state': astate, 'action_target': targets,
            'action_indices': np.array(indices, np.int32), 'action_mask': np.ones(len(indices), np.bool_)}
