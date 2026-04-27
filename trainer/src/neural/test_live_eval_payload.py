from typing import Any, Dict, List

from .live_eval_server import EvalRequest, evaluate_with_model, reset_model_caches


def _request(
    *,
    active: str,
    team: List[str],
    moves: List[Dict[str, Any]],
    hp: str = "100/100",
) -> Dict[str, Any]:
    pokemon = []
    for species in team:
        pokemon.append(
            {
                "ident": f"p1: {species}",
                "details": f"{species}, L80",
                "condition": hp if species == active else "100/100",
                "active": species == active,
                "moves": [move["move"] for move in moves] if species == active else [],
                "item": "Heavy-Duty Boots" if species == active else None,
                "ability": "Skill Link" if species == active else None,
                "baseAbility": "Skill Link" if species == active else None,
                "teraType": "Normal" if species == active else None,
            }
        )
    return {
        "side": {"id": "p1", "pokemon": pokemon},
        "active": [{"moves": moves}],
        "forceSwitch": [False],
    }


def fake_payloads() -> List[EvalRequest]:
    team = ["Toucannon", "Meganium", "Hydreigon"]
    return [
        EvalRequest(
            room_id="smoke-turn-1",
            url="https://play.pokemonshowdown.com/battle-smoke-1",
            player="p1",
            log=[
                "|player|p1|Alice",
                "|player|p2|Bob",
                "|turn|1",
                "|switch|p1a: Toucannon|Toucannon, L80, F|100/100",
                "|switch|p2a: Dodrio|Dodrio, L80, M|100/100",
            ],
            request=_request(
                active="Toucannon",
                team=team,
                moves=[
                    {"id": "beakblast", "move": "Beak Blast", "pp": 8, "maxpp": 16, "disabled": False},
                    {"id": "uturn", "move": "U-turn", "pp": 20, "maxpp": 20, "disabled": False},
                    {"id": "roost", "move": "Roost", "pp": 8, "maxpp": 8, "disabled": False},
                ],
            ),
            legal_actions=[
                {"kind": "move", "label": "Beak Blast", "index": 0},
                {"kind": "move", "label": "U-turn", "index": 1},
                {"kind": "move", "label": "Roost", "index": 2},
                {"kind": "switch", "label": "Meganium", "index": 8},
            ],
        ),
        EvalRequest(
            room_id="smoke-turn-2",
            url="https://play.pokemonshowdown.com/battle-smoke-2",
            player="p1",
            log=[
                "|player|p1|Alice",
                "|player|p2|Bob",
                "|turn|1",
                "|switch|p1a: Toucannon|Toucannon, L80, F|100/100",
                "|switch|p2a: Dodrio|Dodrio, L80, M|100/100",
                "|move|p2a: Dodrio|Knock Off|p1a: Toucannon",
                "|-damage|p1a: Toucannon|55/100",
                "|turn|2",
            ],
            request=_request(
                active="Toucannon",
                team=team,
                hp="55/100",
                moves=[
                    {"id": "beakblast", "move": "Beak Blast", "pp": 7, "maxpp": 16, "disabled": False},
                    {"id": "uturn", "move": "U-turn", "pp": 20, "maxpp": 20, "disabled": False},
                    {"id": "roost", "move": "Roost", "pp": 8, "maxpp": 8, "disabled": False},
                ],
            ),
            legal_actions=[
                {"kind": "move", "label": "Beak Blast", "index": 0},
                {"kind": "move", "label": "U-turn", "index": 1},
                {"kind": "move", "label": "Roost", "index": 2},
                {"kind": "switch", "label": "Meganium", "index": 8},
                {"kind": "switch", "label": "Hydreigon", "index": 9},
            ],
        ),
        EvalRequest(
            room_id="smoke-turn-3",
            url="https://play.pokemonshowdown.com/battle-smoke-3",
            player="p1",
            log=[
                "|player|p1|Alice",
                "|player|p2|Bob",
                "|turn|1",
                "|switch|p1a: Toucannon|Toucannon, L80, F|100/100",
                "|switch|p2a: Dodrio|Dodrio, L80, M|100/100",
                "|move|p2a: Dodrio|Knock Off|p1a: Toucannon",
                "|-damage|p1a: Toucannon|55/100",
                "|move|p1a: Toucannon|U-turn|p2a: Dodrio",
                "|switch|p1a: Meganium|Meganium, L80, F|100/100|[from] U-turn",
                "|move|p2a: Dodrio|Brave Bird|p1a: Meganium",
                "|-damage|p1a: Meganium|44/100",
                "|turn|3",
            ],
            request=_request(
                active="Meganium",
                team=team,
                hp="44/100",
                moves=[
                    {"id": "petalblizzard", "move": "Petal Blizzard", "pp": 15, "maxpp": 15, "disabled": False},
                    {"id": "knockoff", "move": "Knock Off", "pp": 20, "maxpp": 20, "disabled": False},
                    {"id": "synthesis", "move": "Synthesis", "pp": 8, "maxpp": 8, "disabled": False},
                ],
            ),
            legal_actions=[
                {"kind": "move", "label": "Petal Blizzard", "index": 0},
                {"kind": "move", "label": "Knock Off", "index": 1},
                {"kind": "move", "label": "Synthesis", "index": 2},
                {"kind": "switch", "label": "Toucannon", "index": 8},
                {"kind": "switch", "label": "Hydreigon", "index": 9},
            ],
        ),
    ]


def _opponent_candidate_count(response: Dict[str, Any]) -> int:
    opponents = response.get("debug", {}).get("inferred", {}).get("opponent_beliefs", [])
    if not opponents:
        return 0
    return int(opponents[-1].get("candidate_count", 0) or 0)


def main() -> None:
    reset_model_caches()
    previous_preview = None
    for turn, payload in enumerate(fake_payloads(), start=1):
        response = evaluate_with_model(payload)
        private_state = response.get("debug", {}).get("known", {}).get("private_state", {})
        own_active = private_state.get("active_species")
        opponents = response.get("debug", {}).get("inferred", {}).get("opponent_beliefs", [])
        opponent_active = opponents[-1].get("species") if opponents else None
        legal_labels = [action["label"] for action in response.get("debug", {}).get("all_action_estimates", [])]
        top_labels = [
            f"{action['label']} ({action['method']}, score={action['score']:.3f})"
            for action in response.get("top_actions", [])
        ]
        preview = response.get("debug", {}).get("feature_values_preview", [])
        changed = previous_preview is None or preview != previous_preview
        previous_preview = preview
        print(
            "live-eval-smoke "
            f"turn={turn} model_type={response.get('model_type')} "
            f"p1_win_prob={response.get('p1_win_prob'):.3f} p2_win_prob={response.get('p2_win_prob'):.3f} "
            f"own_active={own_active} opponent_active={opponent_active} "
            f"belief_candidates={_opponent_candidate_count(response)} features_changed={changed}"
        )
        print(f"  legal_actions={legal_labels}")
        print(f"  top_actions={top_labels}")


if __name__ == "__main__":
    main()
