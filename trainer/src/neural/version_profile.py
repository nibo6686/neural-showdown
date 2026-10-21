"""Fixed decoder selection only; never engine/source authority."""
from collections.abc import Mapping
from typing import NamedTuple

HISTORICAL10_REVISION = "sim-core@0.1.0+pokemon-showdown@0.11.10"
# native11 now names pinned commit b8f23c99.
NATIVE11_REVISION = "sim-core@0.1.0+pokemon-showdown@0.11.11+b8f23c99"
class ReaderProfile(NamedTuple):
    id: str
    revision: str
    adopted: bool
HISTORICAL10 = ReaderProfile("historical10", HISTORICAL10_REVISION, True)
NATIVE11 = ReaderProfile("native11", NATIVE11_REVISION, False)
class ReaderProfileError(ValueError):
    pass
def _fail(reason):
    raise ReaderProfileError("reader-profile/v1/" + reason)

def recognized_reader_revisions(value):
    revisions, active = [], set()
    def revision(v):
        if isinstance(v, Mapping) and "simulator_revision" in v:
            revisions.append(v["simulator_revision"])
    def evidence(v):
        if isinstance(v, Mapping) and isinstance(v.get("provenance"), Mapping) and v["provenance"].get("kind") == "simulator_only_truth":
            revision(v["provenance"])
    def belief(v):
        if isinstance(v, Mapping):
            revision(v.get("transition_lineage"))
            if isinstance(v.get("transition_history"), list):
                for t in v["transition_history"]: revision(t)
            if isinstance(v.get("evidence"), list):
                for e in v["evidence"]: evidence(e)
    def actor(v):
        if isinstance(v, Mapping):
            revision(v.get("transition")); belief(v.get("input_belief")); belief(v.get("successor_belief"))
    def actors(v):
        if isinstance(v, Mapping):
            for owner in ("p1", "p2"):
                if isinstance(v.get(owner), list):
                    for a in v[owner]: actor(a)
    def visit(v, depth=0):
        if not isinstance(v, Mapping): return
        if depth > 64 or id(v) in active: _fail("invalid-predecessor-chain")
        active.add(id(v)); schema = v.get("schema_version")
        if schema in ("pipeline-linked-record/v1", "pipeline-forced-switch-record/v1", "pipeline-revival-record/v1"):
            actor(v)
        elif schema in ("pipeline-episode-evidence/v1", "pipeline-episode-evidence/v2"):
            if isinstance(v.get("commits"), list):
                for c in v["commits"]:
                    if isinstance(c, Mapping): revision(c.get("transition"))
            if schema == "pipeline-episode-evidence/v2" and isinstance(v.get("closure"), Mapping):
                visit(v["closure"].get("predecessor"), depth + 1)
        elif schema == "pipeline-episode/v1":
            actors(v.get("records")); visit(v.get("evidence_envelope"), depth)
        elif schema == "pipeline-episode-publication-sweep/v1":
            actors(v.get("records")); visit(v.get("evidence_envelope"), depth)
            if isinstance(v.get("beliefs"), list):
                for b in v["beliefs"]:
                    if isinstance(b, Mapping):
                        belief(b.get("fields"))
                        arrays = b.get("arrays")
                        if isinstance(arrays, Mapping):
                            for key, consumer in (("transition_history", revision), ("evidence", evidence)):
                                encoded = arrays.get(key)
                                if isinstance(encoded, Mapping) and isinstance(encoded.get("items"), list):
                                    for item in encoded["items"]: consumer(item)
        active.remove(id(v))
    visit(value)
    return tuple(revisions)

def select_reader_profile(value, selection="auto"):
    if selection not in ("historical10", "native11", "auto"): _fail("unknown-profile")
    revisions = recognized_reader_revisions(value)
    if any(not isinstance(r, str) for r in revisions): _fail("unknown-revision")
    distinct = set(revisions)
    if len(distinct) > 1: _fail("conflicting-revisions")
    if not distinct and selection == "auto": _fail("ambiguous-revision")
    target = selection == "native11" or selection == "auto" and NATIVE11_REVISION in distinct
    if distinct and (NATIVE11_REVISION if target else HISTORICAL10_REVISION) not in distinct: _fail("unknown-revision")
    if target: reader_context(NATIVE11_CONTEXT)
    return NATIVE11 if target else HISTORICAL10

def assert_historical_reader_input(value):
    select_reader_profile(value, "historical10")


import json
from pathlib import Path
from types import MappingProxyType

def _freeze(value):
    if isinstance(value, dict): return MappingProxyType({k: _freeze(v) for k, v in value.items()})
    if isinstance(value, list): return tuple(_freeze(v) for v in value)
    return value

class ReaderContext(NamedTuple):
    profile: ReaderProfile
    protocol: Mapping
    inventory: Mapping
    effects: Mapping
    lifecycle: Mapping

_root = Path(__file__).resolve().parents[3]
_protocol = json.loads((_root / 'trainer/src/neural/protocol_contract.json').read_text(encoding='utf-8'))
_inventory = json.loads((_root / 'sim-core/simulator_coverage/pokemon-showdown-0.11.10-gen9randombattle.json').read_text(encoding='utf-8'))
if (_protocol['simulator']['version'] != '0.11.10' or _inventory['simulator']['version'] != '0.11.10'
        or _inventory['public_typed_state_lifecycle']['schema_version'] != 'public-typed-state-lifecycle/v1'):
    _fail('historical-asset-mismatch')
_effects = {}
for _entry in (*_inventory['condition_inventory'], *_inventory['effect_discovery']['additional_entries']):
    if _entry['id'] in _effects: _fail('duplicate-effect')
    _effects[_entry['id']] = _entry
HISTORICAL10_CONTEXT = ReaderContext(HISTORICAL10, _freeze(_protocol), _freeze(_inventory), _freeze(_effects),
    _freeze({(e['family'], e['id']): e for e in _inventory['public_typed_state_lifecycle']['entries']}))

def reader_context(context=HISTORICAL10_CONTEXT):
    if context is NATIVE11_CONTEXT:
        _ensure_owned_prepared_asset_validated('native11', NATIVE11_GRAMMAR_CONTEXT)
        return context
    if context is not HISTORICAL10_CONTEXT:
        _fail('native11-unadopted' if getattr(getattr(context, 'profile', None), 'id', None) == 'native11' else 'unsupported-context')
    return context

def assert_reader_input(value, context=HISTORICAL10_CONTEXT):
    assert_publication_reader_context(context)
    select_reader_profile(value, "native11" if context is NATIVE11_CONTEXT else "historical10")


def positive_fidelity_scope(profile, ruleset):
    if profile == 'historical10': return ruleset == 'gen9randombattle'
    if profile == 'native11': return False
    _fail('unknown-fidelity-profile')

def assert_positive_fidelity_claim(profile, ruleset, claimed):
    if claimed and not positive_fidelity_scope(profile, ruleset):
        raise ReaderProfileError('fidelity-policy/v1/positive-unaccepted')

def historical_knowledge_source_scope(package_version):
    if package_version == '0.11.10': return True
    if package_version == '0.11.11': return False
    _fail('unknown-source-runtime')

NATIVE_ENGINE_COMMIT = 'b8f23c99629132611ba59e99480cb148ea8c5d3d'
NATIVE_ENGINE_INTEGRITY = 'sha512-ihktUZgY1oy6U7TyCDmHg4lUlPeMb2jcedhqOnc/R0GIAeMgMFTlIDzmVsZ1xjBJ4ddaa/OM8dpfNsqo1dNe3Q=='
_NATIVE_ENGINE_MANIFEST_SHA256 = '806f1bf4edc35c7901902bfbc864ab1bebe6d1254b761808833a7a32b1e37ec6'
_NATIVE_ENGINE_DEPENDENCY = 'file:../vendor/pokemon-showdown-b8f23c99.tgz'


def installed_native_profile():
    """Verify local package bytes; this grants no producer authority."""
    import base64
    core = _root / 'sim-core'
    package = core / 'node_modules/pokemon-showdown'
    pkg = json.loads((package / 'package.json').read_text(encoding='utf-8'))
    declaration = json.loads((core / 'package.json').read_text(encoding='utf-8'))
    lock = json.loads((core / 'package-lock.json').read_text(encoding='utf-8'))
    installed = json.loads((core / 'node_modules/.package-lock.json').read_text(encoding='utf-8'))
    a, b = lock['packages'].get('node_modules/pokemon-showdown', {}), installed['packages'].get('node_modules/pokemon-showdown', {})
    if (pkg.get('version') != '0.11.11' or pkg.get('engine_commit') != NATIVE_ENGINE_COMMIT
            or declaration['dependencies'].get('pokemon-showdown') != _NATIVE_ENGINE_DEPENDENCY
            or lock['packages']['']['dependencies'].get('pokemon-showdown') != _NATIVE_ENGINE_DEPENDENCY
            or any(row.get('version') != '0.11.11' or row.get('integrity') != NATIVE_ENGINE_INTEGRITY
                   or row.get('resolved') != _NATIVE_ENGINE_DEPENDENCY for row in (a,b))):
        _fail('installed-runtime-mismatch')
    manifest = _pinned_asset(package / 'engine-files.json', _NATIVE_ENGINE_MANIFEST_SHA256)
    if manifest['engine_commit'] != NATIVE_ENGINE_COMMIT: _fail('installed-runtime-mismatch')
    entries = list(package.rglob('*'))
    if any(file.is_symlink() for file in entries): _fail('installed-runtime-content')
    actual = {file.relative_to(package).as_posix() for file in entries if file.is_file()}
    if actual != set(manifest['files']) | {'engine-files.json'}: _fail('installed-runtime-content')
    for name, expected in manifest['files'].items():
        if hashlib.sha256((package / name).read_bytes()).hexdigest() != expected: _fail('installed-runtime-content')
    tarball = (_root / 'vendor/pokemon-showdown-b8f23c99.tgz').read_bytes()
    if 'sha512-' + base64.b64encode(hashlib.sha512(tarball).digest()).decode('ascii') != NATIVE_ENGINE_INTEGRITY:
        _fail('installed-runtime-integrity')
    return _freeze({'package_version': '0.11.11', 'engine_commit': NATIVE_ENGINE_COMMIT, 'integrity': NATIVE_ENGINE_INTEGRITY})


def guard_historical_knowledge_source():
    """Fail-only quarantine, never a native authority descriptor/bridge."""
    installed_native_profile()
    raise ReaderProfileError('k-source-policy/v1/historical-origin-quarantined')


import hashlib
_HISTORICAL_LOOKUP_SHA256 = '21250d247e77879d0f7135a12baeee0ffadc7e00c5456a71dd07c066cd06b921'
_INACTIVE_TARGET_INVENTORY_SHA256 = '3d5760e2cc189617499cb9ab7e505ecebfeb6a3a6175f7e854c13fc7ba32dab2'
_historical_lookup = None

def _pinned_asset(path, expected):
    try: data = Path(path).read_bytes()
    except OSError: _fail('missing-version-asset')
    if hashlib.sha256(data).hexdigest() != expected: _fail('version-asset-integrity')
    return _freeze(json.loads(data))

def historical_lookup_data():
    global _historical_lookup
    if _historical_lookup is None:
        _historical_lookup = _pinned_asset(_root / 'sim-core/simulator_coverage/lookups/pokemon-showdown-0.11.10.json', _HISTORICAL_LOOKUP_SHA256)['data']
    return _historical_lookup

def load_inactive_target_inventory(path=None):
    """Read-only inspection, never target reader/native/source adoption."""
    if path is None: path = _root / 'sim-core/simulator_coverage/pokemon-showdown-0.11.11-gen9randombattle.json'
    candidate = _pinned_asset(path, _INACTIVE_TARGET_INVENTORY_SHA256)
    if (candidate['manifest_schema'] != 'simulator-coverage-candidate/v1' or candidate['adopted'] is not False
            or candidate['review_status'] != 'candidate-inactive' or candidate['simulator']['version'] != '0.11.11'
            or candidate['runtime_evidence'] != 'UNEXECUTED'
            or candidate['public_ability_effectiveness']['schema_version'] != 'public-ability-effectiveness/v1'
            or candidate['public_ability_effectiveness']['adopted'] is not False
            or candidate['effect_discovery']['package_wide_dynamic_callback_closure'] is not False
            or candidate['public_typed_state_lifecycle']['prior_projection_only'] is not True):
        _fail('invalid-inactive-inventory')
    return candidate

# Fixed candidate grammar contexts; no target reader/runtime adoption.
class ProtocolRulesContext(NamedTuple):
    protocol: Mapping

_TARGET_PROTOCOL_SHA256 = '6b822f2fed433e507543f30dc71c3b26762d9ae674c86d2237ce202d03c9c802'
_REPLAY_PROTOCOL_SHA256 = 'e8e8dcee5aa9952749047c3e87d70a16da8c04f6e4f480a81568e4bcd9fe02f4'
def load_prepared_protocol_asset(profile, path=None):
    if profile == 'native11': name, pin = 'protocol_contract_b8f23c99.json', _TARGET_PROTOCOL_SHA256
    elif profile == 'replay-compat-v1': name, pin = 'protocol_contract_replay_compat_v1.json', _REPLAY_PROTOCOL_SHA256
    else: _fail('unknown-grammar-profile')
    from .prepared_protocol_contract import validate_prepared_protocol_asset
    asset = _pinned_asset(Path(path) if path is not None else _root / 'trainer/src/neural' / name, pin)
    return _freeze(validate_prepared_protocol_asset(_thaw_prepared(asset), profile))

_target_protocol_asset = _pinned_asset(_root / 'trainer/src/neural/protocol_contract_b8f23c99.json', _TARGET_PROTOCOL_SHA256)
_replay_protocol_asset = _pinned_asset(_root / 'trainer/src/neural/protocol_contract_replay_compat_v1.json', _REPLAY_PROTOCOL_SHA256)
NATIVE11_GRAMMAR_CONTEXT = ProtocolRulesContext(_target_protocol_asset['protocol'])
REPLAY_COMPAT = ReaderProfile('replay-compat-v1', 'importer-replay-compatibility/v1', False)
REPLAY_COMPAT_CONTEXT = ReaderContext(REPLAY_COMPAT, _replay_protocol_asset['protocol'], HISTORICAL10_CONTEXT.inventory, HISTORICAL10_CONTEXT.effects, HISTORICAL10_CONTEXT.lifecycle)
import threading
_prepared_lock = threading.RLock()
_target_validation = {'phase': 'unvalidated'}
_replay_validation = {'phase': 'unvalidated'}
_checking_owned_context = None
_checking_thread = None

def _thaw_prepared(value):
    if isinstance(value, Mapping): return {k: _thaw_prepared(v) for k, v in value.items()}
    if isinstance(value, tuple): return [_thaw_prepared(v) for v in value]
    return value

def _ensure_owned_prepared_asset_validated(profile, context):
    global _checking_owned_context, _checking_thread
    owned = NATIVE11_GRAMMAR_CONTEXT if profile == 'native11' else REPLAY_COMPAT_CONTEXT
    state = _target_validation if profile == 'native11' else _replay_validation
    ident = threading.get_ident()
    with _prepared_lock:
        if context is not owned or (_checking_owned_context is not None and (context is not _checking_owned_context or ident != _checking_thread)):
            _fail('prepared-validation-context')
        if state['phase'] == 'failed': raise state['error']
        if state['phase'] in ('validated', 'checking'): return
        from .prepared_protocol_contract import validate_prepared_protocol_structure, check_prepared_protocol_records
        asset = _target_protocol_asset if profile == 'native11' else _replay_protocol_asset
        try:
            validate_prepared_protocol_structure(_thaw_prepared(asset), profile)
        except Exception as error:
            state.update(phase='failed', error=error)
            raise
        state['phase'] = 'checking'
        _checking_owned_context, _checking_thread = context, ident
    try:
        check_prepared_protocol_records(asset, profile)
        with _prepared_lock: state['phase'] = 'validated'
    except Exception as error:
        with _prepared_lock: state.update(phase='failed', error=error)
        raise
    finally:
        with _prepared_lock: _checking_owned_context, _checking_thread = None, None

def assert_prepared_inspection_available():
    with _prepared_lock:
        if _checking_owned_context is not None: _fail('prepared-validation-context')

def assert_prepared_record_check_input(value, profile):
    with _prepared_lock:
        if _checking_owned_context is None: return
        owned = NATIVE11_GRAMMAR_CONTEXT if profile == 'native11' else REPLAY_COMPAT_CONTEXT
        asset = _target_protocol_asset if profile == 'native11' else _replay_protocol_asset
        if owned is not _checking_owned_context or value is not asset or threading.get_ident() != _checking_thread:
            _fail('prepared-validation-context')

def protocol_context(context=HISTORICAL10_CONTEXT):
    if context is NATIVE11_GRAMMAR_CONTEXT:
        _ensure_owned_prepared_asset_validated('native11', context)
        return context
    if context is REPLAY_COMPAT_CONTEXT:
        _ensure_owned_prepared_asset_validated('replay-compat-v1', context)
        return context
    return reader_context(context)
def replay_reader_context(profile):
    if profile == 'historical10': return HISTORICAL10_CONTEXT
    if profile == 'replay-compat-v1': return protocol_context(REPLAY_COMPAT_CONTEXT)
    _fail('native11-unadopted' if profile == 'native11' else 'explicit-replay-profile-required')
def assert_publication_reader_context(context):
    if context is REPLAY_COMPAT_CONTEXT: _fail('replay-publication-unsupported')
    reader_context(context)

def assert_prepared_protocol_policy(record, context):
    protocol_context(context)
    if context is not NATIVE11_GRAMMAR_CONTEXT and context is not NATIVE11_CONTEXT and context is not REPLAY_COMPAT_CONTEXT: return
    p = record.split('|'); command = p[1] if len(p) > 1 else ''
    effect = p[3] if len(p) > 3 else ''
    stable_leftovers = command == '-heal' and len(p) == 5 and p[4] == '[from] item: Leftovers'
    revival = (context is NATIVE11_CONTEXT or context is NATIVE11_GRAMMAR_CONTEXT) and command == '-heal' and '[from] move: Revival Blessing' in p
    family = ('heal-failure' if context is REPLAY_COMPAT_CONTEXT and command in ('-heal', 'heal', 'cant') and not stable_leftovers and not revival else
              'court-change' if command in ('-swapsideconditions', 'swapsideconditions') or command == '-activate' and effect == 'move: Court Change' else
              'chilly-reception' if context is REPLAY_COMPAT_CONTEXT and command == '-prepare' and effect == 'Chilly Reception' else
              'partial-trap' if context is REPLAY_COMPAT_CONTEXT and command == '-damage' and '[partiallytrapped]' in p else
              'magician' if command in ('-item', 'item') and '[from] ability: Magician' in p else
              'ability-setter' if command == '-activate' and effect in ('ability: Mummy', 'ability: Lingering Aroma') or command == '-ability' and len(p) > 5 and '[from] ability: Trace' not in p else None)
    if family: _fail('prepared-family-unsupported/' + family)

# Candidate-only fixed runtime reader. No source authority or positive fidelity scope.
_target_inventory = _pinned_asset(_root / 'sim-core/simulator_coverage/pokemon-showdown-b8f23c99-gen9randombattle.json', 'fffced361d9b1a5be8c7cc0c073409b46a73ad852178ed62df89e29e9258e19b')
NATIVE11_CONTEXT = ReaderContext(NATIVE11, _target_protocol_asset['protocol'], _target_inventory,
    _freeze({e['id']: e for e in (*_target_inventory['condition_inventory'], *_target_inventory['effect_discovery']['additional_entries'])}),
    _freeze({(e['family'],e['id']): e for e in _target_inventory['public_typed_state_lifecycle']['entries']}))
