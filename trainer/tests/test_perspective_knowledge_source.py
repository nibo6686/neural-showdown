import copy
import hashlib
import json
import os
import pickle
import subprocess
import sys
import unittest
from pathlib import Path

from neural import perspective_knowledge_source as source_module
from neural.dataset_lineage import DATASET_RECORD_SCHEMA, expected_record_id, prefix_hash
from neural.perspective_knowledge import check_knowledge_structure, knowledge_identity
from neural.perspective_knowledge_source import (
    KnowledgeSourceError, LegacyContext, LegacyContextBuilder, LegacyEnvelopeAdapter, SourceRegistry,
    SourceRegistryBuilder, check_knowledge_source_binding,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / 'docs/contracts/fixtures/perspective-knowledge-v1'
WITNESS = ROOT / 'docs/planning/perspective-fidelity-prompt12-witness.cjs'
FORMS = ('ordinary', 'full', 'compact')
OWNERS = ('p1', 'p2')
_WITNESSES = None


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding='utf-8'))


def setUpModule():
    """Trusted local owner side: run the pinned witness harness (Node), then hold its data natively."""
    global _WITNESSES
    env = {k: v for k, v in os.environ.items() if k.upper() not in ('PYTHONUTF8', 'PYTHONIOENCODING')}
    env['PYTHON'] = sys.executable
    run = subprocess.run(['node', str(WITNESS)], cwd=str(ROOT), env=env, capture_output=True, timeout=300)
    if run.returncode != 0:
        raise RuntimeError('witness harness failed')
    _WITNESSES = json.loads(run.stdout.decode('utf-8'))


# ---- independent literal oracle ----
def literal_canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def literal_identity(row):
    payload = {k: v for k, v in row.items() if k != 'id'}
    return 'sha256:' + hashlib.sha256(('pk/v1/' + row['kind'] + '\n' + literal_canonical(payload)).encode('utf-8')).hexdigest()


def tables_of(audit):
    return {kind: sorted(rows.values() if isinstance(rows, dict) else rows, key=lambda r: r['id']) for kind, rows in audit['tables'].items()}


SINGLE = {
    'origin': [], 'source': ['origin'], 'prefix': ['origin'], 'evidence': ['origin', 'source', 'prefix'],
    'certificate': ['source'], 'fact': ['certificate'], 'starting': ['origin', 'source', 'parent'],
    'current': ['origin', 'prefix', 'parent'], 'request': ['origin', 'source', 'prefix'],
    'knowledge': ['origin', 'starting', 'current', 'request'], 'profile': [], 'verdict': ['knowledge', 'profile'],
    'boundary': ['origin', 'parent', 'restored_from'], 'binding': ['origin', 'input_knowledge', 'successor_knowledge'],
}
LISTS = {'certificate': ['witnesses'], 'fact': ['evidence'], 'starting': ['facts'], 'current': ['facts'], 'request': ['facts']}


def reseal(audit):
    expanded = tables_of(audit)
    by_old = {row['id']: row for rows in expanded.values() for row in rows}
    done = {}

    def replace(ident):
        if ident is None or ident not in by_old:
            return ident
        if ident in done:
            return done[ident]
        row = by_old[ident]
        for field in SINGLE[row['kind']]:
            row[field] = replace(row[field])
        for field in LISTS.get(row['kind'], []):
            row[field] = sorted(replace(i) for i in row[field])
        if row['kind'] == 'starting':
            for cross in row['crosswalk']:
                cross['certificate'] = replace(cross['certificate'])
        if row['kind'] == 'boundary':
            for binding in row['bindings']:
                binding['knowledge'] = replace(binding['knowledge']); binding['verdict'] = replace(binding['verdict'])
        row['id'] = literal_identity(row)
        done[ident] = row['id']
        return row['id']

    for ident in list(by_old):
        replace(ident)
    for field in ('origin', 'required_profile', 'target_boundary'):
        audit[field] = replace(audit[field])
    audit['tables'] = {kind: ({r['id']: r for r in sorted(rows, key=lambda r: r['id'])} if audit['form'] == 'compact'
                              else sorted(rows, key=lambda r: r['id'])) for kind, rows in expanded.items()}
    audit['id'] = literal_identity(audit)
    return audit


def mutated(audit, change):
    clone = copy.deepcopy(audit)
    change(tables_of(clone))
    return reseal(clone)


def source_row(rows, source_type, owner, seq=None):
    return next(s for s in rows['source'] if s['source_type'] == source_type and s['owner'] == owner
                and (seq is None or s['delivery_seq'] == seq))


def make_registry(w, omit_initialization=(), omit_requests=(), cursor_shift=None, ledger='full', origin='witness', replay=None):
    builder = SourceRegistryBuilder()
    if origin == 'witness':
        builder.set_origin(w['origin'])
    elif origin is not None:
        builder.set_origin(origin)
    records = w['ledger'] if ledger == 'full' else ledger
    for owner in OWNERS:
        if owner not in omit_initialization:
            builder.add_initialization_witness(owner, w['team_sets'][owner])
        for r in w['requests'][owner]:
            if f"{owner}:{r['sequence']}" in omit_requests or (records is not None and r['cursor'] > len(records)):
                continue
            builder.add_request_delivery(owner, r['sequence'], r['cursor'] + (cursor_shift or {}).get(f"{owner}:{r['sequence']}", 0), r['json'])
    if records is not None:
        builder.set_public_ledger(records)
    if replay is not None:
        builder.set_replay_source(replay)
    return builder.freeze()


def make_legacy(w, nonactor=(), extra=()):
    builder = LegacyContextBuilder(extra)
    for owner in OWNERS:
        if owner in nonactor:
            b = w['bundles'][owner]
            builder.add_nonactor_evidence(owner, (b['input_observation'], b['input_belief']), (b['successor_observation'], b['successor_belief']))
        else:
            builder.add_envelope(w['bundles'][owner])
    return builder.freeze()


class SourceTestBase(unittest.TestCase):
    def code(self, run):
        with self.assertRaises(KnowledgeSourceError) as caught:
            run()
        self.assertEqual(str(caught.exception), caught.exception.code)
        return caught.exception.code

    @property
    def versions(self):
        return list(_WITNESSES)


class SourceBindingTests(SourceTestBase):
    def test_witness_corroboration_and_cross_runtime_ids(self):
        for w in _WITNESSES.values():
            self.assertEqual(len(w['cursors']), 2)
            for owner in OWNERS:
                bundle = w['bundles'][owner]
                self.assertEqual(bundle['input_observation']['event_cursor'], w['requests'][owner][0]['cursor'])
                self.assertEqual(bundle['successor_observation']['protocol_prefix'], w['ledger'][:w['requests'][owner][1]['cursor']])
                self.assertEqual(json.loads(w['requests'][owner][1]['json'])['side']['id'], owner)
            # The TypeScript adapter and the native Python validator derive the same DATA IDs.
            self.assertEqual(w['ts_adapter_record_ids'], w['python_record_ids'])

    def test_actual_positives_all_versions_owners_and_forms(self):
        for w in _WITNESSES.values():
            registry, legacy = make_registry(w), make_legacy(w)
            self.assertEqual(registry.availability, {'origin': True, 'initialization_witness_owners': ['p1', 'p2'], 'original_provider': 'not_adopted',
                                                     'request_deliveries': 4, 'public_ledger': True, 'replay_source': False})
            self.assertEqual(legacy.availability, {'pairs': 2, 'nonactor_pairs': 0, 'envelope_kinds': ['pipeline-linked-record/v1']})
            for form in FORMS:
                audit = w['audits'][form]
                before = literal_canonical(audit)
                result = check_knowledge_source_binding(audit, registry, legacy, audit['required_profile'])
                self.assertEqual(literal_canonical(audit), before)
                self.assertEqual(result, {
                    'structure_valid': True,
                    'source_verification': {'scope': 'declared_source_rows_exact_match', 'verified': True, 'sources': 8, 'prefixes': 2,
                                            'request_deliveries': 4, 'original_delivery': 'test_only_unverified', 'replay_source': False},
                    'legacy_verification': {'scope': 'declared_external_positions', 'verified': True, 'boundaries': 2, 'bindings': 2,
                                            'envelope_kinds': ['pipeline-linked-record/v1']},
                    'fact_semantics': 'unverified', 'original_attribution': 'unverified',
                    'obligation_completeness': 'not_established', 'completeness': 'not_established',
                    'missing_capabilities': ['original_provider'],
                    'unsupported_capabilities': ['original_provider', 'fact_semantics', 'original_attribution', 'family_obligations'],
                    'published': False,
                })
                self.assertEqual(check_knowledge_structure(audit), {'structure_valid': True, 'source_semantics_verified': False,
                                                                    'completeness': 'not_established', 'legacy_envelope_verified': False})

    def test_nonactor_evidence_and_fabricated_data(self):
        for w in _WITNESSES.values():
            registry = make_registry(w); mixed = make_legacy(w, nonactor=('p2',))
            self.assertEqual(mixed.availability, {'pairs': 2, 'nonactor_pairs': 1, 'envelope_kinds': ['nonactor-observation-belief', 'pipeline-linked-record/v1']})
            ok = check_knowledge_source_binding(w['nonactor_audit'], registry, mixed, w['nonactor_audit']['required_profile'])
            self.assertTrue(ok['legacy_verification']['verified']); self.assertEqual(ok['completeness'], 'not_established')
            for form in FORMS:
                audit = w['audits'][form]
                self.assertEqual(self.code(lambda: check_knowledge_source_binding(audit, registry, mixed, audit['required_profile'])), 'legacy/transition')
            self.assertEqual(self.code(lambda: check_knowledge_source_binding(w['nonactor_audit'], registry, make_legacy(w), w['nonactor_audit']['required_profile'])),
                             'legacy/transition')

    def test_sourceless_canary_and_optional_legacy(self):
        for w in _WITNESSES.values():
            audit = w['sourceless_audit']
            for registry in (make_registry(w), make_registry(w, omit_initialization=OWNERS)):
                result = check_knowledge_source_binding(audit, registry, make_legacy(w), audit['required_profile'])
                self.assertEqual(result['source_verification']['original_delivery'], 'absent')
                self.assertEqual(result['missing_capabilities'], ['original_delivery_authority', 'original_provider'])
                self.assertEqual(result['completeness'], 'not_established')
            partial = check_knowledge_source_binding(w['audits']['full'], make_registry(w), None, w['audits']['full']['required_profile'])
            self.assertEqual(partial['legacy_verification'], {'scope': 'not_checked', 'verified': False, 'boundaries': 0, 'bindings': 0, 'envelope_kinds': []})
            self.assertEqual(partial['missing_capabilities'], ['legacy_context', 'original_provider'])

    def test_false_fact_values_stay_unverified(self):
        w = _WITNESSES[self.versions[0]]; registry, legacy = make_registry(w), make_legacy(w)
        for form in FORMS:
            def lie(rows):
                next(f for f in rows['fact'] if f['property'] == 'roster_species' and f['owner'] == 'p1')['value']['data'] = 'Missingno'
            audit = mutated(w['audits'][form], lie)
            result = check_knowledge_source_binding(audit, registry, legacy, audit['required_profile'])
            self.assertEqual(result['fact_semantics'], 'unverified'); self.assertEqual(result['completeness'], 'not_established')
            self.assertTrue(result['source_verification']['verified'])

    def test_resealed_source_negatives(self):
        def pretty(rows):
            s = source_row(rows, 'owner_request', 'p1', 1); s['raw_request']['json'] = json.dumps(json.loads(s['raw_request']['json']), indent=1)

        def reordered(rows):
            s = source_row(rows, 'owner_request', 'p2', 1); parsed = json.loads(s['raw_request']['json'])
            s['raw_request']['json'] = json.dumps(dict(reversed(list(parsed.items()))), separators=(',', ':'))

        def trailing(rows):
            source_row(rows, 'owner_request', 'p1', 0)['raw_request']['json'] += ' '

        def foreign_text(rows):
            a, b = source_row(rows, 'owner_request', 'p1', 0), source_row(rows, 'owner_request', 'p2', 0)
            a['raw_request']['json'], b['raw_request']['json'] = b['raw_request']['json'], a['raw_request']['json']

        def new_sequence(rows):
            s = source_row(rows, 'owner_request', 'p1', 1); s['delivery_seq'] = 7
            next(r for r in rows['request'] if r['source'] == s['id'])['sequence'] = 7

        def altered_team(rows):
            source_row(rows, 'owner_initialization', 'p1')['team'][0]['species'] = 'Forged'

        def foreign_team(rows):
            a, b = source_row(rows, 'owner_initialization', 'p1'), source_row(rows, 'owner_initialization', 'p2')
            a['team'], b['team'] = b['team'], a['team']

        def wrong_public(rows):
            longest = max(rows['prefix'], key=lambda p: len(p['records']))
            src = next(s for s in rows['source'] if s['source_type'] == 'public_prefix' and len(s['records']) == len(longest['records']))
            longest['records'][-1] = '|forged'; src['records'][-1] = '|forged'

        cases = [
            ('source/request-text', pretty), ('source/request-text', reordered), ('source/request-text', trailing),
            ('source/request-text', foreign_text), ('source/missing-request-delivery', new_sequence),
            ('source/original-team', altered_team), ('source/original-team', foreign_team), ('source/public-prefix', wrong_public),
        ]
        for w in _WITNESSES.values():
            registry, legacy = make_registry(w), make_legacy(w)
            for form in FORMS:
                for expected, change in cases:
                    audit = mutated(w['audits'][form], change)
                    self.assertEqual(self.code(lambda: check_knowledge_source_binding(audit, registry, legacy, audit['required_profile'])), expected, (form, change.__name__))

    def test_origin_authority_cursor_and_prefix_failures(self):
        for w in _WITNESSES.values():
            audit = w['audits']['ordinary']; legacy = make_legacy(w)
            foreign = mutated(audit, lambda rows: rows['origin'][0].__setitem__('battle_key', 'someone-else'))
            self.assertEqual(self.code(lambda: check_knowledge_source_binding(foreign, make_registry(w), legacy, foreign['required_profile'])), 'source/foreign-origin')
            expectations = [
                ('source/missing-origin', dict(origin=None)),
                ('source/missing-original-authority', dict(omit_initialization=('p2',))),
                ('source/missing-request-delivery', dict(omit_requests=('p1:1',))),
                ('source/missing-public-ledger', dict(ledger=None)),
                ('source/request-cursor', dict(cursor_shift={'p2:1': -1})),
                ('source/request-cursor', dict(cursor_shift={'p2:0': 1})),
                ('source/foreign-origin', dict(origin=dict(w['origin'], battle_key='someone-else'))),
            ]
            for expected, options in expectations:
                self.assertEqual(self.code(lambda: check_knowledge_source_binding(audit, make_registry(w, **options), legacy, audit['required_profile'])), expected, list(options))
            early = make_registry(w, ledger=w['ledger'][:w['cursors'][0]])
            self.assertEqual(self.code(lambda: check_knowledge_source_binding(audit, early, legacy, audit['required_profile'])), 'source/missing-request-delivery')
            wrong = list(w['ledger']); wrong[3] = '|forged'
            self.assertEqual(self.code(lambda: check_knowledge_source_binding(audit, make_registry(w, ledger=wrong), legacy, audit['required_profile'])), 'source/public-prefix')

    def test_resealed_wrong_legacy_joins(self):
        def fake(prefix, digit):
            return prefix + digit * 64

        for w in _WITNESSES.values():
            registry, legacy = make_registry(w), make_legacy(w)
            for owner in OWNERS:
                other = 'p2' if owner == 'p1' else 'p1'

                def replace_obs(rows, value):
                    binding = next(b for b in rows['binding'] if b['owner'] == owner); old = binding['input_observation']; binding['input_observation'] = value
                    for boundary in rows['boundary']:
                        for row in boundary['bindings']:
                            if row['observation_id'] == old:
                                row['observation_id'] = value

                def replace_belief(rows):
                    binding = next(b for b in rows['binding'] if b['owner'] == owner); old = binding['successor_belief']; binding['successor_belief'] = fake('belief-', 'c')
                    for boundary in rows['boundary']:
                        for row in boundary['bindings']:
                            if row['belief_id'] == old:
                                row['belief_id'] = binding['successor_belief']

                def wrong_actor(rows):
                    binding = next(b for b in rows['binding'] if b['owner'] == owner); binding['actor_record'] = w['python_record_ids'][other]
                    for boundary in rows['boundary']:
                        for row in boundary['bindings']:
                            if row['owner'] == owner and row['actor_record_id'] is not None:
                                row['actor_record_id'] = binding['actor_record']

                def initial_actor(rows):
                    first = next(b for b in rows['boundary'] if b['index'] == 0)
                    next(r for r in first['bindings'] if r['owner'] == owner)['actor_record_id'] = w['python_record_ids'][owner]

                cases = [
                    ('legacy/observation', lambda rows: replace_obs(rows, fake('obs-', 'b'))),
                    ('legacy/observation', lambda rows: replace_obs(rows, fake('sha256:', 'd'))),
                    ('legacy/belief', replace_belief),
                    ('legacy/transition', lambda rows: next(b for b in rows['binding'] if b['owner'] == owner).__setitem__('transition', fake('transition-', 'a'))),
                    ('legacy/actor-record', wrong_actor),
                    ('legacy/initial-actor', initial_actor),
                ]
                for form in FORMS:
                    for expected, change in cases:
                        audit = mutated(w['audits'][form], change)
                        self.assertEqual(self.code(lambda: check_knowledge_source_binding(audit, registry, legacy, audit['required_profile'])), expected, (owner, form, expected))
            names = self.versions
            foreign = _WITNESSES[names[1] if w is _WITNESSES[names[0]] else names[0]]
            audit = w['audits']['ordinary']
            self.assertEqual(self.code(lambda: check_knowledge_source_binding(audit, registry, make_legacy(foreign), audit['required_profile'])), 'legacy/observation')

    def test_adapter_seam_history_and_forged_evidence(self):
        w = _WITNESSES[self.versions[0]]; registry = make_registry(w); audit = w['audits']['ordinary']

        class Tampered(LegacyEnvelopeAdapter):
            schema_version = 'test-tampered-history/v1'

            def verify(self, envelope):
                b = envelope['bundle']; LegacyContextBuilder().add_envelope(b)  # actual validator first
                start = list(b['input_observation']['protocol_prefix'])
                return dict(owner=b['perspective'], battle_id=b['battle_id'], input_observation=b['input_observation']['observation_id'],
                            successor_observation=b['successor_observation']['observation_id'], input_belief=b['input_belief']['belief_id'],
                            successor_belief=b['successor_belief']['belief_id'], transition=b['transition']['transition_id'],
                            actor_record=w['python_record_ids'][b['perspective']], input_prefix=start[:-1] + ['|forged'],
                            successor_prefix=start[:-1] + ['|forged'] + list(b['successor_observation']['protocol_prefix'][len(start):]))

        class Wrapper(Tampered):
            schema_version = 'test-wrapper/v1'

            def verify(self, envelope):
                b = envelope['bundle']; result = super().verify(envelope)
                result['input_prefix'] = list(b['input_observation']['protocol_prefix']); result['successor_prefix'] = list(b['successor_observation']['protocol_prefix'])
                return result

        class Forged(LegacyEnvelopeAdapter):
            schema_version = 'test-forged/v1'

            def verify(self, envelope):
                return dict(owner='p1', battle_id=w['battle_id'], input_observation='sha256:' + '1' * 64, successor_observation='sha256:' + '2' * 64,
                            input_belief='sha256:' + '3' * 64, successor_belief='sha256:' + '4' * 64, transition=None, actor_record=None,
                            input_prefix=[], successor_prefix=[])

        builder = LegacyContextBuilder([Tampered()])
        for owner in OWNERS:
            builder.add_envelope({'schema_version': 'test-tampered-history/v1', 'bundle': w['bundles'][owner]})
        self.assertEqual(self.code(lambda: check_knowledge_source_binding(audit, registry, builder.freeze(), audit['required_profile'])), 'legacy/prefix')
        wrapped = LegacyContextBuilder([Wrapper()])
        for owner in OWNERS:
            wrapped.add_envelope({'schema_version': 'test-wrapper/v1', 'bundle': w['bundles'][owner]})
        self.assertTrue(check_knowledge_source_binding(audit, registry, wrapped.freeze(), audit['required_profile'])['legacy_verification']['verified'])
        self.assertEqual(self.code(lambda: LegacyContextBuilder([Forged()]).add_envelope({'schema_version': 'test-forged/v1'})), 'legacy/adapter-result')
        self.assertEqual(self.code(lambda: LegacyContextBuilder().add_envelope({'schema_version': 'pipeline-linked-record/v1', 'verified': True})), 'legacy/validator-rejected')
        self.assertEqual(self.code(lambda: LegacyContextBuilder().add_envelope(True)), 'legacy/unsupported-envelope-kind')

        class Duplicate(LegacyEnvelopeAdapter):
            schema_version = 'pipeline-linked-record/v1'
        self.assertEqual(self.code(lambda: LegacyContextBuilder([Duplicate()])), 'legacy/adapter')

    def test_unsupported_kinds_and_tampered_bundles(self):
        w = _WITNESSES[self.versions[1]]
        for kind in ('pipeline-forced-switch-record/v1', 'pipeline-revival-record/v1', 'pipeline-episode-evidence/v2', 'pipeline-episode-evidence/v1',
                     'pipeline-episode-publication-sweep/v1', 'unknown/v9'):
            envelope = dict(copy.deepcopy(w['bundles']['p1']), schema_version=kind)
            self.assertEqual(self.code(lambda: LegacyContextBuilder().add_envelope(envelope)), 'legacy/unsupported-envelope-kind', kind)

        def tamper(change):
            b = copy.deepcopy(w['bundles']['p1']); change(b); return b

        for bad in (
            tamper(lambda b: b.__setitem__('battle_id', 'other')),
            tamper(lambda b: b['transition'].__setitem__('transition_id', 'transition-' + 'e' * 64)),
            tamper(lambda b: b['successor_belief'].__setitem__('parent_belief_id', 'belief-' + 'f' * 64)),
            tamper(lambda b: b['input_observation']['protocol_prefix'].append('|forged')),
            tamper(lambda b: b['action'].__setitem__('action_id', 'act-' + '0' * 64)),
        ):
            self.assertEqual(self.code(lambda: LegacyContextBuilder().add_envelope(bad)), 'legacy/validator-rejected')
        b = w['bundles']['p2']
        pair = lambda side: (b[side + '_observation'], b[side + '_belief'])  # noqa: E731
        self.assertEqual(self.code(lambda: LegacyContextBuilder().add_nonactor_evidence('p1', pair('input'), pair('successor'))), 'legacy/validator-rejected')
        forged = copy.deepcopy(pair('successor')); forged[1]['belief_id'] = 'belief-' + '9' * 64
        self.assertEqual(self.code(lambda: LegacyContextBuilder().add_nonactor_evidence('p2', pair('input'), forged)), 'legacy/validator-rejected')
        self.assertEqual(self.code(lambda: LegacyContextBuilder().add_nonactor_evidence('p2', pair('successor'), pair('input'))), 'legacy/validator-rejected')


class CapabilityTests(SourceTestBase):
    def test_forged_copied_serialized_capabilities_rejected(self):
        w = _WITNESSES[self.versions[0]]; audit = w['audits']['full']; registry, legacy = make_registry(w), make_legacy(w)
        profile = audit['required_profile']

        class Subclass(SourceRegistry):
            pass

        for fake in ({}, dict(registry.availability), registry.availability, None, 'registry', SourceRegistryBuilder(),
                     {'origin': w['origin'], 'initialization': w['team_sets'], 'requests': w['requests'], 'ledger': w['ledger']}):
            self.assertEqual(self.code(lambda: check_knowledge_source_binding(audit, fake, legacy, profile)), 'capability/registry')
        for fake in ({}, legacy.availability, LegacyContextBuilder(), True, 0):
            self.assertEqual(self.code(lambda: check_knowledge_source_binding(audit, registry, fake, profile)), 'capability/legacy')
        for operation in (lambda: copy.copy(registry), lambda: copy.deepcopy(registry), lambda: pickle.dumps(registry),
                          lambda: copy.copy(legacy), lambda: pickle.dumps(legacy), lambda: setattr(registry, 'availability', {}),
                          lambda: setattr(registry, 'extra', 1)):
            with self.assertRaises((TypeError, AttributeError)):
                operation()
        self.assertEqual(self.code(lambda: SourceRegistry(object(), {})), 'capability/registry')
        self.assertEqual(self.code(lambda: LegacyContext(object(), {})), 'capability/legacy')
        self.assertEqual(self.code(lambda: Subclass(object(), {'origin': None, 'initialization': {}, 'requests': {}, 'ledger': None, 'replay': None})), 'capability/registry')
        # Audit-supplied registry/provider fields are closed-schema extra keys.
        for form in FORMS:
            extra = copy.deepcopy(w['audits'][form]); extra['registry'] = {'origin': w['origin']}; extra['id'] = knowledge_identity(extra)
            self.assertEqual(self.code(lambda: check_knowledge_source_binding(extra, registry, legacy, profile)), 'structure')
        self.assertEqual(self.code(lambda: check_knowledge_source_binding({'kind': 'audit'}, {}, {}, 'x')), 'structure')
        self.assertEqual(self.code(lambda: check_knowledge_source_binding(audit, registry, legacy, 'sha256:' + '0' * 64)), 'structure')
        self.assertEqual(self.code(lambda: check_knowledge_source_binding(audit, registry, legacy, 7)), 'profile')

    def test_builders_are_one_shot_and_inputs_are_copied(self):
        w = copy.deepcopy(_WITNESSES[self.versions[0]]); audit = json.loads(json.dumps(w['audits']['ordinary']))
        rb = SourceRegistryBuilder(); rb.set_origin(w['origin'])
        for owner in OWNERS:
            rb.add_initialization_witness(owner, w['team_sets'][owner])
            for r in w['requests'][owner]:
                rb.add_request_delivery(owner, r['sequence'], r['cursor'], r['json'])
        rb.set_public_ledger(w['ledger'])
        self.assertEqual(self.code(lambda: rb.set_public_ledger(w['ledger'])), 'registry/duplicate')
        self.assertEqual(self.code(lambda: rb.add_initialization_witness('p1', w['team_sets']['p1'])), 'registry/initialization')
        self.assertEqual(self.code(lambda: rb.add_request_delivery('p1', 0, 1, '{}')), 'registry/request')
        self.assertEqual(self.code(lambda: rb.add_request_delivery('p3', 9, 1, '{}')), 'registry/request')
        self.assertEqual(self.code(lambda: rb.add_request_delivery('p1', 9, 1, '{"a":1,"a":2}')), 'registry/request')
        registry = rb.freeze()
        self.assertEqual(self.code(lambda: rb.set_replay_source([])), 'registry/frozen')
        self.assertEqual(self.code(lambda: rb.freeze()), 'registry/frozen')
        lb = LegacyContextBuilder()
        for owner in OWNERS:
            lb.add_envelope(w['bundles'][owner])
        self.assertEqual(self.code(lambda: lb.add_envelope(w['bundles']['p1'])), 'legacy/duplicate')
        legacy = lb.freeze()
        self.assertEqual(self.code(lambda: lb.add_envelope(w['bundles']['p2'])), 'legacy/frozen')
        w['team_sets']['p1'][0]['species'] = 'Mutated'; w['ledger'][0] = '|mutated'; w['ledger'].append('|extra'); w['origin']['battle_key'] = 'mutated'
        w['bundles']['p1']['transition']['transition_id'] = 'transition-' + '0' * 64; w['bundles']['p2']['input_observation']['protocol_prefix'].append('|x')
        self.assertTrue(check_knowledge_source_binding(audit, registry, legacy, audit['required_profile'])['source_verification']['verified'])
        crafted = mutated(audit, lambda rows: source_row(rows, 'owner_initialization', 'p1')['team'][0].__setitem__('species', 'Mutated'))
        self.assertEqual(self.code(lambda: check_knowledge_source_binding(crafted, registry, legacy, crafted['required_profile'])), 'source/original-team')

    def test_no_privileged_exposure_or_publication_surface(self):
        w = _WITNESSES[self.versions[0]]; registry, legacy, audit = make_registry(w), make_legacy(w), w['audits']['ordinary']
        secrets = [w['team_sets']['p1'][0]['species'], w['requests']['p1'][1]['json'][:24], w['bundles']['p1']['input_observation']['observation_id'], w['battle_id'], w['ledger'][3]]
        for capability in (registry, legacy):
            self.assertEqual(sorted(a for a in dir(capability) if not a.startswith('_')), ['availability'])
            self.assertFalse(hasattr(capability, '__dict__'))
            text = json.dumps(capability.availability)
            for secret in secrets:
                self.assertNotIn(secret, text)
                self.assertNotIn(secret, repr(capability))
        bad = mutated(audit, lambda rows: source_row(rows, 'owner_request', 'p1', 1)['raw_request'].__setitem__('json', source_row(rows, 'owner_request', 'p1', 1)['raw_request']['json'] + ' '))
        runs = [lambda: check_knowledge_source_binding(bad, registry, legacy, bad['required_profile']),
                lambda: check_knowledge_source_binding(audit, {}, legacy, audit['required_profile']),
                lambda: LegacyContextBuilder().add_envelope({'schema_version': 'pipeline-linked-record/v1', 'battle_id': w['battle_id']})]
        for run in runs:
            with self.assertRaises(KnowledgeSourceError) as caught:
                run()
            error = caught.exception
            self.assertRegex(error.code, r'^[a-z-]+/[a-z-]+$|^structure$|^profile$')
            self.assertEqual(str(error), error.code); self.assertIsNone(error.__cause__); self.assertIsNone(error.__context__)
            for secret in secrets:
                self.assertNotIn(secret, repr(error))
        public = sorted(name for name in dir(source_module) if not name.startswith('_') and getattr(getattr(source_module, name), '__module__', None) == source_module.__name__)
        self.assertEqual(public, ['KnowledgeSourceError', 'LegacyContext', 'LegacyContextBuilder', 'LegacyEnvelopeAdapter', 'SourceRegistry', 'SourceRegistryBuilder',
                                  'check_knowledge_source_binding'])
        self.assertFalse(hasattr(source_module, 'main'))
        result = check_knowledge_source_binding(audit, registry, legacy, audit['required_profile'])
        self.assertIs(result['published'], False)
        for key in ('projection', 'registry', 'assurance'):
            self.assertNotIn(key, result)



class LabelAndCompletenessTests(SourceTestBase):
    def test_forged_labels_normalized_text_and_complete_claims(self):
        for w in _WITNESSES.values():
            registry, legacy, audit = make_registry(w), make_legacy(w), w['audits']['ordinary']
            delivered = w['requests']['p1'][0]['json']
            normalized = json.dumps(w['bundles']['p1']['input_observation']['request'], separators=(',', ':'))
            self.assertNotEqual(normalized, delivered)
            swapped = mutated(audit, lambda rows: source_row(rows, 'owner_request', 'p1', 0)['raw_request'].__setitem__('json', normalized))
            self.assertEqual(self.code(lambda: check_knowledge_source_binding(swapped, registry, legacy, swapped['required_profile'])), 'source/request-text')
            labels = [
                lambda rows: source_row(rows, 'owner_initialization', 'p1').__setitem__('phase', 'chronological'),
                lambda rows: source_row(rows, 'owner_initialization', 'p1').__setitem__('provider', 'addressed-request/v1'),
                lambda rows: source_row(rows, 'owner_request', 'p2', 1).__setitem__('owner', 'p1'),
                lambda rows: source_row(rows, 'owner_request', 'p1', 1).__setitem__('delivery_cursor', 3),
                lambda rows: source_row(rows, 'owner_initialization', 'p2')['team'][0].__setitem__('extra', 'x'),
            ]
            for change in labels:
                forged = mutated(audit, change)
                failure = self.code(lambda: check_knowledge_source_binding(forged, registry, legacy, forged['required_profile']))
                self.assertEqual(failure, 'structure')  # closed schema/addressing rules reject every forged label first

            def claim_all(rows):
                for verdict in rows['verdict']:
                    verdict['result'] = 'strong_complete'
            claim = mutated(audit, claim_all)
            self.assertEqual(check_knowledge_source_binding(claim, registry, legacy, claim['required_profile'])['completeness'], 'not_established')
            self.assertTrue(check_knowledge_source_binding(audit, registry, legacy, audit['required_profile'])['source_verification']['verified'])
            self.assertEqual(registry.availability['initialization_witness_owners'], ['p1', 'p2'])


class BoundaryRowTests(SourceTestBase):
    def test_boundary_row_only_mutations_rejected_by_structure(self):
        for w in _WITNESSES.values():
            registry, legacy = make_registry(w), make_legacy(w)

            def second(rows, owner):
                boundary = next(b for b in rows['boundary'] if b['index'] == 1)
                return next(r for r in boundary['bindings'] if r['owner'] == owner)

            def swap_owner(rows):
                b = next(x for x in rows['boundary'] if x['index'] == 1)
                b['bindings'][0]['owner'], b['bindings'][1]['owner'] = b['bindings'][1]['owner'], b['bindings'][0]['owner']

            changes = [lambda rows: second(rows, 'p1').__setitem__('actor_record_id', w['python_record_ids']['p2']),
                       lambda rows: second(rows, 'p1').__setitem__('observation_id', 'obs-' + 'b' * 64), swap_owner]
            for form in FORMS:
                for change in changes:
                    audit = mutated(w['audits'][form], change)
                    self.assertEqual(self.code(lambda: check_knowledge_source_binding(audit, registry, legacy, audit['required_profile'])), 'structure')


class ReplayAndIdentityTests(SourceTestBase):
    def test_replay_distinct_regime_with_hand_audited_oracle(self):
        # Hand-audited oracle metadata for the checked-in replay fixtures (literal U+00C9 and U+1F600).
        origin = {'battle_key': 'fixture-Éclair-\U0001F600', 'format': 'gen9randombattle', 'engine': 'pokemon-showdown@0.11.10', 'rule_version': 'pk-rules/v1'}
        replay = ['|start', '|switch|p1a: Éclair|Pikachu, L80|100/100', '|switch|p2a: Beta|Gengar, L80|100/100', '|-enditem|p1a: Éclair|Oran Berry|[eat]',
                  '|move|p2a: Beta|Tackle|p1a: Éclair', '|replace|p2a: Beta|Zoroark, L80|100/100', '|win|Éclair']
        suffix = replay[:6] + ['|win|Beta']

        def registry_for(records, held_origin=origin):
            builder = SourceRegistryBuilder()
            if held_origin:
                builder.set_origin(held_origin)
            if records is not None:
                builder.set_replay_source(records)
            return builder.freeze()

        for name, records in (('replay-full.json', replay), ('replay-ordinary.json', replay), ('replay-compact.json', replay),
                              ('replay-suffix-full.json', suffix), ('replay-suffix-compact.json', suffix)):
            audit = load(name); profile = audit['required_profile']
            other = suffix if records is replay else replay
            self.assertEqual(self.code(lambda: check_knowledge_source_binding(audit, registry_for(other), None, profile)), 'source/replay-source', name)
            result = check_knowledge_source_binding(audit, registry_for(records), None, profile)
            self.assertTrue(result['source_verification']['replay_source'], name)
            self.assertEqual(result['source_verification']['original_delivery'], 'absent')
            self.assertEqual(result['original_attribution'], 'unverified'); self.assertEqual(result['completeness'], 'not_established')
            self.assertEqual(result['missing_capabilities'], ['legacy_context', 'original_delivery_authority', 'original_provider'])
            self.assertEqual(self.code(lambda: check_knowledge_source_binding(audit, registry_for(None), None, profile)), 'source/missing-replay-source')
            self.assertEqual(self.code(lambda: check_knowledge_source_binding(audit, registry_for(records[:5]), None, profile)), 'source/replay-source')
            self.assertEqual(self.code(lambda: check_knowledge_source_binding(audit, registry_for(records, dict(origin, battle_key='foreign')), None, profile)), 'source/foreign-origin')
        audit = load('replay-full.json')
        self.assertEqual(self.code(lambda: check_knowledge_source_binding(audit, registry_for(replay), LegacyContextBuilder().freeze(), audit['required_profile'])), 'legacy/observation')

    def test_hand_authored_structure_canaries_are_not_source_positives(self):
        audit = load('sim-ordinary.json')
        self.assertTrue(check_knowledge_structure(audit)['structure_valid'])
        self.assertEqual(self.code(lambda: check_knowledge_source_binding(audit, SourceRegistryBuilder().freeze(), None, audit['required_profile'])), 'source/missing-origin')

    def test_data_identity_oracle_vectors(self):
        # Digests identical to the TypeScript adapter test; produced by dataset_lineage.expected_record_id.
        vectors = [
            ('ascii', ['|start', '|switch|p1a: Alpha|Pikachu, L80|100/100'], 'datarec-7e1d02d5c7e300eaa7bc8c50a729e8e068122603341ae9b523e9f94299e9da6b'),
            ('control', ['|ctl\x01\x1f|tab\t|nl\n|cr\r|del\x7f|bs\b|ff\f|q"|bs\\|sl/'], 'datarec-1e9742c83a45eb2a90f0ac44afa2eb837a93582a11b7d122765432a4614a1dc0'),
            ('bmp', ['|bmp Ééあ €|�￿'], 'datarec-9bca5bf6f8789057cae374f712b27047b14b9c397cf545b0eb174746a99a5420'),
            ('astral', ['|astral \U0001F600 \U0001D11E|end'], 'datarec-78d4b16002a4794496e5b4d65f2bf70dc41a6907cf54d763283db90faa2556e3'),
            ('empty', [], 'datarec-62c8c45e54ac375c8ebb40f844d478f47f81c4d4351baa0d43308d74b04ea083'),
        ]
        for name, prefix, expected in vectors:
            record = {'schema_version': DATASET_RECORD_SCHEMA, 'battle_id': 'vec-' + name, 'replay_id': 'sim:vec-' + name, 'source_kind': 'sim_core', 'perspective': 'p1',
                      'observation_cursor': len(prefix), 'observation_prefix_hash': prefix_hash(prefix), 'observation_id': 'obs-' + '1' * 64,
                      'action_id': 'act-' + '2' * 64, 'belief_id': 'belief-' + '3' * 64, 'transition_id': 'transition-' + '4' * 64}
            self.assertEqual(expected_record_id(record), expected, name)

    def test_old_identities_and_check_structure_cli_unchanged(self):
        for vector in load('identity-vectors.json'):
            self.assertEqual(knowledge_identity(vector['object']), vector['id'])
        w = _WITNESSES[self.versions[0]]
        env = {k: v for k, v in os.environ.items() if k.upper() not in ('PYTHONUTF8', 'PYTHONIOENCODING')}
        env['PYTHONPATH'] = str(ROOT / 'trainer/src')
        run = subprocess.run([sys.executable, '-m', 'neural.perspective_knowledge', '--check-structure'], cwd=str(ROOT), env=env,
                             input=json.dumps(w['audits']['ordinary']).encode('utf-8'), capture_output=True, timeout=120)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'{"structure_valid":true,"source_semantics_verified":false,"completeness":"not_established","legacy_envelope_verified":false}\n')
        probe = subprocess.run([sys.executable, '-m', 'neural.perspective_knowledge_source', '--check-structure'], cwd=str(ROOT), env=env,
                               capture_output=True, timeout=120)
        self.assertEqual(probe.stdout, b'', 'the source module has no CLI or output path')


if __name__ == '__main__':
    unittest.main()
