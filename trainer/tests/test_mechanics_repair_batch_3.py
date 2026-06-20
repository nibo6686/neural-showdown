"""Mechanics repair batch 3: dynamic type/STAB and charge/delay timing.

Diagnostic-only. Asserts that:
  * dynamic-type moves resolve their type from state, so impact type-effectiveness
    and STAB reflect the actual type (Weather Ball in snow vs none);
  * an ordinary move is unaffected;
  * two-turn charge / delayed moves fail closed unless they fire this turn
    (sun / Power Herb), and Future Sight always fails closed;
  * Beak Blast (same-turn damage) and Tera Starstorm (Stellar) behave per spec.

No schema name/order/dim changes here; v6 remains 331D.
"""

import unittest

from neural.resolved_action_impact import resolve_action_impact
from neural.resolved_action_impact_diagnostic import _action

_DRAGONITE = {"species": "Dragonite", "level": 80, "hp_fraction": 1.0, "types": ["Dragon", "Flying"]}


def _approx(attacker, defender=_DRAGONITE, *, weather=None):
    return {
        "private_state": {"team": [{**attacker, "active": True}]},
        "view": {"opponent_team": [defender]},
        "tactical_state": {
            "weather": weather,
            "own": {"active_current_types": list(attacker.get("types") or [])},
        },
    }


def _impact(move, attacker, **kw):
    return resolve_action_impact(_action(move), _approx(attacker, **kw))


_CASTFORM = {"species": "Castform", "level": 80, "types": ["Normal"]}


class DynamicTypeTest(unittest.TestCase):
    def test_weather_ball_type_effectiveness_is_dynamic(self):
        # Ice (snow) is 4x on Dragon/Flying; Normal (clear) is 1x.
        snow = _impact("Weather Ball", _CASTFORM, weather="Snow")
        clear = _impact("Weather Ball", _CASTFORM, weather=None)
        self.assertTrue(snow["super_effective"])
        self.assertEqual(snow["type_effectiveness"], 4.0)
        self.assertFalse(clear["super_effective"])
        self.assertEqual(clear["type_effectiveness"], 1.0)

    def test_weather_ball_stab_uses_resolved_type(self):
        # Castform is Normal: STAB on the Normal (clear) Weather Ball, not the Ice one.
        self.assertTrue(_impact("Weather Ball", _CASTFORM, weather=None)["stab"])
        self.assertFalse(_impact("Weather Ball", _CASTFORM, weather="Snow")["stab"])

    def test_revelation_dance_stab_from_user_primary_type(self):
        primarina = {"species": "Primarina", "level": 80, "types": ["Water", "Fairy"]}
        impact = _impact("Revelation Dance", primarina)
        self.assertTrue(impact["available"])
        self.assertTrue(impact["stab"])  # resolved Water in user types

    def test_tera_starstorm_fails_closed_on_stellar(self):
        terapagos = {"species": "Terapagos-Stellar", "level": 80, "types": ["Normal"]}
        impact = _impact("Tera Starstorm", terapagos)
        self.assertFalse(impact["available"])
        self.assertEqual(impact["dynamic_dependency"], "stellar_type")

    def test_ordinary_move_unaffected(self):
        impact = _impact("Surf", {"species": "Blastoise", "level": 80, "types": ["Water"]})
        self.assertTrue(impact["available"])
        self.assertEqual(impact["method"], "smogon_calc")
        self.assertEqual(impact["type_effectiveness"], 0.5)  # Water vs Dragon/Flying
        self.assertTrue(impact["stab"])


class ChargeDelayTest(unittest.TestCase):
    _VENUSAUR = {"species": "Venusaur", "level": 80, "types": ["Grass", "Poison"]}
    _GLIMMORA = {"species": "Glimmora", "level": 80, "types": ["Rock", "Poison"]}

    def test_solar_beam_fails_closed_without_sun_or_herb(self):
        impact = _impact("Solar Beam", self._VENUSAUR)
        self.assertFalse(impact["available"])
        self.assertEqual(impact["fallback_reason"], "two_turn_charge_delayed_damage")
        self.assertEqual(impact["dynamic_dependency"], "charge_timing")

    def test_solar_beam_immediate_in_sun(self):
        impact = _impact("Solar Beam", self._VENUSAUR, weather="SunnyDay")
        self.assertTrue(impact["available"])
        self.assertEqual(impact["method"], "smogon_calc")

    def test_solar_beam_immediate_with_power_herb(self):
        herbed = {**self._VENUSAUR, "item": "Power Herb"}
        self.assertTrue(_impact("Solar Beam", herbed)["available"])

    def test_meteor_beam_needs_power_herb(self):
        self.assertFalse(_impact("Meteor Beam", self._GLIMMORA)["available"])
        herbed = {**self._GLIMMORA, "item": "Power Herb"}
        self.assertTrue(_impact("Meteor Beam", herbed)["available"])

    def test_future_sight_always_fails_closed(self):
        slowking = {"species": "Slowking", "level": 80, "types": ["Water", "Psychic"]}
        for kw in ({}, {"weather": "SunnyDay"}):
            impact = resolve_action_impact(_action("Future Sight"), _approx(slowking, **kw))
            self.assertFalse(impact["available"], kw)
        herbed = {"species": "Slowking", "level": 80, "types": ["Water", "Psychic"], "item": "Power Herb"}
        self.assertFalse(_impact("Future Sight", herbed)["available"])

    def test_beak_blast_same_turn_damage_is_available(self):
        blaziken = {"species": "Blaziken", "level": 80, "types": ["Fire", "Fighting"]}
        impact = _impact("Beak Blast", blaziken)
        self.assertTrue(impact["available"])
        self.assertEqual(impact["method"], "smogon_calc")
        self.assertGreater(impact["expected_fraction"], 0.0)


if __name__ == "__main__":
    unittest.main()
