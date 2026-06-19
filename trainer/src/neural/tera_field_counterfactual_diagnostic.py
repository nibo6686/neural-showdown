"""Diagnostic-only Tera and field counterfactuals for live-private v6."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from .live_private_features import (
    FEATURE_NAMES_V6,
    FEATURE_VERSION_V6,
    build_features_from_live_payload,
)


BASE_LOG = [
    "|start",
    "|switch|p1a: Charizard|Charizard, L80, M|100/100",
    "|switch|p2a: Blastoise|Blastoise, L80, M|100/100",
]


def _request(*, can_tera: Optional[str] = "Fire", terastallized: bool = False) -> Dict[str, Any]:
    active: Dict[str, Any] = {
        "moves": [{"move": "Flamethrower", "id": "flamethrower", "pp": 24, "maxpp": 24}],
    }
    if can_tera:
        active["canTerastallize"] = can_tera
    return {
        "side": {
            "id": "p1",
            "pokemon": [
                {
                    "ident": "p1: Charizard",
                    "details": "Charizard, L80, M",
                    "condition": "200/200",
                    "active": True,
                    "moves": ["flamethrower"],
                    "stats": {},
                    "item": None,
                    "baseAbility": "blaze",
                    "ability": "blaze",
                    "teraType": can_tera or "Fire",
                    "terastallized": (can_tera or "Fire") if terastallized else "",
                }
            ],
        },
        "active": [active],
    }


def _features(
    *,
    log: Optional[List[str]] = None,
    request: Optional[Dict[str, Any]] = None,
    player: str = "p1",
) -> np.ndarray:
    features, *_ = build_features_from_live_payload(
        log=[*(log or BASE_LOG), "|turn|3"],
        room_id="tera-field-counterfactual",
        url="cf://tera-field",
        player=player,
        request_payload=request,
        legal_actions=[],
        feature_version=FEATURE_VERSION_V6,
    )
    return features


def _changed(left: np.ndarray, right: np.ndarray) -> List[str]:
    indices = np.where(~np.isclose(left, right, atol=1e-7))[0]
    return [FEATURE_NAMES_V6[index] for index in indices]


def evaluate_tera_field_counterfactuals() -> Dict[str, Any]:
    neutral = _features()
    tera_available = _features(request=_request(can_tera="Fire"))
    tera_unavailable = _features(request=_request(can_tera=None))
    tera_fire = _features(log=[*BASE_LOG, "|-terastallize|p1a: Charizard|Fire"])
    tera_water = _features(log=[*BASE_LOG, "|-terastallize|p1a: Charizard|Water"])
    opponent_tera = _features(log=[*BASE_LOG, "|-terastallize|p2a: Blastoise|Water"])

    rain = _features(log=[*BASE_LOG, "|-weather|RainDance"])
    sun = _features(log=[*BASE_LOG, "|-weather|SunnyDay"])
    electric_terrain = _features(log=[*BASE_LOG, "|-fieldstart|move: Electric Terrain"])
    trick_room = _features(log=[*BASE_LOG, "|-fieldstart|move: Trick Room"])
    own_reflect = _features(log=[*BASE_LOG, "|-sidestart|p1: Player|move: Reflect"])
    opponent_reflect = _features(log=[*BASE_LOG, "|-sidestart|p2: Player|move: Reflect"])
    own_light_screen = _features(log=[*BASE_LOG, "|-sidestart|p1: Player|move: Light Screen"])
    opponent_light_screen = _features(log=[*BASE_LOG, "|-sidestart|p2: Player|move: Light Screen"])
    own_tailwind = _features(log=[*BASE_LOG, "|-sidestart|p1: Player|move: Tailwind"])
    opponent_tailwind = _features(log=[*BASE_LOG, "|-sidestart|p2: Player|move: Tailwind"])
    own_rocks = _features(log=[*BASE_LOG, "|-sidestart|p1: Player|move: Stealth Rock"])
    opponent_rocks = _features(log=[*BASE_LOG, "|-sidestart|p2: Player|move: Stealth Rock"])
    spikes_one = _features(log=[*BASE_LOG, "|-sidestart|p1: Player|move: Spikes"])
    spikes_two = _features(
        log=[
            *BASE_LOG,
            "|-sidestart|p1: Player|move: Spikes",
            "|-sidestart|p1: Player|move: Spikes",
        ]
    )
    toxic_one = _features(log=[*BASE_LOG, "|-sidestart|p1: Player|move: Toxic Spikes"])
    toxic_two = _features(
        log=[
            *BASE_LOG,
            "|-sidestart|p1: Player|move: Toxic Spikes",
            "|-sidestart|p1: Player|move: Toxic Spikes",
        ]
    )
    sticky_web = _features(log=[*BASE_LOG, "|-sidestart|p1: Player|move: Sticky Web"])

    perspective_log = [
        *BASE_LOG,
        "|-sidestart|p1: Player|move: Reflect",
        "|-sidestart|p1: Player|move: Tailwind",
        "|-sidestart|p1: Player|move: Stealth Rock",
    ]
    p1 = _features(log=perspective_log, player="p1")
    p2 = _features(log=perspective_log, player="p2")

    return {
        "feature_version": FEATURE_VERSION_V6,
        "feature_dim": int(neutral.shape[0]),
        "synthetic": True,
        "comparisons": {
            "own_tera_available_vs_unavailable": _changed(tera_available, tera_unavailable),
            "own_terastallized_vs_not": _changed(neutral, tera_fire),
            "own_tera_fire_vs_water": _changed(tera_fire, tera_water),
            "opponent_revealed_tera_vs_not": _changed(neutral, opponent_tera),
            "base_current_vs_tera_current_type": _changed(neutral, tera_fire),
            "weather_none_vs_rain": _changed(neutral, rain),
            "weather_rain_vs_sun": _changed(rain, sun),
            "terrain_none_vs_electric": _changed(neutral, electric_terrain),
            "trick_room_inactive_vs_active": _changed(neutral, trick_room),
            "own_vs_opponent_reflect": _changed(own_reflect, opponent_reflect),
            "own_vs_opponent_light_screen": _changed(own_light_screen, opponent_light_screen),
            "own_vs_opponent_tailwind": _changed(own_tailwind, opponent_tailwind),
            "own_vs_opponent_stealth_rock": _changed(own_rocks, opponent_rocks),
            "spikes_one_vs_two_layers": _changed(spikes_one, spikes_two),
            "toxic_spikes_one_vs_two_layers": _changed(toxic_one, toxic_two),
            "sticky_web_inactive_vs_active": _changed(neutral, sticky_web),
        },
        "perspective": {
            "p1_own_reflect_active": float(p1[FEATURE_NAMES_V6.index("own_reflect_state_active")]),
            "p2_opponent_reflect_active": float(
                p2[FEATURE_NAMES_V6.index("opponent_reflect_state_active")]
            ),
            "p1_own_tailwind_active": float(p1[FEATURE_NAMES_V6.index("own_tailwind_state_active")]),
            "p2_opponent_tailwind_active": float(
                p2[FEATURE_NAMES_V6.index("opponent_tailwind_state_active")]
            ),
            "p1_own_rocks_active": float(p1[FEATURE_NAMES_V6.index("own_stealthrock_state_active")]),
            "p2_opponent_rocks_active": float(
                p2[FEATURE_NAMES_V6.index("opponent_stealthrock_state_active")]
            ),
        },
    }
