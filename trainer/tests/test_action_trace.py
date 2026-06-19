import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import torch

from neural.action_features import ACTION_FEATURE_DIM
from neural.action_side_effects import annotate_action_side_effects, move_side_effects
from neural.action_trace import action_trace_enabled, write_action_trace_jsonl
from neural.live_action_recommender import recommend_actions, reset_action_ranker_cache
from neural.live_private_features import FEATURE_DIM
from neural.models.action_ranker import ActionRankerMLP


def _make_payload():
    return type(
        "Payload",
        (),
        {
            "request": {},
            "legal_actions": [
                {"kind": "move", "label": "move: Draco Meteor", "index": 0},
                {"kind": "move", "label": "move: Psyshock", "index": 1},
                {"kind": "move", "label": "move: Flamethrower", "index": 2, "disabled": True},
                {"kind": "switch", "label": "switch: Latias", "index": 8},
            ],
        },
    )()


def _private_state():
    return {
        "player_side": "p1",
        "active_moves": [
            {"id": "dracometeor", "name": "Draco Meteor", "pp": 5, "maxpp": 5, "known_from_request": True},
            {"id": "psyshock", "name": "Psyshock", "pp": 10, "maxpp": 10, "known_from_request": True},
            {"id": "flamethrower", "name": "Flamethrower", "pp": 0, "maxpp": 15, "known_from_request": True},
        ],
        "team": [
            {"species": "Latios", "active": True, "hp_fraction": 1.0},
            {"species": "Latias", "active": False, "hp_fraction": 1.0, "moves": ["Recover"]},
        ],
    }


def _run_recommender_with_temp_ranker(env=None):
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        checkpoint = root / "value-ranker.pt"
        missing = root / "missing.pt"
        model = ActionRankerMLP(input_size=FEATURE_DIM + ACTION_FEATURE_DIM, hidden_sizes=[4])
        torch.save(
            {
                "model_state_dict": model.state_dict(),
                "input_size": FEATURE_DIM + ACTION_FEATURE_DIM,
                "state_dim": FEATURE_DIM,
                "action_dim": ACTION_FEATURE_DIM,
                "hidden_sizes": [4],
                "model_type": "action-value-ranker",
                "response_method": "action_value_ranker",
            },
            checkpoint,
        )
        reset_action_ranker_cache()
        patches = [
            patch("neural.live_action_recommender.DEFAULT_ACTION_VALUE_RANKER_V2_PATH", checkpoint),
            patch("neural.live_action_recommender.DEFAULT_ACTION_RANKER_V2_PATH", missing),
            patch("neural.live_action_recommender.DEFAULT_ACTION_RANKER_PATH", missing),
            patch.dict(os.environ, env if env is not None else {"NEURAL_ACTION_TRACE": "1"}, clear=False),
        ]
        for p in patches:
            p.start()
        try:
            report = recommend_actions(
                payload=_make_payload(),
                private_state=_private_state(),
                opponent_belief={"opponents": []},
                trajectory={"turns": []},
                public_features=np.zeros(31, dtype=np.float32),
                live_features=np.zeros(FEATURE_DIM, dtype=np.float32),
                current_value=0.0,
                value_model=None,
                value_metadata={},
                policy_loader=lambda: (None, {"warning": "missing"}),
                device=torch.device("cpu"),
            )
        finally:
            for p in reversed(patches):
                p.stop()
            reset_action_ranker_cache()
        return report


class ActionSideEffectTest(unittest.TestCase):
    def test_detects_draco_meteor_special_attack_drop(self):
        effects = move_side_effects("Draco Meteor")
        self.assertEqual(effects["self_stat_drop"], {"spa": -2})
        self.assertTrue(effects["has_drawback"])

    def test_known_side_effects(self):
        self.assertEqual(move_side_effects("Close Combat")["self_stat_drop"], {"def": -1, "spd": -1})
        self.assertTrue(move_side_effects("Brave Bird")["recoil"])
        self.assertTrue(move_side_effects("Hyper Beam")["recharge"])
        self.assertTrue(move_side_effects("Outrage")["locks_user"])
        self.assertTrue(move_side_effects("U-turn")["switch_move"])
        self.assertTrue(move_side_effects("Swords Dance")["setup_move"])
        self.assertEqual(move_side_effects("Quick Attack")["priority"], 1)

    def test_no_false_drawback_on_clean_move(self):
        psyshock = move_side_effects("Psyshock")
        self.assertIsNone(psyshock["self_stat_drop"])
        self.assertFalse(psyshock["has_drawback"])

    def test_switch_annotation(self):
        switch = annotate_action_side_effects({"kind": "switch", "label": "switch: Latias"})
        self.assertTrue(switch["switch_move"])
        self.assertFalse(switch["has_drawback"])


class ActionTraceContentTest(unittest.TestCase):
    def test_trace_includes_every_legal_action(self):
        report = _run_recommender_with_temp_ranker()
        bundle = report["action_trace"]
        self.assertIsNotNone(bundle)
        # all four candidates (including the disabled one) appear exactly once
        indices = sorted(record["action_index"] for record in bundle["records"])
        self.assertEqual(indices, [0, 1, 2, 8])
        disabled = next(r for r in bundle["records"] if r["action_index"] == 2)
        self.assertFalse(disabled["legal"])

    def test_chosen_action_has_score_components(self):
        report = _run_recommender_with_temp_ranker()
        bundle = report["action_trace"]
        chosen = [r for r in bundle["records"] if r["chosen"]]
        self.assertEqual(len(chosen), 1)
        self.assertEqual(chosen[0]["ranks"]["final_rank"], 1)
        self.assertIn("final_score", chosen[0]["score_components"])
        self.assertIn("ranker_weight", chosen[0]["score_components"])

    def test_unavailable_components_report_reasons(self):
        report = _run_recommender_with_temp_ranker()
        record = report["action_trace"]["records"][0]
        for scorer in ("one_turn_branch", "two_ply_exact", "belief_branch", "material_one_turn"):
            entry = record["scorers"][scorer]
            self.assertFalse(entry["available"])
            self.assertTrue(str(entry.get("reason")))
        # rollout is unavailable live (no seed) and must carry a reason, not be dropped
        rollout = record["scorers"]["rollout"]
        self.assertFalse(rollout["available"])
        self.assertTrue(str(rollout.get("reason")))

    def test_side_effect_annotation_in_trace_flags_draco_drop(self):
        report = _run_recommender_with_temp_ranker()
        draco = next(r for r in report["action_trace"]["records"] if r["action_index"] == 0)
        self.assertEqual(draco["side_effects"]["self_stat_drop"], {"spa": -2})

    def test_trace_does_not_leak_private_payload(self):
        report = _run_recommender_with_temp_ranker()
        blob = json.dumps(report["action_trace"], default=str)
        # No raw request / private team structures.
        for forbidden in ('"request"', '"side"', '"pokemon"', '"maxpp"', '"team"'):
            self.assertNotIn(forbidden, blob)


class ActionTraceDefaultsTest(unittest.TestCase):
    def test_trace_off_by_default_and_weights_unchanged(self):
        # With NEURAL_ACTION_TRACE unset, no trace is produced and live defaults hold.
        env_without_trace = {k: v for k, v in os.environ.items() if k != "NEURAL_ACTION_TRACE"}
        with patch.dict(os.environ, env_without_trace, clear=True):
            self.assertFalse(action_trace_enabled())
            report = _run_recommender_with_temp_ranker(env={})
        self.assertIsNone(report["action_trace"])
        self.assertEqual(report["rollout_weight"], 0.75)
        self.assertEqual(report["ranker_weight"], 0.20)
        self.assertEqual(report["policy_weight"], 0.05)

    def test_jsonl_writer_noop_without_path(self):
        env_without_path = {k: v for k, v in os.environ.items() if k != "NEURAL_ACTION_TRACE_PATH"}
        with patch.dict(os.environ, env_without_path, clear=True):
            result = write_action_trace_jsonl({"records": []}, room_id="r", player="p1", turn=1)
        self.assertIsNone(result)

    def test_jsonl_writer_appends_when_path_set(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "traces.jsonl"
            with patch.dict(os.environ, {"NEURAL_ACTION_TRACE_PATH": str(path)}, clear=False):
                write_action_trace_jsonl(
                    {"schema_version": "action-trace-v1", "records": [{"label": "move: Psyshock"}]},
                    room_id="battle-x",
                    player="p1",
                    turn=14,
                )
            lines = path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)
            record = json.loads(lines[0])
            self.assertEqual(record["room_id"], "battle-x")
            self.assertEqual(record["turn"], 14)


class DracoVsPsyshockDiagnosticTest(unittest.TestCase):
    def test_fixture_is_stable_and_flags_the_drawback(self):
        from neural.action_recommender_diagnostic import build_diagnostic

        first = build_diagnostic()
        second = build_diagnostic()
        # Side-effect-derived findings are deterministic and sim-core-independent.
        self.assertEqual(first["finding"]["draco_self_stat_drop"], {"spa": -2})
        self.assertIsNone(first["finding"]["psyshock_self_stat_drop"])
        self.assertFalse(first["finding"]["spa_drop_represented_in_score"])
        self.assertEqual(
            [r["self_stat_drop"] for r in first["rows"]],
            [r["self_stat_drop"] for r in second["rows"]],
        )
        labels = {r["label"] for r in first["rows"]}
        self.assertIn("move: Draco Meteor", labels)
        self.assertIn("move: Psyshock", labels)


if __name__ == "__main__":
    unittest.main()
