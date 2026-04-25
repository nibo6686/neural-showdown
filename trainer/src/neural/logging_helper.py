"""Line-safe logging helpers for robust stdout output on Windows."""

import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional


def print_line_safe(message: str) -> None:
    """Print a complete single line to stdout with flush.

    Ensures PowerShell continuation prompts cannot interrupt the output.
    """
    print(message, flush=True)


def format_summary(phase: str, data: Dict[str, Any]) -> str:
    """Format a phase summary as a single-line compact message.

    Args:
        phase: Phase name (e.g., 'dataset', 'train', 'eval')
        data: Dictionary of summary data

    Returns:
        Single-line summary string with key metrics
    """
    parts = [f"{phase} done"]

    # Add common fields in a consistent order
    field_order = [
        "battles", "labels", "wins", "losses", "ties",
        "win_rate", "avg_steps", "epochs", "train_loss", "val_acc",
        "device", "checkpoint", "report", "latency", "retries", "timeouts"
    ]

    for field in field_order:
        if field in data:
            value = data[field]
            if isinstance(value, float):
                if value < 0.001:
                    parts.append(f"{field}={value:.6f}")
                elif value < 1.0:
                    parts.append(f"{field}={value:.3f}")
                else:
                    parts.append(f"{field}={value:.2f}")
            elif isinstance(value, Path):
                # Print relative path from current dir for readability
                try:
                    rel_path = value.relative_to(Path.cwd())
                    parts.append(f"{field}={rel_path}")
                except ValueError:
                    parts.append(f"{field}={value}")
            else:
                parts.append(f"{field}={value}")

    # Add any extra fields not in the standard order
    for field, value in data.items():
        if field not in field_order:
            if isinstance(value, float):
                if value < 0.001:
                    parts.append(f"{field}={value:.6f}")
                elif value < 1.0:
                    parts.append(f"{field}={value:.3f}")
                else:
                    parts.append(f"{field}={value:.2f}")
            elif isinstance(value, (str, int, bool)):
                parts.append(f"{field}={value}")

    return " | ".join(parts)


def write_json_summary(path: Any, data: Dict[str, Any], indent: Optional[int] = None) -> None:
    """Write JSON data to file safely.

    Args:
        path: File path
        data: Data to write
        indent: JSON indent level (None for compact)
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent)
