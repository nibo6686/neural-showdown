import argparse
import gzip
import json
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from .logging_helper import format_summary, print_line_safe
from .value_features import (
    VALUE_EXTRA_DIM,
    VALUE_FEATURE_DIM,
    VALUE_FEATURE_VERSION,
    discounted_terminal_return,
    featurize_value_state,
    final_result_from_winner,
    flatten_trace_steps,
    load_trace,
    view_request_from_step,
)


DEFAULT_OUTPUT_PATH = Path("data/value/gen9randombattle_value.npz")
DEFAULT_REPORT_JSON_PATH = Path("artifacts/analysis/value_dataset_report.json")
DEFAULT_REPORT_MD_PATH = Path("artifacts/analysis/value_dataset_report.md")


def _iter_trace_paths(trace_dirs: Sequence[Path], trace_paths: Sequence[Path]) -> List[Path]:
    paths: List[Path] = []
    for trace_dir in trace_dirs:
        if trace_dir.exists():
            paths.extend(sorted(trace_dir.glob("battle_*.json")))
    for trace_path in trace_paths:
        if trace_path.exists():
            paths.append(trace_path)
    deduped: List[Path] = []
    seen = set()
    for path in paths:
        resolved = str(path.resolve())
        if resolved not in seen:
            deduped.append(path)
            seen.add(resolved)
    return deduped


def _chosen_action_index(step: Dict[str, Any], fallback: int = -1) -> int:
    for key in ("chosen_action_index", "action_index"):
        if key in step and step.get(key) is not None:
            try:
                return int(step[key])
            except (TypeError, ValueError):
                return fallback
    return fallback


def _metadata_json(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _append_example(
    examples: List[Dict[str, Any]],
    *,
    view: Dict[str, Any],
    request: Optional[Dict[str, Any]],
    final_result: float,
    discounted_return: float,
    turn: int,
    step_index: int,
    battle_index: int,
    chosen_action_index: int,
    source_id: str,
    source_kind: str,
    protocol_history: Optional[Sequence[str]] = None,
    step_history: Optional[Sequence[Dict[str, Any]]] = None,
    current_step: Optional[Dict[str, Any]] = None,
    include_extras: bool = True,
) -> None:
    features, legal_mask = featurize_value_state(
        view,
        request,
        protocol_history=protocol_history,
        step_history=step_history,
        current_step=current_step,
        include_extras=include_extras,
    )
    examples.append(
        {
            "state": features,
            "legal_mask": legal_mask,
            "final_result": float(final_result),
            "value_target": float(discounted_return),
            "discounted_return": float(discounted_return),
            "turn": int(turn),
            "step_index": int(step_index),
            "battle_index": int(battle_index),
            "chosen_action_index": int(chosen_action_index),
            "source_id": source_id,
            "source_kind": source_kind,
            "metadata_json": _metadata_json(
                {
                    "source_id": source_id,
                    "source_kind": source_kind,
                    "battle_index": int(battle_index),
                    "step_index": int(step_index),
                    "turn": int(turn),
                }
            ),
        }
    )


def examples_from_trace_path(path: Path, *, gamma: float = 1.0, include_extras: bool = True) -> List[Dict[str, Any]]:
    trace = load_trace(path)
    steps = flatten_trace_steps(trace)
    final_result = final_result_from_winner(trace.get("winner"))
    battle_index = int(trace.get("battle_index", _battle_index_from_path(path)) or 0)
    protocol_history: List[str] = []
    examples: List[Dict[str, Any]] = []
    for ordinal, step in enumerate(steps):
        view, request = view_request_from_step(trace, step)
        current_protocol = step.get("protocol_log") if isinstance(step.get("protocol_log"), list) else []
        combined_protocol = protocol_history + [str(line) for line in current_protocol]
        steps_to_terminal = max(0, len(steps) - ordinal - 1)
        _append_example(
            examples,
            view=view,
            request=request,
            final_result=final_result,
            discounted_return=discounted_terminal_return(final_result, steps_to_terminal, gamma),
            turn=int(step.get("turn", view.get("turn", 0)) or 0),
            step_index=int(step.get("step_index", ordinal) or 0),
            battle_index=battle_index,
            chosen_action_index=_chosen_action_index(step),
            source_id=str(path),
            source_kind="trace",
            protocol_history=combined_protocol,
            step_history=steps[:ordinal],
            current_step=step,
            include_extras=include_extras,
        )
        protocol_history = combined_protocol
    return examples


def _battle_index_from_path(path: Path) -> int:
    stem = path.stem
    if stem.startswith("battle_"):
        try:
            return int(stem.split("_", 1)[1])
        except ValueError:
            return 0
    return 0


def _read_jsonl_gz(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                records.append(json.loads(line))
    return records


def _record_final_result(record: Dict[str, Any]) -> float:
    if "final_result" in record:
        return float(record["final_result"])
    if "return" in record:
        return float(record["return"])
    if "winner" in record:
        return final_result_from_winner(record.get("winner"))
    return 0.0


def _examples_from_flat_records(
    records: Sequence[Dict[str, Any]],
    *,
    path: Path,
    gamma: float,
    include_extras: bool,
) -> List[Dict[str, Any]]:
    by_battle: Dict[int, List[Tuple[int, Dict[str, Any]]]] = defaultdict(list)
    for ordinal, record in enumerate(records):
        if "view" not in record:
            continue
        if record.get("player", "p1") != "p1":
            continue
        battle_index = int(record.get("battle_index", 0) or 0)
        by_battle[battle_index].append((ordinal, record))

    examples: List[Dict[str, Any]] = []
    for battle_index, battle_records in by_battle.items():
        battle_records.sort(key=lambda item: int(item[1].get("step_index", item[0]) or 0))
        final_result = _record_final_result(battle_records[-1][1]) if battle_records else 0.0
        for ordinal, (_, record) in enumerate(battle_records):
            steps_to_terminal = max(0, len(battle_records) - ordinal - 1)
            view = record["view"]
            request = record.get("request") if isinstance(record.get("request"), dict) else None
            _append_example(
                examples,
                view=view,
                request=request,
                final_result=final_result,
                discounted_return=discounted_terminal_return(final_result, steps_to_terminal, gamma),
                turn=int(view.get("turn", 0) or 0),
                step_index=int(record.get("step_index", ordinal) or 0),
                battle_index=battle_index,
                chosen_action_index=int(record.get("action_index", -1) if record.get("action_index") is not None else -1),
                source_id=str(path),
                source_kind="jsonl_record",
                include_extras=include_extras,
            )
    return examples


def _examples_from_episode_records(
    episodes: Sequence[Dict[str, Any]],
    *,
    path: Path,
    gamma: float,
    include_extras: bool,
) -> List[Dict[str, Any]]:
    examples: List[Dict[str, Any]] = []
    for fallback_battle_index, episode in enumerate(episodes):
        steps = episode.get("steps")
        if not isinstance(steps, list):
            continue
        final_result = final_result_from_winner(episode.get("winner"))
        battle_index = int(episode.get("battle_index", fallback_battle_index) or 0)
        protocol_history: List[str] = []
        p1_steps = [step for step in steps if isinstance(step, dict) and step.get("player", "p1") == "p1"]
        for ordinal, step in enumerate(p1_steps):
            if "view" not in step:
                continue
            current_protocol = step.get("protocol_log") if isinstance(step.get("protocol_log"), list) else []
            combined_protocol = protocol_history + [str(line) for line in current_protocol]
            view = step["view"]
            request = step.get("request") if isinstance(step.get("request"), dict) else None
            steps_to_terminal = max(0, len(p1_steps) - ordinal - 1)
            _append_example(
                examples,
                view=view,
                request=request,
                final_result=final_result,
                discounted_return=discounted_terminal_return(final_result, steps_to_terminal, gamma),
                turn=int(view.get("turn", step.get("turn", 0)) or 0),
                step_index=int(step.get("step_index", ordinal) or 0),
                battle_index=battle_index,
                chosen_action_index=_chosen_action_index(step),
                source_id=str(path),
                source_kind="jsonl_episode",
                protocol_history=combined_protocol,
                step_history=p1_steps[:ordinal],
                current_step=step,
                include_extras=include_extras,
            )
            protocol_history = combined_protocol
    return examples


def examples_from_jsonl_path(path: Path, *, gamma: float = 1.0, include_extras: bool = True) -> List[Dict[str, Any]]:
    records = _read_jsonl_gz(path)
    episode_records = [record for record in records if isinstance(record.get("steps"), list)]
    flat_records = [record for record in records if not isinstance(record.get("steps"), list)]
    examples = []
    examples.extend(_examples_from_episode_records(episode_records, path=path, gamma=gamma, include_extras=include_extras))
    examples.extend(_examples_from_flat_records(flat_records, path=path, gamma=gamma, include_extras=include_extras))
    return examples


def _stack_examples(examples: Sequence[Dict[str, Any]]) -> Dict[str, np.ndarray]:
    if not examples:
        raise ValueError("No value examples were produced. Provide traces or JSONL records with decision states.")
    return {
        "states": np.asarray([example["state"] for example in examples], dtype=np.float32),
        "legal_masks": np.asarray([example["legal_mask"] for example in examples], dtype=np.float32),
        "value_targets": np.asarray([example["value_target"] for example in examples], dtype=np.float32),
        "final_results": np.asarray([example["final_result"] for example in examples], dtype=np.float32),
        "discounted_returns": np.asarray([example["discounted_return"] for example in examples], dtype=np.float32),
        "turns": np.asarray([example["turn"] for example in examples], dtype=np.int64),
        "step_indices": np.asarray([example["step_index"] for example in examples], dtype=np.int64),
        "battle_indices": np.asarray([example["battle_index"] for example in examples], dtype=np.int64),
        "chosen_action_indices": np.asarray([example["chosen_action_index"] for example in examples], dtype=np.int64),
        "source_ids": np.asarray([example["source_id"] for example in examples]),
        "source_kinds": np.asarray([example["source_kind"] for example in examples]),
        "metadata_json": np.asarray([example["metadata_json"] for example in examples]),
    }


def build_value_dataset(
    *,
    trace_dirs: Sequence[Path],
    trace_paths: Sequence[Path] = (),
    jsonl_paths: Sequence[Path] = (),
    output_path: Path = DEFAULT_OUTPUT_PATH,
    report_json_path: Path = DEFAULT_REPORT_JSON_PATH,
    report_md_path: Path = DEFAULT_REPORT_MD_PATH,
    gamma: float = 1.0,
    include_extras: bool = True,
) -> Dict[str, Any]:
    started_at = time.perf_counter()
    examples: List[Dict[str, Any]] = []
    trace_files = _iter_trace_paths(trace_dirs, trace_paths)
    source_counts: Counter[str] = Counter()

    for path in trace_files:
        source_examples = examples_from_trace_path(path, gamma=gamma, include_extras=include_extras)
        examples.extend(source_examples)
        source_counts["trace"] += len(source_examples)

    for path in jsonl_paths:
        if not path.exists():
            continue
        source_examples = examples_from_jsonl_path(path, gamma=gamma, include_extras=include_extras)
        examples.extend(source_examples)
        source_counts["jsonl"] += len(source_examples)

    arrays = _stack_examples(examples)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        output_path,
        **arrays,
        feature_version=np.asarray(VALUE_FEATURE_VERSION),
        include_extras=np.asarray(bool(include_extras)),
        gamma=np.asarray(float(gamma), dtype=np.float32),
    )

    final_results = arrays["final_results"]
    value_targets = arrays["value_targets"]
    report = {
        "output_path": str(output_path),
        "examples": int(arrays["states"].shape[0]),
        "feature_dim": int(arrays["states"].shape[1]),
        "feature_version": VALUE_FEATURE_VERSION if include_extras else "base-v1",
        "value_extra_dim": VALUE_EXTRA_DIM if include_extras else 0,
        "gamma": float(gamma),
        "trace_dirs": [str(path) for path in trace_dirs],
        "trace_files": [str(path) for path in trace_files],
        "jsonl_paths": [str(path) for path in jsonl_paths],
        "source_counts": dict(source_counts),
        "outcomes": {
            "wins": int((final_results > 0).sum()),
            "losses": int((final_results < 0).sum()),
            "ties": int((final_results == 0).sum()),
        },
        "target_mean": float(value_targets.mean()),
        "target_std": float(value_targets.std()),
        "turn_min": int(arrays["turns"].min()),
        "turn_max": int(arrays["turns"].max()),
        "wall_time_ms": (time.perf_counter() - started_at) * 1000.0,
    }
    report_json_path.parent.mkdir(parents=True, exist_ok=True)
    report_json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report_md_path.parent.mkdir(parents=True, exist_ok=True)
    report_md_path.write_text(_format_markdown_report(report), encoding="utf-8")
    return report


def _format_markdown_report(report: Dict[str, Any]) -> str:
    lines = [
        "# Value Dataset Report",
        "",
        f"- Examples: {report['examples']}",
        f"- Feature dimension: {report['feature_dim']}",
        f"- Feature version: {report['feature_version']}",
        f"- Gamma: {report['gamma']}",
        f"- Target mean/std: {report['target_mean']:.4f} / {report['target_std']:.4f}",
        "",
        "## Outcomes",
        "",
    ]
    for key, value in report.get("outcomes", {}).items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Sources", ""])
    for key, value in report.get("source_counts", {}).items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", f"Output: `{report['output_path']}`", ""])
    return "\n".join(lines)


def _parse_paths(values: Optional[Sequence[str]]) -> List[Path]:
    return [Path(value) for value in values or [] if value]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a battle-state value-model dataset from traces and JSONL records.")
    parser.add_argument("--trace-dir", action="append", default=[], help="Directory containing battle_*.json traces.")
    parser.add_argument("--trace-path", action="append", default=[], help="Individual battle trace JSON path.")
    parser.add_argument("--jsonl", action="append", default=[], help="Optional raw JSONL.GZ episode or decision records.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="Output NPZ path.")
    parser.add_argument("--report-json", default=str(DEFAULT_REPORT_JSON_PATH), help="Output JSON report path.")
    parser.add_argument("--report-md", default=str(DEFAULT_REPORT_MD_PATH), help="Output Markdown report path.")
    parser.add_argument("--gamma", type=float, default=1.0, help="Discount applied by steps to terminal.")
    parser.add_argument("--no-extras", action="store_true", help="Use only the BC-compatible base feature vector.")
    args = parser.parse_args()

    trace_dirs = _parse_paths(args.trace_dir)
    if not trace_dirs and not args.trace_path and not args.jsonl:
        trace_dirs = [Path("artifacts/battles/dev")]

    report = build_value_dataset(
        trace_dirs=trace_dirs,
        trace_paths=_parse_paths(args.trace_path),
        jsonl_paths=_parse_paths(args.jsonl),
        output_path=Path(args.output),
        report_json_path=Path(args.report_json),
        report_md_path=Path(args.report_md),
        gamma=args.gamma,
        include_extras=not args.no_extras,
    )
    print_line_safe(f"value-dataset | wrote={report['examples']} examples to {report['output_path']}")
    print_line_safe(f"value-dataset | report={args.report_json}")
    print_line_safe(
        format_summary(
            "value-dataset",
            {
                "examples": report["examples"],
                "feature_dim": report["feature_dim"],
                "target_mean": f"{report['target_mean']:.4f}",
                "output": report["output_path"],
            },
        )
    )


if __name__ == "__main__":
    main()
