"""Summary writer for creating human-readable run reports."""

import json
from pathlib import Path
from typing import Any, Dict, Optional


def create_markdown_summary(
    profile: str,
    config_path: str,
    dataset_report: Optional[Dict[str, Any]] = None,
    train_report: Optional[Dict[str, Any]] = None,
    eval_report: Optional[Dict[str, Any]] = None,
    checkpoint_path: Optional[str] = None,
    latency_reports: Optional[Dict[str, Path]] = None,
) -> str:
    """Create a human-readable markdown summary.

    Args:
        profile: Profile name
        config_path: Path to config
        dataset_report: Dataset build report
        train_report: Training report
        eval_report: Evaluation report
        checkpoint_path: Path to checkpoint
        latency_reports: Paths to latency reports

    Returns:
        Markdown string
    """
    lines = []
    lines.append(f"# Run Summary: {profile}")
    lines.append("")

    # Metadata
    lines.append("## Metadata")
    lines.append(f"- **Config**: {config_path}")
    if dataset_report and "timestamp" in dataset_report:
        lines.append(f"- **Timestamp**: {dataset_report['timestamp']}")
    lines.append("")

    # Dataset section
    if dataset_report:
        lines.append("## Dataset Build")
        lines.append(f"- **Battles**: {dataset_report.get('successful_battles', '?')}/{dataset_report.get('num_battles', '?')}")
        lines.append(f"- **Labels**: {dataset_report.get('num_records', '?')}")
        lines.append(f"- **Retries**: {dataset_report.get('retries', 0)}")
        lines.append(f"- **Timeouts**: {dataset_report.get('timeouts', 0)}")
        lines.append(f"- **Wall Time**: {dataset_report.get('wall_time_ms', 0):.1f}ms")
        if "sim_core_mode" in dataset_report:
            lines.append(f"- **Sim-Core Mode**: {dataset_report['sim_core_mode']}")
        if latency_reports and "dataset" in latency_reports:
            lines.append(f"- **Latency Report**: {latency_reports['dataset']}")
        lines.append("")

    # Training section
    if train_report:
        lines.append("## Training")
        lines.append(f"- **Device**: {train_report.get('device', '?')}")
        lines.append(f"- **Dataset Size**: {train_report.get('dataset_size', '?')}")
        lines.append(f"- **Train Size**: {train_report.get('train_size', '?')}")
        lines.append(f"- **Val Size**: {train_report.get('val_size', '?')}")
        lines.append(f"- **Epochs**: {train_report.get('epochs', '?')}")
        lines.append(f"- **Batch Size**: {train_report.get('batch_size', '?')}")

        if "training_history" in train_report:
            lines.append("")
            lines.append("### Training History")
            for epoch_data in train_report["training_history"]:
                epoch = epoch_data.get("epoch", "?")
                train_loss = epoch_data.get("train_loss")
                val_acc = epoch_data.get("val_acc")
                line = f"- Epoch {epoch}: train_loss={train_loss:.4f}"
                if val_acc is not None:
                    line += f", val_acc={val_acc:.3f}"
                lines.append(line)

        if checkpoint_path:
            lines.append("")
            lines.append(f"- **Checkpoint**: {checkpoint_path}")
        lines.append("")

    # Evaluation section
    if eval_report:
        lines.append("## Evaluation")
        lines.append(f"- **Battles**: {eval_report.get('successful_battles', '?')}/{eval_report.get('num_battles', '?')}")
        lines.append(f"- **Wins**: {eval_report.get('wins', 0)}")
        lines.append(f"- **Losses**: {eval_report.get('losses', 0)}")
        lines.append(f"- **Ties**: {eval_report.get('ties', 0)}")
        lines.append(f"- **Win Rate**: {eval_report.get('win_rate', 0):.3f}")
        lines.append(f"- **Avg Steps**: {eval_report.get('avg_steps', 0):.2f}")
        lines.append(f"- **Avg Latency**: {eval_report.get('avg_latency_ms', 0):.3f}ms")
        lines.append(f"- **Retries**: {eval_report.get('retries', 0)}")
        lines.append(f"- **Timeouts**: {eval_report.get('timeouts', 0)}")
        lines.append(f"- **Wall Time**: {eval_report.get('wall_time_ms', 0):.1f}ms")
        if "sim_core_mode" in eval_report:
            lines.append(f"- **Sim-Core Mode**: {eval_report['sim_core_mode']}")
        if latency_reports and "eval" in latency_reports:
            lines.append(f"- **Latency Report**: {latency_reports['eval']}")
        lines.append("")

    return "\n".join(lines)


def create_json_summary(
    profile: str,
    config_path: str,
    dataset_report: Optional[Dict[str, Any]] = None,
    train_report: Optional[Dict[str, Any]] = None,
    eval_report: Optional[Dict[str, Any]] = None,
    checkpoint_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a JSON summary combining all reports.

    Args:
        profile: Profile name
        config_path: Path to config
        dataset_report: Dataset build report
        train_report: Training report
        eval_report: Evaluation report
        checkpoint_path: Path to checkpoint

    Returns:
        Dictionary with combined summary
    """
    summary: Dict[str, Any] = {
        "profile": profile,
        "config_path": str(config_path),
    }

    if dataset_report:
        summary["dataset"] = {
            "successful_battles": dataset_report.get("successful_battles"),
            "total_battles": dataset_report.get("num_battles"),
            "num_records": dataset_report.get("num_records"),
            "retries": dataset_report.get("retries"),
            "timeouts": dataset_report.get("timeouts"),
            "wall_time_ms": dataset_report.get("wall_time_ms"),
            "sim_core_mode": dataset_report.get("sim_core_mode"),
        }

    if train_report:
        summary["training"] = {
            "device": train_report.get("device"),
            "dataset_size": train_report.get("dataset_size"),
            "train_size": train_report.get("train_size"),
            "val_size": train_report.get("val_size"),
            "epochs": train_report.get("epochs"),
            "batch_size": train_report.get("batch_size"),
            "checkpoint": checkpoint_path,
        }
        if "training_history" in train_report:
            summary["training"]["training_history"] = train_report["training_history"]

    if eval_report:
        summary["evaluation"] = {
            "successful_battles": eval_report.get("successful_battles"),
            "total_battles": eval_report.get("num_battles"),
            "wins": eval_report.get("wins"),
            "losses": eval_report.get("losses"),
            "ties": eval_report.get("ties"),
            "win_rate": eval_report.get("win_rate"),
            "avg_steps": eval_report.get("avg_steps"),
            "avg_latency_ms": eval_report.get("avg_latency_ms"),
            "retries": eval_report.get("retries"),
            "timeouts": eval_report.get("timeouts"),
            "wall_time_ms": eval_report.get("wall_time_ms"),
            "sim_core_mode": eval_report.get("sim_core_mode"),
        }

    return summary


def write_summary_files(
    output_dir: Path,
    profile: str,
    config_path: str,
    dataset_report: Optional[Dict[str, Any]] = None,
    train_report: Optional[Dict[str, Any]] = None,
    eval_report: Optional[Dict[str, Any]] = None,
    checkpoint_path: Optional[str] = None,
    latency_reports: Optional[Dict[str, Path]] = None,
) -> Dict[str, Path]:
    """Write both JSON and markdown summaries.

    Args:
        output_dir: Directory to write summaries to
        profile: Profile name
        config_path: Path to config
        dataset_report: Dataset build report
        train_report: Training report
        eval_report: Evaluation report
        checkpoint_path: Path to checkpoint
        latency_reports: Paths to latency reports

    Returns:
        Dictionary with paths to written files
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create summary data
    json_summary = create_json_summary(
        profile, config_path, dataset_report, train_report, eval_report, checkpoint_path
    )

    markdown_summary = create_markdown_summary(
        profile,
        config_path,
        dataset_report,
        train_report,
        eval_report,
        checkpoint_path,
        latency_reports,
    )

    # Write files
    stem = config_path.replace(".yaml", "").replace(".json", "").split("/")[-1]
    json_path = output_dir / f"{stem}_summary.json"
    md_path = output_dir / f"{stem}_summary.md"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_summary, f, indent=2)

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown_summary + "\n")

    return {"json": json_path, "md": md_path}
