"""Diagnostic-only item/ability representation counterfactuals for feature v4."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from .live_private_features import (
    FEATURE_NAMES_V4,
    FEATURE_VERSION_V4,
    build_features_from_live_payload,
)


BASE_LOG = [
    "|start",
    "|switch|p1a: Pikachu|Pikachu, L80, M|100/100",
    "|switch|p2a: Charizard|Charizard, L80, M|100/100",
]


def _request(*, item: Optional[str], base_ability: Optional[str], ability: Optional[str]) -> Dict[str, Any]:
    return {
        "side": {
            "id": "p1",
            "pokemon": [
                {
                    "ident": "p1: Pikachu",
                    "details": "Pikachu, L80, M",
                    "condition": "200/200",
                    "active": True,
                    "stats": {"atk": 120, "def": 100, "spa": 140, "spd": 110, "spe": 180},
                    "moves": ["thunderbolt"],
                    "item": item,
                    "baseAbility": base_ability,
                    "ability": ability,
                    "teraType": "Electric",
                }
            ],
        },
        "active": [
            {
                "moves": [
                    {
                        "move": "Thunderbolt",
                        "id": "thunderbolt",
                        "pp": 24,
                        "maxpp": 24,
                        "target": "normal",
                        "disabled": False,
                    }
                ]
            }
        ],
    }


def _features(
    *,
    log: Optional[List[str]] = None,
    request: Optional[Dict[str, Any]] = None,
    player: str = "p1",
) -> np.ndarray:
    features, *_ = build_features_from_live_payload(
        log=[*(log or BASE_LOG), "|turn|1"],
        room_id="item-ability-counterfactual",
        url="cf://item-ability",
        player=player,
        request_payload=request,
        legal_actions=[],
        feature_version=FEATURE_VERSION_V4,
    )
    return features


def _changed(left: np.ndarray, right: np.ndarray) -> List[str]:
    indices = np.where(~np.isclose(left, right, atol=1e-7))[0]
    return [FEATURE_NAMES_V4[index] for index in indices]


def evaluate_item_ability_counterfactuals() -> Dict[str, Any]:
    unknown = _features()
    no_item = _features(request=_request(item=None, base_ability=None, ability=None))
    boots = _features(log=[*BASE_LOG, "|-item|p1a: Pikachu|Heavy-Duty Boots"])
    static = _features(log=[*BASE_LOG, "|-ability|p1a: Pikachu|Static"])

    removed_log = [
        *BASE_LOG,
        "|-item|p1a: Pikachu|Heavy-Duty Boots",
        "|-enditem|p1a: Pikachu|Heavy-Duty Boots|[from] move: Knock Off",
    ]
    consumed_log = [
        *BASE_LOG,
        "|-item|p1a: Pikachu|Sitrus Berry",
        "|-enditem|p1a: Pikachu|Sitrus Berry|[eat]",
    ]
    changed_ability_log = [
        *BASE_LOG,
        "|-ability|p1a: Pikachu|Static",
        "|-ability|p1a: Pikachu|Insomnia|[from] move: Worry Seed",
    ]
    suppressed_ability_log = [
        *BASE_LOG,
        "|-ability|p1a: Pikachu|Static",
        "|-endability|p1a: Pikachu",
    ]
    magic_room_log = [
        *BASE_LOG,
        "|-item|p1a: Pikachu|Heavy-Duty Boots",
        "|-fieldstart|move: Magic Room",
    ]
    removed = _features(log=removed_log)
    consumed = _features(log=consumed_log)
    changed_ability = _features(log=changed_ability_log)
    suppressed_ability = _features(log=suppressed_ability_log)
    magic_room = _features(log=magic_room_log)

    perspective_log = [*BASE_LOG, "|-item|p1a: Pikachu|Heavy-Duty Boots", "|-ability|p1a: Pikachu|Static"]
    p1 = _features(log=perspective_log, player="p1")
    p2 = _features(log=perspective_log, player="p2")

    return {
        "feature_version": FEATURE_VERSION_V4,
        "feature_dim": int(unknown.shape[0]),
        "synthetic": True,
        "comparisons": {
            "unknown_vs_confirmed_no_item": _changed(unknown, no_item),
            "unknown_vs_boots": _changed(unknown, boots),
            "boots_vs_removed": _changed(boots, removed),
            "boots_vs_consumed": _changed(boots, consumed),
            "ability_unknown_vs_static": _changed(unknown, static),
            "base_static_vs_current_insomnia": _changed(static, changed_ability),
            "ability_active_vs_suppressed": _changed(static, suppressed_ability),
            "boots_active_vs_magic_room_suppressed": _changed(boots, magic_room),
        },
        "perspective": {
            "p1_own_item_state_held": float(p1[FEATURE_NAMES_V4.index("own_active_item_state_held")]),
            "p2_opponent_item_state_held": float(
                p2[FEATURE_NAMES_V4.index("opponent_active_item_state_held")]
            ),
            "p1_own_ability_state_known": float(
                p1[FEATURE_NAMES_V4.index("own_active_ability_state_known")]
            ),
            "p2_opponent_ability_state_known": float(
                p2[FEATURE_NAMES_V4.index("opponent_active_ability_state_known")]
            ),
        },
    }
