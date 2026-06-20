"""Public-information belief + effective-context no-leakage tests.

These guard the rule that the model receives the same *category* of information
a skilled Showdown player has (known species, possible abilities/items, speed
ranges, revealed/inferred public info) but never the hidden truth before it is
revealed. Pure-Python, torch-free; no materialization, training, or live change.
"""

import unittest

from neural.provenance_contracts import (
    AbilityKnownness,
    EffectiveAbilityContext,
    EffectiveItemContext,
    EffectiveWeatherContext,
    ItemState,
    item_blocks,
    public_ability_belief,
    public_item_belief,
    speed_belief_exact,
    speed_belief_range,
)


class PublicAbilityBeliefTest(unittest.TestCase):
    def test_unrevealed_ability_stays_unknown_not_species_default(self):
        # Gholdengo's only ability is Good as Gold, but until it is revealed the
        # belief must not treat it as known.
        belief = public_ability_belief(species_known=True, possible_abilities=["Good as Gold"])
        self.assertEqual(belief.knownness, AbilityKnownness.UNKNOWN)
        self.assertIsNone(belief.effective_ability.ability)

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
        return public_ability_belief(True, ["Good as Gold"], revealed_ability="Good as Gold")

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
        unknown = public_ability_belief(True, ["Good as Gold"])
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


if __name__ == "__main__":
    unittest.main()
