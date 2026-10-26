"""Strict addressed decision-frame reader. Validation never fills missing values.

This checks wire structure, identity and request consistency, not simulator truth
or source authority. Frames must come from the local born-session exporter.
"""
import json
from functools import lru_cache
from pathlib import Path

from .canonical_action import canonical_action_from_legal_action
from .perspective_knowledge import _shape, _contract, _fact_shape, knowledge_identity
from .pipeline_record import _validate_episode_observation
from .version_profile import NATIVE11_CONTEXT
from .ts_identity import canonical

SCHEMA_VERSION = 'decision-frame/v1'


def _require(condition, reason):
    if not condition:
        raise ValueError('decision-frame/' + reason)


@lru_cache(maxsize=1)
def _contracts():
    directory = Path(__file__).resolve().parents[3] / 'docs/contracts/fixtures/perspective-knowledge-native11-owner-moves-v1'
    return tuple(json.loads((directory / name).read_text(encoding='utf-8'))
                 for name in ('schema.json', 'profile.json'))


def _addressed(value, owner, cursor):
    if isinstance(value, dict):
        if value.get('state') in ('known', 'unknown') and 'value' in value:
            _require((value['value'] is None) == (value['state'] == 'unknown'), 'fact-value')
            if 'present' in value:
                _require(value['present'] == (value['state'] == 'known'), 'fact-presence')
        for key, item in value.items():
            if key == 'owner':
                _require(item == owner, 'foreign-owner')
            if key in ('subject', 'source_subject') and item is not None:
                _require(isinstance(item, str) and item.startswith(owner + ':'), 'foreign-subject')
            if key in ('cursor', 'observed_at') and item is not None:
                _require(type(item) is int and 0 <= item <= cursor, 'future-cursor')
            _addressed(item, owner, cursor)
    elif isinstance(value, list):
        for item in value:
            _addressed(item, owner, cursor)


def _request_shape(request, owner):
    """Close private request containers; public opponent fields live only in view."""
    for pokemon in request['side']:
        keys = {'slot', 'ident', 'details', 'condition', 'active', 'moves', 'stats',
                'base_ability', 'ability', 'item', 'tera_type', 'terastallized'}
        _require(set(pokemon) in (keys, keys | {'reviving'}), 'request-roster-fields')
        _require(pokemon['ident'].startswith(owner + ':'), 'foreign-request-roster')
        _require(set(pokemon['stats']) == {'atk', 'def', 'spa', 'spd', 'spe'}, 'request-stats')
        _require(all(type(n) is int and n >= 0 for n in pokemon['stats'].values()), 'request-stat-values')
        _require(all(type(move) is str for move in pokemon['moves']), 'request-roster-moves')
        _require(all(type(pokemon[key]) is str for key in ('ident', 'details', 'condition')), 'request-roster-text')
        _require(all(pokemon[key] is None or type(pokemon[key]) is str
                     for key in ('ability', 'base_ability', 'item', 'tera_type')), 'request-roster-identifiers')
    active = request['active']
    if active is not None:
        _require(set(active) == {'moves', 'can_terastallize', 'tera_type', 'trapped', 'can_switch'}, 'active-fields')
        for move in active['moves']:
            _require(set(move) == {'slot', 'move', 'id', 'pp', 'maxpp', 'target', 'disabled',
                                   'type', 'category', 'base_power', 'accuracy'}, 'request-move-fields')
            _require(all(type(move[key]) is str for key in ('move', 'id', 'target')), 'request-move-text')
    for action in request['legal_actions']['actions']:
        if action is not None:
            _require({'index', 'kind', 'choice', 'label'} <= set(action) <=
                     {'index', 'kind', 'choice', 'label', 'move', 'slot'}, 'legal-fields')
            _require(all(type(action[key]) is str for key in ('kind', 'choice', 'label')), 'legal-text')


def _request_state(observation):
    request = observation['request']
    if observation['view']['terminated']:
        return 'terminal'
    if request is None:
        return 'requestless'
    if request['wait']:
        return 'waiting'
    if request['force_switch']:
        return 'revival_selection' if any(p.get('reviving') is True for p in request['side']) else 'forced_switch'
    return 'move' if request['active'] is not None else 'unsupported'


def _active_consistency(projection, request):
    """Cross-check shared values without reconstructing writer/source authority."""
    active = next((p for p in request['side'] if p['active']), None)
    subject = projection['request']['subject']
    if active is None or subject is None:
        return
    hp = active['condition'].split(' ')[0].split('/')
    expected = {'hp': int(hp[0]), 'fainted': active['condition'] == '0 fnt'}
    if len(hp) == 2:
        expected['hp_max'] = int(hp[1])
    for fact in projection['current']:
        if fact['subject'] == subject and fact['state'] == 'known' and fact['property'] in expected:
            _require(canonical(fact['value']['data']) == canonical(expected[fact['property']]), 'request-fact-value')
    if request['active'] is not None:
        for option in projection['request']['options'] or []:
            index = option['option_index'] - 1
            _require(index < len(request['active']['moves']), 'option-index')
            move = request['active']['moves'][index]
            _require(option['request_move_id'] == move['id'], 'option-move')
            for fact, key in (('pp', 'pp'), ('max_pp', 'maxpp')):
                if option[fact]['state'] == 'known':
                    _require(option[fact]['value'] == move[key], 'option-pp')


def validate_frame(frame):
    """Return the supplied frame unchanged; reject malformed or private fields."""
    _require(type(frame) is dict and set(frame) in (
        {'schema_version', 'battle_id', 'step_index', 'owner', 'observation', 'knowledge', 'legal_actions'},
        {'schema_version', 'battle_id', 'step_index', 'owner', 'observation', 'knowledge', 'legal_actions', 'action'}), 'fields')
    _require(frame['schema_version'] == SCHEMA_VERSION, 'version')
    owner = frame['owner']
    _require(owner in ('p1', 'p2'), 'owner')
    _require(type(frame['step_index']) is int and frame['step_index'] >= 0, 'step-index')
    observation = _validate_episode_observation(frame['observation'], owner, frame['battle_id'],
                                               'decision frame', reader_rules=NATIVE11_CONTEXT)
    knowledge = frame['knowledge']
    _require(type(knowledge) is dict and set(knowledge) == {'projection', 'binding'}, 'knowledge-fields')
    projection, binding = knowledge['projection'], knowledge['binding']
    schema, profile = _contracts()
    _shape(projection, schema, schema['$defs'])
    _require(projection['id'] == knowledge_identity(projection), 'knowledge-identity')
    _require(projection['owner'] == owner and projection['boundary'] == frame['step_index'], 'projection-binding')
    _require(binding == {'observation_id': observation['observation_id'],
                        'prefix_cursor': observation['event_cursor'],
                        'request_adaptation': 'owned_health/v1',
                        'request_descriptor': 'owned-active-options/v1',
                        'request_state': binding.get('request_state')}, 'observation-binding')
    _require(binding['request_state'] in ('move', 'waiting', 'forced_switch', 'revival_selection',
                                         'terminal', 'requestless', 'unsupported'), 'request-state')
    descriptor = projection['request']
    _require(descriptor['cursor'] == observation['event_cursor'], 'descriptor-cursor')
    move_request = projection['owned_moves']['request']
    _require(move_request['cursor'] == descriptor['cursor'] and
             move_request['sequence'] == descriptor['sequence'], 'move-request-binding')
    if descriptor['state'] in ('ordinary_pp', 'exact_options'):
        _require(binding['request_state'] == 'move', 'descriptor-state')
    elif descriptor['state'] != 'unsupported':
        _require(binding['request_state'] == descriptor['state'], 'descriptor-state')
    _addressed(projection, owner, observation['event_cursor'])
    contract = _contract()
    for section in ('starting', 'current'):
        for fact in projection[section]:
            rules = [rule for rule in profile['rules'] if rule['context'] == section
                     and rule['property'] == fact['property'] and rule['family'] == fact['family']]
            _require(len(rules) == 1, 'property-scope')
            rule = rules[0]
            _require(fact['state'] in rule['states'], 'fact-state')
            _require(fact['reason'] in rule['reasons'][fact['state']] if 'reasons' in rule
                     else fact['reason'] == rule['reason'], 'fact-reason')
            _fact_shape(fact, contract, {rule['family']: [rule['property']]}, proofs=False)
    request = observation['request']
    _require(binding['request_state'] == _request_state(observation), 'request-state-binding')
    expected = []
    if request is not None:
        _request_shape(request, owner)
        _active_consistency(projection, request)
        legal = request['legal_actions']
        _require(len(legal['mask']) == len(legal['actions']) == 13, 'legal-shape')
        indices = [i for i, enabled in enumerate(legal['mask']) if enabled is True]
        _require(all(type(item) is bool for item in legal['mask']) and indices == legal['available_indices'], 'legal-mask')
        adapted = {**request, 'legal_actions': {i: legal['actions'][i] for i in indices}}
        expected = [canonical_action_from_legal_action(legal['actions'][i], adapted, owner) for i in indices]
    _require(canonical(frame['legal_actions']) == canonical(expected), 'legal-set')
    _require('action' not in frame or canonical(frame['action']) in {canonical(a) for a in expected}, 'chosen-action')
    return frame


def _pairs(entries):
    value = {}
    for key, item in entries:
        _require(key not in value, 'duplicate-key')
        value[key] = item
    return value


def read_frames(path):
    """Stream UTF-8 JSONL, preserving booleans, nulls and omitted fields."""
    with Path(path).open(encoding='utf-8') as source:
        for line in source:
            _require(len(line.encode('utf-8')) <= 16 * 1024 * 1024, 'wire-size')
            frame = json.loads(line, object_pairs_hook=_pairs,
                               parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
            yield validate_frame(frame)
