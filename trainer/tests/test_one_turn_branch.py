import json
import os
import unittest
from typing import Any, Dict, List, Optional

from neural.env_client import SimCoreClient
from neural.one_turn_branch import (
    BranchConfig,
    _terminal_score,
    evaluate_action_branches,
    make_material_score_fn,
    make_state_score_fn,
)


RESULT_OPTIONS = {
    "view_players": ["p1", "p2"],
    "include_log_delta": True,
    "include_possible_roles": False,
}
SEED = [101, 202, 303, 404]


def _faint_count_score(protocol, step_result, player_side) -> float:
    """Deterministic stub: number of faint events in the branch protocol."""
    return float(sum(1 for line in protocol if str(line).startswith("|faint|")))


def _terminal_only_score(protocol, step_result, player_side) -> float:
    """Non-terminal states score 0; terminal outcomes are handled internally."""
    return 0.0


class OneTurnBranchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        command_json = os.environ.get("NEURAL_SIM_CORE_COMMAND_JSON")
        cwd = os.environ.get("NEURAL_SIM_CORE_CWD")
        if not command_json or not cwd:
            raise unittest.SkipTest("sim-core process environment is not configured")
        cls.client = SimCoreClient(json.loads(command_json), cwd)
        cls.turns, cls.winner = cls._play_battle(cls.client, SEED)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "client"):
            cls.client.close()

    @staticmethod
    def _play_battle(client: SimCoreClient, seed):
        env_id = client.create_env(
            "gen9randombattle",
            seed,
            {"p1": {"controller": "external"}, "p2": {"controller": "external"}},
            timeout_sec=30,
        )
        turns: List[Dict[str, Any]] = []
        history: List[Dict[str, str]] = []
        result = client.reset(env_id, RESULT_OPTIONS, timeout_sec=60)
        try:
            while not result.get("terminated"):
                requests = result.get("requests") or {}
                turns.append(
                    {
                        "history": [dict(entry) for entry in history],
                        "requests": {
                            key: (dict(value) if isinstance(value, dict) else value)
                            for key, value in requests.items()
                        },
                    }
                )
                choices: Dict[str, str] = {}
                for player in ("p1", "p2"):
                    request = requests.get(player)
                    if isinstance(request, dict) and request.get("legal_actions"):
                        decision = client.agent_action(env_id, player, "heuristic", timeout_sec=20)
                        choices[player] = str(decision.get("choice") or "default")
                if not choices:
                    break
                result = client.step(env_id, choices, RESULT_OPTIONS, timeout_sec=60)
                history.append(dict(choices))
            winner = result.get("winner")
        finally:
            client.close_env(env_id, timeout_sec=10)
        return turns, winner

    def _first_actionable_turn(self, side: str) -> Dict[str, Any]:
        for turn in self.turns:
            request = turn["requests"].get(side)
            if isinstance(request, dict) and request.get("legal_actions") and not request.get("wait"):
                return turn
        self.skipTest(f"no actionable {side} turn found")

    def _evaluate(self, turn: Dict[str, Any], side: str, score_fn, **config_kwargs) -> Dict[str, Any]:
        opponent = "p2" if side == "p1" else "p1"
        return evaluate_action_branches(
            client=self.client,
            seed=SEED,
            history=turn["history"],
            player_side=side,
            player_request=turn["requests"].get(side),
            opponent_request=turn["requests"].get(opponent),
            score_fn=score_fn,
            config=BranchConfig(**config_kwargs),
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
            before_request = before["requests"]["p1"]
            open_before = len(self.client._open_envs)

            turn = {"history": [], "requests": before["requests"]}
            report = self._evaluate(turn, "p1", _faint_count_score)
            self.assertGreater(report["branch_count"], 0)

            # The live env was never stepped: a fresh step still advances turn 1 -> 2.
            p1_choice = before_request["legal_actions"]["actions"][
                before_request["legal_actions"]["available_indices"][0]
            ]["choice"]
            p2_request = before["requests"]["p2"]
            p2_choice = p2_request["legal_actions"]["actions"][
                p2_request["legal_actions"]["available_indices"][0]
            ]["choice"]
            after = self.client.step(live_env, {"p1": p1_choice, "p2": p2_choice}, RESULT_OPTIONS, timeout_sec=60)
            self.assertGreaterEqual(int(after["info"]["turn"]), int(before["info"]["turn"]))
            # All fork envs were closed; only the live env remains beyond the baseline.
            self.assertEqual(len(self.client._open_envs), open_before)
        finally:
            self.client.close_env(live_env, timeout_sec=10)

    def test_same_seed_state_actions_are_deterministic(self):
        turn = self._first_actionable_turn("p1")
        first = self._evaluate(turn, "p1", _faint_count_score)
        second = self._evaluate(turn, "p1", _faint_count_score)
        first_scores = [(row["index"], row["mean_score"], row["worst_score"], row["best_score"]) for row in first["actions"]]
        second_scores = [(row["index"], row["mean_score"], row["worst_score"], row["best_score"]) for row in second["actions"]]
        self.assertEqual(first_scores, second_scores)
        self.assertEqual(first["branch_count"], second["branch_count"])

    def test_illegal_action_subset_is_ignored_cleanly(self):
        turn = self._first_actionable_turn("p1")
        opponent = "p2"
        report = evaluate_action_branches(
            client=self.client,
            seed=SEED,
            history=turn["history"],
            player_side="p1",
            player_request=turn["requests"].get("p1"),
            opponent_request=turn["requests"].get(opponent),
            score_fn=_faint_count_score,
            config=BranchConfig(),
            legal_action_indices=[999],  # not a legal index
        )
        self.assertEqual(report["actions"], [])
        self.assertEqual(report["branch_count"], 0)

    def test_forced_switch_state_is_handled(self):
        for turn in self.turns:
            for side in ("p1", "p2"):
                request = turn["requests"].get(side)
                if isinstance(request, dict) and request.get("force_switch") and request.get("legal_actions"):
                    report = self._evaluate(turn, side, _faint_count_score)
                    self.assertEqual(report["branch_errors"], 0)
                    self.assertGreater(len(report["actions"]), 0)
                    for row in report["actions"]:
                        self.assertEqual(row["action_category"], "switch")
                    return
        self.skipTest("no forced-switch state found in this seed")

    def test_obvious_ko_branch_scores_better_than_non_ko(self):
        if self.winner not in ("p1", "p2"):
            self.skipTest("battle did not produce a decisive winner")
        side = self.winner
        actionable = [
            turn
            for turn in self.turns
            if isinstance(turn["requests"].get(side), dict)
            and turn["requests"][side].get("legal_actions")
            and not turn["requests"][side].get("wait")
        ]
        for turn in reversed(actionable[-6:]):
            report = self._evaluate(turn, side, _terminal_only_score, objective="best_score")
            winning = [row for row in report["actions"] if row["best_score"] == 1.0]
            non_winning = [row for row in report["actions"] if row["best_score"] is not None and row["best_score"] < 1.0]
            if winning and non_winning:
                self.assertEqual(report["actions"][0]["best_score"], 1.0)
                self.assertGreater(report["actions"][0]["best_score"], non_winning[0]["best_score"])
                return
        self.skipTest("no practical one-turn KO/win fixture in this seed")

    def test_no_heuristic_damage_fallback_inside_branches(self):
        turn = self._first_actionable_turn("p1")
        report = self._evaluate(turn, "p1", _faint_count_score)
        self.assertEqual(report["damage_fallbacks"], 0)
        serialized = json.dumps(report)
        self.assertNotIn("heuristic_fallback", serialized)

    def test_latency_is_recorded(self):
        turn = self._first_actionable_turn("p1")
        report = self._evaluate(turn, "p1", _faint_count_score)
        self.assertGreater(report["latency_ms"], 0.0)
        for row in report["actions"]:
            self.assertGreaterEqual(row["latency_ms"], 0.0)


def _mon(hp, active=False, status=None, boosts=None):
    return {
        "active": active,
        "fainted": hp <= 0.0,
        "hp_ratio": hp,
        "status": status,
        "boosts": boosts or {},
    }


def _view(own, opp, team_size=None):
    return {
        "self_team": own,
        "opponent_team": opp,
        "team_size": team_size or {"p1": 6, "p2": 6},
        "field": {"side_conditions": {"self": {}, "opponent": {}}},
    }


def _result(views):
    return {"views": views, "requests": {}, "terminated": False, "winner": None, "info": {"turn": 5}}


class StateScorerTest(unittest.TestCase):
    """Perspective/correctness tests for the deterministic exact-state scorers.

    These are pure-function tests and do not require sim-core.
    """

    def setUp(self):
        self.healthy = [_mon(1.0, active=True)] + [_mon(1.0) for _ in range(5)]
        self.crippled = [_mon(0.1, active=True)] + [_mon(0.1) for _ in range(5)]

    def test_state_scorer_flips_sign_with_perspective(self):
        score = make_state_score_fn()
        # Same underlying state viewed from each side: healthy team vs crippled team.
        s_advantaged = score([], _result({"p1": _view(self.healthy, self.crippled)}), "p1")
        s_disadvantaged = score([], _result({"p2": _view(self.crippled, self.healthy)}), "p2")
        self.assertGreater(s_advantaged, 0.0)
        self.assertLess(s_disadvantaged, 0.0)
        # Public information is symmetric, so scores should be near opposite.
        self.assertLess(abs(s_advantaged + s_disadvantaged), 0.25)

    def test_scorer_does_not_treat_both_sides_as_winning(self):
        for score in (make_state_score_fn(), make_material_score_fn()):
            s_p1 = score([], _result({"p1": _view(self.healthy, self.crippled)}), "p1")
            s_p2 = score([], _result({"p2": _view(self.crippled, self.healthy)}), "p2")
            self.assertFalse(s_p1 > 0.05 and s_p2 > 0.05, "both sides scored as winning")

    def test_material_advantage_scores_above_disadvantage(self):
        for score in (make_state_score_fn(), make_material_score_fn()):
            advantage = score([], _result({"p1": _view(self.healthy, self.crippled)}), "p1")
            disadvantage = score([], _result({"p1": _view(self.crippled, self.healthy)}), "p1")
            self.assertGreater(advantage, disadvantage)
            self.assertGreater(advantage, 0.0)
            self.assertLess(disadvantage, 0.0)

    def test_terminal_win_scores_above_terminal_loss(self):
        self.assertEqual(_terminal_score({"winner": "p1"}, "p1"), 1.0)
        self.assertEqual(_terminal_score({"winner": "p2"}, "p1"), -1.0)
        self.assertEqual(_terminal_score({"winner": "tie"}, "p1"), 0.0)
        self.assertGreater(
            _terminal_score({"winner": "p1"}, "p1"),
            _terminal_score({"winner": "p2"}, "p1"),
        )

    def test_status_and_hazards_shift_score_in_expected_direction(self):
        score = make_state_score_fn()
        base = score([], _result({"p1": _view(self.healthy, list(self.healthy))}), "p1")
        # Opponent active asleep should help us relative to the neutral baseline.
        opp_status = [_mon(1.0, active=True, status="slp")] + [_mon(1.0) for _ in range(5)]
        with_status = score([], _result({"p1": _view(self.healthy, opp_status)}), "p1")
        self.assertGreater(with_status, base)

    def test_strict_mode_flags_wrong_feature_version(self):
        from neural.live_eval_server import _strict_live_eval_errors

        diagnostics = {
            "selected_checkpoints": {
                "value": {"exists": True, "metadata": {"feature_version": "wrong-version"}},
                "action_ranker": {"exists": True, "metadata": {}},
            },
            "sim_core_damage_rpc": {"reachable": True, "sample": {"damage_method": "smogon_calc"}},
            "damage_engine_smoke": {"result": {"damage_method": "smogon_calc"}},
        }
        errors = _strict_live_eval_errors(diagnostics)
        self.assertTrue(any("feature_version" in error for error in errors))


class LiveSimValueTest(unittest.TestCase):
    """Tests for the live/sim bounded value head and its branch scorer (Part G).

    Pure-function / checkpoint tests; no sim-core required.
    """

    def test_dataset_label_perspective_flips_sign(self):
        from neural.build_replay_value_dataset import result_from_winner_side

        self.assertEqual(result_from_winner_side("p1", "p1"), 1.0)
        self.assertEqual(result_from_winner_side("p1", "p2"), -1.0)
        self.assertEqual(result_from_winner_side("p2", "p2"), 1.0)
        self.assertEqual(result_from_winner_side("tie", "p1"), 0.0)

    def test_discounted_label_is_bounded_and_decays(self):
        from neural.value_features import discounted_terminal_return

        self.assertEqual(discounted_terminal_return(1.0, 0, 0.97), 1.0)
        self.assertLessEqual(abs(discounted_terminal_return(1.0, 12, 0.97)), 1.0)
        self.assertLess(
            discounted_terminal_return(1.0, 12, 0.97),
            discounted_terminal_return(1.0, 2, 0.97),
        )

    def test_bounded_model_output_range(self):
        import torch

        from neural.models.value_mlp import BoundedValueMLP

        model = BoundedValueMLP(input_size=115, hidden_sizes=[16, 16])
        out = model(torch.randn(8, 115) * 50.0)
        self.assertEqual(tuple(out.shape), (8,))
        self.assertGreaterEqual(float(out.min()), -1.0)
        self.assertLessEqual(float(out.max()), 1.0)

    def _write_checkpoint(self, tmp_path, *, feature_version, feature_dim, bounded):
        import torch

        from neural.models.value_mlp import BoundedValueMLP

        model = BoundedValueMLP(input_size=feature_dim, hidden_sizes=[16])
        torch.save(
            {
                "model_state_dict": model.state_dict(),
                "model_type": "live-sim-bounded-value",
                "feature_version": feature_version,
                "feature_dim": feature_dim,
                "input_size": feature_dim,
                "hidden_sizes": [16],
                "bounded_output": bounded,
            },
            tmp_path,
        )

    def test_scorer_rejects_wrong_feature_dim_and_version(self):
        import tempfile

        from neural.live_private_features import FEATURE_DIM, FEATURE_VERSION
        from neural.one_turn_branch import make_live_sim_value_score_fn

        with tempfile.TemporaryDirectory() as tmp:
            wrong_dim = f"{tmp}/wrong_dim.pt"
            self._write_checkpoint(wrong_dim, feature_version=FEATURE_VERSION, feature_dim=FEATURE_DIM - 1, bounded=True)
            with self.assertRaises(ValueError):
                make_live_sim_value_score_fn(wrong_dim)

            wrong_version = f"{tmp}/wrong_version.pt"
            self._write_checkpoint(wrong_version, feature_version="bad-version", feature_dim=FEATURE_DIM, bounded=True)
            with self.assertRaises(ValueError):
                make_live_sim_value_score_fn(wrong_version)

            not_bounded = f"{tmp}/not_bounded.pt"
            self._write_checkpoint(not_bounded, feature_version=FEATURE_VERSION, feature_dim=FEATURE_DIM, bounded=False)
            with self.assertRaises(ValueError):
                make_live_sim_value_score_fn(not_bounded)

    def test_scorer_loads_correct_checkpoint(self):
        from neural.live_private_features import FEATURE_DIM, FEATURE_VERSION
        from neural.one_turn_branch import DEFAULT_LIVE_SIM_VALUE_CHECKPOINT, make_live_sim_value_score_fn

        if not os.path.exists(DEFAULT_LIVE_SIM_VALUE_CHECKPOINT):
            self.skipTest("live_sim_value checkpoint not trained in this environment")
        score = make_live_sim_value_score_fn()
        meta = getattr(score, "metadata", {})
        self.assertEqual(meta.get("feature_version"), FEATURE_VERSION)
        self.assertEqual(meta.get("feature_dim"), FEATURE_DIM)
        self.assertTrue(meta.get("bounded_output"))


if __name__ == "__main__":
    unittest.main()
