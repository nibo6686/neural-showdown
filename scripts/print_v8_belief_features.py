"""Print the v8 belief feature slice for an opponent active slot at a prefix.

Read-only diagnostic. Uses only the public protocol prefix and the pinned
Randbats prior source. Example:

    python scripts/print_v8_belief_features.py \
        --replay data/replays/raw/gen9randombattle/gen9randombattle-2587967313.log \
        --perspective p1 --through-turn 6
"""

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TRAINER_SRC = REPO_ROOT / "trainer" / "src"
if str(TRAINER_SRC) not in sys.path:
    sys.path.insert(0, str(TRAINER_SRC))

from neural.live_private_features import active_opponent_set_belief
from neural.parse_replay_logs import parse_protocol_log
from neural.v8_belief_features import (
    V8_BELIEF_FEATURE_NAMES,
    v8_belief_slice_feature_vector,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay", type=Path, required=True)
    parser.add_argument("--perspective", default="p1", choices=["p1", "p2"])
    parser.add_argument("--through-turn", type=int, default=None)
    parser.add_argument("--prior-source", type=Path, default=None)
    args = parser.parse_args()

    lines = args.replay.read_text(encoding="utf-8", errors="replace").splitlines()
    trajectory = parse_protocol_log(
        lines, replay_id=args.replay.stem, format_name="gen9randombattle"
    )
    belief = active_opponent_set_belief(
        trajectory,
        player_side=args.perspective,
        sets_path=str(args.prior_source) if args.prior_source else None,
        through_turn=args.through_turn,
    )
    species = belief.species_form_key if belief is not None else "<none>"
    print(f"replay={args.replay.stem} perspective={args.perspective} "
          f"through_turn={args.through_turn} opponent_active={species}")
    vector = v8_belief_slice_feature_vector(belief)
    width = max(len(name) for name in V8_BELIEF_FEATURE_NAMES)
    for name, value in zip(V8_BELIEF_FEATURE_NAMES, vector.tolist()):
        print(f"  {name:<{width}} {float(value):.4f}")


if __name__ == "__main__":
    main()
