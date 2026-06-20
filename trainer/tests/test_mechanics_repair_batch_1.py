"""Mechanics repair batch 1: fixed-damage, multi-hit and dynamic accuracy.

Diagnostic-only. Asserts that `resolve_action_impact`:
  * routes level-based fixed-damage moves (Night Shade / Seismic Toss) to the
    oracle and reports exact non-zero damage instead of "0 damage";
  * leaves an ordinary damaging move unaffected;
  * fails closed (impact_unknown) for target-HP / counter fixed-damage moves and
    for multi-hit moves rather than emitting a wrong-exact value;
  * reflects weather in the hit chance of weather-dependent-accuracy moves, and
    fails closed on accuracy when the weather context is unsupported.

No live defaults, schema names, or dims change here.
"""

import unittest

from neural.action_features import (
    ACTION_FEATURE_NAMES_V6,
    build_action_feature_vector_v6,
)
from neural.resolved_action_impact import resolve_action_impact
from neural.resolved_action_impact_diagnostic import _action, _approx

_ANNIHILAPE = {"species": "Annihilape", "level": 80, "types": ["Fighting", "Ghost"]}
_CRESSELIA = {"species": "Cresselia", "level": 80, "hp_fraction": 1.0, "types": ["Psychic"]}


def _impact(move, attacker=_ANNIHILAPE, defender=_CRESSELIA, **action_extra):
    action = _action(move, **action_extra)
    return resolve_action_impact(action, _approx(attacker, defender))


def _approx_weather(weather, attacker=_ANNIHILAPE, defender=_CRESSELIA):
    return {
        "private_state": {"team": [{**attacker, "active": True}]},
        "view": {"opponent_team": [defender]},
        "tactical_state": {
            "weather": weather,
            "own": {"active_current_types": list(attacker.get("types") or [])},
        },
    }


def _v6_idx(name):
    return ACTION_FEATURE_NAMES_V6.index(name)


class FixedDamageTest(unittest.TestCase):
    def test_level_based_fixed_damage_routes_to_oracle(self):
        for move in ("Night Shade", "Seismic Toss"):
            impact = _impact(move)
            self.assertTrue(impact["available"], move)
            self.assertEqual(impact["method"], "smogon_calc", move)
            self.assertFalse(impact["non_damaging"], move)
            self.assertGreater(impact["expected_fraction"], 0.0, move)

    def test_ordinary_damaging_move_unaffected(self):
        # Close Combat (Fighting STAB) damages Cresselia; an ordinary move must
        # not be touched by the fixed-damage / multi-hit / accuracy repairs.
        impact = _impact("Close Combat")
        self.assertTrue(impact["available"])
        self.assertEqual(impact["method"], "smogon_calc")
        self.assertFalse(impact["immune"])
        self.assertGreater(impact["expected_fraction"], 0.0)

    def test_target_hp_fixed_damage_fails_closed(self):
        for move in ("Super Fang", "Ruination", "Endeavor"):
            impact = _impact(move)
            self.assertFalse(impact["available"], move)
            self.assertEqual(impact["method"], "unavailable", move)
            self.assertEqual(impact["fallback_reason"], "fixed_damage_target_context_unresolved", move)
            self.assertEqual(impact["dynamic_dependency"], "target_hp", move)

    def test_counter_fixed_damage_fails_closed(self):
        impact = _impact("Mirror Coat")
        self.assertFalse(impact["available"])
        self.assertEqual(impact["dynamic_dependency"], "damage_taken")

    def test_fail_closed_fixed_damage_sets_impact_unknown(self):
        action = _action("Super Fang")
        impact = resolve_action_impact(action, _approx(_ANNIHILAPE, _CRESSELIA))
        vec = build_action_feature_vector_v6(action, {"team": [{**_ANNIHILAPE, "active": True}]}, {}, impact)
        self.assertEqual(vec[_v6_idx("impact_unknown")], 1.0)
        self.assertEqual(vec[_v6_idx("impact_method_unavailable")], 1.0)


class MultiHitTest(unittest.TestCase):
    def test_multi_hit_moves_fail_closed(self):
        for move in ("Bullet Seed", "Rock Blast", "Surging Strikes", "Population Bomb"):
            impact = _impact(move)
            self.assertFalse(impact["available"], move)
            self.assertEqual(impact["fallback_reason"], "multihit_total_unrepresented", move)
            self.assertEqual(impact["dynamic_dependency"], "multihit", move)

    def test_multi_hit_sets_impact_unknown_in_vector(self):
        action = _action("Bullet Seed")
        impact = resolve_action_impact(action, _approx(_ANNIHILAPE, _CRESSELIA))
        vec = build_action_feature_vector_v6(action, {"team": [{**_ANNIHILAPE, "active": True}]}, {}, impact)
        self.assertEqual(vec[_v6_idx("impact_unknown")], 1.0)


class DynamicAccuracyTest(unittest.TestCase):
    def test_blizzard_perfect_in_snow_else_base(self):
        snow = resolve_action_impact(_action("Blizzard"), _approx_weather("snow"))
        clear = resolve_action_impact(_action("Blizzard"), _approx_weather(None))
        self.assertEqual(snow["hit_chance"], 1.0)
        self.assertTrue(snow["accuracy_known"])
        self.assertAlmostEqual(clear["hit_chance"], 0.70, places=2)
        self.assertTrue(clear["accuracy_known"])
        # A low-accuracy move in clear weather is not as reliable as in snow.
        self.assertLess(clear["hit_chance"], snow["hit_chance"])
        # Damage path is otherwise intact.
        self.assertTrue(snow["available"])

    def test_thunder_rain_and_sun(self):
        rain = resolve_action_impact(_action("Thunder"), _approx_weather("RainDance"))
        sun = resolve_action_impact(_action("Thunder"), _approx_weather("SunnyDay"))
        self.assertEqual(rain["hit_chance"], 1.0)
        self.assertEqual(sun["hit_chance"], 0.5)
        self.assertTrue(rain["accuracy_known"] and sun["accuracy_known"])

    def test_unsupported_weather_context_fails_closed_on_accuracy(self):
        # No tactical_state -> weather provenance unavailable -> accuracy not exact.
        approx = {
            "private_state": {"team": [{**_ANNIHILAPE, "active": True}]},
            "view": {"opponent_team": [_CRESSELIA]},
        }
        impact = resolve_action_impact(_action("Blizzard"), approx)
        self.assertFalse(impact["accuracy_known"])


if __name__ == "__main__":
    unittest.main()
