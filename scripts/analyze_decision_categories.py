import argparse
import csv
import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path

TYPE_CHART = {
    "Normal": {"Rock": 0.5, "Ghost": 0.0, "Steel": 0.5},
    "Fire": {"Fire": 0.5, "Water": 0.5, "Grass": 2.0, "Ice": 2.0, "Bug": 2.0, "Rock": 0.5, "Dragon": 0.5, "Steel": 2.0},
    "Water": {"Fire": 2.0, "Water": 0.5, "Grass": 0.5, "Ground": 2.0, "Rock": 2.0, "Dragon": 0.5},
    "Electric": {"Water": 2.0, "Electric": 0.5, "Grass": 0.5, "Ground": 0.0, "Flying": 2.0, "Dragon": 0.5},
    "Grass": {"Fire": 0.5, "Water": 2.0, "Grass": 0.5, "Poison": 0.5, "Ground": 2.0, "Flying": 0.5, "Bug": 0.5, "Rock": 2.0, "Dragon": 0.5, "Steel": 0.5},
    "Ice": {"Fire": 0.5, "Water": 0.5, "Grass": 2.0, "Ice": 0.5, "Ground": 2.0, "Flying": 2.0, "Dragon": 2.0, "Steel": 0.5},
    "Fighting": {"Normal": 2.0, "Ice": 2.0, "Poison": 0.5, "Flying": 0.5, "Psychic": 0.5, "Bug": 0.5, "Rock": 2.0, "Ghost": 0.0, "Dark": 2.0, "Steel": 2.0, "Fairy": 0.5},
    "Poison": {"Grass": 2.0, "Poison": 0.5, "Ground": 0.5, "Rock": 0.5, "Ghost": 0.5, "Steel": 0.0, "Fairy": 2.0},
    "Ground": {"Fire": 2.0, "Electric": 2.0, "Grass": 0.5, "Poison": 2.0, "Flying": 0.0, "Bug": 0.5, "Rock": 2.0, "Steel": 2.0},
    "Flying": {"Electric": 0.5, "Grass": 2.0, "Fighting": 2.0, "Bug": 2.0, "Rock": 0.5, "Steel": 0.5},
    "Psychic": {"Fighting": 2.0, "Poison": 2.0, "Psychic": 0.5, "Dark": 0.0, "Steel": 0.5},
    "Bug": {"Fire": 0.5, "Grass": 2.0, "Fighting": 0.5, "Poison": 0.5, "Flying": 0.5, "Psychic": 2.0, "Ghost": 0.5, "Dark": 2.0, "Steel": 0.5, "Fairy": 0.5},
    "Rock": {"Fire": 2.0, "Ice": 2.0, "Fighting": 0.5, "Ground": 0.5, "Flying": 2.0, "Bug": 2.0, "Steel": 0.5},
    "Ghost": {"Normal": 0.0, "Psychic": 2.0, "Ghost": 2.0, "Dark": 0.5},
    "Dragon": {"Dragon": 2.0, "Steel": 0.5, "Fairy": 0.0},
    "Dark": {"Fighting": 0.5, "Psychic": 2.0, "Ghost": 2.0, "Dark": 0.5, "Fairy": 0.5},
    "Steel": {"Fire": 0.5, "Water": 0.5, "Electric": 0.5, "Ice": 2.0, "Rock": 2.0, "Steel": 0.5, "Fairy": 2.0},
    "Fairy": {"Fire": 0.5, "Fighting": 2.0, "Poison": 0.5, "Dragon": 2.0, "Dark": 2.0, "Steel": 0.5},
}

RECOVERY_MOVES = {"recover", "roost", "soft-boiled", "softboiled", "slack off", "slackoff", "synthesis", "moonlight", "morning sun", "morningsun", "milk drink", "milkdrink", "wish", "rest"}
SETUP_HINTS = ["dance", "plot", "calm mind", "bulk up", "iron defense", "cosmic power", "coil", "shell smash", "swords dance", "nasty plot", "quiver dance", "dragon dance"]
HAZARD_MOVES = {"stealth rock", "spikes", "toxic spikes", "sticky web"}
STATUS_MOVES = {"toxic", "will-o-wisp", "willowisp", "thunder wave", "thunderwave", "spore", "stun spore", "stunspore", "sleep powder", "sleeppowder", "glare", "nuzzle", "yawn"}

def active_pokemon(view, side):
    for p in (view.get(side) or []):
        if isinstance(p, dict) and p.get("active"):
            return p
    return {}

def hp_is_zero(p):
    hp = p.get("hp_text") or p.get("hp")
    return hp == 0 or hp == "0" or str(hp).startswith("0/")

def legal_actions(r):
    actions = ((r.get("request") or {}).get("legal_actions") or {}).get("actions") or []
    return [a for a in actions if isinstance(a, dict)]

def chosen_action(r):
    idx = r.get("action_index")
    for a in legal_actions(r):
        if a.get("index") == idx:
            return a
    choice = r.get("choice") or ""
    if choice.startswith("switch"):
        return {"kind": "switch", "label": choice}
    if choice == "default":
        return {"kind": "default", "label": "default"}
    return {"kind": "unknown", "label": choice or f"action_index={idx}"}

def move_info_for_action(r, action):
    slot = action.get("slot")
    active = (r.get("request") or {}).get("active") or {}
    moves = active.get("moves") if isinstance(active, dict) else []
    if slot is not None:
        for m in moves or []:
            if isinstance(m, dict) and m.get("slot") == slot:
                return m
        if isinstance(slot, int) and 1 <= slot <= len(moves or []):
            m = moves[slot - 1]
            if isinstance(m, dict):
                return m
    return {}

def type_multiplier(move_type, defender_types):
    if not move_type or not defender_types:
        return None
    mult = 1.0
    for t in defender_types:
        mult *= TYPE_CHART.get(move_type, {}).get(t, 1.0)
    return mult

def effectiveness_label(mult):
    if mult is None:
        return "unknown_effectiveness"
    if mult == 0:
        return "no_effect_attack"
    if mult < 1:
        return "resisted_attack"
    if mult == 1:
        return "neutral_attack"
    return "super_effective_attack"

def status_category(move_name):
    m = str(move_name or "").lower()
    if m in RECOVERY_MOVES:
        return "recovery_status_move"
    if m in HAZARD_MOVES:
        return "hazard_status_move"
    if m in STATUS_MOVES:
        return "status_condition_move"
    if any(h in m for h in SETUP_HINTS):
        return "setup_status_move"
    return "other_status_move"

def switch_category(r):
    req = r.get("request") or {}
    view = r.get("view") or {}
    active = active_pokemon(view, "self_team")
    labels = [a.get("label") or "" for a in legal_actions(r)]
    has_move = any(x.startswith("move:") or x.startswith("move_tera:") for x in labels)
    has_switch = any(x.startswith("switch:") for x in labels)

    if req.get("force_switch") or active.get("fainted") or hp_is_zero(active):
        return "forced_switch"
    if has_switch and not has_move:
        return "no_move_options_switch"
    return "voluntary_switch"

def categorize(r):
    view = r.get("view") or {}
    action = chosen_action(r)
    kind = action.get("kind") or "unknown"
    label = action.get("label") or ""

    self_active = active_pokemon(view, "self_team")
    opp_active = active_pokemon(view, "opponent_team")
    legal = legal_actions(r)

    row = {
        "battle_index": r.get("battle_index"),
        "step_index": r.get("step_index"),
        "turn": view.get("turn"),
        "return": r.get("return"),
        "self_species": self_active.get("species"),
        "self_hp": self_active.get("hp_text") or self_active.get("hp"),
        "self_hp_ratio": self_active.get("hp_ratio"),
        "self_status": self_active.get("status"),
        "opp_species": opp_active.get("species"),
        "opp_hp": opp_active.get("hp_text") or opp_active.get("hp"),
        "opp_hp_ratio": opp_active.get("hp_ratio"),
        "opp_status": opp_active.get("status"),
        "opp_types": "/".join(opp_active.get("types") or []),
        "choice": r.get("choice"),
        "action_index": r.get("action_index"),
        "chosen_label": label,
        "action_kind": kind,
        "legal_move_count": sum(1 for a in legal if (a.get("label") or "").startswith(("move:", "move_tera:"))),
        "legal_switch_count": sum(1 for a in legal if (a.get("label") or "").startswith("switch:")),
        "category": "unknown",
        "effectiveness_multiplier": "",
        "move_name": action.get("move") or "",
        "move_type": "",
        "move_category": "",
        "base_power": "",
        "tera_used": str(kind == "move_tera" or "terastallize" in (r.get("choice") or "").lower()),
        "switch_type": "",
    }

    if kind == "switch" or label.startswith("switch:"):
        cat = switch_category(r)
        row["category"] = cat
        row["switch_type"] = cat
        return row

    if kind == "default" or label == "default" or r.get("choice") == "default":
        row["category"] = "default_or_locked_move"
        return row

    if kind in ("move", "move_tera") or label.startswith(("move:", "move_tera:")):
        m = move_info_for_action(r, action)
        move_name = m.get("move") or action.get("move") or label.split(":", 1)[-1]
        move_type = m.get("type")
        move_cat = m.get("category")
        base_power = m.get("base_power")

        row["move_name"] = move_name
        row["move_type"] = move_type or ""
        row["move_category"] = move_cat or ""
        row["base_power"] = base_power if base_power is not None else ""

        is_damaging = move_cat in ("Physical", "Special") or (isinstance(base_power, (int, float)) and base_power > 0)
        if not is_damaging:
            row["category"] = status_category(move_name)
            return row

        mult = type_multiplier(move_type, opp_active.get("types") or [])
        row["effectiveness_multiplier"] = mult if mult is not None else ""
        row["category"] = effectiveness_label(mult)
        return row

    row["category"] = "unknown_action"
    return row

path = Path(r"C:\Users\cloud\Downloads\neural\final\data\raw\gen9randombattle_bc.jsonl.gz")
out = Path(r"C:\Users\cloud\Downloads\neural\final\artifacts\analysis\decision_categories.csv")
out.parent.mkdir(parents=True, exist_ok=True)

rows = []
with gzip.open(path, "rt", encoding="utf-8") as f:
    for line in f:
        rows.append(categorize(json.loads(line)))

with out.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

total = len(rows)
by_category = Counter(r["category"] for r in rows)
attack_rows = [r for r in rows if r["category"] in {"super_effective_attack", "neutral_attack", "resisted_attack", "no_effect_attack", "unknown_effectiveness"}]
first_turns = [r for r in rows if r.get("step_index") == 0]
first_turn_tera = sum(1 for r in first_turns if r.get("tera_used") == "True")

print(f"Read decisions: {total}")
print(f"Wrote CSV: {out}")
print()
print("Decision categories:")
for cat, count in by_category.most_common():
    print(f"  {count:5}  {count / total:7.2%}  {cat}")

print()
print("Attack-only effectiveness:")
for cat, count in Counter(r["category"] for r in attack_rows).most_common():
    print(f"  {count:5}  {count / len(attack_rows):7.2%}  {cat}")

print()
if first_turns:
    print(f"First-turn tera: {first_turn_tera}/{len(first_turns)} ({first_turn_tera / len(first_turns):.2%})")

print()
print("Examples by category:")
grouped = defaultdict(list)
for r in rows:
    if len(grouped[r["category"]]) < 5:
        grouped[r["category"]].append(r)

for cat in sorted(grouped):
    print()
    print("=" * 90)
    print(cat)
    print("=" * 90)
    for r in grouped[cat]:
        print(
            f"battle={r['battle_index']:>3} step={r['step_index']:>3} turn={r['turn']:>3} "
            f"{r['self_species']} HP={r['self_hp']} vs {r['opp_species']} HP={r['opp_hp']} "
            f"| {r['chosen_label']} | mult={r['effectiveness_multiplier']} return={r['return']}"
        )
