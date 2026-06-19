import json
import os
import unittest

from neural.env_client import SimCoreClient
from neural.two_ply_branch import derive_belief_particle_seed


OPTIONS = {
    "view_players": ["p1", "p2"],
    "include_log_delta": True,
    "include_possible_roles": False,
}


class BeliefBranchRpcTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        command_json = os.environ.get("NEURAL_SIM_CORE_COMMAND_JSON")
        cwd = os.environ.get("NEURAL_SIM_CORE_CWD")
        if not command_json or not cwd:
            raise unittest.SkipTest("sim-core process environment is not configured")
        cls.client = SimCoreClient(json.loads(command_json), cwd)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "client"):
            cls.client.close()

    def _source(self):
        env_id = self.client.create_env(
            "gen9randombattle",
            [101, 202, 303, 404],
            {"p1": {"controller": "external"}, "p2": {"controller": "external"}},
            timeout_sec=30,
        )
        return env_id, self.client.reset(env_id, OPTIONS, timeout_sec=60)

    def test_fork_is_labeled_deterministic_and_preserves_public_state(self):
        source, result = self._source()
        forks = []
        try:
            first = self.client.fork_belief_env(source, "p1", [9, 8, 7, 6], OPTIONS, 60)
            second = self.client.fork_belief_env(source, "p1", [9, 8, 7, 6], OPTIONS, 60)
            forks.extend([first["env_id"], second["env_id"]])
            self.assertEqual(first["belief"]["mode"], "randbats_belief")
            self.assertEqual(first["belief"]["sampled_sets"], second["belief"]["sampled_sets"])
            self.assertEqual(first["belief"]["public_info_constraint_violations"], 0)
            self.assertEqual(
                [mon["species"] for mon in result["views"]["p1"]["opponent_team"]],
                [mon["species"] for mon in first["result"]["views"]["p1"]["opponent_team"]],
            )
        finally:
            for env_id in forks:
                self.client.close_env(env_id, timeout_sec=10)
            self.client.close_env(source, timeout_sec=10)

    def test_different_belief_seed_can_change_hidden_sets(self):
        source, _ = self._source()
        forks = []
        try:
            first = self.client.fork_belief_env(source, "p1", [1, 2, 3, 4], OPTIONS, 60)
            second = self.client.fork_belief_env(source, "p1", [4, 3, 2, 1], OPTIONS, 60)
            forks.extend([first["env_id"], second["env_id"]])
            first_hidden = [row for row in first["belief"]["sampled_sets"] if not row["revealed"]]
            second_hidden = [row for row in second["belief"]["sampled_sets"] if not row["revealed"]]
            self.assertNotEqual(first_hidden, second_hidden)
        finally:
            for env_id in forks:
                self.client.close_env(env_id, timeout_sec=10)
            self.client.close_env(source, timeout_sec=10)

    def test_three_derived_particles_are_deterministic_and_distinct(self):
        source, _ = self._source()
        forks = []
        try:
            base = [9, 8, 7, 6]
            first_samples = []
            second_samples = []
            for particle_index in range(3):
                particle_seed = derive_belief_particle_seed(base, particle_index)
                first = self.client.fork_belief_env(source, "p1", particle_seed, OPTIONS, 60)
                second = self.client.fork_belief_env(source, "p1", particle_seed, OPTIONS, 60)
                forks.extend([first["env_id"], second["env_id"]])
                first_samples.append(first["belief"]["sampled_sets"])
                second_samples.append(second["belief"]["sampled_sets"])
                self.assertEqual(first["belief"]["public_info_constraint_violations"], 0)
            self.assertEqual(first_samples, second_samples)
            hidden_signatures = {
                json.dumps(
                    [row for row in sample if not row["revealed"]],
                    sort_keys=True,
                )
                for sample in first_samples
            }
            self.assertEqual(len(hidden_signatures), 3)
        finally:
            for env_id in forks:
                self.client.close_env(env_id, timeout_sec=10)
            self.client.close_env(source, timeout_sec=10)


if __name__ == "__main__":
    unittest.main()
