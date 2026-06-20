import unittest

from neural.delayed_damage import resolve_delayed_attacks, run_delayed_timeline, schedule_delayed_attack
from neural.end_of_turn import apply_end_of_turn, apply_end_of_turns
from neural.rollout_parity import run_harness
from neural.entry_hazards import hazard_switch_transition
from neural.prevention import apply_immediate_prevention


class RolloutParityHarnessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = run_harness()

    def test_oracle_vs_local_report_has_no_wrong_exact_failures(self):
        self.assertEqual(self.report["summary"]["FAIL"], 0)
        self.assertGreaterEqual(self.report["summary"]["PASS"], 29)
        self.assertGreaterEqual(self.report["summary"]["GAP"], 4)

    def test_harness_distinguishes_transition_phases(self):
        phases = {case["phase"] for case in self.report["cases"]}
        self.assertEqual(phases, {"immediate", "end_of_turn", "switch_entry", "delayed_future"})
        for case in self.report["cases"]:
            self.assertTrue(case["starting_state"])
            self.assertTrue(case["chosen_actions"])
            self.assertIn(case["status"], {"PASS", "FAIL", "GAP"})
            self.assertIn("diff", case)

    def test_switch_entry_cases_match_showdown(self):
        cases = {case["id"]: case for case in self.report["cases"]}
        for case_id in (
            "stealth_rock_type_effectiveness",
            "spikes_grounded_one_layer",
            "spikes_airborne_immunity",
            "toxic_spikes_grounded_poison",
            "sticky_web_grounded_speed_drop",
            "heavy_duty_boots_prevents_hazards",
        ):
            self.assertEqual(cases[case_id]["status"], "PASS", msg=cases[case_id]["diff"])

    def test_supported_residual_cases_match_showdown(self):
        cases = {case["id"]: case for case in self.report["cases"]}
        for case_id in (
            "toxic_ramp_three_turns",
            "leech_seed_damage_and_heal",
            "burn_residual",
            "regular_poison_residual",
            "salt_cure_normal_residual",
            "salt_cure_water_residual",
            "salt_cure_steel_residual",
            "sandstorm_chip",
            "grassy_terrain_healing",
            "grassy_terrain_airborne_no_heal",
            "no_residual_unchanged",
        ):
            self.assertEqual(cases[case_id]["status"], "PASS", msg=cases[case_id]["diff"])

    def test_unsupported_residual_and_delayed_cases_are_explicit_gaps(self):
        cases = {case["id"]: case for case in self.report["cases"]}
        for case_id in (
            "binding_residual",
            "future_sight_replacement_damage_unavailable",
            "magic_bounce_reflection_gap",
            "good_as_gold_status_gap",
        ):
            self.assertEqual(cases[case_id]["status"], "GAP")
            self.assertTrue(cases[case_id]["local"]["reason"])

    def test_supported_prevention_cases_match_showdown(self):
        cases = {case["id"]: case for case in self.report["cases"]}
        for case_id in (
            "psychic_terrain_blocks_grounded_priority",
            "psychic_terrain_does_not_block_non_priority",
            "psychic_terrain_does_not_block_airborne_target",
            "psychic_terrain_does_not_block_grassy_glide_without_grassy_terrain",
            "substitute_blocks_leech_seed",
            "misty_terrain_blocks_status",
            "electric_terrain_blocks_sleep",
            "damp_blocks_explosion",
        ):
            self.assertEqual(cases[case_id]["status"], "PASS", msg=cases[case_id]["diff"])

    def test_supported_delayed_damage_cases_match_showdown(self):
        cases = {case["id"]: case for case in self.report["cases"]}
        for case_id in (
            "future_sight_lands_later",
            "future_sight_hits_replacement_in_target_slot",
            "future_sight_duplicate_schedule_fails",
            "doom_desire_lands_later",
        ):
            self.assertEqual(cases[case_id]["status"], "PASS", msg=cases[case_id]["diff"])

    def test_delayed_damage_consumes_empty_slot_without_damage(self):
        state = {"active_slots": {}, "delayed_attacks": {}}
        scheduled = schedule_delayed_attack(
            state,
            {
                "move": "Future Sight",
                "scheduled_turn": 1,
                "source_side": "p1",
                "source_pokemon_id": "slowking",
                "target_side": "p2",
                "target_slot": 0,
                "damage_by_target": {"machamp": 100},
                "damage_provenance": "fixture",
            },
        )
        self.assertTrue(scheduled["scheduled"])
        result = resolve_delayed_attacks(scheduled["state"], 3)
        self.assertTrue(result["available"])
        self.assertEqual(result["events"][0]["result"], "no_target")
        self.assertEqual(result["state"]["delayed_attacks"], {})

    def test_delayed_damage_fails_closed_for_unknown_replacement_damage(self):
        state = {
            "active_slots": {"p2:0": {"pokemon_id": "blissey", "hp": 651, "max_hp": 651}},
            "delayed_attacks": {},
        }
        result = run_delayed_timeline(
            state,
            [
                {
                    "turn": 1,
                    "schedule": {
                        "move": "Future Sight",
                        "scheduled_turn": 1,
                        "source_side": "p1",
                        "source_pokemon_id": "slowking",
                        "target_side": "p2",
                        "target_slot": 0,
                        "damage_by_target": {"machamp": 321},
                        "damage_provenance": "fixture",
                    },
                },
                {"turn": 2},
                {"turn": 3},
            ],
        )
        self.assertFalse(result["available"])
        self.assertIn("landing_damage_missing_for:blissey", result["reason"])

    def test_residual_helper_handles_hp_floor_and_fainting(self):
        state = {
            "combatants": {
                "p1": {
                    "hp": 1,
                    "max_hp": 160,
                    "status": "brn",
                    "types": ["Normal"],
                    "ability": "Run Away",
                    "item": "",
                    "residual_modifiers_known": True,
                    "volatiles": {},
                }
            }
        }
        result = apply_end_of_turn(state)
        self.assertTrue(result["available"])
        self.assertEqual(result["state"]["combatants"]["p1"]["hp"], 0)
        self.assertEqual(result["events"][0]["damage"], 1)

    def test_residual_helper_requires_toxic_stage_and_modifier_provenance(self):
        base = {
            "combatants": {
                "p1": {
                    "hp": 160,
                    "max_hp": 160,
                    "status": "tox",
                    "types": ["Normal"],
                    "ability": "Run Away",
                    "item": "",
                    "residual_modifiers_known": True,
                    "volatiles": {},
                }
            }
        }
        self.assertFalse(apply_end_of_turn(base)["available"])
        base["combatants"]["p1"]["toxic_stage"] = 0
        base["combatants"]["p1"]["residual_modifiers_known"] = False
        self.assertFalse(apply_end_of_turns(base, 2)["available"])

    def test_residual_helper_uses_showdown_order_for_supported_effects(self):
        state = {
            "weather": "sandstorm",
            "combatants": {
                "p1": {
                    "hp": 160,
                    "max_hp": 160,
                    "status": None,
                    "types": ["Normal"],
                    "ability": "Run Away",
                    "item": "",
                    "residual_modifiers_known": True,
                    "volatiles": {},
                },
                "p2": {
                    "hp": 160,
                    "max_hp": 160,
                    "status": "brn",
                    "types": ["Normal"],
                    "ability": "Run Away",
                    "item": "",
                    "residual_modifiers_known": True,
                    "volatiles": {"leechseed": {"source": "p1"}, "saltcure": True},
                },
            },
        }
        result = apply_end_of_turn(state)
        self.assertTrue(result["available"])
        effects = [event["effect"] for event in result["events"]]
        self.assertEqual(effects, ["sandstorm", "sandstorm", "leechseed", "brn", "saltcure"])

    def test_grassy_terrain_healing_requires_grounding(self):
        state = {
            "terrain": "grassyterrain",
            "combatants": {
                "p1": {
                    "hp": 80,
                    "max_hp": 160,
                    "status": None,
                    "types": [],
                    "ability": "",
                    "item": "",
                    "residual_modifiers_known": True,
                    "volatiles": {},
                }
            },
        }
        result = apply_end_of_turn(state)
        self.assertFalse(result["available"])
        self.assertEqual(result["reason"], "p1:grassy_terrain_grounding_required")

    def test_spikes_layer_fractions_are_not_linear(self):
        target = {"types": ["Electric"], "hp_fraction": 1.0}
        self.assertAlmostEqual(hazard_switch_transition(target, {"spikes": 1})["switch_hazard_damage"], 1 / 8)
        self.assertAlmostEqual(hazard_switch_transition(target, {"spikes": 2})["switch_hazard_damage"], 1 / 6)
        self.assertAlmostEqual(hazard_switch_transition(target, {"spikes": 3})["switch_hazard_damage"], 1 / 4)

    def test_prevention_helper_fails_closed_without_grounding(self):
        result = apply_immediate_prevention(
            {"terrain": "psychicterrain", "target": {}, "attacker": {"types": ["Normal"]}},
            {"name": "Quick Attack", "priority": 1},
        )
        self.assertFalse(result["available"])
        self.assertEqual(result["reason"], "target_grounding_required_for_psychic_terrain")


if __name__ == "__main__":
    unittest.main()
