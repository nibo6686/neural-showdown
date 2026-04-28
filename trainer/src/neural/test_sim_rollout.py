import json

from .sim_branch_evaluator import evaluate_actions


def _seeded_trace() -> dict:
    return {
        "format": "gen9randombattle",
        "protocol_log": [">start " + json.dumps({"seed": [1, 2, 3, 4]})],
        "turns": [
            {
                "turn": 1,
                "steps": [
                    {
                        "step_index": 0,
                        "turn": 1,
                        "p1_species": "Morpeko",
                        "p2_species": "Vileplume",
                        "p1_hp_ratio": 1.0,
                        "p2_hp_ratio": 1.0,
                        "legal_actions": [
                            {"index": 0, "kind": "move", "label": "move:Will-O-Wisp", "move": "Will-O-Wisp"},
                            {"index": 1, "kind": "move", "label": "move:Tackle", "move": "Tackle"},
                        ],
                        "chosen_action_index": 1,
                    }
                ],
            }
        ],
    }


def _public_trace() -> dict:
    trace = _seeded_trace()
    trace["protocol_log"] = []
    return trace


def main() -> None:
    exact_results = evaluate_actions(
        {"trace": _seeded_trace()},
        "p1",
        [{"index": 0, "kind": "move", "label": "move:Will-O-Wisp", "move": "Will-O-Wisp"}],
        rollout_config={"rollout_mode": "exact", "rollouts_per_action": 1},
    )
    approx_results = evaluate_actions(
        {"trace": _public_trace()},
        "p1",
        [{"index": 0, "kind": "move", "label": "move:Will-O-Wisp", "move": "Will-O-Wisp"}],
        rollout_config={"rollout_mode": "approximate", "rollouts_per_action": 4},
    )
    print(
        json.dumps(
            {
                "exact_methods": [row.get("method") for row in exact_results],
                "approx_methods": [row.get("method") for row in approx_results],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
