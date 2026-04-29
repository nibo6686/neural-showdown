import json
import os
import socket
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    from neural.build_replay_value_dataset import (
        FEATURE_NAMES,
        FEATURE_VERSION,
        _apply_event,
        _feature_vector,
        _initial_state,
        _new_recent,
    )
    from neural.checkpoints import torch_load
    from neural import damage_engine
    from neural import live_action_recommender as live_action_recommender_module
    from neural.action_features import ACTION_FEATURE_DIM
    from neural.env_client import SimCoreClient
    from neural.live_action_recommender import legal_action_candidates as _recommend_action_candidates
    from neural.live_action_recommender import recommend_actions
    from neural.live_action_recommender import reset_action_ranker_cache
    from neural.live_opponent_beliefs import build_opponent_beliefs
    from neural.live_private_features import (
        FEATURE_DIM as LIVE_PRIVATE_FEATURE_DIM,
        FEATURE_DIM_V1 as LIVE_PRIVATE_FEATURE_DIM_V1,
        FEATURE_VERSION as LIVE_PRIVATE_FEATURE_VERSION,
        FEATURE_VERSION_V1 as LIVE_PRIVATE_FEATURE_VERSION_V1,
        build_features_from_live_payload,
    )
    from neural.live_private_state import extract_private_side_state
    from neural.models.policy_value_mlp import PolicyValueMLP
    from neural.parse_replay_logs import parse_protocol_log
except ImportError:
    from trainer.src.neural.build_replay_value_dataset import (
        FEATURE_NAMES,
        FEATURE_VERSION,
        _apply_event,
        _feature_vector,
        _initial_state,
        _new_recent,
    )
    from trainer.src.neural.checkpoints import torch_load
    from trainer.src.neural import damage_engine
    from trainer.src.neural import live_action_recommender as live_action_recommender_module
    from trainer.src.neural.action_features import ACTION_FEATURE_DIM
    from trainer.src.neural.env_client import SimCoreClient
    from trainer.src.neural.live_action_recommender import legal_action_candidates as _recommend_action_candidates
    from trainer.src.neural.live_action_recommender import recommend_actions
    from trainer.src.neural.live_action_recommender import reset_action_ranker_cache
    from trainer.src.neural.live_opponent_beliefs import build_opponent_beliefs
    from trainer.src.neural.live_private_features import (
        FEATURE_DIM as LIVE_PRIVATE_FEATURE_DIM,
        FEATURE_DIM_V1 as LIVE_PRIVATE_FEATURE_DIM_V1,
        FEATURE_VERSION as LIVE_PRIVATE_FEATURE_VERSION,
        FEATURE_VERSION_V1 as LIVE_PRIVATE_FEATURE_VERSION_V1,
        build_features_from_live_payload,
    )
    from trainer.src.neural.live_private_state import extract_private_side_state
    from trainer.src.neural.models.policy_value_mlp import PolicyValueMLP
    from trainer.src.neural.parse_replay_logs import parse_protocol_log


class LegalAction(BaseModel):
    kind: str
    label: str
    slot: Optional[int] = None
    index: Optional[int] = None
    disabled: bool = False


class EvalRequest(BaseModel):
    room_id: str
    url: str
    player: Optional[str] = None
    log: List[str] = Field(default_factory=list)
    request: Optional[Dict[str, Any]] = None
    legal_actions: List[LegalAction] = Field(default_factory=list)


DEFAULT_CORS_ORIGINS = ("https://play.pokemonshowdown.com", "https://pokemonshowdown.com")
DEFAULT_CORS_ORIGIN_REGEX = r"https://([a-z0-9-]+\.)?psim\.us(:\d+)?"


def _env_csv(name: str, default: Sequence[str]) -> List[str]:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return list(default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def _env_cors_origin_regex() -> str:
    return os.environ.get("NEURAL_LIVE_CORS_ORIGIN_REGEX", DEFAULT_CORS_ORIGIN_REGEX).strip()


def _env_flag(name: str) -> bool:
    value = os.environ.get(name, "").strip().lower()
    return value in {"1", "true", "yes", "on"}


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=_env_csv("NEURAL_LIVE_CORS_ORIGINS", DEFAULT_CORS_ORIGINS),
    allow_origin_regex=_env_cors_origin_regex() or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

OLD_VALUE_MODEL_PATH = Path("artifacts/checkpoints/gen9randombattle_replay_value.pt")
_CANONICAL_LIVE_PRIVATE_VALUE_MODEL_V2_PATH = Path("artifacts/checkpoints/gen9randombattle_live_private_value_v2.pt")
LIVE_PRIVATE_VALUE_MODEL_V2_PATH = _CANONICAL_LIVE_PRIVATE_VALUE_MODEL_V2_PATH
_CANONICAL_LIVE_PRIVATE_VALUE_MODEL_PATH = Path("artifacts/checkpoints/gen9randombattle_live_private_value.pt")
LIVE_PRIVATE_VALUE_MODEL_PATH = _CANONICAL_LIVE_PRIVATE_VALUE_MODEL_PATH
REPLAY_POLICY_MODEL_PATH = Path("artifacts/checkpoints/gen9randombattle_replay_policy.pt")
INPUT_SIZE = 31
HIDDEN_SIZES = [128, 128]
ACTION_SIZE = 13
DEBUG_FEATURE_PREVIEW = 8

_value_model = None
_value_model_metadata: Optional[Dict[str, Any]] = None
_policy_model = None
_policy_model_metadata: Optional[Dict[str, Any]] = None


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _git_branch() -> Optional[str]:
    try:
        proc = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=str(_repo_root()),
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=5,
            check=False,
        )
        branch = proc.stdout.strip()
        return branch or None
    except Exception:
        return None


def _neural_package_path() -> Optional[str]:
    package = sys.modules.get("neural")
    return str(getattr(package, "__file__", None) or getattr(package, "__path__", [""])[0] or "") if package else None


def _selected_value_checkpoint_path() -> Path:
    mode = _env_model_mode()
    if mode == "public-replay":
        return _env_value_checkpoint(OLD_VALUE_MODEL_PATH)
    env_override = os.environ.get("NEURAL_LIVE_VALUE_CHECKPOINT", "").strip()
    if env_override:
        return Path(env_override)
    if LIVE_PRIVATE_VALUE_MODEL_V2_PATH != _CANONICAL_LIVE_PRIVATE_VALUE_MODEL_V2_PATH and LIVE_PRIVATE_VALUE_MODEL_V2_PATH.exists():
        return LIVE_PRIVATE_VALUE_MODEL_V2_PATH
    if LIVE_PRIVATE_VALUE_MODEL_PATH != _CANONICAL_LIVE_PRIVATE_VALUE_MODEL_PATH:
        return LIVE_PRIVATE_VALUE_MODEL_PATH
    return LIVE_PRIVATE_VALUE_MODEL_V2_PATH if LIVE_PRIVATE_VALUE_MODEL_V2_PATH.exists() else LIVE_PRIVATE_VALUE_MODEL_PATH


def _selected_action_ranker_path() -> Optional[str]:
    try:
        env_path = os.environ.get("NEURAL_ACTION_RANKER_CHECKPOINT", "").strip()
        if env_path:
            return env_path
        value_ranker = getattr(live_action_recommender_module, "DEFAULT_ACTION_VALUE_RANKER_V2_PATH", None)
        if value_ranker is not None and Path(value_ranker).exists():
            return str(value_ranker)
        ranker = getattr(live_action_recommender_module, "DEFAULT_ACTION_RANKER_PATH", None)
        return str(ranker) if ranker is not None else None
    except Exception as exc:
        return f"unavailable:{type(exc).__name__}:{exc}"


def _checkpoint_summary(path: Optional[Path]) -> Dict[str, Any]:
    summary: Dict[str, Any] = {
        "path": str(path) if path is not None else None,
        "exists": bool(path is not None and path.exists()),
    }
    if path is None or not path.exists():
        return summary

    try:
        stat = path.stat()
        summary.update(
            {
                "size_bytes": stat.st_size,
                "mtime_epoch": stat.st_mtime,
                "mtime_iso": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
            }
        )
    except OSError as exc:
        summary["stat_error"] = f"{type(exc).__name__}: {exc}"

    try:
        checkpoint = torch_load(path, torch.device("cpu"))
    except Exception as exc:
        summary["load_error"] = f"{type(exc).__name__}: {exc}"
        return summary

    if isinstance(checkpoint, dict):
        metadata_keys = (
            "model_type",
            "source",
            "checkpoint_type",
            "training_objective",
            "input_size",
            "hidden_sizes",
            "action_size",
            "feature_version",
            "state_dim",
            "action_dim",
            "action_feature_version",
            "state_feature_version",
            "response_method",
            "saved_at",
            "epoch",
            "global_step",
        )
        summary["metadata"] = {key: checkpoint.get(key) for key in metadata_keys if key in checkpoint}
    else:
        summary["metadata"] = {"checkpoint_type": type(checkpoint).__name__}
    return summary


def _selected_action_ranker_checkpoint_path() -> Optional[Path]:
    selected = _selected_action_ranker_path()
    if not selected or selected.startswith("unavailable:"):
        return None
    return Path(selected)


def _port_owner_lines(port: int) -> List[str]:
    try:
        proc = subprocess.run(
            ["netstat", "-ano"],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=5,
            check=False,
        )
        needle = f":{port}"
        return [line.strip() for line in proc.stdout.splitlines() if needle in line]
    except Exception as exc:
        return [f"netstat failed: {type(exc).__name__}: {exc}"]


def _check_port_available(host: str, port: int) -> Tuple[bool, List[str]]:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
            return True, []
        except OSError:
            return False, _port_owner_lines(port)


def _sample_damage_result() -> Dict[str, Any]:
    cases: Dict[str, Any] = {}
    try:
        result = damage_engine.estimate_damage(
            attacker={"species": "Banette", "level": 80},
            defender={"species": "Kingambit", "level": 80, "hp_fraction": 1.0},
            move="Gunk Shot",
        )
        cases["banette_gunk_shot_into_kingambit"] = {
            "ok": result.get("damage_method") == "smogon_calc" and bool(result.get("immune")) and result.get("type_effectiveness") == 0,
            "result": result,
        }
        earthquake = damage_engine.estimate_damage(
            attacker={"species": "Quagsire", "level": 80},
            defender={"species": "Vivillon-Ocean", "level": 80, "hp_fraction": 1.0},
            move="Earthquake",
        )
        cases["quagsire_earthquake_into_vivillon_ocean"] = {
            "ok": earthquake.get("damage_method") == "smogon_calc" and bool(earthquake.get("immune")) and earthquake.get("type_effectiveness") == 0,
            "result": earthquake,
        }
        hurricane = damage_engine.estimate_damage(
            attacker={"species": "Vivillon-Ocean", "level": 80},
            defender={"species": "Quagsire", "level": 80, "hp_fraction": 1.0},
            move="Hurricane",
        )
        cases["vivillon_ocean_hurricane_into_quagsire"] = {
            "ok": hurricane.get("damage_method") == "smogon_calc" and float(hurricane.get("average_percent") or 0.0) > 0.0,
            "result": hurricane,
        }
        sleep_powder = damage_engine.estimate_damage(
            attacker={"species": "Vivillon-Ocean", "level": 80},
            defender={"species": "Quagsire", "level": 80, "hp_fraction": 1.0},
            move="Sleep Powder",
        )
        cases["sleep_powder_non_damaging"] = {
            "ok": sleep_powder.get("damage_method") == "non_damaging_move" and sleep_powder.get("type_effectiveness") is None,
            "result": sleep_powder,
        }
        try:
            from neural.sim_branch_evaluator import _damage_diagnostics
        except ImportError:
            from trainer.src.neural.sim_branch_evaluator import _damage_diagnostics
        switch_diag = _damage_diagnostics({"kind": "switch", "label": "switch: Pikachu"}, {})
        cases["switch_diagnostic"] = {
            "ok": switch_diag.get("damage_method") == "not_applicable_switch" and switch_diag.get("type_effectiveness") is None,
            "result": switch_diag,
        }
        ok = all(bool(case.get("ok")) for case in cases.values())
        return {"ok": ok, "result": result, "cases": cases}
    except Exception as exc:
        return {"ok": False, "cases": cases, "exception": {"type": type(exc).__name__, "message": str(exc)}}


def _sim_core_damage_rpc_status() -> Dict[str, Any]:
    cwd = os.environ.get("NEURAL_SIM_CORE_CWD", "").strip()
    command_json = os.environ.get("NEURAL_SIM_CORE_COMMAND_JSON", "").strip()
    status: Dict[str, Any] = {
        "configured": bool(cwd and command_json),
        "cwd": cwd or None,
        "command_json": command_json or None,
    }
    if not cwd or not command_json:
        status["reachable"] = False
        status["reason"] = "NEURAL_SIM_CORE_CWD or NEURAL_SIM_CORE_COMMAND_JSON is not set."
        return status
    try:
        command = json.loads(command_json)
        if not isinstance(command, list) or not all(isinstance(item, str) for item in command):
            raise ValueError("NEURAL_SIM_CORE_COMMAND_JSON must decode to a list of strings.")
        with SimCoreClient(command, cwd) as client:
            result = client.damage_estimate(
                {
                    "attacker": {"species": "Banette", "level": 80},
                    "defender": {"species": "Kingambit", "level": 80, "hp_fraction": 1.0},
                    "move": "Gunk Shot",
                    "use_tera": False,
                },
                timeout_sec=15,
            )
        status["reachable"] = True
        status["sample"] = result
        status["ok"] = result.get("damage_method") == "smogon_calc" and bool(result.get("immune")) and result.get("type_effectiveness") == 0
    except Exception as exc:
        status["reachable"] = False
        status["exception"] = {"type": type(exc).__name__, "message": str(exc)}
    return status


def live_eval_diagnostics(*, check_rpc: bool = True, check_damage: bool = True, check_port: bool = False, port: int = 8765) -> Dict[str, Any]:
    value_checkpoint = _selected_value_checkpoint_path()
    action_ranker_checkpoint = _selected_action_ranker_checkpoint_path()
    diagnostics: Dict[str, Any] = {
        "python_executable": sys.executable,
        "sys_path_first_entries": sys.path[:8],
        "neural_package_path": _neural_package_path(),
        "live_eval_server_file": __file__,
        "damage_engine_file": getattr(damage_engine, "__file__", None),
        "git_branch": _git_branch(),
        "model": {
            "mode": os.environ.get("NEURAL_LIVE_MODEL", "live-private"),
            "value_checkpoint": str(value_checkpoint),
            "value_checkpoint_exists": value_checkpoint.exists(),
            "policy_checkpoint": str(REPLAY_POLICY_MODEL_PATH),
            "policy_checkpoint_exists": REPLAY_POLICY_MODEL_PATH.exists(),
            "action_ranker_checkpoint": _selected_action_ranker_path(),
        },
        "selected_checkpoints": {
            "value": _checkpoint_summary(value_checkpoint),
            "policy": _checkpoint_summary(REPLAY_POLICY_MODEL_PATH),
            "action_ranker": _checkpoint_summary(action_ranker_checkpoint),
        },
        "features": {
            "action_feature_dim": ACTION_FEATURE_DIM,
            "live_private_feature_version": LIVE_PRIVATE_FEATURE_VERSION,
            "live_private_feature_dim": LIVE_PRIVATE_FEATURE_DIM,
            "public_feature_version": FEATURE_VERSION,
            "public_feature_dim": INPUT_SIZE,
        },
        "environment": {
            "NEURAL_SIM_CORE_CWD": os.environ.get("NEURAL_SIM_CORE_CWD"),
            "NEURAL_SIM_CORE_COMMAND_JSON": os.environ.get("NEURAL_SIM_CORE_COMMAND_JSON"),
            "PYTHONPATH": os.environ.get("PYTHONPATH"),
            "NEURAL_STRICT_LIVE_EVAL": os.environ.get("NEURAL_STRICT_LIVE_EVAL"),
        },
        "strict_live_eval": {"enabled": _env_flag("NEURAL_STRICT_LIVE_EVAL")},
    }
    if check_rpc:
        diagnostics["sim_core_damage_rpc"] = _sim_core_damage_rpc_status()
    if check_damage:
        diagnostics["damage_engine_smoke"] = _sample_damage_result()
    if check_port:
        available, owners = _check_port_available("127.0.0.1", port)
        diagnostics["port"] = {"host": "127.0.0.1", "port": port, "available": available, "owners": owners}
    return diagnostics


def _metadata(summary: Dict[str, Any]) -> Dict[str, Any]:
    metadata = summary.get("metadata")
    return metadata if isinstance(metadata, dict) else {}


def _contains_heuristic_fallback(value: Any) -> bool:
    if isinstance(value, dict):
        if value.get("damage_method") == "heuristic_fallback":
            return True
        return any(_contains_heuristic_fallback(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_heuristic_fallback(item) for item in value)
    if isinstance(value, str):
        return "heuristic_fallback" in value
    return False


def _strict_live_eval_errors(diagnostics: Dict[str, Any]) -> List[str]:
    checkpoints = diagnostics.get("selected_checkpoints") if isinstance(diagnostics.get("selected_checkpoints"), dict) else {}
    value_summary = checkpoints.get("value") if isinstance(checkpoints.get("value"), dict) else {}
    action_summary = checkpoints.get("action_ranker") if isinstance(checkpoints.get("action_ranker"), dict) else {}
    value_metadata = _metadata(value_summary)
    action_metadata = _metadata(action_summary)
    errors: List[str] = []

    if _env_model_mode() != "live-private":
        errors.append("NEURAL_LIVE_MODEL must select live-private mode when NEURAL_STRICT_LIVE_EVAL=1.")
    if not value_summary.get("exists"):
        errors.append(f"Live-private value checkpoint is missing: {value_summary.get('path')}")
    if value_summary.get("load_error"):
        errors.append(f"Live-private value checkpoint could not be loaded: {value_summary.get('load_error')}")
    if value_metadata.get("feature_version") != LIVE_PRIVATE_FEATURE_VERSION:
        errors.append(
            f"Live-private value checkpoint feature_version={value_metadata.get('feature_version')!r}; "
            f"expected {LIVE_PRIVATE_FEATURE_VERSION!r}."
        )

    if not action_summary.get("exists"):
        errors.append(f"Action-value ranker checkpoint is missing: {action_summary.get('path')}")
    if action_summary.get("load_error"):
        errors.append(f"Action-value ranker checkpoint could not be loaded: {action_summary.get('load_error')}")
    model_type = str(action_metadata.get("model_type") or "").lower()
    response_method = str(action_metadata.get("response_method") or "").lower()
    if model_type != "action-value-ranker" and response_method != "action_value_ranker":
        errors.append(
            "Selected action ranker must be an action-value ranker "
            f"(model_type={action_metadata.get('model_type')!r}, response_method={action_metadata.get('response_method')!r})."
        )
    try:
        input_size = int(action_metadata.get("input_size"))
        state_dim = int(action_metadata.get("state_dim"))
        action_dim = int(action_metadata.get("action_dim"))
        if input_size != state_dim + action_dim:
            errors.append(f"Action-value ranker input_size={input_size}; expected state_dim + action_dim = {state_dim + action_dim}.")
        if action_dim != ACTION_FEATURE_DIM:
            errors.append(f"Action-value ranker action_dim={action_dim}; expected current ACTION_FEATURE_DIM={ACTION_FEATURE_DIM}.")
        if state_dim != LIVE_PRIVATE_FEATURE_DIM:
            errors.append(f"Action-value ranker state_dim={state_dim}; expected current LIVE_PRIVATE_FEATURE_DIM={LIVE_PRIVATE_FEATURE_DIM}.")
    except (TypeError, ValueError):
        errors.append(
            "Action-value ranker metadata must include integer input_size, state_dim, and action_dim "
            f"(metadata={action_metadata})."
        )

    rpc_status = diagnostics.get("sim_core_damage_rpc") if isinstance(diagnostics.get("sim_core_damage_rpc"), dict) else {}
    if not rpc_status.get("reachable"):
        reason = rpc_status.get("reason") or rpc_status.get("exception")
        errors.append(f"sim-core is not reachable: {reason}")
    rpc_sample = rpc_status.get("sample") if isinstance(rpc_status.get("sample"), dict) else {}
    if rpc_sample and rpc_sample.get("damage_method") != "smogon_calc":
        errors.append(f"sim-core damage RPC returned damage_method={rpc_sample.get('damage_method')!r}; expected 'smogon_calc'.")

    smoke = diagnostics.get("damage_engine_smoke") if isinstance(diagnostics.get("damage_engine_smoke"), dict) else {}
    smoke_result = smoke.get("result") if isinstance(smoke.get("result"), dict) else {}
    if smoke_result.get("damage_method") != "smogon_calc":
        errors.append(f"Smogon damage healthcheck returned damage_method={smoke_result.get('damage_method')!r}; expected 'smogon_calc'.")
    if _contains_heuristic_fallback(smoke) or _contains_heuristic_fallback(rpc_status):
        errors.append("Startup smoke test used heuristic_fallback; strict live eval requires Smogon/sim-core damage paths only.")

    return errors


def enforce_strict_live_eval_startup(diagnostics: Dict[str, Any]) -> None:
    if not _env_flag("NEURAL_STRICT_LIVE_EVAL"):
        return
    errors = _strict_live_eval_errors(diagnostics)
    if errors:
        print("ERROR: NEURAL_STRICT_LIVE_EVAL startup validation failed:", flush=True)
        for error in errors:
            print(f"  - {error}", flush=True)
        raise SystemExit(1)
    print("NEURAL_STRICT_LIVE_EVAL startup validation passed.", flush=True)


def print_startup_diagnostics(*, port: int = 8765) -> Dict[str, Any]:
    diagnostics = live_eval_diagnostics(check_rpc=True, check_damage=True, check_port=True, port=port)
    print("=== neural.live_eval_server startup diagnostics ===", flush=True)
    print(json.dumps(diagnostics, indent=2, default=str), flush=True)
    enforce_strict_live_eval_startup(diagnostics)
    smoke = diagnostics.get("damage_engine_smoke", {})
    result = smoke.get("result", {}) if isinstance(smoke, dict) else {}
    if not smoke.get("ok"):
        print(
            "WARNING: damage_engine startup smoke did not return smogon_calc immune=true type_effectiveness=0.",
            flush=True,
        )
        print(
            json.dumps(
                {
                    "damage_method": result.get("damage_method"),
                    "warnings": result.get("warnings"),
                    "exception": smoke.get("exception"),
                    "sim_core_config": diagnostics.get("environment"),
                },
                indent=2,
                default=str,
            ),
            flush=True,
        )
    return diagnostics


def _env_model_mode() -> str:
    mode = os.environ.get("NEURAL_LIVE_MODEL", "live-private").strip().lower()
    if mode in ("live-private", "live_private", "private", "live-private-belief"):
        return "live-private"
    if mode in ("public-replay", "public_replay", "public", "replay"):
        return "public-replay"
    raise ValueError("NEURAL_LIVE_MODEL must be 'live-private' or 'public-replay'.")


def _env_value_checkpoint(default_path: Path) -> Path:
    override = os.environ.get("NEURAL_LIVE_VALUE_CHECKPOINT", "").strip()
    return Path(override) if override else default_path


def _checkpoint_state_dict(checkpoint: Any) -> Dict[str, Any]:
    if isinstance(checkpoint, dict):
        return (
            checkpoint.get("model_state_dict")
            or checkpoint.get("state_dict")
            or checkpoint.get("model")
            or checkpoint
        )
    return checkpoint


def _load_policy_value_model(path: Path, *, default_input_size: int) -> Tuple[PolicyValueMLP, Dict[str, Any]]:
    checkpoint = torch_load(path, DEVICE)
    if isinstance(checkpoint, dict):
        state_dict = _checkpoint_state_dict(checkpoint)
        input_size = int(checkpoint.get("input_size") or default_input_size)
        hidden_sizes = (
            checkpoint.get("hidden_sizes")
            or checkpoint.get("model_config", {}).get("hidden_sizes")
            or checkpoint.get("config", {}).get("hidden_sizes")
            or HIDDEN_SIZES
        )
        action_size = int(checkpoint.get("action_size", ACTION_SIZE))
        metadata = dict(checkpoint)
    else:
        state_dict = checkpoint
        input_size = default_input_size
        hidden_sizes = HIDDEN_SIZES
        action_size = ACTION_SIZE
        metadata = {}

    model = PolicyValueMLP(input_size=input_size, hidden_sizes=hidden_sizes, action_size=action_size)
    model.load_state_dict(state_dict, strict=False)
    model.to(DEVICE)
    model.eval()
    metadata.update({"input_size": input_size, "hidden_sizes": list(hidden_sizes), "action_size": action_size})
    return model, metadata


def _validate_live_private_checkpoint(metadata: Dict[str, Any], path: Path) -> None:
    input_size = int(metadata.get("input_size", 0) or 0)
    allowed_dims = {LIVE_PRIVATE_FEATURE_DIM, LIVE_PRIVATE_FEATURE_DIM_V1}
    if input_size not in allowed_dims:
        raise ValueError(
            f"Live-private checkpoint {path} has input_size={input_size}; "
            f"expected one of {sorted(allowed_dims)} for live-private features."
        )
    feature_version = metadata.get("feature_version")
    allowed_versions = {LIVE_PRIVATE_FEATURE_VERSION, LIVE_PRIVATE_FEATURE_VERSION_V1}
    if feature_version is not None and str(feature_version) not in allowed_versions:
        raise ValueError(
            f"Live-private checkpoint {path} has feature_version={feature_version!r}; "
            f"expected one of {sorted(allowed_versions)!r}."
        )


def _checkpoint_is_policy(metadata: Dict[str, Any], path: Path) -> bool:
    text = " ".join(
        str(metadata.get(key, ""))
        for key in ("task", "source", "model_type", "checkpoint_type", "training_objective")
    ).lower()
    return "policy" in text or "replay_policy" in path.name.lower() or "public_policy" in path.name.lower()


def reset_model_caches() -> None:
    global _value_model, _value_model_metadata, _policy_model, _policy_model_metadata
    _value_model = None
    _value_model_metadata = None
    _policy_model = None
    _policy_model_metadata = None
    reset_action_ranker_cache()


def load_value_model_once() -> Tuple[PolicyValueMLP, Dict[str, Any]]:
    global _value_model, _value_model_metadata
    if _value_model is not None and _value_model_metadata is not None:
        return _value_model, _value_model_metadata

    mode = _env_model_mode()
    fallback_reason = None

    if mode == "public-replay":
        path = _env_value_checkpoint(OLD_VALUE_MODEL_PATH)
        model, metadata = _load_policy_value_model(path, default_input_size=INPUT_SIZE)
        fallback_reason = "NEURAL_LIVE_MODEL=public-replay"
        metadata.update(
            {
                "path": str(path),
                "model_type": "public-replay-value",
                "feature_version": FEATURE_VERSION,
                "uses_live_private_features": False,
                "fallback_reason": fallback_reason,
            }
        )
    else:
        env_override = os.environ.get("NEURAL_LIVE_VALUE_CHECKPOINT", "").strip()
        if env_override:
            live_path = Path(env_override)
        elif LIVE_PRIVATE_VALUE_MODEL_V2_PATH != _CANONICAL_LIVE_PRIVATE_VALUE_MODEL_V2_PATH and LIVE_PRIVATE_VALUE_MODEL_V2_PATH.exists():
            live_path = LIVE_PRIVATE_VALUE_MODEL_V2_PATH
        elif LIVE_PRIVATE_VALUE_MODEL_PATH != _CANONICAL_LIVE_PRIVATE_VALUE_MODEL_PATH:
            live_path = LIVE_PRIVATE_VALUE_MODEL_PATH
        else:
            live_path = LIVE_PRIVATE_VALUE_MODEL_V2_PATH if LIVE_PRIVATE_VALUE_MODEL_V2_PATH.exists() else LIVE_PRIVATE_VALUE_MODEL_PATH
        if live_path.exists():
            model, metadata = _load_policy_value_model(live_path, default_input_size=LIVE_PRIVATE_FEATURE_DIM)
            _validate_live_private_checkpoint(metadata, live_path)
            metadata.update(
                {
                    "path": str(live_path),
                    "model_type": "live-private-belief-value",
                    "feature_version": metadata.get("feature_version")
                    or (LIVE_PRIVATE_FEATURE_VERSION if int(metadata.get("input_size", 0) or 0) == LIVE_PRIVATE_FEATURE_DIM else LIVE_PRIVATE_FEATURE_VERSION_V1),
                    "uses_live_private_features": True,
                    "fallback_reason": None,
                }
            )
        else:
            fallback_reason = f"Live-private checkpoint missing: {live_path}"
            model, metadata = _load_policy_value_model(OLD_VALUE_MODEL_PATH, default_input_size=INPUT_SIZE)
            metadata.update(
                {
                    "path": str(OLD_VALUE_MODEL_PATH),
                    "model_type": "public-replay-value",
                    "feature_version": FEATURE_VERSION,
                    "uses_live_private_features": False,
                    "fallback_reason": fallback_reason,
                }
            )

    _value_model = model
    _value_model_metadata = metadata
    return model, metadata


def load_policy_model_once() -> Tuple[Optional[PolicyValueMLP], Optional[Dict[str, Any]]]:
    global _policy_model, _policy_model_metadata
    if _policy_model is not None or _policy_model_metadata is not None:
        return _policy_model, _policy_model_metadata
    if not REPLAY_POLICY_MODEL_PATH.exists():
        _policy_model_metadata = {"warning": f"Policy checkpoint missing: {REPLAY_POLICY_MODEL_PATH}"}
        return None, _policy_model_metadata
    model, metadata = _load_policy_value_model(REPLAY_POLICY_MODEL_PATH, default_input_size=INPUT_SIZE)
    if not _checkpoint_is_policy(metadata, REPLAY_POLICY_MODEL_PATH):
        _policy_model_metadata = {
            "path": str(REPLAY_POLICY_MODEL_PATH),
            "warning": f"Checkpoint is not marked as a policy model: {REPLAY_POLICY_MODEL_PATH}",
        }
        return None, _policy_model_metadata
    metadata.update({"path": str(REPLAY_POLICY_MODEL_PATH), "model_type": "replay-policy"})
    _policy_model = model
    _policy_model_metadata = metadata
    return _policy_model, _policy_model_metadata


def _trajectory_from_live_payload(payload: EvalRequest) -> Dict[str, Any]:
    return parse_protocol_log(
        payload.log,
        replay_id=payload.room_id,
        format_name="gen9randombattle",
        source_path=payload.url,
        metadata={"source": "live_eval", "player": payload.player or ""},
    )


def _latest_turn_from_trajectory(trajectory: Dict[str, Any]) -> int:
    turns = trajectory.get("turns") if isinstance(trajectory.get("turns"), list) else []
    if not turns:
        return 0
    return max(int(record.get("turn", 0) or 0) for record in turns if isinstance(record, dict))


def build_features_from_payload(payload: EvalRequest) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Build the unchanged 31D public replay-event feature vector."""
    trajectory = _trajectory_from_live_payload(payload)
    state = _initial_state(trajectory)
    recent = _new_recent()
    latest_turn = 0

    turn_records = trajectory.get("turns") if isinstance(trajectory.get("turns"), list) else []
    for turn_record in sorted(turn_records, key=lambda item: int(item.get("turn", 0) or 0)):
        latest_turn = int(turn_record.get("turn", 0) or 0)
        recent = _new_recent()
        events = turn_record.get("events") if isinstance(turn_record.get("events"), list) else []
        for event in events:
            if isinstance(event, dict):
                _apply_event(state, recent, event)

    features = _feature_vector(state, recent, latest_turn)
    if features.ndim != 1 or features.shape[0] != INPUT_SIZE:
        raise ValueError(
            f"Feature size mismatch: got {features.shape[0]}, expected {INPUT_SIZE}. "
            f"Feature version={FEATURE_VERSION}"
        )

    debug = {
        "room_id": payload.room_id,
        "player": payload.player,
        "log_length": len(payload.log),
        "latest_turn": _latest_turn_from_trajectory(trajectory),
        "feature_version": FEATURE_VERSION,
        "feature_names_preview": FEATURE_NAMES[:DEBUG_FEATURE_PREVIEW],
        "feature_values_preview": [float(v) for v in features[:DEBUG_FEATURE_PREVIEW].tolist()],
    }
    return features.astype(np.float32), debug


def _legal_action_to_dict(action: LegalAction) -> Dict[str, Any]:
    if isinstance(action, dict):
        return dict(action)
    if hasattr(action, "model_dump"):
        return action.model_dump()
    return action.dict()


def _player_side_from_private_state(private_state: Dict[str, Any]) -> Optional[str]:
    side = private_state.get("player_side")
    if side in ("p1", "p2"):
        return str(side)
    return None


def _request_active_moves(request_payload: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(request_payload, dict):
        return []
    active = request_payload.get("active")
    active_block = active[0] if isinstance(active, list) and active else active if isinstance(active, dict) else {}
    moves = active_block.get("moves") if isinstance(active_block, dict) else None
    if not isinstance(moves, list):
        return []
    result = []
    for index, move in enumerate(moves):
        if not isinstance(move, dict):
            continue
        name = move.get("move") or move.get("name") or move.get("id") or f"move {index + 1}"
        result.append(
            {
                "index": index,
                "kind": "move",
                "label": f"move: {name}",
                "prob": None,
                "disabled": bool(move.get("disabled", False)),
            }
        )
    return result


def _request_switches(request_payload: Optional[Dict[str, Any]], existing_labels: Sequence[str]) -> List[Dict[str, Any]]:
    if not isinstance(request_payload, dict):
        return []
    side = request_payload.get("side") if isinstance(request_payload.get("side"), dict) else {}
    team = side.get("pokemon") if isinstance(side.get("pokemon"), list) else []
    existing = {label.lower() for label in existing_labels}
    switches = []
    for slot, mon in enumerate(team):
        if not isinstance(mon, dict):
            continue
        if mon.get("active") or mon.get("fainted") or "fnt" in str(mon.get("condition", "")):
            continue
        details = str(mon.get("details") or mon.get("ident") or f"slot {slot + 1}")
        species = details.split(",", 1)[0].split(": ", 1)[-1].strip()
        label = f"switch: {species}"
        if label.lower() in existing:
            continue
        switches.append({"index": 8 + max(0, slot - 1), "kind": "switch", "label": label, "prob": None, "disabled": False})
    return switches


def legal_action_candidates(payload: EvalRequest) -> List[Dict[str, Any]]:
    return _recommend_action_candidates(payload)


def _policy_features_for_model(
    *,
    policy_metadata: Dict[str, Any],
    public_features: np.ndarray,
    live_features: np.ndarray,
) -> np.ndarray:
    input_size = int(policy_metadata.get("input_size", INPUT_SIZE))
    if input_size == live_features.shape[0]:
        return live_features.astype(np.float32)
    if input_size == public_features.shape[0]:
        return public_features.astype(np.float32)
    selected = live_features if live_features.shape[0] < input_size else live_features[:input_size]
    if selected.shape[0] == input_size:
        return selected.astype(np.float32)
    padded = np.zeros(input_size, dtype=np.float32)
    padded[: selected.shape[0]] = selected
    return padded


def _value_features_for_model(*, model_metadata: Dict[str, Any], public_features: np.ndarray, live_features: np.ndarray) -> np.ndarray:
    input_size = int(model_metadata.get("input_size", len(live_features)))
    if input_size == live_features.shape[0]:
        return live_features.astype(np.float32)
    if input_size == public_features.shape[0]:
        return public_features.astype(np.float32)
    selected = live_features if live_features.shape[0] < input_size else live_features[:input_size]
    if selected.shape[0] == input_size:
        return selected.astype(np.float32)
    padded = np.zeros(input_size, dtype=np.float32)
    padded[: selected.shape[0]] = selected
    return padded


def build_top_actions(
    payload: EvalRequest,
    *,
    public_features: np.ndarray,
    live_features: np.ndarray,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    candidates = legal_action_candidates(payload)
    warnings: List[str] = []
    policy_model, policy_metadata = load_policy_model_once()
    if not candidates:
        return [], warnings
    if policy_model is None or not policy_metadata or policy_metadata.get("warning"):
        warnings.append(str((policy_metadata or {}).get("warning") or "Policy checkpoint missing."))
        legal_candidates = [candidate for candidate in candidates if not candidate.get("disabled")]
        probability = 1.0 / float(len(legal_candidates) or len(candidates))
        for candidate in candidates:
            candidate["prob"] = 0.0 if candidate.get("disabled") else probability
        return sorted(candidates, key=lambda item: item["prob"], reverse=True)[:5], warnings

    features = _policy_features_for_model(
        policy_metadata=policy_metadata,
        public_features=public_features,
        live_features=live_features,
    )
    x = torch.tensor(features, dtype=torch.float32, device=DEVICE).unsqueeze(0)
    with torch.no_grad():
        policy_logits, _ = policy_model(x)
        probs = torch.softmax(policy_logits.squeeze(0), dim=0).detach().cpu().numpy()

    for candidate in candidates:
        index = int(candidate.get("index", 0) or 0)
        candidate["prob"] = float(probs[index]) if 0 <= index < len(probs) and not candidate.get("disabled") else 0.0
    return sorted(candidates, key=lambda item: item["prob"], reverse=True)[:5], warnings


def evaluate_with_model(payload: EvalRequest) -> Dict[str, Any]:
    model, model_metadata = load_value_model_once()

    public_features, public_feature_debug = build_features_from_payload(payload)
    legal_action_payload = [_legal_action_to_dict(action) for action in payload.legal_actions]
    private_state = extract_private_side_state(
        request_payload=payload.request,
        legal_actions=legal_action_payload,
        player_hint=payload.player,
    )
    player_side = _player_side_from_private_state(private_state)
    trajectory = _trajectory_from_live_payload(payload)
    opponent_beliefs = build_opponent_beliefs(
        protocol_log=payload.log,
        trajectory=trajectory,
        player_side=player_side,
    )
    live_features, live_feature_debug, private_state, opponent_beliefs, trajectory = build_features_from_live_payload(
        log=payload.log,
        room_id=payload.room_id,
        url=payload.url,
        player=payload.player,
        request_payload=payload.request,
        legal_actions=legal_action_payload,
    )
    player_side = _player_side_from_private_state(private_state)

    if model_metadata.get("uses_live_private_features"):
        features = _value_features_for_model(
            model_metadata=model_metadata,
            public_features=public_features,
            live_features=live_features,
        )
        feature_debug = live_feature_debug
    else:
        features = public_features
        feature_debug = public_feature_debug

    x = torch.tensor(features, dtype=torch.float32, device=DEVICE).unsqueeze(0)
    with torch.no_grad():
        output = model(x)

    if isinstance(output, tuple):
        _, value_tensor = output
    elif isinstance(output, dict):
        value_tensor = output.get("value")
    else:
        value_tensor = output

    value = float(value_tensor.squeeze().cpu().item())
    p1_win_prob = max(0.0, min(1.0, (value + 1.0) / 2.0))
    p2_win_prob = 1.0 - p1_win_prob
    action_report = recommend_actions(
        payload=payload,
        private_state=private_state,
        opponent_belief=opponent_beliefs,
        trajectory=trajectory,
        public_features=public_features,
        live_features=live_features,
        current_value=value,
        value_model=model,
        value_metadata=model_metadata,
        policy_loader=load_policy_model_once,
        device=DEVICE,
    )

    used_live = bool(model_metadata.get("uses_live_private_features"))
    policy_warnings = list(action_report.get("warnings", []))
    action_estimates = action_report.get("all_action_estimates", [])
    damage_methods = {
        str(action.get("damage_method"))
        for action in action_estimates
        if isinstance(action, dict) and action.get("damage_method") is not None
    }
    damage_engine_status = "fallback_present" if "heuristic_fallback" in damage_methods else "ok"
    debug_summary = {
        "selected_value_model_path": model_metadata.get("path"),
        "selected_action_ranker_path": action_report.get("action_ranker_path"),
        "selected_policy_path": action_report.get("policy_checkpoint_path") or str(REPLAY_POLICY_MODEL_PATH),
        "feature_version": model_metadata.get("feature_version"),
        "feature_dim": int(model_metadata.get("input_size", len(features))),
        "action_feature_dim": ACTION_FEATURE_DIM,
        "action_ranker_input_size": action_report.get("action_ranker_input_size"),
        "damage_engine_status": damage_engine_status,
        "smogon_calc_available": "smogon_calc" in damage_methods,
        "rollout_mode": action_report.get("rollout_mode"),
        "rollouts_per_action": action_report.get("rollouts_per_action"),
        "rollout_weight": action_report.get("rollout_weight"),
        "ranker_weight": action_report.get("ranker_weight"),
        "policy_weight": action_report.get("policy_weight"),
        "top_action_by_ranker": action_report.get("top_action_by_ranker"),
        "top_action_by_rollout": action_report.get("top_action_by_rollout"),
        "top_action_by_final_score": action_report.get("top_action_by_final_score"),
        "action_category_counts": action_report.get("action_category_counts", {}),
    }
    return {
        "p1_win_prob": p1_win_prob,
        "p2_win_prob": p2_win_prob,
        "value": value,
        "top_actions": action_report.get("top_actions", []),
        "action_recommendation_method": action_report.get("action_recommendation_method"),
        "policy_checkpoint_loaded": bool(action_report.get("policy_checkpoint_loaded")),
        "policy_checkpoint_path": action_report.get("policy_checkpoint_path"),
        "action_ranker_loaded": bool(action_report.get("action_ranker_loaded")),
        "action_ranker_path": action_report.get("action_ranker_path"),
        "model_type": model_metadata.get("model_type"),
        "checkpoint_path": model_metadata.get("path"),
        "feature_version": model_metadata.get("feature_version"),
        "feature_dim": int(model_metadata.get("input_size", len(features))),
        "used_private_state": bool(used_live and private_state.get("team")),
        "used_opponent_belief": bool(used_live and opponent_beliefs.get("opponents")),
        "fallback_reason": model_metadata.get("fallback_reason"),
        "warning": "; ".join(policy_warnings) if policy_warnings else None,
        "debug_summary": debug_summary,
        "debug": {
            **feature_debug,
            "model_path": model_metadata.get("path"),
            "player_side": player_side,
            "known": {"private_state": private_state},
            "inferred": {"opponent_beliefs": opponent_beliefs.get("opponents", [])},
            "unknown": {"opponent_unknowns": opponent_beliefs.get("unknowns", [])},
            "tera": {
                "can_tera": bool(private_state.get("can_tera")),
                "tera_used": bool(private_state.get("tera_used")),
                "active_tera_type": private_state.get("active_tera_type"),
                "legal_tera_actions": [
                    action for action in action_report.get("all_action_estimates", []) if str(action.get("kind")) == "move_tera"
                ],
            },
            "belief_source": opponent_beliefs.get("source"),
            "belief_warnings": opponent_beliefs.get("warnings", []),
            "all_action_estimates": action_estimates,
        },
    }


@app.post("/evaluate")
def evaluate(payload: EvalRequest):
    return evaluate_with_model(payload)


if __name__ == "__main__":
    port = int(os.environ.get("NEURAL_LIVE_EVAL_PORT", "8765"))
    diagnostics = print_startup_diagnostics(port=port)
    port_info = diagnostics.get("port", {}) if isinstance(diagnostics.get("port"), dict) else {}
    if port_info and not port_info.get("available", True):
        print(f"ERROR: 127.0.0.1:{port} is already in use.", flush=True)
        owners = port_info.get("owners") or []
        if owners:
            print("Existing process line(s) from netstat:", flush=True)
            for line in owners:
                print(f"  {line}", flush=True)
        print("To inspect on Windows: netstat -ano | findstr :8765", flush=True)
        print("To stop a conflicting process: Stop-Process -Id <PID> -Force", flush=True)
        raise SystemExit(1)
    uvicorn.run(app, host="127.0.0.1", port=port)
