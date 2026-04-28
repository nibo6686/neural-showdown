import json
import os
import unittest

from neural import sim_branch_evaluator


class IntegrationSimRolloutTests(unittest.TestCase):
    def setUp(self):
        self.sim_command = os.environ.get("NEURAL_SIM_CORE_COMMAND_JSON")
        self.sim_cwd = os.environ.get("NEURAL_SIM_CORE_CWD")

    def _build_public_trace(self):
        trace = {"format": "gen9randombattle", "protocol_log": [], "turns": [{"turn": 1, "steps": [{"legal_actions": [{"index": 0, "label": "move:A", "choice": "move 1", "kind": "move", "move": "Will-O-Wisp"}, {"index": 1, "label": "move:B", "choice": "move 2", "kind": "move", "move": "Tackle"}], "chosen_action_index": 0, "p1_species": "Morpeko", "p2_species": "Vileplume", "p1_hp_ratio": 1.0, "p2_hp_ratio": 1.0}]}]}
        return trace

    def test_sim_core_integration_rollout(self):
        trace = self._build_public_trace()
        legal_actions = [{"index": 0, "label": "move:A"}, {"index": 1, "label": "move:B"}]

        results = sim_branch_evaluator.evaluate_actions(
            {"trace": trace},
            player_side="p1",
            legal_actions=legal_actions,
            rollout_config={"rollout_mode": "approximate", "rollouts_per_action": 2},
        )

        if not results:
            self.fail("approximate rollout returned no results (no details available)")

        # If any result reports approximate rollout with samples, test passes
        for r in results:
            if r.get("method") == "approx_sim_rollout" and int(r.get("rollout_count", 0)) > 0:
                return

        # Otherwise, surface detailed diagnostics.
        details = []
        for r in results:
            entry = {
                "label": r.get("label"),
                "method": r.get("method"),
                "rollout_unavailable_reason": r.get("rollout_unavailable_reason"),
                "rollout_unavailable_details": r.get("rollout_unavailable_details"),
                "rollout_count": r.get("rollout_count"),
            }
            details.append(entry)

        self.fail(f"approximate rollout did not produce approx_sim_rollout: {json.dumps(details, indent=2)}")


if __name__ == "__main__":
    unittest.main()
