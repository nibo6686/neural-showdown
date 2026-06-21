import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from neural.benchmark_vnext_featuregen import (
    _repeat_chain_enabled,
    _validate_supported_replay_team_sizes,
    _validate_full_preflight,
    _completed_teams_for_action_reconstruction,
    _context_for_prefix,
    _trajectory_prefix_before_event,
    benchmark_metadata,
    main,
    select_manifest_subset,
    validate_benchmark_arrays,
)
from neural.build_action_rank_dataset import _legal_actions_from_private_state
from neural.action_features import ACTION_FEATURE_NAMES_V5, ACTION_FEATURE_NAMES_V7
from neural.live_private_features import FEATURE_NAMES_V7
from neural.parse_replay_logs import parse_protocol_log
from neural.vnext_labels import chosen_action_label, match_chosen_action


def _entry(index, split):
    mechanics = {
        "tera": index % 2 == 0,
        "transform": index % 5 == 0,
        "tailwind": index % 7 == 0,
    }
    return {
        "replay_id": f"battle-{index}",
        "path": f"battle-{index}.log",
        "split": split,
        "profile_version": "replay-pool-profile-v1",
        "turn_count": 15 + index,
        "mechanics": mechanics,
    }


class VNextFeaturegenBenchmarkTest(unittest.TestCase):
    def setUp(self):
        entries = (
            [_entry(index, "train") for index in range(20)]
            + [_entry(100 + index, "validation") for index in range(10)]
            + [_entry(200 + index, "test") for index in range(10)]
        )
        self.manifest = {
            "manifest_version": "diagnostic-300-manifest-v1",
            "seed": 123,
            "catalog_checksum": "abc",
            "entries": entries,
        }

    def test_subset_selection_is_deterministic_and_split_preserving(self):
        first = select_manifest_subset(self.manifest, size=10, seed=9)
        second = select_manifest_subset(self.manifest, size=10, seed=9)
        self.assertEqual(first, second)
        self.assertEqual(len({row["replay_id"] for row in first}), 10)
        self.assertEqual(sum(row["split"] == "train" for row in first), 4)
        self.assertEqual(sum(row["split"] == "validation" for row in first), 3)
        self.assertEqual(sum(row["split"] == "test" for row in first), 3)

    def test_metadata_records_v7_v5_and_live_defaults(self):
        selected = select_manifest_subset(self.manifest, size=10, seed=9)
        metadata = benchmark_metadata(manifest=self.manifest, selected_entries=selected, seed=9)
        self.assertEqual(metadata["state_feature_version"], "live-private-belief-v7")
        self.assertEqual(metadata["state_feature_dim"], 3208)
        self.assertEqual(metadata["action_feature_version"], "legal-action-v5")
        self.assertEqual(metadata["action_feature_dim"], 318)
        self.assertEqual(len(metadata["state_feature_names_sha256"]), 64)
        self.assertEqual(len(metadata["action_feature_names_sha256"]), 64)
        self.assertEqual(metadata["live_default_state_feature_version"], "live-private-belief-v2")
        self.assertEqual(metadata["live_default_action_feature_version"], "legal-action-v3")

    def test_metadata_can_explicitly_select_v7_v6_without_changing_defaults(self):
        selected = select_manifest_subset(self.manifest, size=10, seed=9)
        metadata = benchmark_metadata(
            manifest=self.manifest,
            selected_entries=selected,
            seed=9,
            action_feature_version="legal-action-v6",
        )
        self.assertEqual(metadata["state_feature_version"], "live-private-belief-v7")
        self.assertEqual(metadata["action_feature_version"], "legal-action-v6")
        self.assertEqual(metadata["action_feature_dim"], 331)
        self.assertEqual(metadata["live_default_action_feature_version"], "legal-action-v3")
        self.assertFalse(metadata["state_vectors_duplicated_per_candidate"])

    def test_metadata_can_select_v7_with_exact_schema_guardrails(self):
        selected = select_manifest_subset(self.manifest, size=10, seed=9)
        metadata = benchmark_metadata(
            manifest=self.manifest,
            selected_entries=selected,
            seed=9,
            action_feature_version="legal-action-v7",
        )
        self.assertEqual(metadata["action_feature_version"], "legal-action-v7")
        self.assertEqual(metadata["action_feature_dim"], 552)
        self.assertEqual(
            metadata["action_feature_names_sha256"],
            "956da3d225ba9a22e05cfe774f6fa21efcbb77fa88267a8f96b1291701bf39d7",
        )
        arrays = {
            "state_features": np.zeros((1, 3208), dtype=np.float16),
            "action_features": np.zeros((1, 552), dtype=np.float16),
            "candidate_state_indices": np.asarray([0], dtype=np.int32),
            "state_value_targets": np.asarray([1.0], dtype=np.float32),
            "action_rank_labels": np.asarray([1], dtype=np.int8),
            "state_replay_ids": np.asarray([selected[0]["replay_id"]]),
            "state_splits": np.asarray([selected[0]["split"]]),
            "state_feature_names": np.asarray(FEATURE_NAMES_V7),
            "action_feature_names": np.asarray(ACTION_FEATURE_NAMES_V7),
        }
        self.assertTrue(validate_benchmark_arrays(arrays, metadata)["passed"])

    def test_cli_accepts_v7_without_running_materialization(self):
        with patch("neural.benchmark_vnext_featuregen.run_full_materialization") as materialize:
            main(["--full-manifest", "--action-feature-version", "legal-action-v7"])
        self.assertEqual(materialize.call_args.kwargs["action_feature_version"], "legal-action-v7")

    def test_cli_rejects_unknown_action_feature_version(self):
        with self.assertRaises(SystemExit):
            main(["--action-feature-version", "legal-action-v8"])

    def test_v6_and_v7_enable_the_same_repeat_chain_impact_path(self):
        self.assertFalse(_repeat_chain_enabled("legal-action-v5"))
        self.assertTrue(_repeat_chain_enabled("legal-action-v6"))
        self.assertTrue(_repeat_chain_enabled("legal-action-v7"))

    def test_array_validation_checks_dimensions_and_split_separation(self):
        selected = select_manifest_subset(self.manifest, size=10, seed=9)
        metadata = benchmark_metadata(manifest=self.manifest, selected_entries=selected, seed=9)
        arrays = {
            "state_features": np.zeros((2, 3208), dtype=np.float16),
            "action_features": np.zeros((3, 318), dtype=np.float16),
            "candidate_state_indices": np.asarray([0, 0, 1], dtype=np.int32),
            "state_value_targets": np.asarray([1.0, -1.0], dtype=np.float32),
            "action_rank_labels": np.asarray([1, 0, 1], dtype=np.int8),
            "state_replay_ids": np.asarray([selected[0]["replay_id"], selected[1]["replay_id"]]),
            "state_splits": np.asarray([selected[0]["split"], selected[1]["split"]]),
            "state_feature_names": np.asarray(FEATURE_NAMES_V7),
            "action_feature_names": np.asarray(ACTION_FEATURE_NAMES_V5),
        }
        self.assertTrue(validate_benchmark_arrays(arrays, metadata)["passed"])
        arrays["action_features"] = np.zeros((3, 317), dtype=np.float16)
        result = validate_benchmark_arrays(arrays, metadata)
        self.assertFalse(result["passed"])
        self.assertFalse(result["checks"]["action_dim_matches_schema"])

    def test_full_preflight_rejects_non_diagnostic_output(self):
        with self.assertRaises(ValueError):
            _validate_full_preflight(
                manifest=self.manifest,
                manifest_path=Path("artifacts/training_plan/manifests/diagnostic_300_manifest.json"),
                output_dir=Path("data/production"),
            )

    def test_completed_team_assigns_moves_to_active_species_not_actor_alias(self):
        switch = {"type": "switch", "side": "p1", "details": "Dugtrio-Alola, L84", "actor": "p1a: Dugtrio"}
        move = {"type": "move", "side": "p1", "actor": "p1a: Dugtrio", "move": "Stealth Rock"}
        trajectory = {"turns": [{"turn": 0, "events": [switch]}, {"turn": 1, "events": [move]}], "protocol_log": []}
        teams = _completed_teams_for_action_reconstruction(trajectory)
        self.assertIn("Stealth Rock", teams["p1"]["Dugtrio-Alola"]["moves"])
        self.assertNotIn("Dugtrio", teams["p1"])

    def test_per_battle_validation_rejects_custom_team_size(self):
        with self.assertRaisesRegex(ValueError, "frozen six-slot schema"):
            _validate_supported_replay_team_sizes(
                {"teamsize": {"p1": 24, "p2": 24}},
                replay_id="custom-24",
            )
        _validate_supported_replay_team_sizes(
            {"teamsize": {"p1": 6, "p2": 6}},
            replay_id="standard-six",
        )

    def test_pre_action_prefix_stops_before_same_decision_tera_event(self):
        tera = {"type": "tera", "side": "p1", "raw": "|-terastallize|p1a: X|Ghost"}
        move = {"type": "move", "side": "p1", "move": "Shadow Ball", "raw": "|move|p1a: X|Shadow Ball|p2a: Y"}
        trajectory = {
            "turns": [{"turn": 1, "events": [tera, move]}],
            "protocol_log": ["|turn|1", tera["raw"], move["raw"]],
        }
        prefix = _trajectory_prefix_before_event(
            trajectory, turn_number=1, event=move, turn_events=[tera, move]
        )
        self.assertNotIn(tera["raw"], prefix["protocol_log"])

    def _replay_decision(self, replay_id, raw_command, *, side=None):
        path = Path("data/replays/raw/gen9randombattle") / f"{replay_id}.log"
        trajectory = parse_protocol_log(
            path.read_text(encoding="utf-8").splitlines(),
            replay_id=replay_id,
            source_path=str(path),
        )
        completed = _completed_teams_for_action_reconstruction(trajectory)
        for turn in trajectory["turns"]:
            events = turn.get("events", [])
            for event in events:
                if event.get("raw") == raw_command and (side is None or event.get("side") == side):
                    prefix = _trajectory_prefix_before_event(
                        trajectory=trajectory,
                        turn_number=int(turn["turn"]),
                        event=event,
                        turn_events=events,
                    )
                    _, private_state, opponent_belief, _ = _context_for_prefix(
                        trajectory=trajectory,
                        prefix=prefix,
                        side=event["side"],
                        through_turn=int(turn["turn"]),
                        completed_teams=completed,
                        sets_path=None,
                    )
                    actions = _legal_actions_from_private_state(private_state, "")
                    return {
                        "trajectory": trajectory,
                        "completed": completed,
                        "event": event,
                        "turn_events": events,
                        "private_state": private_state,
                        "opponent_belief": opponent_belief,
                        "label": chosen_action_label(event, turn_events=events),
                        "actions": actions,
                    }
        self.fail(f"Replay command not found: {raw_command}")

    def test_top_replay_support_move_survives_struggle_slot_pressure(self):
        decision = self._replay_decision(
            "gen9randombattle-2592785310",
            "|move|p2a: Gholdengo|Thunder Wave|p1a: Registeel",
            side="p2",
        )
        self.assertEqual(decision["label"], "move: Thunder Wave")
        self.assertIn("Thunder Wave", [move["name"] for move in decision["private_state"]["active_moves"]])
        self.assertNotIn("Struggle", [move["name"] for move in decision["private_state"]["active_moves"]])
        self.assertIsNotNone(match_chosen_action(decision["actions"], decision["label"]))

    def test_battle_form_switch_target_matches_roster_slot(self):
        decision = self._replay_decision(
            "gen9randombattle-2587967313",
            "|drag|p2a: Terapagos|Terapagos-Terastal, L77, F|239/273",
            side="p2",
        )
        self.assertEqual(decision["label"], "switch: Terapagos-Terastal")
        self.assertIn("switch: Terapagos", [action["label"] for action in decision["actions"]])
        self.assertIsNotNone(match_chosen_action(decision["actions"], decision["label"]))

    def test_roster_aliases_keep_sixth_switch_target_available(self):
        decision = self._replay_decision(
            "gen9randombattle-2589411985",
            "|switch|p2a: Glalie|Glalie, L96, F|309/309|[from] Volt Switch",
            side="p2",
        )
        self.assertEqual(decision["label"], "switch: Glalie")
        self.assertIn("switch: Glalie", [action["label"] for action in decision["actions"]])
        self.assertIsNotNone(match_chosen_action(decision["actions"], decision["label"]))

    def test_revival_blessing_heal_restores_switch_legality(self):
        decision = self._replay_decision(
            "gen9randombattle-2592073212",
            "|switch|p2a: Venomoth|Venomoth, L84, M|127/255",
            side="p2",
        )
        self.assertEqual(decision["label"], "switch: Venomoth")
        self.assertIn("switch: Venomoth", [action["label"] for action in decision["actions"]])
        self.assertIsNotNone(match_chosen_action(decision["actions"], decision["label"]))

    def test_public_illusion_replace_updates_active_identity(self):
        decision = self._replay_decision(
            "gen9randombattle-2591469202",
            "|move|p2a: Zoroark|Sludge Bomb|p1a: Chansey",
            side="p2",
        )
        self.assertEqual(decision["private_state"]["active_species"], "Zoroark")
        self.assertIn("Sludge Bomb", [move["name"] for move in decision["private_state"]["active_moves"]])
        self.assertIsNotNone(match_chosen_action(decision["actions"], decision["label"]))

    def test_public_illusion_replace_restores_true_bench_switch(self):
        decision = self._replay_decision(
            "gen9randombattle-2591469202",
            "|switch|p2a: Staraptor|Staraptor, L79, F|263/263",
            side="p2",
        )
        self.assertEqual(decision["private_state"]["active_species"], "Zoroark")
        self.assertIn("switch: Staraptor", [action["label"] for action in decision["actions"]])
        self.assertIsNotNone(match_chosen_action(decision["actions"], decision["label"]))

    def test_move_tera_candidate_reconstructed_without_chosen_injection(self):
        decision = self._replay_decision(
            "gen9randombattle-2589811158",
            "|move|p2a: Glaceon|Wish|p2a: Glaceon",
            side="p2",
        )
        self.assertEqual(decision["label"], "move_tera: Wish")
        self.assertIn("move_tera: Wish", [action["label"] for action in decision["actions"]])
        self.assertIsNotNone(match_chosen_action(decision["actions"], decision["label"]))

    def test_struggle_is_exhaustion_candidate_without_displacing_real_moves(self):
        decision = self._replay_decision(
            "gen9randombattle-2587977426",
            "|move|p2a: Lapras|Struggle|p1a: Phione",
            side="p2",
        )
        self.assertEqual(decision["label"], "move: Struggle")
        active_moves = [move["name"] for move in decision["private_state"]["active_moves"]]
        self.assertEqual(active_moves, ["Freeze-Dry", "Rest", "Sleep Talk", "Sparkling Aria"])
        self.assertIn("move: Struggle", [action["label"] for action in decision["actions"]])
        self.assertIsNotNone(match_chosen_action(decision["actions"], decision["label"]))

    def test_no_chosen_action_injection_or_illusion_move_leakage(self):
        decision = self._replay_decision(
            "gen9randombattle-2591469202",
            "|move|p2a: Staraptor|Sludge Bomb|p1a: Chansey",
            side="p2",
        )
        self.assertEqual(decision["label"], "move: Sludge Bomb")
        self.assertIsNone(match_chosen_action(decision["actions"], decision["label"]))
        self.assertNotIn("move: Sludge Bomb", [action["label"] for action in decision["actions"]])

        path = Path("data/replays/raw/gen9randombattle/gen9randombattle-2591469202.log")
        trajectory = parse_protocol_log(
            path.read_text(encoding="utf-8").splitlines(),
            replay_id="gen9randombattle-2591469202",
            source_path=str(path),
        )
        completed = _completed_teams_for_action_reconstruction(trajectory)
        turn = next(row for row in trajectory["turns"] if int(row["turn"]) == 1)
        event = next(row for row in turn["events"] if row.get("raw") == "|move|p2a: Staraptor|Sludge Bomb|p1a: Chansey")
        prefix = _trajectory_prefix_before_event(
            trajectory=trajectory,
            turn_number=1,
            event=event,
            turn_events=turn["events"],
        )
        _, _, opponent_belief, _ = _context_for_prefix(
            trajectory=trajectory,
            prefix=prefix,
            side="p1",
            through_turn=1,
            completed_teams=completed,
            sets_path=None,
        )
        self.assertNotIn("Sludge Bomb", json.dumps(opponent_belief))

    def test_ditto_transform_exposes_current_stint_copied_move(self):
        decision = self._replay_decision(
            "gen9randombattle-2589571474",
            "|move|p1a: Ditto|Thunder Wave|p2a: Virizion",
            side="p1",
        )
        self.assertEqual(decision["label"], "move: Thunder Wave")
        self.assertEqual(decision["private_state"]["active_species"], "Ditto")
        names = [move["name"] for move in decision["private_state"]["active_moves"]]
        self.assertIn("Thunder Wave", names)
        self.assertIsNotNone(match_chosen_action(decision["actions"], decision["label"]))

    def test_ditto_transform_excludes_future_transform_stint_move(self):
        decision = self._replay_decision(
            "gen9randombattle-2589571474",
            "|move|p1a: Ditto|Thunder Wave|p2a: Virizion",
            side="p1",
        )
        names = [move["name"] for move in decision["private_state"]["active_moves"]]
        # Leaf Blade is copied during a later Virizion Transform stint after the
        # decision and must not contaminate the current Sableye stint.
        self.assertNotIn("Leaf Blade", names)

    def test_transform_copied_moves_do_not_merge_across_stints(self):
        decision = self._replay_decision(
            "gen9randombattle-2589571474",
            "|move|p1a: Ditto|Brave Bird|p2a: Ho-Oh",
            side="p1",
        )
        names = [move["name"] for move in decision["private_state"]["active_moves"]]
        # Ho-Oh stint exposes its own copied moves only, never moves copied during
        # the later Sableye or Virizion stints.
        self.assertIn("Brave Bird", names)
        self.assertNotIn("Thunder Wave", names)
        self.assertNotIn("Leaf Blade", names)
        self.assertIsNotNone(match_chosen_action(decision["actions"], decision["label"]))

    def test_transform_copied_moves_not_globally_backfilled_into_species(self):
        decision = self._replay_decision(
            "gen9randombattle-2589571474",
            "|move|p1a: Ditto|Thunder Wave|p2a: Virizion",
            side="p1",
        )
        ditto_moves = set(decision["completed"]["p1"].get("Ditto", {}).get("moves", set()))
        # Copied opponent moves must not be backfilled into Ditto's global moveset.
        for copied in ("Thunder Wave", "Brave Bird", "Leaf Blade", "Knock Off"):
            self.assertNotIn(copied, ditto_moves)


class GeneralizedFullPreflightTest(unittest.TestCase):
    def _manifest(self, counts, *, shared_path, split_targets=None, dup=False, overlap=False):
        entries = []
        idx = 0
        for split, count in counts.items():
            for _ in range(count):
                entries.append(
                    {
                        "replay_id": f"b{idx}",
                        "path": str(shared_path),
                        "split": split,
                        "profile_version": "replay-pool-profile-v1",
                        "mechanics": {},
                    }
                )
                idx += 1
        if dup:
            entries.append(dict(entries[0]))
        if overlap:
            clone = dict(entries[0])
            clone["split"] = "test" if entries[0]["split"] != "test" else "train"
            entries.append(clone)
        return {
            "manifest_version": "test-manifest",
            "seed": 1,
            "catalog_checksum": "x",
            "split_targets": split_targets,
            "entries": entries,
        }

    def _preflight(self, tmp, manifest, output_name="ds"):
        from neural.benchmark_vnext_featuregen import _validate_full_preflight

        manifest_path = tmp / "manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        return _validate_full_preflight(
            manifest=manifest,
            manifest_path=manifest_path,
            output_dir=tmp / output_name,
        )

    def test_accepts_300_split_targets(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            shared = tmp / "r.log"
            shared.write_text("x", encoding="utf-8")
            manifest = self._manifest(
                {"train": 210, "validation": 45, "test": 45},
                shared_path=shared,
                split_targets={"train": 210, "validation": 45, "test": 45},
            )
            result = self._preflight(tmp, manifest)
        self.assertTrue(all(result["checks"].values()), result["checks"])
        self.assertEqual(result["expected_total_battles"], 300)

    def test_accepts_1000_action_rank_splits(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            shared = tmp / "r.log"
            shared.write_text("x", encoding="utf-8")
            manifest = self._manifest(
                {"train": 700, "validation": 150, "test": 150},
                shared_path=shared,
                split_targets={"train": 700, "validation": 150, "test": 150},
            )
            # A non-diagnostic_300 output directory must be accepted.
            result = self._preflight(tmp, manifest, output_name="diagnostic_1000_action_rank_v7_v5")
        self.assertTrue(all(result["checks"].values()), result["checks"])
        self.assertEqual(result["expected_total_battles"], 1000)
        self.assertEqual(result["split_counts"], {"train": 700, "validation": 150, "test": 150})

    def test_rejects_duplicate_battle_ids(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            shared = tmp / "r.log"
            shared.write_text("x", encoding="utf-8")
            manifest = self._manifest(
                {"train": 4, "validation": 3, "test": 3},
                shared_path=shared,
                split_targets={"train": 4, "validation": 3, "test": 3},
                dup=True,
            )
            with self.assertRaisesRegex(ValueError, "preflight failed"):
                self._preflight(tmp, manifest)

    def test_rejects_split_overlap(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            shared = tmp / "r.log"
            shared.write_text("x", encoding="utf-8")
            manifest = self._manifest(
                {"train": 4, "validation": 3, "test": 3},
                shared_path=shared,
                split_targets={"train": 4, "validation": 3, "test": 3},
                overlap=True,
            )
            with self.assertRaisesRegex(ValueError, "preflight failed"):
                self._preflight(tmp, manifest)

    def test_rejects_missing_replay_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            manifest = self._manifest(
                {"train": 4, "validation": 3, "test": 3},
                shared_path=tmp / "does_not_exist.log",
                split_targets={"train": 4, "validation": 3, "test": 3},
            )
            with self.assertRaisesRegex(ValueError, "preflight failed"):
                self._preflight(tmp, manifest)

    def test_rejects_wrong_split_counts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            shared = tmp / "r.log"
            shared.write_text("x", encoding="utf-8")
            # Entries do not match the declared split targets.
            manifest = self._manifest(
                {"train": 209, "validation": 45, "test": 45},
                shared_path=shared,
                split_targets={"train": 210, "validation": 45, "test": 45},
            )
            with self.assertRaisesRegex(ValueError, "preflight failed"):
                self._preflight(tmp, manifest)

    def test_rejects_replay_with_team_size_above_frozen_six_slots(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            shared = tmp / "r.log"
            shared.write_text(
                "|teamsize|p1|24\n|teamsize|p2|24\n|turn|1\n",
                encoding="utf-8",
            )
            manifest = self._manifest(
                {"train": 2, "validation": 1, "test": 1},
                shared_path=shared,
                split_targets={"train": 2, "validation": 1, "test": 1},
            )
            with self.assertRaisesRegex(ValueError, "unsupported_team_sizes"):
                self._preflight(tmp, manifest)


class FullMaterializationResumeTest(unittest.TestCase):
    def test_combines_from_existing_shards_without_simcore(self):
        import pickle

        from neural.action_features import ACTION_FEATURE_DIM_V5
        from neural.benchmark_vnext_featuregen import (
            FEATURE_DIM_V7,
            _shard_path,
            run_full_materialization,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            shared = tmp / "r.log"
            shared.write_text("x", encoding="utf-8")
            splits = ["train", "train", "validation", "test"]
            entries = [
                {
                    "replay_id": f"b{i}",
                    "path": str(shared),
                    "split": splits[i],
                    "profile_version": "replay-pool-profile-v1",
                    "mechanics": {},
                }
                for i in range(4)
            ]
            manifest = {
                "manifest_version": "test",
                "seed": 1,
                "catalog_checksum": "x",
                "split_targets": {"train": 2, "validation": 1, "test": 1},
                "entries": entries,
            }
            manifest_path = tmp / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            output_dir = tmp / "diagnostic_test_v7_v5"
            shards_dir = output_dir / "_shards"
            shards_dir.mkdir(parents=True)

            # Pre-seed every shard so no sim-core worker is spawned (resume path).
            for i, entry in enumerate(entries):
                result = {
                    "replay_id": entry["replay_id"],
                    "split": entry["split"],
                    "state_rows": np.zeros((1, FEATURE_DIM_V7), dtype=np.float16),
                    "state_turns": [1],
                    "state_sides": ["p1"],
                    "state_value_targets": [1.0 if i % 2 == 0 else -1.0],
                    "action_rows": np.zeros((2, ACTION_FEATURE_DIM_V5), dtype=np.float16),
                    "candidate_local_state_indices": [0, 0],
                    "candidate_action_indices": [0, 1],
                    "candidate_kinds": ["move", "switch"],
                    "observed_actions": [1, 0],
                    "label_counts": {
                        "state_value_labels": 1,
                        "chosen_action_matched": 1,
                        "action_rank_positive": 1,
                        "action_rank_unchosen": 1,
                    },
                    "impact_methods": {},
                    "skip_audit": [],
                    "unmatched_audit": [],
                    "failure": None,
                    "valid": True,
                }
                with open(_shard_path(shards_dir, entry["replay_id"]), "wb") as handle:
                    pickle.dump(result, handle)

            report = run_full_materialization(
                manifest_path=manifest_path,
                output_dir=output_dir,
                workers=1,
                resume=True,
            )

            self.assertTrue(report["validation"]["passed"], report["validation"]["checks"])
            self.assertEqual(report["decision_states"], 4)
            self.assertEqual(report["legal_action_candidates"], 8)
            self.assertEqual(report["split_battle_counts"], {"train": 2, "validation": 1, "test": 1})
            self.assertEqual(report["action_value_labels_generated"], 0)
            self.assertTrue((output_dir / "diagnostic_test_v7_v5.npz").exists())
            # Report filename drops the schema suffix, matching the repo convention.
            self.assertTrue((output_dir / "diagnostic_test_materialization_report.md").exists())


if __name__ == "__main__":
    unittest.main()
