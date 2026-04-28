import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import torch

from neural.build_live_private_value_dataset import build_live_private_value_dataset
from neural.live_private_features import (
    FEATURE_DIM,
    FEATURE_NAMES,
    FEATURE_VERSION,
    build_live_private_feature_vector,
    mirror_public_features,
    opponent_belief_feature_vector,
    private_state_feature_vector,
    public_feature_vector_from_trajectory,
)
from neural.live_eval_server import EvalRequest, evaluate_with_model, legal_action_candidates, reset_model_caches
from neural.compare_replay_evals import compare_replay_evals
from neural.live_action_recommender import recommend_actions
from neural.live_private_state import extract_private_side_state
from neural.models.policy_value_mlp import PolicyValueMLP
from neural.parse_replay_logs import parse_protocol_log
from neural.train_live_private_value import train_live_private_value_model


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "replay_sample.log"


def write_tiny_trace(path: Path) -> None:
    trace = {
        "battle_index": 0,
        "env_id": "env-1",
        "format": "gen9randombattle",
        "winner": "p1",
        "turns": [
            {
                "turn": 1,
                "steps": [
                    {
                        "step_index": 0,
                        "turn": 1,
                        "p1_species": "Pikachu",
                        "p1_hp_ratio": 1.0,
                        "p2_species": "Charizard",
                        "p2_hp_ratio": 1.0,
                        "legal_actions": [
                            {"index": 0, "kind": "move", "label": "move:Thunderbolt", "move": "Thunderbolt"},
                            {"index": 8, "kind": "switch", "label": "switch:Bulbasaur"},
                        ],
                        "protocol_log": [
                            "|player|p1|Alice",
                            "|player|p2|Bob",
                            "|turn|1",
                            "|move|p1a: Pikachu|Thunderbolt|p2a: Charizard",
                        ],
                    }
                ],
            }
        ],
    }
    path.write_text(json.dumps(trace), encoding="utf-8")


def save_checkpoint(path: Path, input_size: int) -> None:
    model = PolicyValueMLP(input_size=input_size, hidden_sizes=[4], action_size=13)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "input_size": input_size,
            "hidden_sizes": [4],
            "action_size": 13,
            "feature_version": FEATURE_VERSION if input_size == FEATURE_DIM else "public-replay-events-v1",
        },
        path,
    )


class LivePrivateFeatureTest(unittest.TestCase):
    def test_feature_schema_is_stable_shape(self):
        self.assertEqual(FEATURE_VERSION, "live-private-belief-v2")
        self.assertEqual(len(FEATURE_NAMES), FEATURE_DIM)
        self.assertEqual(len(set(FEATURE_NAMES)), len(FEATURE_NAMES))
        self.assertIn("missing_private_state", FEATURE_NAMES)
        self.assertIn("opponent_candidate_entropy_norm", FEATURE_NAMES)
        self.assertIn("opp_active_seeded", FEATURE_NAMES)

    def test_missing_private_state_is_safe(self):
        vector = private_state_feature_vector(None)
        self.assertEqual(vector.shape[0], len([name for name in FEATURE_NAMES if name.startswith("missing_")]) + 32)
        self.assertEqual(float(vector[0]), 1.0)
        self.assertTrue(np.isfinite(vector).all())

    def test_opponent_belief_features_are_included(self):
        belief = {
            "opponents": [
                {
                    "species": "Charizard",
                    "revealed": {"moves": ["Flamethrower"], "item": "Heavy-Duty Boots", "ability": None, "tera_type": "Dragon"},
                    "candidate_count": 2,
                    "filter_relaxed": True,
                    "top_candidates": [
                        {"prob": 0.75, "moves": ["Flamethrower", "Roost"], "abilities": ["Blaze"], "tera_types": ["Dragon"]},
                        {"prob": 0.25, "moves": ["Fire Blast"], "abilities": ["Solar Power"], "tera_types": ["Fire"]},
                    ],
                    "inferred": {"abilities": [{"value": "Blaze"}], "tera_types": [{"value": "Dragon"}]},
                }
            ]
        }
        vector = opponent_belief_feature_vector(belief)
        self.assertEqual(vector.shape[0], 14)
        self.assertGreater(vector[2], 0.0)
        self.assertEqual(float(vector[7]), 1.0)
        self.assertEqual(float(vector[9]), 1.0)

    def test_live_private_feature_vector_combines_public_private_belief(self):
        trajectory = parse_protocol_log(FIXTURE_PATH.read_text(encoding="utf-8").splitlines())
        public, _ = public_feature_vector_from_trajectory(trajectory)
        private_state = {
            "team": [{"species": "Pikachu", "active": True, "hp_fraction": 0.5, "item": "Light Ball", "ability": "Static", "tera_type": "Electric"}],
            "active_moves": [{"name": "Thunderbolt", "pp": 10, "maxpp": 15, "disabled": False}],
            "legal_actions": [{"kind": "move", "label": "Thunderbolt"}],
        }
        features, debug = build_live_private_feature_vector(
            public_features=public,
            private_state=private_state,
            opponent_belief={"opponents": []},
            trajectory=trajectory,
            player_side="p1",
        )
        self.assertEqual(features.shape[0], FEATURE_DIM)
        self.assertEqual(debug["feature_version"], FEATURE_VERSION)
        self.assertTrue(debug["used_private_state"])

    def test_public_features_can_be_mirrored_for_p2_perspective(self):
        trajectory = parse_protocol_log(FIXTURE_PATH.read_text(encoding="utf-8").splitlines())
        p1_public, _ = public_feature_vector_from_trajectory(trajectory, perspective_side="p1")
        p2_public, _ = public_feature_vector_from_trajectory(trajectory, perspective_side="p2")
        self.assertTrue(np.allclose(p2_public, mirror_public_features(p1_public)))
        self.assertAlmostEqual(float(p2_public[3]), -float(p1_public[3]), places=5)


class LivePrivateDatasetTrainTest(unittest.TestCase):
    def test_build_live_private_value_dataset_smoke(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            raw = root / "raw"
            raw.mkdir()
            (raw / "fixture.log").write_text(FIXTURE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
            trace_dir = root / "traces"
            trace_dir.mkdir()
            write_tiny_trace(trace_dir / "battle_0.json")
            sets_path = root / "sets.json"
            sets_path.write_text("{}", encoding="utf-8")
            trajectories = root / "trajectories.jsonl.gz"
            output = root / "live.npz"
            report = build_live_private_value_dataset(
                replay_dir=raw,
                trajectories_path=trajectories,
                trace_dirs=[trace_dir],
                output_path=output,
                report_json_path=root / "report.json",
                report_md_path=root / "report.md",
                sets_path=str(sets_path),
                include_debug_fields=True,
            )
            self.assertTrue(output.exists())
            self.assertGreater(report["examples_from_public_replays"], 0)
            self.assertGreater(report["examples_from_local_traces"], 0)
            self.assertIn("public_replay_private_reconstructed", report["source_breakdown"])
            self.assertEqual(report["missing_private_state_percentage"], 0.0)
            with np.load(output, allow_pickle=True) as data:
                self.assertEqual(data["states"].shape[1], FEATURE_DIM)
                self.assertEqual(str(data["feature_version"]), FEATURE_VERSION)
                self.assertIn("public_replay_private_reconstructed", set(data["source_kinds"].astype(str).tolist()))
                metadata = [json.loads(raw) for raw in data["metadata_json"].astype(str).tolist()]
                perspectives = {item.get("perspective") for item in metadata if item.get("source_kind") == "public_replay_private_reconstructed"}
                self.assertEqual(perspectives, {"p1", "p2"})
                self.assertTrue((data["missing_private_state"] == 0.0).all())

    def test_train_live_private_value_tiny_dataset(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            dataset = root / "live.npz"
            checkpoint = root / "live.pt"
            rng = np.random.RandomState(7)
            np.savez(
                dataset,
                states=rng.randn(8, FEATURE_DIM).astype(np.float32),
                value_targets=np.asarray([1, -1, 1, -1, 0, 1, -1, 0], dtype=np.float32),
                final_results=np.asarray([1, -1, 1, -1, 0, 1, -1, 0], dtype=np.float32),
                source_kinds=np.asarray(["public_replay_augmented"] * 4 + ["local_trace_private"] * 4),
                missing_private_state=np.asarray([1, 1, 1, 1, 0, 0, 0, 0], dtype=np.float32),
                feature_version=np.asarray(FEATURE_VERSION),
            )
            report = train_live_private_value_model(
                dataset_path=dataset,
                checkpoint_path=checkpoint,
                hidden_sizes=[8],
                epochs=1,
                batch_size=4,
            )
            self.assertTrue(checkpoint.exists())
            self.assertEqual(report["feature_dim"], FEATURE_DIM)
            self.assertIn("source_specific_validation", report)


class LiveEvalServerModelSelectionTest(unittest.TestCase):
    def setUp(self):
        reset_model_caches()

    def tearDown(self):
        reset_model_caches()

    def _payload(self) -> EvalRequest:
        return EvalRequest(
            room_id="battle-test",
            url="https://play.pokemonshowdown.com/battle-test",
            player="p1",
            log=[
                "|player|p1|Alice",
                "|player|p2|Bob",
                "|turn|1",
                "|switch|p2a: Charizard|Charizard, L80, M|100/100",
                "|move|p1a: Pikachu|Thunderbolt|p2a: Charizard",
            ],
            request={
                "side": {
                    "id": "p1",
                    "pokemon": [
                        {"ident": "p1: Pikachu", "details": "Pikachu, L80", "condition": "100/100", "active": True},
                        {"ident": "p1: Bulbasaur", "details": "Bulbasaur, L80", "condition": "100/100", "active": False},
                    ],
                },
                "active": [{"moves": [{"move": "Thunderbolt", "pp": 10, "maxpp": 15, "disabled": False}]}],
            },
            legal_actions=[{"kind": "move", "label": "Thunderbolt", "index": 0}, {"kind": "switch", "label": "Bulbasaur", "index": 8}],
        )

    def test_live_eval_falls_back_to_31d_when_new_checkpoint_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            old_path = root / "old.pt"
            new_path = root / "missing.pt"
            policy_path = root / "missing_policy.pt"
            save_checkpoint(old_path, 31)
            with patch("neural.live_eval_server.OLD_VALUE_MODEL_PATH", old_path), patch(
                "neural.live_eval_server.LIVE_PRIVATE_VALUE_MODEL_PATH", new_path
            ), patch("neural.live_eval_server.REPLAY_POLICY_MODEL_PATH", policy_path):
                reset_model_caches()
                response = evaluate_with_model(self._payload())
        self.assertEqual(response["model_type"], "public-replay-value")
        self.assertEqual(response["feature_version"], "public-replay-events-v1")
        self.assertFalse(response["used_private_state"])

    def test_live_eval_uses_new_checkpoint_when_present(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            old_path = root / "old.pt"
            new_path = root / "new.pt"
            v2_path = root / "missing_v2.pt"
            policy_path = root / "missing_policy.pt"
            save_checkpoint(old_path, 31)
            save_checkpoint(new_path, FEATURE_DIM)
            with patch("neural.live_eval_server.OLD_VALUE_MODEL_PATH", old_path), patch(
                "neural.live_eval_server.LIVE_PRIVATE_VALUE_MODEL_V2_PATH", v2_path
            ), patch("neural.live_eval_server.LIVE_PRIVATE_VALUE_MODEL_PATH", new_path), patch("neural.live_eval_server.REPLAY_POLICY_MODEL_PATH", policy_path):
                reset_model_caches()
                response = evaluate_with_model(self._payload())
        self.assertEqual(response["model_type"], "live-private-belief-value")
        self.assertEqual(response["feature_version"], FEATURE_VERSION)
        self.assertTrue(response["used_private_state"])
        self.assertIn("opponent_beliefs", response["debug"]["inferred"])

    def test_live_eval_prefers_v2_checkpoint_when_present(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            old_path = root / "old.pt"
            v1_path = root / "v1.pt"
            v2_path = root / "v2.pt"
            policy_path = root / "missing_policy.pt"
            save_checkpoint(old_path, 31)
            save_checkpoint(v1_path, FEATURE_DIM)
            save_checkpoint(v2_path, FEATURE_DIM)
            with patch("neural.live_eval_server.OLD_VALUE_MODEL_PATH", old_path), patch(
                "neural.live_eval_server.LIVE_PRIVATE_VALUE_MODEL_V2_PATH", v2_path
            ), patch("neural.live_eval_server.LIVE_PRIVATE_VALUE_MODEL_PATH", v1_path), patch("neural.live_eval_server.REPLAY_POLICY_MODEL_PATH", policy_path):
                reset_model_caches()
                response = evaluate_with_model(self._payload())
        self.assertEqual(response["checkpoint_path"], str(v2_path))
        self.assertEqual(response["feature_version"], FEATURE_VERSION)

    def test_top_actions_use_request_move_labels(self):
        payload = self._payload()
        labels = [candidate["label"] for candidate in legal_action_candidates(payload)]
        self.assertIn("move: Thunderbolt", labels)
        self.assertIn("switch: Bulbasaur", labels)

    def test_live_eval_response_has_live_private_model_type(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            old_path = root / "old.pt"
            new_path = root / "new.pt"
            policy_path = root / "missing_policy.pt"
            save_checkpoint(old_path, 31)
            save_checkpoint(new_path, FEATURE_DIM)
            with patch("neural.live_eval_server.OLD_VALUE_MODEL_PATH", old_path), patch(
                "neural.live_eval_server.LIVE_PRIVATE_VALUE_MODEL_PATH", new_path
            ), patch("neural.live_eval_server.REPLAY_POLICY_MODEL_PATH", policy_path):
                reset_model_caches()
                response = evaluate_with_model(self._payload())
        self.assertEqual(response["model_type"], "live-private-belief-value")
        self.assertEqual(response["feature_dim"], FEATURE_DIM)
        self.assertEqual(response["feature_version"], FEATURE_VERSION)

    def test_live_eval_can_be_forced_to_public_replay(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            old_path = root / "old.pt"
            new_path = root / "new.pt"
            policy_path = root / "missing_policy.pt"
            save_checkpoint(old_path, 31)
            save_checkpoint(new_path, FEATURE_DIM)
            with patch.dict("os.environ", {"NEURAL_LIVE_MODEL": "public-replay"}, clear=False), patch(
                "neural.live_eval_server.OLD_VALUE_MODEL_PATH", old_path
            ), patch("neural.live_eval_server.LIVE_PRIVATE_VALUE_MODEL_PATH", new_path), patch(
                "neural.live_eval_server.REPLAY_POLICY_MODEL_PATH", policy_path
            ):
                reset_model_caches()
                response = evaluate_with_model(self._payload())
        self.assertEqual(response["model_type"], "public-replay-value")
        self.assertEqual(response["fallback_reason"], "NEURAL_LIVE_MODEL=public-replay")

    def test_no_stale_move_labels_from_previous_active(self):
        payload = self._payload()
        payload.request["active"] = [{"moves": [{"move": "Petal Blizzard", "pp": 10, "maxpp": 10, "disabled": False}]}]
        payload.legal_actions = [
            {"kind": "move", "label": "Petal Blizzard", "index": 0},
            {"kind": "switch", "label": "Bulbasaur", "index": 8},
        ]
        labels = [candidate["label"] for candidate in legal_action_candidates(payload)]
        self.assertIn("move: Petal Blizzard", labels)
        self.assertNotIn("move: Thunderbolt", labels)

    def test_randbats_fallback_fills_missing_moves_as_inferred(self):
        index = {
            "zebstrika": [
                {
                    "species": "Zebstrika",
                    "moves": ["Thunderbolt", "Overheat"],
                    "items": ["Heavy-Duty Boots"],
                    "abilities": ["Sap Sipper"],
                    "tera_types": ["Electric"],
                    "weight": 1.0,
                }
            ]
        }
        with patch("neural.live_private_state.load_randbats_index", return_value=(index, "mock-sets", [])):
            private_state = extract_private_side_state(
                request_payload={
                    "side": {
                        "id": "p1",
                        "pokemon": [
                            {"ident": "p1: Zebstrika", "details": "Zebstrika, L80", "condition": "100/100", "active": True}
                        ],
                    },
                    "active": [{}],
                },
                legal_actions=[],
                player_hint="p1",
            )
        self.assertTrue(private_state["inferred_from_randbats"])
        self.assertTrue(all(move["inferred"] for move in private_state["active_moves"]))
        self.assertEqual(private_state["randbats_inference"]["source"], "mock-sets")

    def test_randbats_fallback_does_not_override_request_moves(self):
        index = {
            "zebstrika": [
                {
                    "species": "Zebstrika",
                    "moves": ["Overheat"],
                    "items": ["Heavy-Duty Boots"],
                    "abilities": ["Sap Sipper"],
                    "tera_types": ["Electric"],
                }
            ]
        }
        with patch("neural.live_private_state.load_randbats_index", return_value=(index, "mock-sets", [])):
            private_state = extract_private_side_state(
                request_payload={
                    "side": {
                        "id": "p1",
                        "pokemon": [
                            {"ident": "p1: Zebstrika", "details": "Zebstrika, L80", "condition": "100/100", "active": True}
                        ],
                    },
                    "active": [{"moves": [{"move": "Thunderbolt", "pp": 10, "maxpp": 10, "disabled": False}]}],
                },
                legal_actions=[],
                player_hint="p1",
            )
        self.assertEqual([move["name"] for move in private_state["active_moves"]], ["Thunderbolt"])
        self.assertTrue(private_state["active_moves"][0]["known_from_request"])

    def test_action_recommender_returns_legal_enabled_actions_first(self):
        payload = self._payload()
        payload.request["active"] = [{}]
        payload.legal_actions = [
            {"kind": "move", "label": "Thunderbolt", "index": 0, "disabled": True},
            {"kind": "switch", "label": "Bulbasaur", "index": 8, "disabled": False},
        ]
        report = recommend_actions(
            payload=payload,
            private_state={"player_side": "p1", "team": [], "active_moves": []},
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
        self.assertTrue(report["top_actions"])
        self.assertFalse(report["top_actions"][0]["disabled"])
        self.assertTrue(all(action["label"] in {"switch: Bulbasaur"} for action in report["top_actions"]))

    def test_action_recommender_does_not_synthesize_old_switch_indices(self):
        policy_model = PolicyValueMLP(input_size=31, hidden_sizes=[4], action_size=13)
        policy_model.eval()
        value_model = PolicyValueMLP(input_size=FEATURE_DIM, hidden_sizes=[4], action_size=13)
        value_model.eval()
        switch_species = ["Latias", "Regice", "Tornadus", "Iron Hands", "Alomomola"]
        payload = EvalRequest(
            room_id="battle-switch-index-test",
            url="https://play.pokemonshowdown.com/battle-switch-index-test",
            player="p1",
            log=[],
            request={
                "side": {
                    "id": "p1",
                    "pokemon": [
                        {"ident": "p1: Glimmora", "details": "Glimmora, L80", "condition": "100/100", "active": True},
                        *[
                            {
                                "ident": f"p1: {species}",
                                "details": f"{species}, L80",
                                "condition": "100/100",
                                "active": False,
                            }
                            for species in switch_species
                        ],
                    ],
                },
                "active": [{"moves": [{"move": f"Move {i + 1}", "pp": 10, "maxpp": 10, "disabled": False} for i in range(4)]}],
            },
            legal_actions=[
                *[{"kind": "move", "label": f"Move {i + 1}", "index": i} for i in range(4)],
                *[
                    {"kind": "switch", "label": species, "index": index}
                    for index, species in enumerate(switch_species, start=4)
                ],
            ],
        )
        private_state = {
            "player_side": "p1",
            "active_species": "Glimmora",
            "team": [
                {"species": "Glimmora", "active": True, "hp_fraction": 1.0, "moves": [f"Move {i + 1}" for i in range(4)]},
                *[
                    {"species": species, "active": False, "hp_fraction": 1.0, "moves": ["Recover"]}
                    for species in switch_species
                ],
            ],
            "active_moves": [{"name": f"Move {i + 1}", "disabled": False} for i in range(4)],
            "legal_actions": payload.legal_actions,
        }
        reset_model_caches()
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_ranker = Path(tmpdir) / "missing-ranker.pt"
            with patch("neural.live_action_recommender.DEFAULT_ACTION_RANKER_PATH", missing_ranker):
                report = recommend_actions(
                    payload=payload,
                    private_state=private_state,
                    opponent_belief={"opponents": []},
                    trajectory={"turns": []},
                    public_features=np.zeros(31, dtype=np.float32),
                    live_features=np.zeros(FEATURE_DIM, dtype=np.float32),
                    current_value=0.0,
                    value_model=value_model,
                    value_metadata={"uses_live_private_features": True},
                    policy_loader=lambda: (policy_model, {"input_size": 31, "path": "mock-policy.pt", "source": "public_replay_policy_31d"}),
                    device=torch.device("cpu"),
                    limit=9,
                )
        estimates = report["all_action_estimates"]
        labels = [row["label"] for row in estimates]
        indices = [row["index"] for row in estimates]
        switch_indices = [row["index"] for row in estimates if row["kind"] == "switch"]
        self.assertEqual(len(estimates), 9)
        self.assertEqual(len(set(labels)), len(labels))
        self.assertEqual(len(set(indices)), len(indices))
        self.assertEqual(switch_indices, [4, 5, 6, 7, 8])
        self.assertFalse(any(row["kind"] == "switch" and row["index"] in {9, 10, 11, 12} for row in estimates))

    def test_compare_replay_evals_writes_reports(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            old_path = root / "old.pt"
            new_path = root / "new.pt"
            replay_path = root / "fixture.log"
            out_dir = root / "reports"
            save_checkpoint(old_path, 31)
            save_checkpoint(new_path, FEATURE_DIM)
            replay_path.write_text(FIXTURE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
            report = compare_replay_evals(
                replay=str(replay_path),
                side="p1",
                old_checkpoint=old_path,
                new_checkpoint=new_path,
                output_dir=out_dir,
                replay_dir=root,
                trajectories_path=root / "missing.jsonl.gz",
            )
            self.assertGreater(report["turn_action_count"], 0)
            self.assertTrue((out_dir / "fixture_model_comparison.json").exists())
            self.assertTrue((out_dir / "fixture_model_comparison.md").exists())


if __name__ == "__main__":
    unittest.main()
