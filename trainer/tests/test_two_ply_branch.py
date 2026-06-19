import json
import os
import unittest
from typing import Any, Dict, List, Mapping

from neural.env_client import SimCoreClient
from neural.one_turn_branch import make_material_score_fn
from neural.two_ply_branch import (
    TwoPlyConfig,
    _score_result,
    aggregate_belief_particle_reports,
    evaluate_belief_particle_branches,
    evaluate_two_ply_branches,
)


RESULT_OPTIONS = {
    "view_players": ["p1", "p2"],
    "include_log_delta": True,
    "include_possible_roles": False,
}
SEED = [101, 202, 303, 404]


class TwoPlyBranchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        command_json = os.environ.get("NEURAL_SIM_CORE_COMMAND_JSON")
        cwd = os.environ.get("NEURAL_SIM_CORE_CWD")
        if not command_json or not cwd:
            raise unittest.SkipTest("sim-core process environment is not configured")
        cls.client = SimCoreClient(json.loads(command_json), cwd)
        cls.turns = cls._play_battle()

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "client"):
            cls.client.close()

    @classmethod
    def _play_battle(cls):
        env_id = cls.client.create_env(
            "gen9randombattle",
            SEED,
            {"p1": {"controller": "external"}, "p2": {"controller": "external"}},
            timeout_sec=30,
        )
        result = cls.client.reset(env_id, RESULT_OPTIONS, timeout_sec=60)
        history: List[Dict[str, str]] = []
        turns: List[Dict[str, Any]] = []
        try:
            while not result.get("terminated"):
                requests = result.get("requests") or {}
                turns.append(
                    {
                        "history": [dict(row) for row in history],
                        "requests": {
                            side: dict(request) if isinstance(request, dict) else request
                            for side, request in requests.items()
                        },
                    }
                )
                choices: Dict[str, str] = {}
                for side in ("p1", "p2"):
                    request = requests.get(side)
                    if isinstance(request, Mapping) and request.get("legal_actions"):
                        decision = cls.client.agent_action(env_id, side, "heuristic", timeout_sec=20)
                        choices[side] = str(decision.get("choice") or "default")
                if not choices:
                    break
                result = cls.client.step(env_id, choices, RESULT_OPTIONS, timeout_sec=60)
                history.append(dict(choices))
        finally:
            cls.client.close_env(env_id, timeout_sec=10)
        return turns

    def _actionable_turn(self, side="p1", forced=None):
        for turn in self.turns:
            request = turn["requests"].get(side)
            if not isinstance(request, Mapping) or not request.get("legal_actions"):
                continue
            if forced is not None and bool(request.get("force_switch")) != forced:
                continue
            return turn
        self.skipTest(f"no matching {side} turn")

    def _evaluate(self, turn, side="p1", **kwargs):
        opponent = "p2" if side == "p1" else "p1"
        defaults = {
            "max_root_actions": 1,
            "max_opponent_actions": 1,
            "max_followup_actions": 1,
            "max_decision_time_sec": 30.0,
        }
        defaults.update(kwargs)
        return evaluate_two_ply_branches(
            client=self.client,
            seed=SEED,
            history=turn["history"],
            player_side=side,
            player_request=turn["requests"][side],
            opponent_request=turn["requests"].get(opponent),
            score_fn=make_material_score_fn(),
            config=TwoPlyConfig(**defaults),
        )

    def test_does_not_mutate_original_environment(self):
        live_env = self.client.create_env(
            "gen9randombattle",
            SEED,
            {"p1": {"controller": "external"}, "p2": {"controller": "external"}},
            timeout_sec=30,
        )
        try:
            before = self.client.reset(live_env, RESULT_OPTIONS, timeout_sec=60)
            open_before = len(self.client._open_envs)
            report = self._evaluate({"history": [], "requests": before["requests"]})
            self.assertGreater(report["branch_count"], 0)
            choices = {}
            for side in ("p1", "p2"):
                decision = self.client.agent_action(live_env, side, "heuristic", timeout_sec=20)
                choices[side] = decision["choice"]
            after = self.client.step(live_env, choices, RESULT_OPTIONS, timeout_sec=60)
            self.assertGreaterEqual(int(after["info"]["turn"]), int(before["info"]["turn"]))
            self.assertEqual(len(self.client._open_envs), open_before)
        finally:
            self.client.close_env(live_env, timeout_sec=10)

    def test_same_seed_state_actions_are_deterministic(self):
        turn = self._actionable_turn(forced=False)
        first = self._evaluate(turn)
        second = self._evaluate(turn)
        projection = lambda report: [
            (
                row["index"],
                row["mean_score"],
                row["worst_score"],
                row["best_score"],
                row["leaf_count"],
            )
            for row in report["actions"]
        ]
        self.assertEqual(projection(first), projection(second))
        self.assertEqual(first["branch_count"], second["branch_count"])
        self.assertEqual(first["leaf_count"], second["leaf_count"])

    def test_branch_count_is_bounded(self):
        turn = self._actionable_turn(forced=False)
        report = self._evaluate(
            turn,
            max_root_actions=2,
            max_opponent_actions=1,
            max_followup_actions=2,
        )
        self.assertLessEqual(report["branch_count"], 2 * 1 * (1 + 2))
        self.assertLessEqual(report["leaf_count"], 2 * 1 * 2)

    def test_illegal_action_subset_is_ignored_cleanly(self):
        turn = self._actionable_turn(forced=False)
        opponent = "p2"
        report = evaluate_two_ply_branches(
            client=self.client,
            seed=SEED,
            history=turn["history"],
            player_side="p1",
            player_request=turn["requests"]["p1"],
            opponent_request=turn["requests"].get(opponent),
            score_fn=make_material_score_fn(),
            config=TwoPlyConfig(max_root_actions=2, max_opponent_actions=1, max_followup_actions=1),
            legal_action_indices=[999],
        )
        self.assertEqual(report["actions"], [])
        self.assertEqual(report["selected"], None)

    def test_forced_switch_is_explicit_one_turn_fallback(self):
        for side in ("p1", "p2"):
            try:
                turn = self._actionable_turn(side=side, forced=True)
            except unittest.SkipTest:
                continue
            report = self._evaluate(turn, side=side)
            self.assertTrue(report["fallback_to_one_turn"])
            self.assertEqual(report["unsupported_reason"], "root_forced_switch")
            return
        self.skipTest("no forced-switch state found")

    def test_no_heuristic_damage_fallback(self):
        turn = self._actionable_turn(forced=False)
        report = self._evaluate(turn)
        self.assertEqual(report["damage_fallbacks"], 0)
        self.assertNotIn("heuristic_fallback", json.dumps(report))

    def test_three_particle_belief_reports_counts_and_safeguards(self):
        source = self.client.create_env(
            "gen9randombattle",
            SEED,
            {"p1": {"controller": "external"}, "p2": {"controller": "external"}},
            timeout_sec=30,
        )
        try:
            result = self.client.reset(source, RESULT_OPTIONS, timeout_sec=60)
            report = evaluate_belief_particle_branches(
                client=self.client,
                seed=SEED,
                history=[],
                player_side="p1",
                player_request=result["requests"]["p1"],
                score_fn=make_material_score_fn(),
                config=TwoPlyConfig(
                    max_root_actions=1,
                    max_opponent_actions=1,
                    max_followup_actions=1,
                    max_decision_time_sec=30,
                    belief_mode=True,
                ),
                source_env_id=source,
                base_belief_seed=[9, 8, 7, 6],
                particle_count=3,
            )
            self.assertEqual(report["particle_count"], 3)
            self.assertEqual(report["completed_particle_count"], 3)
            self.assertEqual(report["belief_samples"], 3)
            self.assertEqual(report["belief_sample_errors"], 0)
            self.assertEqual(report["belief_constraint_violations"], 0)
            self.assertEqual(report["damage_fallbacks"], 0)
            self.assertIsNotNone(report["selected"])
            self.assertEqual(report["selected"]["particle_count"], 3)
            single = evaluate_two_ply_branches(
                client=self.client,
                seed=SEED,
                history=[],
                player_side="p1",
                player_request=result["requests"]["p1"],
                opponent_request=None,
                score_fn=make_material_score_fn(),
                config=TwoPlyConfig(
                    max_root_actions=1,
                    max_opponent_actions=1,
                    max_followup_actions=1,
                    max_decision_time_sec=30,
                    belief_mode=True,
                ),
                source_env_id=source,
                belief_seed=[9, 8, 7, 6],
            )
            self.assertEqual(single["search"], "two_ply_belief")
            self.assertEqual(single["belief_samples"], 1)
            self.assertEqual(single["belief_constraint_violations"], 0)
        finally:
            self.client.close_env(source, timeout_sec=10)


class TwoPlyTerminalScoreTest(unittest.TestCase):
    def test_particle_aggregation_is_deterministic(self):
        reports = [
            {
                "actions": [
                    {"index": 0, "choice": "move 1", "label": "A", "kind": "move", "mean_score": score_a},
                    {"index": 1, "choice": "move 2", "label": "B", "kind": "move", "mean_score": score_b},
                ],
                "selected": {"index": selected},
            }
            for score_a, score_b, selected in [(0.2, 0.1, 0), (-0.1, 0.3, 1), (0.5, 0.1, 0)]
        ]
        first = aggregate_belief_particle_reports(reports, particle_count=3)
        second = aggregate_belief_particle_reports(reports, particle_count=3)
        self.assertEqual(first, second)
        self.assertEqual(first["selected"]["index"], 0)
        self.assertTrue(first["particle_disagreement"])

    def test_terminal_win_loss_override_material_score(self):
        bad_scorer = lambda protocol, result, side: -0.75
        win, win_method = _score_result([], {"terminated": True, "winner": "p1"}, "p1", bad_scorer)
        loss, loss_method = _score_result([], {"terminated": True, "winner": "p2"}, "p1", bad_scorer)
        self.assertEqual((win, win_method), (1.0, "terminal"))
        self.assertEqual((loss, loss_method), (-1.0, "terminal"))

    def test_two_ply_selects_ko_preserving_fixture_line(self):
        class FakeClient:
            def __init__(self):
                self.next_env = 0
                self.steps = {}
                self.root_choices = {}

            def create_env(self, *args, **kwargs):
                self.next_env += 1
                env_id = f"env-{self.next_env}"
                self.steps[env_id] = 0
                return env_id

            def reset(self, env_id, *args, **kwargs):
                return {"terminated": False, "log_delta": [], "requests": {}}

            def step(self, env_id, choices, *args, **kwargs):
                self.steps[env_id] += 1
                if self.steps[env_id] == 1:
                    self.root_choices[env_id] = choices["p1"]
                    return {
                        "terminated": False,
                        "winner": None,
                        "log_delta": [],
                        "requests": {
                            "p1": {
                                "legal_actions": {
                                    "actions": [{"index": 0, "kind": "move", "choice": "move finish", "label": "Finish"}]
                                }
                            },
                            "p2": {
                                "legal_actions": {
                                    "actions": [{"index": 0, "kind": "move", "choice": "move counter", "label": "Counter"}]
                                }
                            },
                        },
                    }
                winner = "p1" if self.root_choices[env_id] == "switch preserve" else "p2"
                return {"terminated": True, "winner": winner, "log_delta": [], "requests": {}}

            def agent_action(self, env_id, side, *args, **kwargs):
                return {"action_index": 0, "choice": "unused"}

            def close_env(self, *args, **kwargs):
                return {}

        player_request = {
            "legal_actions": {
                "actions": [
                    {"index": 0, "kind": "move", "choice": "move unsafe", "label": "Unsafe attack"},
                    {"index": 1, "kind": "switch", "choice": "switch preserve", "label": "Preserve win condition"},
                ]
            }
        }
        opponent_request = {
            "legal_actions": {
                "actions": [{"index": 0, "kind": "move", "choice": "move pressure", "label": "Pressure"}]
            }
        }
        report = evaluate_two_ply_branches(
            client=FakeClient(),
            seed=SEED,
            history=[],
            player_side="p1",
            player_request=player_request,
            opponent_request=opponent_request,
            score_fn=lambda protocol, result, side: 0.0,
            config=TwoPlyConfig(
                max_root_actions=2,
                max_opponent_actions=1,
                max_followup_actions=1,
                max_decision_time_sec=30,
            ),
        )
        self.assertEqual(report["selected"]["choice"], "switch preserve")
        self.assertEqual(report["selected"]["mean_score"], 1.0)


if __name__ == "__main__":
    unittest.main()
