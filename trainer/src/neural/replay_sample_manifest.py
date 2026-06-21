import argparse
import hashlib
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from .logging_helper import print_line_safe
from .replay_pool_profiler import MECHANIC_FLAGS, PROFILE_VERSION, RARE_FLAGS, catalog_checksum


MANIFEST_VERSION = "diagnostic-300-manifest-v1"
DEFAULT_SEED = 20260619
DEFAULT_CATALOG = Path("artifacts/training_plan/replay_catalog.jsonl")
DEFAULT_OUTPUT = Path("artifacts/training_plan/manifests/diagnostic_300_manifest.json")

BUCKET_TARGETS = {
    "rare_mechanic": 30,
    "higher_rating": 30,
    "long_close": 45,
    "mechanics_enriched": 75,
    "broad_random": 120,
}
SPLIT_TARGETS = {"train": 210, "validation": 45, "test": 45}


def load_catalog(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            payload = json.loads(line)
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def _stable_random_key(seed: int, replay_id: str, namespace: str) -> str:
    value = f"{seed}:{namespace}:{replay_id}".encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def _mechanic_count(row: Dict[str, Any]) -> int:
    mechanics = row.get("mechanics") if isinstance(row.get("mechanics"), dict) else {}
    return sum(bool(mechanics.get(name)) for name in MECHANIC_FLAGS)


def _selection_tags(row: Dict[str, Any], high_rating_threshold: float) -> List[str]:
    tags: List[str] = []
    mechanics = row.get("mechanics") if isinstance(row.get("mechanics"), dict) else {}
    tags.extend(name for name in MECHANIC_FLAGS if mechanics.get(name))
    if row.get("long_game"):
        tags.append("long_game")
    if row.get("close_game_proxy"):
        tags.append("close_game_proxy")
    rating = row.get("rating")
    if rating is not None and float(rating) >= high_rating_threshold:
        tags.append("higher_rating_quartile")
    return tags


def _take(
    candidates: Iterable[Dict[str, Any]],
    count: int,
    selected_ids: set,
    *,
    seed: int,
    namespace: str,
    score=None,
) -> List[Dict[str, Any]]:
    available = [row for row in candidates if row["replay_id"] not in selected_ids]
    if score is None:
        available.sort(key=lambda row: _stable_random_key(seed, row["replay_id"], namespace))
    else:
        available.sort(
            key=lambda row: (
                -score(row),
                _stable_random_key(seed, row["replay_id"], namespace),
            )
        )
    chosen = available[:count]
    selected_ids.update(row["replay_id"] for row in chosen)
    return chosen


def _assign_splits(entries: List[Dict[str, Any]], seed: int) -> None:
    remaining = dict(SPLIT_TARGETS)
    by_bucket: Dict[str, List[Dict[str, Any]]] = {}
    for entry in entries:
        by_bucket.setdefault(entry["primary_stratum"], []).append(entry)
    bucket_order = list(BUCKET_TARGETS)
    for bucket in bucket_order:
        bucket_entries = by_bucket.get(bucket, [])
        bucket_entries.sort(key=lambda row: _stable_random_key(seed, row["replay_id"], f"split:{bucket}"))
        for entry in bucket_entries:
            total_remaining = sum(remaining.values())
            best = max(
                remaining,
                key=lambda split: (
                    remaining[split] / max(1, total_remaining),
                    remaining[split],
                    split,
                ),
            )
            entry["split"] = best
            remaining[best] -= 1
    if any(remaining.values()):
        raise ValueError(f"Could not satisfy split targets: {remaining}")


def _coverage(rows: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    return {
        name: sum(bool(row.get("mechanics", {}).get(name)) for row in rows)
        for name in MECHANIC_FLAGS
    }


def validate_manifest(manifest: Dict[str, Any], catalog_rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    entries = manifest["entries"]
    ids = [entry["replay_id"] for entry in entries]
    catalog_by_id = {row["replay_id"]: row for row in catalog_rows}
    split_counts = Counter(entry["split"] for entry in entries)
    missing_ids = sorted(set(ids) - set(catalog_by_id))
    missing_paths = sorted(
        entry["replay_id"] for entry in entries
        if not Path(entry["path"]).exists()
    )
    selected_coverage = _coverage(entries)
    baseline_coverage = manifest["random_baseline"]["mechanic_counts"]
    selected_total = sum(selected_coverage.values())
    baseline_total = sum(baseline_coverage.values())
    checks = {
        "exactly_300_entries": len(entries) == 300,
        "300_unique_ids": len(set(ids)) == 300,
        "split_sizes_exact": dict(split_counts) == SPLIT_TARGETS,
        "no_cross_split_duplicates": len(ids) == len(set(ids)),
        "all_entries_in_catalog": not missing_ids,
        "all_paths_exist": not missing_paths,
        "mechanic_coverage_at_least_random_baseline": selected_total >= baseline_total,
        "seed_recorded": manifest.get("seed") is not None,
        "catalog_checksum_recorded": bool(manifest.get("catalog_checksum")),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "split_counts": dict(split_counts),
        "missing_catalog_ids": missing_ids,
        "missing_paths": missing_paths,
        "selected_mechanic_counts": selected_coverage,
        "random_baseline_mechanic_counts": baseline_coverage,
        "selected_mechanic_flag_total": selected_total,
        "random_baseline_mechanic_flag_total": baseline_total,
    }


def generate_diagnostic_manifest(
    *,
    catalog_path: Path = DEFAULT_CATALOG,
    output_path: Path = DEFAULT_OUTPUT,
    seed: int = DEFAULT_SEED,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    rows = load_catalog(catalog_path)
    eligible = [
        row for row in rows
        if row.get("eligible_diagnostic_300") and not row.get("parse_error")
    ]
    unique = {row["replay_id"]: row for row in eligible}
    eligible = list(unique.values())
    if len(eligible) < 300:
        raise ValueError(f"Need 300 eligible unique replays, found {len(eligible)}")
    ratings = sorted(float(row["rating"]) for row in eligible if row.get("rating") is not None)
    high_rating_threshold = ratings[int(0.75 * (len(ratings) - 1))] if ratings else float("inf")
    selected_ids = set()
    selections: List[Tuple[str, Dict[str, Any]]] = []
    shortfalls: Dict[str, int] = {}

    bucket_candidates = {
        "rare_mechanic": [row for row in eligible if any(row.get("mechanics", {}).get(name) for name in RARE_FLAGS)],
        "higher_rating": [row for row in eligible if row.get("rating") is not None and float(row["rating"]) >= high_rating_threshold],
        "long_close": [row for row in eligible if row.get("long_game") or row.get("close_game_proxy")],
        "mechanics_enriched": [row for row in eligible if _mechanic_count(row) > 0],
        "broad_random": eligible,
    }
    for bucket, target in BUCKET_TARGETS.items():
        score = None
        if bucket == "rare_mechanic":
            score = lambda row: sum(bool(row.get("mechanics", {}).get(name)) for name in RARE_FLAGS)
        elif bucket == "long_close":
            score = lambda row: int(bool(row.get("close_game_proxy"))) * 10 + int(row.get("turn_count", 0))
        elif bucket == "mechanics_enriched":
            score = _mechanic_count
        elif bucket == "higher_rating":
            score = lambda row: float(row.get("rating") or 0)
        chosen: List[Dict[str, Any]] = []
        if bucket == "rare_mechanic":
            for flag in RARE_FLAGS:
                chosen.extend(_take(
                    (row for row in bucket_candidates[bucket] if row.get("mechanics", {}).get(flag)),
                    min(2, target - len(chosen)),
                    selected_ids,
                    seed=seed,
                    namespace=f"{bucket}:{flag}",
                    score=score,
                ))
                if len(chosen) >= target:
                    break
        chosen.extend(_take(
            bucket_candidates[bucket],
            target - len(chosen),
            selected_ids,
            seed=seed,
            namespace=bucket,
            score=score,
        ))
        shortfalls[bucket] = target - len(chosen)
        selections.extend((bucket, row) for row in chosen)

    if len(selections) < 300:
        fillers = _take(
            eligible,
            300 - len(selections),
            selected_ids,
            seed=seed,
            namespace="shortfall_fill",
        )
        selections.extend(("broad_random_fill", row) for row in fillers)
    if len(selections) != 300:
        raise ValueError(f"Manifest selection produced {len(selections)} rows")

    entries: List[Dict[str, Any]] = []
    for bucket, row in selections:
        mechanics = row.get("mechanics") if isinstance(row.get("mechanics"), dict) else {}
        entries.append({
            "replay_id": row["replay_id"],
            "path": row["path"],
            "primary_stratum": bucket,
            "source_strata": _selection_tags(row, high_rating_threshold),
            "selection_reasons": [bucket] + _selection_tags(row, high_rating_threshold),
            "rating": row.get("rating"),
            "upload_time": row.get("upload_time"),
            "turn_count": row.get("turn_count"),
            "approx_decision_state_count": row.get("approx_decision_state_count"),
            "mechanics": {name: bool(mechanics.get(name)) for name in MECHANIC_FLAGS},
            "profile_version": row.get("profile_version") or PROFILE_VERSION,
            "selection_seed": seed,
        })
    _assign_splits(entries, seed)
    entries.sort(key=lambda row: (("train", "validation", "test").index(row["split"]), row["replay_id"]))

    baseline = sorted(
        eligible,
        key=lambda row: _stable_random_key(seed, row["replay_id"], "random_baseline"),
    )[:300]
    manifest = {
        "manifest_version": MANIFEST_VERSION,
        "profile_version": PROFILE_VERSION,
        "seed": seed,
        "catalog_path": str(catalog_path),
        "catalog_checksum": catalog_checksum(catalog_path),
        "eligible_pool_size": len(eligible),
        "high_rating_threshold_top_quartile": None if not ratings else high_rating_threshold,
        "target_bucket_sizes": BUCKET_TARGETS,
        "bucket_shortfalls_before_fill": shortfalls,
        "split_targets": SPLIT_TARGETS,
        "random_baseline": {
            "method": "deterministic uniform sample from eligible pool",
            "mechanic_counts": _coverage(baseline),
        },
        "entries": entries,
    }
    report = validate_manifest(manifest, rows)
    if not report["passed"]:
        raise ValueError(f"Manifest validation failed: {report['checks']}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    output_path.with_suffix(".md").write_text(_manifest_markdown(manifest), encoding="utf-8")
    output_path.with_name(output_path.stem + "_report.md").write_text(
        _report_markdown(manifest, report), encoding="utf-8"
    )
    print_line_safe(
        f"diagnostic-manifest done | entries={len(entries)} splits={report['split_counts']} "
        f"output={output_path}"
    )
    return manifest, report


def _manifest_markdown(manifest: Dict[str, Any]) -> str:
    split_counts = Counter(entry["split"] for entry in manifest["entries"])
    bucket_counts = Counter(entry["primary_stratum"] for entry in manifest["entries"])
    lines = [
        "# diagnostic_300 Manifest",
        "",
        f"- Seed: `{manifest['seed']}`",
        f"- Catalog SHA-256: `{manifest['catalog_checksum']}`",
        f"- Eligible pool: {manifest['eligible_pool_size']:,}",
        f"- Splits: train {split_counts['train']}, validation {split_counts['validation']}, test {split_counts['test']}",
        "",
        "## Selection Composition",
        "",
    ]
    for bucket, count in bucket_counts.items():
        lines.append(f"- `{bucket}`: {count}")
    lines.extend(["", "Battle-level assignment is fixed before feature generation; IDs are unique across splits.", ""])
    return "\n".join(lines)


def _report_markdown(manifest: Dict[str, Any], report: Dict[str, Any]) -> str:
    lines = [
        "# diagnostic_300 Manifest Validation Report",
        "",
        f"- Overall: **{'PASS' if report['passed'] else 'FAIL'}**",
        f"- Seed: `{manifest['seed']}`",
        f"- Catalog SHA-256: `{manifest['catalog_checksum']}`",
        "",
        "## Checks",
        "",
    ]
    for name, passed in report["checks"].items():
        lines.append(f"- [{'x' if passed else ' '}] `{name}`")
    lines.extend([
        "",
        "## Mechanic Enrichment",
        "",
        f"- Selected mechanic-flag total: {report['selected_mechanic_flag_total']}",
        f"- Random-baseline mechanic-flag total: {report['random_baseline_mechanic_flag_total']}",
        "",
        "| Mechanic | Selected | Random baseline |",
        "| --- | ---: | ---: |",
    ])
    for name in MECHANIC_FLAGS:
        lines.append(
            f"| `{name}` | {report['selected_mechanic_counts'][name]} | "
            f"{report['random_baseline_mechanic_counts'][name]} |"
        )
    lines.append("")
    return "\n".join(lines)


# --- diagnostic_1000 action-rank manifest (larger, Tera/switch-enriched) ---

ACTION_RANK_MANIFEST_VERSION = "diagnostic-1000-action-rank-manifest-v1"
ACTION_RANK_TOTAL = 1000
ACTION_RANK_OUTPUT = Path(
    "artifacts/training_plan/manifests/diagnostic_1000_action_rank_manifest.json"
)
ACTION_RANK_SPLIT_TARGETS = {"train": 700, "validation": 150, "test": 150}
ACTION_RANK_BUCKET_TARGETS = {
    "tera_action_enriched": 90,
    "switch_heavy": 110,
    "rare_mechanic": 60,
    "higher_rating": 90,
    "long_close": 150,
    "mechanics_enriched": 150,
    "broad_random": 350,
}
# Top-quartile switch-decision count in the eligible pool (input:switch p75 == 18).
SWITCH_HEAVY_MIN = 18


def _command_count(row: Dict[str, Any], key: str) -> int:
    counts = row.get("raw_command_counts")
    if isinstance(counts, dict):
        try:
            return int(counts.get(key, 0) or 0)
        except (TypeError, ValueError):
            return 0
    return 0


def _tera_action_count(row: Dict[str, Any]) -> int:
    return _command_count(row, "-terastallize")


def _switch_decision_count(row: Dict[str, Any]) -> int:
    return _command_count(row, "input:switch")


def _assign_splits_general(
    entries: List[Dict[str, Any]],
    seed: int,
    split_targets: Dict[str, int],
    bucket_order: Sequence[str],
) -> None:
    remaining = dict(split_targets)
    by_bucket: Dict[str, List[Dict[str, Any]]] = {}
    for entry in entries:
        by_bucket.setdefault(entry["primary_stratum"], []).append(entry)
    for bucket in bucket_order:
        bucket_entries = by_bucket.get(bucket, [])
        bucket_entries.sort(
            key=lambda row: _stable_random_key(seed, row["replay_id"], f"split:{bucket}")
        )
        for entry in bucket_entries:
            total_remaining = sum(remaining.values())
            best = max(
                remaining,
                key=lambda split: (
                    remaining[split] / max(1, total_remaining),
                    remaining[split],
                    split,
                ),
            )
            entry["split"] = best
            remaining[best] -= 1
    if any(remaining.values()):
        raise ValueError(f"Could not satisfy split targets: {remaining}")


def validate_action_rank_manifest(
    manifest: Dict[str, Any],
    catalog_rows: Sequence[Dict[str, Any]],
    *,
    total: int,
    split_targets: Dict[str, int],
) -> Dict[str, Any]:
    entries = manifest["entries"]
    ids = [entry["replay_id"] for entry in entries]
    catalog_by_id = {row["replay_id"]: row for row in catalog_rows}
    split_counts = Counter(entry["split"] for entry in entries)
    missing_ids = sorted(set(ids) - set(catalog_by_id))
    missing_paths = sorted(
        entry["replay_id"] for entry in entries if not Path(entry["path"]).exists()
    )
    selected_coverage = _coverage(entries)
    baseline_coverage = manifest["random_baseline"]["mechanic_counts"]
    selected_total = sum(selected_coverage.values())
    baseline_total = sum(baseline_coverage.values())
    checks = {
        "exactly_total_entries": len(entries) == total,
        "unique_ids": len(set(ids)) == total,
        "split_sizes_exact": dict(split_counts) == split_targets,
        "no_cross_split_duplicates": len(ids) == len(set(ids)),
        "all_entries_in_catalog": not missing_ids,
        "all_paths_exist": not missing_paths,
        "mechanic_coverage_at_least_random_baseline": selected_total >= baseline_total,
        "seed_recorded": manifest.get("seed") is not None,
        "catalog_checksum_recorded": bool(manifest.get("catalog_checksum")),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "split_counts": dict(split_counts),
        "missing_catalog_ids": missing_ids,
        "missing_paths": missing_paths,
        "selected_mechanic_counts": selected_coverage,
        "random_baseline_mechanic_counts": baseline_coverage,
        "selected_mechanic_flag_total": selected_total,
        "random_baseline_mechanic_flag_total": baseline_total,
    }


def _enrichment_summary(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    n = max(1, len(rows))
    tera_action_total = sum(_tera_action_count(r) for r in rows)
    switch_total = sum(_switch_decision_count(r) for r in rows)
    move_total = sum(_command_count(r, "input:move") for r in rows)
    decisions = switch_total + move_total
    return {
        "battles": len(rows),
        "tera_battle_count": sum(1 for r in rows if r.get("mechanics", {}).get("tera")),
        "tera_action_total": tera_action_total,
        "battles_with_tera_action": sum(1 for r in rows if _tera_action_count(r) >= 1),
        "switch_decision_total": switch_total,
        "switch_decision_mean_per_battle": round(switch_total / n, 2),
        "switch_share_of_decisions": round(switch_total / max(1, decisions), 3),
        "long_game_rate": round(sum(1 for r in rows if r.get("long_game")) / n, 3),
        "close_game_rate": round(sum(1 for r in rows if r.get("close_game_proxy")) / n, 3),
        "short_or_forfeit_rate": round(
            sum(1 for r in rows if r.get("early_forfeit_or_short")) / n, 3
        ),
        "rating_available_rate": round(
            sum(1 for r in rows if r.get("rating") is not None) / n, 3
        ),
    }


def _fits_frozen_six_slot_schema(row: Dict[str, Any]) -> bool:
    path = Path(str(row.get("path") or ""))
    if not path.is_file():
        return True
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split("|")
        if len(parts) >= 4 and parts[1] == "teamsize":
            try:
                if int(parts[3]) > 6:
                    return False
            except ValueError:
                continue
    return True


def generate_action_rank_manifest(
    *,
    catalog_path: Path = DEFAULT_CATALOG,
    output_path: Path = ACTION_RANK_OUTPUT,
    seed: int = DEFAULT_SEED,
    action_feature_version: str = "legal-action-v5",
    action_feature_dim: int = 318,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    rows = load_catalog(catalog_path)
    eligible = [
        row
        for row in rows
        if row.get("eligible_diagnostic_300")
        and not row.get("parse_error")
        and _fits_frozen_six_slot_schema(row)
    ]
    unique = {row["replay_id"]: row for row in eligible}
    eligible = list(unique.values())
    if len(eligible) < ACTION_RANK_TOTAL:
        raise ValueError(
            f"Need {ACTION_RANK_TOTAL} eligible unique replays, found {len(eligible)}"
        )
    ratings = sorted(float(r["rating"]) for r in eligible if r.get("rating") is not None)
    high_rating_threshold = (
        ratings[int(0.75 * (len(ratings) - 1))] if ratings else float("inf")
    )
    selected_ids: set = set()
    selections: List[Tuple[str, Dict[str, Any]]] = []
    shortfalls: Dict[str, int] = {}

    bucket_candidates = {
        "tera_action_enriched": [r for r in eligible if _tera_action_count(r) >= 1],
        "switch_heavy": [r for r in eligible if _switch_decision_count(r) >= SWITCH_HEAVY_MIN],
        "rare_mechanic": [
            r for r in eligible if any(r.get("mechanics", {}).get(f) for f in RARE_FLAGS)
        ],
        "higher_rating": [
            r
            for r in eligible
            if r.get("rating") is not None and float(r["rating"]) >= high_rating_threshold
        ],
        "long_close": [r for r in eligible if r.get("long_game") or r.get("close_game_proxy")],
        "mechanics_enriched": [r for r in eligible if _mechanic_count(r) > 0],
        "broad_random": eligible,
    }
    bucket_scores = {
        "tera_action_enriched": _tera_action_count,
        "switch_heavy": _switch_decision_count,
        "rare_mechanic": lambda r: sum(bool(r.get("mechanics", {}).get(f)) for f in RARE_FLAGS),
        "higher_rating": lambda r: float(r.get("rating") or 0),
        "long_close": lambda r: int(bool(r.get("close_game_proxy"))) * 10 + int(r.get("turn_count", 0)),
        "mechanics_enriched": _mechanic_count,
        "broad_random": None,
    }
    for bucket, target in ACTION_RANK_BUCKET_TARGETS.items():
        chosen = _take(
            bucket_candidates[bucket],
            target,
            selected_ids,
            seed=seed,
            namespace=bucket,
            score=bucket_scores[bucket],
        )
        shortfalls[bucket] = target - len(chosen)
        selections.extend((bucket, row) for row in chosen)

    if len(selections) < ACTION_RANK_TOTAL:
        fillers = _take(
            eligible,
            ACTION_RANK_TOTAL - len(selections),
            selected_ids,
            seed=seed,
            namespace="shortfall_fill",
        )
        selections.extend(("broad_random_fill", row) for row in fillers)
    if len(selections) != ACTION_RANK_TOTAL:
        raise ValueError(f"Manifest selection produced {len(selections)} rows")

    entries: List[Dict[str, Any]] = []
    for bucket, row in selections:
        mechanics = row.get("mechanics") if isinstance(row.get("mechanics"), dict) else {}
        entries.append(
            {
                "replay_id": row["replay_id"],
                "path": row["path"],
                "primary_stratum": bucket,
                "source_strata": _selection_tags(row, high_rating_threshold),
                "selection_reasons": [bucket] + _selection_tags(row, high_rating_threshold),
                "rating": row.get("rating"),
                "upload_time": row.get("upload_time"),
                "turn_count": row.get("turn_count"),
                "approx_decision_state_count": row.get("approx_decision_state_count"),
                "tera_action_count": _tera_action_count(row),
                "switch_decision_count": _switch_decision_count(row),
                "mechanics": {name: bool(mechanics.get(name)) for name in MECHANIC_FLAGS},
                "profile_version": row.get("profile_version") or PROFILE_VERSION,
                "selection_seed": seed,
            }
        )
    bucket_order = list(ACTION_RANK_BUCKET_TARGETS) + ["broad_random_fill"]
    _assign_splits_general(entries, seed, ACTION_RANK_SPLIT_TARGETS, bucket_order)
    entries.sort(
        key=lambda row: (("train", "validation", "test").index(row["split"]), row["replay_id"])
    )

    baseline = sorted(
        eligible,
        key=lambda row: _stable_random_key(seed, row["replay_id"], "random_baseline"),
    )[:ACTION_RANK_TOTAL]
    manifest = {
        "manifest_version": ACTION_RANK_MANIFEST_VERSION,
        "profile_version": PROFILE_VERSION,
        "objective": "action_rank",
        "state_feature_version": "live-private-belief-v7",
        "state_feature_dim": 3208,
        "action_feature_version": action_feature_version,
        "action_feature_dim": action_feature_dim,
        "seed": seed,
        "catalog_path": str(catalog_path),
        "catalog_checksum": catalog_checksum(catalog_path),
        "eligible_pool_size": len(eligible),
        "high_rating_threshold_top_quartile": None if not ratings else high_rating_threshold,
        "switch_heavy_min_decisions": SWITCH_HEAVY_MIN,
        "target_bucket_sizes": ACTION_RANK_BUCKET_TARGETS,
        "bucket_shortfalls_before_fill": shortfalls,
        "split_targets": ACTION_RANK_SPLIT_TARGETS,
        "random_baseline": {
            "method": "deterministic uniform sample from eligible pool",
            "mechanic_counts": _coverage(baseline),
            "enrichment": _enrichment_summary(baseline),
        },
        "selected_enrichment": _enrichment_summary([row for _, row in selections]),
        "entries": entries,
    }
    report = validate_action_rank_manifest(
        manifest, rows, total=ACTION_RANK_TOTAL, split_targets=ACTION_RANK_SPLIT_TARGETS
    )
    if not report["passed"]:
        raise ValueError(f"Action-rank manifest validation failed: {report['checks']}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    output_path.with_name(output_path.stem + "_report.md").write_text(
        _action_rank_report_markdown(manifest, report), encoding="utf-8"
    )
    print_line_safe(
        f"action-rank-manifest done | entries={len(entries)} "
        f"splits={report['split_counts']} output={output_path}"
    )
    return manifest, report


def _action_rank_report_markdown(manifest: Dict[str, Any], report: Dict[str, Any]) -> str:
    sel = manifest["selected_enrichment"]
    base = manifest["random_baseline"]["enrichment"]
    bucket_counts = Counter(entry["primary_stratum"] for entry in manifest["entries"])
    lines = [
        "# diagnostic_1000 Action-Rank Manifest Validation Report",
        "",
        f"- Overall: **{'PASS' if report['passed'] else 'FAIL'}**",
        f"- Manifest version: `{manifest['manifest_version']}`",
        f"- Objective: action-rank (state v7/3208, "
        f"action {manifest['action_feature_version']}/{manifest['action_feature_dim']})",
        f"- Seed: `{manifest['seed']}`",
        f"- Source replay pool: `{manifest['catalog_path']}`",
        f"- Catalog SHA-256: `{manifest['catalog_checksum']}`",
        f"- Eligible pool: {manifest['eligible_pool_size']:,}",
        f"- Splits: train {report['split_counts'].get('train')}, "
        f"validation {report['split_counts'].get('validation')}, "
        f"test {report['split_counts'].get('test')}",
        "",
        "## Checks",
        "",
    ]
    for name, passed in report["checks"].items():
        lines.append(f"- [{'x' if passed else ' '}] `{name}`")
    lines.extend(["", "## Selection Composition", ""])
    for bucket, count in bucket_counts.items():
        lines.append(f"- `{bucket}`: {count}")
    lines.extend(
        [
            "",
            "## Enrichment vs Random Baseline (per 1000 battles)",
            "",
            "| Metric | Selected | Random baseline |",
            "| --- | ---: | ---: |",
            f"| Tera battles | {sel['tera_battle_count']} | {base['tera_battle_count']} |",
            f"| Battles with >=1 Tera action | {sel['battles_with_tera_action']} | {base['battles_with_tera_action']} |",
            f"| Tera action total | {sel['tera_action_total']} | {base['tera_action_total']} |",
            f"| Switch decision total | {sel['switch_decision_total']} | {base['switch_decision_total']} |",
            f"| Switch decisions/battle | {sel['switch_decision_mean_per_battle']} | {base['switch_decision_mean_per_battle']} |",
            f"| Switch share of decisions | {sel['switch_share_of_decisions']} | {base['switch_share_of_decisions']} |",
            f"| Long-game rate | {sel['long_game_rate']} | {base['long_game_rate']} |",
            f"| Close-game rate | {sel['close_game_rate']} | {base['close_game_rate']} |",
            f"| Short/forfeit rate | {sel['short_or_forfeit_rate']} | {base['short_or_forfeit_rate']} |",
            f"| Rating available | {sel['rating_available_rate']} | {base['rating_available_rate']} |",
            "",
            "## Mechanic Coverage",
            "",
            f"- Selected mechanic-flag total: {report['selected_mechanic_flag_total']}",
            f"- Random-baseline mechanic-flag total: {report['random_baseline_mechanic_flag_total']}",
            "",
            "| Mechanic | Selected | Random baseline |",
            "| --- | ---: | ---: |",
        ]
    )
    for name in MECHANIC_FLAGS:
        lines.append(
            f"| `{name}` | {report['selected_mechanic_counts'][name]} | "
            f"{report['random_baseline_mechanic_counts'][name]} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the deterministic battle-level diagnostic_300 manifest.")
    parser.add_argument("--catalog", default=str(DEFAULT_CATALOG))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()
    generate_diagnostic_manifest(
        catalog_path=Path(args.catalog),
        output_path=Path(args.output),
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
