import tempfile
import unittest
from pathlib import Path

import numpy as np

from neural.live_private_features import (
    FEATURE_DIM,
    FEATURE_DIM_V3,
    FEATURE_DIM_V4,
    FEATURE_DIM_V5,
    FEATURE_DIM_V6,
    FEATURE_DIM_V7,
    FEATURE_NAMES_V6,
    FEATURE_NAMES_V7,
    FEATURE_VERSION,
    FEATURE_VERSION_V6,
    FEATURE_VERSION_V7,
    V7_SLICE5_FEATURE_NAMES,
    validate_live_private_feature_metadata,
)
from neural.moves_actions_counterfactual_diagnostic import (
    BASE_LOG,
    _features,
    _request,
    _FOUR,
    _FLAME,
    _AIR,
    evaluate_state_counterfactuals,
)


def _value(features, name):
    return float(features[FEATURE_NAMES_V7.index(name)])


class LivePrivateFeaturesV7Test(unittest.TestCase):
    def test_v7_is_immutable_extension_and_older_versions_are_unchanged(self):
        self.assertEqual(FEATURE_VERSION, "live-private-belief-v2")
        self.assertEqual(FEATURE_DIM, 115)
        self.assertEqual(FEATURE_DIM_V3, 217)
        self.assertEqual(FEATURE_DIM_V4, 765)
        self.assertEqual(FEATURE_DIM_V5, 2293)
        self.assertEqual(FEATURE_DIM_V6, 2493)
        self.assertEqual(FEATURE_VERSION_V7, "live-private-belief-v7")
        self.assertEqual(FEATURE_DIM_V7, 3208)
        # v6 is the exact ordered prefix of v7.
        self.assertEqual(FEATURE_NAMES_V7[:FEATURE_DIM_V6], FEATURE_NAMES_V6)
        self.assertEqual(FEATURE_NAMES_V7[FEATURE_DIM_V6:], V7_SLICE5_FEATURE_NAMES)
        self.assertEqual(len(set(FEATURE_NAMES_V7)), len(FEATURE_NAMES_V7))

    def test_metadata_is_strict_and_live_default_remains_v2(self):
        validate_live_private_feature_metadata(
            feature_version=FEATURE_VERSION_V7,
            feature_dim=FEATURE_DIM_V7,
            expected_version=FEATURE_VERSION_V7,
        )
        with self.assertRaises(ValueError):
            validate_live_private_feature_metadata(
                feature_version=FEATURE_VERSION,
                feature_dim=FEATURE_DIM,
                expected_version=FEATURE_VERSION_V7,
            )
        from neural.live_eval_server import _validate_live_private_checkpoint

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "metadata-only.pt"
            # Live default v2 stays accepted; v7 is rejected by strict prod checks.
            _validate_live_private_checkpoint(
                {"feature_version": FEATURE_VERSION, "input_size": FEATURE_DIM},
                path,
            )
            with self.assertRaises(ValueError):
                _validate_live_private_checkpoint(
                    {"feature_version": FEATURE_VERSION_V7, "input_size": FEATURE_DIM_V7},
                    path,
                )

    def test_own_move_identity_known_vs_unknown(self):
        known = _features(request=_request([_FLAME, _AIR]))
        self.assertEqual(_value(known, "own_active_move_slot_1_known"), 1.0)
        self.assertEqual(_value(known, "own_active_move_slot_1_provenance_request"), 1.0)
        # Slot 3/4 absent from the request -> represented as unknown, not collapsed.
        self.assertEqual(_value(known, "own_active_move_slot_3_unknown"), 1.0)
        self.assertEqual(_value(known, "own_active_move_slot_3_known"), 0.0)

    def test_pp_known_vs_unknown_represented(self):
        with_pp = _features(request=_request([_FLAME, _AIR]))
        without_pp = _features(request=_request([{"move": "Flamethrower", "id": "flamethrower"}, _AIR]))
        self.assertEqual(_value(with_pp, "own_active_move_slot_1_pp_known"), 1.0)
        self.assertEqual(_value(without_pp, "own_active_move_slot_1_pp_known"), 0.0)
        self.assertFalse(np.allclose(with_pp, without_pp))

    def test_disabled_recharge_two_turn_and_taunt_constraints(self):
        disabled = _features(request=_request([dict(_FLAME, disabled=True), _AIR]))
        self.assertEqual(_value(disabled, "own_active_move_slot_1_disabled"), 1.0)

        recharge = _features(request=_request([{"move": "Recharge", "id": "recharge"}]))
        self.assertEqual(_value(recharge, "own_recharge_state_active"), 1.0)
        self.assertEqual(_value(recharge, "own_must_recharge"), 1.0)
        self.assertEqual(_value(recharge, "own_two_turn_lock_state_active"), 0.0)

        two_turn = _features(request=_request([{"move": "Outrage", "id": "outrage"}]))
        self.assertEqual(_value(two_turn, "own_two_turn_lock_state_active"), 1.0)
        self.assertEqual(_value(two_turn, "own_recharge_state_active"), 0.0)

        taunt = _features(log=[*BASE_LOG, "|-start|p1a: Charizard|move: Taunt"], request=_request(_FOUR))
        self.assertEqual(_value(taunt, "own_taunt_state_active"), 1.0)

    def test_encore_and_single_move_lock_represented(self):
        encore = _features(
            log=[*BASE_LOG, "|-start|p1a: Charizard|move: Encore"],
            request=_request([dict(_FLAME, disabled=True), _AIR]),
        )
        self.assertEqual(_value(encore, "own_encore_lock_state_active"), 1.0)
        self.assertEqual(_value(encore, "own_single_move_lock_state_active"), 1.0)
        # No encore volatile -> a single selectable move is inferred as a choice lock.
        choice = _features(
            request=_request([_FLAME, dict(_AIR, disabled=True)])
        )
        self.assertEqual(_value(choice, "own_choice_lock_inferred"), 1.0)
        self.assertEqual(_value(choice, "own_encore_lock_state_active"), 0.0)

    def test_opponent_revealed_move_represented(self):
        revealed = _features(
            log=[*BASE_LOG, "|move|p2a: Blastoise|Surf|p1a: Charizard"], request=_request(_FOUR)
        )
        unknown = _features(request=_request(_FOUR))
        self.assertEqual(_value(revealed, "opponent_active_move_slot_1_revealed"), 1.0)
        self.assertEqual(_value(revealed, "opponent_active_move_slot_1_provenance_protocol"), 1.0)
        self.assertEqual(_value(unknown, "opponent_active_move_slot_1_unknown"), 1.0)
        self.assertFalse(np.allclose(revealed, unknown))

    def test_all_required_state_counterfactuals_change_features(self):
        report = evaluate_state_counterfactuals()
        for name, changed in report.items():
            self.assertTrue(changed, f"counterfactual {name} produced no feature change")


if __name__ == "__main__":
    unittest.main()
