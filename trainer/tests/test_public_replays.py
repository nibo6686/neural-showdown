import gzip
import json
import tempfile
import unittest
import urllib.parse
from pathlib import Path

import numpy as np

from neural.build_replay_policy_dataset import build_public_replay_policy_dataset
from neural.build_replay_value_dataset import build_public_replay_value_dataset
from neural.parse_replay_logs import parse_protocol_log, parse_replay_logs
from neural.replay_fetch import (
    build_search_url,
    is_replay_downloaded,
    known_downloaded_ids,
    metadata_from_search_entry,
)


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "replay_sample.log"
REPO_ROOT = Path(__file__).resolve().parents[2]


class PublicReplayFetchTest(unittest.TestCase):
    def test_replay_search_url_construction(self):
        url = build_search_url("gen9randombattle", before=12345, base_endpoint="https://example.test/search.json")
        parsed = urllib.parse.urlparse(url)
        query = urllib.parse.parse_qs(parsed.query)
        self.assertEqual(parsed.scheme, "https")
        self.assertEqual(parsed.netloc, "example.test")
        self.assertEqual(parsed.path, "/search.json")
        self.assertEqual(query["format"], ["gen9randombattle"])
        self.assertEqual(query["before"], ["12345"])

    def test_replay_metadata_parsing(self):
        metadata = metadata_from_search_entry(
            {
                "id": "gen9randombattle-123",
                "format": "gen9randombattle",
                "uploadtime": 1712345678,
                "p1": "Alice",
                "p2": "Bob",
                "rating": 1500,
            },
            "gen9randombattle",
        )
        self.assertEqual(metadata["replay_id"], "gen9randombattle-123")
        self.assertEqual(metadata["format"], "gen9randombattle")
        self.assertEqual(metadata["players"]["p1"], "Alice")
        self.assertEqual(metadata["players"]["p2"], "Bob")
        self.assertEqual(metadata["rating"], 1500)
        self.assertTrue(metadata["source_url"].endswith("/gen9randombattle-123"))

    def test_duplicate_download_skip_logic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            (out_dir / "gen9randombattle-123.log").write_text("|win|Alice\n", encoding="utf-8")
            known = known_downloaded_ids(out_dir)
            self.assertTrue(is_replay_downloaded("gen9randombattle-123", out_dir, known))
            self.assertFalse(is_replay_downloaded("gen9randombattle-456", out_dir, known))


class PublicReplayParserTest(unittest.TestCase):
    def test_protocol_log_parser_extracts_battle_events(self):
        trajectory = parse_protocol_log(
            FIXTURE_PATH.read_text(encoding="utf-8").splitlines(),
            replay_id="fixture",
            format_name="gen9randombattle",
            source_path=str(FIXTURE_PATH),
        )
        self.assertEqual(trajectory["players"]["p1"], "Alice")
        self.assertEqual(trajectory["players"]["p2"], "Bob")
        self.assertEqual(trajectory["winner"], "Alice")
        self.assertEqual(trajectory["winner_side"], "p1")
        self.assertEqual(trajectory["total_turns"], 2)
        self.assertEqual(len(trajectory["move_actions"]["p1"]), 2)
        self.assertEqual(len(trajectory["move_actions"]["p2"]), 1)
        self.assertGreaterEqual(len(trajectory["switch_actions"]["p1"]), 1)
        self.assertEqual(len(trajectory["faint_events"]), 1)
        self.assertGreaterEqual(len(trajectory["damage_events"]), 3)
        self.assertEqual(len(trajectory["tera_events"]), 1)

    def test_value_dataset_builder_smoke_from_fixture(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            raw_dir = root / "raw"
            raw_dir.mkdir()
            (raw_dir / "fixture.log").write_text(FIXTURE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
            trajectories = root / "fixture_trajectories.jsonl.gz"
            parse_report = parse_replay_logs(
                format_name="gen9randombattle",
                replay_dir=raw_dir,
                output_path=trajectories,
                report_json_path=root / "parse_report.json",
                report_md_path=root / "parse_report.md",
            )
            self.assertEqual(parse_report["parsed_battles"], 1)

            output = root / "value.npz"
            value_report = build_public_replay_value_dataset(
                format_name="gen9randombattle",
                replay_dir=raw_dir,
                trajectories_path=trajectories,
                output_path=output,
                report_json_path=root / "value_report.json",
                report_md_path=root / "value_report.md",
            )
            self.assertEqual(value_report["parsed_battles"], 1)
            self.assertGreaterEqual(value_report["examples"], 2)
            self.assertEqual(value_report["p1_outcomes"]["win"], 1)
            with np.load(output) as data:
                self.assertEqual(data["states"].shape[1], value_report["feature_dim"])
                self.assertIn("public-replay-events-v1", str(data["feature_version"]))

    def test_policy_dataset_builder_stores_unmapped_labels(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            raw_dir = root / "raw"
            raw_dir.mkdir()
            (raw_dir / "fixture.log").write_text(FIXTURE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
            trajectories = root / "fixture_trajectories.jsonl.gz"
            parse_replay_logs(
                format_name="gen9randombattle",
                replay_dir=raw_dir,
                output_path=trajectories,
                report_json_path=root / "parse_report.json",
                report_md_path=root / "parse_report.md",
            )
            output = root / "policy.jsonl.gz"
            report = build_public_replay_policy_dataset(
                format_name="gen9randombattle",
                replay_dir=raw_dir,
                trajectories_path=trajectories,
                output_path=output,
                report_json_path=root / "policy_report.json",
                report_md_path=root / "policy_report.md",
            )
            self.assertGreater(report["examples"], 0)
            self.assertEqual(report["unmapped_action_percentage"], 100.0)
            with gzip.open(output, "rt", encoding="utf-8") as handle:
                first = json.loads(next(handle))
            self.assertIn("selected_action_label", first)
            self.assertFalse(first["mapped_to_fixed_head"])


class PublicReplayLauncherTest(unittest.TestCase):
    def test_launcher_exposes_replay_actions_and_parameters(self):
        script = (REPO_ROOT / "scripts" / "run_windows.ps1").read_text(encoding="utf-8")
        self.assertIn("fetch-replays", script)
        self.assertIn("parse-replays", script)
        self.assertIn("build-replay-value-dataset", script)
        self.assertIn("build-replay-policy-dataset", script)
        self.assertIn("$Format", script)
        self.assertIn("$MaxReplays", script)
        self.assertIn("$ReplayDir", script)
        self.assertIn("$DelaySec", script)


if __name__ == "__main__":
    unittest.main()
