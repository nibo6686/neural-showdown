import unittest
from pathlib import Path
from unittest.mock import patch

from neural.damage_engine import estimate_action_damage, estimate_damage
from neural.live_action_recommender import recommend_actions
from neural.live_private_features import FEATURE_DIM
from neural.sim_branch_evaluator import evaluate_actions

import numpy as np
import torch


class DamageEngineTest(unittest.TestCase):
    def test_direct_smogon_calc_reports_immunity(self):
        result = estimate_damage(
            attacker={"species": "Banette", "level": 80},
            defender={"species": "Kingambit", "level": 80, "hp_fraction": 1.0},
            move="Gunk Shot",
        )
        self.assertEqual(result["damage_method"], "smogon_calc")
        self.assertTrue(result["immune"])
        self.assertEqual(result["type_effectiveness"], 0.0)
        for key in ("average_percent", "min_percent", "max_percent", "ko_chance", "tera_damage_bonus"):
            self.assertIn(key, result)

    def test_direct_live_vivillon_quagsire_regressions(self):
        hurricane = estimate_damage(
            attacker={"species": "Vivillon-Ocean", "level": 80, "stats": {"atk": 100, "def": 100, "spa": 100, "spd": 100, "spe": 100}},
            defender={"species": "Quagsire", "level": 80, "hp_fraction": 1.0, "stats": {"atk": 100, "def": 100, "spa": 100, "spd": 100, "spe": 100}},
            move="Hurricane",
        )
        self.assertEqual(hurricane["damage_method"], "smogon_calc")
        self.assertFalse(any("smogon_calc_failed" in warning for warning in hurricane.get("warnings", [])))

        earthquake = estimate_damage(
            attacker={"species": "Quagsire", "level": 80, "stats": {"atk": 100, "def": 100, "spa": 100, "spd": 100, "spe": 100}},
            defender={"species": "Vivillon-Ocean", "level": 80, "hp_fraction": 1.0, "stats": {"atk": 100, "def": 100, "spa": 100, "spd": 100, "spe": 100}},
            move="Earthquake",
        )
        self.assertEqual(earthquake["damage_method"], "smogon_calc")
        self.assertTrue(earthquake["immune"])
        self.assertEqual(earthquake["type_effectiveness"], 0)
        self.assertEqual(earthquake["average_percent"], 0)

        tera_blast = estimate_damage(
            attacker={"species": "Vivillon-Ocean", "level": 80, "tera_type": "Flying", "stats": {"atk": 100, "def": 100, "spa": 100, "spd": 100, "spe": 100}},
            defender={"species": "Quagsire", "level": 80, "hp_fraction": 1.0, "stats": {"atk": 100, "def": 100, "spa": 100, "spd": 100, "spe": 100}},
            move="Tera Blast",
            use_tera=True,
        )
        self.assertEqual(tera_blast["damage_method"], "smogon_calc")
        self.assertFalse(any("smogon_calc_failed" in warning for warning in tera_blast.get("warnings", [])))

    def test_direct_status_moves_bypass_smogon_calc(self):
        cases = [
            ("Vivillon-Ocean", "Quagsire", "Sleep Powder"),
            ("Vivillon-Ocean", "Quagsire", "Quiver Dance"),
            ("Quagsire", "Vivillon-Ocean", "Toxic"),
            ("Quagsire", "Vivillon-Ocean", "Spikes"),
        ]
        for attacker, defender, move in cases:
            with self.subTest(move=move):
                result = estimate_damage(
                    attacker={"species": attacker, "level": 80},
                    defender={"species": defender, "level": 80, "hp_fraction": 1.0},
                    move=move,
                )
                self.assertEqual(result["damage_method"], "non_damaging_move")
                self.assertEqual(result["damage_rolls"], [])
                self.assertEqual(result["average_percent"], 0)
                self.assertFalse(result["immune"])
                self.assertIsNone(result["type_effectiveness"])
                self.assertFalse(any("smogon_calc_failed" in warning for warning in result.get("warnings", [])))

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

    def test_public_replay_approximate_gunk_shot_into_kingambit_is_immune(self):
        legal = [
            {"index": 0, "kind": "move", "label": "move:Gunk Shot", "choice": "Gunk Shot", "slot": 1, "move": "Gunk Shot"},
            {"index": 1, "kind": "move", "label": "move:Poltergeist", "choice": "Poltergeist", "slot": 2, "move": "Poltergeist"},
            {"index": 2, "kind": "move", "label": "move:Shadow Sneak", "choice": "Shadow Sneak", "slot": 3, "move": "Shadow Sneak"},
        ]
        trace = {
            "replay_id": "public-regression",
            "format": "gen9randombattle",
            "protocol_log": [
                "|turn|10",
                "|switch|p1a: Kingambit|Kingambit, L80|100/100",
                "|switch|p2a: Banette|Banette, L80|100/100",
            ],
            "turns": [
                {
                    "turn": 10,
                    "steps": [
                        {
                            "step_index": 0,
                            "turn": 10,
                            "player_side": "p2",
                            "view": {
                                "format": "gen9randombattle",
                                "gen": 9,
                                "turn": 10,
                                "player": "p2",
                                "opponent": "p1",
                                "active": {"self": 0, "opponent": 0},
                                "self_team": [{"species": "Banette", "details": "Banette, L80", "active": True, "hp_fraction": 1.0}],
                                "opponent_team": [{"species": "Kingambit", "details": "Kingambit, L80", "types": ["Dark", "Steel"], "active": True, "hp_fraction": 1.0}],
                            },
                            "request": {
                                "player": "p2",
                                "side": {
                                    "id": "p2",
                                    "pokemon": [{"ident": "p2a: Banette", "details": "Banette, L80", "condition": "100/100", "active": True, "moves": ["Gunk Shot", "Poltergeist", "Shadow Sneak"]}],
                                },
                                "active": [
                                    {
                                        "moves": [
                                            {"move": "Gunk Shot", "id": "gunkshot", "pp": 1, "maxpp": 1, "disabled": False},
                                            {"move": "Poltergeist", "id": "poltergeist", "pp": 1, "maxpp": 1, "disabled": False},
                                            {"move": "Shadow Sneak", "id": "shadowsneak", "pp": 1, "maxpp": 1, "disabled": False},
                                        ]
                                    }
                                ],
                                "legal_actions": {"actions": legal},
                            },
                        }
                    ],
                }
            ],
        }
        results = evaluate_actions({"trace": trace}, "p2", legal, rollout_config={"rollout_mode": "approximate", "rollouts_per_action": 8})
        by_label = {row["label"]: row for row in results}
        gunk = by_label["move:Gunk Shot"]
        self.assertEqual(gunk["damage_method"], "smogon_calc")
        self.assertTrue(gunk["immune"])
        self.assertEqual(gunk["type_effectiveness"], 0.0)
        self.assertLess(gunk["final_score"], by_label["move:Shadow Sneak"]["final_score"])

    def test_live_recommender_public_step_uses_smogon_damage(self):
        request = {
            "side": {
                "id": "p2",
                "pokemon": [
                    {
                        "ident": "p2a: Banette",
                        "details": "Banette, L80",
                        "condition": "100/100",
                        "active": True,
                        "moves": ["Gunk Shot", "Poltergeist", "Shadow Sneak"],
                    }
                ],
            },
            "active": [
                {
                    "moves": [
                        {"move": "Gunk Shot", "id": "gunkshot", "pp": 1, "maxpp": 1, "disabled": False},
                        {"move": "Poltergeist", "id": "poltergeist", "pp": 1, "maxpp": 1, "disabled": False},
                        {"move": "Shadow Sneak", "id": "shadowsneak", "pp": 1, "maxpp": 1, "disabled": False},
                    ]
                }
            ],
        }
        payload = type("Payload", (), {"request": request, "legal_actions": []})()
        private_state = {
            "player_side": "p2",
            "active_species": "Banette",
            "team": [{"species": "Banette", "level": 80, "active": True, "hp_fraction": 1.0}],
            "active_moves": [{"name": "Gunk Shot"}, {"name": "Poltergeist"}, {"name": "Shadow Sneak"}],
        }
        trajectory = {
            "replay_id": "live-public-regression",
            "format": "gen9randombattle",
            "protocol_log": [
                "|turn|10",
                "|switch|p1a: Kingambit|Kingambit, L80|100/100",
                "|switch|p2a: Banette|Banette, L80|100/100",
            ],
            "turns": [{"turn": 10, "events": []}],
        }
        with patch("neural.live_action_recommender.DEFAULT_ACTION_RANKER_PATH", Path("missing-action-ranker.pt")), patch(
            "neural.live_action_recommender.DEFAULT_ACTION_VALUE_RANKER_V2_PATH", Path("missing-action-value-ranker.pt")
        ):
            report = recommend_actions(
                payload=payload,
                private_state=private_state,
                opponent_belief={"opponents": []},
                trajectory=trajectory,
                public_features=np.zeros(31, dtype=np.float32),
                live_features=np.zeros(FEATURE_DIM, dtype=np.float32),
                current_value=0.0,
                value_model=None,
                value_metadata={},
                policy_loader=lambda: (None, {"warning": "missing"}),
                device=torch.device("cpu"),
                limit=3,
            )
        by_label = {row["label"]: row for row in report["all_action_estimates"]}
        gunk = by_label["move: Gunk Shot"]
        self.assertEqual(gunk["damage_method"], "smogon_calc")
        self.assertTrue(gunk["immune"])
        self.assertEqual(gunk["type_effectiveness"], 0.0)
        self.assertTrue(
            any(
                gunk["final_score"] < by_label[label]["final_score"]
                for label in ("move: Poltergeist", "move: Shadow Sneak")
            )
        )


if __name__ == "__main__":
    unittest.main()
