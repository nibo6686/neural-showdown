import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


LATENCY_METRIC_NAMES = [
    "round_trip_ms",
    "queue_wait_ms",
    "server_elapsed_ms",
    "transport_overhead_ms",
]


def summarize_samples(samples: Iterable[Optional[float]]) -> Dict[str, float]:
    values = sorted(float(sample) for sample in samples if sample is not None and not math.isnan(float(sample)))
    if not values:
        return {
            "count": 0,
            "mean_ms": 0.0,
            "p50_ms": 0.0,
            "p95_ms": 0.0,
            "max_ms": 0.0,
        }

    def percentile(fraction: float) -> float:
        if len(values) == 1:
            return values[0]
        position = (len(values) - 1) * fraction
        lower = math.floor(position)
        upper = math.ceil(position)
        if lower == upper:
            return values[lower]
        weight = position - lower
        return values[lower] + (values[upper] - values[lower]) * weight

    return {
        "count": len(values),
        "mean_ms": sum(values) / len(values),
        "p50_ms": percentile(0.50),
        "p95_ms": percentile(0.95),
        "max_ms": values[-1],
    }


def summarize_rpc_events(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for event in events:
        grouped.setdefault(str(event.get("request_type", "unknown")), []).append(event)

    by_request_type: Dict[str, Any] = {}
    for request_type, request_events in sorted(grouped.items()):
        metrics = {
            metric_name: summarize_samples(event.get(metric_name) for event in request_events)
            for metric_name in LATENCY_METRIC_NAMES
        }
        by_request_type[request_type] = {
            "count": len(request_events),
            "metrics": metrics,
        }

    hotspots = sorted(
        [
            {
                "request_type": request_type,
                "count": summary["count"],
                "mean_round_trip_ms": summary["metrics"]["round_trip_ms"]["mean_ms"],
                "p95_round_trip_ms": summary["metrics"]["round_trip_ms"]["p95_ms"],
                "max_round_trip_ms": summary["metrics"]["round_trip_ms"]["max_ms"],
            }
            for request_type, summary in by_request_type.items()
        ],
        key=lambda item: (item["p95_round_trip_ms"], item["mean_round_trip_ms"], item["count"]),
        reverse=True,
    )

    return {
        "count": len(events),
        "metrics": {
            metric_name: summarize_samples(event.get(metric_name) for event in events)
            for metric_name in LATENCY_METRIC_NAMES
        },
        "by_request_type": by_request_type,
        "hotspots": hotspots,
    }


def top_slowest_battles(battles: List[Dict[str, Any]], limit: int = 10) -> List[Dict[str, Any]]:
    return sorted(battles, key=lambda battle: float(battle.get("wall_time_ms", 0.0)), reverse=True)[:limit]


def write_json_report(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
