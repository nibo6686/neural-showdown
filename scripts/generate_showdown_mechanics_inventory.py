"""Generate a source-driven Pokemon Showdown mechanics edge-case inventory.

Audit utility only. It reads local bundled Showdown/sim-core source and writes
the training-plan JSON + Markdown inventory artifacts.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PS = ROOT / "sim-core" / "node_modules" / "pokemon-showdown"
OUT_JSON = ROOT / "artifacts" / "training_plan" / "showdown_mechanics_edge_case_inventory.json"
OUT_MD = ROOT / "artifacts" / "training_plan" / "showdown_mechanics_edge_case_inventory_report.md"

HOOKS = [
    "onTry", "onTryHit", "onPrepareHit", "onModifyMove", "onModifyType",
    "onModifyPriority", "onBasePower", "onSourceBasePower",
    "onModifyDamage", "onEffectiveness", "onHit", "onAfterHit",
    "onAfterMove", "onAfterMoveSecondary", "onAfterMoveSecondarySelf",
    "onResidual", "onBeforeMove", "onDisableMove", "onSwitchIn",
    "onSwitchOut", "onDragOut", "onFaint", "condition",
    "volatileStatus", "self.volatileStatus", "secondary", "secondaries",
    "flags", "multihit", "critRatio", "hasSheerForceBoost",
    "overrideOffensiveStat", "overrideDefensiveStat",
]
HOOK_RE = re.compile(r"\b(?:" + "|".join(re.escape(h) for h in HOOKS) + r")\b")

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
NEXT_ORDER = {
    "rollout parity batch 5": 0,
    "state-schema/provenance design": 1,
    "v7 batch 9": 2,
    "format-scoped adapter": 3,
    "deferred NatDex/old-gen backlog": 4,
    "no action now": 5,
}


def source_files() -> list[Path]:
    files = [
        PS / "data" / "moves.ts",
        PS / "data" / "abilities.ts",
        PS / "data" / "items.ts",
        PS / "data" / "conditions.ts",
        PS / "data" / "rulesets.ts",
        PS / "data" / "scripts.ts",
        PS / "config" / "formats.ts",
        PS / "sim" / "dex-moves.ts",
    ]
    mods = PS / "data" / "mods"
    for name in ("moves.ts", "abilities.ts", "items.ts", "conditions.ts", "scripts.ts", "rulesets.ts"):
        files.extend(sorted(mods.glob(f"**/{name}")))
    files.extend(sorted((ROOT / "sim-core" / "src").glob("**/*.ts")))
    seen: set[str] = set()
    out = []
    for path in files:
        key = str(path)
        if path.exists() and key not in seen:
            seen.add(key)
            out.append(path)
    return out


def to_rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def scan_sources() -> tuple[list[dict[str, Any]], dict[str, list[str]], Counter[str]]:
    scanned = []
    lines_by_file: dict[str, list[str]] = {}
    hook_counter: Counter[str] = Counter()
    for path in source_files():
        rel = to_rel(path)
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        lines_by_file[rel] = lines
        counts = Counter(HOOK_RE.findall(text))
        hook_counter.update(counts)
        scanned.append({
            "path": rel,
            "line_count": len(lines),
            "hook_occurrences": int(sum(counts.values())),
            "hooks": dict(sorted(counts.items())),
        })
    return scanned, lines_by_file, hook_counter


def find_source(
    scanned: list[dict[str, Any]],
    lines_by_file: dict[str, list[str]],
    kind: str,
    ids: str | list[str],
    *,
    patterns: str | list[str] | None = None,
    prefer_mod: str | None = None,
) -> dict[str, Any]:
    needles = [ids] if isinstance(ids, str) else list(ids)
    needles += ([patterns] if isinstance(patterns, str) else list(patterns or []))
    preferred = {
        "move": ["sim-core/node_modules/pokemon-showdown/data/moves.ts"],
        "ability": ["sim-core/node_modules/pokemon-showdown/data/abilities.ts"],
        "item": ["sim-core/node_modules/pokemon-showdown/data/items.ts"],
        "condition": ["sim-core/node_modules/pokemon-showdown/data/conditions.ts"],
        "ruleset": [
            "sim-core/node_modules/pokemon-showdown/data/rulesets.ts",
            "sim-core/node_modules/pokemon-showdown/config/formats.ts",
        ],
    }
    candidates: list[str] = []
    if prefer_mod:
        candidates.extend([
            f"sim-core/node_modules/pokemon-showdown/data/mods/{prefer_mod}/{kind}s.ts",
            f"sim-core/node_modules/pokemon-showdown/data/mods/{prefer_mod}/conditions.ts",
            f"sim-core/node_modules/pokemon-showdown/data/mods/{prefer_mod}/scripts.ts",
        ])
    candidates.extend(preferred.get(kind, []))
    for item in scanned:
        rel = item["path"]
        if rel.endswith(f"/{kind}s.ts") or (kind == "condition" and rel.endswith("/conditions.ts")):
            candidates.append(rel)
    for item in scanned:
        rel = item["path"]
        if rel.endswith(("/scripts.ts", "/dex-moves.ts", "/damage_calc.ts", "/rollout_parity_oracle.ts", "/state_extractor.ts")):
            candidates.append(rel)

    seen: set[str] = set()
    for rel in candidates:
        if rel in seen or rel not in lines_by_file:
            continue
        seen.add(rel)
        for needle in needles:
            if not needle:
                continue
            exact = re.compile(rf"^\s*{re.escape(str(needle))}\s*:\s*\{{", re.I)
            loose = re.compile(re.escape(str(needle)), re.I)
            for line_no, line in enumerate(lines_by_file[rel], start=1):
                if exact.search(line) or loose.search(line):
                    return {"file": rel, "line": line_no, "matched": needle}
    return {"file": "unknown", "line": None, "matched": needles[0] if needles else "unknown"}


def build_entries(scanned: list[dict[str, Any]], lines_by_file: dict[str, list[str]]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []

    def add(
        id_: str,
        name: str,
        kind: str,
        ids: str | list[str],
        categories: str | list[str],
        hook: str,
        gen9: str,
        natdex: str,
        oldgen: str,
        v7: str,
        rollout: str,
        needs: list[str],
        priority: str,
        reason: str,
        next_plan: str,
        *,
        patterns: str | list[str] | None = None,
        prefer_mod: str | None = None,
    ) -> None:
        entries.append({
            "id": id_,
            "name": name,
            "kind": kind,
            "source": find_source(scanned, lines_by_file, kind, ids, patterns=patterns, prefer_mod=prefer_mod),
            "hook_or_field": hook,
            "categories": categories if isinstance(categories, list) else [categories],
            "gen9_randbats_relevance": gen9,
            "natdex_future_format_relevance": natdex,
            "old_gen_only_relevance": oldgen,
            "current_v7_likely_covers": v7,
            "current_rollout_harness_likely_covers": rollout,
            "needs": needs,
            "priority": priority,
            "reason": reason,
            "recommended_next": next_plan,
        })

    # Status, counters, residuals, delayed effects.
    add("sleep-natural-counter", "Natural sleep counter/range", "condition", "slp",
        ["status and volatile counters", "no-leakage/public-information concerns"],
        "onBeforeMove / random duration", "high", "high", "medium",
        "no; action features can cause sleep but current-state counter/range is not in action v7",
        "no", ["state/provenance feature", "rollout parity fixture"], "high",
        "Showdown samples hidden sleep duration; features must expose public elapsed/range, not sampled future wake turn.",
        "state-schema/provenance design", patterns=["sleep", "random(2, 5)"])
    add("rest-fixed-sleep", "Rest fixed sleep provenance", "move", "rest",
        ["status and volatile counters", "no-leakage/public-information concerns"],
        "onHit / statusState.time", "high", "high", "medium",
        "partial; move sleep effect exists but Rest-vs-natural sleep provenance is state-level",
        "no", ["state/provenance feature", "rollout parity fixture"], "high",
        "Rest overwrites sleep duration; model needs public Rest provenance separate from natural hidden duration.",
        "state-schema/provenance design")
    add("confusion-counter", "Confusion duration/range and self-hit branch", "condition", "confusion",
        ["status and volatile counters", "branch-dependent execution", "no-leakage/public-information concerns"],
        "onBeforeMove / random duration", "high", "high", "medium",
        "partial; confusion chance exists, current counter/range is missing", "no",
        ["state/provenance feature", "rollout parity fixture"], "high",
        "Confusion duration is hidden; current action features do not expose elapsed/range or 33% self-hit branch state.",
        "state-schema/provenance design")
    add("toxic-ramp", "Toxic ramping", "condition", "tox",
        ["residual and end-of-turn effects", "status and volatile counters"],
        "onResidual", "high", "high", "low",
        "partial; action status chance exists, current toxic stage is state/rollout", "yes",
        ["state/provenance feature"], "medium",
        "Rollout batch 1 covers fixture parity when toxic stage is available; adapter still needs robust stage provenance.",
        "state-schema/provenance design", patterns=["toxic", "onResidual"])
    add("salt-cure", "Salt Cure residual normal/Water/Steel", "move", "saltcure",
        ["residual and end-of-turn effects", "dynamic type / effectiveness"],
        "volatileStatus / condition.onResidual", "high", "high", "none",
        "partial; residual pressure exists, exact current-state residual is rollout", "yes",
        ["state/provenance feature"], "medium",
        "Parity passes for represented state; broader adapters need source/effect identity and current target typing.",
        "state-schema/provenance design")
    add("future-sight", "Future Sight delayed slot damage", "move", "futuresight",
        ["delayed damage/future effects", "no-leakage/public-information concerns"],
        "flags.futuremove / onTry", "high", "high", "medium",
        "partial; action delayed pressure exists, landing damage remains rollout/state", "partial",
        ["state/provenance feature", "rollout parity fixture"], "high",
        "Scheduling parity exists; replacement damage must use landing target state, not original stale damage.",
        "rollout parity batch 5")
    add("doom-desire", "Doom Desire delayed slot damage", "move", "doomdesire",
        "delayed damage/future effects", "flags.futuremove / onTry", "medium", "medium", "medium",
        "partial; same as Future Sight", "partial",
        ["state/provenance feature", "rollout parity fixture"], "medium",
        "Shares Future Sight queue and target-slot semantics; landing damage provenance still missing generally.",
        "rollout parity batch 5")

    dynamic_damage = [
        ("ragefist", "Rage Fist times-hit power", "Requires public times-attacked history to avoid stale 50 BP damage.", "medium"),
        ("lastrespects", "Last Respects fainted-ally power", "Depends on allied faint count and battle history provenance.", "medium"),
        ("storedpower", "Stored Power / Power Trip boost count power", "Depends on current positive boosts and exact boost state.", "medium"),
        ("gyroball", "Gyro Ball speed-ratio power", "Depends on speed stats, boosts, items and field.", "medium"),
        ("electroball", "Electro Ball speed-ratio power", "Depends on speed ratio and current modifiers.", "medium"),
        ("grassknot", "Grass Knot / Low Kick weight power", "Depends on target weight and possibly form/known species.", "medium"),
        ("heavyslam", "Heavy Slam / Heat Crash weight-ratio power", "Depends on both weights and target state.", "medium"),
        ("reversal", "Reversal / Flail HP power", "Depends on exact current user HP bracket.", "medium"),
        ("beatup", "Beat Up party-member damage", "Depends on party composition and per-ally Attack stats; current impact fails closed.", "high"),
        ("ficklebeam", "Fickle Beam random double power", "Random power branch should be distribution/provenance, not deterministic damage.", "medium"),
        ("bide", "Bide stored damage release", "Depends on damage accumulated over prior turns.", "high"),
        ("counter", "Counter received physical damage", "Depends on same-turn/last damage source and amount.", "high"),
        ("mirrorcoat", "Mirror Coat received special damage", "Depends on same-turn/last damage source and amount.", "high"),
        ("metalburst", "Metal Burst received damage", "Depends on same-turn damage and move order.", "high"),
    ]
    for move_id, name, reason, priority in dynamic_damage:
        add(f"dynamic-damage-{move_id}", name, "move", move_id, "dynamic base power / damage",
            "basePowerCallback / damageCallback / onHit",
            "high" if priority == "high" else "medium", "high",
            "medium" if move_id in {"bide", "counter", "mirrorcoat", "metalburst"} else "low",
            "partial; many fail closed or use exact context where available", "no",
            ["state/provenance feature", "rollout parity fixture"], priority, reason,
            "state-schema/provenance design" if priority == "high" else "v7 batch 9")

    dynamic_type = [
        ("weatherball", "Weather Ball type/power", ["format-scoped adapter", "rollout parity fixture"], "medium", "rollout parity batch 5"),
        ("terrainpulse", "Terrain Pulse grounded type/power", ["state/provenance feature", "rollout parity fixture"], "medium", "rollout parity batch 5"),
        ("terablast", "Tera Blast current Tera type/category", ["state/provenance feature"], "medium", "v7 batch 9"),
        ("hiddenpower", "Hidden Power type generation/formats", ["format-scoped adapter"], "low", "deferred NatDex/old-gen backlog"),
        ("naturalgift", "Natural Gift berry type/power", ["format-scoped adapter", "state/provenance feature"], "low", "deferred NatDex/old-gen backlog"),
        ("freezedry", "Freeze-Dry Water effectiveness override", ["no action now"], "low", "no action now"),
        ("photongeyser", "Photon Geyser offensive stat/category override", ["no action now"], "low", "no action now"),
    ]
    for move_id, name, needs, priority, next_plan in dynamic_type:
        add(f"dynamic-type-{move_id}", name, "move", move_id, "dynamic type / effectiveness",
            "onModifyType / onEffectiveness / overrideOffensiveStat",
            "medium" if priority != "low" else "low", "high",
            "high" if move_id in {"hiddenpower", "naturalgift"} else "medium",
            "partial; exact impact handles some cases, schema lacks some provenance", "partial",
            needs, priority,
            "Source contains generation- and state-sensitive type/effectiveness behavior that should stay Showdown-format scoped.",
            next_plan)
    add("weather-primordial-sea", "Primordial Sea / Desolate Land weather prevention", "ability",
        ["primordialsea", "desolateland"], ["dynamic type / effectiveness", "accuracy / priority / target validity"],
        "onSetWeather / onTryMove", "medium", "high", "none",
        "partial; weather fields exist but primal weather prevention/attack nullification is not fully modeled", "no",
        ["state/provenance feature", "rollout parity fixture", "format-scoped adapter"], "medium",
        "Harsh weather can block Fire/Water moves and weather replacement; needs field provenance in rollout/search.",
        "rollout parity batch 5")

    branch_moves = [
        ("suckerpunch", "Sucker Punch target-action branch", "branch-dependent execution", "yes; branch pressure fields", "no", ["rollout parity fixture", "future search/branch evaluation"], "medium", "Feature marks pressure but search/rollout still needs branch evaluation.", "rollout parity batch 5"),
        ("thunderclap", "Thunderclap target-action branch", "branch-dependent execution", "yes; branch pressure fields", "no", ["rollout parity fixture", "future search/branch evaluation"], "medium", "Same target-action condition as Sucker Punch with priority context.", "rollout parity batch 5"),
        ("focuspunch", "Focus Punch lost-focus branch", "branch-dependent execution", "partial; opponent-action pressure only", "no", ["state/provenance feature", "rollout parity fixture"], "medium", "Needs within-turn damage/lost-focus provenance.", "state-schema/provenance design"),
        ("fakeout", "Fake Out first-active-turn condition", "branch-dependent execution", "yes; active-turn branch", "no", ["state/provenance feature", "rollout parity fixture"], "medium", "Needs active-turn counter/provenance to resolve exact legality/success.", "state-schema/provenance design"),
        ("firstimpression", "First Impression first-active-turn condition", "branch-dependent execution", "yes; active-turn branch", "no", ["state/provenance feature", "rollout parity fixture"], "medium", "Same first-active-turn provenance need as Fake Out.", "state-schema/provenance design"),
        ("feint", "Feint Gen 9 Protect-breaking behavior", "format/generation overrides", "yes; not treated as old-gen branch", "no", ["format-scoped adapter"], "low", "Current Gen 9 behavior differs from older assumptions; keep format-scoped.", "format-scoped adapter"),
        ("pursuit", "Pursuit target-switch old/NatDex behavior", "branch-dependent execution", "partial; batch 7 marks future-format pressure", "no", ["format-scoped adapter", "future search/branch evaluation"], "low", "Absent from current Gen 9 Randbats but important for NatDex/old-gen adapters.", "deferred NatDex/old-gen backlog"),
        ("powder", "Powder Fire-move prevention", "accuracy / priority / target validity", "partial; volatile pressure only", "no", ["state/provenance feature", "rollout parity fixture"], "medium", "Needs volatile prevention callback routing for Fire moves.", "rollout parity batch 5"),
    ]
    for move_id, name, category, v7, rollout, needs, priority, reason, next_plan in branch_moves:
        add(f"branch-{move_id}", name, "move", move_id, category, "onTry / onTryHit / condition",
            "high" if priority != "low" else "low", "high", "high" if move_id in {"feint", "pursuit"} else "low",
            v7, rollout, needs, priority, reason, next_plan)
    add("priority-psychic-terrain", "Psychic Terrain priority prevention", "condition", "psychicterrain",
        ["accuracy / priority / target validity", "ability-triggered prevention/modification"],
        "onTryHit / terrain condition", "high", "high", "none",
        "yes; priority/timing and branch risk fields", "yes", ["rollout parity fixture"], "low",
        "Already has fixed fixtures for grounded priority prevention; keep as regression coverage.", "no action now")
    add("terrain-status-prevention", "Misty/Electric Terrain status prevention", "condition",
        ["mistyterrain", "electricterrain"], ["accuracy / priority / target validity", "ability-triggered prevention/modification"],
        "onSetStatus / terrain condition", "high", "high", "none",
        "partial; status action effects exist, prevention is rollout", "yes", ["rollout parity fixture"], "low",
        "Current parity passes selected terrain prevention; keep expanding only if new callbacks appear.", "no action now")

    secondary = [
        ("move", "flowertrick", "Guaranteed crit moves", "crit chance and crit rules", "willCrit / critRatio", "high", "high", "medium", "yes; guaranteed_crit", ["no action now"], "low", "Batch 7 distinguishes guaranteed from ordinary crit.", "no action now"),
        ("ability", "serenegrace", "Serene Grace secondary chance modifier", "secondary effects and secondary modifiers", "onModifyMove", "high", "high", "none", "yes; batch 8 modifier fields", ["rollout parity fixture"], "medium", "Features now expose modified chance; rollout/search still should verify outcome provenance.", "rollout parity batch 5"),
        ("ability", "sheerforce", "Sheer Force secondary removal and power boost", "secondary effects and secondary modifiers", "onBasePower / hasSheerForceBoost", "high", "high", "none", "partial; batch 8 marks secondary removal, damage power interaction needs audit", ["v7 action feature", "rollout parity fixture"], "high", "Need ensure damage estimates include Sheer Force power and no secondary side effects.", "v7 batch 9"),
        ("ability", "shielddust", "Shield Dust secondary blocking", "secondary effects and secondary modifiers", "onModifySecondaries", "medium", "high", "none", "yes when known target ability", ["rollout parity fixture"], "medium", "Feature provenance exists; transition tests should verify blocking.", "rollout parity batch 5"),
        ("item", "covertcloak", "Covert Cloak secondary blocking", "secondary effects and secondary modifiers", "onModifySecondaries", "medium", "high", "none", "yes when known target item", ["rollout parity fixture"], "medium", "Feature provenance exists; transition tests should verify blocking.", "rollout parity batch 5"),
    ]
    for kind, idv, name, category, hook, gen9, nat, old, v7, needs, priority, reason, next_plan in secondary:
        add(f"secondary-{idv}", name, kind, idv, category, hook, gen9, nat, old, v7, "no", needs, priority, reason, next_plan)

    call_multihit = [
        ("populationbomb", "Population Bomb sequential multiaccuracy", "multi-hit and sequential-hit behavior", "yes; batch 7 sequential distribution", ["rollout parity fixture"], "medium", "Features summarize expected hit count but rollout needs distribution fixture.", "rollout parity batch 5"),
        ("tripleaxel", "Triple Axel sequential hit power ramp", "multi-hit and sequential-hit behavior", "yes; batch 7 sequential and per-hit power fields", ["rollout parity fixture"], "medium", "Needs fixture for miss-stop and per-hit power ramp.", "rollout parity batch 5"),
        ("bulletseed", "2-5 hit distribution", "multi-hit and sequential-hit behavior", "yes; batch 7 distribution", ["rollout parity fixture"], "low", "Feature has distribution summary; exact rollout can stay future unless decision impact needs it.", "rollout parity batch 5"),
        ("metronome", "Metronome format callable pool", "random-call and callable-pool behavior", "yes; batch 7 pool summary", ["format-scoped adapter", "no-leakage test"], "medium", "Pool must remain format-scoped and not leak sampled called move.", "format-scoped adapter"),
        ("sleeptalk", "Sleep Talk current move callable pool", "random-call and callable-pool behavior", "yes when current moves known", ["state/provenance feature", "no-leakage test"], "medium", "Needs sleep-state and known move-slot provenance; do not sample future called move.", "state-schema/provenance design"),
        ("copycat", "Copycat last-move callable", "random-call and callable-pool behavior", "partial; dependency flag only", ["state/provenance feature", "format-scoped adapter"], "medium", "Requires reliable last-move provenance and format exclusions.", "state-schema/provenance design"),
        ("mirrormove", "Mirror Move target last move", "random-call and callable-pool behavior", "partial; dependency flag only", ["state/provenance feature", "format-scoped adapter"], "low", "Mostly future-format; needs target last-move provenance.", "deferred NatDex/old-gen backlog"),
        ("assist", "Assist party callable pool", "random-call and callable-pool behavior", "partial; batch 7 marks party/format dependency", ["format-scoped adapter", "state/provenance feature"], "low", "Absent from current Gen 9 Randbats but important for NatDex/Assist-abuse teams.", "deferred NatDex/old-gen backlog"),
    ]
    for move_id, name, category, v7, needs, priority, reason, next_plan in call_multihit:
        add(f"call-multihit-{move_id}", name, "move", move_id, category, "multihit / multiaccuracy / onHit",
            "high" if priority == "medium" else "low", "high", "medium",
            v7, "no", needs, priority, reason, next_plan)
    add("multihit-loadeddice", "Loaded Dice multi-hit modification", "item", "loadeddice",
        "multi-hit and sequential-hit behavior", "onModifyMove", "high", "high", "none",
        "yes when known item", "no", ["rollout parity fixture"], "medium",
        "Changes 2-5 and Population Bomb hit distribution when item known.", "rollout parity batch 5")
    add("multihit-skilllink", "Skill Link max-hit guarantee", "ability", "skilllink",
        "multi-hit and sequential-hit behavior", "onModifyMove", "high", "high", "none",
        "yes when known ability", "no", ["rollout parity fixture"], "medium",
        "Forces max hits and removes multiaccuracy when ability known.", "rollout parity batch 5")

    switch_items = [
        ("move", "uturn", "Self-pivot follow-up replacement", "switch / drag / pivot / forced replacement", "selfSwitch", "high", "high", "yes; batch 8", ["future search/branch evaluation"], "medium", "Action label remains U-turn; replacement is later forced decision.", "state-schema/provenance design"),
        ("move", "memento", "Self-KO sacrifice replacement", "switch / drag / pivot / forced replacement", "selfdestruct", "medium", "high", "yes; batch 8", ["rollout parity fixture"], "medium", "Needs transition/replacement fixture for sacrifice tempo.", "rollout parity batch 5"),
        ("move", "roar", "Phazing forced target switch", "switch / drag / pivot / forced replacement", "forceSwitch / drag", "medium", "high", "yes; batch 8", ["rollout parity fixture", "future search/branch evaluation"], "medium", "Features pressure; rollout/search must model random replacement branch.", "rollout parity batch 5"),
        ("item", "ejectbutton", "Eject Button hit-triggered switch", "item-triggered effects", "onAfterMoveSecondary", "medium", "high", "yes when known item", ["rollout parity fixture", "future search/branch evaluation"], "medium", "Needs branch fixture for item-triggered switch after damage.", "rollout parity batch 5"),
        ("item", "ejectpack", "Eject Pack stat-drop switch", "item-triggered effects", "onAfterBoost", "medium", "high", "yes when known item", ["rollout parity fixture"], "medium", "Needs stat-drop trigger and suppression provenance.", "rollout parity batch 5"),
        ("item", "redcard", "Red Card forced target switch", "item-triggered effects", "onAfterMoveSecondary", "medium", "high", "yes when known item", ["rollout parity fixture", "future search/branch evaluation"], "medium", "Needs forced random replacement branch fixture.", "rollout parity batch 5"),
        ("ability", "magicbounce", "Magic Bounce reflection", "ability-triggered prevention/modification", "onTryHit", "high", "high", "partial/no; known rollout GAP", ["state/provenance feature", "rollout parity fixture"], "high", "Needs reflected action target and side-effect provenance.", "rollout parity batch 5"),
        ("ability", "goodasgold", "Good as Gold status move blocking", "ability-triggered prevention/modification", "onTryHit", "high", "high", "partial/no; known rollout GAP", ["state/provenance feature", "rollout parity fixture"], "high", "Needs reliable ability provenance and generalized status callback routing.", "rollout parity batch 5"),
        ("ability", "damp", "Damp Explosion prevention", "ability-triggered prevention/modification", "onAnyTryMove", "medium", "high", "partial; prevention helper covers represented state", ["rollout parity fixture"], "low", "Existing parity passes Damp Explosion; keep regression.", "no action now"),
        ("ability", "soundproof", "Soundproof sound-move immunity", "ability-triggered prevention/modification", "onTryHit", "medium", "high", "partial; coarse blocker exists", ["rollout parity fixture"], "medium", "Needs generalized flag-based prevention fixtures beyond coarse tactical blocker.", "rollout parity batch 5"),
        ("ability", "bulletproof", "Bulletproof bullet-move immunity", "ability-triggered prevention/modification", "onTryHit", "medium", "high", "partial; coarse blocker exists", ["rollout parity fixture"], "medium", "Needs generalized flag-based prevention fixtures.", "rollout parity batch 5"),
    ]
    for kind, idv, name, category, hook, gen9, nat, v7, needs, priority, reason, next_plan in switch_items:
        add(f"switch-prevention-{idv}", name, kind, idv, category, hook, gen9, nat, "none",
            v7, "partial" if priority != "high" else "no", needs, priority, reason, next_plan)

    residual_format = [
        ("condition", "partiallytrapped", "Binding/partial trapping duration and source", "residual and end-of-turn effects", "onResidual", "high", "high", "high", "partial; binding pressure only", "no; known GAP", ["state/provenance feature", "rollout parity fixture"], "high", "Needs source activity/effect, duration, and Binding Band divisor.", "rollout parity batch 5", None),
        ("condition", "sandstorm", "Sandstorm residual", "residual and end-of-turn effects", "onResidual", "high", "high", "medium", "partial; rollout not action schema", "yes", ["no action now"], "low", "Fixture already passes ordinary sandstorm chip for represented state.", "no action now", None),
        ("condition", "grassyterrain", "Grassy Terrain end-of-turn healing", "residual and end-of-turn effects", "onResidual", "high", "high", "none", "partial; rollout not action schema", "yes", ["no action now"], "low", "Batch 4 rollout parity covers grounded and airborne no-heal fixtures.", "no action now", None),
        ("move", "explosion", "Old-gen Explosion defense/crit/self-KO quirks", "format/generation overrides", "selfdestruct / gen mods", "high", "high", "high", "yes for Gen 9 self-KO; old-gen quirks deferred", "partial", ["format-scoped adapter"], "low", "Gen 1-4 Explosion and crit behavior are future-format notes only.", "deferred NatDex/old-gen backlog", "gen1"),
        ("move", "hyperbeam", "Old-gen recharge quirks", "format/generation overrides", "mustrecharge / gen mods", "low", "medium", "high", "partial; recharge timing fields exist for current gen", "no", ["format-scoped adapter"], "low", "Old-gen recharge behavior belongs in generation adapter, not current Gen 9 schema.", "deferred NatDex/old-gen backlog", "gen1"),
        ("condition", "partiallytrapped", "Old-gen partial trapping lock behavior", "format/generation overrides", "onBeforeMove / residual", "low", "medium", "high", "no; current binding only pressure", "no", ["format-scoped adapter"], "low", "Old-gen partial trapping differs radically and should stay format-scoped.", "deferred NatDex/old-gen backlog", "gen1"),
        ("condition", "focusenergy", "Old-gen crit quirks", "crit chance and crit rules", "onModifyCritRatio / gen mods", "low", "medium", "high", "no; current crit fields Gen 9 scoped", "no", ["format-scoped adapter"], "low", "Old-gen crit stages and Focus Energy quirks are not current target.", "deferred NatDex/old-gen backlog", "gen1"),
    ]
    for index, row in enumerate(residual_format):
        kind, idv, name, category, hook, gen9, nat, old, v7, rollout, needs, priority, reason, next_plan, prefer = row
        add(f"residual-format-{idv}-{index}", name, kind, idv, category, hook, gen9, nat, old,
            v7, rollout, needs, priority, reason, next_plan, prefer_mod=prefer)

    wrappers = [
        ("damage_calc", "sim-core damage calculator wrapper", "Wrapper can omit dynamic callbacks unless explicitly plumbed; keep audit tests tied to Showdown source.", "medium", "v7 batch 9"),
        ("rollout_parity_oracle", "rollout parity oracle fixtures", "Local fixtures should expand only where represented state/provenance is available.", "medium", "rollout parity batch 5"),
        ("state_extractor", "live state extraction provenance", "Many gaps are not action features; they require reliable public/private state extraction.", "high", "state-schema/provenance design"),
    ]
    for ident, name, reason, priority, next_plan in wrappers:
        wrapper_path = f"sim-core/src/{ident}.ts"
        entries.append({
            "id": f"local-wrapper-{ident}",
            "name": name,
            "kind": "local-wrapper",
            "source": {"file": wrapper_path, "line": 1 if wrapper_path in lines_by_file else None, "matched": ident},
            "hook_or_field": "local sim-core wrapper",
            "categories": ["no-leakage/public-information concerns"],
            "gen9_randbats_relevance": "high",
            "natdex_future_format_relevance": "high",
            "old_gen_only_relevance": "medium",
            "current_v7_likely_covers": "not directly",
            "current_rollout_harness_likely_covers": "partial",
            "needs": ["state/provenance feature", "rollout parity fixture"],
            "priority": priority,
            "reason": reason,
            "recommended_next": next_plan,
        })

    by_id = {item["id"]: item for item in entries}
    return list(by_id.values())


def top20(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(entries, key=lambda e: (
        PRIORITY_ORDER.get(e["priority"], 9),
        NEXT_ORDER.get(e["recommended_next"], 9),
        e["id"],
    ))
    out = []
    for item in ranked:
        if item["recommended_next"] == "no action now":
            continue
        out.append({
            "id": item["id"],
            "name": item["name"],
            "priority": item["priority"],
            "recommended_next": item["recommended_next"],
            "needs": item["needs"],
            "reason": item["reason"],
        })
        if len(out) == 20:
            break
    return out


def write_outputs() -> dict[str, Any]:
    scanned, lines_by_file, hook_counter = scan_sources()
    entries = build_entries(scanned, lines_by_file)
    top = top20(entries)
    category_counts: Counter[str] = Counter()
    for item in entries:
        for category in item["categories"]:
            category_counts[category] += 1
    split_counts = {
        "gen9_high_or_medium": sum(1 for e in entries if e["gen9_randbats_relevance"] in {"high", "medium"}),
        "natdex_future_high_or_medium": sum(1 for e in entries if e["natdex_future_format_relevance"] in {"high", "medium"}),
        "old_gen_high_or_medium": sum(1 for e in entries if e["old_gen_only_relevance"] in {"high", "medium"}),
    }
    inventory = {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "task": "source-driven mechanics edge-case inventory from local Pokemon Showdown source",
            "current_action_schema": "legal-action-v7 batch 8",
            "current_action_dim": 552,
            "current_action_fingerprint": "956da3d225ba9a22e05cfe774f6fa21efcbb77fa88267a8f96b1291701bf39d7",
            "batch7_prefix_fingerprint": "c03b2dd345f47dae0bffefc2a0d2b5731ee7d1eb8f2bf4cabc8d415d183149f5",
            "rollout_parity_summary": {"fixtures": 33, "PASS": 29, "FAIL": 0, "GAP": 4},
            "source_files_scanned": len(scanned),
            "hook_occurrences_found": int(sum(hook_counter.values())),
            "inventory_entries": len(entries),
            "scan_scope": [
                "pokemon-showdown/data/{moves,abilities,items,conditions,rulesets,scripts}.ts",
                "pokemon-showdown/config/formats.ts",
                "pokemon-showdown/data/mods/**/{moves,abilities,items,conditions,rulesets,scripts}.ts",
                "pokemon-showdown/sim/dex-moves.ts",
                "sim-core/src/**/*.ts",
            ],
        },
        "hook_occurrence_counts": dict(sorted(hook_counter.items())),
        "category_counts": dict(sorted(category_counts.items())),
        "format_split_counts": split_counts,
        "scanned_files": scanned,
        "entries": entries,
        "top20_recommended_next_actions": top,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# Showdown Mechanics Edge-Case Inventory",
        "",
        "## Scope",
        "",
        "This inventory was generated from the local bundled Pokemon Showdown source and local `sim-core` wrappers. It is an audit artifact only: no schema, live default, checkpoint, dataset, materialization, or training path changed.",
        "",
        f"- Source files scanned: **{len(scanned)}**",
        f"- Hook/field occurrences found: **{int(sum(hook_counter.values()))}**",
        f"- Inventory mechanics entries: **{len(entries)}**",
        "- Current action schema: `legal-action-v7` batch 8, 552D",
        "- Current v7 fingerprint: `956da3d225ba9a22e05cfe774f6fa21efcbb77fa88267a8f96b1291701bf39d7`",
        "- Rollout parity baseline: 33 fixtures, 29 PASS / 0 FAIL / 4 GAP",
        "",
        "## High-Risk Categories",
        "",
    ]
    for category, count in sorted(category_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:8]:
        lines.append(f"- {category}: {count} entries")
    lines += [
        "",
        "The highest-risk Gen 9 gaps cluster around state/provenance and rollout/search, not additional action labels. Sleep/Rest counters, confusion counters, Future Sight landing damage, binding provenance, Magic Bounce reflection, Good as Gold routing, counter-style damage, and item-triggered switch branches all need public-state provenance or branch evaluation before they can be safely resolved.",
        "",
        "## Top 20 Recommended Next Actions",
        "",
    ]
    for index, item in enumerate(top, start=1):
        lines.append(f"{index}. **{item['name']}** (`{item['id']}`) -> {item['recommended_next']} [{item['priority']}]")
        lines.append(f"   Needs: {', '.join(item['needs'])}. Reason: {item['reason']}")
    lines += [
        "",
        "## Gen 9 vs NatDex / Old-Gen Split",
        "",
        f"- Gen 9 high/medium relevance: {split_counts['gen9_high_or_medium']} entries",
        f"- NatDex/future-format high/medium relevance: {split_counts['natdex_future_high_or_medium']} entries",
        f"- Old-gen high/medium relevance: {split_counts['old_gen_high_or_medium']} entries",
        "",
        "Current implementation work should stay Gen 9 Random Battles scoped. Pursuit, Assist, Natural Gift, Hidden Power, old-gen partial trapping, old-gen recharge, old-gen Explosion, and old-gen crit quirks are explicitly deferred to format-scoped adapters or NatDex/old-gen backlog.",
        "",
        "## Inventory By Category",
    ]
    for category in sorted(category_counts):
        lines += ["", f"### {category}"]
        subset = [item for item in entries if category in item["categories"]]
        subset.sort(key=lambda item: (PRIORITY_ORDER.get(item["priority"], 9), item["name"]))
        for item in subset:
            src = item["source"]
            line = f":{src['line']}" if src.get("line") else ""
            lines.append(
                f"- **{item['name']}** (`{item['id']}`) [{item['priority']}] - "
                f"{src['file']}{line}; hook `{item['hook_or_field']}`; "
                f"v7 `{item['current_v7_likely_covers']}`; "
                f"rollout `{item['current_rollout_harness_likely_covers']}`; "
                f"next `{item['recommended_next']}`. {item['reason']}"
            )
    lines += ["", "## Source Scan Summary", "", "Top hook occurrence counts:"]
    for hook, count in hook_counter.most_common(20):
        lines.append(f"- `{hook}`: {count}")
    lines += [
        "",
        "The full per-file hook counts and machine-readable classifications are in `showdown_mechanics_edge_case_inventory.json`.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "json": OUT_JSON.relative_to(ROOT).as_posix(),
        "report": OUT_MD.relative_to(ROOT).as_posix(),
        "source_files_scanned": len(scanned),
        "hook_occurrences_found": int(sum(hook_counter.values())),
        "inventory_entries": len(entries),
    }


if __name__ == "__main__":
    print(json.dumps(write_outputs(), indent=2))
