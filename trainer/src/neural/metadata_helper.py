"""Metadata collection for experiment runs on Windows."""

import json
import os
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


def get_platform_info() -> Dict[str, str]:
    """Get platform and environment information."""
    return {
        "platform": sys.platform,
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "platform_system": platform.system(),
        "platform_release": platform.release(),
    }


def get_git_info() -> Dict[str, Optional[str]]:
    """Get git commit and status if available."""
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).parent.parent.parent.parent,
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        commit = None

    try:
        status = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=Path(__file__).parent.parent.parent.parent,
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
        has_changes = bool(status)
    except (subprocess.CalledProcessError, FileNotFoundError):
        has_changes = None

    return {
        "git_commit": commit,
        "git_has_uncommitted_changes": has_changes,
    }


def get_torch_device_info() -> Dict[str, Any]:
    """Get PyTorch device information."""
    try:
        import torch
        return {
            "torch_device": "cuda" if torch.cuda.is_available() else "cpu",
            "torch_cuda_available": torch.cuda.is_available(),
        }
    except ImportError:
        return {"torch_device": None, "torch_cuda_available": False}


def get_sim_core_info() -> Dict[str, Optional[str]]:
    """Get sim-core runtime mode and paths from environment."""
    command_json = os.environ.get("NEURAL_SIM_CORE_COMMAND_JSON")

    mode = None
    node_exe = None
    npm_cmd = None

    if command_json:
        try:
            command = json.loads(command_json)
            if isinstance(command, list):
                if command[0].endswith("wsl"):
                    mode = "wsl"
                else:
                    mode = "native"
                    # For native mode, first element is node executable
                    node_exe = command[0]
        except (json.JSONDecodeError, IndexError):
            pass

    return {
        "sim_core_mode": mode,
        "sim_core_node_exe": node_exe,
    }


def create_run_metadata(
    config_path: str,
    profile: str,
    dataset_size: Optional[int] = None,
    train_size: Optional[int] = None,
    val_size: Optional[int] = None,
) -> Dict[str, Any]:
    """Create comprehensive metadata for a run.

    Args:
        config_path: Path to the config file
        profile: Profile name (e.g., 'dev', 'full')
        dataset_size: Size of full dataset
        train_size: Size of training set
        val_size: Size of validation set

    Returns:
        Dictionary with all metadata
    """
    metadata = {
        "timestamp": datetime.now().isoformat(),
        "config_path": str(config_path),
        "profile": profile,
    }

    metadata.update(get_platform_info())
    metadata.update(get_git_info())
    metadata.update(get_torch_device_info())
    metadata.update(get_sim_core_info())

    if dataset_size is not None:
        metadata["dataset_size"] = dataset_size
    if train_size is not None:
        metadata["train_size"] = train_size
    if val_size is not None:
        metadata["val_size"] = val_size

    return metadata
