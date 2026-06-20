import unittest

import numpy as np

from neural.action_features import ACTION_FEATURE_NAMES, build_action_feature_vector
from neural.live_private_features import FEATURE_DIM, FEATURE_NAMES, FEATURE_VERSION, build_live_private_feature_vector
from neural.tactical_state import build_tactical_state, snapshot_with_private_state, tactical_action_flags, tactical_state_feature_vector


class TacticalStateTest(unittest.TestCase):
    def test_complete_history_marks_boosts_known(self):
        state = build_tactical_state(
            [
                "|start",
                "|switch|p1a: Espeon|Espeon, L80|100/100",
                "|-boost|p1a: Espeon|spa|2",
                "|-boost|p1a: Espeon|spe|2",
            ],
            perspective_side="p1",
        )
        self.assertTrue(state["history_complete"])
        self.assertTrue(state["own"]["boosts_known"])
        self.assertEqual(state["own"]["boosts"]["spa"], 2)
        self.assertEqual(state["own"]["boosts"]["spe"], 2)

    def test_times_attacked_tracks_direct_hits_and_persists_per_species(self):
        state = build_tactical_state(
            [
                "|start",
                "|switch|p1a: Annihilape|Annihilape, L76|292/292",
                "|switch|p2a: Cresselia|Cresselia, L80|323/323",
                "|move|p2a: Cresselia|Psyshock|p1a: Annihilape",
                "|-damage|p1a: Annihilape|220/292",
                "|move|p2a: Cresselia|Moonblast|p1a: Annihilape",
                "|-damage|p1a: Annihilape|140/292",
                "|-damage|p1a: Annihilape|130/292|[from] psn",
                "|switch|p1a: Pikachu|Pikachu, L80|200/200",
                "|switch|p1a: Annihilape|Annihilape, L76|130/292",
            ],
            perspective_side="p1",
        )
        self.assertTrue(state["own"]["active_times_attacked_known"])
        self.assertEqual(state["own"]["active_times_attacked"], 2)
        annihilape = next(mon for mon in state["own"]["known_team"] if mon["species"] == "Annihilape")
        self.assertEqual(annihilape["times_attacked"], 2)

    def test_times_attacked_is_unknown_without_complete_history(self):
        state = build_tactical_state(
            [
                "|switch|p1a: Annihilape|Annihilape, L76|220/292",
                "|move|p2a: Cresselia|Psyshock|p1a: Annihilape",
                "|-damage|p1a: Annihilape|150/292",
            ],
            perspective_side="p1",
        )
        self.assertFalse(state["own"]["active_times_attacked_known"])
        self.assertEqual(state["own"]["active_times_attacked"], 1)

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

    def test_status_boosts_and_snapshot_are_persistent(self):
        tracker_state = build_tactical_state(
            [
                "|turn|1",
                "|switch|p2a: Gouging Fire|Gouging Fire, L80|239/239 par",
                "|-boost|p2a: Gouging Fire|atk|2",
                "|-boost|p2a: Gouging Fire|atk|4",
                "|-boost|p2a: Gouging Fire|atk|0",
                "|turn|2",
            ],
            perspective_side="p1",
        )
        self.assertEqual(tracker_state["opponent"]["status"], "par")
        self.assertEqual(tracker_state["opponent"]["boosts"]["atk"], 6)
        self.assertIn("boost_capped:p2:atk", tracker_state["warnings"])

    def test_status_move_into_existing_status_flag(self):
        state = build_tactical_state(
            [
                "|turn|5",
                "|switch|p2a: Gouging Fire|Gouging Fire, L80|56/100 par",
            ],
            perspective_side="p1",
        )
        flags = tactical_action_flags({"kind": "move", "label": "move: Thunder Wave"}, tactical_state=state)
        self.assertIn("status_into_existing_status", flags)

    def test_hazard_max_layer_flag_uses_target_side(self):
        state = build_tactical_state(
            [
                "|turn|4",
                "|-sidestart|p2: johnding|move: Toxic Spikes",
                "|turn|5",
                "|-sidestart|p2: johnding|move: Toxic Spikes",
                "|turn|6",
            ],
            perspective_side="p1",
        )
        self.assertEqual(state["opponent"]["side_conditions"]["toxicspikes"], 2)
        flags = tactical_action_flags({"kind": "move", "label": "move: Toxic Spikes"}, tactical_state=state)
        self.assertIn("redundant_hazard_max_layers", flags)

    def test_setup_at_cap_flag(self):
        state = build_tactical_state(
            [
                "|turn|9",
                "|switch|p2a: Gogoat|Gogoat, L84|100/100",
                "|-boost|p2a: Gogoat|atk|6",
                "|-boost|p2a: Gogoat|def|6",
                "|turn|10",
            ],
            perspective_side="p2",
        )
        flags = tactical_action_flags({"kind": "move", "label": "move: Bulk Up"}, tactical_state=state)
        self.assertIn("setup_at_cap", flags)

    def test_known_and_repeated_immunity_flags(self):
        state = build_tactical_state(
            [
                "|turn|10",
                "|switch|p1a: Kingambit|Kingambit, L80|100/100",
                "|switch|p2a: Banette|Banette, L80|100/100",
                "|move|p2a: Banette|Gunk Shot|p1a: Kingambit",
                "|-immune|p1a: Kingambit",
                "|turn|11",
            ],
            perspective_side="p2",
        )
        flags = tactical_action_flags({"kind": "move", "label": "move: Gunk Shot"}, tactical_state=state)
        self.assertIn("known_immunity", flags)
        self.assertIn("repeated_immune_move", flags)

    def test_dragon_into_fairy_immunity_flag(self):
        state = build_tactical_state(
            [
                "|turn|3",
                "|switch|p1a: Gouging Fire|Gouging Fire, L80|100/100",
                "|switch|p2a: Wigglytuff|Wigglytuff, L80|100/100",
            ],
            perspective_side="p1",
        )
        flags = tactical_action_flags({"kind": "move", "label": "move: Outrage"}, tactical_state=state)
        self.assertIn("known_immunity", flags)

    def test_hp_faint_team_and_active_switch_tracking(self):
        state = build_tactical_state(
            [
                "|teamsize|p2|6",
                "|turn|1",
                "|switch|p2a: Veluza|Veluza, L80|277/277",
                "|-damage|p2a: Veluza|56/100",
                "|turn|3",
                "|move|p1a: Wigglytuff|Alluring Voice|p2a: Veluza",
                "|faint|p2a: Veluza",
                "|switch|p2a: Gouging Fire|Gouging Fire, L80|239/239",
                "|turn|5",
                "|-status|p2a: Gouging Fire|par",
                "|-damage|p2a: Gouging Fire|180/239 par",
            ],
            perspective_side="p1",
        )
        opponent = state["opponent"]
        self.assertEqual(opponent["active_species"], "Gouging Fire")
        self.assertEqual(opponent["active_status"], "par")
        self.assertAlmostEqual(opponent["active_hp_fraction"], 180 / 239)
        self.assertIn("Veluza", [mon["species"] for mon in opponent["known_team"]])
        self.assertIn("Gouging Fire", [mon["species"] for mon in opponent["known_team"]])
        self.assertIn("Veluza", opponent["fainted_species"])
        self.assertEqual(opponent["remaining_known_count"], 1)
        self.assertEqual(opponent["total_team_size"], 6)
        self.assertEqual(opponent["unknown_unrevealed_count"], 4)

    def test_public_revealed_moves_usage_and_inferred_pp(self):
        state = build_tactical_state(
            [
                "|turn|1",
                "|switch|p2a: Banette|Banette, L80|100/100",
                "|move|p2a: Banette|Gunk Shot|p1a: Kingambit",
                "|turn|2",
                "|move|p2a: Banette|Gunk Shot|p1a: Kingambit",
            ],
            perspective_side="p1",
        )
        opponent = state["opponent"]
        self.assertIn("Gunk Shot", opponent["revealed_moves_by_species"]["Banette"])
        self.assertEqual(opponent["move_use_counts_by_species"]["Banette"]["gunkshot"], 2)
        pp = opponent["inferred_pp_by_species_move"]["Banette"]["gunkshot"]
        self.assertEqual(pp["provenance"], "inferred_from_public_usage")
        self.assertEqual(pp["observed_uses"], 2)
        self.assertEqual(opponent["exact_pp_by_species_move"]["Banette"], {})

    def test_live_private_snapshot_marks_exact_pp(self):
        state = build_tactical_state(
            ["|turn|1", "|switch|p1a: Pikachu|Pikachu, L80|100/100"],
            perspective_side="p1",
        )
        private_state = {
            "player_side": "p1",
            "active_species": "Pikachu",
            "team": [
                {
                    "ident": "p1: Pikachu",
                    "species": "Pikachu",
                    "condition": "80/100 par",
                    "hp_fraction": 0.8,
                    "status": "par",
                    "active": True,
                    "moves": ["Thunderbolt"],
                    "item": "Light Ball",
                    "ability": "Static",
                    "tera_type": "Electric",
                }
            ],
            "active_moves": [{"id": "thunderbolt", "name": "Thunderbolt", "pp": 10, "maxpp": 15}],
        }
        merged = snapshot_with_private_state(state, private_state)
        own = merged["own"]
        self.assertEqual(own["active_status"], "par")
        self.assertEqual(own["active_hp_fraction"], 0.8)
        self.assertTrue(own["item_known"])
        self.assertTrue(own["ability_known"])
        self.assertTrue(own["tera_type_known"])
        pp = own["exact_pp_by_species_move"]["Pikachu"]["thunderbolt"]
        self.assertEqual(pp["pp"], 10)
        self.assertEqual(pp["maxpp"], 15)
        self.assertEqual(pp["provenance"], "exact_private_request")

    def test_terastallize_protocol_marks_side_and_active_species(self):
        state = build_tactical_state(
            [
                "|turn|1",
                "|switch|p1a: Typhlosion|Typhlosion, L84, M|267/267",
                "|-terastallize|p1a: Typhlosion|Fire",
            ],
            perspective_side="p1",
        )
        own = state["own"]
        self.assertTrue(own["tera_used"])
        self.assertEqual(own["active_tera_type"], "Fire")
        self.assertTrue(own["tera_type_known"])
        typhlosion = next(mon for mon in own["known_team"] if mon["species"] == "Typhlosion")
        self.assertTrue(typhlosion["terastallized"])
        self.assertEqual(typhlosion["tera_type"], "Fire")


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
