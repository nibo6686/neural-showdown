"""Diagnostic adapter from parsed public replay prefixes to set beliefs.

This module consumes only ``parse_protocol_log`` output retained in
``trajectory["protocol_log"]``.  It deliberately ignores private/request/team
payloads and does not produce model features.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from .meta_prior import MetaPriorSource, canonical_id
from .opponent_set_belief import (
    EvidenceKind,
    OpponentSetBelief,
    PublicEvidence,
    initialize_belief,
)


@dataclass(frozen=True)
class PublicOpponentSlotBelief:
    """One causally observed public identity segment.

    ``replace`` starts a new segment instead of rewriting the earlier displayed
    identity.  This is important for Illusion: pre-reveal evidence remains
    attached to the public disguise that was visible at that prefix.
    """

    slot_key: str
    position: str
    species_form_key: str
    belief: OpponentSetBelief
    active: bool = False
    identity_ambiguous: bool = False
    superseded_by: Optional[str] = None


@dataclass(frozen=True)
class ReplayPrefixBeliefSnapshot:
    replay_id: Optional[str]
    format_id: str
    opponent_side: str
    prefix_line_count: int
    through_turn: Optional[int]
    slots: Tuple[PublicOpponentSlotBelief, ...]

    @property
    def active_slots(self) -> Tuple[PublicOpponentSlotBelief, ...]:
        return tuple(slot for slot in self.slots if slot.active)

    @property
    def known_slots(self) -> Tuple[PublicOpponentSlotBelief, ...]:
        return self.slots

    def slots_for_species(self, species_form_key: str) -> Tuple[PublicOpponentSlotBelief, ...]:
        key = canonical_id(species_form_key)
        return tuple(slot for slot in self.slots if slot.species_form_key == key)

    def slot(self, slot_key: str) -> PublicOpponentSlotBelief:
        for row in self.slots:
            if row.slot_key == slot_key:
                return row
        raise KeyError(slot_key)


def _opponent_side(perspective_side: str) -> str:
    if perspective_side == "p1":
        return "p2"
    if perspective_side == "p2":
        return "p1"
    raise ValueError("perspective_side must be 'p1' or 'p2'.")


def _parts(raw: str) -> List[str]:
    return raw.split("|") if isinstance(raw, str) and raw.startswith("|") else []


def _position(ident: str) -> Optional[str]:
    match = re.match(r"^(p[12][a-z]?):", str(ident or "").strip())
    return match.group(1) if match else None


def _side(ident: str) -> Optional[str]:
    match = re.match(r"^(p[12])", str(ident or "").strip())
    return match.group(1) if match else None


def _species_from_details(details: str) -> str:
    return canonical_id(str(details or "").split(",", 1)[0])


def _species_from_ident(ident: str) -> str:
    text = str(ident or "")
    return canonical_id(text.split(": ", 1)[1] if ": " in text else "")


def replay_protocol_prefix(
    trajectory: Mapping[str, Any],
    *,
    through_turn: Optional[int] = None,
    through_line: Optional[int] = None,
) -> Tuple[str, ...]:
    """Return an exclusive-line / inclusive-turn public protocol prefix."""

    raw = trajectory.get("protocol_log")
    lines = tuple(str(line) for line in raw) if isinstance(raw, list) else ()
    line_limit = len(lines) if through_line is None else max(0, min(len(lines), int(through_line)))
    selected: List[str] = []
    for line in lines[:line_limit]:
        parts = _parts(line)
        if (
            through_turn is not None
            and len(parts) > 2
            and parts[1] == "turn"
        ):
            try:
                if int(parts[2]) > int(through_turn):
                    break
            except ValueError:
                pass
        selected.append(line)
    return tuple(selected)


def _named_owner(raw: str, default_ident: str) -> str:
    match = re.search(r"\[of\]\s*([^|]+)", raw, re.I)
    return match.group(1).strip() if match else default_ident


def _line_evidence(raw: str, event_index: int, turn: int) -> Tuple[Tuple[str, PublicEvidence], ...]:
    """Convert one protocol row into explicitly attributable set evidence."""

    parts = _parts(raw)
    if len(parts) < 3:
        return ()
    command = parts[1]
    subject = parts[2]
    result: List[Tuple[str, PublicEvidence]] = []

    from_ability = re.search(r"\[from\]\s*ability:\s*([^|\]]+)", raw, re.I)
    from_item = re.search(r"\[from\]\s*item:\s*([^|\]]+)", raw, re.I)
    if from_ability:
        owner = _named_owner(raw, subject)
        result.append(
            (
                owner,
                PublicEvidence(
                    EvidenceKind.ABILITY_REVEALED,
                    from_ability.group(1),
                    event_index,
                    turn,
                    provenance="public_replay_named_ability",
                ),
            )
        )
    if from_item:
        owner = _named_owner(raw, subject)
        result.append(
            (
                owner,
                PublicEvidence(
                    EvidenceKind.ITEM_REVEALED,
                    from_item.group(1),
                    event_index,
                    turn,
                    provenance="public_replay_named_item",
                ),
            )
        )

    if command == "move" and len(parts) > 3 and not from_ability:
        result.append(
            (
                subject,
                PublicEvidence(
                    EvidenceKind.MOVE_REVEALED,
                    parts[3],
                    event_index,
                    turn,
                    provenance="public_replay_move",
                ),
            )
        )
    elif command == "-ability" and len(parts) > 3:
        result.append(
            (
                subject,
                PublicEvidence(
                    EvidenceKind.ABILITY_REVEALED,
                    parts[3],
                    event_index,
                    turn,
                    provenance="public_replay_ability",
                ),
            )
        )
    elif command in {"-item", "-enditem"} and len(parts) > 3:
        result.append(
            (
                subject,
                PublicEvidence(
                    EvidenceKind.ITEM_REVEALED,
                    parts[3],
                    event_index,
                    turn,
                    provenance="public_replay_item",
                ),
            )
        )
    elif command == "-terastallize" and len(parts) > 3:
        result.append(
            (
                subject,
                PublicEvidence(
                    EvidenceKind.TERA_TYPE_REVEALED,
                    parts[3],
                    event_index,
                    turn,
                    provenance="public_replay_tera",
                ),
            )
        )
    elif command == "-activate" and len(parts) > 3:
        activation = re.fullmatch(r"\s*(ability|item)\s*:\s*(.+?)\s*", parts[3], re.I)
        if activation:
            kind = (
                EvidenceKind.ABILITY_REVEALED
                if activation.group(1).lower() == "ability"
                else EvidenceKind.ITEM_REVEALED
            )
            result.append(
                (
                    subject,
                    PublicEvidence(
                        kind,
                        activation.group(2),
                        event_index,
                        turn,
                        provenance="public_replay_activation",
                    ),
                )
            )
        elif (
            canonical_id(parts[3]) == "movepoltergeist"
            and len(parts) > 4
            and canonical_id(parts[4])
        ):
            result.append(
                (
                    subject,
                    PublicEvidence(
                        EvidenceKind.ITEM_REVEALED,
                        parts[4],
                        event_index,
                        turn,
                        provenance="public_replay_poltergeist_item",
                    ),
                )
            )
    return tuple(result)


def build_replay_prefix_beliefs(
    trajectory: Mapping[str, Any],
    source: MetaPriorSource,
    *,
    perspective_side: str,
    through_turn: Optional[int] = None,
    through_line: Optional[int] = None,
) -> ReplayPrefixBeliefSnapshot:
    """Build diagnostic beliefs from only the retained public replay prefix."""

    opponent_side = _opponent_side(perspective_side)
    format_id = canonical_id(trajectory.get("format") or source.metadata.format_id)
    lines = replay_protocol_prefix(
        trajectory, through_turn=through_turn, through_line=through_line
    )
    slots: Dict[str, PublicOpponentSlotBelief] = {}
    slot_order: List[str] = []
    active_by_position: Dict[str, str] = {}
    reusable_by_species: Dict[str, str] = {}
    species_counts: Dict[str, int] = {}
    turn = 0

    def create_slot(position: str, species: str) -> str:
        count = species_counts.get(species, 0) + 1
        species_counts[species] = count
        slot_key = f"{opponent_side}:{species}#{count}"
        slots[slot_key] = PublicOpponentSlotBelief(
            slot_key=slot_key,
            position=position,
            species_form_key=species,
            belief=initialize_belief(
                source, format_id=format_id, species_form_key=species
            ),
            active=True,
        )
        slot_order.append(slot_key)
        reusable_by_species[species] = slot_key
        return slot_key

    def deactivate(position: str) -> None:
        old_key = active_by_position.get(position)
        if old_key:
            slots[old_key] = replace(slots[old_key], active=False)

    def select_switch_slot(position: str, species: str) -> str:
        reusable = reusable_by_species.get(species)
        if reusable and not slots[reusable].identity_ambiguous:
            slots[reusable] = replace(slots[reusable], position=position, active=True)
            return reusable
        return create_slot(position, species)

    for index, raw in enumerate(lines):
        parts = _parts(raw)
        command = parts[1] if len(parts) > 1 else ""
        if command == "turn" and len(parts) > 2:
            try:
                turn = int(parts[2])
            except ValueError:
                pass
            continue

        if command in {"switch", "drag"} and len(parts) > 3 and _side(parts[2]) == opponent_side:
            position = _position(parts[2])
            species = _species_from_details(parts[3])
            if position and species:
                deactivate(position)
                slot_key = select_switch_slot(position, species)
                active_by_position[position] = slot_key
        elif command == "replace" and len(parts) > 3 and _side(parts[2]) == opponent_side:
            position = _position(parts[2])
            species = _species_from_details(parts[3])
            if position and species:
                previous = active_by_position.get(position)
                if previous:
                    slots[previous] = replace(
                        slots[previous],
                        active=False,
                        identity_ambiguous=True,
                    )
                    reusable_by_species.pop(slots[previous].species_form_key, None)
                new_key = create_slot(position, species)
                if previous:
                    slots[previous] = replace(slots[previous], superseded_by=new_key)
                active_by_position[position] = new_key

        for owner_ident, evidence in _line_evidence(raw, index, turn):
            if _side(owner_ident) != opponent_side:
                continue
            position = _position(owner_ident)
            if not position:
                continue
            slot_key = active_by_position.get(position)
            if not slot_key:
                species = _species_from_ident(owner_ident)
                if not species:
                    continue
                slot_key = create_slot(position, species)
                active_by_position[position] = slot_key
            slot = slots[slot_key]
            applied = replace(evidence, subject_key=slot.species_form_key)
            slots[slot_key] = replace(slot, belief=slot.belief.update(applied))

    return ReplayPrefixBeliefSnapshot(
        replay_id=(
            str(trajectory.get("replay_id"))
            if trajectory.get("replay_id") is not None
            else None
        ),
        format_id=format_id,
        opponent_side=opponent_side,
        prefix_line_count=len(lines),
        through_turn=through_turn,
        slots=tuple(slots[key] for key in slot_order),
    )


def fixture_source_for_species(
    *,
    format_id: str,
    priors: Mapping[str, Any],
    source_version: str = "replay-adapter-fixture-v1",
) -> MetaPriorSource:
    """Small convenience wrapper used by diagnostic replay-prefix tests."""

    from .meta_prior import FixtureMetaPriorSource

    return FixtureMetaPriorSource(
        format_id=format_id,
        priors=priors,
        source_version=source_version,
    )
