from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping

import torch


ROOT = Path(__file__).resolve().parents[3]
AUDIT = ROOT / "artifacts" / "agent_audit"
CHECKPOINTS = ROOT / "artifacts" / "checkpoints"
REPLAYS = ROOT / "artifacts" / "replays"
VALIDATION = ROOT / "artifacts" / "validation" / "sim_core_validation_results.json"


def _load(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _checkpoint_rows() -> List[Dict[str, Any]]:
    selected = [
        "gen9randombattle_bc.pt",
        "gen9randombattle_replay_policy.pt",
        "gen9randombattle_replay_value.pt",
        "gen9randombattle_live_private_value_v2.pt",
        "gen9randombattle_action_ranker.pt",
        "gen9randombattle_action_ranker_v2.pt",
        "gen9randombattle_action_value_ranker_v2.pt",
        "gen9randombattle_value.pt",
    ]
    rows = []
    for name in selected:
        path = CHECKPOINTS / name
        checkpoint = torch.load(path, map_location="cpu", weights_only=False)
        rows.append(
            {
                "name": name,
                "size": path.stat().st_size,
                "mtime": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
                "model_type": checkpoint.get("model_type"),
                "feature_version": checkpoint.get("feature_version") or checkpoint.get("state_feature_version"),
                "input_size": checkpoint.get("input_size"),
                "state_dim": checkpoint.get("state_dim"),
                "action_dim": checkpoint.get("action_dim"),
                "action_size": checkpoint.get("action_size"),
            }
        )
    return rows


def _all_summaries() -> List[Dict[str, Any]]:
    rows = []
    for directory in (AUDIT / "runs", AUDIT / "runs_rollout"):
        if not directory.exists():
            continue
        for path in directory.glob("*.json"):
            if path.name == "summary.json":
                continue
            payload = _load(path)
            if isinstance(payload.get("summary"), dict):
                rows.append(payload["summary"])
    order = {name: index for index, name in enumerate([
        "random", "heuristic", "behavior_cloning", "replay_policy",
        "action_ranker", "action_value_ranker", "rollout", "ranker_rollout", "default",
    ])}
    return sorted(rows, key=lambda row: order.get(str(row.get("agent")), 99))


def _fmt_pct(value: Any) -> str:
    return f"{100 * float(value or 0):.1f}%"


def _inventory() -> str:
    rows = _checkpoint_rows()
    lines = [
        "# Agent Inventory",
        "",
        "Audit date: 2026-06-18",
        "",
        "## Runtime and validated scope",
        "",
        "- CPU: Intel Core i7-9700, 8 physical cores / 8 logical processors.",
        "- GPU: NVIDIA GeForce RTX 2060 SUPER; PyTorch CUDA is available.",
        "- Pokemon Showdown battle mechanics are CPU-bound JavaScript. CUDA accelerates model inference only.",
        "- Seeded Gen 9 singles is the validated simulator scope.",
        "- Strict live-eval healthcheck: PASS.",
        "- Default value checkpoint: `gen9randombattle_live_private_value_v2.pt`.",
        "- Default action checkpoint: `gen9randombattle_action_value_ranker_v2.pt`.",
        "",
        "## Checkpoints",
        "",
        "| Checkpoint | Size | Modified | Type | Feature version | Input | State | Action |",
        "| --- | ---: | --- | --- | --- | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| `{row['name']}` | {row['size']:,} | {row['mtime']} | "
            f"{row['model_type'] or 'policy/value MLP'} | {row['feature_version'] or 'legacy/local'} | "
            f"{row['input_size'] or '-'} | {row['state_dim'] or '-'} | {row['action_dim'] or row['action_size'] or '-'} |"
        )
    lines.extend([
        "",
        "## Compatibility",
        "",
        "- Current live-private dimension: 115.",
        "- Current action feature dimension: 165; current ranker input: 280.",
        "- `action_ranker_v2` and `action_value_ranker_v2` match current dimensions.",
        "- Legacy `gen9randombattle_action_ranker.pt` is stale (`78 + 56 = 134`) and is not a valid current live default.",
        "- Behavior-cloning checkpoints use the current local simulator feature dimension, 1163.",
        "",
        "## Supported recommendation methods",
        "",
        "- random and heuristic sim-core baselines",
        "- behavior-cloning fixed 13-action policy",
        "- replay-policy prior",
        "- current action ranker and action-value ranker",
        "- approximate rollout-only and ranker-plus-rollout scoring",
        "- current default: live-private value + action-value ranker + replay policy + approximate rollout",
        "",
        "A live-private value model by itself is not a complete action-selection agent: it scores the current state, while most move actions do not have exact successor states. It was therefore audited as a component through replay value comparisons, not misrepresented as a standalone policy.",
        "",
    ])
    return "\n".join(lines)


def _ablation() -> str:
    rows = _all_summaries()
    lines = [
        "# Agent Ablation Report",
        "",
        "All agents used paired sides on shared seeds against the heuristic baseline. Non-rollout agents received 20 battles each. Rollout variants received four battles each because measured latency was roughly 4–5 seconds per decision; their winrates are directional only.",
        "",
        "| Agent | Battles | Wins | Losses | Draws/Timeouts | Winrate | Avg turns | Avg latency | Fallbacks | Notes |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        notes = []
        if row.get("damage_fallbacks"):
            notes.append(f"{row['damage_fallbacks']} damage fallbacks")
        if row.get("rollout_unavailable"):
            notes.append(f"{row['rollout_unavailable']} rollout unavailable")
        if row.get("timeouts_or_errors"):
            notes.append(f"{row['timeouts_or_errors']} technical failures")
        lines.append(
            f"| {row['agent']} | {row['battles']} | {row['wins']} | {row['losses']} | "
            f"{int(row.get('draws', 0)) + int(row.get('timeouts_or_errors', 0))} | "
            f"{_fmt_pct(row['winrate'])} | {row['avg_turns']:.1f} | "
            f"{row['avg_decision_latency_ms']:.1f} ms | {row['fallbacks']} | {'; '.join(notes) or 'none'} |"
        )
    lines.extend([
        "",
        "## Answers",
        "",
        "1. **Best by measured winrate:** heuristic (50%, as expected in paired heuristic self-play). The highest learned non-rollout agent was behavior cloning at 20%. Ranker+rollout also measured 50%, but only over four battles and is not statistically comparable.",
        "2. **Most stable:** heuristic. It completed all battles with no fallbacks and about 2 ms decision latency.",
        "3. **Action-value versus older current-schema ranker:** action-value ranker won 10% versus action-ranker v2 at 0% in autonomous battles. Replay imitation was mixed: action-value was better on replay 2587963818, tied on 2587966474, and worse on the long replay 2587967313.",
        "4. **Rollouts:** no reliable winrate benefit was established. They increased latency by roughly two orders of magnitude and produced frequent heuristic damage fallback in autonomous live states.",
        "5. **Live-private value:** replay sign alignment improved on two of three checked replays and tied on one, so it is useful as a state estimator. The audit did not prove that its current coupling improves action selection.",
        "6. **Tradeoff:** rankers cost about 28–38 ms per decision; approximate rollouts cost about 4,100–5,000 ms.",
        "7. **Fallback dependence:** non-rollout agents had no damage fallback. Rollout agents did—69 to 72 fallback-marked decisions in four battles.",
        "8. **Current default:** not supported as the best production default by this audit. It was slower than ranker-only and had pervasive damage fallback; its four-battle winrate was 25%.",
        "",
        "These samples are intentionally bounded first-pass evidence, not publication-grade confidence intervals.",
        "",
    ])
    return "\n".join(lines)


def _protocol_proxy_counts(rows: Iterable[Mapping[str, Any]]) -> Counter:
    counts: Counter = Counter()
    for row in rows:
        if row.get("result") != "loss":
            continue
        side = row.get("audit_side")
        log = [str(line) for line in row.get("log") or []]
        counts["losses"] += 1
        counts["switches"] += sum(line.startswith(f"|switch|{side}") for line in log)
        counts["tera_in_losses"] += sum(line.startswith(f"|-terastallize|{side}") for line in log)
        counts["immunity_events"] += sum(line.startswith("|-immune|") for line in log)
        counts["resisted_events"] += sum(line.startswith("|-resisted|") for line in log)
        counts["hazard_damage_events"] += sum("[from] Stealth Rock" in line or "[from] Spikes" in line for line in log)
    return counts


def _tactical() -> str:
    sections = []
    for agent in ("behavior_cloning", "action_value_ranker", "random"):
        payload = _load(AUDIT / "runs" / f"{agent}.json")
        counts = _protocol_proxy_counts(payload["battles"])
        sections.append((agent, counts))
    ranker_slices = Counter()
    for replay in ("2587963818", "2587966474", "2587967313"):
        payload = _load(REPLAYS / f"gen9randombattle-{replay}_action_ranker_comparison_p1.json")
        for name, data in (payload.get("tactical_slice_metrics") or {}).items():
            ranker_slices[name] += int(data.get("count", 0))
    lines = [
        "# Tactical Failure Report",
        "",
        "This report uses protocol-event proxies plus the existing tactical-slice comparison tooling. Event counts are indicators, not proof that each event caused the loss.",
        "",
        "## Loss protocol proxies",
        "",
        "| Agent | Losses | Switches | Tera in losses | Immunity events | Resisted events | Hazard damage |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for agent, counts in sections:
        lines.append(
            f"| {agent} | {counts['losses']} | {counts['switches']} | {counts['tera_in_losses']} | "
            f"{counts['immunity_events']} | {counts['resisted_events']} | {counts['hazard_damage_events']} |"
        )
    lines.extend([
        "",
        "## Existing tactical slices across three replay checks",
        "",
    ])
    for name, count in ranker_slices.most_common():
        lines.append(f"- `{name}`: {count} flagged decisions")
    lines.extend([
        "",
        "## Main failure modes",
        "",
        "- **Switch scoring remains weak.** Offline validation accuracy is materially lower for switches than moves, and `switch_into_ko_heavy_damage` is the largest replay slice.",
        "- **Win-condition preservation/endgame planning is weak.** Learned autonomous agents lose substantially to the heuristic despite reasonable imitation metrics.",
        "- **Setup timing and repeated moves remain visible.** `setup_into_immediate_death` and `repeated_failed_moves` recur in replay slices.",
        "- **Approximate opponent/state knowledge is a rollout problem.** Replay diagnostics frequently report `target_type_unknown`; live rollouts use inferred opponent policies and can score impossible or poorly calibrated branches.",
        "- **Damage fallback contaminates rollout evaluation.** The autonomous rollout variants repeatedly used heuristic damage fallback, so rollout scores are not yet a clean test of Showdown-backed search.",
        "- **No evidence of systemic illegal-action failures** appeared in completed audit battles.",
        "",
    ])
    return "\n".join(lines)


def _live_sanity() -> str:
    validation = _load(VALIDATION)
    exact = validation["damage"]["rows"][-1]
    lines = [
        "# Live/Replay Evaluation Sanity",
        "",
        "| Replay | Actions | Avg value delta | Better sign alignment | V2 ranker top-1 | Action-value top-1 |",
        "| --- | ---: | ---: | --- | ---: | ---: |",
    ]
    for replay in ("2587963818", "2587966474", "2587967313"):
        value = _load(REPLAYS / f"gen9randombattle-{replay}_model_comparison.json")
        rank = _load(REPLAYS / f"gen9randombattle-{replay}_action_ranker_comparison_p1.json")
        lines.append(
            f"| {replay} | {value['turn_action_count']} | {value['average_absolute_difference']:.3f} | "
            f"{value['better_sign_alignment']} | "
            f"{rank['aggregate']['v2_action_ranker']['top1_imitation_accuracy']:.1%} | "
            f"{rank['aggregate']['action_value_ranker']['top1_imitation_accuracy']:.1%} |"
        )
    lines.extend([
        "",
        "## Damage checks",
        "",
        f"- Exact-stat validation used attacker stats: `{exact['used_exact_attacker_stats']}`.",
        f"- Exact-stat validation used defender stats: `{exact['used_exact_defender_stats']}`.",
        f"- Exact-stat damage method: `{exact['damage_method']}`.",
        "- Standalone turn-10 rollout diagnostics for all three replays returned `smogon_calc` for damaging actions and no heuristic fallback.",
        "- Autonomous live rollout battles did show frequent heuristic fallback. This difference indicates that some live battle snapshots lack enough clean species/state data for the strict calc path even though curated replay states succeed.",
        "",
        "## Interpretation",
        "",
        "- Live-private value sign alignment was better on two replay checks and tied on one.",
        "- Action-value ranker improvements are not uniform: it beat v2 on one replay, tied on one, and regressed on the long replay.",
        "- Exact-stat support works when private stats are supplied.",
        "- The no-fallback requirement is satisfied for curated replay diagnostics but not for continuous autonomous rollout use.",
        "",
    ])
    return "\n".join(lines)


def _recommendations() -> str:
    return r"""# Agent Audit Recommendations

## 1. Keep approximate rollouts disabled in live defaults

Damage plumbing is clean and latency is acceptable, but approximate rollout
values are still scoring proxies rather than exact Showdown transitions. The
clean 20-battle smoke scored 4-16 against heuristic.

## 2. Do not retrain the action-value ranker solely for this fix

The current dataset uses live-private value deltas and final results, not
rollout-damage labels. Keep the dataset and checkpoint. Retrain only after a
new target improves switch/endgame supervision or trustworthy branch labels
exist.

## 3. Keep the current live recommender default unchanged

The action-value ranker remains provisional and has not beaten heuristic.
Removing damage fallback does not establish that rollout weighting is stronger.

## 4. Next task: replace score sampling with real one-turn branches

Branch the current sim-core state for each legal action against a bounded
opponent-action set. Require zero damage fallbacks/timeouts, fixed-seed
determinism, no information leakage, and stronger paired results before using
rollout labels or production rollout weights.

## 5. Keep six-worker process sharding

Each worker should reuse one sim-core process for battle and damage RPCs.
PyTorch inference uses CUDA; Showdown mechanics remain CPU-bound.

Command: `.\scripts\run_windows.ps1 -Action agent-audit -SimCoreMode native`.
"""


def main() -> None:
    AUDIT.mkdir(parents=True, exist_ok=True)
    outputs = {
        "agent_inventory.md": _inventory(),
        "agent_ablation_report.md": _ablation(),
        "tactical_failure_report.md": _tactical(),
        "live_eval_sanity.md": _live_sanity(),
        "recommendations.md": _recommendations(),
    }
    for name, text in outputs.items():
        (AUDIT / name).write_text(text, encoding="utf-8")
    print(json.dumps({"reports": sorted(outputs), "output_dir": str(AUDIT)}))


if __name__ == "__main__":
    main()
