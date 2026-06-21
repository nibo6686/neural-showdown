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


# Showdown mechanics that produce *current-state* facts, not base hidden-set
# facts.  Evidence flagged current-state-only is recorded in the ledger but must
# never filter or contradict the base-set prior hypotheses.
COPIED_ABILITY_MARKER = "trace"  # `[from] ability: Trace` copies the target ability
TRANSFORM_ABILITY_MARKERS = frozenset({"imposter"})  # auto-Transform on switch-in
UNIVERSAL_NOISE_MOVES = frozenset({"struggle"})  # never a declared set move

# Forme/identity-tied abilities whose label reflects current forme activation;
# the static role source stores the base set under a (possibly different) forme
# key, so the reveal is forme state, not a base-set contradiction.
FORME_STATE_ABILITY_PREFIXES = (
    "asone",
    "embodyaspect",
    "terashell",
    "terashift",
    "battlebond",
    "zerotohero",
    "shieldsdown",
    "powerconstruct",
    "schooling",
    "gulpmissile",
    "iceface",
    "hungerswitch",
    "disguise",
    "commander",
)


def is_universal_noise_move(value: str) -> bool:
    return canonical_id(value) in UNIVERSAL_NOISE_MOVES


def is_copied_ability_marker(value: str) -> bool:
    return canonical_id(value) == COPIED_ABILITY_MARKER


def is_transform_ability(value: str) -> bool:
    return canonical_id(value) in TRANSFORM_ABILITY_MARKERS


def is_forme_state_ability(value: str) -> bool:
    canonical = canonical_id(value)
    return any(
        canonical == prefix or canonical.startswith(prefix)
        for prefix in FORME_STATE_ABILITY_PREFIXES
    )


@dataclass(frozen=True)
class PublicEvidence:
    kind: EvidenceKind
    value: str
    event_index: int
    turn: int = 0
    subject_key: Optional[str] = None
    provenance: str = "public_protocol"
    # When True the reveal is a copied/forme current-state fact (Trace, Imposter/
    # Transform copies, Struggle, forme-state abilities) recorded without
    # filtering or contradicting the base hidden-set prior.
    current_state_only: bool = False

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
    source_covered: bool = True
    current_state_only: bool = False


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
    # Set when the prior was resolved through an explicit form-alias policy.
    prior_source_key: Optional[str] = None
    prior_alias_policy_version: Optional[str] = None
    # Source-quality provenance copied from the originating ``SetPrior`` so that
    # feature consumers can expose calibration/coverage caveats explicitly.
    prior_joint_quality: Optional[str] = None
    prior_coverage_warnings: Tuple[str, ...] = ()

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

        if evidence.current_state_only:
            # Copied/forme current-state fact (Trace, Imposter/Transform copy,
            # Struggle, forme-state ability).  Record it in the ledger only; the
            # base-set hypotheses, confirmed base facts, ruled-out sets, and tail
            # are all left untouched and it can never trigger a contradiction.
            before_mass = sum(hypothesis.probability for hypothesis in before)
            entry = EvidenceLedgerEntry(
                evidence=evidence,
                support_before=len(before),
                support_after=len(before),
                mass_before=before_mass,
                mass_after=before_mass,
                contradiction=False,
                source_covered=True,
                current_state_only=True,
            )
            return replace(
                self,
                evidence_ledger=(*self.evidence_ledger, entry),
                last_public_event_index=evidence.event_index,
            )

        confirmed = _confirmed_with(self.confirmed, evidence)

        if not _dimension_covered(before, evidence.kind):
            # The pinned source does not model this attribute for any hypothesis
            # (e.g. items in the Randbats role data, or any reveal on a
            # missing-species belief).  Record the public fact without filtering
            # or contradicting the unrelated role/ability/move/Tera posterior;
            # the explicit unknown tail is preserved unchanged.
            before_mass = sum(hypothesis.probability for hypothesis in before)
            entry = EvidenceLedgerEntry(
                evidence=evidence,
                support_before=len(before),
                support_after=len(before),
                mass_before=before_mass,
                mass_after=before_mass,
                contradiction=False,
                source_covered=False,
            )
            return replace(
                self,
                confirmed=confirmed,
                evidence_ledger=(*self.evidence_ledger, entry),
                last_public_event_index=evidence.event_index,
            )

        compatible = tuple(
            hypothesis
            for hypothesis in before
            if _hypothesis_matches(hypothesis, evidence)
        )
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
            source_covered=True,
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
        prior_source_key=prior.source_species_key,
        prior_alias_policy_version=prior.alias_policy_version,
        prior_joint_quality=prior.joint_quality.value,
        prior_coverage_warnings=prior.coverage_warnings,
    )


def _dimension_covered(
    hypotheses: Sequence[SetHypothesis], kind: EvidenceKind
) -> bool:
    """Whether the prior models the evidence's attribute for any hypothesis.

    A dimension is source-covered when at least one concrete hypothesis carries
    a value for it.  When no hypothesis does (items in the Randbats role data, or
    any reveal on a missing-species belief), the source simply does not know the
    attribute, so a reveal must be recorded as a public fact rather than treated
    as a contradiction of the role/ability/move/Tera hypotheses.
    """
    if kind == EvidenceKind.MOVE_REVEALED:
        return any(hypothesis.moves for hypothesis in hypotheses)
    if kind == EvidenceKind.ABILITY_REVEALED:
        return any(hypothesis.ability for hypothesis in hypotheses)
    if kind == EvidenceKind.ITEM_REVEALED:
        return any(hypothesis.item for hypothesis in hypotheses)
    if kind == EvidenceKind.TERA_TYPE_REVEALED:
        return any(hypothesis.tera_type for hypothesis in hypotheses)
    raise ValueError(f"Unsupported public evidence kind: {kind!r}")


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
    transformed: set[str] = set()
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
        position = subject.split(":", 1)[0].strip()
        if command in {"switch", "drag"}:
            # A fresh switch-in reverts any Transform copied state at this slot.
            transformed.discard(position)
            continue
        copied_slot = position in transformed
        from_ability = re.search(r"\[from\]\s*ability:\s*([^|\]]+)", raw, re.I)
        from_item = re.search(r"\[from\]\s*item:\s*([^|\]]+)", raw, re.I)
        trace_copy = bool(from_ability and is_copied_ability_marker(from_ability.group(1)))
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
                    current_state_only=copied_slot or is_universal_noise_move(parts[3]),
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
                    current_state_only=(
                        copied_slot
                        or trace_copy
                        or is_forme_state_ability(parts[3])
                    ),
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
                is_ability = activation.group(1).lower() == "ability"
                kind = (
                    EvidenceKind.ABILITY_REVEALED
                    if is_ability
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
                        current_state_only=(
                            copied_slot
                            or (is_ability and is_forme_state_ability(activation.group(2)))
                        ),
                    )
                )
        if command == "-transform":
            # Mark after this line so the row's own `[from] ability: Imposter`
            # stays base evidence; copied moves/abilities arrive on later lines.
            transformed.add(position)
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
