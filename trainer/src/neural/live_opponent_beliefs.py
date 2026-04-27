import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_sets_candidates() -> List[Path]:
    root = _repo_root()
    return [
        root / "pokemon-showdown" / "data" / "random-battles" / "gen9" / "sets.json",
        root / "data" / "random-battles" / "gen9" / "sets.json",
        Path("pokemon-showdown/data/random-battles/gen9/sets.json"),
    ]


def _string_set(value: Any) -> List[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value if isinstance(item, (str, int, float))]
    return []


def _species_from_details(details: Optional[str]) -> Optional[str]:
    if not details:
        return None
    return str(details).split(",", 1)[0].strip() or None


def _species_key(species: str) -> str:
    return re.sub(r"[^a-z0-9]", "", species.lower())


def _normalize_candidate(species: str, candidate: Dict[str, Any]) -> Dict[str, Any]:
    abilities = _string_set(candidate.get("abilities") or candidate.get("ability"))
    items = _string_set(candidate.get("items") or candidate.get("item"))

    moves_value = candidate.get("moves") or candidate.get("movepool")
    moves: List[str] = []
    if isinstance(moves_value, list):
        for entry in moves_value:
            if isinstance(entry, str):
                moves.append(entry)
            elif isinstance(entry, list):
                moves.extend([str(item) for item in entry if isinstance(item, (str, int, float))])

    tera_types = _string_set(
        candidate.get("teraTypes")
        or candidate.get("tera_types")
        or candidate.get("teraType")
        or candidate.get("tera_type")
    )

    weight = candidate.get("weight")
    if not isinstance(weight, (int, float)) or weight <= 0:
        weight = 1.0

    return {
        "species": species,
        "role": candidate.get("role"),
        "abilities": sorted(set(str(v) for v in abilities)),
        "items": sorted(set(str(v) for v in items)),
        "moves": sorted(set(str(v) for v in moves)),
        "tera_types": sorted(set(str(v) for v in tera_types)),
        "weight": float(weight),
    }


def _extract_candidates_for_species(species: str, payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [_normalize_candidate(species, c) for c in payload if isinstance(c, dict)]

    if isinstance(payload, dict):
        if isinstance(payload.get("sets"), list):
            return [_normalize_candidate(species, c) for c in payload["sets"] if isinstance(c, dict)]
        # Some generated formats use role-name keys.
        result: List[Dict[str, Any]] = []
        for value in payload.values():
            if isinstance(value, dict):
                result.append(_normalize_candidate(species, value))
            elif isinstance(value, list):
                result.extend(_normalize_candidate(species, c) for c in value if isinstance(c, dict))
        if result:
            return result

    return []


def _load_sets_payload(path: Path) -> Dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        return raw
    return {}


@lru_cache(maxsize=8)
def load_randbats_index(sets_path: Optional[str] = None) -> Tuple[Dict[str, List[Dict[str, Any]]], str, List[str]]:
    warnings: List[str] = []
    selected_path: Optional[Path] = None

    if sets_path:
        candidate = Path(sets_path)
        if candidate.exists():
            selected_path = candidate
        else:
            warnings.append(f"Configured sets path does not exist: {sets_path}")

    if selected_path is None:
        for candidate in _default_sets_candidates():
            if candidate.exists():
                selected_path = candidate
                break

    if selected_path is None:
        warnings.append("No Gen9 randbats sets.json was found; beliefs limited to public reveal summaries.")
        return {}, "missing", warnings

    payload = _load_sets_payload(selected_path)
    index: Dict[str, List[Dict[str, Any]]] = {}
    for species, species_payload in payload.items():
        species_name = str(species)
        candidates = _extract_candidates_for_species(species_name, species_payload)
        if candidates:
            index[_species_key(species_name)] = candidates

    if not index:
        warnings.append(f"Loaded randbats source but found no candidate sets: {selected_path}")

    return index, str(selected_path), warnings


def _collect_revealed_from_trajectory(trajectory: Dict[str, Any], opponent_side: str) -> Dict[str, Dict[str, Any]]:
    revealed: Dict[str, Dict[str, Any]] = {}

    turns = trajectory.get("turns") if isinstance(trajectory.get("turns"), list) else []
    for turn in turns:
        if not isinstance(turn, dict):
            continue
        events = turn.get("events") if isinstance(turn.get("events"), list) else []
        for event in events:
            if not isinstance(event, dict):
                continue
            side = event.get("side")
            if side != opponent_side:
                continue

            event_type = str(event.get("type") or "")
            actor = str(event.get("actor") or "")
            target = str(event.get("target") or "")
            details = event.get("details")

            species = None
            if event_type == "switch":
                species = _species_from_details(details)
            if not species and ": " in actor:
                species = actor.split(": ", 1)[1].split(",", 1)[0].strip()
            if not species and ": " in target:
                species = target.split(": ", 1)[1].split(",", 1)[0].strip()
            if not species:
                continue

            slot = revealed.setdefault(
                species,
                {
                    "species": species,
                    "moves": set(),
                    "ability": None,
                    "item": None,
                    "tera_type": None,
                    "status": set(),
                    "fainted": False,
                },
            )

            if event_type == "move" and event.get("move"):
                slot["moves"].add(str(event.get("move")))
            elif event_type == "status" and event.get("status"):
                slot["status"].add(str(event.get("status")))
            elif event_type == "tera" and event.get("tera_type"):
                slot["tera_type"] = str(event.get("tera_type"))
            elif event_type == "faint":
                slot["fainted"] = True

    return revealed


def _collect_revealed_from_protocol_lines(protocol_log: Iterable[str], opponent_side: str) -> Dict[str, Dict[str, Any]]:
    revealed: Dict[str, Dict[str, Any]] = {}

    for line in protocol_log:
        if not isinstance(line, str) or not line.startswith("|-"):
            continue
        parts = line.split("|")
        if len(parts) < 4:
            continue

        tag = parts[1]
        if tag not in ("-ability", "-item", "-enditem", "-terastallize"):
            continue

        target = parts[2]
        if not target.startswith(opponent_side):
            continue
        if ": " not in target:
            continue
        species = target.split(": ", 1)[1].split(",", 1)[0].strip()
        if not species:
            continue

        slot = revealed.setdefault(species, {"species": species})
        if tag == "-ability" and len(parts) >= 4:
            slot["ability"] = parts[3]
        elif tag in ("-item", "-enditem") and len(parts) >= 4:
            slot["item"] = parts[3]
        elif tag == "-terastallize" and len(parts) >= 4:
            slot["tera_type"] = parts[3]

    return revealed


def _distribution_from_candidates(candidates: List[Dict[str, Any]], field: str) -> List[Dict[str, Any]]:
    weights: Dict[str, float] = {}
    total = 0.0
    for candidate in candidates:
        weight = float(candidate.get("weight", 1.0))
        values = candidate.get(field)
        if isinstance(values, list):
            values_list = [str(v) for v in values if str(v)]
        elif values:
            values_list = [str(values)]
        else:
            values_list = []
        if not values_list:
            continue

        share = weight / float(len(values_list))
        for value in values_list:
            weights[value] = weights.get(value, 0.0) + share
            total += share

    if total <= 0:
        return []

    ranked = sorted(weights.items(), key=lambda item: item[1], reverse=True)
    return [{"value": key, "prob": value / total} for key, value in ranked[:5]]


def _filter_candidates_for_reveal(
    all_candidates: List[Dict[str, Any]],
    reveal: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], bool]:
    filtered = list(all_candidates)

    revealed_moves = {str(m).lower() for m in reveal.get("moves", set())}
    if revealed_moves:
        move_filtered = []
        for candidate in filtered:
            candidate_moves = {str(m).lower() for m in candidate.get("moves", [])}
            if revealed_moves.issubset(candidate_moves):
                move_filtered.append(candidate)
        if move_filtered:
            filtered = move_filtered

    ability = reveal.get("ability")
    if ability:
        ability_lower = str(ability).lower()
        ability_filtered = [
            candidate
            for candidate in filtered
            if not candidate.get("abilities")
            or ability_lower in {str(v).lower() for v in candidate.get("abilities", [])}
        ]
        if ability_filtered:
            filtered = ability_filtered

    item = reveal.get("item")
    if item:
        item_lower = str(item).lower()
        item_filtered = [
            candidate
            for candidate in filtered
            if not candidate.get("items")
            or item_lower in {str(v).lower() for v in candidate.get("items", [])}
        ]
        if item_filtered:
            filtered = item_filtered

    tera_type = reveal.get("tera_type")
    if tera_type:
        tera_lower = str(tera_type).lower()
        tera_filtered = [
            candidate
            for candidate in filtered
            if not candidate.get("tera_types")
            or tera_lower in {str(v).lower() for v in candidate.get("tera_types", [])}
        ]
        if tera_filtered:
            filtered = tera_filtered

    filter_relaxed = len(filtered) == len(all_candidates)
    return filtered, filter_relaxed


def build_opponent_beliefs(
    *,
    protocol_log: List[str],
    trajectory: Dict[str, Any],
    player_side: Optional[str],
    sets_path: Optional[str] = None,
) -> Dict[str, Any]:
    if player_side not in ("p1", "p2"):
        return {
            "source": "unknown-player-side",
            "warnings": ["Could not infer player_side from request payload."],
            "opponents": [],
            "unknowns": ["opponent_side_unknown"],
        }

    opponent_side = "p2" if player_side == "p1" else "p1"
    index, source_path, warnings = load_randbats_index(sets_path=sets_path)

    revealed = _collect_revealed_from_trajectory(trajectory, opponent_side)
    line_revealed = _collect_revealed_from_protocol_lines(protocol_log, opponent_side)

    for species, extra in line_revealed.items():
        slot = revealed.setdefault(
            species,
            {
                "species": species,
                "moves": set(),
                "ability": None,
                "item": None,
                "tera_type": None,
                "status": set(),
                "fainted": False,
            },
        )
        for key in ("ability", "item", "tera_type"):
            if extra.get(key):
                slot[key] = extra[key]

    opponent_summaries: List[Dict[str, Any]] = []
    unknowns: List[str] = []

    for species, reveal in sorted(revealed.items()):
        species_index_key = _species_key(species)
        all_candidates = index.get(species_index_key, [])

        if not all_candidates:
            unknowns.append(f"no_randbats_candidates:{species}")
            opponent_summaries.append(
                {
                    "species": species,
                    "revealed": {
                        "moves": sorted(list(reveal.get("moves", set()))),
                        "ability": reveal.get("ability"),
                        "item": reveal.get("item"),
                        "tera_type": reveal.get("tera_type"),
                        "status": sorted(list(reveal.get("status", set()))),
                        "fainted": bool(reveal.get("fainted", False)),
                    },
                    "candidate_count": 0,
                    "top_candidates": [],
                    "inferred": {"abilities": [], "items": [], "tera_types": []},
                }
            )
            continue

        filtered, filter_relaxed = _filter_candidates_for_reveal(all_candidates, reveal)
        total_weight = sum(float(c.get("weight", 1.0)) for c in filtered) or 1.0

        ranked = sorted(filtered, key=lambda item: float(item.get("weight", 1.0)), reverse=True)
        top_candidates = []
        for candidate in ranked[:5]:
            weight = float(candidate.get("weight", 1.0))
            top_candidates.append(
                {
                    "role": candidate.get("role"),
                    "prob": weight / total_weight,
                    "abilities": candidate.get("abilities", []),
                    "items": candidate.get("items", []),
                    "moves": candidate.get("moves", [])[:6],
                    "tera_types": candidate.get("tera_types", []),
                }
            )

        opponent_summaries.append(
            {
                "species": species,
                "revealed": {
                    "moves": sorted(list(reveal.get("moves", set()))),
                    "ability": reveal.get("ability"),
                    "item": reveal.get("item"),
                    "tera_type": reveal.get("tera_type"),
                    "status": sorted(list(reveal.get("status", set()))),
                    "fainted": bool(reveal.get("fainted", False)),
                },
                "candidate_count": len(filtered),
                "filter_relaxed": filter_relaxed,
                "top_candidates": top_candidates,
                "inferred": {
                    "abilities": _distribution_from_candidates(filtered, "abilities"),
                    "items": _distribution_from_candidates(filtered, "items"),
                    "tera_types": _distribution_from_candidates(filtered, "tera_types"),
                },
            }
        )

    if not opponent_summaries:
        unknowns.append("no_public_opponent_reveals")

    return {
        "source": source_path,
        "warnings": warnings,
        "opponents": opponent_summaries,
        "unknowns": unknowns,
    }
