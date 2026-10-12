"""PK-02B-Source: non-publishing source and legacy verification seam.

A trusted local creation owner builds a registry capability and a legacy-context
capability inside this process; ``check_knowledge_source_binding`` joins an
already structurally valid audit to them. Capabilities are recognised only by
module-private weak-key membership, so dictionaries, copies, pickles and audit
fields cannot stand in. This is a trusted-caller boundary, not authentication
against code already controlling the process. Source presence never certifies
fact values; fact semantics, original attribution, obligation completeness and
aggregate completeness stay unverified/not_established. Nothing is published.
"""
import copy
import json
import re
import weakref

from neural.perspective_knowledge import (
    canonical_knowledge_json, check_knowledge_structure, knowledge_identity, parse_knowledge_json,
)
from neural.pipeline_record import _prefix as _legacy_prefix, validate_pipeline_bundle
from neural.public_boosts import validate_public_boosts
from neural.ts_identity import verify_belief, verify_observation
from neural.typed_state import validate_public_typed_state

LIVE_POLICY = 'simulator-causal/v1'
OWNERS = ('p1', 'p2')
ORIGIN_CONSTANTS = {'format': 'gen9randombattle', 'engine': 'pokemon-showdown@0.11.10', 'rule_version': 'pk-rules/v1'}
_NATIVE = {
    'observation': re.compile(r'obs-[0-9a-f]{64}'), 'belief': re.compile(r'belief-[0-9a-f]{64}'),
    'transition': re.compile(r'transition-[0-9a-f]{64}'), 'actor_record': re.compile(r'datarec-[0-9a-f]{64}'),
}
_TOKEN = object()
_REGISTRIES = weakref.WeakKeyDictionary()
_CONTEXTS = weakref.WeakKeyDictionary()


class KnowledgeSourceError(ValueError):
    """Payload-independent failure: ``code`` is a fixed string, never audit or source content."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _need(condition, code):
    if not condition:
        raise KnowledgeSourceError(code)


def _same(a, b):
    return canonical_knowledge_json(a) == canonical_knowledge_json(b)


def _snapshot(value, code):
    try:
        return parse_knowledge_json(canonical_knowledge_json(value))
    except Exception:
        pass
    # Raised after the handler so no payload-bearing __context__ is retained.
    raise KnowledgeSourceError(code)


def _is_prefix(shorter, longer):
    return len(shorter) <= len(longer) and list(longer[:len(shorter)]) == list(shorter)


class _Opaque:
    """Capability base: immutable, no copy/pickle path."""
    __slots__ = ('availability', '__weakref__')

    def __setattr__(self, name, value):
        raise AttributeError('capability is immutable')

    def __copy__(self):
        raise TypeError('capability cannot be copied')

    def __deepcopy__(self, memo):
        raise TypeError('capability cannot be copied')

    def __reduce_ex__(self, protocol):
        raise TypeError('capability cannot be serialized')


class SourceRegistry(_Opaque):
    """Opaque frozen registry capability. Only ``SourceRegistryBuilder.freeze`` creates one."""
    __slots__ = ()

    def __init__(self, token, data):
        _need(token is _TOKEN, 'capability/registry')
        _REGISTRIES[self] = data
        object.__setattr__(self, 'availability', {
            'origin': data['origin'] is not None,
            # Test-owned initialization witnesses only. No production original provider is adopted.
            'initialization_witness_owners': sorted(data['initialization']),
            'original_provider': 'not_adopted',
            'request_deliveries': len(data['requests']),
            'public_ledger': data['ledger'] is not None,
            'replay_source': data['replay'] is not None,
        })


class SourceRegistryBuilder:
    """Trusted-owner construction. Inputs are deep-copied; the builder is unusable after ``freeze``."""

    def __init__(self):
        self._data = {'origin': None, 'initialization': {}, 'requests': {}, 'ledger': None, 'replay': None}

    def _open(self):
        _need(self._data is not None, 'registry/frozen')
        return self._data

    def set_origin(self, origin):
        data = self._open(); _need(data['origin'] is None, 'registry/duplicate')
        copy = _snapshot(origin, 'registry/origin')
        _need(type(copy) is dict and sorted(copy) == ['battle_key', 'engine', 'format', 'rule_version']
              and type(copy['battle_key']) is str and copy['battle_key'], 'registry/origin')
        _need(all(copy[key] == value for key, value in ORIGIN_CONSTANTS.items()), 'registry/origin')
        data['origin'] = copy

    def add_initialization_witness(self, owner, team):
        """Test-owned witness: never evidence that a production provider exists."""
        data = self._open(); _need(owner in OWNERS and owner not in data['initialization'], 'registry/initialization')
        copy = _snapshot(team, 'registry/initialization')
        _need(type(copy) is list and 1 <= len(copy) <= 6
              and all(type(s) is dict and s.get('slot') == i + 1 for i, s in enumerate(copy)), 'registry/initialization')
        data['initialization'][owner] = copy

    def add_request_delivery(self, owner, sequence, cursor, json_text):
        data = self._open(); key = (owner, sequence)
        _need(owner in OWNERS and type(sequence) is int and sequence >= 0 and type(cursor) is int and cursor >= 0
              and type(json_text) is str and key not in data['requests'], 'registry/request')
        _snapshot({'raw_request': {'json': json_text}}, 'registry/request')  # exact text must obey raw-request limits
        data['requests'][key] = (cursor, json_text)

    def set_public_ledger(self, records):
        data = self._open(); _need(data['ledger'] is None, 'registry/duplicate')
        _need(type(records) in (list, tuple), 'registry/ledger')
        data['ledger'] = _snapshot(list(records), 'registry/ledger')

    def set_replay_source(self, records):
        """Explicit owner-selected local replay source evidence; no external loading."""
        data = self._open(); _need(data['replay'] is None, 'registry/duplicate')
        _need(type(records) in (list, tuple), 'registry/replay')
        data['replay'] = _snapshot(list(records), 'registry/replay')

    def freeze(self):
        data = self._open()
        for owner in OWNERS:
            rows = sorted((seq, cursor) for (o, seq), (cursor, _) in data['requests'].items() if o == owner)
            _need(all(seq == i and (i == 0 or cursor >= rows[i - 1][1])
                      and (data['ledger'] is None or cursor <= len(data['ledger'])) for i, (seq, cursor) in enumerate(rows)),
                  'registry/request-order')
        self._data = None
        return SourceRegistry(_TOKEN, copy.deepcopy(data))


# ----------------------------------------------------------- legacy context


class LegacyEnvelopeAdapter:
    """Later envelope kinds plug in here; ``verify`` must call the actual existing validators.

    ``verify`` returns a dict with owner, battle_id, input_observation, successor_observation,
    input_belief, successor_belief, transition, actor_record (the last two null together for
    nonactor evidence), input_prefix and successor_prefix.
    """
    schema_version = None

    def verify(self, envelope):
        raise NotImplementedError


class _OrdinaryBundleAdapter(LegacyEnvelopeAdapter):
    schema_version = 'pipeline-linked-record/v1'

    def verify(self, envelope):
        bundle = json.loads(json.dumps(envelope))  # snapshot
        record = validate_pipeline_bundle(bundle)  # actual existing validator; DATA object stays internal
        return {
            'owner': bundle['perspective'], 'battle_id': bundle['battle_id'],
            'input_observation': bundle['input_observation']['observation_id'],
            'successor_observation': bundle['successor_observation']['observation_id'],
            'input_belief': bundle['input_belief']['belief_id'], 'successor_belief': bundle['successor_belief']['belief_id'],
            'transition': bundle['transition']['transition_id'], 'actor_record': record['record_id'],
            'input_prefix': list(bundle['input_observation']['protocol_prefix']),
            'successor_prefix': list(bundle['successor_observation']['protocol_prefix']),
        }


class LegacyContext(_Opaque):
    """Opaque frozen locally verified legacy-context capability."""
    __slots__ = ()

    def __init__(self, token, data):
        _need(token is _TOKEN, 'capability/legacy')
        _CONTEXTS[self] = data
        object.__setattr__(self, 'availability', {
            'pairs': len(data['pairs']),
            'nonactor_pairs': sum(1 for p in data['pairs'].values() if p['transition'] is None),
            'envelope_kinds': sorted(data['kinds']),
        })


def _pair_key(owner, input_observation, successor_observation):
    return (owner, input_observation, successor_observation)


class LegacyContextBuilder:
    def __init__(self, extra_adapters=()):
        self._data = {'pairs': {}, 'observations': {}, 'kinds': set()}
        ordinary = _OrdinaryBundleAdapter()
        self._adapters = {ordinary.schema_version: ordinary}
        for adapter in extra_adapters:
            _need(isinstance(adapter, LegacyEnvelopeAdapter) and isinstance(adapter.schema_version, str)
                  and adapter.schema_version not in self._adapters, 'legacy/adapter')
            self._adapters[adapter.schema_version] = adapter

    def _open(self):
        _need(self._data is not None, 'legacy/frozen')
        return self._data

    def add_envelope(self, envelope):
        """Verifies a supplied envelope with its adapter; unsupported kinds fail explicitly."""
        data = self._open()
        kind = envelope.get('schema_version') if isinstance(envelope, dict) else None
        adapter = self._adapters.get(kind) if isinstance(kind, str) else None
        _need(adapter is not None, 'legacy/unsupported-envelope-kind')
        evidence = None
        try:
            evidence = adapter.verify(envelope)
        except KnowledgeSourceError:
            raise
        except Exception:
            pass
        _need(evidence is not None, 'legacy/validator-rejected')
        self._record(data, evidence, adapter.schema_version)

    def add_nonactor_evidence(self, owner, input_pair, successor_pair):
        """Real validated observation/belief evidence for an owner that did not act; no DATA row exists.

        Each pair is ``(observation, belief)``.
        """
        data = self._open()
        evidence = None
        try:
            copy = json.loads(json.dumps([owner, list(input_pair), list(successor_pair)]))
            owner, (before, before_belief), (after, after_belief) = copy
            for label, observation, belief in (('input', before, before_belief), ('successor', after, after_belief)):
                verify_observation(observation, label)
                validate_public_typed_state(observation, label)
                if observation['schema_version'] == 'observable-battle-state/v2':
                    validate_public_boosts(observation)
                _legacy_prefix(observation, label)
                verify_belief(belief, observation, label)
                _need(belief['battle_id'] == observation['battle_id'] and belief['perspective'] == observation['perspective'] == owner
                      and belief['source_protocol_prefix'] == observation['protocol_prefix'], 'legacy/validator-rejected')
            _need(before['battle_id'] == after['battle_id'] and _is_prefix(before['protocol_prefix'], after['protocol_prefix'])
                  and after_belief['parent_belief_id'] == before_belief['belief_id'], 'legacy/validator-rejected')
            evidence = {
                'owner': owner, 'battle_id': before['battle_id'],
                'input_observation': before['observation_id'], 'successor_observation': after['observation_id'],
                'input_belief': before_belief['belief_id'], 'successor_belief': after_belief['belief_id'],
                'transition': None, 'actor_record': None,
                'input_prefix': list(before['protocol_prefix']), 'successor_prefix': list(after['protocol_prefix']),
            }
        except KnowledgeSourceError:
            raise
        except Exception:
            pass
        _need(evidence is not None, 'legacy/validator-rejected')
        self._record(data, evidence, 'nonactor-observation-belief')

    def _record(self, data, e, kind):
        shaped = (isinstance(e, dict) and e.get('owner') in OWNERS and type(e.get('battle_id')) is str
                  and _NATIVE['observation'].fullmatch(str(e.get('input_observation')))
                  and _NATIVE['observation'].fullmatch(str(e.get('successor_observation')))
                  and _NATIVE['belief'].fullmatch(str(e.get('input_belief'))) and _NATIVE['belief'].fullmatch(str(e.get('successor_belief')))
                  and (e.get('transition') is None) == (e.get('actor_record') is None)
                  and (e.get('transition') is None or (_NATIVE['transition'].fullmatch(str(e['transition']))
                                                       and _NATIVE['actor_record'].fullmatch(str(e['actor_record']))))
                  and isinstance(e.get('input_prefix'), list) and isinstance(e.get('successor_prefix'), list)
                  and _is_prefix(e['input_prefix'], e['successor_prefix']))
        _need(shaped, 'legacy/adapter-result')
        pair = json.loads(json.dumps(e)); key = _pair_key(pair['owner'], pair['input_observation'], pair['successor_observation'])
        _need(key not in data['pairs'], 'legacy/duplicate')
        for observation, belief, prefix in ((pair['input_observation'], pair['input_belief'], pair['input_prefix']),
                                            (pair['successor_observation'], pair['successor_belief'], pair['successor_prefix'])):
            known = data['observations'].get(observation)
            _need(known is None or (known['owner'] == pair['owner'] and known['belief'] == belief
                                    and known['battle_id'] == pair['battle_id'] and known['prefix'] == prefix), 'legacy/inconsistent')
            data['observations'][observation] = {'owner': pair['owner'], 'battle_id': pair['battle_id'], 'belief': belief, 'prefix': list(prefix)}
        data['pairs'][key] = pair; data['kinds'].add(kind)

    def freeze(self):
        data = self._open(); self._data = None
        return LegacyContext(_TOKEN, copy.deepcopy(data))


# -------------------------------------------------------------------- check


def _expand(audit):
    return {kind: (list(rows.values()) if audit['form'] == 'compact' else list(rows)) for kind, rows in audit['tables'].items()}


def _join_sources(tables, audit, data, policy):
    origin = next(row for row in tables['origin'] if row['id'] == audit['origin'])
    _need(data['origin'] is not None, 'source/missing-origin')
    expected = {'kind': 'origin', **data['origin']}
    _need(origin['id'] == knowledge_identity(expected) and _same({k: v for k, v in origin.items() if k != 'id'}, expected), 'source/foreign-origin')
    ledger = data['ledger'] if policy == LIVE_POLICY else data['replay']
    init_owners = set(); deliveries = 0; replay = False
    # Fixed type order keeps the first reported code deterministic.
    rank = {'owner_initialization': 0, 'owner_request': 1, 'public_replay': 2, 'public_prefix': 3}
    for source in sorted(tables['source'], key=lambda row: rank[row['source_type']]):
        kind = source['source_type']
        if kind == 'owner_initialization':
            held = data['initialization'].get(source['owner'])
            _need(held is not None, 'source/missing-original-authority')
            _need(_same(source['team'], held) and source['raw_request'] is None and not source['records'], 'source/original-team')
            init_owners.add(source['owner'])
        elif kind == 'owner_request':
            held = data['requests'].get((source['owner'], source['delivery_seq']))
            _need(held is not None, 'source/missing-request-delivery')
            _need(held[0] == source['delivery_cursor'], 'source/request-cursor')
            _need(source['raw_request'] is not None and held[1] == source['raw_request']['json'] and not source['records'], 'source/request-text')
            deliveries += 1
        elif kind == 'public_prefix':
            _need(ledger is not None, 'source/missing-public-ledger')
            _need(_is_prefix(source['records'], ledger), 'source/public-prefix')
        else:  # public_replay
            _need(data['replay'] is not None, 'source/missing-replay-source')
            _need(_same(source['records'], data['replay']), 'source/replay-source')
            replay = True
    for prefix in tables['prefix']:
        _need(ledger is not None, 'source/missing-public-ledger')
        _need(_is_prefix(prefix['records'], ledger), 'source/prefix')
    return init_owners, deliveries, replay


def _join_legacy(tables, audit, data):
    by_id = {row['id']: row for rows in tables.values() for row in rows}
    origin = by_id[audit['origin']]
    for boundary in tables['boundary']:
        for row in boundary['bindings']:
            seen = data['observations'].get(row['observation_id'])
            _need(seen is not None and seen['owner'] == row['owner'] and seen['battle_id'] == origin['battle_key'], 'legacy/observation')
            _need(row['belief_id'] == seen['belief'], 'legacy/belief')
            current = by_id[by_id[row['knowledge']]['current']]
            _need(by_id[current['prefix']]['records'] == seen['prefix'], 'legacy/prefix')
            _need(boundary['index'] > 0 or row['actor_record_id'] is None, 'legacy/initial-actor')
    for binding in tables['binding']:
        pair = data['pairs'].get(_pair_key(binding['owner'], binding['input_observation'], binding['successor_observation']))
        _need(pair is not None and pair['battle_id'] == origin['battle_key'], 'legacy/missing-pair')
        _need(binding['input_belief'] == pair['input_belief'] and binding['successor_belief'] == pair['successor_belief'], 'legacy/belief')
        _need(binding['transition'] == pair['transition'], 'legacy/transition')
        _need(binding['actor_record'] == pair['actor_record'], 'legacy/actor-record')
    return len(tables['boundary']), len(tables['binding'])


def check_knowledge_source_binding(audit, registry, legacy, required_profile):
    """Entry check: accepted structure first, then declared source and legacy joins.

    ``legacy`` may be None to run the source join alone; that is reported as a
    missing capability, never as success of the legacy scope.
    """
    _need(type(required_profile) is str, 'profile')
    copy = _snapshot(audit, 'structure')  # one immutable view for every later step
    structure_ok = False
    try:
        check_knowledge_structure(copy, required_profile)
        structure_ok = True
    except Exception:
        pass
    _need(structure_ok, 'structure')
    registry_data = _REGISTRIES.get(registry) if type(registry) is SourceRegistry else None
    _need(registry_data is not None, 'capability/registry')
    legacy_data = None
    if legacy is not None:
        legacy_data = _CONTEXTS.get(legacy) if type(legacy) is LegacyContext else None
        _need(legacy_data is not None, 'capability/legacy')
    tables = _expand(copy)
    policy = next(row for row in tables['profile'] if row['id'] == copy['required_profile'])['policy']
    init_owners, deliveries, replay = _join_sources(tables, copy, registry_data, policy)
    joined = _join_legacy(tables, copy, legacy_data) if legacy_data is not None else None
    return {
        'structure_valid': True,
        'source_verification': {
            'scope': 'declared_source_rows_exact_match', 'verified': True, 'sources': len(tables['source']),
            'prefixes': len(tables['prefix']), 'request_deliveries': deliveries,
            'original_delivery': 'test_only_unverified' if len(init_owners) == 2 else ('partial' if init_owners else 'absent'), 'replay_source': replay,
        },
        'legacy_verification': {
            'scope': 'declared_external_positions' if joined else 'not_checked', 'verified': joined is not None,
            'boundaries': joined[0] if joined else 0, 'bindings': joined[1] if joined else 0,
            'envelope_kinds': sorted(legacy_data['kinds']) if legacy_data else [],
        },
        'fact_semantics': 'unverified', 'original_attribution': 'unverified',
        'obligation_completeness': 'not_established', 'completeness': 'not_established',
        'missing_capabilities': ([] if joined else ['legacy_context']) + ([] if len(init_owners) == 2 else ['original_delivery_authority']) + ['original_provider'],
        'unsupported_capabilities': ['original_provider', 'fact_semantics', 'original_attribution', 'family_obligations'],
        'published': False,
    }
