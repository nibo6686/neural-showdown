import unittest
from unittest.mock import patch

from neural import agent_audit
from neural.agent_audit import SPECS, _learned_choice, _summary


class AgentAuditTest(unittest.TestCase):
    def test_ablation_specs_keep_rollout_agents_explicit(self):
        self.assertEqual(SPECS["action_value_ranker"].rollout_mode, "off")
        self.assertEqual(SPECS["rollout"].rollout_mode, "approximate")
        self.assertEqual(SPECS["default"].rollout_weight, 0.75)

    def test_summary_counts_results_and_fallbacks(self):
        rows = [
            {
                "result": "win",
                "turns": 10,
                "avg_decision_latency_ms": 4.0,
                "decision_latencies_ms": [3.0, 5.0],
                "fallback_count": 0,
                "damage_fallback_count": 0,
                "damage_call_count": 4,
                "smogon_calc_count": 4,
                "heuristic_fallback_call_count": 0,
                "damage_fallback_reasons": {},
                "rollout_unavailable_count": 0,
                "rollout_timeout_count": 0,
                "methods": {"action_value_ranker": 3},
            },
            {
                "result": "loss",
                "turns": 20,
                "avg_decision_latency_ms": 6.0,
                "decision_latencies_ms": [4.0, 8.0],
                "fallback_count": 1,
                "damage_fallback_count": 2,
                "damage_call_count": 6,
                "smogon_calc_count": 4,
                "heuristic_fallback_call_count": 2,
                "damage_fallback_reasons": {"damage_rpc_failed:RuntimeError:offline": 2},
                "rollout_unavailable_count": 1,
                "rollout_timeout_count": 1,
                "methods": {"action_value_ranker": 4},
            },
        ]
        result = _summary("action_value_ranker", rows, wall_time_sec=2.0, workers=2)
        self.assertEqual(result["wins"], 1)
        self.assertEqual(result["losses"], 1)
        self.assertEqual(result["winrate"], 0.5)
        self.assertEqual(result["fallbacks"], 1)
        self.assertEqual(result["damage_fallbacks"], 2)
        self.assertEqual(result["total_damage_calls"], 10)
        self.assertEqual(result["smogon_calc_calls"], 8)
        self.assertEqual(result["heuristic_fallback_calls"], 2)
        self.assertEqual(result["damage_fallback_rate"], 0.2)
        self.assertEqual(result["rollout_timeout_count"], 1)
        self.assertGreater(result["p95_decision_latency_ms"], result["avg_decision_latency_ms"])
        self.assertEqual(
            result["top_damage_fallback_reasons"]["damage_rpc_failed:RuntimeError:offline"],
            2,
        )
        self.assertEqual(result["method_counts"]["action_value_ranker"], 7)

    def test_autonomous_rollout_counts_clean_damage_calls(self):
        report = {
            "action_recommendation_method": "approx_sim_rollout",
            "debug": {
                "all_action_estimates": [
                    {
                        "index": 0,
                        "expected_value": 0.5,
                        "damage_method": "smogon_calc",
                        "fallback_reason": None,
                    },
                    {
                        "index": 1,
                        "expected_value": 0.1,
                        "damage_method": "non_damaging_move",
                        "fallback_reason": None,
                    },
                    {
                        "index": 8,
                        "expected_value": 0.0,
                        "damage_method": "not_applicable_switch",
                        "fallback_reason": None,
                    },
                ]
            },
        }
        request = {
            "legal_actions": {
                "actions": [
                    {"index": 0, "choice": "move 1"},
                    {"index": 1, "choice": "move 2"},
                    {"index": 8, "choice": "switch 2"},
                ]
            }
        }
        with patch.object(agent_audit, "evaluate_with_model", return_value=report):
            _, debug = _learned_choice(SPECS["rollout"], "env", "p1", request, [])
        self.assertEqual(debug["damage_calls"], 2)
        self.assertEqual(debug["smogon_calc_calls"], 1)
        self.assertEqual(debug["heuristic_fallback_calls"], 0)
        self.assertFalse(debug["damage_fallback"])
        self.assertEqual(debug["damage_fallback_reasons"], {})


if __name__ == "__main__":
    unittest.main()
