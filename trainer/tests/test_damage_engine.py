import unittest

from neural.damage_engine import estimate_action_damage


class DamageEngineTest(unittest.TestCase):
    def test_fallback_reports_required_fields_and_immunity(self):
        result = estimate_action_damage(
            action={"kind": "move", "move": "Gunk Shot", "label": "move: Gunk Shot"},
            approx_state={
                "private_state": {"team": [{"species": "Banette", "active": True}]},
                "view": {"opponent_team": [{"species": "Kingambit", "types": ["Dark", "Steel"], "hp_fraction": 1.0}]},
            },
        )
        self.assertEqual(result["damage_method"], "heuristic_fallback")
        self.assertTrue(result["immune"])
        self.assertEqual(result["type_effectiveness"], 0.0)
        for key in ("average_percent", "min_percent", "max_percent", "ko_chance", "tera_damage_bonus"):
            self.assertIn(key, result)

    def test_rpc_result_is_used_when_available(self):
        class FakeClient:
            def damage_estimate(self, request):
                return {
                    "damage_method": "smogon_calc",
                    "average_percent": 42.0,
                    "min_percent": 35.0,
                    "max_percent": 49.0,
                    "ko_chance": 0.5,
                    "immune": False,
                    "type_effectiveness": 2.0,
                    "tera_damage_bonus": 0.0,
                }

        result = estimate_action_damage(
            action={"kind": "move", "move": "Thunderbolt", "label": "move: Thunderbolt"},
            approx_state={
                "private_state": {"team": [{"species": "Pikachu", "active": True}]},
                "view": {"opponent_team": [{"species": "Charizard", "types": ["Fire", "Flying"], "hp_fraction": 0.5}]},
            },
            client=FakeClient(),
        )
        self.assertEqual(result["damage_method"], "smogon_calc")
        self.assertEqual(result["average_percent"], 42.0)

    def test_fallback_survives_rpc_failure(self):
        class BrokenClient:
            def damage_estimate(self, request):
                raise RuntimeError("offline")

        result = estimate_action_damage(
            action={"kind": "move", "move": "Thunderbolt", "label": "move: Thunderbolt"},
            approx_state={
                "private_state": {"team": [{"species": "Pikachu", "active": True}]},
                "view": {"opponent_team": [{"species": "Charizard", "types": ["Fire", "Flying"], "hp_fraction": 0.5}]},
            },
            client=BrokenClient(),
        )
        self.assertEqual(result["damage_method"], "heuristic_fallback")
        self.assertTrue(any("damage_rpc_failed" in warning for warning in result["warnings"]))


if __name__ == "__main__":
    unittest.main()
