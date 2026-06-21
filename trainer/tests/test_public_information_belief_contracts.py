"""Public-information belief + effective-context no-leakage tests.

These guard the rule that the model receives the same *category* of information
a skilled Showdown player has (known species, possible abilities/items, speed
ranges, revealed/inferred public info) but never the hidden truth before it is
revealed. Pure-Python, torch-free; no materialization, training, or live change.
"""

import unittest

from neural.end_of_turn import apply_end_of_turn
from neural.prevention import apply_immediate_prevention
from neural.provenance_contracts import (
    AbilityKnownness,
    EffectiveAbilityContext,
    EffectiveItemContext,
    EffectiveWeatherContext,
    ItemState,
    item_belief_from_public_evidence,
    item_belief_from_state,
    item_blocks,
    neutralizing_gas_suppresses_target,
    own_side_public_knowledge,
    public_ability_belief,
    public_item_belief,
    resolve_status_move_ability_block,
    secondary_effect_blocked,
    source_ignores_target_abilities,
    speed_belief_exact,
    speed_belief_range,
)
from neural.tactical_state import build_tactical_state


class PublicAbilityBeliefTest(unittest.TestCase):
    def test_ordinary_displayed_gholdengo_allows_singleton_inference(self):
        tactical = build_tactical_state(
            ["|start", "|switch|p2a: Gholdengo|Gholdengo, L80|100/100"],
            perspective_side="p1",
        )
        opponent = tactical["opponent"]
        belief = public_ability_belief(
            species_known=bool(opponent["active_displayed_species"]),
            possible_abilities=["Good as Gold"],
            displayed_species_uncertain=opponent["active_displayed_species_uncertain"],
        )
        self.assertEqual(belief.knownness, AbilityKnownness.INFERRED)
        self.assertEqual(belief.effective_ability.ability, "goodasgold")

    def test_ordinary_ambiguous_species_ability_does_not_collapse(self):
        tactical = build_tactical_state(
            ["|start", "|switch|p2a: Salamence|Salamence, L80|100/100"],
            perspective_side="p1",
        )
        opponent = tactical["opponent"]
        belief = public_ability_belief(
            species_known=bool(opponent["active_displayed_species"]),
            possible_abilities=["Intimidate", "Moxie"],
            displayed_species_uncertain=opponent["active_displayed_species_uncertain"],
        )
        self.assertEqual(belief.knownness, AbilityKnownness.UNKNOWN)
        self.assertIsNone(belief.effective_ability.ability)

    def test_species_singleton_ability_is_deterministic_public_inference(self):
        belief = public_ability_belief(species_known=True, possible_abilities=["Good as Gold"])
        self.assertEqual(belief.knownness, AbilityKnownness.INFERRED)
        self.assertEqual(belief.effective_ability.ability, "goodasgold")

    def test_possible_abilities_listed_without_selecting_truth(self):
        belief = public_ability_belief(
            species_known=True, possible_abilities=["Intimidate", "Sand Veil", "Moxie"]
        )
        self.assertEqual(set(belief.possible_abilities), {"intimidate", "sandveil", "moxie"})
        self.assertIsNone(belief.effective_ability.ability)
        self.assertEqual(belief.knownness, AbilityKnownness.UNKNOWN)

    def test_revealed_ability_becomes_known(self):
        belief = public_ability_belief(
            species_known=True, possible_abilities=["Intimidate", "Moxie"], revealed_ability="Moxie"
        )
        self.assertEqual(belief.knownness, AbilityKnownness.KNOWN)
        eff = belief.effective_ability
        self.assertEqual(eff.ability, "moxie")
        self.assertEqual(eff.knownness, AbilityKnownness.KNOWN)

    def test_inferred_ability_is_inferred_not_known(self):
        belief = public_ability_belief(
            species_known=True, possible_abilities=["Good as Gold"], inferred_ability="Good as Gold"
        )
        self.assertEqual(belief.knownness, AbilityKnownness.INFERRED)
        self.assertEqual(belief.effective_ability.knownness, AbilityKnownness.INFERRED)

    def test_singleton_does_not_collapse_under_illusion_uncertainty(self):
        belief = public_ability_belief(
            species_known=True,
            possible_abilities=["Good as Gold"],
            displayed_species_uncertain=True,
        )
        self.assertEqual(belief.knownness, AbilityKnownness.UNKNOWN)
        self.assertIsNone(belief.effective_ability.ability)

    def test_singleton_does_not_collapse_when_species_is_unknown(self):
        belief = public_ability_belief(species_known=False, possible_abilities=["Good as Gold"])
        self.assertEqual(belief.knownness, AbilityKnownness.UNKNOWN)
        self.assertIsNone(belief.effective_ability.ability)


class OwnSidePublicKnowledgeTest(unittest.TestCase):
    def test_own_side_request_facts_are_exact_known(self):
        own = own_side_public_knowledge(
            ability="Neutralizing Gas",
            item="Ability Shield",
            moves=["Sludge Bomb", "Will-O-Wisp"],
            tera_type="Dark",
        )
        self.assertEqual(own.ability_belief.knownness, AbilityKnownness.KNOWN)
        self.assertEqual(own.ability_belief.effective_ability.ability, "neutralizinggas")
        self.assertEqual(own.item_belief.state, ItemState.KNOWN)
        self.assertEqual(own.item_belief.revealed_item, "abilityshield")
        self.assertEqual(set(own.moves), {"sludgebomb", "willowisp"})
        self.assertEqual(own.tera_type, "dark")


class PublicItemBeliefTest(unittest.TestCase):
    def test_unknown_item_stays_unknown(self):
        belief = public_item_belief(possible_items=["Leftovers", "Heavy-Duty Boots"])
        self.assertEqual(belief.state, ItemState.UNKNOWN)
        self.assertIsNone(belief.has_active_item)

    def test_revealed_item_becomes_known(self):
        belief = public_item_belief(possible_items=["Leftovers"], revealed_item="Leftovers")
        self.assertEqual(belief.state, ItemState.KNOWN)
        self.assertTrue(belief.has_active_item)
        self.assertEqual(belief.revealed_item, "leftovers")

    def test_removed_item_has_no_active_item(self):
        belief = public_item_belief(possible_items=[], revealed_item="Leftovers", state=ItemState.REMOVED)
        self.assertFalse(belief.has_active_item)

    def test_consumed_item_has_no_active_item(self):
        belief = public_item_belief(possible_items=[], revealed_item="Sitrus Berry", state=ItemState.CONSUMED)
        self.assertFalse(belief.has_active_item)

    def test_showdown_reveal_makes_safety_goggles_known(self):
        belief = item_belief_from_public_evidence(
            ["Safety Goggles", "Leftovers"],
            candidate_item="Safety Goggles",
            evidence="showdown_reveal",
        )
        self.assertEqual(belief.state, ItemState.KNOWN)
        self.assertEqual(belief.revealed_item, "safetygoggles")

    def test_one_probabilistic_non_flinch_does_not_infer_covert_cloak(self):
        belief = item_belief_from_public_evidence(
            ["Covert Cloak", "Leftovers"],
            candidate_item="Covert Cloak",
            evidence="single_probabilistic_secondary_absence",
        )
        self.assertEqual(belief.state, ItemState.UNKNOWN)
        self.assertIsNone(belief.revealed_item)

    def test_deterministic_public_item_deduction_is_inferred_not_revealed(self):
        belief = item_belief_from_public_evidence(
            ["Safety Goggles", "Leftovers"],
            candidate_item="Safety Goggles",
            evidence="deterministic_public_deduction",
        )
        self.assertEqual(belief.state, ItemState.INFERRED)
        self.assertEqual(belief.revealed_item, "safetygoggles")


class PublicSpeedBeliefTest(unittest.TestCase):
    def test_range_does_not_leak_exact_speed(self):
        belief = speed_belief_range(180, 240)
        self.assertFalse(belief.is_exact)
        self.assertIsNone(belief.known_exact)
        self.assertEqual((belief.possible_speed_min, belief.possible_speed_max), (180, 240))

    def test_exact_only_when_publicly_provided(self):
        belief = speed_belief_exact(213)
        self.assertTrue(belief.is_exact)
        self.assertEqual(belief.known_exact, 213)

    def test_range_min_does_not_exceed_max(self):
        belief = speed_belief_range(250, 100)
        self.assertLessEqual(belief.possible_speed_min, belief.possible_speed_max)


class EffectiveAbilityContextTest(unittest.TestCase):
    def _known_gag(self):
        return public_ability_belief(True, ["Good as Gold"])

    def test_species_deterministic_good_as_gold_is_active(self):
        eff = EffectiveAbilityContext(belief=self._known_gag()).resolve()
        self.assertEqual(eff.ability, "goodasgold")
        self.assertEqual(eff.knownness, AbilityKnownness.INFERRED)
        self.assertTrue(eff.is_active)

    def test_neutralizing_gas_suppresses_known_ability(self):
        context = EffectiveAbilityContext(belief=self._known_gag(), neutralizing_gas_known=True)
        eff = context.resolve()
        self.assertTrue(eff.suppressed)
        self.assertFalse(eff.is_active)

    def test_ability_shield_prevents_suppression(self):
        context = EffectiveAbilityContext(
            belief=self._known_gag(), neutralizing_gas_known=True, ability_shield_known=True
        )
        eff = context.resolve()
        self.assertFalse(eff.suppressed)
        self.assertTrue(eff.is_active)

    def test_mold_breaker_bypass_ignores_known_ability(self):
        context = EffectiveAbilityContext(belief=self._known_gag(), source_ignores_abilities_known=True)
        eff = context.resolve()
        self.assertTrue(eff.ignored)
        self.assertFalse(eff.is_active)

    def test_gastro_acid_suppresses(self):
        context = EffectiveAbilityContext(belief=self._known_gag(), gastro_acid_known=True)
        self.assertTrue(context.resolve().suppressed)

    def test_unknown_ability_stays_unknown_even_under_suppression(self):
        # Suppressing an unknown ability does not turn it into a known ability.
        unknown = public_ability_belief(True, ["Magic Bounce", "Synchronize"])
        context = EffectiveAbilityContext(belief=unknown, neutralizing_gas_known=True)
        eff = context.resolve()
        self.assertEqual(eff.knownness, AbilityKnownness.UNKNOWN)
        self.assertIsNone(eff.ability)


class EffectiveItemContextTest(unittest.TestCase):
    def test_safety_goggles_blocks_when_known(self):
        context = EffectiveItemContext(
            belief=public_item_belief(["Safety Goggles"], revealed_item="Safety Goggles")
        )
        result = item_blocks(context, "Safety Goggles")
        self.assertTrue(result["available"])
        self.assertTrue(result["blocks"])

    def test_unknown_item_fails_closed(self):
        context = EffectiveItemContext(belief=public_item_belief(["Heavy-Duty Boots", "Leftovers"]))
        result = item_blocks(context, "Heavy-Duty Boots")
        self.assertFalse(result["available"])
        self.assertIsNone(result["blocks"])

    def test_known_other_item_does_not_block(self):
        context = EffectiveItemContext(belief=public_item_belief(["Leftovers"], revealed_item="Leftovers"))
        result = item_blocks(context, "Heavy-Duty Boots")
        self.assertTrue(result["available"])
        self.assertFalse(result["blocks"])

    def test_covert_cloak_blocks_secondary_when_known(self):
        context = EffectiveItemContext(
            belief=public_item_belief(["Covert Cloak"], revealed_item="Covert Cloak")
        )
        self.assertTrue(item_blocks(context, "Covert Cloak")["blocks"])

    def test_magic_room_suppresses_item_effect(self):
        context = EffectiveItemContext(
            belief=public_item_belief(["Heavy-Duty Boots"], revealed_item="Heavy-Duty Boots"),
            magic_room_known=True,
        )
        result = item_blocks(context, "Heavy-Duty Boots")
        self.assertTrue(result["available"])
        self.assertFalse(result["blocks"])

    def test_removed_item_does_not_block(self):
        context = EffectiveItemContext(
            belief=public_item_belief([], revealed_item="Heavy-Duty Boots", state=ItemState.REMOVED)
        )
        self.assertFalse(item_blocks(context, "Heavy-Duty Boots")["blocks"])


class EffectiveWeatherContextTest(unittest.TestCase):
    def test_weather_effects_active_without_negator(self):
        context = EffectiveWeatherContext(weather="Sandstorm")
        self.assertTrue(context.weather_effects_active)
        self.assertEqual(context.effective_weather(), "sandstorm")

    def test_cloud_nine_air_lock_suppresses_when_known(self):
        context = EffectiveWeatherContext(weather="Sandstorm", weather_negator_known=True)
        self.assertFalse(context.weather_effects_active)
        self.assertIsNone(context.effective_weather())

    def test_no_weather_means_no_effects(self):
        context = EffectiveWeatherContext(weather=None)
        self.assertFalse(context.weather_effects_active)
        self.assertIsNone(context.effective_weather())


class ItemBeliefFromStateTest(unittest.TestCase):
    def test_known_item_is_present(self):
        belief = item_belief_from_state({"item": "Safety Goggles", "item_known": True})
        self.assertEqual(belief.state, ItemState.KNOWN)
        self.assertTrue(belief.has_active_item)

    def test_unknown_item_stays_unknown(self):
        # Item present in state but not yet revealed: must not be treated as known.
        belief = item_belief_from_state({"item": "Safety Goggles"})
        self.assertEqual(belief.state, ItemState.UNKNOWN)
        self.assertIsNone(belief.has_active_item)

    def test_removed_item(self):
        belief = item_belief_from_state({"item": "Leftovers", "item_known": True, "item_removed": True})
        self.assertEqual(belief.state, ItemState.REMOVED)
        self.assertFalse(belief.has_active_item)


class MoldBreakerBypassTest(unittest.TestCase):
    def test_known_mold_breaker_source_ignores_abilities(self):
        self.assertTrue(source_ignores_target_abilities({"ability": "Mold Breaker", "ability_known": True}))
        self.assertTrue(source_ignores_target_abilities({"ability": "Teravolt", "ability_known": True}))

    def test_unknown_source_ability_is_not_assumed_to_bypass(self):
        self.assertFalse(source_ignores_target_abilities({"ability": "Mold Breaker"}))
        self.assertFalse(source_ignores_target_abilities({"ability": "Intimidate", "ability_known": True}))

    def test_mold_breaker_bypasses_known_good_as_gold(self):
        target = {"ability": "Good as Gold", "ability_known": True}
        attacker = {"ability": "Mold Breaker", "ability_known": True}
        result = resolve_status_move_ability_block(target, attacker, {"name": "Thunder Wave", "category": "Status"})
        self.assertFalse(result["prevented"])

    def test_ability_shield_protects_good_as_gold_from_mold_breaker(self):
        target = {"ability": "Good as Gold", "ability_known": True, "item": "Ability Shield", "item_known": True}
        attacker = {"ability": "Mold Breaker", "ability_known": True}
        result = resolve_status_move_ability_block(target, attacker, {"name": "Thunder Wave", "category": "Status"})
        self.assertTrue(result["prevented"])

    def test_unknown_ability_shield_does_not_protect(self):
        # Ability Shield present but unrevealed: not assumed, so bypass applies.
        target = {"ability": "Good as Gold", "ability_known": True, "item": "Ability Shield"}
        attacker = {"ability": "Mold Breaker", "ability_known": True}
        result = resolve_status_move_ability_block(target, attacker, {"name": "Thunder Wave", "category": "Status"})
        self.assertFalse(result["prevented"])


class SafetyGogglesPreventionTest(unittest.TestCase):
    def _powder_move(self):
        return {"name": "Spore", "category": "Status", "status": "slp", "powder": True}

    def test_known_safety_goggles_blocks_powder(self):
        state = {
            "attacker": {"types": ["Grass", "Poison"], "ability": "Effect Spore"},
            "target": {"types": ["Normal"], "ability": "Thick Fat", "item": "Safety Goggles", "item_known": True},
        }
        result = apply_immediate_prevention(state, self._powder_move())
        self.assertTrue(result["available"])
        self.assertTrue(result["prevented"])

    def test_unknown_item_does_not_block_powder(self):
        # Unrevealed item: Safety Goggles is not assumed, so the powder move is
        # not blocked by this path (no guess, no GAP).
        state = {
            "attacker": {"types": ["Grass", "Poison"], "ability": "Effect Spore"},
            "target": {"types": ["Normal"], "ability": "Thick Fat", "item": "Safety Goggles"},
        }
        result = apply_immediate_prevention(state, self._powder_move())
        self.assertTrue(result["available"])
        self.assertFalse(result["prevented"])

    def test_non_powder_move_is_unaffected(self):
        state = {
            "attacker": {"types": ["Normal"], "ability": "Thick Fat"},
            "target": {"types": ["Normal"], "ability": "Thick Fat", "item": "Safety Goggles", "item_known": True},
        }
        result = apply_immediate_prevention(state, {"name": "Tackle", "priority": 0})
        self.assertTrue(result["available"])
        self.assertFalse(result["prevented"])


class CloudNineWeatherSuppressionTest(unittest.TestCase):
    def _sand_state(self, **extra):
        return {
            "weather": "sandstorm",
            "combatants": {
                "p1": {"hp": 160, "max_hp": 320, "types": ["Water"], "residual_modifiers_known": True},
            },
            **extra,
        }

    def test_known_cloud_nine_suppresses_sandstorm_chip(self):
        result = apply_end_of_turn(self._sand_state(weather_negator_known=True))
        self.assertTrue(result["available"])
        self.assertEqual(result["state"]["combatants"]["p1"]["hp"], 160)  # no chip
        self.assertEqual(result["events"], [])

    def test_unknown_negator_does_not_suppress_chip(self):
        # No known negator: sandstorm chip applies (floor(320/16) = 20).
        result = apply_end_of_turn(self._sand_state())
        self.assertTrue(result["available"])
        self.assertEqual(result["state"]["combatants"]["p1"]["hp"], 140)


class NeutralizingGasSuppressionTest(unittest.TestCase):
    def test_known_neutralizing_gas_suppresses_target_ability(self):
        self.assertTrue(neutralizing_gas_suppresses_target({"ability": "Good as Gold", "ability_known": True}, True))

    def test_unknown_neutralizing_gas_does_not_suppress(self):
        self.assertFalse(neutralizing_gas_suppresses_target({"ability": "Good as Gold", "ability_known": True}, False))

    def test_ability_shield_protects_from_neutralizing_gas(self):
        target = {"ability": "Good as Gold", "ability_known": True, "item": "Ability Shield", "item_known": True}
        self.assertFalse(neutralizing_gas_suppresses_target(target, True))

    def test_own_neutralizing_gas_is_not_self_suppressed(self):
        target = {"ability": "Neutralizing Gas", "ability_known": True}
        self.assertFalse(neutralizing_gas_suppresses_target(target, True))

    def test_known_neutralizing_gas_unblocks_good_as_gold_status_move(self):
        state = {
            "attacker": {"ability": "Neutralizing Gas", "ability_known": True},
            "target": {"ability": "Good as Gold", "ability_known": True},
            "neutralizing_gas_known": True,
        }
        result = apply_immediate_prevention(state, {"name": "Will-O-Wisp", "category": "Status", "status": "brn"})
        self.assertTrue(result["available"])
        self.assertFalse(result["prevented"])

    def test_ability_shield_keeps_good_as_gold_under_neutralizing_gas(self):
        state = {
            "attacker": {"ability": "Neutralizing Gas", "ability_known": True},
            "target": {
                "ability": "Good as Gold",
                "ability_known": True,
                "item": "Ability Shield",
                "item_known": True,
            },
            "neutralizing_gas_known": True,
        }
        result = apply_immediate_prevention(state, {"name": "Will-O-Wisp", "category": "Status", "status": "brn"})
        self.assertTrue(result["available"])
        self.assertTrue(result["prevented"])


class SecondaryEffectBlockingTest(unittest.TestCase):
    def _flinch(self):
        return {"chance": 30, "volatileStatus": "flinch"}

    def test_known_covert_cloak_blocks_secondary(self):
        target = {"item": "Covert Cloak", "item_known": True}
        result = secondary_effect_blocked(target, {}, self._flinch())
        self.assertTrue(result["available"])
        self.assertTrue(result["blocked"])

    def test_known_shield_dust_blocks_secondary(self):
        target = {"ability": "Shield Dust", "ability_known": True}
        result = secondary_effect_blocked(target, {}, self._flinch())
        self.assertTrue(result["available"])
        self.assertTrue(result["blocked"])

    def test_mold_breaker_bypasses_shield_dust(self):
        target = {"ability": "Shield Dust", "ability_known": True}
        attacker = {"ability": "Mold Breaker", "ability_known": True}
        result = secondary_effect_blocked(target, attacker, self._flinch())
        # Both known: Shield Dust is breakable and bypassed, so the secondary
        # lands. We know this definitively (not fail-closed): blocked is False.
        self.assertTrue(result["available"])
        self.assertFalse(result["blocked"])

    def test_unknown_blocker_fails_closed(self):
        result = secondary_effect_blocked({}, {}, self._flinch())
        self.assertFalse(result["available"])
        self.assertIsNone(result["blocked"])

    def test_self_secondary_is_never_blocked(self):
        target = {"item": "Covert Cloak", "item_known": True}
        result = secondary_effect_blocked(target, {}, {"chance": 100, "self": {"boosts": {"spe": 1}}})
        self.assertTrue(result["available"])
        self.assertFalse(result["blocked"])


if __name__ == "__main__":
    unittest.main()
