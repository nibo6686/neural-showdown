import unittest

from neural.featurize import GLOBAL_DIM, POKEMON_DIM, REQUEST_DIM, featurize_battle


def sample_result():
    view = {
        "env_id": "env-1",
        "format": "gen9randombattle",
        "gen": 9,
        "turn": 3,
        "player": "p1",
        "opponent": "p2",
        "terminated": False,
        "winner": None,
        "names": {"p1": "Agent-1", "p2": "Agent-2"},
        "team_size": {"p1": 6, "p2": 6},
        "active": {"self": 0, "opponent": 0},
        "field": {
            "weather": None,
            "terrain": None,
            "pseudo_weather": [],
            "side_conditions": {"self": {}, "opponent": {"stealthrock": 1}},
        },
        "self_team": [
            {
                "slot": 1,
                "ident": "p1: Typhlosion",
                "name": "Typhlosion",
                "species": "Typhlosion",
                "details": "Typhlosion, L84, M",
                "active": True,
                "fainted": False,
                "hp_text": "267/267",
                "hp_ratio": 1.0,
                "status": None,
                "gender": "M",
                "level": 84,
                "item": "choicescarf",
                "ability": "flashfire",
                "base_ability": "flashfire",
                "moves": ["fireblast", "eruption", "focusblast", "scorchingsands"],
                "revealed_moves": ["Fire Blast", "Eruption", "Focus Blast", "Scorching Sands"],
                "types": ["Fire"],
                "tera_type": "Fire",
                "terastallized": False,
                "stats": {"atk": 146, "def": 179, "spa": 231, "spd": 191, "spe": 216},
                "boosts": {},
                "volatiles": [],
                "possible_roles": [],
                "possible_moves": [],
                "possible_abilities": [],
                "possible_tera_types": [],
            }
        ],
        "opponent_team": [
            {
                "slot": 1,
                "ident": "p2a: Gliscor",
                "name": "Gliscor",
                "species": "Gliscor",
                "details": "Gliscor, L76, M",
                "active": True,
                "fainted": False,
                "hp_text": "100/100",
                "hp_ratio": 1.0,
                "status": None,
                "gender": "M",
                "level": 76,
                "item": None,
                "ability": None,
                "base_ability": None,
                "moves": [],
                "revealed_moves": ["Earthquake"],
                "types": ["Ground", "Flying"],
                "tera_type": None,
                "terastallized": False,
                "stats": {},
                "boosts": {},
                "volatiles": [],
                "possible_roles": [],
                "possible_moves": [],
                "possible_abilities": [],
                "possible_tera_types": [],
            }
        ],
    }
    request = {
        "player": "p1",
        "wait": False,
        "team_preview": False,
        "force_switch": False,
        "trapped": False,
        "rqid": 1,
        "active": {
            "moves": [
                {
                    "slot": 1,
                    "move": "Fire Blast",
                    "id": "fireblast",
                    "pp": 8,
                    "maxpp": 8,
                    "target": "normal",
                    "disabled": False,
                    "type": "Fire",
                    "category": "Special",
                    "base_power": 110,
                    "accuracy": 85,
                }
            ],
            "can_terastallize": True,
            "tera_type": "Fire",
            "trapped": False,
            "can_switch": True,
        },
        "side": [],
        "legal_actions": {
            "mask": [True] + [False] * 12,
            "actions": [{"index": 0, "kind": "move", "choice": "move 1", "label": "move:Fire Blast", "move": "Fire Blast", "slot": 1}] + [None] * 12,
            "available_indices": [0],
        },
        "raw": {},
    }
    return view, request


class FeaturizeTest(unittest.TestCase):
    def test_shapes_are_stable(self):
        view, request = sample_result()
        features = featurize_battle(view, request)
        self.assertEqual(features.global_vector.shape, (GLOBAL_DIM,))
        self.assertEqual(features.own_team.shape, (6, POKEMON_DIM))
        self.assertEqual(features.opponent_team.shape, (6, POKEMON_DIM))
        self.assertEqual(features.request_vector.shape, (REQUEST_DIM,))
        self.assertEqual(features.legal_mask.shape, (13,))
        self.assertEqual(features.flat.shape[0], GLOBAL_DIM + 6 * POKEMON_DIM + 6 * POKEMON_DIM + REQUEST_DIM)


if __name__ == "__main__":
    unittest.main()
