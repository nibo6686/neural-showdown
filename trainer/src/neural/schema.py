from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TypedDict

import numpy as np


class LegalAction(TypedDict, total=False):
    index: int
    kind: str
    choice: str
    label: str
    move: Optional[str]
    slot: Optional[int]


class LegalActionSet(TypedDict):
    mask: List[bool]
    actions: List[Optional[LegalAction]]
    available_indices: List[int]


class RequestMoveView(TypedDict):
    slot: int
    move: str
    id: str
    pp: int
    maxpp: int
    target: str
    disabled: bool
    type: Optional[str]
    category: Optional[str]
    base_power: int
    accuracy: Optional[int]


class RequestActiveView(TypedDict, total=False):
    moves: List[RequestMoveView]
    can_terastallize: bool
    tera_type: Optional[str]
    trapped: bool
    can_switch: bool


class RequestSidePokemonView(TypedDict, total=False):
    slot: int
    ident: str
    details: str
    condition: str
    active: bool
    moves: List[str]
    stats: Dict[str, int]
    base_ability: Optional[str]
    ability: Optional[str]
    item: Optional[str]
    tera_type: Optional[str]
    terastallized: bool


class ChoiceRequestView(TypedDict):
    player: str
    wait: bool
    team_preview: bool
    force_switch: bool
    trapped: bool
    rqid: Optional[int]
    active: Optional[RequestActiveView]
    side: List[RequestSidePokemonView]
    legal_actions: LegalActionSet
    raw: Any


class PokemonView(TypedDict, total=False):
    slot: int
    ident: str
    name: str
    species: str
    details: str
    active: bool
    fainted: bool
    hp_text: Optional[str]
    hp_ratio: Optional[float]
    status: Optional[str]
    gender: Optional[str]
    level: Optional[int]
    item: Optional[str]
    ability: Optional[str]
    base_ability: Optional[str]
    moves: List[str]
    revealed_moves: List[str]
    types: List[str]
    tera_type: Optional[str]
    terastallized: bool
    stats: Dict[str, int]
    boosts: Dict[str, int]
    volatiles: List[str]
    possible_roles: List[str]
    possible_moves: List[str]
    possible_abilities: List[str]
    possible_tera_types: List[str]


class FieldView(TypedDict):
    weather: Optional[str]
    terrain: Optional[str]
    pseudo_weather: List[str]
    side_conditions: Dict[str, Dict[str, int]]


class BattleView(TypedDict):
    env_id: str
    format: str
    gen: Optional[int]
    turn: int
    player: str
    opponent: str
    terminated: bool
    winner: Optional[str]
    names: Dict[str, Optional[str]]
    team_size: Dict[str, int]
    active: Dict[str, Optional[int]]
    field: FieldView
    self_team: List[PokemonView]
    opponent_team: List[PokemonView]


class StepResult(TypedDict):
    env_id: str
    terminated: bool
    winner: Optional[str]
    rewards: Dict[str, float]
    requests: Dict[str, Optional[ChoiceRequestView]]
    views: Dict[str, BattleView]
    omniscient: Any
    log_delta: List[str]
    info: Dict[str, Any]


@dataclass
class FeatureTensors:
    global_vector: np.ndarray
    own_team: np.ndarray
    opponent_team: np.ndarray
    request_vector: np.ndarray
    legal_mask: np.ndarray
    flat: np.ndarray
