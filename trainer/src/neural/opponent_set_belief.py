"""Public-prefix-only opponent set belief contracts.

The API intentionally has no hidden-opponent-set input.  Beliefs are immutable:
each safe public evidence update returns a new snapshot, preserving prefix
causality and making future-reveal contamination structurally difficult.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, replace
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .meta_prior import (
    MetaPriorMetadata,
    MetaPriorSource,
    SetHypothesis,
    canonical_id,
)


class EvidenceKind(str, Enum):
    MOVE_REVEALED = "move_revealed"
    ABILITY_REVEALED = "ability_revealed"
    ITEM_REVEALED = "item_revealed"
    TERA_TYPE_REVEALED = "tera_type_revealed"


@dataclass(frozen=True)
class PublicEvidence:
    kind: EvidenceKind
    value: str
    event_index: int
    turn: int = 0
    subject_key: Optional[str] = None
    provenance: str = "public_protocol"

    def __post_init__(self) -> None:
        normalized = canonical_id(self.value)
        if not normalized:
            raise ValueError("Public evidence value is required.")
        if self.event_index < 0:
            raise ValueError("Public evidence event_index cannot be negative.")
        object.__setattr__(self, "value", normalized)
        object.__setattr__(
            self, "subject_key", canonical_id(self.subject_key) or None
        )


@dataclass(frozen=True)
class EvidenceLedgerEntry:
    evidence: PublicEvidence
    support_before: int
    support_after: int
    mass_before: float
    mass_after: float
    contradiction: bool


@dataclass(frozen=True)
class ConfirmedFacts:
    moves: frozenset[str] = frozenset()
    ability: Optional[str] = None
    item: Optional[str] = None
    tera_type: Optional[str] = None


@dataclass(frozen=True)
class RuledOutFacts:
    hypothesis_ids: frozenset[str] = frozenset()
    abilities: frozenset[str] = frozenset()
    items: frozenset[str] = frozenset()
    moves: frozenset[str] = frozenset()
    tera_types: frozenset[str] = frozenset()


@dataclass(frozen=True)
class OpponentSetBelief:
    format_id: str
    species_form_key: str
    source_metadata: MetaPriorMetadata
    hypotheses: Tuple[SetHypothesis, ...]
    other_mass: float
    source_available: bool
    confirmed: ConfirmedFacts = ConfirmedFacts()
    ruled_out: RuledOutFacts = RuledOutFacts()
    prior_contradiction: bool = False
    evidence_ledger: Tuple[EvidenceLedgerEntry, ...] = ()
    last_public_event_index: int = -1

    def __post_init__(self) -> None:
        total = sum(hypothesis.probability for hypothesis in self.hypotheses)
        total += float(self.other_mass)
        if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1.0e-9):
            raise ValueError(f"Opponent belief probability mass must sum to 1, got {total}.")

    @property
    def possible_abilities(self) -> frozenset[str]:
        return frozenset(
            hypothesis.ability for hypothesis in self.hypotheses if hypothesis.ability
        )

    @property
    def possible_items(self) -> frozenset[str]:
        return frozenset(
            hypothesis.item for hypothesis in self.hypotheses if hypothesis.item
        )

    @property
    def possible_moves(self) -> frozenset[str]:
        return frozenset(
            move for hypothesis in self.hypotheses for move in hypothesis.moves
        )

    @property
    def possible_tera_types(self) -> frozenset[str]:
        return frozenset(
            hypothesis.tera_type
            for hypothesis in self.hypotheses
            if hypothesis.tera_type
        )

    def update(self, evidence: PublicEvidence) -> "OpponentSetBelief":
        if evidence.event_index < self.last_public_event_index:
            raise ValueError(
                "Public evidence must be applied in non-decreasing event order."
            )
        if evidence.subject_key and evidence.subject_key != self.species_form_key:
            return replace(self, last_public_event_index=evidence.event_index)

        before = self.hypotheses
        compatible = tuple(
            hypothesis
            for hypothesis in before
            if _hypothesis_matches(hypothesis, evidence)
        )
        confirmed = _confirmed_with(self.confirmed, evidence)
        newly_ruled = {hypothesis.hypothesis_id for hypothesis in before} - {
            hypothesis.hypothesis_id for hypothesis in compatible
        }
        ruled_out = _ruled_out_with(
            self.ruled_out, before, compatible, newly_ruled
        )
        contradiction = bool(self.source_available and before and not compatible)

        if contradiction:
            hypotheses: Tuple[SetHypothesis, ...] = ()
            other_mass = 1.0
        else:
            compatible_mass = sum(hypothesis.probability for hypothesis in compatible)
            denominator = compatible_mass + self.other_mass
            if denominator <= 0.0:
                hypotheses = ()
                other_mass = 1.0
                contradiction = self.source_available
            else:
                hypotheses = tuple(
                    replace(
                        hypothesis,
                        probability=hypothesis.probability / denominator,
                    )
                    for hypothesis in compatible
                )
                other_mass = self.other_mass / denominator

        entry = EvidenceLedgerEntry(
            evidence=evidence,
            support_before=len(before),
            support_after=len(hypotheses),
            mass_before=sum(hypothesis.probability for hypothesis in before),
            mass_after=sum(hypothesis.probability for hypothesis in hypotheses),
            contradiction=contradiction,
        )
        return OpponentSetBelief(
            format_id=self.format_id,
            species_form_key=self.species_form_key,
            source_metadata=self.source_metadata,
            hypotheses=hypotheses,
            other_mass=other_mass,
            source_available=self.source_available,
            confirmed=confirmed,
            ruled_out=ruled_out,
            prior_contradiction=self.prior_contradiction or contradiction,
            evidence_ledger=(*self.evidence_ledger, entry),
            last_public_event_index=evidence.event_index,
        )


def initialize_belief(
    source: MetaPriorSource,
    *,
    format_id: str,
    species_form_key: str,
) -> OpponentSetBelief:
    prior = source.prior_for(format_id, species_form_key)
    if prior is None:
        return OpponentSetBelief(
            format_id=canonical_id(format_id),
            species_form_key=canonical_id(species_form_key),
            source_metadata=source.metadata,
            hypotheses=(),
            other_mass=1.0,
            source_available=False,
        )
    return OpponentSetBelief(
        format_id=canonical_id(format_id),
        species_form_key=prior.species_form_key,
        source_metadata=source.metadata,
        hypotheses=prior.hypotheses,
        other_mass=prior.other_mass,
        source_available=True,
    )


def _hypothesis_matches(
    hypothesis: SetHypothesis, evidence: PublicEvidence
) -> bool:
    if evidence.kind == EvidenceKind.MOVE_REVEALED:
        return evidence.value in hypothesis.moves
    if evidence.kind == EvidenceKind.ABILITY_REVEALED:
        return hypothesis.ability == evidence.value
    if evidence.kind == EvidenceKind.ITEM_REVEALED:
        return hypothesis.item == evidence.value
    if evidence.kind == EvidenceKind.TERA_TYPE_REVEALED:
        return hypothesis.tera_type == evidence.value
    raise ValueError(f"Unsupported public evidence kind: {evidence.kind!r}")


def _confirmed_with(
    confirmed: ConfirmedFacts, evidence: PublicEvidence
) -> ConfirmedFacts:
    if evidence.kind == EvidenceKind.MOVE_REVEALED:
        return replace(confirmed, moves=confirmed.moves | {evidence.value})
    if evidence.kind == EvidenceKind.ABILITY_REVEALED:
        return replace(confirmed, ability=evidence.value)
    if evidence.kind == EvidenceKind.ITEM_REVEALED:
        return replace(confirmed, item=evidence.value)
    if evidence.kind == EvidenceKind.TERA_TYPE_REVEALED:
        return replace(confirmed, tera_type=evidence.value)
    return confirmed


def _ruled_out_with(
    ruled_out: RuledOutFacts,
    before: Sequence[SetHypothesis],
    compatible: Sequence[SetHypothesis],
    newly_ruled: set[str],
) -> RuledOutFacts:
    before_abilities = {row.ability for row in before if row.ability}
    after_abilities = {row.ability for row in compatible if row.ability}
    before_items = {row.item for row in before if row.item}
    after_items = {row.item for row in compatible if row.item}
    before_moves = {move for row in before for move in row.moves}
    after_moves = {move for row in compatible for move in row.moves}
    before_tera = {row.tera_type for row in before if row.tera_type}
    after_tera = {row.tera_type for row in compatible if row.tera_type}
    return RuledOutFacts(
        hypothesis_ids=ruled_out.hypothesis_ids | newly_ruled,
        abilities=ruled_out.abilities | (before_abilities - after_abilities),
        items=ruled_out.items | (before_items - after_items),
        moves=ruled_out.moves | (before_moves - after_moves),
        tera_types=ruled_out.tera_types | (before_tera - after_tera),
    )


def _subject_from_ident(value: str) -> Optional[str]:
    if ": " not in value:
        return None
    return canonical_id(value.split(": ", 1)[1].split(",", 1)[0])


def public_evidence_from_protocol_lines(
    protocol_lines: Iterable[str],
    *,
    opponent_side: str,
    through_line: Optional[int] = None,
) -> Tuple[PublicEvidence, ...]:
    """Extract only explicit, safely attributable public set evidence.

    Generic failures/immunities are ignored.  A named ``[from] ability: X``
    marker is accepted because the protocol explicitly attributes the effect.
    Reflected move rows do not become move-use evidence for the reflector.
    """
    lines = list(protocol_lines)
    if through_line is not None:
        lines = lines[: max(0, int(through_line))]
    result: List[PublicEvidence] = []
    turn = 0
    for index, raw in enumerate(lines):
        if not isinstance(raw, str) or not raw.startswith("|"):
            continue
        parts = raw.split("|")
        command = parts[1] if len(parts) > 1 else ""
        if command == "turn" and len(parts) > 2:
            try:
                turn = int(parts[2])
            except ValueError:
                pass
            continue
        subject = parts[2] if len(parts) > 2 else ""
        if not subject.startswith(opponent_side):
            continue
        subject_key = _subject_from_ident(subject)
        from_ability = re.search(r"\[from\]\s*ability:\s*([^|\]]+)", raw, re.I)
        from_item = re.search(r"\[from\]\s*item:\s*([^|\]]+)", raw, re.I)
        if from_ability:
            result.append(
                PublicEvidence(
                    EvidenceKind.ABILITY_REVEALED,
                    from_ability.group(1),
                    index,
                    turn,
                    subject_key,
                    "public_protocol_named_ability",
                )
            )
        if from_item:
            result.append(
                PublicEvidence(
                    EvidenceKind.ITEM_REVEALED,
                    from_item.group(1),
                    index,
                    turn,
                    subject_key,
                    "public_protocol_named_item",
                )
            )
        if command == "move" and len(parts) > 3 and not from_ability:
            result.append(
                PublicEvidence(
                    EvidenceKind.MOVE_REVEALED,
                    parts[3],
                    index,
                    turn,
                    subject_key,
                )
            )
        elif command == "-ability" and len(parts) > 3:
            result.append(
                PublicEvidence(
                    EvidenceKind.ABILITY_REVEALED,
                    parts[3],
                    index,
                    turn,
                    subject_key,
                )
            )
        elif command in {"-item", "-enditem"} and len(parts) > 3:
            result.append(
                PublicEvidence(
                    EvidenceKind.ITEM_REVEALED,
                    parts[3],
                    index,
                    turn,
                    subject_key,
                )
            )
        elif command == "-terastallize" and len(parts) > 3:
            result.append(
                PublicEvidence(
                    EvidenceKind.TERA_TYPE_REVEALED,
                    parts[3],
                    index,
                    turn,
                    subject_key,
                )
            )
        elif command == "-activate" and len(parts) > 3:
            activation = re.fullmatch(
                r"\s*(ability|item)\s*:\s*(.+?)\s*", parts[3], re.I
            )
            if activation:
                kind = (
                    EvidenceKind.ABILITY_REVEALED
                    if activation.group(1).lower() == "ability"
                    else EvidenceKind.ITEM_REVEALED
                )
                result.append(
                    PublicEvidence(
                        kind,
                        activation.group(2),
                        index,
                        turn,
                        subject_key,
                        "public_protocol_activation",
                    )
                )
    return tuple(result)


def belief_from_public_prefix(
    source: MetaPriorSource,
    *,
    format_id: str,
    species_form_key: str,
    protocol_lines: Iterable[str],
    opponent_side: str,
    through_line: Optional[int] = None,
) -> OpponentSetBelief:
    belief = initialize_belief(
        source, format_id=format_id, species_form_key=species_form_key
    )
    for evidence in public_evidence_from_protocol_lines(
        protocol_lines, opponent_side=opponent_side, through_line=through_line
    ):
        belief = belief.update(evidence)
    return belief
