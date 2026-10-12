"""Prompt 13 / S01a characterization (no production change).

Every `CURRENT_BEHAVIOR_LOSSY` test passes by asserting what the Python side does TODAY with real
addressed requests, and is expected to flip when S01b lands. The data comes from the test-owned pinned
BattleStream harness plus the real PipelineIntegrationSession (see the witness header); Python only
consumes the resulting JSON and runs its own validators.
"""
import copy
import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

from neural.pipeline_record import PipelineRecordError, _validate_episode_observation, validate_pipeline_bundle
from neural.ts_identity import observation_digest

ROOT = Path(__file__).resolve().parents[2]
WITNESS = ROOT / 'docs/planning/perspective-fidelity-prompt13-witness.cjs'
V1, V2 = 'observable-battle-state/v1', 'observable-battle-state/v2'
OWNERS = ('p1', 'p2')
MOVE_KEYS = ['slot', 'move', 'id', 'pp', 'maxpp', 'target', 'disabled', 'type', 'category', 'base_power', 'accuracy']
_CASES = None


def setUpModule():
    """Trusted local owner side: run the pinned witness (Node), without encoding overrides."""
    global _CASES
    env = {k: v for k, v in os.environ.items() if k.upper() not in ('PYTHONUTF8', 'PYTHONIOENCODING')}
    env['PYTHON'] = sys.executable
    run = subprocess.run(['node', str(WITNESS)], cwd=str(ROOT), env=env, capture_output=True, timeout=300)
    if run.returncode != 0:
        raise RuntimeError('witness harness failed: ' + run.stderr.decode('utf-8', 'replace')[:500])
    _CASES = json.loads(run.stdout.decode('utf-8'))


def subject(case_id):
    return 'p2' if case_id.endswith('_mirror') else 'p1'


def request_of(case, owner, version=V2):
    return case['versions'][version]['observations'][owner]['request']


def raw_of(case, owner):
    return json.loads(case['raw'][owner]['json'])


def keys_deep(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from keys_deep(child)
    elif isinstance(value, list):
        for child in value:
            yield from keys_deep(child)


def resealed(observation, mutate):
    """Independent forger: mutate a deep copy and recompute the legacy observation identity."""
    forged = copy.deepcopy(observation)
    mutate(forged)
    forged['observation_id'] = observation_digest(forged)
    return forged


def check_observation(observation):
    return _validate_episode_observation(copy.deepcopy(observation), observation['perspective'], observation['battle_id'], 'characterization')


class RequestKnowledgeCharacterization(unittest.TestCase):
    def test_control_case_inventory_and_actionable_bundles_validate(self):
        self.assertEqual(len(_CASES), 20)
        validated = 0
        for case_id, case in _CASES.items():
            for version, entry in case['versions'].items():
                if entry['bundles']:
                    for owner in OWNERS:
                        record = validate_pipeline_bundle(copy.deepcopy(entry['bundles'][owner]))
                        self.assertEqual(record['perspective'], owner, case_id)
                        validated += 1
        self.assertEqual(validated, 68)

    def test_control_every_v2_observation_passes_the_python_observation_validator(self):
        for case_id, case in _CASES.items():
            for owner in OWNERS:
                check_observation(case['versions'][V2]['observations'][owner])
                self.assertEqual(request_of(case, owner, V1), request_of(case, owner, V2), case_id)

    def test_current_behavior_lossy_locked_recharge_struggle_arrive_as_zero_sentinels(self):
        for case_id in ('two_turn_locked_move', 'two_turn_locked_move_mirror', 'recharge', 'recharge_mirror'):
            case, owner = _CASES[case_id], subject(case_id)
            raw_active = raw_of(case, owner)['active'][0]
            self.assertEqual(list(raw_active), ['moves', 'trapped'])
            self.assertEqual(set(raw_active['moves'][0]), {'move', 'id'})  # PP/maxpp/target/disabled all omitted
            for version in (V1, V2):
                carried = request_of(case, owner, version)['active']
                move = carried['moves'][0]
                self.assertEqual(list(move), MOVE_KEYS)
                self.assertEqual((move['pp'], move['maxpp'], move['target'], move['disabled']), (0, 0, 'normal', False))
                self.assertEqual((carried['trapped'], carried['can_switch'], carried['can_terastallize']), (True, False, False))
            legal = request_of(case, owner)['legal_actions']
            self.assertEqual(legal['available_indices'], [0])
            self.assertEqual(legal['actions'][0]['choice'], 'default')
        for case_id in ('struggle_fallback', 'struggle_fallback_mirror'):
            case, owner = _CASES[case_id], subject(case_id)
            self.assertEqual(raw_of(case, owner)['active'][0]['moves'],
                             [{'move': 'Struggle', 'id': 'struggle', 'target': 'randomNormal', 'disabled': False}])
            move = request_of(case, owner)['active']['moves'][0]
            self.assertEqual((move['pp'], move['maxpp'], move['target'], move['disabled']), (0, 0, 'randomNormal', False))

    def test_current_behavior_lossy_real_pp_zero_equals_absent_pp(self):
        zero = _CASES['real_pp_zero']
        raw_move = raw_of(zero, 'p1')['active'][0]['moves'][0]
        self.assertEqual((raw_move['pp'], raw_move['maxpp'], raw_move['disabled']), (0, 8, True))
        carried_zero = request_of(zero, 'p1')['active']['moves'][0]
        locked = request_of(_CASES['two_turn_locked_move'], 'p1')['active']['moves'][0]
        self.assertEqual(carried_zero['pp'], locked['pp'])  # real zero and absent PP: the same pp field
        self.assertEqual((locked['maxpp'], carried_zero['maxpp']), (0, 8))  # only an unmarked maxpp==0 convention separates them
        ordinary = request_of(_CASES['ordinary_slots'], 'p1')['active']['moves'][0]
        self.assertEqual(raw_of(_CASES['ordinary_slots'], 'p1')['active'][0]['moves'][0]['target'], 'normal')
        self.assertEqual((locked['target'], locked['disabled']), (ordinary['target'], ordinary['disabled']))  # omitted == real 'normal'

    def test_current_behavior_lossy_maybe_flags_are_dropped_and_absent_from_every_python_path(self):
        for case_id in ('maybe_disabled_imprison', 'maybe_disabled_imprison_mirror', 'maybe_trapped_shadow_tag', 'maybe_trapped_shadow_tag_mirror'):
            case, owner = _CASES[case_id], subject(case_id)
            flag = 'maybeDisabled' if 'disabled' in case_id else 'maybeTrapped'
            self.assertIs(raw_of(case, owner)['active'][0][flag], True)
            for version in (V1, V2):
                entry = case['versions'][version]
                self.assertFalse([key for key in keys_deep(entry['observations'][owner]) if 'maybe' in key.lower()])
                for bundle in (entry['bundles'] or {}).values():
                    self.assertFalse([key for key in keys_deep(bundle) if 'maybe' in key.lower()])
            carried = request_of(case, owner)['active']
            if flag == 'maybeDisabled':
                self.assertTrue(all(move['disabled'] is False for move in carried['moves']))
                self.assertTrue(case['versions'][V2]['reject_probe']['rejected'])
            else:
                self.assertEqual((carried['trapped'], carried['can_switch']), (False, True))
        # Static check: no Python production module even names the source flags.
        for module in sorted((ROOT / 'trainer/src/neural').glob('*.py')):
            if module.name.startswith(('pipeline_', 'typed_state', 'ts_identity', 'public_')):
                self.assertFalse(re.search(r'maybe_?(disabled|trapped)', module.read_text(encoding='utf-8'), re.I), module.name)

    def test_current_behavior_lossy_non_actionable_states_have_no_active_slots_and_terminal_has_no_request(self):
        wf = _CASES['waiting_and_forced_switch']
        self.assertIsNone(request_of(wf, 'p1')['active'])
        self.assertTrue(request_of(wf, 'p1')['wait'])
        self.assertIsNone(request_of(wf, 'p2')['active'])
        self.assertTrue(request_of(wf, 'p2')['force_switch'])
        for owner in OWNERS:
            for member in request_of(wf, owner)['side']:
                self.assertTrue(all(isinstance(name, str) for name in member['moves']))
        revival = _CASES['revival_selection_and_waiting']
        self.assertTrue(any(member.get('reviving') for member in request_of(revival, 'p1')['side']))
        for owner in OWNERS:
            self.assertIsNone(_CASES['terminal_requestless']['versions'][V2]['observations'][owner]['request'])
            self.assertIsNone(revival['versions'][V2]['after_revival']['observations'][owner]['request'])

    def test_current_behavior_lossy_resealed_false_certainty_is_accepted(self):
        locked = _CASES['two_turn_locked_move']['versions'][V2]['observations']['p1']

        def claim_pp(observation):
            move = observation['request']['active']['moves'][0]
            move['pp'], move['maxpp'] = 15, 16  # fabricated PP for a request that emitted none

        check_observation(resealed(locked, claim_pp))  # accepted: Python has no request-knowledge oracle

        imprison = _CASES['maybe_disabled_imprison']['versions'][V2]['observations']['p1']

        def assert_definite_disable(observation):  # the source only said "maybe"; a definite claim is equally unverifiable
            observation['request']['active']['moves'][0]['disabled'] = True

        check_observation(resealed(imprison, assert_definite_disable))

        mean_look = _CASES['known_trapped_mean_look']['versions'][V2]['observations']['p1']

        def deny_trap(observation):
            observation['request']['active']['trapped'] = False
            observation['request']['trapped'] = False

        check_observation(resealed(mean_look, deny_trap))  # a known trap erased and resealed is accepted

    def test_control_wrong_owner_request_reseal_is_rejected_today(self):
        observation = _CASES['two_turn_locked_move']['versions'][V2]['observations']['p1']
        forged = resealed(observation, lambda o: o['request'].__setitem__('player', 'p2'))
        with self.assertRaises(PipelineRecordError) as raised:
            check_observation(forged)
        self.assertIn('not owned by its perspective', str(raised.exception))
        # Unresealed tamper is rejected by the identity check.
        tampered = copy.deepcopy(observation)
        tampered['request']['active']['moves'][0]['pp'] = 15
        with self.assertRaises(PipelineRecordError):
            check_observation(tampered)


if __name__ == '__main__':
    unittest.main()
