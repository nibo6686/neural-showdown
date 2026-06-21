"""Targeted read-only reproduction for the two Magic Bounce residual battles."""

from pathlib import Path

from neural.benchmark_vnext_featuregen import (
    _completed_teams_for_action_reconstruction,
    _context_for_prefix,
    _trajectory_prefix_before_event,
)
from neural.build_action_rank_dataset import _legal_actions_from_private_state
from neural.parse_replay_logs import parse_protocol_log
from neural.vnext_labels import chosen_action_label, match_chosen_action


REPLAY_DIR = Path("data/replays/raw/gen9randombattle")


def _trajectory(replay_id: str):
    path = REPLAY_DIR / f"{replay_id}.log"
    return parse_protocol_log(
        path.read_text(encoding="utf-8").splitlines(),
        replay_id=replay_id,
        source_path=str(path),
    )


def _event(trajectory, *, turn_number: int, raw: str):
    for turn in trajectory["turns"]:
        if int(turn["turn"]) != turn_number:
            continue
        events = turn.get("events", [])
        for event in events:
            if event.get("raw") == raw:
                return event, events
    raise AssertionError(f"Event not found: turn={turn_number} raw={raw}")


def main() -> int:
    defog_replay = "gen9randombattle-2589608300"
    defog_raw = "|move|p2a: Hatterene|Defog|p1a: Weezing|[from] ability: Magic Bounce"
    psychic_raw = "|move|p2a: Hatterene|Psychic|p1a: Bastiodon"
    trajectory = _trajectory(defog_replay)
    teams = _completed_teams_for_action_reconstruction(trajectory)
    hatterene_moves = sorted(teams["p2"]["Hatterene"]["moves"])
    psychic, psychic_turn_events = _event(trajectory, turn_number=24, raw=psychic_raw)
    prefix = _trajectory_prefix_before_event(
        trajectory=trajectory,
        turn_number=24,
        event=psychic,
        turn_events=psychic_turn_events,
    )
    _, private_state, _, _ = _context_for_prefix(
        trajectory=trajectory,
        prefix=prefix,
        side="p2",
        through_turn=24,
        completed_teams=teams,
        sets_path=None,
    )
    actions = _legal_actions_from_private_state(private_state, "")
    psychic_label = chosen_action_label(psychic, turn_events=psychic_turn_events)
    psychic_matched = match_chosen_action(actions, psychic_label) is not None

    bounce_replay = "gen9randombattle-2594129364"
    bounce_raw = (
        "|move|p2a: Hatterene|Will-O-Wisp|p1a: Misdreavus|"
        "[from] ability: Magic Bounce"
    )
    bounce_trajectory = _trajectory(bounce_replay)
    bounce_event, bounce_turn_events = _event(
        bounce_trajectory, turn_number=2, raw=bounce_raw
    )
    bounce_label = chosen_action_label(bounce_event, turn_events=bounce_turn_events)

    checks = {
        "reflected_defog_not_in_hatterene_moveset": "Defog" not in hatterene_moves,
        "psychic_remains_in_hatterene_moveset": "Psychic" in hatterene_moves,
        "psychic_matches_legal_candidates": psychic_matched,
        "reflected_will_o_wisp_has_no_actor_choice_label": bounce_label is None,
    }
    print(f"defog_replay={defog_replay} turn=5 side=p2 reflected_move=Defog")
    print(f"hatterene_moves={hatterene_moves}")
    print(f"psychic_candidates={[action['label'] for action in actions]}")
    print(f"psychic_label={psychic_label!r} matched={psychic_matched}")
    print(
        f"bounce_replay={bounce_replay} turn=2 side=p2 "
        f"reflected_move=Will-O-Wisp label={bounce_label!r}"
    )
    for name, passed in checks.items():
        print(f"{name}={passed}")
    passed = all(checks.values())
    print(f"all_passed={passed}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
