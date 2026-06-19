"""Diagnostic-only move/action counterfactuals for Slice 5.

Two halves:

* State side (`live-private-belief-v7`): proves that move identity, revealed PP,
  disabled/lock/recharge constraints, and Taunt are *represented* in the state
  vector. Built through the real live serving path.
* Action side (`legal-action-v4`): proves that move side-effects — most notably
  Draco Meteor's self Special-Attack drop and Curse vs Bulk Up's stat deltas — are
  represented as explicit action fields.

These are representation tests (does the vector change?), not tactical rules. No
training, no checkpoints, no live defaults touched.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from .action_features import (
    ACTION_FEATURE_DIM_V4,
    ACTION_FEATURE_NAMES_V4,
    ACTION_FEATURE_VERSION_V4,
    build_action_feature_vector_v4,
)
from .live_private_features import (
    FEATURE_NAMES_V7,
    FEATURE_VERSION_V7,
    build_features_from_live_payload,
)


BASE_LOG = [
    "|start",
    "|switch|p1a: Charizard|Charizard, L80, M|100/100",
    "|switch|p2a: Blastoise|Blastoise, L80, M|100/100",
]

_FLAME = {"move": "Flamethrower", "id": "flamethrower", "pp": 24, "maxpp": 24, "target": "normal"}
_AIR = {"move": "Air Slash", "id": "airslash", "pp": 24, "maxpp": 24, "target": "normal"}
_ROOST = {"move": "Roost", "id": "roost", "pp": 16, "maxpp": 16, "target": "self"}
_DRAGON = {"move": "Dragon Pulse", "id": "dragonpulse", "pp": 16, "maxpp": 16, "target": "normal"}
_FOUR = [_FLAME, _AIR, _ROOST, _DRAGON]


def _request(moves: List[Dict[str, Any]], **extra: Any) -> Dict[str, Any]:
    side = {
        "id": "p1",
        "pokemon": [
            {
                "ident": "p1: Charizard",
                "details": "Charizard, L80, M",
                "condition": "200/200",
                "active": True,
                "moves": [m["id"] for m in moves],
                "baseAbility": "blaze",
                "ability": "blaze",
            }
        ],
    }
    payload: Dict[str, Any] = {"side": side, "active": [{"moves": moves}]}
    payload.update(extra)
    return payload


def _features(
    *,
    log: Optional[List[str]] = None,
    request: Optional[Dict[str, Any]] = None,
    player: str = "p1",
) -> np.ndarray:
    features, *_ = build_features_from_live_payload(
        log=[*(log or BASE_LOG), "|turn|3"],
        room_id="moves-actions-counterfactual",
        url="cf://moves-actions",
        player=player,
        request_payload=request,
        legal_actions=[],
        feature_version=FEATURE_VERSION_V7,
    )
    return features


def _changed(left: np.ndarray, right: np.ndarray) -> List[str]:
    indices = np.where(~np.isclose(left, right, atol=1e-7))[0]
    return [FEATURE_NAMES_V7[index] for index in indices]


def _action(name: str, kind: str = "move", **extra: Any) -> Dict[str, Any]:
    action = {"kind": kind, "label": f"{kind}: {name}", "move": name}
    action.update(extra)
    return action


def _avec(action: Dict[str, Any], private_state: Optional[Dict[str, Any]] = None) -> np.ndarray:
    return build_action_feature_vector_v4(action, private_state or {"team": []}, {})


def _achanged(left: np.ndarray, right: np.ndarray) -> List[str]:
    indices = np.where(~np.isclose(left, right, atol=1e-7))[0]
    return [ACTION_FEATURE_NAMES_V4[index] for index in indices]


def evaluate_state_counterfactuals() -> Dict[str, Any]:
    slot_a = _features(request=_request(_FOUR))
    slot_b = _features(request=_request([_AIR, _FLAME, _ROOST, _DRAGON]))

    opp_revealed = _features(
        log=[*BASE_LOG, "|move|p2a: Blastoise|Surf|p1a: Charizard"], request=_request(_FOUR)
    )
    opp_unknown = _features(request=_request(_FOUR))

    pp_known = _features(request=_request([_FLAME, _AIR]))
    pp_unknown = _features(request=_request([{"move": "Flamethrower", "id": "flamethrower"}, _AIR]))

    disabled = _features(request=_request([dict(_FLAME, disabled=True), _AIR]))
    available = _features(request=_request([_FLAME, _AIR]))

    encore = _features(
        log=[*BASE_LOG, "|-start|p1a: Charizard|move: Encore"],
        request=_request([dict(_FLAME, disabled=True), _AIR]),
    )
    no_encore = _features(request=_request(_FOUR))

    choice_lock = _features(request=_request([_FLAME, dict(_AIR, disabled=True), dict(_ROOST, disabled=True), dict(_DRAGON, disabled=True)]))
    no_lock = _features(request=_request(_FOUR))

    recharge = _features(request=_request([{"move": "Recharge", "id": "recharge"}]))
    no_recharge = _features(request=_request(_FOUR))

    taunt = _features(log=[*BASE_LOG, "|-start|p1a: Charizard|move: Taunt"], request=_request(_FOUR))
    no_taunt = _features(request=_request(_FOUR))

    two_turn = _features(request=_request([{"move": "Outrage", "id": "outrage"}]))
    no_two_turn = _features(request=_request(_FOUR))

    # No request payload here: own/opponent active-move slots come purely from the
    # perspective-relative revealed-move maps, so flipping the player must remap
    # which side's move identity lands in own vs opponent slots.
    flip_log = [
        *BASE_LOG,
        "|move|p1a: Charizard|Flamethrower|p2a: Blastoise",
        "|move|p2a: Blastoise|Surf|p1a: Charizard",
    ]
    p1 = _features(log=flip_log, request=None, player="p1")
    p2 = _features(log=flip_log, request=None, player="p2")

    return {
        "own_move_slot_a_vs_b": _changed(slot_a, slot_b),
        "opponent_revealed_move_vs_unknown": _changed(opp_revealed, opp_unknown),
        "pp_known_vs_unknown": _changed(pp_known, pp_unknown),
        "disabled_move_vs_available": _changed(disabled, available),
        "encore_locked_vs_none": _changed(encore, no_encore),
        "choice_lock_vs_none": _changed(choice_lock, no_lock),
        "recharge_vs_none": _changed(recharge, no_recharge),
        "taunt_active_vs_inactive": _changed(taunt, no_taunt),
        "two_turn_move_vs_none": _changed(two_turn, no_two_turn),
        "perspective_flip_changes_features": _changed(p1, p2),
    }


def evaluate_action_counterfactuals() -> Dict[str, Any]:
    draco = _avec(_action("Draco Meteor"))
    psyshock = _avec(_action("Psyshock"))
    curse = _avec(_action("Curse"))
    bulk_up = _avec(_action("Bulk Up"))
    flamethrower = _avec(_action("Flamethrower"))
    will_o_wisp = _avec(_action("Will-O-Wisp"))
    tera_move = _avec(_action("Flamethrower", kind="move_tera", is_tera_action=True))
    normal_move = _avec(_action("Flamethrower"))
    switch_action = _avec(
        _action("Pikachu", kind="switch", index=9),
        {"team": [{"species": "Pikachu", "active": False}]},
    )
    move_action = _avec(_action("Flamethrower"))
    disabled_action = _avec(_action("Flamethrower", disabled=True))
    enabled_action = _avec(_action("Flamethrower"))
    extreme_speed = _avec(_action("Extreme Speed"))
    tackle = _avec(_action("Tackle"))
    flare_blitz = _avec(_action("Flare Blitz"))
    fire_punch = _avec(_action("Fire Punch"))

    def stat(vec: np.ndarray, name: str) -> float:
        return float(vec[ACTION_FEATURE_NAMES_V4.index(name)])

    return {
        "draco_vs_no_drawback_self_spa": {
            "changed": _achanged(draco, psyshock),
            "draco_self_spa_delta": stat(draco, "self_stat_delta_spa"),
            "psyshock_self_spa_delta": stat(psyshock, "self_stat_delta_spa"),
        },
        "curse_vs_bulk_up_speed": {
            "changed": _achanged(curse, bulk_up),
            "curse_spe": stat(curse, "self_stat_delta_spe"),
            "bulk_up_spe": stat(bulk_up, "self_stat_delta_spe"),
            "curse_atk": stat(curse, "self_stat_delta_atk"),
            "bulk_up_atk": stat(bulk_up, "self_stat_delta_atk"),
            "curse_def": stat(curse, "self_stat_delta_def"),
            "bulk_up_def": stat(bulk_up, "self_stat_delta_def"),
        },
        "damaging_vs_status": _achanged(flamethrower, will_o_wisp),
        "tera_move_vs_normal": _achanged(tera_move, normal_move),
        "switch_vs_move": _achanged(switch_action, move_action),
        "disabled_vs_enabled": _achanged(disabled_action, enabled_action),
        "priority_vs_non_priority": {
            "changed": _achanged(extreme_speed, tackle),
            "extreme_speed_priority": stat(extreme_speed, "effect_priority_norm"),
            "tackle_priority": stat(tackle, "effect_priority_norm"),
        },
        "recoil_vs_no_recoil": {
            "changed": _achanged(flare_blitz, fire_punch),
            "flare_blitz_recoil": stat(flare_blitz, "effect_recoil"),
            "fire_punch_recoil": stat(fire_punch, "effect_recoil"),
        },
    }


def evaluate_moves_actions_counterfactuals() -> Dict[str, Any]:
    state = evaluate_state_counterfactuals()
    action = evaluate_action_counterfactuals()
    neutral = _features(request=_request(_FOUR))
    return {
        "state_feature_version": FEATURE_VERSION_V7,
        "state_feature_dim": int(neutral.shape[0]),
        "action_feature_version": ACTION_FEATURE_VERSION_V4,
        "action_feature_dim": ACTION_FEATURE_DIM_V4,
        "synthetic": True,
        "state_comparisons": state,
        "action_comparisons": action,
    }


if __name__ == "__main__":  # pragma: no cover
    import json

    print(json.dumps(evaluate_moves_actions_counterfactuals(), indent=2, default=list))
