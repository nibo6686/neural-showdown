import unittest
from unittest.mock import patch

from neural.live_eval_server import EvalRequest, build_features_from_payload
from neural.live_opponent_beliefs import build_opponent_beliefs
from neural.live_private_state import extract_private_side_state
from neural.parse_replay_logs import parse_protocol_log


class LiveAnalysisTest(unittest.TestCase):
    def test_live_features_change_when_log_changes(self):
        payload_a = EvalRequest(
            room_id="room-a",
            url="https://play.pokemonshowdown.com/room-a",
            player="p1",
            log=[
                "|player|p1|Alice",
                "|player|p2|Bob",
                "|turn|1",
                "|move|p1a: Pikachu|Thunderbolt|p2a: Corviknight",
            ],
        )
        payload_b = EvalRequest(
            room_id="room-a",
            url="https://play.pokemonshowdown.com/room-a",
            player="p1",
            log=[
                "|player|p1|Alice",
                "|player|p2|Bob",
                "|turn|1",
                "|move|p1a: Pikachu|Thunderbolt|p2a: Corviknight",
                "|-damage|p2a: Corviknight|50/100",
            ],
        )

        features_a, debug_a = build_features_from_payload(payload_a)
        features_b, debug_b = build_features_from_payload(payload_b)

        self.assertEqual(features_a.shape[0], 31)
        self.assertEqual(features_b.shape[0], 31)
        self.assertTrue((features_a != features_b).any())
        self.assertEqual(debug_a["feature_version"], "public-replay-events-v1")
        self.assertEqual(debug_b["feature_version"], "public-replay-events-v1")

    def test_private_request_extraction_contains_own_full_info(self):
        request_payload = {
            "side": {
                "id": "p1",
                "pokemon": [
                    {
                        "ident": "p1: Toucannon",
                        "details": "Toucannon, L80, M",
                        "condition": "214/284",
                        "active": True,
                        "moves": ["Beak Blast", "U-turn", "Roost", "Boomburst"],
                        "item": "Heavy-Duty Boots",
                        "ability": "Skill Link",
                        "baseAbility": "Skill Link",
                        "teraType": "Normal",
                    }
                ],
            },
            "active": [
                {
                    "moves": [
                        {
                            "id": "beakblast",
                            "move": "Beak Blast",
                            "pp": 8,
                            "maxpp": 16,
                            "target": "normal",
                            "disabled": False,
                        },
                        {
                            "id": "uturn",
                            "move": "U-turn",
                            "pp": 20,
                            "maxpp": 20,
                            "target": "normal",
                            "disabled": False,
                        },
                    ]
                }
            ],
            "forceSwitch": [False],
        }
        legal_actions = [
            {"kind": "move", "label": "Beak Blast", "slot": 1, "disabled": False},
            {"kind": "move", "label": "U-turn", "slot": 2, "disabled": False},
        ]

        private_state = extract_private_side_state(
            request_payload=request_payload,
            legal_actions=legal_actions,
            player_hint="p1",
        )

        self.assertEqual(private_state["player_side"], "p1")
        self.assertEqual(private_state["active_species"], "Toucannon")
        self.assertEqual(private_state["team"][0]["item"], "Heavy-Duty Boots")
        self.assertEqual(private_state["team"][0]["ability"], "Skill Link")
        self.assertEqual(private_state["team"][0]["tera_type"], "Normal")
        self.assertEqual(private_state["active_moves"][0]["name"], "Beak Blast")
        self.assertEqual(private_state["active_moves"][1]["name"], "U-turn")

    def test_opponent_beliefs_filter_candidates(self):
        log_lines = [
            "|player|p1|Alice",
            "|player|p2|Bob",
            "|turn|1",
            "|switch|p2a: Corviknight|Corviknight, L80, M|100/100",
            "|move|p2a: Corviknight|Brave Bird|p1a: Pikachu",
            "|-terastallize|p2a: Corviknight|Water",
        ]
        trajectory = parse_protocol_log(log_lines, replay_id="room-b", format_name="gen9randombattle")

        index = {
            "corviknight": [
                {
                    "species": "Corviknight",
                    "role": "defensive",
                    "abilities": ["Pressure"],
                    "items": ["Leftovers"],
                    "moves": ["Brave Bird", "Roost", "U-turn", "Body Press"],
                    "tera_types": ["Water"],
                    "weight": 1.0,
                },
                {
                    "species": "Corviknight",
                    "role": "utility",
                    "abilities": ["Mirror Armor"],
                    "items": ["Rocky Helmet"],
                    "moves": ["Iron Defense", "Roost", "Body Press", "Taunt"],
                    "tera_types": ["Dragon"],
                    "weight": 1.0,
                },
            ]
        }

        with patch("neural.live_opponent_beliefs.load_randbats_index", return_value=(index, "mock", [])):
            beliefs = build_opponent_beliefs(
                protocol_log=log_lines,
                trajectory=trajectory,
                player_side="p1",
            )

        self.assertEqual(beliefs["source"], "mock")
        self.assertEqual(len(beliefs["opponents"]), 1)
        self.assertEqual(beliefs["opponents"][0]["species"], "Corviknight")
        self.assertEqual(beliefs["opponents"][0]["candidate_count"], 1)


if __name__ == "__main__":
    unittest.main()
