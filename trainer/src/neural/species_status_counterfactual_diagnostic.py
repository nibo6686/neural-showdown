"""Diagnostic-only species, roster, and major-status counterfactuals for v5."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from .live_private_features import (
    FEATURE_NAMES_V5,
    FEATURE_VERSION_V5,
    build_features_from_live_payload,
)


BASE_LOG = [
    "|start",
    "|teamsize|p1|6",
    "|teamsize|p2|6",
    "|switch|p1a: Pikachu|Pikachu, L80, M|100/100",
    "|switch|p2a: Charizard|Charizard, L80, M|100/100",
]


def _request(
    active_species: str = "Pikachu",
    bench_species: str = "Blissey",
    *,
    active_slot: int = 1,
) -> Dict[str, Any]:
    return {
        "side": {
            "id": "p1",
            "pokemon": [
                {
                    "ident": f"p1: {active_species}",
                    "details": f"{active_species}, L80",
                    "condition": "200/200",
                    "active": active_slot == 1,
                    "moves": ["tackle"],
                    "stats": {},
                    "item": None,
                    "baseAbility": None,
                    "ability": None,
                    "teraType": "Normal",
                },
                {
                    "ident": f"p1: {bench_species}",
                    "details": f"{bench_species}, L80",
                    "condition": "200/200",
                    "active": active_slot == 2,
                    "moves": ["tackle"],
                    "stats": {},
                    "item": None,
                    "baseAbility": None,
                    "ability": None,
                    "teraType": "Normal",
                },
            ],
        },
        "active": [{"moves": [{"move": "Tackle", "id": "tackle", "pp": 35, "maxpp": 35}]}],
    }


def _features(
    *,
    log: Optional[List[str]] = None,
    request: Optional[Dict[str, Any]] = None,
    player: str = "p1",
) -> np.ndarray:
    features, *_ = build_features_from_live_payload(
        log=[*(log or BASE_LOG), "|turn|3"],
        room_id="species-status-counterfactual",
        url="cf://species-status",
        player=player,
        request_payload=request,
        legal_actions=[],
        feature_version=FEATURE_VERSION_V5,
    )
    return features


def _changed(left: np.ndarray, right: np.ndarray) -> List[str]:
    indices = np.where(~np.isclose(left, right, atol=1e-7))[0]
    return [FEATURE_NAMES_V5[index] for index in indices]


def evaluate_species_status_counterfactuals() -> Dict[str, Any]:
    own_pikachu = _features(request=_request("Pikachu", "Blissey"))
    own_raichu = _features(request=_request("Raichu", "Blissey"))
    own_bench_garchomp = _features(request=_request("Pikachu", "Garchomp"))
    own_blissey_active = _features(request=_request("Pikachu", "Blissey", active_slot=2))

    opponent_charizard = _features()
    opponent_dragonite = _features(
        log=[
            *BASE_LOG[:-1],
            "|switch|p2a: Dragonite|Dragonite, L80, M|100/100",
        ]
    )
    opponent_unknown = _features(log=BASE_LOG[:-1])
    opponent_bench_a = _features(
        log=[
            *BASE_LOG,
            "|switch|p2a: Garchomp|Garchomp, L80, M|100/100",
        ]
    )
    opponent_bench_b = _features(
        log=[
            *BASE_LOG[:-1],
            "|switch|p2a: Dragonite|Dragonite, L80, M|100/100",
            "|switch|p2a: Garchomp|Garchomp, L80, M|100/100",
        ]
    )

    transformed = _features(
        log=[
            "|start",
            "|switch|p1a: Ditto|Ditto, L80|100/100",
            "|switch|p2a: Garchomp|Garchomp, L80, M|100/100",
            "|-transform|p1a: Ditto|p2a: Garchomp",
        ]
    )
    untransformed = _features(
        log=[
            "|start",
            "|switch|p1a: Ditto|Ditto, L80|100/100",
            "|switch|p2a: Garchomp|Garchomp, L80, M|100/100",
        ]
    )

    status_vectors = {
        "none": _features(),
        **{
            status: _features(log=[*BASE_LOG, f"|-status|p1a: Pikachu|{status}"])
            for status in ("brn", "par", "slp", "psn", "tox", "frz")
        },
        "unknown": _features(log=["|start", "|switch|p2a: Charizard|Charizard, L80|100/100"]),
    }
    perspective_log = [
        *BASE_LOG,
        "|-status|p1a: Pikachu|brn",
        "|switch|p1a: Blissey|Blissey, L80, F|100/100",
    ]
    p1 = _features(log=perspective_log, player="p1")
    p2 = _features(log=perspective_log, player="p2")

    return {
        "feature_version": FEATURE_VERSION_V5,
        "feature_dim": int(own_pikachu.shape[0]),
        "synthetic": True,
        "comparisons": {
            "own_active_pikachu_vs_raichu": _changed(own_pikachu, own_raichu),
            "opponent_active_charizard_vs_dragonite": _changed(opponent_charizard, opponent_dragonite),
            "transform_current_vs_base": _changed(untransformed, transformed),
            "opponent_active_unknown_vs_known": _changed(opponent_unknown, opponent_charizard),
            "own_bench_blissey_vs_garchomp": _changed(own_pikachu, own_bench_garchomp),
            "same_roster_active_slot_1_vs_slot_2": _changed(own_pikachu, own_blissey_active),
            "opponent_revealed_bench_charizard_vs_dragonite": _changed(opponent_bench_a, opponent_bench_b),
            "burn_vs_none": _changed(status_vectors["none"], status_vectors["brn"]),
            "paralysis_vs_burn": _changed(status_vectors["brn"], status_vectors["par"]),
            "sleep_vs_paralysis": _changed(status_vectors["par"], status_vectors["slp"]),
            "poison_vs_toxic": _changed(status_vectors["psn"], status_vectors["tox"]),
            "freeze_vs_none": _changed(status_vectors["none"], status_vectors["frz"]),
            "status_unknown_vs_none": _changed(status_vectors["unknown"], status_vectors["none"]),
        },
        "perspective": {
            "p1_opponent_roster_slot_1_status_burn": float(
                p1[FEATURE_NAMES_V5.index("own_roster_slot_1_status_brn")]
            ),
            "p2_opponent_roster_slot_1_status_burn": float(
                p2[FEATURE_NAMES_V5.index("opponent_roster_slot_1_status_brn")]
            ),
            "p1_own_roster_slot_2_active": float(
                p1[FEATURE_NAMES_V5.index("own_roster_slot_2_placement_active")]
            ),
            "p2_opponent_roster_slot_2_active": float(
                p2[FEATURE_NAMES_V5.index("opponent_roster_slot_2_placement_active")]
            ),
        },
    }
