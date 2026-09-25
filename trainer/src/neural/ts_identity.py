"""Content identity verification for the TypeScript pipeline JSON wire format.

Absent keys stay absent. Legacy v1 abbreviated references are checked without
normalizing or rewriting the supplied payload. No version disables hash checks.
"""
import hashlib
import json
import math
import re
import unicodedata
from decimal import Decimal

OBSERVATION_VERSIONS = ('observable-battle-state/v1', 'observable-battle-state/v2')
REFERENCE_KEYS = ('schema_version', 'observation_id', 'source_kind', 'event_cursor', 'protocol_prefix_hash', 'snapshot_phase')


def _string(value):
    # JSON.stringify escapes lone surrogates but emits valid surrogate pairs as Unicode.
    value = value.encode('utf-16-le', 'surrogatepass').decode('utf-16-le', 'surrogatepass')
    return ''.join('\\u%04x' % ord(c) if 0xD800 <= ord(c) <= 0xDFFF else c
                   for c in json.dumps(value, ensure_ascii=False))


def canonical(value):
    if isinstance(value, dict):
        if any(not isinstance(k, str) for k in value): raise ValueError('JSON keys must be strings')
        keys = sorted(value, key=lambda k: k.encode('utf-16-be', 'surrogatepass'))
        return '{' + ','.join(_string(k) + ':' + canonical(value[k]) for k in keys) + '}'
    if isinstance(value, list): return '[' + ','.join(canonical(v) for v in value) + ']'
    if value is None: return 'null'
    if isinstance(value, bool): return 'true' if value else 'false'
    if isinstance(value, str): return _string(value)
    if isinstance(value, (int, float)):
        number = float(value)  # The source runtime uses binary64, including JSON integers.
        if not math.isfinite(number): raise ValueError('Nonfinite identity number')
        if number == 0: return '0'
        spelling = repr(number)
        if 1e-6 <= abs(number) < 1e21:
            fixed = format(Decimal(spelling), 'f')
            return fixed.rstrip('0').rstrip('.') if '.' in fixed else fixed
        mantissa, exponent = spelling.lower().split('e')
        return mantissa.removesuffix('.0') + 'e' + ('+' if int(exponent) >= 0 else '-') + str(abs(int(exponent)))
    raise ValueError('Unsupported identity value')


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf8')).hexdigest()


def observation_digest(value):
    return 'obs-' + digest({k: v for k, v in value.items() if k not in ('observation_id', 'protocol_prefix')})


def belief_digest(value):
    return 'belief-' + digest({k: v for k, v in value.items() if k != 'belief_id'})


def _require(ok, path, reason):
    if not ok: raise ValueError(path + ': ' + reason)


def verify_observation(observation, path):
    _require(observation.get('schema_version') in OBSERVATION_VERSIONS, path, 'unsupported version')
    _require(observation.get('observation_id') == observation_digest(observation), path, 'observation content identity mismatch')
    _require(observation.get('protocol_prefix_hash') == digest(observation['protocol_prefix']), path, 'prefix identity mismatch')
    _require(observation.get('event_cursor') == len(observation['protocol_prefix']), path, 'prefix cursor mismatch')


def _safe_integer(value):
    return type(value) in (int, float) and math.isfinite(value) and value == int(value) and abs(value) <= 9007199254740991


def _normalized(value):
    whitespace = '\u0009\u000a\u000b\u000c\u000d \u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff'
    return isinstance(value, str) and bool(value) and value == unicodedata.normalize('NFC', value).strip(whitespace)


def _verify_reference(ref, version, prefix, path):
    _require(isinstance(ref, dict), path, 'observation reference must be an object')
    allowed = (set(REFERENCE_KEYS), set(REFERENCE_KEYS) - {'schema_version'}) if version == OBSERVATION_VERSIONS[0] else (set(REFERENCE_KEYS),)
    _require(set(ref) in allowed, path, 'observation reference fields mismatch')
    _require(ref.get('schema_version', OBSERVATION_VERSIONS[0]) == version, path, 'observation reference version mismatch')
    _require(isinstance(ref['observation_id'], str) and re.fullmatch(r'obs-[a-f0-9]{64}', ref['observation_id']), path, 'observation reference identity malformed')
    _require(isinstance(ref['source_kind'], str) and ref['source_kind'] in ('sim_core', 'replay', 'live'), path, 'observation reference source_kind unsupported')
    _require(isinstance(ref['snapshot_phase'], str) and ref['snapshot_phase'] in ('pre_decision', 'post_resolution', 'forced_switch', 'terminal', 'other'), path, 'observation reference snapshot_phase unsupported')
    end = ref['event_cursor']
    _require(_safe_integer(end) and 0 <= end <= len(prefix), path, 'observation reference cursor invalid')
    _require(isinstance(ref['protocol_prefix_hash'], str) and re.fullmatch(r'[a-f0-9]{64}', ref['protocol_prefix_hash']), path, 'observation reference prefix hash malformed')
    _require(ref['protocol_prefix_hash'] == digest(prefix[:int(end)]), path, 'observation reference prefix mismatch')


def verify_belief(belief, observation, path):
    _require(belief.get('schema_version') == 'belief-state/v1', path, 'unsupported belief version')
    _require(belief.get('belief_id') == belief_digest(belief), path, 'belief content identity mismatch')
    version = observation['schema_version']
    current = belief['observation']
    expected = {k: observation[k] for k in REFERENCE_KEYS}
    _verify_reference(current, version, belief['source_protocol_prefix'], path + '.observation')
    _require(all(current[k] == expected[k] for k in current), path, 'observation reference content mismatch')
    history = belief.get('observation_history')
    _require(isinstance(history, list) and bool(history), path, 'observation history missing')
    seen, cursor = set(), -1
    for index, ref in enumerate(history):
        _verify_reference(ref, version, belief['source_protocol_prefix'], f'{path}.observation_history[{index}]')
        _require(ref['event_cursor'] >= cursor, path, 'historical cursor decreases')
        _require(ref['observation_id'] not in seen, path, 'duplicate historical observation identity')
        seen.add(ref['observation_id']); cursor = ref['event_cursor']
    _require(canonical(history[-1]) == canonical(current), path, 'current observation history mismatch')
    evidence = belief.get('evidence', [])
    ids = set()
    for entry in evidence:
        identity = {k: v for k, v in entry.items() if k != 'evidence_id'}
        _require(all(_normalized(entry.get(k)) for k in ('subject_key', 'value')), path, 'evidence strings are not normalized')
        _require(entry.get('perspective') == belief['perspective'] and entry.get('assertion') in ('supports', 'refutes'), path, 'evidence perspective/assertion mismatch')
        _require(set(identity) == {'perspective', 'category', 'subject_key', 'value', 'assertion', 'provenance'}, path, 'evidence fields mismatch')
        _require(entry.get('evidence_id') == 'evidence-' + digest(identity), path, 'nested evidence identity mismatch')
        _require(entry['evidence_id'] not in ids, path, 'duplicate evidence identity')
        ids.add(entry['evidence_id'])
    for entry in evidence:
        provenance = entry['provenance']
        if provenance.get('kind') in ('direct_observed', 'derived'):
            _require(any(ref['observation_id'] == provenance.get('observation_id') and ref['event_cursor'] == provenance.get('event_cursor') for ref in history), path, 'evidence observation reference mismatch')
        if provenance.get('kind') == 'direct_observed':
            index = provenance.get('event_index')
            _require(_safe_integer(index) and _safe_integer(provenance['event_cursor']) and 0 <= index < provenance['event_cursor'], path, 'evidence event index mismatch')
            record = belief['source_protocol_prefix'][int(index)]
            _require(record == provenance.get('record') and not record.startswith('|request|'), path, 'evidence record mismatch')
            _require(hashlib.sha256(record.encode('utf-16-le', 'surrogatepass').decode('utf-16-le', 'replace').encode('utf8')).hexdigest() == provenance.get('record_hash'), path, 'nested record identity mismatch')
        if provenance.get('kind') == 'derived':
            _require(provenance['input_evidence_ids'] == sorted(set(provenance['input_evidence_ids'])), path, 'derived inputs are not canonical')
            _require(all(i in ids for i in provenance['input_evidence_ids']), path, 'derived evidence references missing identity')
    for candidate in belief.get('candidates', []):
        _require(all(_normalized(candidate.get(k)) for k in ('subject_key', 'value')), path, 'candidate strings are not normalized')
        _require(candidate.get('candidate_id') == 'hyp-' + digest([candidate[k] for k in ('category', 'subject_key', 'value')]), path, 'nested candidate identity mismatch')
        matching = [entry for entry in evidence if all(entry[k] == candidate[k] for k in ('category', 'subject_key', 'value'))]
        _require(candidate['evidence_ids'] == sorted(entry['evidence_id'] for entry in matching), path, 'candidate evidence references mismatch')
        signs = {entry['assertion'] for entry in matching}
        disposition = 'contradictory' if len(signs) == 2 else 'supported' if 'supports' in signs else 'ruled_out' if 'refutes' in signs else 'possible'
        _require(candidate['disposition'] == disposition, path, 'candidate disposition mismatch')


def verify_bundle_identities(bundle):
    for which in ('input', 'successor'):
        obs, belief = bundle[which + '_observation'], bundle[which + '_belief']
        verify_observation(obs, which + '_observation')
        verify_belief(belief, obs, which + '_belief')
    before, after = bundle['input_belief'], bundle['successor_belief']
    _require(after.get('parent_belief_id') == before['belief_id'], 'successor_belief', 'parent identity mismatch')
    old, new = before.get('observation_history'), after.get('observation_history')
    if old is not None:
        _require(isinstance(new, list) and new[:len(old)] == old, 'successor_belief', 'historical references changed')
    known = {bundle[k]['observation_id']: bundle[k] for k in ('input_observation', 'successor_observation')}
    for belief in (before, after):
        for ref in belief.get('observation_history', []):
            if ref['observation_id'] in known:
                _require(all(ref[k] == known[ref['observation_id']][k] for k in ref), 'belief history', 'reference disagrees with verified observation')
