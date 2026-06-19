"""Build a value dataset from seeded sim-core games featurized through the SAME
live/sim-core path that branch/live evaluation uses.

Motivation: the production live-private value model was trained on the
replay-native reconstruction path, but branch/live evaluation feeds sim-core
``ChoiceRequestView`` states through ``build_features_from_live_payload``. That
train/serve skew collapsed the model on branch states. This builder generates
states on the serving distribution so a bounded value head can be trained to
match it.

Scope: seeded Gen 9 Random Battle singles. Features are live-style and
perspective-filtered (own request + public protocol + randbats beliefs); they do
NOT contain exact hidden opponent information.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from .build_replay_value_dataset import result_from_winner_side
from .env_client import SimCoreClient
from .live_private_features import FEATURE_DIM, FEATURE_VERSION, build_features_from_live_payload
from .runtime import make_battle_seed
from .value_features import discounted_terminal_return


REPO_ROOT = Path(__file__).resolve().parents[3]
SIM_CORE_DIR = REPO_ROOT / "sim-core"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "data" / "value" / "gen9randombattle_live_sim_value_v1.npz"
DEFAULT_REPORT_PATH = REPO_ROOT / "artifacts" / "agent_audit" / "live_sim_value_dataset_report.md"
RESULT_OPTIONS = {"view_players": ["p1", "p2"], "include_log_delta": True, "include_possible_roles": False}
LABEL_DEFINITION = "discounted_terminal_return(perspective_final_result, turns_to_end, gamma); bounded [-1,1]"


def _make_client() -> SimCoreClient:
    command_json = os.environ.get("NEURAL_SIM_CORE_COMMAND_JSON")
    cwd = os.environ.get("NEURAL_SIM_CORE_CWD")
    if command_json and cwd:
        return SimCoreClient(json.loads(command_json), cwd)
    return SimCoreClient(["node", "dist/src/server.js"], str(SIM_CORE_DIR))


def _actionable(request: Any) -> bool:
    return (
        isinstance(request, Mapping)
        and isinstance(request.get("legal_actions"), Mapping)
        and bool((request["legal_actions"] or {}).get("actions"))
        and not request.get("wait")
        and not request.get("team_preview")
    )


def _play_game(
    client: SimCoreClient,
    seed: Sequence[int],
    controllers: Mapping[str, str],
) -> Tuple[List[Dict[str, Any]], Optional[str], int]:
    """Play one seeded game; return per-turn snapshots, winner_side, final turn."""
    env_id = client.create_env(
        "gen9randombattle",
        list(seed),
        {"p1": {"controller": "external"}, "p2": {"controller": "external"}},
        timeout_sec=30,
    )
    snapshots: List[Dict[str, Any]] = []
    protocol: List[str] = []
    result = client.reset(env_id, RESULT_OPTIONS, timeout_sec=60)
    protocol.extend(result.get("log_delta") or [])
    try:
        while not result.get("terminated"):
            requests = result.get("requests") or {}
            turn = int((result.get("info") or {}).get("turn") or 0)
            snapshots.append(
                {
                    "protocol": list(protocol),
                    "requests": {
                        side: (dict(req) if isinstance(req, Mapping) else None)
                        for side, req in requests.items()
                    },
                    "turn": turn,
                }
            )
            choices: Dict[str, str] = {}
            for side in ("p1", "p2"):
                if _actionable(requests.get(side)):
                    decision = client.agent_action(env_id, side, controllers[side], timeout_sec=20)
                    choices[side] = str(decision.get("choice") or "default")
            if not choices:
                break
            result = client.step(env_id, choices, RESULT_OPTIONS, timeout_sec=60)
            protocol.extend(result.get("log_delta") or [])
        winner = result.get("winner")
        final_turn = int((result.get("info") or {}).get("turn") or 0)
        return snapshots, winner, final_turn
    finally:
        try:
            client.close_env(env_id, timeout_sec=10)
        except Exception:
            pass


def build_dataset(
    *,
    num_games: int = 40,
    gamma: float = 0.97,
    start_index: int = 0,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> Dict[str, Any]:
    client = _make_client()
    states: List[np.ndarray] = []
    targets: List[float] = []
    final_results: List[float] = []
    perspectives: List[int] = []
    turns: List[int] = []
    seeds: List[List[int]] = []
    skipped: Counter[str] = Counter()
    games_used = 0
    controller_counts: Counter[str] = Counter()

    started = time.perf_counter()
    try:
        for game in range(num_games):
            seed = make_battle_seed(start_index + game)
            # Alternate matchups for state diversity: balanced heuristic mirror and
            # lopsided heuristic-vs-random games (more decisive states).
            controllers = (
                {"p1": "heuristic", "p2": "heuristic"}
                if game % 2 == 0
                else {"p1": "heuristic", "p2": "random"}
            )
            controller_counts["/".join(sorted(set(controllers.values())))] += 1
            try:
                snapshots, winner, final_turn = _play_game(client, seed, controllers)
            except Exception as exc:  # pragma: no cover - generation guard
                skipped[f"game_error:{type(exc).__name__}"] += 1
                continue
            if winner not in ("p1", "p2", "tie"):
                skipped["no_winner_game"] += 1
                continue
            games_used += 1
            for snapshot in snapshots:
                for side in ("p1", "p2"):
                    request = snapshot["requests"].get(side)
                    if not _actionable(request):
                        skipped["non_actionable_request"] += 1
                        continue
                    result = result_from_winner_side(winner, perspective=side)
                    if result is None:
                        skipped["no_perspective_result"] += 1
                        continue
                    try:
                        features, _, _, _, _ = build_features_from_live_payload(
                            log=snapshot["protocol"],
                            room_id=f"sim-{game}",
                            url="sim://live-sim-value",
                            player=side,
                            request_payload=request,
                            legal_actions=[],
                        )
                    except Exception as exc:
                        skipped[f"feature_error:{type(exc).__name__}"] += 1
                        continue
                    features = np.asarray(features, dtype=np.float32)
                    if features.shape != (FEATURE_DIM,):
                        skipped["wrong_feature_dim"] += 1
                        continue
                    turns_to_end = max(0, int(final_turn) - int(snapshot["turn"]))
                    label = float(discounted_terminal_return(float(result), turns_to_end, gamma))
                    states.append(features)
                    targets.append(label)
                    final_results.append(float(result))
                    perspectives.append(0 if side == "p1" else 1)
                    turns.append(int(snapshot["turn"]))
                    seeds.append(list(seed))
    finally:
        client.close()

    if not states:
        raise ValueError("No live-sim value examples were produced.")

    states_arr = np.asarray(states, dtype=np.float32)
    targets_arr = np.asarray(targets, dtype=np.float32)
    finals_arr = np.asarray(final_results, dtype=np.float32)
    perspectives_arr = np.asarray(perspectives, dtype=np.int64)
    turns_arr = np.asarray(turns, dtype=np.int64)
    seeds_arr = np.asarray(seeds, dtype=np.int64)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_path,
        states=states_arr,
        value_targets=targets_arr,
        final_results=finals_arr,
        perspectives=perspectives_arr,
        turns=turns_arr,
        seeds=seeds_arr,
        feature_version=np.asarray(FEATURE_VERSION),
        feature_dim=np.asarray(FEATURE_DIM),
        label_definition=np.asarray(LABEL_DEFINITION),
        format_name=np.asarray("gen9randombattle"),
        gamma=np.asarray(gamma, dtype=np.float32),
        generation_mode=np.asarray("live_style_seeded_sim_core"),
    )

    report = {
        "output_path": str(output_path),
        "feature_version": FEATURE_VERSION,
        "feature_dim": int(FEATURE_DIM),
        "label_definition": LABEL_DEFINITION,
        "gamma": float(gamma),
        "num_games_requested": int(num_games),
        "num_games_used": int(games_used),
        "num_states": int(states_arr.shape[0]),
        "controller_matchups": dict(controller_counts),
        "p1_examples": int((perspectives_arr == 0).sum()),
        "p2_examples": int((perspectives_arr == 1).sum()),
        "win_examples": int((finals_arr > 0).sum()),
        "loss_examples": int((finals_arr < 0).sum()),
        "tie_examples": int((finals_arr == 0).sum()),
        "label_mean": float(targets_arr.mean()),
        "label_std": float(targets_arr.std()),
        "label_min": float(targets_arr.min()),
        "label_max": float(targets_arr.max()),
        "skipped": dict(skipped),
        "wall_time_sec": time.perf_counter() - started,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    return report


def _format_report_md(report: Dict[str, Any]) -> str:
    lines = [
        "# Live/Sim Value Dataset Report (Part B)",
        "",
        f"Generated: {report['timestamp']}",
        f"Output: `{report['output_path']}`",
        "",
        "## Generation",
        "",
        f"- Feature version: {report['feature_version']}",
        f"- Feature dimension: {report['feature_dim']}",
        f"- Label definition: {report['label_definition']}",
        f"- Gamma: {report['gamma']}",
        f"- Generation mode: live-style seeded sim-core (no exact hidden opponent info in features)",
        f"- Games requested/used: {report['num_games_requested']} / {report['num_games_used']}",
        f"- Controller matchups: {report['controller_matchups']}",
        f"- Wall time: {report['wall_time_sec']:.1f}s",
        "",
        "## States",
        "",
        f"- Total states: {report['num_states']}",
        f"- p1 / p2 examples: {report['p1_examples']} / {report['p2_examples']}",
        f"- win / loss / tie examples: {report['win_examples']} / {report['loss_examples']} / {report['tie_examples']}",
        "",
        "## Labels",
        "",
        f"- mean / std: {report['label_mean']:.4f} / {report['label_std']:.4f}",
        f"- min / max: {report['label_min']:.4f} / {report['label_max']:.4f}",
        "",
        "## Skipped states",
        "",
    ]
    if report["skipped"]:
        for reason, count in sorted(report["skipped"].items()):
            lines.append(f"- {reason}: {count}")
    else:
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a live/sim-core value dataset (seeded Gen 9 singles).")
    parser.add_argument("--num-games", type=int, default=40)
    parser.add_argument("--gamma", type=float, default=0.97)
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    args = parser.parse_args()

    report = build_dataset(
        num_games=args.num_games,
        gamma=args.gamma,
        start_index=args.start_index,
        output_path=args.output_path,
    )
    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_text(_format_report_md(report), encoding="utf-8")
    print(json.dumps({"output": report["output_path"], "states": report["num_states"], "report": str(args.report_path)}))


if __name__ == "__main__":
    main()
