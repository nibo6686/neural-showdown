"""Prompt 14 / S01b: request-knowledge/v1 Python builder, independent validator and TS parity.

Expected values come from the exact addressed raw text (hand-written literals below, audited against the
witness raw texts) and from forged variants of them, never from the builder under test. Cases and
unchanged v1/v2 observations come from the test-owned witness (pinned BattleStream text + real legacy sessions).
"""
import copy
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from neural.perspective_knowledge_source import SourceRegistryBuilder
from neural.request_knowledge import (
    FRESH_DELIVERY, RequestKnowledgeError, build_request_knowledge, canonical_request_knowledge_json, request_knowledge_id,
    validate_request_knowledge,
)
from neural.ts_identity import observation_digest

ROOT = Path(__file__).resolve().parents[2]
WITNESS = ROOT / 'docs/planning/perspective-fidelity-prompt14-witness.cjs'
V1, V2 = 'observable-battle-state/v1', 'observable-battle-state/v2'
OWNERS = ('p1', 'p2')
_DATA = None


def _clean_env():
    return {k: v for k, v in os.environ.items() if k.upper() not in ('PYTHONUTF8', 'PYTHONIOENCODING')}


def setUpModule():
    raise unittest.SkipTest("Retired Prompt14 raw-restore sidecar witness; native replay-born K coverage replaces authority checks; moves/flags are W1.2/W1.3.")
    global _DATA
    env = _clean_env()
    env['PYTHON'] = sys.executable
    run = subprocess.run(['node', str(WITNESS)], cwd=str(ROOT), env=env, capture_output=True, timeout=600)
    if run.returncode != 0:
        raise RuntimeError('witness failed: ' + run.stderr.decode('utf-8', 'replace')[:500])
    _DATA = json.loads(run.stdout.decode('utf-8'))


def observation(case_id, owner, version=V2):
    return copy.deepcopy(_DATA['cases'][case_id]['versions'][version]['observations'][owner])


def raw_text(case_id, owner):
    return _DATA['cases'][case_id]['raw'][owner]['json']


def forge_record(record, mutate):
    forged = copy.deepcopy(record)
    mutate(forged)
    forged['id'] = request_knowledge_id(forged)
    return forged


def forge_observation(obs, mutate):
    forged = copy.deepcopy(obs)
    mutate(forged)
    forged['observation_id'] = observation_digest(forged)
    return forged


def fresh(case_id, owner, version=V2):
    obs = observation(case_id, owner, version)
    text = None if obs['view']['terminated'] or obs['request'] is None else raw_text(case_id, owner)
    return build_request_knowledge(owner, text, obs, FRESH_DELIVERY), obs


def bind(record, obs):
    """Re-point a record at a (forged, resealed) observation so only the semantic check can reject it."""
    return forge_record(record, lambda r: r.update(observation_id=obs['observation_id']))


class RequestKnowledgeBase(unittest.TestCase):
    def rejects(self, code, record, obs, **kwargs):
        with self.assertRaises(RequestKnowledgeError) as caught:
            validate_request_knowledge(record, obs, **kwargs)
        self.assertEqual(caught.exception.code, code)

    def refuses(self, code, *args):
        with self.assertRaises(RequestKnowledgeError) as caught:
            build_request_knowledge(*args)
        self.assertEqual(caught.exception.code, code)


# (lock, trapped, maybe_trapped, maybe_disabled, switch_in_available, moves as (id, pp, max_pp, target, disabled)); hand-audited vs raw text.
R = lambda *a: a
HAND = {
    ('ordinary_slots', 'p1'): ('no_hard_lock', False, False, False, True, [R('tackle', 56, 56, 'normal', False), R('rest', 8, 8, 'self', False), R('curse', 16, 16, 'self', False), R('bodyslam', 24, 24, 'normal', False)]),
    ('ordinary_slots', 'p2'): ('no_hard_lock', False, False, False, True, [R('splash', 64, 64, 'self', False), R('tackle', 56, 56, 'normal', False)]),
    ('two_turn_locked_move', 'p1'): ('locked_move', True, False, False, True, [R('solarbeam', None, None, None, None)]),
    ('recharge_mirror', 'p2'): ('recharge', True, False, False, True, [R('recharge', None, None, None, None)]),
    ('struggle_fallback', 'p1'): ('struggle', False, False, False, True, [R('struggle', None, None, 'randomNormal', False)]),
    ('struggle_maybe_disabled', 'p1'): ('struggle', False, False, True, True, [R('struggle', None, None, 'randomNormal', False)]),
    ('struggle_all_pp_zero', 'p1'): ('struggle', False, False, False, True, [R('struggle', None, None, 'randomNormal', False)]),
    ('real_pp_zero', 'p1'): ('no_hard_lock', False, False, False, True, [R('destinybond', 0, 8, 'self', True), R('splash', 64, 64, 'self', False)]),
    ('maybe_disabled_imprison', 'p1'): ('no_hard_lock', False, False, True, True, [R('tackle', 56, 56, 'normal', False), R('rest', 8, 8, 'self', False), R('curse', 16, 16, 'self', False), R('splash', 63, 64, 'self', False)]),
    ('maybe_trapped_shadow_tag_mirror', 'p2'): ('no_hard_lock', False, True, False, True, [R('tackle', 56, 56, 'normal', False), R('splash', 64, 64, 'self', False)]),
    ('known_trapped_mean_look', 'p1'): ('no_hard_lock', True, False, False, True, [R('tackle', 56, 56, 'normal', False), R('splash', 63, 64, 'self', False)]),
    ('maybe_trapped_empty_bench', 'p1'): ('no_hard_lock', None, None, False, False, [R('tackle', 56, 56, 'normal', False), R('splash', 64, 64, 'self', False)]),
    ('locked_empty_bench', 'p1'): ('locked_move', None, None, False, False, [R('solarbeam', None, None, None, None)]),
    ('outrage_lock', 'p1'): ('locked_move', True, False, False, True, [R('outrage', None, None, None, None)]),
    ('rollout_lock', 'p1'): ('locked_move', True, False, False, True, [R('rollout', None, None, None, None)]),
    ('uproar_lock', 'p1'): ('locked_move', True, False, False, True, [R('uproar', None, None, None, None)]),
    ('choice_lock_soft', 'p1'): ('no_hard_lock', False, False, False, True, [R('tackle', 55, 56, 'normal', False), R('rest', 8, 8, 'self', True), R('curse', 16, 16, 'self', True), R('bodyslam', 24, 24, 'normal', True)]),
    ('unicode_names', 'p1'): ('no_hard_lock', False, False, False, True, [R('tackle', 56, 56, 'normal', False), R('splash', 64, 64, 'self', False)]),
}
PRESENCE = {('waiting_and_forced_switch', 'p1'): 'waiting', ('waiting_and_forced_switch', 'p2'): 'forced_switch',
            ('revival_selection_and_waiting', 'p1'): 'revival_selection', ('revival_selection_and_waiting', 'p2'): 'waiting',
            ('terminal_requestless', 'p1'): 'terminal', ('terminal_requestless', 'p2'): 'terminal'}


class Parity(RequestKnowledgeBase):
    def test_python_builds_exactly_the_typescript_records_and_validates_them(self):
        count = 0
        for case_id, records in _DATA['records'].items():
            for key, ts_record in records.items():
                version, owner = 'observable-battle-state/' + key[:2], key[3:]
                record, obs = fresh(case_id, owner, version)
                self.assertEqual(record, ts_record, (case_id, key))
                self.assertEqual(canonical_request_knowledge_json(record), canonical_request_knowledge_json(ts_record))
                self.assertEqual(validate_request_knowledge(ts_record, obs), {'record_id': ts_record['id'], 'presence': ts_record['presence'], 'delivery_authority': 'structure_only'})
                count += 1
        self.assertEqual(count, 110)
        self.assertEqual(len(_DATA['cases']), 28)

    def test_hand_audited_literals(self):
        for (case_id, owner), expected in HAND.items():
            record, _ = fresh(case_id, owner)
            active = record['active']
            self.assertEqual((record['presence'], active['lock'], active['trapped'], active['maybe_trapped'], active['maybe_disabled'], active['switch_in_available']),
                             ('actionable',) + expected[:5], (case_id, owner))
            self.assertEqual([(m['id'], m['pp'], m['max_pp'], m['target'], m['disabled']) for m in active['moves']], expected[5], (case_id, owner))
        for (case_id, owner), presence in PRESENCE.items():
            record, _ = fresh(case_id, owner)
            self.assertEqual((record['presence'], record['active'], record['request_present'], record['raw_request'] is None), (presence, None, presence != 'terminal', presence == 'terminal'))

    def test_derivation_enums_name_the_rule(self):
        self.assertEqual(fresh('maybe_trapped_shadow_tag', 'p1')[0]['active']['derivation'],
                         {'lock': 'pp_bearing_rows', 'trapped': 'omitted_with_switch_in', 'maybe_trapped': 'raw_true', 'maybe_disabled': 'omitted_singles_rule'})
        self.assertEqual(fresh('known_trapped_mean_look', 'p1')[0]['active']['derivation'],
                         {'lock': 'pp_bearing_rows', 'trapped': 'raw_true', 'maybe_trapped': 'superseded_by_trapped', 'maybe_disabled': 'omitted_singles_rule'})
        self.assertEqual(fresh('locked_empty_bench', 'p1')[0]['active']['derivation'],
                         {'lock': 'bare_single_row', 'trapped': 'omitted_without_switch_in', 'maybe_trapped': 'omitted_without_switch_in', 'maybe_disabled': 'omitted_singles_rule'})


class FalseCertainty(RequestKnowledgeBase):
    def case(self, case_id, owner='p1'):
        return fresh(case_id, owner)

    def test_every_false_certainty_is_rejected_even_when_the_id_is_resealed(self):
        def moves(**changes):
            return lambda r: r['active']['moves'][0].update(changes)
        def flags(**changes):
            return lambda r: r['active'].update(changes)
        def derivation(**changes):
            return lambda r: r['active']['derivation'].update(changes)
        cases = [
            ('two_turn_locked_move', moves(pp=15, max_pp=16)), ('two_turn_locked_move', moves(disabled=False)), ('two_turn_locked_move', moves(target='normal')),
            ('two_turn_locked_move', flags(lock='no_hard_lock')), ('recharge', flags(lock='locked_move')), ('struggle_fallback', flags(lock='locked_move')),
            ('struggle_fallback', moves(pp=0)), ('known_trapped_mean_look', flags(trapped=False)),
            ('known_trapped_mean_look', lambda r: (r['active'].update(trapped=False), r['active']['derivation'].update(trapped='omitted_with_switch_in'))),
            ('maybe_trapped_shadow_tag', flags(maybe_trapped=False)), ('maybe_trapped_shadow_tag', flags(maybe_trapped=None)),
            ('maybe_disabled_imprison', flags(maybe_disabled=False)), ('maybe_trapped_empty_bench', flags(trapped=False)),
            ('maybe_trapped_empty_bench', flags(switch_in_available=True)), ('locked_empty_bench', flags(trapped=True)),
            ('ordinary_slots', moves(pp=None)), ('ordinary_slots', moves(pp=55)), ('ordinary_slots', moves(disabled=None)),
            ('real_pp_zero', moves(pp=None)), ('maybe_trapped_shadow_tag', derivation(maybe_trapped='omitted_with_switch_in')),
            ('maybe_disabled_imprison', derivation(maybe_disabled='omitted_singles_rule')),
            ('waiting_and_forced_switch', lambda r: r.update(active=copy.deepcopy(fresh('ordinary_slots', 'p1')[0]['active']))),
            ('ordinary_slots', lambda r: r.update(rqid=3)),
            ('two_turn_locked_move', derivation(lock='pp_bearing_rows')), ('ordinary_slots', derivation(lock='bare_single_row')),
        ]
        for case_id, mutate in cases:
            record, obs = self.case(case_id)
            self.rejects('false-certainty', forge_record(record, mutate), obs)
            self.assertEqual(validate_request_knowledge(record, obs)['record_id'], record['id'])

    def test_wire_negatives(self):
        record, obs = self.case('maybe_trapped_shadow_tag')
        cases = {
            'wire-keys': [lambda r: r.update(extra=1), lambda r: r.pop('rqid'), lambda r: r['active'].update(extra=1), lambda r: r['active'].pop('lock'),
                          lambda r: r['active']['derivation'].pop('trapped'), lambda r: r['active']['moves'][0].update(extra=1), lambda r: r['active']['moves'][0].pop('pp')],
            'wire-type': [lambda r: r.update(event_cursor=True), lambda r: r.update(rqid=True), lambda r: r['active']['moves'][0].update(slot=True),
                          lambda r: r['active']['moves'][0].update(pp=True), lambda r: r['active']['moves'][0].update(pp=56.0), lambda r: r['active']['moves'][0].update(disabled=0),
                          lambda r: r.update(request_present=1), lambda r: r.update(battle_id='x' * 257), lambda r: r['active'].update(trapped='false'),
                          lambda r: r['active'].update(maybe_disabled=None), lambda r: r.update(presence='no_legal_actions'), lambda r: r.update(presence='team_preview'),
                          lambda r: r.update(schema_version='request-knowledge/v2')],
            'wire-size': [lambda r: r.update(raw_request=r['raw_request'] + ' ' * 65537), lambda r: r['active'].update(moves=r['active']['moves'] * 3)],
        }
        for code, mutations in cases.items():
            for mutate in mutations:
                forged = copy.deepcopy(record); mutate(forged)
                self.rejects(code, forged, obs)
        with self.assertRaises(RequestKnowledgeError):
            canonical_request_knowledge_json({'a': 1.5})
        with self.assertRaises(RequestKnowledgeError):
            canonical_request_knowledge_json({'a': True and 2 ** 31})
        self.rejects('wire-keys', 'not a dict', obs)

    def test_duplicate_key_and_unknown_raw_keys(self):
        record, obs = self.case('maybe_trapped_shadow_tag')
        dup = record['raw_request'].replace('"maybeTrapped":true', '"maybeTrapped":true,"maybeTrapped":true')
        self.assertNotEqual(dup, record['raw_request'])
        self.rejects('raw-json', forge_record(record, lambda r: r.update(raw_request=dup)), obs)
        self.refuses('raw-json', 'p1', dup, obs, FRESH_DELIVERY)
        raw = json.loads(record['raw_request']); raw['active'][0]['canMegaEvo'] = True
        self.rejects('raw-grammar', forge_record(record, lambda r: r.update(raw_request=json.dumps(raw, separators=(',', ':')))), obs)
        raw = json.loads(record['raw_request']); raw['active'][0]['moves'][0]['pp'] = 1.5
        self.rejects('raw-json', forge_record(record, lambda r: r.update(raw_request=json.dumps(raw, separators=(',', ':')))), obs)

    def test_doubles_team_preview_and_no_legal_actions_are_rejected_not_mapped(self):
        record, obs = self.case('maybe_trapped_shadow_tag')
        raw = json.loads(record['raw_request']); raw['active'].append(copy.deepcopy(raw['active'][0]))
        text = json.dumps(raw, separators=(',', ':'))
        self.rejects('doubles', forge_record(record, lambda r: r.update(raw_request=text)), obs)
        self.refuses('doubles', 'p1', text, obs, FRESH_DELIVERY)
        raw = json.loads(record['raw_request']); raw['side']['pokemon'][1]['active'] = True
        self.refuses('doubles', 'p1', json.dumps(raw, separators=(',', ':')), obs, FRESH_DELIVERY)
        forced_record, forced_obs = self.case('waiting_and_forced_switch', 'p2')
        raw = json.loads(forced_record['raw_request']); raw['forceSwitch'] = [True, False]
        self.rejects('doubles', forge_record(forced_record, lambda r: r.update(raw_request=json.dumps(raw, separators=(',', ':')))), forced_obs)
        raw = json.loads(record['raw_request']); raw['teamPreview'] = True
        self.rejects('team-preview', forge_record(record, lambda r: r.update(raw_request=json.dumps(raw, separators=(',', ':')))), obs)
        preview = forge_observation(obs, lambda o: o['request'].update(team_preview=True))
        self.refuses('team-preview', 'p1', record['raw_request'], preview, FRESH_DELIVERY)
        none = forge_observation(obs, lambda o: o['request']['legal_actions'].update(available_indices=[]))
        self.refuses('no-legal-actions', 'p1', record['raw_request'], none, FRESH_DELIVERY)
        self.rejects('no-legal-actions', bind(record, none), none)
        unavailable = forge_observation(obs, lambda o: o['decision_availability'].update(available=False))
        self.refuses('no-legal-actions', 'p1', record['raw_request'], unavailable, FRESH_DELIVERY)

    def test_legality_invariant_is_recomputed_from_the_raw_request(self):
        record, obs = self.case('two_turn_locked_move')
        # A numbered move action for a null-PP locked row is a legality fabrication.
        fabricated = forge_observation(obs, lambda o: o['request']['legal_actions']['actions'].__setitem__(1, {'index': 1, 'kind': 'move', 'choice': 'move 1', 'label': 'move:Solar Beam', 'move': 'Solar Beam', 'slot': 1}))
        self.rejects('legality-mismatch', bind(record, fabricated), fabricated)
        disabled_record, disabled_obs = self.case('choice_lock_soft')
        enabled = forge_observation(disabled_obs, lambda o: o['request']['legal_actions']['actions'].__setitem__(1, {'index': 1, 'kind': 'move', 'choice': 'move 2', 'label': 'move:Rest', 'move': 'Rest', 'slot': 2}))
        self.rejects('legality-mismatch', bind(disabled_record, enabled), enabled)


class CorrectionRound(RequestKnowledgeBase):
    def test_forged_presence_and_forged_active_on_terminal(self):
        record, obs = fresh('ordinary_slots', 'p1')
        for presence in ('waiting', 'forced_switch', 'revival_selection', 'requestless', 'terminal'):
            self.rejects('presence-mismatch', forge_record(record, lambda r: r.update(presence=presence)), obs)
        terminal, terminal_obs = fresh('terminal_requestless', 'p1')
        self.rejects('presence-mismatch', forge_record(terminal, lambda r: r.update(active=copy.deepcopy(record['active']))), terminal_obs)
        self.rejects('presence-mismatch', forge_record(terminal, lambda r: r.update(presence='actionable')), terminal_obs)

    def test_terminated_observation_must_carry_no_request(self):
        terminal, terminal_obs = fresh('terminal_requestless', 'p1')
        live = observation('ordinary_slots', 'p1')
        weird = forge_observation(live, lambda o: o['view'].update(terminated=True))
        self.rejects('presence-mismatch', forge_record(terminal, lambda r: r.update(observation_id=weird['observation_id'], battle_id=weird['battle_id'], event_cursor=weird['event_cursor'])), weird)
        self.refuses('presence-mismatch', 'p1', raw_text('ordinary_slots', 'p1'), weird, FRESH_DELIVERY)

    def test_caps_and_wait_no_cancel_in_builder(self):
        live = observation('ordinary_slots', 'p1')
        long_id = forge_observation(live, lambda o: o.update(battle_id='b' * 257))
        self.refuses('observation-mismatch', 'p1', raw_text('ordinary_slots', 'p1'), long_id, FRESH_DELIVERY)
        self.assertEqual(len(build_request_knowledge('p1', raw_text('ordinary_slots', 'p1'), forge_observation(live, lambda o: o.update(battle_id='b' * 256)), FRESH_DELIVERY)['battle_id']), 256)
        for value in ({'battle_id': 'x' * 257}, {'id': 'x' * 257}):
            with self.assertRaises(RequestKnowledgeError):
                canonical_request_knowledge_json(value)
        self.assertGreater(len(canonical_request_knowledge_json({'raw_request': 'x' * 300})), 300)
        for key in ('move', 'id', 'target'):
            raw = json.loads(raw_text('ordinary_slots', 'p1')); raw['active'][0]['moves'][0][key] = 'm' * 257
            with self.assertRaises(RequestKnowledgeError) as caught:
                build_request_knowledge('p1', json.dumps(raw, separators=(',', ':')), live, FRESH_DELIVERY)
            self.assertIn(caught.exception.code, ('raw-json', 'raw-grammar'))
        waiting = observation('waiting_and_forced_switch', 'p1')
        raw = json.loads(raw_text('waiting_and_forced_switch', 'p1')); raw['noCancel'] = True
        self.refuses('raw-grammar', 'p1', json.dumps(raw, separators=(',', ':')), waiting, FRESH_DELIVERY)
        record, _ = fresh('waiting_and_forced_switch', 'p1')
        self.rejects('raw-grammar', forge_record(record, lambda r: r.update(raw_request=json.dumps(raw, separators=(',', ':')))), waiting)
        raw = json.loads(raw_text('ordinary_slots', 'p1')); raw['noCancel'] = True
        self.refuses('raw-grammar', 'p1', json.dumps(raw, separators=(',', ':')), live, FRESH_DELIVERY)

    def test_non_null_rqid_positive_path(self):
        # The pinned stream emits no rqid: hand-audited literal (rqid 7 in the text, request.rqid 7 in the observation).
        base = observation('ordinary_slots', 'p1')
        raw = json.loads(raw_text('ordinary_slots', 'p1')); raw['rqid'] = 7
        text = json.dumps(raw, separators=(',', ':'))
        obs = forge_observation(base, lambda o: o['request'].update(rqid=7))
        record = build_request_knowledge('p1', text, obs, FRESH_DELIVERY)
        self.assertEqual(record['rqid'], 7)
        self.assertEqual(validate_request_knowledge(record, obs)['record_id'], record['id'])
        self.rejects('false-certainty', forge_record(record, lambda r: r.update(rqid=None)), obs)
        self.rejects('false-certainty', forge_record(record, lambda r: r.update(rqid=8)), obs)
        self.refuses('observation-mismatch', 'p1', text, base, FRESH_DELIVERY)
        self.rejects('observation-mismatch', bind(record, base), base)
        raw['rqid'] = '7'
        self.refuses('raw-grammar', 'p1', json.dumps(raw, separators=(',', ':')), obs, FRESH_DELIVERY)


class OwnerAndFreshness(RequestKnowledgeBase):
    def test_wrong_owner_in_every_position(self):
        record, obs = fresh('two_turn_locked_move', 'p1')
        self.rejects('wrong-owner', forge_record(record, lambda r: r.update(perspective='p2')), obs)
        other_record, other_obs = fresh('two_turn_locked_move', 'p2')
        # Other owner's raw under p1's identity, record and observation jointly resealed as p1.
        self.rejects('wrong-owner', forge_record(record, lambda r: r.update(raw_request=other_record['raw_request'])), obs)
        wrong_player = forge_observation(obs, lambda o: o['request'].update(player='p2'))
        self.rejects('wrong-owner', bind(record, wrong_player), wrong_player)
        # p1's raw presented as p2 everywhere except the raw itself.
        flipped_obs = forge_observation(obs, lambda o: (o.update(perspective='p2'), o['request'].update(player='p2')))
        self.rejects('wrong-owner', forge_record(record, lambda r: r.update(perspective='p2', observation_id=flipped_obs['observation_id'])), flipped_obs)
        self.refuses('wrong-owner', 'p2', record['raw_request'], flipped_obs, FRESH_DELIVERY)
        self.refuses('wrong-owner', 'p2', record['raw_request'], obs, FRESH_DELIVERY)
        self.refuses('wrong-owner', 'p1', other_record['raw_request'], obs, FRESH_DELIVERY)
        self.refuses('wrong-owner', 'p3', record['raw_request'], obs, FRESH_DELIVERY)
        # A raw whose roster idents name the other owner is rejected even if side.id was rewritten.
        raw = json.loads(other_record['raw_request']); raw['side']['id'] = 'p1'
        self.rejects('wrong-owner', forge_record(record, lambda r: r.update(raw_request=json.dumps(raw, separators=(',', ':')))), obs)

    def test_validator_raw_grammar_is_as_strict_as_the_builder(self):
        record, obs = fresh('maybe_trapped_shadow_tag', 'p1')
        for mutate in (lambda r: r.update(rqid=None), lambda r: r.update(noCancel=True), lambda r: r['active'][0].update(canTerastallize=5)):
            raw = json.loads(record['raw_request']); mutate(raw)
            self.rejects('raw-grammar', forge_record(record, lambda r: r.update(raw_request=json.dumps(raw, separators=(',', ':')))), obs)

    def test_stale_cursor_and_stale_observation(self):
        record, obs = fresh('maybe_trapped_shadow_tag', 'p1')
        self.rejects('stale', forge_record(record, lambda r: r.update(event_cursor=record['event_cursor'] + 1)), obs)
        self.rejects('stale', forge_record(record, lambda r: r.update(event_cursor=record['event_cursor'] - 1)), obs)
        self.rejects('stale', record, observation('ordinary_slots', 'p1'))
        self.rejects('stale', forge_record(record, lambda r: r.update(observation_id='obs-' + '0' * 64)), obs)
        self.rejects('observation-identity', record, {**obs, 'battle_id': 'tampered'})  # not resealed: legacy identity check catches it

    def test_resealed_record_and_observation_cannot_fabricate_what_the_raw_omits(self):
        record, obs = fresh('two_turn_locked_move', 'p1')
        def fabricate_obs(o):
            o['request']['active']['moves'][0].update(pp=15, maxpp=16)
        forged_obs = forge_observation(obs, fabricate_obs)
        self.rejects('observation-mismatch', bind(record, forged_obs), forged_obs)
        forged_record = forge_record(record, lambda r: r['active']['moves'][0].update(pp=15, max_pp=16))
        forged_record['observation_id'] = forged_obs['observation_id']
        forged_record['id'] = request_knowledge_id(forged_record)
        self.rejects('false-certainty', forged_record, forged_obs)

    def test_jointly_resealed_record_raw_and_observation_is_structure_only_and_needs_the_registry(self):
        record, obs = fresh('two_turn_locked_move', 'p1')
        raw = json.loads(record['raw_request'])
        raw['active'][0]['moves'][0].update(pp=15, maxpp=16, target='normal', disabled=False)
        forged_text = json.dumps(raw, separators=(',', ':'))
        forged_obs = forge_observation(obs, lambda o: o['request']['active']['moves'][0].update(pp=15, maxpp=16))
        forged = build_request_knowledge('p1', forged_text, forged_obs, FRESH_DELIVERY)
        self.assertEqual(validate_request_knowledge(forged, forged_obs)['delivery_authority'], 'structure_only')

        def registry(text, cursor=obs['event_cursor'], owner='p1'):
            builder = SourceRegistryBuilder()
            builder.add_request_delivery(owner, 0, cursor, text)
            return builder.freeze()
        self.rejects('registry-delivery', forged, forged_obs, delivery_registry=registry(record['raw_request']))
        self.assertEqual(validate_request_knowledge(record, obs, delivery_registry=registry(record['raw_request']))['delivery_authority'], 'registry_bound')
        # Wrong owner key, wrong cursor, wrong type.
        self.rejects('registry-delivery', record, obs, delivery_registry=registry(record['raw_request'], owner='p2'))
        self.rejects('registry-delivery', record, obs, delivery_registry=registry(record['raw_request'], cursor=obs['event_cursor'] + 1))
        self.rejects('registry-type', record, obs, delivery_registry=object())
        # Requestless/terminal claims cannot be bound by a registry: stay structure-only.
        terminal, terminal_obs = fresh('terminal_requestless', 'p1')
        self.assertEqual(validate_request_knowledge(terminal, terminal_obs, delivery_registry=registry('{}', cursor=0))['delivery_authority'], 'structure_only')

    def test_restored_request_is_refused_and_a_stale_but_once_delivered_text_loses_to_the_registry(self):
        case = _DATA['cases']['trapped_after_rejection']
        stale_obs = observation('trapped_after_rejection', 'p1')
        first, second = case['raw_history']['p1']
        self.assertEqual(second, case['raw']['p1']['json'])
        for provenance in ('restored_session', '', None, 'fresh'):
            self.refuses('provenance', 'p1', first, stale_obs, provenance)

        def trap(o):
            o['request']['trapped'] = True
            o['request']['active'].update(trapped=True, can_switch=False)
            actions = o['request']['legal_actions']
            actions['mask'][8] = False; actions['actions'][8] = None; actions['available_indices'] = [0, 1]
            o['decision_availability']['legal_action_indices'] = [0, 1]
        fresh_obs = forge_observation(stale_obs, trap)
        before = build_request_knowledge('p1', first, stale_obs, FRESH_DELIVERY)
        after = build_request_knowledge('p1', second, fresh_obs, FRESH_DELIVERY)
        self.assertEqual((before['active']['trapped'], before['active']['maybe_trapped']), (False, True))
        self.assertEqual((after['active']['trapped'], after['active']['maybe_trapped'], after['active']['derivation']['trapped']), (True, False, 'raw_true'))
        self.assertNotEqual(before['id'], after['id'])
        self.refuses('observation-mismatch', 'p1', first, fresh_obs, FRESH_DELIVERY)
        self.refuses('observation-mismatch', 'p1', second, stale_obs, FRESH_DELIVERY)
        builder = SourceRegistryBuilder()
        builder.add_request_delivery('p1', 0, stale_obs['event_cursor'], first)
        builder.add_request_delivery('p1', 1, stale_obs['event_cursor'], second)
        registry = builder.freeze()
        self.assertEqual(validate_request_knowledge(before, stale_obs)['delivery_authority'], 'structure_only')  # self-consistent, so structure alone cannot tell
        self.rejects('registry-delivery', before, stale_obs, delivery_registry=registry)  # the registry knows a later delivery superseded it
        self.assertEqual(validate_request_knowledge(after, fresh_obs, delivery_registry=registry)['delivery_authority'], 'registry_bound')


class Publication(RequestKnowledgeBase):
    def test_unicode_names_round_trip_with_utf8_environment_unset(self):
        self.assertNotIn('PYTHONUTF8', _clean_env()); self.assertNotIn('PYTHONIOENCODING', _clean_env())
        record, obs = fresh('unicode_names', 'p1')
        name = 'p1: Ñandú 日本'
        self.assertEqual(json.loads(record['raw_request'])['side']['pokemon'][0]['ident'], name)
        payload = json.dumps([{'owner': 'p1', 'raw_request': record['raw_request'], 'observation': obs}], ensure_ascii=False).encode('utf-8')
        env = _clean_env(); env['PYTHONPATH'] = str(ROOT / 'trainer/src')
        run = subprocess.run([sys.executable, '-m', 'neural.request_knowledge', 'build'], input=payload, env=env, capture_output=True, timeout=120, cwd=str(ROOT))
        self.assertEqual(run.returncode, 0, run.stderr.decode('utf-8', 'replace'))
        self.assertEqual(run.stdout, canonical_request_knowledge_json(record) + b'\n')
        self.assertIn(name.encode('utf-8'), run.stdout)
        self.assertEqual(json.loads(run.stdout.decode('utf-8')), record)
        ts_record = _DATA['records']['unicode_names']['v2/p1']
        self.assertEqual(canonical_request_knowledge_json(ts_record), run.stdout[:-1])


if __name__ == '__main__':
    unittest.main()
