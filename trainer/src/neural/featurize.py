from typing import Dict, Iterable, List, Optional

import numpy as np

from .schema import BattleView, ChoiceRequestView, FeatureTensors, PokemonView

TYPES = [
    "Normal",
    "Fire",
    "Water",
    "Electric",
    "Grass",
    "Ice",
    "Fighting",
    "Poison",
    "Ground",
    "Flying",
    "Psychic",
    "Bug",
    "Rock",
    "Ghost",
    "Dragon",
    "Dark",
    "Steel",
    "Fairy",
]
STATUSES = ["none", "brn", "frz", "par", "psn", "tox", "slp"]
WEATHERS = ["none", "raindance", "sunnyday", "sandstorm", "snow"]
TERRAINS = ["none", "electricterrain", "grassyterrain", "mistyterrain", "psychicterrain"]
PSEUDO_WEATHER = ["trickroom", "gravity", "magicroom", "wonderroom"]
SIDE_CONDITIONS = [
    "stealthrock",
    "spikes",
    "toxicspikes",
    "stickyweb",
    "reflect",
    "lightscreen",
    "auroraveil",
    "tailwind",
]
MOVE_CATEGORIES = ["Physical", "Special", "Status"]
MOVE_TARGETS = ["normal", "allAdjacentFoes", "adjacentFoe", "allySide", "self", "adjacentAlly", "adjacentAllyOrSelf"]

GLOBAL_DIM = 33
POKEMON_DIM = 82
REQUEST_DIM = 146
MOVE_SLOT_DIM = 32

TYPE_INDEX = {name: index for index, name in enumerate(TYPES)}
STATUS_INDEX = {name: index for index, name in enumerate(STATUSES)}
WEATHER_INDEX = {name: index for index, name in enumerate(WEATHERS)}
TERRAIN_INDEX = {name: index for index, name in enumerate(TERRAINS)}
PSEUDO_WEATHER_INDEX = {name: index for index, name in enumerate(PSEUDO_WEATHER)}
SIDE_CONDITION_INDEX = {name: index for index, name in enumerate(SIDE_CONDITIONS)}
MOVE_CATEGORY_INDEX = {name: index for index, name in enumerate(MOVE_CATEGORIES)}
MOVE_TARGET_INDEX = {name: index for index, name in enumerate(MOVE_TARGETS)}

ZERO_POKEMON_VECTOR = np.zeros(POKEMON_DIM, dtype=np.float32)
ZERO_MOVE_SLOT_VECTOR = np.zeros(MOVE_SLOT_DIM, dtype=np.float32)
ZERO_FLAGS_VECTOR = np.zeros(5, dtype=np.float32)


def _one_hot(value: Optional[str], index_map: Dict[str, int], size: int) -> np.ndarray:
    vector = np.zeros(size, dtype=np.float32)
    index = index_map.get(value or "")
    if index is not None:
        vector[index] = 1.0
    return vector


def _side_condition_features(side_conditions: Dict[str, int]) -> np.ndarray:
    vector = np.zeros(len(SIDE_CONDITIONS), dtype=np.float32)
    for name, value in side_conditions.items():
        index = SIDE_CONDITION_INDEX.get(name)
        if index is not None:
            vector[index] = float(value)
    return vector


def _type_slot_features(types: List[str]) -> np.ndarray:
    vector = np.zeros(len(TYPES) * 2, dtype=np.float32)
    if len(types) > 0:
        index = TYPE_INDEX.get(types[0])
        if index is not None:
            vector[index] = 1.0
    if len(types) > 1:
        index = TYPE_INDEX.get(types[1])
        if index is not None:
            vector[len(TYPES) + index] = 1.0
    return vector


def _pokemon_vector(pokemon: Optional[PokemonView]) -> np.ndarray:
    if not pokemon:
        return ZERO_POKEMON_VECTOR

    stats = pokemon.get("stats", {})
    boosts = pokemon.get("boosts", {})
    status = pokemon.get("status") or "none"
    tera_type = pokemon.get("tera_type")
    vector = np.zeros(POKEMON_DIM, dtype=np.float32)
    vector[0] = 1.0
    vector[1] = float(bool(pokemon.get("active")))
    vector[2] = float(bool(pokemon.get("fainted")))
    vector[3] = float(pokemon.get("hp_ratio") or 0.0)
    vector[4] = float((pokemon.get("level") or 100) / 100.0)
    status_index = STATUS_INDEX.get(status)
    if status_index is not None:
        vector[5 + status_index] = 1.0
    vector[12:48] = _type_slot_features(pokemon.get("types", []))
    vector[48] = float(bool(pokemon.get("terastallized")))
    tera_index = TYPE_INDEX.get(tera_type or "")
    if tera_index is not None:
        vector[49 + tera_index] = 1.0
    vector[67] = float(bool(pokemon.get("item")))
    vector[68] = float(bool(pokemon.get("ability")))
    vector[69] = float(len(pokemon.get("revealed_moves", [])) / 4.0)
    vector[70] = float(stats.get("atk", 0) / 400.0)
    vector[71] = float(stats.get("def", 0) / 400.0)
    vector[72] = float(stats.get("spa", 0) / 400.0)
    vector[73] = float(stats.get("spd", 0) / 400.0)
    vector[74] = float(stats.get("spe", 0) / 400.0)
    vector[75] = float(boosts.get("atk", 0) / 6.0)
    vector[76] = float(boosts.get("def", 0) / 6.0)
    vector[77] = float(boosts.get("spa", 0) / 6.0)
    vector[78] = float(boosts.get("spd", 0) / 6.0)
    vector[79] = float(boosts.get("spe", 0) / 6.0)
    vector[80] = float(boosts.get("accuracy", 0) / 6.0)
    vector[81] = float(boosts.get("evasion", 0) / 6.0)
    assert vector.shape == (POKEMON_DIM,)
    return vector


def _move_slot_vector(move: Optional[Dict[str, object]]) -> np.ndarray:
    if not move:
        return ZERO_MOVE_SLOT_VECTOR
    pp = float(move.get("pp", 0))
    maxpp = float(move.get("maxpp", 0)) or 1.0
    vector = np.zeros(MOVE_SLOT_DIM, dtype=np.float32)
    vector[0] = pp / maxpp
    vector[1] = float(bool(move.get("disabled")))
    vector[2] = float(move.get("base_power", 0) / 200.0)
    vector[3] = float((move.get("accuracy") or 100) / 100.0)
    category_index = MOVE_CATEGORY_INDEX.get(str(move.get("category") or ""))
    if category_index is not None:
        vector[4 + category_index] = 1.0
    type_index = TYPE_INDEX.get(str(move.get("type") or ""))
    if type_index is not None:
        vector[7 + type_index] = 1.0
    target_index = MOVE_TARGET_INDEX.get(str(move.get("target") or ""))
    if target_index is not None:
        vector[25 + target_index] = 1.0
    return vector


def featurize_battle(view: BattleView, request: Optional[ChoiceRequestView]) -> FeatureTensors:
    weather = view["field"].get("weather") or "none"
    terrain = view["field"].get("terrain") or "none"
    pseudo = view["field"].get("pseudo_weather", [])
    self_side = view["field"]["side_conditions"].get("self", {})
    opp_side = view["field"]["side_conditions"].get("opponent", {})
    self_active = view["self_team"][view["active"]["self"]] if view["active"]["self"] is not None else None
    opp_active = view["opponent_team"][view["active"]["opponent"]] if view["active"]["opponent"] is not None else None

    global_vector = np.zeros(GLOBAL_DIM, dtype=np.float32)
    global_vector[0] = float(view.get("turn", 0) / 50.0)
    global_vector[1] = float(self_active.get("hp_ratio", 0.0) if self_active else 0.0)
    global_vector[2] = float(opp_active.get("hp_ratio", 0.0) if opp_active else 0.0)
    weather_index = WEATHER_INDEX.get(weather)
    if weather_index is not None:
        global_vector[3 + weather_index] = 1.0
    terrain_index = TERRAIN_INDEX.get(terrain)
    if terrain_index is not None:
        global_vector[8 + terrain_index] = 1.0
    for condition in pseudo:
        pseudo_index = PSEUDO_WEATHER_INDEX.get(condition)
        if pseudo_index is not None:
            global_vector[13 + pseudo_index] = 1.0
    global_vector[17:25] = _side_condition_features(self_side)
    global_vector[25:33] = _side_condition_features(opp_side)
    assert global_vector.shape == (GLOBAL_DIM,)

    own_team = np.stack(
        [_pokemon_vector(view["self_team"][index] if index < len(view["self_team"]) else None) for index in range(6)],
        axis=0,
    )
    opponent_team = np.stack(
        [_pokemon_vector(view["opponent_team"][index] if index < len(view["opponent_team"]) else None) for index in range(6)],
        axis=0,
    )

    legal_mask = np.zeros(13, dtype=np.float32)
    request_vector = np.zeros(REQUEST_DIM, dtype=np.float32)
    if request:
        legal_mask = np.asarray([1.0 if value else 0.0 for value in request["legal_actions"]["mask"]], dtype=np.float32)
        request_vector[0:13] = legal_mask
        request_vector[13] = float(request["wait"])
        request_vector[14] = float(request["team_preview"])
        request_vector[15] = float(request["force_switch"])
        request_vector[16] = float(request["trapped"])
        request_vector[17] = float(request["active"]["can_terastallize"]) if request["active"] else 0.0
        active_moves = request["active"]["moves"] if request["active"] else []
        for slot in range(4):
            start = 18 + (slot * MOVE_SLOT_DIM)
            request_vector[start : start + MOVE_SLOT_DIM] = _move_slot_vector(
                active_moves[slot] if slot < len(active_moves) else None
            )
    else:
        request_vector[13:18] = ZERO_FLAGS_VECTOR
    assert request_vector.shape == (REQUEST_DIM,)

    flat = np.concatenate([global_vector, own_team.reshape(-1), opponent_team.reshape(-1), request_vector]).astype(
        np.float32
    )
    return FeatureTensors(
        global_vector=global_vector,
        own_team=own_team,
        opponent_team=opponent_team,
        request_vector=request_vector,
        legal_mask=legal_mask,
        flat=flat,
    )
