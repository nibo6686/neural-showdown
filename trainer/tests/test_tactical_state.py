import unittest

import numpy as np

from neural.action_features import ACTION_FEATURE_NAMES, build_action_feature_vector
from neural.live_private_features import FEATURE_DIM, FEATURE_NAMES, FEATURE_VERSION, build_live_private_feature_vector
from neural.tactical_state import build_tactical_state, tactical_state_feature_vector


class TacticalStateTest(unittest.TestCase):
    def test_leech_seed_already_active_is_tracked(self):
        state = build_tactical_state(
            [
                "|turn|1",
                "|switch|p2a: Volbeat|Volbeat, L80|100/100",
                "|move|p1a: Jumpluff|Leech Seed|p2a: Volbeat",
                "|-start|p2a: Volbeat|move: Leech Seed",
            ],
            perspective_side="p1",
        )
        self.assertIn("leechseed", state["opponent"]["volatiles"])
        vector = tactical_state_feature_vector(state)
        self.assertEqual(float(vector[3]), 1.0)

    def test_repeated_failed_leech_seed_sets_recent_failure(self):
        state = build_tactical_state(
            [
                "|turn|1",
                "|move|p1a: Jumpluff|Leech Seed|p2a: Brute Bonnet",
                "|-fail|p2a: Brute Bonnet|move: Leech Seed",
                "|turn|2",
                "|move|p1a: Jumpluff|Leech Seed|p2a: Brute Bonnet",
                "|-fail|p2a: Brute Bonnet|move: Leech Seed",
            ],
            perspective_side="p1",
        )
        self.assertGreaterEqual(state["own"]["same_move_chain"]["failed_count"], 2)
        self.assertGreater(tactical_state_feature_vector(state)[25], 0.0)

    def test_dry_skin_healing_from_water_move_is_tracked(self):
        state = build_tactical_state(
            [
                "|turn|1",
                "|move|p1a: Lapras|Sparkling Aria|p2a: Toxicroak",
                "|-heal|p2a: Toxicroak|100/100|[from] ability: Dry Skin",
            ],
            perspective_side="p1",
        )
        self.assertTrue(any(event["result"] == "healed_target" for event in state["recent_events"]))
        self.assertGreater(tactical_state_feature_vector(state)[27], 0.0)

    def test_side_hazard_layers_are_tracked(self):
        state = build_tactical_state(
            [
                "|turn|1",
                "|-sidestart|p2|move: Stealth Rock",
                "|-sidestart|p2|Spikes",
                "|-sidestart|p2|Spikes",
            ],
            perspective_side="p1",
        )
        self.assertEqual(state["opponent"]["side_conditions"]["stealthrock"], 1)
        self.assertEqual(state["opponent"]["side_conditions"]["spikes"], 2)


class TacticalFeatureIntegrationTest(unittest.TestCase):
    def test_action_features_differ_before_and_after_target_is_seeded(self):
        action = {"kind": "move", "label": "move: Leech Seed", "index": 0}
        private = {"active_moves": [{"id": "leechseed", "name": "Leech Seed", "pp": 10, "maxpp": 10}]}
        before = build_action_feature_vector(action, private, tactical_state=build_tactical_state([], perspective_side="p1"))
        after_state = build_tactical_state(
            ["|-start|p2a: Volbeat|move: Leech Seed"],
            perspective_side="p1",
        )
        after = build_action_feature_vector(action, private, tactical_state=after_state)
        index = ACTION_FEATURE_NAMES.index("target_already_seeded")
        self.assertEqual(float(before[index]), 0.0)
        self.assertEqual(float(after[index]), 1.0)

    def test_action_features_differ_against_dry_skin_known_target(self):
        action = {"kind": "move", "label": "move: Sparkling Aria", "index": 0}
        private = {"active_moves": [{"id": "sparklingaria", "name": "Sparkling Aria", "pp": 10, "maxpp": 10}]}
        normal = build_action_feature_vector(action, private, tactical_state=build_tactical_state([], perspective_side="p1"))
        dry_skin = build_tactical_state(["|-ability|p2a: Toxicroak|Dry Skin"], perspective_side="p1")
        against_dry_skin = build_action_feature_vector(action, private, tactical_state=dry_skin)
        index = ACTION_FEATURE_NAMES.index("target_known_or_possible_ability_absorbs_move_type")
        self.assertEqual(float(normal[index]), 0.0)
        self.assertEqual(float(against_dry_skin[index]), 1.0)

    def test_v2_live_feature_vector_is_versioned_and_stable(self):
        public = np.zeros(31, dtype=np.float32)
        features, debug = build_live_private_feature_vector(
            public_features=public,
            private_state={"team": [{"species": "Lapras", "active": True, "hp_fraction": 1.0}]},
            opponent_belief={"opponents": []},
            trajectory={"protocol_log": []},
            player_side="p1",
        )
        self.assertEqual(FEATURE_VERSION, "live-private-belief-v2")
        self.assertEqual(features.shape[0], FEATURE_DIM)
        self.assertEqual(len(FEATURE_NAMES), FEATURE_DIM)
        self.assertEqual(debug["feature_version"], FEATURE_VERSION)


if __name__ == "__main__":
    unittest.main()

