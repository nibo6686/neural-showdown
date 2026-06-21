import json
import tempfile
import unittest
from pathlib import Path

from neural.replay_pool_profiler import extract_replay_profile
from neural.replay_sample_manifest import (
    generate_diagnostic_manifest,
    validate_manifest,
)


SYNTHETIC_LOG = """|player|p1|Alice|
|player|p2|Bob|
|teamsize|p1|6
|teamsize|p2|6
|switch|p1a: Pikachu|Pikachu, L80|100/100
|switch|p2a: Garchomp|Garchomp, L80|100/100
|turn|1
|-terastallize|p1a: Pikachu|Flying
|-boost|p1a: Pikachu|atk|1
|-status|p2a: Garchomp|brn
|-enditem|p2a: Garchomp|Leftovers
|-weather|RainDance
|-fieldstart|move: Electric Terrain
|-sidestart|p2: Bob|move: Stealth Rock
|-start|p2a: Garchomp|move: Encore
|-start|p2a: Garchomp|Disable
|-start|p2a: Garchomp|move: Taunt
|-mustrecharge|p1a: Pikachu
|turn|5
|win|Alice
"""


class ReplayPoolProfilerTest(unittest.TestCase):
    def test_synthetic_log_extracts_metadata_and_mechanics(self):
        row = extract_replay_profile(
            SYNTHETIC_LOG,
            replay_id="fixture",
            path=Path("fixture.log"),
            metadata={"format": "[Gen 9] Random Battle", "rating": 1500},
            replay_json={
                "uploadtime": 1712345678,
                "inputlog": ">p1 move thunderbolt\n>p2 switch 2\n",
            },
        )
        self.assertEqual(row["players"], {"p1": "Alice", "p2": "Bob"})
        self.assertEqual(row["winner"], "Alice")
        self.assertEqual(row["turn_count"], 5)
        self.assertEqual(row["approx_decision_state_count"], 2)
        for flag in (
            "tera", "boosts_drops", "major_status", "item_reveal_loss",
            "weather", "terrain", "hazards", "encore", "disable", "taunt",
            "recharge_lock_constraints",
        ):
            self.assertTrue(row["mechanics"][flag], flag)

    def test_missing_metadata_is_graceful(self):
        row = extract_replay_profile(
            "|turn|1\n|move|p1a: A|Tackle|p2a: B\n",
            replay_id="missing",
            path=Path("missing.log"),
        )
        self.assertIsNone(row["format"])
        self.assertIsNone(row["rating"])
        self.assertIsNone(row["winner"])
        self.assertFalse(row["eligible_diagnostic_300"])

    def test_illusion_rule_and_timer_countdown_are_not_event_evidence(self):
        row = extract_replay_profile(
            "|rule|Illusion Level Mod: Illusion disguises the Pokemon's true level\n"
            "|inactive|Battle timer is ON: inactive players will automatically lose.\n"
            "|inactive|Alice has 30 seconds left.\n|turn|5\n|win|Alice\n",
            replay_id="no-illusion",
            path=Path("no-illusion.log"),
            metadata={"format": "gen9randombattle"},
            replay_json={"inputlog": ">p1 move tackle\n"},
        )
        self.assertFalse(row["mechanics"]["illusion"])
        self.assertFalse(row["early_forfeit_or_short"])

    def test_custom_team_size_above_six_is_not_diagnostic_eligible(self):
        row = extract_replay_profile(
            "|teamsize|p1|24\n|teamsize|p2|24\n|turn|5\n|win|Alice\n",
            replay_id="custom-24",
            path=Path("custom-24.log"),
            metadata={"format": "gen9randombattle"},
            replay_json={"inputlog": ">p1 move tackle\n"},
        )
        self.assertEqual(row["team_sizes"], {"p1": 24, "p2": 24})
        self.assertFalse(row["eligible_diagnostic_300"])


def _catalog_row(root: Path, index: int) -> dict:
    path = root / f"battle-{index}.log"
    path.write_text("|turn|5\n|win|Alice\n", encoding="utf-8")
    mechanics = {
        "tera": index % 2 == 0,
        "boosts_drops": index % 3 == 0,
        "major_status": index % 4 == 0,
        "item_reveal_loss": index % 5 == 0,
        "ability_reveal_change_suppression": index % 7 == 0,
        "type_change": index % 11 == 0,
        "transform": index % 31 == 0,
        "illusion": index % 29 == 0,
        "weather": index % 6 == 0,
        "terrain": index % 8 == 0,
        "screens": index % 9 == 0,
        "tailwind": index % 10 == 0,
        "hazards": index % 3 == 0,
        "recharge_lock_constraints": index % 13 == 0,
        "encore": index % 17 == 0,
        "disable": index % 19 == 0,
        "taunt": index % 23 == 0,
        "choice_like_constraints": index % 27 == 0,
    }
    return {
        "profile_version": "replay-pool-profile-v1",
        "replay_id": f"battle-{index}",
        "path": str(path),
        "format_normalized": "gen9randombattle",
        "rating": 1000 + index,
        "upload_time": 1700000000 + index,
        "turn_count": 10 + index % 30,
        "approx_decision_state_count": 20,
        "long_game": index % 5 == 0,
        "close_game_proxy": index % 7 == 0,
        "parse_error": False,
        "eligible_diagnostic_300": True,
        "mechanics": mechanics,
    }


class ReplaySampleManifestTest(unittest.TestCase):
    def test_manifest_is_unique_split_and_deterministic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            catalog = root / "catalog.jsonl"
            rows = [_catalog_row(root, index) for index in range(400)]
            catalog.write_text(
                "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
                encoding="utf-8",
            )
            first, first_report = generate_diagnostic_manifest(
                catalog_path=catalog,
                output_path=root / "first.json",
                seed=123,
            )
            second, second_report = generate_diagnostic_manifest(
                catalog_path=catalog,
                output_path=root / "second.json",
                seed=123,
            )
            self.assertTrue(first_report["passed"])
            self.assertTrue(second_report["passed"])
            self.assertEqual(first["entries"], second["entries"])
            self.assertEqual(len({row["replay_id"] for row in first["entries"]}), 300)
            self.assertEqual(
                {"train": 210, "validation": 45, "test": 45},
                first_report["split_counts"],
            )
            self.assertTrue(validate_manifest(first, rows)["passed"])


if __name__ == "__main__":
    unittest.main()
