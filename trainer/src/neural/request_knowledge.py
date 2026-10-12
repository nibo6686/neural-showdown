"""request-knowledge/v1 sidecar (Prompt 14 / S01b), Python side.

``build_request_knowledge`` mirrors the TypeScript builder. ``validate_request_knowledge`` is an independent
checker: it re-derives every field from ``raw_request`` with its own grammar and joins the result to the
unchanged v1/v2 observation. Without a delivery registry it is structure-only about who was delivered the
text. Pure functions; nothing here feeds legal-action construction. See docs/contracts/REQUEST_KNOWLEDGE.md.
"""
import hashlib
import json
import re
import sys

from neural.perspective_knowledge import KnowledgeStructureError, parse_knowledge_json
from neural.ts_identity import verify_observation

SCHEMA = 'request-knowledge/v1'
FRESH_DELIVERY = 'fresh_delivery'
OWNERS = ('p1', 'p2')
OBSERVATION_SCHEMAS = ('observable-battle-state/v1', 'observable-battle-state/v2')
PRESENCES = ('actionable', 'waiting', 'forced_switch', 'revival_selection', 'requestless', 'terminal')
LOCKS = ('no_hard_lock', 'locked_move', 'recharge', 'struggle')
MAX_RAW_SCALARS = 65536
MAX_INT = 2147483647
TOP_KEYS = ('schema_version', 'id', 'battle_id', 'perspective', 'observation_schema_version', 'observation_id', 'event_cursor',
            'presence', 'request_present', 'raw_request', 'rqid', 'active')
ACTIVE_KEYS = ('lock', 'trapped', 'maybe_trapped', 'maybe_disabled', 'switch_in_available', 'derivation', 'moves')
DERIVATION_VALUES = {
    'lock': ('bare_single_row', 'pp_bearing_rows'),
    'trapped': ('raw_true', 'omitted_with_switch_in', 'omitted_without_switch_in'),
    'maybe_trapped': ('raw_true', 'superseded_by_trapped', 'omitted_with_switch_in', 'omitted_without_switch_in'),
    'maybe_disabled': ('raw_true', 'omitted_singles_rule'),
}
MOVE_KEYS = ('slot', 'id', 'name', 'pp', 'max_pp', 'target', 'disabled')


class RequestKnowledgeError(ValueError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _need(condition, code):
    if not condition:
        raise RequestKnowledgeError(code)


def _is_int(value):
    return type(value) is int and 0 <= value <= MAX_INT


def _is_str(value, limit=256):
    return type(value) is str and len(value) <= limit and not any(0xD800 <= ord(c) <= 0xDFFF for c in value)


def canonical_request_knowledge_json(value):
    """Canonical bytes: ASCII keys sorted, minimal integers, UTF-8 strings, no normalization; floats and bool-as-int reject."""
    def visit(item, key=''):
        if item is None: return 'null'
        if type(item) is bool: return 'true' if item else 'false'
        if type(item) is int:
            _need(0 <= item <= MAX_INT, 'wire-number'); return str(item)
        if type(item) is str:
            _need(_is_str(item, MAX_RAW_SCALARS if key == 'raw_request' else 256), 'wire-size'); return json.dumps(item, ensure_ascii=False)
        if type(item) is list: return '[' + ','.join(visit(entry) for entry in item) + ']'
        _need(type(item) is dict and all(type(k) is str and k.isascii() for k in item), 'wire-type')
        return '{' + ','.join(json.dumps(k) + ':' + visit(item[k], k) for k in sorted(item)) + '}'
    return visit(value).encode('utf-8')


def request_knowledge_id(record):
    body = {k: v for k, v in record.items() if k != 'id'}
    return 'rkn-' + hashlib.sha256((SCHEMA + '\n').encode('ascii') + canonical_request_knowledge_json(body)).hexdigest()


def _fainted(condition):
    return condition == 'fnt' or condition.endswith(' fnt')


# ------------------------------------------------------------------------------------------------ builder


def _parse_raw(owner, text):
    _need(type(text) is str and len(text) <= MAX_RAW_SCALARS, 'raw-size')
    try:
        raw = parse_knowledge_json(text)
    except KnowledgeStructureError:
        raise RequestKnowledgeError('raw-json') from None
    _need(type(raw) is dict, 'raw-grammar')
    _need(not raw.get('teamPreview'), 'team-preview')
    _need(set(raw) <= {'active', 'wait', 'forceSwitch', 'side', 'rqid', 'noCancel'}, 'raw-grammar')
    _need(sum(key in raw for key in ('active', 'wait', 'forceSwitch')) == 1, 'raw-grammar')
    _need('rqid' not in raw or _is_int(raw['rqid']), 'raw-grammar')
    _need('noCancel' not in raw or (raw['noCancel'] is True and 'forceSwitch' in raw), 'raw-grammar')
    side = raw.get('side')
    _need(type(side) is dict and set(side) <= {'name', 'id', 'pokemon'} and type(side.get('name')) is str, 'raw-grammar')
    _need(type(side.get('pokemon')) is list and 1 <= len(side['pokemon']) <= 6, 'raw-grammar')
    _need(side.get('id') == owner, 'wrong-owner')
    for pokemon in side['pokemon']:
        _need(type(pokemon) is dict and type(pokemon.get('ident')) is str and type(pokemon.get('condition')) is str
              and type(pokemon.get('active')) is bool, 'raw-grammar')
        _need(pokemon['ident'].startswith(owner + ': '), 'wrong-owner')
    actives = sum(p['active'] for p in side['pokemon'])
    _need(actives <= 1, 'doubles')
    _need(actives == 1, 'raw-grammar')
    if 'wait' in raw:
        _need(raw['wait'] is True, 'raw-grammar')
        return 'waiting', raw
    if 'forceSwitch' in raw:
        _need(type(raw['forceSwitch']) is list, 'raw-grammar')
        _need(len(raw['forceSwitch']) <= 1, 'doubles')
        _need(raw['forceSwitch'] == [True], 'raw-grammar')
        return ('revival_selection' if any(p.get('reviving') is True for p in side['pokemon']) else 'forced_switch'), raw
    _need(type(raw['active']) is list, 'raw-grammar')
    _need(len(raw['active']) <= 1, 'doubles')
    _need(len(raw['active']) == 1 and type(raw['active'][0]) is dict, 'raw-grammar')
    return 'actionable', raw


def _derive_active(raw):
    source = raw['active'][0]
    _need(set(source) <= {'moves', 'maybeDisabled', 'maybeTrapped', 'trapped', 'canTerastallize'}, 'raw-grammar')
    _need(all(source.get(key, True) is True for key in ('maybeDisabled', 'maybeTrapped', 'trapped')), 'raw-grammar')
    _need('canTerastallize' not in source or type(source['canTerastallize']) is str, 'raw-grammar')
    _need(type(source.get('moves')) is list and 1 <= len(source['moves']) <= 4, 'raw-grammar')
    rows = []
    for index, row in enumerate(source['moves']):
        _need(type(row) is dict and set(row) <= {'move', 'id', 'pp', 'maxpp', 'target', 'disabled'}, 'raw-grammar')
        _need(type(row.get('move')) is str and row['move'] and type(row.get('id')) is str and row['id'], 'raw-grammar')
        _need(_is_str(row['move']) and _is_str(row['id']) and ('target' not in row or _is_str(row['target'])), 'raw-grammar')
        _need('pp' not in row or _is_int(row['pp']), 'raw-grammar')
        _need('maxpp' not in row or _is_int(row['maxpp']), 'raw-grammar')
        _need('target' not in row or type(row['target']) is str, 'raw-grammar')
        _need('disabled' not in row or type(row['disabled']) is bool, 'raw-grammar')
        rows.append({'slot': index + 1, 'id': row['id'], 'name': row['move'], 'pp': row.get('pp'), 'max_pp': row.get('maxpp'),
                     'target': row.get('target'), 'disabled': row.get('disabled')})
    locked_shape = len(rows) == 1 and rows[0]['pp'] is None and rows[0]['max_pp'] is None
    lock = 'no_hard_lock' if not locked_shape else {'recharge': 'recharge', 'struggle': 'struggle'}.get(rows[0]['id'], 'locked_move')
    switch_in = any(not p['active'] and not _fainted(p['condition']) for p in raw['side']['pokemon'])
    _need(not ('trapped' in source and 'maybeTrapped' in source), 'raw-grammar')
    omitted = 'omitted_with_switch_in' if switch_in else 'omitted_without_switch_in'
    trapped = True if 'trapped' in source else (False if switch_in else None)
    maybe_trapped = True if 'maybeTrapped' in source else (False if 'trapped' in source or switch_in else None)
    return {
        'lock': lock, 'trapped': trapped, 'maybe_trapped': maybe_trapped, 'maybe_disabled': 'maybeDisabled' in source,
        'switch_in_available': switch_in,
        'derivation': {
            'lock': 'bare_single_row' if locked_shape else 'pp_bearing_rows',
            'trapped': 'raw_true' if 'trapped' in source else omitted,
            'maybe_trapped': 'raw_true' if 'maybeTrapped' in source else ('superseded_by_trapped' if 'trapped' in source else omitted),
            'maybe_disabled': 'raw_true' if 'maybeDisabled' in source else 'omitted_singles_rule',
        },
        'moves': rows,
    }


def _builder_join(owner, kind, raw, active, observation):
    request = observation['request']
    _need(type(request) is dict and request.get('player') == owner and not request.get('team_preview'),
          'team-preview' if type(request) is dict and request.get('team_preview') else 'observation-mismatch')
    _need(request['wait'] is (kind == 'waiting') and request['force_switch'] is (kind in ('forced_switch', 'revival_selection')), 'presence-mismatch')
    _need(request.get('rqid') == raw.get('rqid'), 'observation-mismatch')
    pokemon = raw['side']['pokemon']
    _need(len(pokemon) == len(request['side']) and all(
        seen['ident'] == p['ident'] and seen['condition'] == p['condition'] and seen['active'] is p['active']
        and (seen.get('reviving') is True) == (p.get('reviving') is True) for seen, p in zip(request['side'], pokemon)), 'observation-mismatch')
    _need(kind == 'waiting' or (observation['decision_availability']['available'] and request['legal_actions']['available_indices']), 'no-legal-actions')
    if active is None:
        _need(request['active'] is None, 'observation-mismatch')
        return
    seen = request['active']
    _need(type(seen) is dict and len(seen['moves']) == len(active['moves']), 'observation-mismatch')
    for row, carried in zip(active['moves'], seen['moves']):
        _need(carried['slot'] == row['slot'] and carried['id'] == row['id'] and carried['move'] == row['name']
              and carried['pp'] == (0 if row['pp'] is None else row['pp']) and carried['maxpp'] == (0 if row['max_pp'] is None else row['max_pp'])
              and carried['target'] == ('normal' if row['target'] is None else row['target'])
              and carried['disabled'] is (row['disabled'] is True), 'observation-mismatch')
    _need(seen['trapped'] is (active['trapped'] is True) and request['trapped'] is (active['trapped'] is True), 'observation-mismatch')
    _need(seen['can_switch'] is (active['trapped'] is not True and active['switch_in_available']), 'observation-mismatch')
    _check_legality(request, active['moves'])


def _check_legality(request, rows):
    """A numbered move action needs a request-supplied enabled row with PP, or the request-supplied Struggle row."""
    for action in request['legal_actions']['actions']:
        if action is None or action['kind'] not in ('move', 'move_tera') or action['slot'] is None:
            continue
        row = rows[action['slot'] - 1] if 1 <= action['slot'] <= len(rows) else None
        _need(row is not None and row['disabled'] is not True
              and ((row['pp'] is not None and row['pp'] > 0) or (row['id'] == 'struggle' and row['pp'] is None)), 'legality-mismatch')


def build_request_knowledge(owner, raw_text, observation, provenance):
    _need(provenance == FRESH_DELIVERY, 'provenance')
    _need(owner in OWNERS and type(observation) is dict and observation.get('perspective') == owner, 'wrong-owner')
    _need(observation.get('schema_version') in OBSERVATION_SCHEMAS and re.fullmatch(r'obs-[0-9a-f]{64}', str(observation.get('observation_id')))
          and _is_int(observation.get('event_cursor')) and _is_str(observation.get('battle_id')) and observation['battle_id'], 'observation-mismatch')
    raw, active = None, None
    if observation['view']['terminated']:
        presence = 'terminal'
        _need(raw_text is None and observation['request'] is None, 'presence-mismatch')
    elif observation['request'] is None:
        presence = 'requestless'
        _need(raw_text is None, 'presence-mismatch')
    else:
        _need(type(raw_text) is str, 'presence-mismatch')
        presence, raw = _parse_raw(owner, raw_text)
        active = _derive_active(raw) if presence == 'actionable' else None
        _builder_join(owner, presence, raw, active, observation)
    record = {
        'schema_version': SCHEMA, 'id': '', 'battle_id': observation['battle_id'], 'perspective': owner,
        'observation_schema_version': observation['schema_version'], 'observation_id': observation['observation_id'],
        'event_cursor': observation['event_cursor'], 'presence': presence, 'request_present': raw_text is not None,
        'raw_request': raw_text, 'rqid': None if raw is None else raw.get('rqid'), 'active': active,
    }
    record['id'] = request_knowledge_id(record)
    return record


# ---------------------------------------------------------------------------------------------- validator


def _wire(record):
    """(1) Strict wire shape: exact keys, bool is not int, no floats, bounded strings."""
    _need(type(record) is dict and tuple(sorted(record)) == tuple(sorted(TOP_KEYS)), 'wire-keys')
    _need(record['schema_version'] == SCHEMA and type(record['id']) is str and re.fullmatch(r'rkn-[0-9a-f]{64}', record['id']), 'wire-type')
    _need(_is_str(record['battle_id']) and record['battle_id'] and record['perspective'] in OWNERS
          and record['observation_schema_version'] in OBSERVATION_SCHEMAS and type(record['observation_id']) is str
          and re.fullmatch(r'obs-[0-9a-f]{64}', record['observation_id']) and _is_int(record['event_cursor']), 'wire-type')
    _need(record['presence'] in PRESENCES and type(record['request_present']) is bool, 'wire-type')
    _need(record['raw_request'] is None or _is_str(record['raw_request'], MAX_RAW_SCALARS), 'wire-size')
    _need(record['rqid'] is None or _is_int(record['rqid']), 'wire-type')
    _need(record['request_present'] is (record['raw_request'] is not None), 'wire-type')
    active = record['active']
    if active is None:
        return
    _need(type(active) is dict and tuple(sorted(active)) == tuple(sorted(ACTIVE_KEYS)), 'wire-keys')
    _need(active['lock'] in LOCKS and type(active['switch_in_available']) is bool and type(active['maybe_disabled']) is bool, 'wire-type')
    _need(all(active[k] is None or type(active[k]) is bool for k in ('trapped', 'maybe_trapped')), 'wire-type')
    derivation = active['derivation']
    _need(type(derivation) is dict and sorted(derivation) == sorted(DERIVATION_VALUES)
          and all(derivation[k] in DERIVATION_VALUES[k] for k in DERIVATION_VALUES), 'wire-keys')
    _need(type(active['moves']) is list and 1 <= len(active['moves']) <= 4, 'wire-size')
    for move in active['moves']:
        _need(type(move) is dict and tuple(sorted(move)) == tuple(sorted(MOVE_KEYS)), 'wire-keys')
        _need(_is_int(move['slot']) and _is_str(move['id']) and _is_str(move['name']), 'wire-type')
        _need(all(move[k] is None or _is_int(move[k]) for k in ('pp', 'max_pp')), 'wire-type')
        _need(move['target'] is None or _is_str(move['target']), 'wire-type')
        _need(move['disabled'] is None or type(move['disabled']) is bool, 'wire-type')


def _audit(perspective, text):
    """(2) Independent grammar: returns what the raw text alone entitles the record to say."""
    try:
        raw = parse_knowledge_json(text)
    except KnowledgeStructureError:
        raise RequestKnowledgeError('raw-json') from None
    _need(isinstance(raw, dict) and 'teamPreview' not in raw, 'team-preview')
    kinds = [k for k in ('active', 'wait', 'forceSwitch') if k in raw]
    _need(len(kinds) == 1 and not set(raw) - {kinds[0], 'side', 'rqid', 'noCancel'}, 'raw-grammar')
    side = raw.get('side')
    _need(isinstance(side, dict) and not set(side) - {'name', 'id', 'pokemon'} and isinstance(side.get('name'), str)
          and isinstance(side.get('pokemon'), list) and 1 <= len(side['pokemon']) <= 6, 'raw-grammar')
    _need(side.get('id') == perspective, 'wrong-owner')
    _need(all(isinstance(p, dict) and isinstance(p.get('ident'), str) and isinstance(p.get('condition'), str)
              and type(p.get('active')) is bool for p in side['pokemon']), 'raw-grammar')
    _need(all(p['ident'].split(': ', 1)[0] == perspective for p in side['pokemon']), 'wrong-owner')
    _need(sum(1 for p in side['pokemon'] if p['active']) == 1, 'doubles' if sum(1 for p in side['pokemon'] if p['active']) > 1 else 'raw-grammar')
    if kinds[0] == 'forceSwitch':
        _need(isinstance(raw['forceSwitch'], list) and len(raw['forceSwitch']) <= 1, 'doubles')
        _need(raw['forceSwitch'] == [True], 'raw-grammar')
    _need(kinds[0] != 'wait' or raw['wait'] is True, 'raw-grammar')
    _need('rqid' not in raw or _is_int(raw['rqid']), 'raw-grammar')
    _need('noCancel' not in raw or (raw['noCancel'] is True and kinds[0] == 'forceSwitch'), 'raw-grammar')
    return kinds[0], raw, side['pokemon']


def _expected_flags(source, bench):
    """Pinned singles source rule: trapped/maybeTrapped are only emitted while a switch-in exists; maybeDisabled is always emitted."""
    return {
        'trapped': (True, 'raw_true') if source.get('trapped') is True else ((False, 'omitted_with_switch_in') if bench else (None, 'omitted_without_switch_in')),
        'maybe_trapped': (True, 'raw_true') if source.get('maybeTrapped') is True
        else (False, 'superseded_by_trapped') if source.get('trapped') is True
        else ((False, 'omitted_with_switch_in') if bench else (None, 'omitted_without_switch_in')),
        'maybe_disabled': (True, 'raw_true') if source.get('maybeDisabled') is True else (False, 'omitted_singles_rule'),
    }


def validate_request_knowledge(record, observation, *, delivery_registry=None):
    """Re-derive and join; raises RequestKnowledgeError(code). Returns the authority actually established."""
    _wire(record)
    try:
        verify_observation(observation, 'observation')
    except Exception:
        raise RequestKnowledgeError('observation-identity') from None
    # (6) stale cursor / observation, and the join keys.
    _need(record['observation_id'] == observation['observation_id'] and record['event_cursor'] == observation['event_cursor'], 'stale')
    _need(record['battle_id'] == observation['battle_id'] and record['observation_schema_version'] == observation['schema_version'], 'observation-mismatch')
    # (5) owner: the record, the observation and (below) the raw text must all name the same side.
    owner = record['perspective']
    _need(observation['perspective'] == owner, 'wrong-owner')
    request, terminated = observation['request'], observation['view']['terminated']
    text = record['raw_request']
    if terminated or request is None:
        _need(request is None, 'presence-mismatch')
        _need(record['presence'] == ('terminal' if terminated else 'requestless') and text is None and not record['request_present']
              and record['rqid'] is None and record['active'] is None, 'presence-mismatch')
    else:
        _need(text is not None, 'presence-mismatch')
        kind, raw, pokemon = _audit(owner, text)
        _need(request.get('player') == owner, 'wrong-owner')
        expected = {'wait': 'waiting', 'forceSwitch': 'revival_selection' if any(p.get('reviving') is True for p in pokemon) else 'forced_switch',
                    'active': 'actionable'}[kind]
        _need(record['presence'] == expected, 'presence-mismatch')
        _need(record['rqid'] == raw.get('rqid'), 'false-certainty')
        _validate_active(record, raw, kind, pokemon, request, observation)
        _validate_join(request, observation, record, pokemon, raw)
    # delivery authority
    authority = 'structure_only'
    if delivery_registry is not None:
        from neural.perspective_knowledge_source import SourceRegistry, _REGISTRIES
        data = _REGISTRIES.get(delivery_registry) if type(delivery_registry) is SourceRegistry else None
        _need(data is not None, 'registry-type')
        if text is not None:
            # The text must be the LATEST delivery to this owner at this cursor: an earlier one (for example the
            # pre-rejection request) is stale even though it was genuinely delivered.
            latest = max(((seq, held) for (o, seq), (cursor, held) in data['requests'].items()
                          if o == owner and cursor == record['event_cursor']), default=None)
            _need(latest is not None and latest[1] == text, 'registry-delivery')
        # Only a request text can be bound to a delivery; requestless/terminal claims stay structure-only.
        authority = 'registry_bound' if text is not None else 'structure_only'
    _need(record['id'] == request_knowledge_id(record), 'id')
    return {'record_id': record['id'], 'presence': record['presence'], 'delivery_authority': authority}


def _validate_active(record, raw, kind, pokemon, request, observation):
    active = record['active']
    if kind != 'active':
        _need(active is None, 'false-certainty')
        return
    source = raw['active']
    _need(isinstance(source, list) and len(source) == 1 and isinstance(source[0], dict), 'doubles' if isinstance(source, list) and len(source) > 1 else 'raw-grammar')
    source = source[0]
    _need(not set(source) - {'moves', 'maybeDisabled', 'maybeTrapped', 'trapped', 'canTerastallize'}, 'raw-grammar')
    _need(isinstance(source.get('canTerastallize', ''), str), 'raw-grammar')
    _need(all(source[k] is True for k in ('maybeDisabled', 'maybeTrapped', 'trapped') if k in source), 'raw-grammar')
    _need(not ('trapped' in source and 'maybeTrapped' in source), 'raw-grammar')
    rows = source.get('moves')
    _need(isinstance(rows, list) and 1 <= len(rows) <= 4, 'raw-grammar')
    _need(active is not None and len(active['moves']) == len(rows), 'false-certainty')
    for slot, (row, claimed) in enumerate(zip(rows, active['moves']), start=1):
        _need(isinstance(row, dict) and not set(row) - {'move', 'id', 'pp', 'maxpp', 'target', 'disabled'}, 'raw-grammar')
        _need(isinstance(row.get('move'), str) and row['move'] and isinstance(row.get('id'), str) and row['id'], 'raw-grammar')
        _need(all(_is_int(row[k]) for k in ('pp', 'maxpp') if k in row) and ('target' not in row or isinstance(row['target'], str))
              and ('disabled' not in row or type(row['disabled']) is bool), 'raw-grammar')
        _need(claimed['slot'] == slot and claimed['id'] == row['id'] and claimed['name'] == row['move'], 'false-certainty')
        for key, raw_key in (('pp', 'pp'), ('max_pp', 'maxpp'), ('target', 'target'), ('disabled', 'disabled')):
            # Absent in the raw row means unknown (null) - never a default; present means exactly that value.
            _need(claimed[key] == (row[raw_key] if raw_key in row else None) and type(claimed[key]) is type(row.get(raw_key)), 'false-certainty')
    bare = len(rows) == 1 and 'pp' not in rows[0] and 'maxpp' not in rows[0]
    _need(active['lock'] == (rows[0]['id'] if bare and rows[0]['id'] in ('recharge', 'struggle') else 'locked_move' if bare else 'no_hard_lock'), 'false-certainty')
    _need(active['derivation']['lock'] == ('bare_single_row' if bare else 'pp_bearing_rows'), 'false-certainty')
    bench = any(not p['active'] and not _fainted(p['condition']) for p in pokemon)
    _need(active['switch_in_available'] is bench, 'false-certainty')
    for key, (value, derivation) in _expected_flags(source, bench).items():
        _need(active[key] is value and active['derivation'][key] == derivation, 'false-certainty')
    _need(active['trapped'] is not True or active['maybe_trapped'] is not True, 'false-certainty')


def _validate_join(request, observation, record, pokemon, raw):
    """(3) The unchanged observation carries `value ?? legacy default`; (4) legality still follows the request only."""
    _need(request['wait'] is (record['presence'] == 'waiting')
          and request['force_switch'] is (record['presence'] in ('forced_switch', 'revival_selection')), 'presence-mismatch')
    _need(request.get('team_preview') is False, 'team-preview')
    _need(request.get('rqid') == record['rqid'], 'observation-mismatch')
    _need(len(request['side']) == len(pokemon) and all(
        seen['ident'] == p['ident'] and seen['condition'] == p['condition'] and seen['active'] is p['active']
        and (seen.get('reviving') is True) == (p.get('reviving') is True) for seen, p in zip(request['side'], pokemon)), 'observation-mismatch')
    if record['presence'] != 'waiting':
        _need(observation['decision_availability']['available'] and request['legal_actions']['available_indices'], 'no-legal-actions')
    active = record['active']
    if active is None:
        _need(request['active'] is None, 'observation-mismatch')
        return
    seen = request['active']
    _need(seen is not None and len(seen['moves']) == len(active['moves']), 'observation-mismatch')
    for claimed, carried in zip(active['moves'], seen['moves']):
        legacy = {'pp': 0, 'maxpp': 0, 'target': 'normal', 'disabled': False}
        for key, carried_key in (('pp', 'pp'), ('max_pp', 'maxpp'), ('target', 'target'), ('disabled', 'disabled')):
            value = claimed[key] if claimed[key] is not None else legacy[carried_key]
            _need(carried[carried_key] == value and type(carried[carried_key]) is type(value), 'observation-mismatch')
        _need(carried['slot'] == claimed['slot'] and carried['id'] == claimed['id'] and carried['move'] == claimed['name'], 'observation-mismatch')
    known_trap = active['trapped'] is True
    _need(seen['trapped'] is known_trap and request['trapped'] is known_trap
          and seen['can_switch'] is (not known_trap and active['switch_in_available']), 'observation-mismatch')
    _check_legality(request, active['moves'])


def main(argv=None):
    """CLI for cross-runtime checks. Reads a UTF-8 JSON list on stdin; writes one UTF-8 line per item to stdout bytes."""
    argv = sys.argv[1:] if argv is None else argv
    _need(len(argv) == 1 and argv[0] in ('build', 'validate'), 'cli')
    lines = []
    for item in json.loads(sys.stdin.buffer.read().decode('utf-8')):
        if argv[0] == 'build':
            lines.append(canonical_request_knowledge_json(build_request_knowledge(item['owner'], item['raw_request'], item['observation'], FRESH_DELIVERY)))
        else:
            lines.append(json.dumps(validate_request_knowledge(item['record'], item['observation']), ensure_ascii=False).encode('utf-8'))
    sys.stdout.buffer.write(b'\n'.join(lines) + b'\n')


if __name__ == '__main__':
    main()
