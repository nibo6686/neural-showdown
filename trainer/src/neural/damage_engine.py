from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from .action_features import load_move_metadata, to_id


def _active_private_mon(private_state: Dict[str, Any]) -> Dict[str, Any]:
    team = private_state.get("team") if isinstance(private_state.get("team"), list) else []
    for mon in team:
        if isinstance(mon, dict) and mon.get("active"):
            return mon
    return team[0] if team and isinstance(team[0], dict) else {}


def _opponent_view_mon(approx_state: Dict[str, Any]) -> Dict[str, Any]:
    view = approx_state.get("view") if isinstance(approx_state.get("view"), dict) else {}
    team = view.get("opponent_team") if isinstance(view.get("opponent_team"), list) else []
    return team[0] if team and isinstance(team[0], dict) else {}


def _type_multiplier(move_type: Optional[str], target_types: Sequence[str]) -> float:
    if not move_type:
        return 1.0
    chart = {
        ("Electric", "Flying"): 2.0,
        ("Electric", "Water"): 2.0,
        ("Electric", "Ground"): 0.0,
        ("Dragon", "Fairy"): 0.0,
        ("Poison", "Steel"): 0.0,
        ("Normal", "Ghost"): 0.0,
        ("Fighting", "Ghost"): 0.0,
        ("Ground", "Flying"): 0.0,
        ("Rock", "Grass"): 0.5,
        ("Rock", "Ground"): 0.5,
        ("Water", "Fire"): 2.0,
        ("Fire", "Grass"): 2.0,
    }
    multiplier = 1.0
    for target_type in target_types:
        multiplier *= chart.get((str(move_type), str(target_type)), 1.0)
    return float(multiplier)


def _default_estimate(method: str = "heuristic_fallback") -> Dict[str, Any]:
    return {
        "damage_method": method,
        "damage_rolls": [],
        "average_percent": 0.0,
        "min_percent": 0.0,
        "max_percent": 0.0,
        "ko_chance": 0.0,
        "immune": False,
        "type_effectiveness": 1.0,
        "item_modifier": 1.0,
        "burn_attack_penalty": False,
        "tera_damage_bonus": 0.0,
        "warnings": [],
    }


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _compact_damage_payload_summary(payload: Dict[str, Any]) -> Dict[str, Any]:
    attacker = payload.get("attacker") if isinstance(payload.get("attacker"), dict) else {}
    defender = payload.get("defender") if isinstance(payload.get("defender"), dict) else {}

    def mon_summary(mon: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "species": mon.get("species"),
            "level": mon.get("level"),
            "item": mon.get("item"),
            "ability": mon.get("ability"),
            "status": mon.get("status"),
            "tera_type": mon.get("tera_type") or mon.get("teraType"),
            "terastallized": mon.get("terastallized"),
            "hp_fraction": mon.get("hp_fraction"),
            "cur_hp": mon.get("cur_hp"),
            "max_hp": mon.get("max_hp"),
            "stats_keys": sorted((mon.get("stats") or {}).keys()) if isinstance(mon.get("stats"), dict) else [],
            "evs_keys": sorted((mon.get("evs") or {}).keys()) if isinstance(mon.get("evs"), dict) else [],
            "ivs_keys": sorted((mon.get("ivs") or {}).keys()) if isinstance(mon.get("ivs"), dict) else [],
            "boosts": mon.get("boosts") if isinstance(mon.get("boosts"), dict) else {},
        }

    return {
        "attacker": mon_summary(attacker),
        "defender": mon_summary(defender),
        "move": payload.get("move"),
        "use_tera": payload.get("use_tera"),
        "field": payload.get("field") if isinstance(payload.get("field"), dict) else {},
    }


def _damage_failure_warning(prefix: str, exc: Exception, payload: Dict[str, Any]) -> str:
    attacker = payload.get("attacker") if isinstance(payload.get("attacker"), dict) else {}
    defender = payload.get("defender") if isinstance(payload.get("defender"), dict) else {}
    summary = _compact_damage_payload_summary(payload)
    return (
        f"{prefix}:{type(exc).__name__}:{exc}; "
        f"attacker_species={attacker.get('species')!r}; "
        f"defender_species={defender.get('species')!r}; "
        f"move={payload.get('move')!r}; "
        f"input_summary={json.dumps(summary, sort_keys=True, default=str)}"
    )


def _rpc_payload(action: Dict[str, Any], approx_state: Dict[str, Any], *, force_tera_active: Optional[bool]) -> Dict[str, Any]:
    private_state = approx_state.get("private_state") if isinstance(approx_state.get("private_state"), dict) else {}
    attacker = dict(_active_private_mon(private_state))
    defender = dict(_opponent_view_mon(approx_state))
    tactical_state = approx_state.get("tactical_state") if isinstance(approx_state.get("tactical_state"), dict) else {}
    tactical_own = tactical_state.get("own") if isinstance(tactical_state.get("own"), dict) else {}
    tactical_opp = tactical_state.get("opponent") if isinstance(tactical_state.get("opponent"), dict) else {}
    if not attacker.get("status"):
        attacker["status"] = tactical_own.get("active_status")
    if not defender.get("status"):
        defender["status"] = tactical_opp.get("active_status")
    move = str(action.get("move") or action.get("label") or "").split(":", 1)[-1].strip()
    if action.get("tera_type") and not attacker.get("tera_type"):
        attacker["tera_type"] = action.get("tera_type")
    use_tera = str(action.get("kind") or "") == "move_tera" or bool(action.get("is_tera_action"))
    if force_tera_active is not None:
        use_tera = bool(force_tera_active)
    return {
        "attacker": attacker,
        "defender": defender,
        "move": move,
        "use_tera": use_tera,
        "field": {
            "weather": tactical_state.get("weather"),
            "terrain": tactical_state.get("terrain"),
            "reflect": bool(((tactical_state.get("opponent") or {}).get("side_conditions") or {}).get("reflect")),
            "light_screen": bool(((tactical_state.get("opponent") or {}).get("side_conditions") or {}).get("lightscreen")),
            "aurora_veil": bool(((tactical_state.get("opponent") or {}).get("side_conditions") or {}).get("auroraveil")),
        },
    }


def _estimate_with_node(payload: Dict[str, Any]) -> Dict[str, Any]:
    sim_core = _repo_root() / "sim-core"
    module_path = sim_core / "dist" / "src" / "damage_calc.js"
    src_path = sim_core / "src" / "damage_calc.ts"
    needs_build = not module_path.exists()
    if not needs_build and src_path.exists():
        needs_build = src_path.stat().st_mtime > module_path.stat().st_mtime
    if needs_build:
        build = subprocess.run(
            ["npm", "run", "build"],
            cwd=str(sim_core),
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=60,
            check=False,
        )
        if build.returncode != 0 or not module_path.exists():
            raise FileNotFoundError(
                f"sim-core damage calculator is not built: {module_path}; build output: {(build.stderr or build.stdout).strip()}"
            )
    script = (
        "const {estimateDamage}=require('./dist/src/damage_calc.js');"
        "const fs=require('fs');"
        "const payload=JSON.parse(fs.readFileSync(0,'utf8'));"
        "process.stdout.write(JSON.stringify(estimateDamage(payload)));"
    )
    proc = subprocess.run(
        ["node", "-e", script],
        cwd=str(sim_core),
        input=json.dumps(payload),
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=10,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or f"node exited {proc.returncode}").strip())
    result = json.loads(proc.stdout or "{}")
    if not isinstance(result, dict):
        raise RuntimeError("smogon damage calculator returned a non-object result")
    return result


def _heuristic_estimate(action: Dict[str, Any], approx_state: Dict[str, Any], *, force_tera_active: Optional[bool]) -> Dict[str, Any]:
    estimate = _default_estimate()
    move_name = str(action.get("move") or action.get("label") or "").split(":", 1)[-1].strip()
    metadata, _ = load_move_metadata()
    move_meta = metadata.get(to_id(move_name), {})
    base_power = float(move_meta.get("base_power", 0.0) or 0.0)
    if str(move_meta.get("category") or "").lower() == "status" or base_power <= 0:
        estimate["damage_method"] = "heuristic_fallback"
        return estimate
    move_type = str(move_meta.get("type") or "") or None
    private_state = approx_state.get("private_state") if isinstance(approx_state.get("private_state"), dict) else {}
    attacker = _active_private_mon(private_state)
    defender = _opponent_view_mon(approx_state)
    target_types = [str(value) for value in defender.get("types", [])] if isinstance(defender.get("types"), list) else []
    type_eff = _type_multiplier(move_type, target_types)
    item_modifier = 1.3 if to_id(attacker.get("item")) == "lifeorb" else 1.0
    tactical_state = approx_state.get("tactical_state") if isinstance(approx_state.get("tactical_state"), dict) else {}
    tactical_own = tactical_state.get("own") if isinstance(tactical_state.get("own"), dict) else {}
    burned = str(attacker.get("status") or tactical_own.get("active_status") or "").lower() == "brn"
    burn_penalty = bool(burned and str(move_meta.get("category") or "").lower() == "physical")
    tera_active = str(action.get("kind") or "") == "move_tera" or bool(action.get("is_tera_action"))
    if force_tera_active is not None:
        tera_active = bool(force_tera_active)
    tera_type = str(action.get("tera_type") or private_state.get("active_tera_type") or attacker.get("tera_type") or "")
    tera_modifier = 1.5 if tera_active and move_type and tera_type.lower() == move_type.lower() else 1.0
    average = base_power * type_eff * item_modifier * (0.5 if burn_penalty else 1.0) * tera_modifier / 2.4
    if type_eff == 0.0:
        average = 0.0
    target_hp = float(defender.get("hp_fraction") if defender.get("hp_fraction") is not None else 1.0) * 100.0
    min_percent = float(average * 0.85)
    max_percent = float(average)
    if to_id(defender.get("item")) == "focussash" and float(defender.get("hp_fraction") or 1.0) >= 1.0 and max_percent >= 100.0:
        max_percent = 99.0
        min_percent = min(min_percent, max_percent)
    estimate.update(
        {
            "average_percent": float(average),
            "min_percent": min_percent,
            "max_percent": max_percent,
            "ko_chance": 1.0 if max_percent >= target_hp and target_hp > 0 else 0.0,
            "immune": bool(type_eff == 0.0),
            "type_effectiveness": float(type_eff),
            "item_modifier": item_modifier,
            "burn_attack_penalty": burn_penalty,
            "tera_damage_bonus": float(max(0.0, average - average / tera_modifier)) if tera_modifier > 1.0 else 0.0,
        }
    )
    return estimate


def estimate_action_damage(
    *,
    action: Dict[str, Any],
    approx_state: Dict[str, Any],
    client: Any = None,
    force_tera_active: Optional[bool] = None,
) -> Dict[str, Any]:
    if client is not None:
        try:
            result = client.damage_estimate(_rpc_payload(action, approx_state, force_tera_active=force_tera_active))
            if isinstance(result, dict):
                merged = _default_estimate("smogon_calc")
                merged.update(result)
                merged.setdefault("warnings", [])
                return merged
        except Exception as exc:
            fallback = _heuristic_estimate(action, approx_state, force_tera_active=force_tera_active)
            fallback.setdefault("warnings", []).append(_damage_failure_warning("damage_rpc_failed", exc, _rpc_payload(action, approx_state, force_tera_active=force_tera_active)))
            return fallback

    payload = _rpc_payload(action, approx_state, force_tera_active=force_tera_active)
    try:
        result = _estimate_with_node(payload)
        merged = _default_estimate("smogon_calc")
        merged.update(result)
        merged.setdefault("warnings", [])
        return merged
    except Exception as exc:
        fallback = _heuristic_estimate(action, approx_state, force_tera_active=force_tera_active)
        fallback.setdefault("warnings", []).append(_damage_failure_warning("smogon_calc_failed", exc, payload))
        return fallback


def estimate_damage(
    *,
    attacker: Dict[str, Any],
    defender: Dict[str, Any],
    move: str,
    use_tera: bool = False,
    field: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    approx_state = {
        "private_state": {"team": [{**dict(attacker), "active": True}]},
        "view": {"opponent_team": [dict(defender)]},
        "tactical_state": {"weather": (field or {}).get("weather"), "terrain": (field or {}).get("terrain")},
    }
    action = {
        "kind": "move_tera" if use_tera else "move",
        "move": move,
        "label": f"move: {move}",
        "tera_type": attacker.get("tera_type") or attacker.get("teraType"),
    }
    return estimate_action_damage(action=action, approx_state=approx_state, force_tera_active=use_tera)


def main() -> None:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Check Smogon-backed damage engine health.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON only.")
    args = parser.parse_args()

    result = estimate_damage(
        attacker={"species": "Banette", "level": 80},
        defender={"species": "Kingambit", "level": 80, "hp_fraction": 1.0},
        move="Gunk Shot",
    )
    payload = {
        "python_executable": sys.executable,
        "damage_engine_file": __file__,
        "repo_root": str(_repo_root()),
        "sim_core_dist_damage_calc": str(_repo_root() / "sim-core" / "dist" / "src" / "damage_calc.js"),
        "sample": result,
        "ok": result.get("damage_method") == "smogon_calc" and bool(result.get("immune")) and result.get("type_effectiveness") == 0,
    }
    if args.json:
        print(json.dumps(payload, indent=2, default=str))
    else:
        print("DAMAGE_ENGINE_HEALTHCHECK:")
        print(json.dumps(payload, indent=2, default=str))


if __name__ == "__main__":
    main()
