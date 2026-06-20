"""Replay sanitized live /evaluate captures through the vNext dry-run path."""

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .live_eval_server import EvalRequest
from .vnext_live_shadow import build_dry_run


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CAPTURE_DIR = REPO_ROOT / "artifacts/live_eval_captures"
DEFAULT_REPORT = REPO_ROOT / "artifacts/training_plan/vnext_real_packet_shadow_validation_report.md"


def _species(value: Any) -> str:
    text = str(value or "").split(",", 1)[0].split(": ", 1)[-1]
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _request_moves(request: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    active = (request or {}).get("active")
    block = active[0] if isinstance(active, list) and active else {}
    moves = block.get("moves") if isinstance(block, dict) else []
    return [move for move in moves if isinstance(move, dict)]


def _request_team(request: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    side = (request or {}).get("side")
    team = side.get("pokemon") if isinstance(side, dict) else []
    return [mon for mon in team if isinstance(mon, dict)]


def validate_payload_slots(payload: EvalRequest, result: Dict[str, Any]) -> Dict[str, Any]:
    moves = _request_moves(payload.request)
    team = _request_team(payload.request)
    errors: List[str] = []
    checked_moves = checked_tera = checked_switches = 0
    tera_legal = bool(
        moves
        and isinstance((payload.request or {}).get("active"), list)
        and ((payload.request or {}).get("active") or [{}])[0].get("canTerastallize")
    )

    for action in payload.legal_actions:
        if action.disabled or action.slot is None:
            continue
        slot = int(action.slot)
        if action.kind in {"move", "move_tera"}:
            if not 1 <= slot <= len(moves):
                errors.append(f"{action.kind} slot {slot} outside request move list")
                continue
            expected = str(moves[slot - 1].get("move") or moves[slot - 1].get("name") or moves[slot - 1].get("id") or "")
            if _species(expected) not in _species(action.label):
                errors.append(f"{action.kind} slot {slot} label {action.label!r} != {expected!r}")
            checked_moves += 1
            if action.kind == "move_tera":
                checked_tera += 1
                if not tera_legal:
                    errors.append(f"move {slot} terastallize present when request does not allow Tera")
        elif action.kind == "switch":
            if not 1 <= slot <= len(team):
                errors.append(f"switch slot {slot} outside side Pokémon list")
                continue
            expected = team[slot - 1].get("details") or team[slot - 1].get("ident")
            if _species(expected) not in _species(action.label):
                errors.append(f"switch slot {slot} label {action.label!r} != {expected!r}")
            checked_switches += 1

    if not tera_legal and result.get("candidate_kind_counts", {}).get("move_tera", 0):
        errors.append("vNext generated Tera candidates when Tera was not legal")

    selected = result.get("selected") if isinstance(result.get("selected"), dict) else {}
    choice = str(result.get("choice") or "")
    if selected and choice.startswith("move "):
        slot = selected.get("move_slot")
        if not isinstance(slot, int) or not 1 <= slot <= len(moves):
            errors.append(f"selected move slot {slot!r} outside request move list")
        if choice.endswith(" terastallize") and not tera_legal:
            errors.append("selected Tera command when Tera was not legal")
    if selected and choice.startswith("switch "):
        slot = selected.get("switch_slot")
        if not isinstance(slot, int) or not 1 <= slot <= len(team):
            errors.append(f"selected switch slot {slot!r} outside side Pokémon list")

    return {
        "ok": not errors,
        "errors": errors,
        "move_actions_checked": checked_moves,
        "tera_actions_checked": checked_tera,
        "switch_actions_checked": checked_switches,
        "tera_legal": tera_legal,
    }


def replay_capture(path: Path) -> Dict[str, Any]:
    payload = EvalRequest(**json.loads(path.read_text(encoding="utf-8")))
    result = build_dry_run(
        log=payload.log,
        room_id=payload.room_id,
        url=payload.url,
        player=payload.player,
        request_payload=payload.request,
        legal_actions=[action.model_dump() if hasattr(action, "model_dump") else action.dict() for action in payload.legal_actions],
    )
    return {
        "file": str(path),
        "turn": payload.turn,
        "decision_phase": payload.decision_phase,
        "result": result,
        "slot_validation": validate_payload_slots(payload, result),
    }


def _write_report(report_path: Path, captures: List[Dict[str, Any]]) -> None:
    successful = [item for item in captures if item["result"].get("ok")]
    failed = [item for item in captures if not item["result"].get("ok")]
    packet_types: Dict[str, int] = {}
    for item in captures:
        phase = str(item.get("decision_phase") or "unknown")
        packet_types[phase] = packet_types.get(phase, 0) + 1
    lines = [
        "# vNext Real Packet Shadow Validation Report",
        "",
        "- Existing replayable captures before this task: **no** (server logs contained access lines only).",
        "- Capture mechanism: **added**, opt-in via `NEURAL_CAPTURE_EVALUATE_PAYLOADS=1`, default off, maximum 3 distinct actionable packets.",
        f"- Packets replayed: **{len(captures)}** ({', '.join(f'{key}: {value}' for key, value in packet_types.items()) or 'none'}).",
        "- Sanitization: room ID and URL replaced; account/player names redacted from request metadata and protocol player/win lines; chat/auth-like lines and token/session keys omitted.",
        f"- Dry-run successes: **{len(successful)}**; fail-closed cases: **{len(failed)}**.",
        "- Command sent to Showdown: **no**.",
        "- Battle played by the model: **no**.",
        "- Live defaults changed: **no**.",
        "",
        "## Packet Results",
        "",
    ]
    if not captures:
        lines += [
            "No real packets have been captured yet. Restart the existing server with capture enabled, then make one normal move decision in Showdown.",
            "",
        ]
    for item in captures:
        result = item["result"]
        schema = result.get("schema") or {}
        counts = result.get("candidate_kind_counts") or {}
        latency = result.get("latency_ms") or {}
        slots = item["slot_validation"]
        lines += [
            f"### `{Path(item['file']).name}`",
            "",
            f"- Phase/turn: `{item.get('decision_phase')}` / `{item.get('turn')}`",
            f"- Result: `ok={result.get('ok')}`, fail-closed reason: `{result.get('fallback_reason')}`",
            f"- v7 state: `{schema.get('state_feature_version')}`, **{schema.get('state_feature_dim')}D**",
            f"- v5 candidates: `{schema.get('action_feature_version')}`, **{schema.get('action_feature_dim')}D**",
            f"- Candidate kinds: move={counts.get('move', 0)}, move_tera={counts.get('move_tera', 0)}, switch={counts.get('switch', 0)}",
            f"- Tera candidates: `{(result.get('tera') or {}).get('tera_candidates_generated')}`; switch candidates: `{result.get('switch_candidate_count')}`",
            f"- Selected command: `{result.get('choice')}`",
            f"- Latency: `{latency.get('total_ms')}` ms",
            f"- Slot validation: `ok={slots.get('ok')}`; move={slots.get('move_actions_checked')}, Tera={slots.get('tera_actions_checked')}, switch={slots.get('switch_actions_checked')}; errors={slots.get('errors')}",
            "",
        ]
    lines += [
        "## Remaining Blocker",
        "",
        (
            "A force-switch real packet remains recommended coverage before manual recommendation testing. "
            "The recorded latency is a cold standalone replay without the live server's persistent sim-core client; "
            "use the existing warm-server measurement (~35–60 ms) for interactive latency expectations."
            if successful
            else "A successful normal-move real packet replay remains required before manual recommendation testing."
        ),
        "",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture-dir", type=Path, default=DEFAULT_CAPTURE_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    paths = sorted(args.capture_dir.glob("evaluate_*.json"))
    captures = [replay_capture(path) for path in paths]
    _write_report(args.report, captures)
    print(json.dumps(captures, indent=2))
    return 0 if captures and all(item["result"].get("ok") and item["slot_validation"]["ok"] for item in captures) else 1


if __name__ == "__main__":
    raise SystemExit(main())
