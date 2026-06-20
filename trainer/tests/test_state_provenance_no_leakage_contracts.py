"""Batch A no-leakage / provenance contract tests.

These guard the rules in
`artifacts/training_plan/state_provenance_schema_design_for_remaining_gaps.md`
before the full state schema is implemented. They are pure-Python, torch-free,
and do not materialize, train, or touch any live default.
"""

import unittest

from neural.delayed_damage import resolve_delayed_attacks
from neural.prevention import apply_immediate_prevention
from neural.provenance_contracts import (
    AbilityKnownness,
    ConfusionProvenance,
    EffectiveAbility,
    SleepProvenance,
    assert_no_hidden_sampled_values,
    confusion_provenance,
    delayed_landing_resolvable,
    effective_ability_from_state,
    natural_sleep_provenance,
    rest_sleep_provenance,
    resolve_status_move_ability_block,
    status_move_blocked_by_ability,
    validate_multihit_trace,
    validate_reflection_provenance,
)


class DelayedNoStaleDamageTest(unittest.TestCase):
    def test_target_specific_damage_for_occupant_is_resolvable(self):
        attack = {"damage_by_target": {"gholdengo": 90}, "damage_provenance": "scheduled_calc"}
        result = delayed_landing_resolvable(attack, "gholdengo")
        self.assertTrue(result["available"])
        self.assertEqual(result["mode"], "target_specific")
        self.assertEqual(result["damage"], 90)

    def test_replacement_occupant_cannot_reuse_original_target_damage(self):
        # Damage was computed for the original target only.
        attack = {"damage_by_target": {"original_target": 120}, "damage_provenance": "scheduled_calc"}
        result = delayed_landing_resolvable(attack, "replacement_mon")
        self.assertFalse(result["available"])
        self.assertEqual(result["reason"], "replacement_landing_damage_unavailable")
        self.assertNotIn("damage", result)

    def test_incomplete_resolver_bundle_fails_closed(self):
        attack = {"resolver_inputs": {"source_snapshot": {}, "move_id": "futuresight"}}
        result = delayed_landing_resolvable(attack, "replacement_mon")
        self.assertFalse(result["available"])
        self.assertTrue(result["reason"].startswith("resolver_inputs_incomplete:"))

    def test_complete_resolver_bundle_is_resolvable_without_precomputed_damage(self):
        attack = {
            "resolver_inputs": {
                "source_snapshot": {"id": "src"},
                "move_id": "futuresight",
                "move_type": "psychic",
                "move_category": "special",
                "move_base_power": 120,
                "target_snapshot": {"id": "replacement_mon"},
                "field_snapshot": {"weather": None},
            }
        }
        result = delayed_landing_resolvable(attack, "replacement_mon")
        self.assertTrue(result["available"])
        self.assertEqual(result["mode"], "resolver_inputs_present")
        self.assertIsNone(result["damage"])

    def test_real_delayed_module_fails_closed_for_unkeyed_replacement(self):
        # Integration: the production delayed queue must not invent damage when
        # the slot occupant has no target-specific landing damage.
        state = {
            "delayed_attacks": {
                "p2:0": {
                    "move": "futuresight",
                    "source_side": "p1",
                    "source_pokemon_id": "src",
                    "target_side": "p2",
                    "target_slot": 0,
                    "scheduled_turn": 1,
                    "landing_turn": 3,
                    "damage_by_target": {"original_target": 100},
                    "damage_provenance": "scheduled_calc",
                }
            },
            "active_slots": {"p2:0": {"pokemon_id": "replacement_mon", "hp": 200}},
        }
        result = resolve_delayed_attacks(state, 3)
        self.assertFalse(result["available"])
        self.assertIn("replacement_landing_damage_unavailable", result["reason"])
        # HP untouched: no stale damage applied.
        self.assertEqual(result["state"]["active_slots"]["p2:0"]["hp"], 200)


class DelayedResolverBundleTest(unittest.TestCase):
    """Batch B: complete landing-time resolver bundle path."""

    def _bundle(self, occupant_id: str, landing_damage):
        return {
            "source_snapshot": {"id": "slowking", "side": "p1"},
            "move_id": "futuresight",
            "move_type": "psychic",
            "move_category": "special",
            "move_base_power": 120,
            "target_snapshot": {"pokemon_id": occupant_id, "hp": 360, "max_hp": 360},
            "field_snapshot": {"weather": None, "terrain": None, "screens": []},
            "landing_damage": landing_damage,
            "damage_provenance": "bundled_showdown_resolver_bundle",
        }

    def test_resolver_bundle_exact_damage_for_matching_occupant(self):
        attack = {"resolver_inputs": self._bundle("blissey", 120)}
        result = delayed_landing_resolvable(attack, "blissey")
        self.assertTrue(result["available"])
        self.assertEqual(result["mode"], "resolver_exact")
        self.assertEqual(result["damage"], 120)

    def test_resolver_bundle_rejected_for_mismatched_occupant(self):
        # Bundle was built for blissey; the actual occupant is a different mon.
        attack = {"resolver_inputs": self._bundle("blissey", 120)}
        result = delayed_landing_resolvable(attack, "machamp")
        self.assertFalse(result["available"])
        self.assertEqual(result["reason"], "resolver_target_mismatch")

    def test_resolver_bundle_without_exact_damage_defers(self):
        bundle = self._bundle("blissey", None)
        del bundle["landing_damage"]
        del bundle["damage_provenance"]
        result = delayed_landing_resolvable({"resolver_inputs": bundle}, "blissey")
        self.assertTrue(result["available"])
        self.assertEqual(result["mode"], "resolver_inputs_present")
        self.assertIsNone(result["damage"])

    def test_real_module_applies_resolver_exact_to_matching_occupant(self):
        state = {
            "delayed_attacks": {
                "p2:0": {
                    "move": "futuresight",
                    "source_side": "p1",
                    "source_pokemon_id": "slowking",
                    "target_side": "p2",
                    "target_slot": 0,
                    "scheduled_turn": 1,
                    "landing_turn": 3,
                    "damage_by_target": {},
                    "damage_provenance": None,
                    "resolver_inputs": self._bundle("blissey", 120),
                }
            },
            "active_slots": {"p2:0": {"pokemon_id": "blissey", "hp": 360, "max_hp": 360}},
        }
        result = resolve_delayed_attacks(state, 3)
        self.assertTrue(result["available"])
        self.assertEqual(result["state"]["active_slots"]["p2:0"]["hp"], 240)
        hit = result["events"][0]
        self.assertEqual(hit["result"], "hit")
        self.assertEqual(hit["damage"], 120)
        self.assertEqual(hit["landing_mode"], "resolver_exact")

    def test_real_module_fails_closed_on_resolver_occupant_mismatch(self):
        # Occupant differs from the bundle target; no stale damage may apply.
        state = {
            "delayed_attacks": {
                "p2:0": {
                    "move": "futuresight",
                    "source_side": "p1",
                    "source_pokemon_id": "slowking",
                    "target_side": "p2",
                    "target_slot": 0,
                    "scheduled_turn": 1,
                    "landing_turn": 3,
                    "damage_by_target": {},
                    "damage_provenance": None,
                    "resolver_inputs": self._bundle("blissey", 120),
                }
            },
            "active_slots": {"p2:0": {"pokemon_id": "chansey", "hp": 360, "max_hp": 360}},
        }
        result = resolve_delayed_attacks(state, 3)
        self.assertFalse(result["available"])
        self.assertIn("resolver_target_mismatch", result["reason"])
        self.assertEqual(result["state"]["active_slots"]["p2:0"]["hp"], 360)


class HiddenDurationNoLeakageTest(unittest.TestCase):
    def test_natural_sleep_has_range_and_unknown_hidden_duration(self):
        prov = natural_sleep_provenance(turns_elapsed=1)
        self.assertIsInstance(prov, SleepProvenance)
        self.assertFalse(prov.from_rest)
        self.assertTrue(prov.hidden_duration_unknown)
        # A genuine range, not a single fixed value.
        self.assertLess(prov.remaining_min, prov.remaining_max)

    def test_rest_sleep_has_fixed_duration_provenance(self):
        prov = rest_sleep_provenance(turns_elapsed=0)
        self.assertTrue(prov.from_rest)
        self.assertFalse(prov.hidden_duration_unknown)
        # Fixed: min == max.
        self.assertEqual(prov.remaining_min, prov.remaining_max)

    def test_confusion_has_range_and_unknown_hidden_duration(self):
        prov = confusion_provenance(turns_elapsed=1)
        self.assertIsInstance(prov, ConfusionProvenance)
        self.assertTrue(prov.hidden_duration_unknown)
        self.assertLessEqual(prov.remaining_min, prov.remaining_max)
        self.assertAlmostEqual(prov.self_hit_chance, 1.0 / 3.0)

    def test_no_provenance_field_surfaces_a_sampled_wake_turn(self):
        # The builders take only public elapsed turns, so the dataclass fields
        # can never include a sampled hidden value.
        for prov in (natural_sleep_provenance(2), rest_sleep_provenance(1), confusion_provenance(2)):
            assert_no_hidden_sampled_values(vars(prov))

    def test_assert_rejects_a_leaked_sampled_duration(self):
        leaky = {"turns_elapsed": 1, "sampled_wake_turn": 4}
        with self.assertRaises(ValueError):
            assert_no_hidden_sampled_values(leaky)


class AbilityKnownnessTest(unittest.TestCase):
    def test_known_good_as_gold_blocks_status_move(self):
        defender = EffectiveAbility(ability="goodasgold", knownness=AbilityKnownness.KNOWN)
        result = status_move_blocked_by_ability(defender, "goodasgold")
        self.assertTrue(result["available"])
        self.assertTrue(result["blocked"])

    def test_known_other_ability_does_not_block(self):
        defender = EffectiveAbility(ability="levitate", knownness=AbilityKnownness.KNOWN)
        result = status_move_blocked_by_ability(defender, "goodasgold")
        self.assertTrue(result["available"])
        self.assertFalse(result["blocked"])

    def test_unknown_ability_fails_closed_not_assumed_either_way(self):
        defender = EffectiveAbility(ability=None, knownness=AbilityKnownness.UNKNOWN)
        result = status_move_blocked_by_ability(defender, "goodasgold")
        self.assertFalse(result["available"])
        self.assertIsNone(result["blocked"])

    def test_suppressed_good_as_gold_does_not_block(self):
        defender = EffectiveAbility(ability="goodasgold", knownness=AbilityKnownness.KNOWN, suppressed=True)
        result = status_move_blocked_by_ability(defender, "goodasgold")
        self.assertTrue(result["available"])
        self.assertFalse(result["blocked"])

    def test_ignored_good_as_gold_does_not_block(self):
        defender = EffectiveAbility(ability="goodasgold", knownness=AbilityKnownness.KNOWN, ignored=True)
        result = status_move_blocked_by_ability(defender, "goodasgold")
        self.assertTrue(result["available"])
        self.assertFalse(result["blocked"])


class ReflectionRoutingTest(unittest.TestCase):
    def _complete(self):
        return {
            "original_source": "p1:0",
            "reflector": "p2:0",
            "destination_side": "p1",
            "reflected_target": "p1:0",
            "effect_payload": {"status": "tox"},
            "reflectable": True,
            "reflector_ability": EffectiveAbility(ability="magicbounce", knownness=AbilityKnownness.KNOWN),
        }

    def test_complete_reflection_provenance_resolves(self):
        result = validate_reflection_provenance(self._complete())
        self.assertTrue(result["available"])
        self.assertEqual(result["new_source"], "p2:0")
        self.assertEqual(result["new_target"], "p1:0")
        self.assertEqual(result["destination_side"], "p1")

    def test_missing_destination_side_fails_closed(self):
        reflection = self._complete()
        del reflection["destination_side"]
        result = validate_reflection_provenance(reflection)
        self.assertFalse(result["available"])
        self.assertIn("destination_side", result["reason"])

    def test_unknown_reflector_ability_fails_closed(self):
        reflection = self._complete()
        reflection["reflector_ability"] = EffectiveAbility(ability=None, knownness=AbilityKnownness.UNKNOWN)
        result = validate_reflection_provenance(reflection)
        self.assertFalse(result["available"])
        self.assertEqual(result["reason"], "reflector_ability_unknown")

    def test_non_reflectable_move_fails_closed(self):
        reflection = self._complete()
        reflection["reflectable"] = False
        result = validate_reflection_provenance(reflection)
        self.assertFalse(result["available"])
        self.assertEqual(result["reason"], "move_not_reflectable")


class SequentialMultihitTraceTest(unittest.TestCase):
    def test_complete_per_hit_trace_is_accepted(self):
        trace = [
            {"accuracy_roll": 0.5, "hit": True, "base_power": 20, "damage": 30},
            {"accuracy_roll": 0.9, "hit": True, "base_power": 40, "damage": 35},
            {"accuracy_roll": 0.2, "hit": True, "base_power": 60, "damage": 40},
        ]
        result = validate_multihit_trace(trace)
        self.assertTrue(result["available"])
        self.assertEqual(result["hit_count"], 3)

    def test_missing_per_hit_damage_fails_closed(self):
        trace = [{"accuracy_roll": 0.5, "hit": True, "base_power": 20}]
        result = validate_multihit_trace(trace)
        self.assertFalse(result["available"])
        self.assertTrue(result["reason"].startswith("hit[0]_incomplete:"))

    def test_empty_trace_fails_closed(self):
        result = validate_multihit_trace([])
        self.assertFalse(result["available"])
        self.assertEqual(result["reason"], "per_hit_trace_required")

    def test_distribution_summary_is_not_an_exact_trace(self):
        summary = {"multihit_min": 1, "multihit_max": 10, "multihit_expected": 4.2}
        result = validate_multihit_trace(summary)
        self.assertFalse(result["available"])
        self.assertEqual(result["reason"], "summary_is_not_exact_trace")


class EffectiveAbilityProvenanceTest(unittest.TestCase):
    """Batch C: ability knownness/suppression read from dict state."""

    def test_known_ability_is_surfaced(self):
        eff = effective_ability_from_state({"ability": "Good as Gold", "ability_known": True})
        self.assertEqual(eff.ability, "goodasgold")
        self.assertEqual(eff.knownness, AbilityKnownness.KNOWN)

    def test_unknown_ability_identity_is_not_surfaced(self):
        # No ability_known flag => unknown; the raw (unrevealed) identity is hidden.
        eff = effective_ability_from_state({"ability": "Good as Gold"})
        self.assertEqual(eff.knownness, AbilityKnownness.UNKNOWN)
        self.assertIsNone(eff.ability)

    def test_inferred_ability_knownness(self):
        eff = effective_ability_from_state({"ability": "Levitate", "ability_known": "inferred"})
        self.assertEqual(eff.knownness, AbilityKnownness.INFERRED)

    def test_suppressed_and_ignored_make_ability_inactive(self):
        eff = effective_ability_from_state(
            {"ability": "Good as Gold", "ability_known": True, "ability_suppressed": True},
            {"ability_ignoring": True},
        )
        self.assertTrue(eff.suppressed)
        self.assertTrue(eff.ignored)
        self.assertFalse(eff.is_active)


class GoodAsGoldResolverTest(unittest.TestCase):
    def test_non_status_move_is_not_applicable(self):
        result = resolve_status_move_ability_block(
            {"ability": "Good as Gold", "ability_known": True}, {}, {"name": "Tackle", "category": "Physical"}
        )
        self.assertIsNone(result)

    def test_unknown_ability_is_not_a_guess(self):
        # Unknown ability => fall through (None), never a silent "not blocked".
        result = resolve_status_move_ability_block(
            {"ability": "Good as Gold"}, {}, {"name": "Spore", "category": "Status"}
        )
        self.assertIsNone(result)

    def test_known_good_as_gold_blocks(self):
        result = resolve_status_move_ability_block(
            {"ability": "Good as Gold", "ability_known": True}, {}, {"name": "Spore", "category": "Status"}
        )
        self.assertTrue(result["prevented"])

    def test_suppressed_good_as_gold_does_not_block(self):
        result = resolve_status_move_ability_block(
            {"ability": "Good as Gold", "ability_known": True, "ability_suppressed": True},
            {},
            {"name": "Spore", "category": "Status"},
        )
        self.assertFalse(result["prevented"])

    def test_ignored_good_as_gold_does_not_block(self):
        result = resolve_status_move_ability_block(
            {"ability": "Good as Gold", "ability_known": True},
            {"ability_ignoring": True},
            {"name": "Spore", "category": "Status"},
        )
        self.assertFalse(result["prevented"])


class ImmediatePreventionAbilityReflectionTest(unittest.TestCase):
    """Batch C: prevention.py wiring for Good as Gold and Magic Bounce."""

    def test_good_as_gold_known_blocks_status_move(self):
        state = {"attacker": {"ability": "Effect Spore"}, "target": {"ability": "Good as Gold", "ability_known": True}}
        result = apply_immediate_prevention(state, {"name": "Spore", "category": "Status", "status": "slp"})
        self.assertTrue(result["available"])
        self.assertTrue(result["prevented"])
        self.assertTrue(result.get("blocked"))

    def test_good_as_gold_unknown_does_not_block(self):
        # Unrevealed ability: this path makes no guess (prevented False); the
        # harness keeps the unknown-ability scenario an explicit fixture GAP.
        state = {"attacker": {"ability": "Effect Spore"}, "target": {"ability": "Good as Gold"}}
        result = apply_immediate_prevention(state, {"name": "Spore", "category": "Status", "status": "slp"})
        self.assertTrue(result["available"])
        self.assertFalse(result["prevented"])

    def test_good_as_gold_suppressed_does_not_block(self):
        state = {
            "attacker": {"ability": "Effect Spore"},
            "target": {"ability": "Good as Gold", "ability_known": True, "ability_suppressed": True},
        }
        result = apply_immediate_prevention(state, {"name": "Spore", "category": "Status", "status": "slp"})
        self.assertTrue(result["available"])
        self.assertFalse(result["prevented"])

    def _reflection_state(self, with_payload=True):
        reflection = {
            "original_source": "p2:0",
            "reflector": "p1:0",
            "destination_side": "p2",
            "reflected_target": "p2:0",
        }
        if with_payload:
            reflection["effect_payload"] = {"side_condition": "stealthrock"}
        return {
            "attacker": {"ability": "Synchronize"},
            "target": {"ability": "Magic Bounce", "ability_known": True},
            "reflection": reflection,
        }

    def test_magic_bounce_complete_reflection(self):
        result = apply_immediate_prevention(
            self._reflection_state(), {"name": "Stealth Rock", "reflectable": True, "category": "Status"}
        )
        self.assertTrue(result["available"])
        self.assertTrue(result["reflected"])
        self.assertEqual(result["destination_side"], "p2")

    def test_magic_bounce_incomplete_payload_fails_closed(self):
        result = apply_immediate_prevention(
            self._reflection_state(with_payload=False),
            {"name": "Stealth Rock", "reflectable": True, "category": "Status"},
        )
        self.assertFalse(result["available"])
        self.assertIn("effect_payload", result["reason"])

    def test_magic_bounce_unknown_ability_does_not_reflect(self):
        state = self._reflection_state()
        state["target"] = {"ability": "Magic Bounce"}  # not known
        result = apply_immediate_prevention(state, {"name": "Stealth Rock", "reflectable": True, "category": "Status"})
        self.assertTrue(result["available"])
        self.assertFalse(bool(result.get("reflected")))


if __name__ == "__main__":
    unittest.main()
