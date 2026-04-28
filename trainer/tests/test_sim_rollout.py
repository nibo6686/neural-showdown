import json
import os
import unittest
from types import SimpleNamespace

from neural import sim_branch_evaluator, action_value_search


class FakeSimCoreClient:
    def __init__(self, command, cwd):
        self.envs = {}
        self.counter = 0

    def create_env(self, format_name="gen9randombattle", seed=None, players=None):
        self.counter += 1
        env_id = f"env-{self.counter}"
        self.envs[env_id] = {"seed": seed}
        return env_id

    def reset(self, env_id):
        # return a simple request structure with p1/p2 legal actions
        actions_p1 = [{"index": 0, "label": "move:A", "choice": "move 1"}, {"index": 1, "label": "move:B", "choice": "move 2"}]
        actions_p2 = [{"index": 0, "label": "move:X", "choice": "move 1"}]
        return {"requests": {"p1": {"legal_actions": {"actions": actions_p1}}, "p2": {"legal_actions": {"actions": actions_p2}}}}

    def step(self, env_id, choices, options=None):
        # simulate a protocol delta and return requests unchanged
        res = {"log_delta": ["|move|p1a: move 1"], "requests": (self.reset(env_id)["requests"]) }
        return res

    def close_env(self, env_id):
        self.envs.pop(env_id, None)

    def close(self):
        self.envs.clear()


class WrapperSimRolloutTests(unittest.TestCase):
    def setUp(self):
        # monkeypatch SimCoreClient used in evaluator
        self.orig_client = sim_branch_evaluator.SimCoreClient
        sim_branch_evaluator.SimCoreClient = FakeSimCoreClient

        # monkeypatch value loader to return a deterministic value fn
        self.orig_loader = action_value_search._load_value_fn

        def fake_loader(path):
            return lambda view, request, protocol_history, step_history, current_step: 0.42

        action_value_search._load_value_fn = fake_loader

        # set env vars to enable sim path
        os.environ["NEURAL_SIM_CORE_COMMAND_JSON"] = json.dumps(["fake"])
        os.environ["NEURAL_SIM_CORE_CWD"] = "."

    def tearDown(self):
        sim_branch_evaluator.SimCoreClient = self.orig_client
        action_value_search._load_value_fn = self.orig_loader
        os.environ.pop("NEURAL_SIM_CORE_COMMAND_JSON", None)
        os.environ.pop("NEURAL_SIM_CORE_CWD", None)

    def _build_trace_with_seed(self):
        trace = {"format": "gen9randombattle", "protocol_log": [">start " + json.dumps({"seed": [1, 2, 3, 4]})], "turns": [{"turn": 1, "steps": [{"legal_actions": [{"index": 0, "label": "move:A", "choice": "move 1"}, {"index": 1, "label": "move:B", "choice": "move 2"}], "chosen_action_index": 0}]}]}
        return trace

    def test_sim_rollout_success(self):
        trace = self._build_trace_with_seed()
        legal_actions = [{"index": 0, "label": "move:A"}, {"index": 1, "label": "move:B"}]
        results = sim_branch_evaluator.evaluate_actions(
            {"trace": trace},
            player_side="p1",
            legal_actions=legal_actions,
            rollout_config={"value_checkpoint": "dummy", "rollout_mode": "exact", "rollouts_per_action": 2},
        )
        print("SIM RESULTS:", results)
        self.assertTrue(results)
        for r in results:
            self.assertEqual(r.get("method"), "exact_sim_rollout")
            self.assertGreater(r.get("rollout_count", 0), 0)
            self.assertIsNotNone(r.get("expected_value"))

    def test_missing_seed_reports_unavailable_in_exact_mode(self):
        trace = {"format": "gen9randombattle", "protocol_log": [], "turns": [{"turn": 1, "steps": [{"legal_actions": [{"index": 0, "label": "move:A", "choice": "move 1"}], "chosen_action_index": 0}]}]}
        legal_actions = [{"index": 0, "label": "move:A"}]
        results = sim_branch_evaluator.evaluate_actions(
            {"trace": trace},
            player_side="p1",
            legal_actions=legal_actions,
            rollout_config={"value_checkpoint": "dummy", "rollout_mode": "exact"},
        )
        self.assertTrue(results)
        for r in results:
            self.assertNotEqual(r.get("method"), "exact_sim_rollout")
            self.assertEqual(r.get("rollout_unavailable_reason"), "exact_replay_unavailable")

    def test_missing_seed_uses_approximate_mode(self):
        trace = {"format": "gen9randombattle", "protocol_log": [], "turns": [{"turn": 1, "steps": [{"legal_actions": [{"index": 0, "label": "move:A", "choice": "move 1"}], "chosen_action_index": 0, "p1_species": "Morpeko", "p2_species": "Vileplume", "p1_hp_ratio": 1.0, "p2_hp_ratio": 1.0}]}]}
        legal_actions = [{"index": 0, "label": "move:A", "kind": "move", "move": "Will-O-Wisp"}]
        results = sim_branch_evaluator.evaluate_actions(
            {"trace": trace},
            player_side="p1",
            legal_actions=legal_actions,
            rollout_config={"value_checkpoint": "dummy", "rollout_mode": "approximate", "rollouts_per_action": 3},
        )
        self.assertTrue(results)
        for r in results:
            self.assertEqual(r.get("method"), "approx_sim_rollout")
            self.assertGreater(r.get("rollout_count", 0), 0)


if __name__ == "__main__":
    unittest.main()
