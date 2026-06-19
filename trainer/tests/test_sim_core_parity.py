import json
import os
import unittest
from pathlib import Path

from neural.damage_engine import estimate_damage
from neural.env_client import SimCoreClient
from neural.parse_replay_logs import parse_protocol_log


REPO_ROOT = Path(__file__).resolve().parents[2]
REPLAY_DIR = REPO_ROOT / "data" / "replays" / "raw" / "gen9randombattle"


class SimCoreRpcParityTest(unittest.TestCase):
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

    def test_seeded_reset_is_deterministic_and_player_views_are_private(self):
        players = {"p1": {"controller": "external"}, "p2": {"controller": "external"}}
        env1 = self.client.create_env("gen9randombattle", [101, 202, 303, 404], players)
        env2 = self.client.create_env("gen9randombattle", [101, 202, 303, 404], players)
        try:
            first = self.client.reset(env1)
            second = self.client.reset(env2)
            first_team = [pokemon["species"] for pokemon in first["views"]["p1"]["self_team"]]
            second_team = [pokemon["species"] for pokemon in second["views"]["p1"]["self_team"]]
            self.assertEqual(first_team, second_team)

            opponent = first["views"]["p1"]["opponent_team"]
            self.assertTrue(opponent)
            for pokemon in opponent:
                self.assertEqual(pokemon["moves"], [])
                self.assertEqual(pokemon["revealed_moves"], [])
                self.assertIsNone(pokemon["ability"])
                self.assertIsNone(pokemon["tera_type"])

            request = first["requests"]["p1"]
            self.assertEqual(len(request["legal_actions"]["mask"]), 13)
            self.assertTrue(request["side"][0]["moves"])
            self.assertIsNotNone(request["side"][0]["item"])
            self.assertIsNotNone(request["side"][0]["ability"])
            self.assertIsNotNone(request["side"][0]["tera_type"])
        finally:
            self.client.close_env(env1)
            self.client.close_env(env2)

    def test_damage_rpc_uses_smogon_calc_without_fallback(self):
        cases = [
            ("Pikachu", "Mew", "Thunderbolt", None),
            ("Pikachu", "Gyarados", "Thunderbolt", 4.0),
            ("Pikachu", "Magnezone", "Thunderbolt", 0.5),
            ("Pikachu", "Golem", "Thunderbolt", 0.0),
            ("Pelipper", "Arcanine", "Surf", 2.0),
        ]
        for attacker, defender, move, effectiveness in cases:
            with self.subTest(attacker=attacker, defender=defender, move=move):
                result = self.client.damage_estimate(
                    {
                        "attacker": {"species": attacker, "level": 80},
                        "defender": {"species": defender, "level": 80, "hp_fraction": 1.0},
                        "move": move,
                    }
                )
                self.assertEqual(result["damage_method"], "smogon_calc")
                self.assertNotIn("heuristic_fallback", json.dumps(result))
                self.assertLessEqual(result["min_percent"], result["max_percent"])
                if effectiveness is not None:
                    self.assertEqual(result["type_effectiveness"], effectiveness)

    def test_python_damage_path_matches_rpc_range(self):
        request = {
            "attacker": {"species": "Garchomp", "level": 80, "item": "Choice Band"},
            "defender": {"species": "Blissey", "level": 80, "hp_fraction": 1.0},
            "move": "Earthquake",
        }
        rpc = self.client.damage_estimate(request)
        direct = estimate_damage(**request)
        self.assertEqual(rpc["damage_method"], "smogon_calc")
        self.assertEqual(direct["damage_method"], "smogon_calc")
        self.assertAlmostEqual(rpc["min_percent"], direct["min_percent"], places=6)
        self.assertAlmostEqual(rpc["max_percent"], direct["max_percent"], places=6)

    def test_exact_stats_change_rpc_damage_and_set_diagnostics(self):
        low = self.client.damage_estimate(
            {
                "attacker": {"species": "Mew", "level": 80, "stats": {"spa": 50}},
                "defender": {"species": "Mew", "level": 80, "stats": {"spd": 500, "hp": 400}},
                "move": "Aura Sphere",
            }
        )
        high = self.client.damage_estimate(
            {
                "attacker": {"species": "Mew", "level": 80, "stats": {"spa": 500}},
                "defender": {"species": "Mew", "level": 80, "stats": {"spd": 50, "hp": 400}},
                "move": "Aura Sphere",
            }
        )
        self.assertGreater(high["min_percent"], low["max_percent"])
        self.assertTrue(low["used_exact_attacker_stats"])
        self.assertTrue(low["used_exact_defender_stats"])
        self.assertEqual(low["damage_method"], "smogon_calc")
        self.assertNotIn("heuristic_fallback", json.dumps([low, high]))


class PublicReplaySanityTest(unittest.TestCase):
    def test_saved_replays_reproduce_public_event_prefixes_but_have_no_private_seed(self):
        paths = sorted(REPLAY_DIR.glob("*.log"))[:5]
        self.assertGreaterEqual(len(paths), 3)
        for path in paths:
            with self.subTest(replay=path.name):
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
                trace = parse_protocol_log(
                    lines,
                    replay_id=path.stem,
                    format_name="gen9randombattle",
                    source_path=str(path),
                )
                raw_moves = [line for line in lines if line.startswith("|move|")]
                raw_switches = [line for line in lines if line.startswith("|switch|") or line.startswith("|drag|")]
                raw_damage = [line for line in lines if line.startswith("|-damage|")]
                self.assertEqual(sum(len(value) for value in trace["move_actions"].values()), len(raw_moves))
                self.assertEqual(sum(len(value) for value in trace["switch_actions"].values()), len(raw_switches))
                self.assertEqual(len(trace["damage_events"]), len(raw_damage))
                self.assertEqual(trace["line_count"], len([line for line in lines if line]))
                self.assertFalse(any(line.startswith(">start ") for line in lines))
                self.assertFalse(any(line.startswith("|request|") for line in lines))
                self.assertNotIn("seed", trace)

    def test_winner_side_survives_post_battle_player_disconnect_lines(self):
        trace = parse_protocol_log(
            [
                "|player|p1|Alice|1|",
                "|player|p2|Bob|2|",
                "|turn|1",
                "|win|Bob",
                "|player|p2|",
            ],
            replay_id="disconnect-after-win",
            format_name="gen9randombattle",
        )
        self.assertEqual(trace["winner_side"], "p2")
        self.assertEqual(trace["winner_status"], "known")
        self.assertTrue(trace["winner_known"])


if __name__ == "__main__":
    unittest.main()
