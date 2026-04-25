import json
import os
from pathlib import Path
from typing import Any, Dict, Sequence, Tuple


def load_config(path: str) -> Dict[str, Any]:
    config_path = Path(path).resolve()
    text = config_path.read_text(encoding="utf-8")

    try:
        config = json.loads(text)
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "Config is not valid JSON, and PyYAML is not installed for YAML parsing."
            ) from exc
        config = yaml.safe_load(text)

    if not isinstance(config, dict):
        raise ValueError(f"Config at {config_path} must decode to an object.")

    config["_config_path"] = str(config_path)
    return config


def resolve_path(config: Dict[str, Any], value: str) -> Path:
    base = Path(config["_config_path"]).resolve().parent
    path = Path(value)
    return (base / path).resolve() if not path.is_absolute() else path


def resolve_process_spec(config: Dict[str, Any]) -> Tuple[Sequence[str], str]:
    env_command = os.environ.get("NEURAL_SIM_CORE_COMMAND_JSON")
    env_cwd = os.environ.get("NEURAL_SIM_CORE_CWD")
    if env_command:
        try:
            command = json.loads(env_command)
        except json.JSONDecodeError as exc:
            raise ValueError("NEURAL_SIM_CORE_COMMAND_JSON must be valid JSON.") from exc
        if not isinstance(command, list) or not all(isinstance(item, str) for item in command):
            raise ValueError("NEURAL_SIM_CORE_COMMAND_JSON must decode to a list of strings.")
        if not env_cwd:
            raise ValueError("NEURAL_SIM_CORE_CWD must be set when overriding sim-core command.")
        return command, str(Path(env_cwd).resolve())

    sim_core = config.get("sim_core", {})
    command = sim_core.get("command")
    cwd = sim_core.get("cwd")
    if not command or not isinstance(command, list):
        raise ValueError("sim_core.command must be a list of argv strings.")
    if not cwd or not isinstance(cwd, str):
        raise ValueError("sim_core.cwd must be a string.")
    return command, str(resolve_path(config, cwd))
