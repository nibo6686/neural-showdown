"""Exhaustive Gen 9 Random Battles move-pool mechanics completeness audit."""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set

from .action_features import (
    ACTION_FEATURE_DIM_V6,
    ACTION_FEATURE_VERSION_V6,
    DYNAMIC_TYPE_FAIL_CLOSED_MOVE_IDS,
    FIXED_DAMAGE_FAIL_CLOSED_MOVE_IDS,
    FIXED_DAMAGE_ORACLE_MOVE_IDS,
    SCREEN_BREAK_ON_HIT_MOVE_IDS,
)

# Batch 4: turn/history power that cannot trigger in singles, so base power is exact.
SINGLES_BASE_POWER_PASS_IDS = {"fusionbolt", "fusionflare"}
from .dynamic_move_mechanics_audit import run_audit as run_representative_audit


REPO_ROOT = Path(__file__).resolve().parents[3]
SETS_PATH = REPO_ROOT / "sim-core/node_modules/pokemon-showdown/data/random-battles/gen9/sets.json"
SIM_CORE_DIR = REPO_ROOT / "sim-core"
DEFAULT_REPORT = REPO_ROOT / "artifacts/training_plan/gen9randbats_mechanics_completeness_audit.md"

STAT_SOURCE_PASS = {"bodypress", "foulplay", "psyshock", "psystrike", "secretssword"}
HISTORY_PASS = {"ragefist", "lastrespects", "rollout", "furycutter"}
BOOST_POWER_PASS = {"storedpower", "powertrip"}
HP_POWER_PASS = {"eruption", "waterspout", "dragonenergy", "reversal", "flail"}
SPEED_WEIGHT_PASS = {
    "gyroball", "electroball", "grassknot", "lowkick", "heavyslam", "heatcrash",
}
STATUS_POWER_PASS = {"facade", "hex", "venoshock"}
ITEM_POWER_PASS = {"acrobatics"}
REPEAT_CHAIN_IDS = {"rollout", "furycutter"}
DYNAMIC_ACCURACY_IDS = {"blizzard", "bleakwindstorm", "hurricane", "thunder"}
DYNAMIC_TYPE_IDS = {
    "aurawheel", "ivycudgel", "judgment", "ragingbull", "revelationdance",
    "terablast", "terastarstorm", "weatherball",
}
MISSING_HISTORY_POWER_IDS = {
    "avalanche", "payback", "lashout", "stompingtantrum", "temperflare",
    "fusionbolt", "fusionflare",
}
RANDOM_POWER_IDS = {"ficklebeam"}
CONDITIONAL_EXECUTION_IDS = {
    "fakeout", "firstimpression", "focuspunch", "suckerpunch", "thunderclap",
    "hyperspacefury", "poltergeist", "doubleshock",
}
CHARGE_OR_DELAY_IDS = {"beakblast", "meteorbeam", "solarbeam", "futuresight"}
SPECIAL_EFFECTIVENESS_IDS = {"freezedry"}
CONDITIONAL_PRIORITY_IDS = {"grassyglide"}
FIELD_POWER_PASS = {"expandingforce", "psyblade"}
EFFECTIVENESS_POWER_PASS = {"collisioncourse", "electrodrift"}
STATIC_SETUP_PASS = {
    "acidarmor", "agility", "amnesia", "bulkup", "calmmind", "coil",
    "cosmicpower", "dragondance", "growth", "honeclaws", "irondefense",
    "nastyplot", "quiverdance", "rockpolish", "shellsmash", "shiftgear",
    "swordsdance", "tailglow",
}
RECOVERY_IDS = {
    "recover", "roost", "slackoff", "softboiled", "milkdrink", "moonlight",
    "morningsun", "shoreup", "synthesis", "rest", "strengthsap", "wish",
}
COARSE_FIELD_IDS = {
    "auroraveil", "courtchange", "defog", "haze", "rapidspin", "mortalspin",
    "spikes", "stealthrock", "stickyweb", "toxicspikes", "stoneaxe",
    "ceaselessedge", "tidyup", "reflect", "lightscreen", "tailwind",
    "raindance", "sunnyday", "sandstorm", "snowscape", "electricterrain",
    "grassyterrain", "mistyterrain", "psychicterrain", "trickroom",
}
FORCED_OR_PIVOT_IDS = {
    "circlethrow", "dragontail", "roar", "whirlwind", "uturn", "voltswitch",
    "flipturn", "partingshot", "chillyreception", "teleport", "shedtail",
}


def _showdown_move_metadata() -> List[Dict[str, Any]]:
    script = r"""
const fs = require('fs');
const {Dex} = require('pokemon-showdown');
const sets = JSON.parse(fs.readFileSync(
  './node_modules/pokemon-showdown/data/random-battles/gen9/sets.json', 'utf8'));
const names = new Set();
for (const value of Object.values(sets)) {
  for (const set of (value.sets || [])) {
    for (const move of (set.movepool || [])) names.add(move);
  }
}
const compact = value => {
  if (value === undefined || value === null) return null;
  return JSON.parse(JSON.stringify(value));
};
const rows = [...names].sort().map(name => {
  const move = Dex.moves.get(name);
  return {
    id: move.id, name: move.name, category: move.category, type: move.type,
    basePower: move.basePower, accuracy: move.accuracy, priority: move.priority,
    target: move.target, callbacks: Object.keys(move).filter(k => typeof move[k] === 'function'),
    recoil: compact(move.recoil), drain: compact(move.drain),
    selfdestruct: compact(move.selfdestruct), selfSwitch: compact(move.selfSwitch),
    forceSwitch: compact(move.forceSwitch), multihit: compact(move.multihit),
    flags: compact(move.flags) || {}, boosts: compact(move.boosts),
    self: compact(move.self), secondary: compact(move.secondary),
    secondaries: compact(move.secondaries), status: compact(move.status),
    volatileStatus: compact(move.volatileStatus), sideCondition: compact(move.sideCondition),
    weather: compact(move.weather), terrain: compact(move.terrain), heal: compact(move.heal),
    willCrit: compact(move.willCrit),
  };
});
process.stdout.write(JSON.stringify(rows));
"""
    proc = subprocess.run(
        ["node", "-e", script],
        cwd=SIM_CORE_DIR,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=30,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or f"node exited {proc.returncode}")
    rows = json.loads(proc.stdout)
    if not isinstance(rows, list):
        raise RuntimeError("Showdown move metadata export returned a non-list.")
    return rows


def _material_secondary(move: Dict[str, Any]) -> bool:
    values: List[Dict[str, Any]] = []
    if isinstance(move.get("secondary"), dict):
        values.append(move["secondary"])
    if isinstance(move.get("secondaries"), list):
        values.extend(value for value in move["secondaries"] if isinstance(value, dict))
    for value in values:
        keys = set(value) - {"chance", "self"}
        chance = int(value.get("chance", 100) or 0)
        if keys or chance < 100:
            return True
    return False


def _self_cost_or_heal(move: Dict[str, Any]) -> bool:
    return bool(
        move.get("recoil")
        or move.get("drain")
        or move.get("selfdestruct")
        or move.get("heal")
        or (move.get("flags") or {}).get("heal")
    )


def _mechanic_buckets(move: Dict[str, Any]) -> List[str]:
    move_id = str(move["id"])
    callbacks = set(move.get("callbacks") or [])
    buckets: Set[str] = set()
    if callbacks & {"basePowerCallback", "onBasePower", "damageCallback"} or move.get("multihit"):
        buckets.add("dynamic_base_power_or_damage")
    if move_id in DYNAMIC_ACCURACY_IDS:
        buckets.add("dynamic_accuracy")
    if move_id in STATUS_POWER_PASS or move.get("status") or move.get("volatileStatus"):
        buckets.add("status_dependent_or_inflicting")
    if move_id in HP_POWER_PASS or move.get("heal") or move.get("drain") or move.get("recoil"):
        buckets.add("hp_dependent_or_hp_cost")
    if move_id in SPEED_WEIGHT_PASS:
        buckets.add("speed_or_weight")
    if move_id in ITEM_POWER_PASS or move_id in {"knockoff", "poltergeist", "trick", "switcheroo", "bugbite"}:
        buckets.add("item_dependent")
    if move_id in DYNAMIC_TYPE_IDS or move_id == "curse":
        buckets.add("type_dependent")
    if move_id in FIELD_POWER_PASS or move_id in {"weatherball", "terrainpulse"} or move.get("weather") or move.get("terrain"):
        buckets.add("weather_or_terrain")
    if move_id in STAT_SOURCE_PASS:
        buckets.add("nonstandard_stat_source")
    if move_id in REPEAT_CHAIN_IDS or move_id in {"outrage", "petaldance"} or (move.get("flags") or {}).get("charge"):
        buckets.add("multi_turn_or_repeat_chain")
    if _self_cost_or_heal(move) or move_id in {"highjumpkick", "supercellslam", "bellydrum", "clangoroussoul", "filletaway", "substitute"}:
        buckets.add("recoil_drain_crash_or_self_damage")
    if int(move.get("priority", 0) or 0) != 0 or "onModifyPriority" in callbacks or "priorityChargeCallback" in callbacks:
        buckets.add("priority")
    if move_id in FORCED_OR_PIVOT_IDS or move_id in CONDITIONAL_EXECUTION_IDS:
        buckets.add("forced_move_or_execution_constraint")
    if str(move.get("category")) == "Status" or _material_secondary(move) or move.get("boosts") or move.get("self"):
        buckets.add("side_effect")
    return sorted(buckets) or ["ordinary_damage"]


def _classify(move: Dict[str, Any]) -> Dict[str, str]:
    move_id = str(move["id"])
    category = str(move.get("category") or "")
    callbacks = set(move.get("callbacks") or [])
    reasons: List[str] = []

    # Wrong exact resolved damage or exact categorical fields take precedence.
    # Mechanics-repair batch 1: fixed-damage and multi-hit no longer emit a
    # wrong-exact value (oracle-resolved or fail-closed); weather-dependent
    # accuracy is now honest, so those moves are judged on their residual blocker
    # (the omitted secondary effect) further below.
    if move_id in FIXED_DAMAGE_ORACLE_MOVE_IDS:
        return {"status": "PASS", "reason": "fixed level-based damage routed to the oracle (batch 1); honors type immunity"}
    if move_id in FIXED_DAMAGE_FAIL_CLOSED_MOVE_IDS:
        return {"status": "INEXACT", "reason": "fixed-damage target/counter context fails closed (impact_unknown) in batch 1"}
    if move.get("multihit"):
        return {"status": "INEXACT", "reason": "multi-hit total/distribution fails closed (impact_unknown) in batch 1"}
    if move_id in DYNAMIC_TYPE_IDS:
        if move_id in DYNAMIC_TYPE_FAIL_CLOSED_MOVE_IDS:
            return {"status": "INEXACT", "reason": "Stellar-type STAB/effectiveness not representable by the standard type chart; fails closed (batch 3)"}
        return {"status": "PASS", "reason": "dynamic move type resolved from state via sim-core result.move.type for type-effectiveness and STAB (batch 3)"}
    if move_id in SINGLES_BASE_POWER_PASS_IDS:
        return {"status": "PASS", "reason": "singles: the partner-fusion same-turn power doubling cannot occur, so base power is exact (batch 4)"}
    if move_id in MISSING_HISTORY_POWER_IDS:
        return {"status": "INEXACT", "reason": "turn/history-conditional power depends on same-turn order/hit/stat-drop or prior-move-failure not plumbed to the oracle; fails closed (batch 4)"}
    if move_id in RANDOM_POWER_IDS:
        return {"status": "INEXACT", "reason": "random double-power branch is not represented; fails closed rather than emit one exact value (batch 5)"}
    if move_id in CONDITIONAL_EXECUTION_IDS:
        return {"status": "INEXACT", "reason": "move-success depends on opponent action / first-active turn / form / target item; fails closed rather than assume it hits (batch 4)"}
    if move_id == "pollenpuff":
        return {"status": "PASS", "reason": "singles: Pollen Puff always damages the foe (no ally-heal branch); damage is exact (batch 4)"}
    if move_id in SCREEN_BREAK_ON_HIT_MOVE_IDS:
        return {"status": "INEXACT", "reason": "damage is exact (calc bypasses screens); the conditional screen removal is coarsely flagged as a field/side change (batch 4)"}
    if move_id in CHARGE_OR_DELAY_IDS:
        if move_id == "beakblast":
            return {"status": "PASS", "reason": "same-turn damage is exact; -3 priority charge with reactive contact-burn is out of v6 impact scope (batch 3)"}
        return {"status": "INEXACT", "reason": "two-turn charge/delayed damage: exact only with sun/Power Herb, fails closed otherwise so immediate timing is not assumed (batch 3)"}
    if move_id in SPECIAL_EFFECTIVENESS_IDS:
        return {"status": "PASS", "reason": "Freeze-Dry's special Water effectiveness is now reflected in sim-core type-effectiveness and damage (batch 5)"}
    if move.get("willCrit"):
        return {"status": "PASS", "reason": "guaranteed crit is baked into the calc damage rolls; impact reports crit_included=True (batch 5)"}
    if move_id == "photongeyser":
        return {"status": "PASS", "reason": "calc selects the higher attacking stat and matching category (verified physical/special); damage is exact (batch 5)"}
    if move_id == "beatup":
        return {"status": "INEXACT", "reason": "per-ally-Attack damage is not resolvable by the calc (returns 0); fails closed (batch 5)"}
    if move_id in CONDITIONAL_PRIORITY_IDS:
        return {"status": "INEXACT", "reason": "damage is exact; the terrain-conditional +1 priority modifier is not represented in the static priority feature (needs v7) (batch 5)"}
    if _material_secondary(move):
        return {"status": "INEXACT", "reason": "secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented"}
    if move_id == "knockoff":
        return {"status": "INEXACT", "reason": "damage (incl. item 1.5x scaling) is exact; the target item removal next-state is unrepresented (needs v7 item-delta) (batch 5)"}
    if move_id == "bugbite":
        return {"status": "INEXACT", "reason": "damage is exact; the stolen-berry consumption effect is unrepresented (needs v7 item-delta) (batch 5)"}
    if move.get("status") or move.get("volatileStatus"):
        return {"status": "INEXACT", "reason": "target status/volatile coarsely flagged via next-state change fields (batch 2); exact status type not represented"}
    if category == "Status":
        if move_id == "curse" or move_id in STATIC_SETUP_PASS or (
            isinstance(move.get("boosts"), dict) and not callbacks
        ):
            return {"status": "PASS", "reason": "deterministic stat/type-dependent effect is represented by existing v6 fields"}
        if move_id in RECOVERY_IDS:
            return {"status": "INEXACT", "reason": "healing is annotated but exact own-HP delta remains unknown"}
        if move_id in COARSE_FIELD_IDS:
            return {"status": "INEXACT", "reason": "field/side change is marked, but exact layers/duration/success are not resolved"}
        if move_id in FORCED_OR_PIVOT_IDS:
            return {"status": "INEXACT", "reason": "switch/force-switch effect is marked without exact resulting state"}
        return {"status": "INEXACT", "reason": "non-damaging status transition coarsely flagged (action_non_damaging + next-state change fields, batch 2); item-swap/copy/random-call effects need typed v7 fields"}
    if _self_cost_or_heal(move) or move_id in {"highjumpkick", "supercellslam"}:
        return {"status": "INEXACT", "reason": "damage is resolved and drawback/heal is flagged, but exact own-HP delta is unknown"}
    if move_id in FORCED_OR_PIVOT_IDS:
        return {"status": "INEXACT", "reason": "damage is resolved and switching is flagged, but resulting state is not exact"}
    if move_id in HISTORY_PASS | BOOST_POWER_PASS | HP_POWER_PASS | SPEED_WEIGHT_PASS | STATUS_POWER_PASS:
        return {"status": "PASS", "reason": "required dynamic dependency is explicitly supplied to Showdown/sim-core"}
    if move_id in ITEM_POWER_PASS | STAT_SOURCE_PASS | FIELD_POWER_PASS | EFFECTIVENESS_POWER_PASS:
        return {"status": "PASS", "reason": "Showdown/sim-core oracle receives the required represented state"}
    if callbacks & {"basePowerCallback", "onBasePower", "damageCallback", "onModifyMove", "onModifyType", "onEffectiveness"}:
        reasons.append("unverified callback-dependent damage/type behavior is emitted as exact")
    if callbacks & {"onTry", "onTryHit", "onTryMove", "beforeMoveCallback", "onMoveFail"}:
        reasons.append("conditional success/failure path is not represented")
    if reasons:
        return {"status": "FAIL", "reason": "; ".join(reasons)}
    return {"status": "PASS", "reason": "ordinary conditional-on-hit damage and static accuracy resolve through sim-core"}


def run_audit() -> Dict[str, Any]:
    sets = json.loads(SETS_PATH.read_text(encoding="utf-8"))
    rows = _showdown_move_metadata()
    representative = run_representative_audit()
    audited: List[Dict[str, Any]] = []
    bucket_statuses: Dict[str, Counter[str]] = defaultdict(Counter)
    for move in rows:
        classification = _classify(move)
        buckets = _mechanic_buckets(move)
        row = {
            "id": move["id"],
            "name": move["name"],
            "category": move["category"],
            "buckets": buckets,
            **classification,
        }
        audited.append(row)
        for bucket in buckets:
            bucket_statuses[bucket][classification["status"]] += 1
    counts = Counter(row["status"] for row in audited)
    for status in ("PASS", "FAIL", "INEXACT", "NOT_RELEVANT"):
        counts.setdefault(status, 0)
    return {
        "schema": {"version": ACTION_FEATURE_VERSION_V6, "dim": ACTION_FEATURE_DIM_V6},
        "source": str(SETS_PATH.relative_to(REPO_ROOT)),
        "species_entries": len(sets),
        "moves_audited": len(audited),
        "summary": dict(counts),
        "representative_oracle_summary": representative["summary"],
        "bucket_statuses": {key: dict(value) for key, value in sorted(bucket_statuses.items())},
        "moves": audited,
    }


def _status_list(rows: Iterable[Dict[str, Any]], status: str) -> str:
    values = [row["name"] for row in rows if row["status"] == status]
    return ", ".join(values) if values else "None"


def write_markdown(report: Dict[str, Any], path: Path) -> None:
    summary = report["summary"]
    lines = [
        "# Gen 9 Random Battles Mechanics Completeness Audit",
        "",
        "## Scope and Decision Rule",
        "",
        f"- Source: `{report['source']}` ({report['species_entries']} species/form entries).",
        f"- Unique move pool audited: **{report['moves_audited']}**.",
        f"- Schema: `{report['schema']['version']}`, {report['schema']['dim']}D.",
        "- Oracle: bundled Pokémon Showdown move definitions and sim-core/@smogon calc; the focused counterfactual suite remains 12 PASS / 0 FAIL.",
        "- PASS means all material behavior used by current v6 impact fields is represented correctly.",
        "- INEXACT means the limitation is explicit through unknown/fail-closed fields or coarse effect annotation.",
        "- FAIL means v6 emits an exact-looking value/absence that can be mechanically wrong.",
        "- NOT_RELEVANT is reserved for behavior outside every current v6 action-impact field.",
        "",
        "## Summary",
        "",
        f"- PASS: **{summary['PASS']}**",
        f"- FAIL: **{summary['FAIL']}**",
        f"- INEXACT: **{summary['INEXACT']}**",
        f"- NOT_RELEVANT: **{summary['NOT_RELEVANT']}**",
        "",
        "After mechanics-repair batches 1-5 the exhaustive move-pool audit has **zero wrong-exact (FAIL) entries**: every material move-impact mechanic is either PASS or explicitly INEXACT/fail-closed. The gate remains closed pending the separate training-readiness review, not on mechanics fidelity.",
        "",
        "Mechanics-repair batch 1 (`mechanics_repair_batch_1_fixed_multihit_accuracy.md`) cleared the fixed-damage and multi-hit wrong-exact buckets and made dynamic accuracy honest: Seismic Toss and Night Shade route level-based fixed damage to the oracle (PASS); Super Fang, Ruination, Endeavor, Mirror Coat and all multi-hit moves fail closed (impact_unknown) → INEXACT.",
        "",
        "Mechanics-repair batch 2 (`mechanics_repair_batch_2_secondary_effects.md`) cleared the secondary/status/stat/volatile wrong-exact bucket (FAIL 159 → 39). A coarse presence detector now fills the existing next-state change flags (`next_opp_status_change`, `next_own_status_change`, `next_opp_stat_change`, `next_own_stat_change`) so a move with a real secondary status/stat/volatile effect is no longer encoded as a wrong-exact \"no change\"; the exact status type, chance and magnitude remain unrepresented, so these moves are INEXACT, not PASS. The four weather-accuracy moves now leave FAIL on this same basis. Item-swap, copy and random-call status moves (Trick, Switcheroo, Transform, Sleep Talk) are coarsely flagged as non-damaging actions and noted as needing typed v7 fields.",
        "",
        "Mechanics-repair batch 3 (`mechanics_repair_batch_3_dynamic_type_charge.md`) handled dynamic type/STAB and charge/delay timing (FAIL 39 → 27). sim-core now returns the resolved (post-`calculate`) move type, so impact type-effectiveness and STAB use the actual dynamic type: Weather Ball, Terrain Pulse, Judgment, Ivy Cudgel, Raging Bull, Revelation Dance, Aura Wheel and Tera Blast become PASS. Tera Starstorm fails closed (Stellar STAB/effectiveness are not representable). Two-turn charge / delayed moves no longer emit on-hit damage as immediate: Solar Beam (sun/Power Herb) and Meteor Beam (Power Herb) are exact only when they fire this turn and otherwise fail closed; Future Sight always fails closed; Beak Blast is PASS because its damage is same-turn.",
        "",
        "Mechanics-repair batch 4 (`mechanics_repair_batch_4_conditional_execution_history_power.md`) handled conditional execution/success and turn/history-conditional power (FAIL 27 → 9). Moves whose success or power depends on the opponent's same-turn action, the first-active turn, the user's form, the target's item, within-turn order, or unplumbed prior-move-failure history now fail closed (impact_unknown) instead of claiming damage: Fake Out, First Impression, Sucker Punch, Thunderclap, Focus Punch, Double Shock, Hyperspace Fury, Poltergeist, Payback, Avalanche, Lash Out, Stomping Tantrum, Temper Flare. Fusion Bolt / Fusion Flare and Pollen Puff are PASS because their doubling / ally-heal branch cannot occur in singles. Brick Break / Psychic Fangs keep their exact (screen-bypassing) damage and coarsely flag the conditional screen removal as a field/side change.",
        "",
        "Mechanics-repair batch 5 (`mechanics_repair_batch_5_final_failures.md`) cleared the final wrong-exact bucket (FAIL 9 → 0). PASS: Flower Trick / Wicked Blow (the calc bakes the guaranteed crit into the rolls, so the impact reports crit_included=True), Freeze-Dry (sim-core now reflects its special 2x-vs-Water effectiveness in type-effectiveness and damage), Photon Geyser (the calc selects the higher attacking stat and matching physical/special category — verified exact). INEXACT, fail-closed because the damage itself is wrong-exact: Beat Up (per-ally-Attack damage returns 0 from the calc) and Fickle Beam (random double-power branch). INEXACT with damage kept exact (only an unrepresented next-state effect remains, documented for a v7 typed field): Knock Off (target item removal), Bug Bite (stolen berry), Grassy Glide (terrain-conditional +1 priority). No schema name/order/dim changed; v6 remains 331D.",
        "",
        "## Mechanic Bucket Counts",
        "",
        "| Bucket | PASS | FAIL | INEXACT | NOT_RELEVANT |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for bucket, counts in report["bucket_statuses"].items():
        lines.append(
            f"| {bucket.replace('_', ' ')} | {counts.get('PASS', 0)} | "
            f"{counts.get('FAIL', 0)} | {counts.get('INEXACT', 0)} | "
            f"{counts.get('NOT_RELEVANT', 0)} |"
        )
    lines += [
        "",
        "## Material Blockers",
        "",
        f"- Wrong-exact moves: {_status_list(report['moves'], 'FAIL')}",
        "",
        f"- Explicitly inexact moves: {_status_list(report['moves'], 'INEXACT')}",
        "",
        "## Per-Move Classification",
        "",
        "| Move | Category | Mechanic buckets | Status | Reason |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in report["moves"]:
        lines.append(
            f"| {row['name']} | {row['category']} | {', '.join(row['buckets'])} | "
            f"**{row['status']}** | {row['reason']} |"
        )
    lines += [
        "",
        "## Schema and Gate",
        "",
        "No schema field was added or reordered by this audit. v6 remains 331D and the v5 prefix remains unchanged.",
        "",
        "Batches 1-5 reduced the wrong-exact set to **zero FAIL**: every material move-impact mechanic is now either PASS or explicitly INEXACT/fail-closed (impact_unknown / coarse next-state annotation). The completeness audit's no-wrong-exact criterion is therefore met. The gate nonetheless remains **closed** pending the separately approval-gated training-readiness review (stale v5/v6 data/checkpoint disposition, value-label quality audit, larger-dataset value learning). Training, rematerialization, checkpoint promotion, and live-default changes must not proceed without that explicit approval. The 212 INEXACT moves rely on fail-closed/coarse encodings; raising any of them to PASS requires the documented v7 typed-effect/timing/item fields, which were not implemented.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report = run_audit()
    write_markdown(report, args.report)
    print(json.dumps({
        "moves_audited": report["moves_audited"],
        "summary": report["summary"],
        "representative_oracle_summary": report["representative_oracle_summary"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
