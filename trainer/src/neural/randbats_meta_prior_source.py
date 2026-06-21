"""Pinned adapter for the repository's existing Gen 9 Randbats role data.

The checked-in ``sets.json`` contains role declarations and movepools, not
sampled complete sets.  This adapter therefore reports factorized quality,
keeps an explicit unknown tail, and never claims item or exact four-move-set
knowledge that the source does not contain.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

from .live_opponent_beliefs import load_randbats_index
from .meta_prior import (
    JointQuality,
    MetaPriorMetadata,
    MetaPriorSource,
    SetHypothesis,
    SetPrior,
    SourceKind,
    canonical_id,
)


RANDBATS_META_PRIOR_ADAPTER_VERSION = "randbats-role-data-adapter-v1"
DEFAULT_FORMAT_ID = "gen9randombattle"
DEFAULT_UNKNOWN_TAIL_MASS = 0.5


class RandbatsMetaPriorSource(MetaPriorSource):
    """Wrap the old shortcut's pinned role/movepool source as a prior source."""

    def __init__(
        self,
        *,
        format_id: str = DEFAULT_FORMAT_ID,
        sets_path: Optional[str] = None,
        unknown_tail_mass: float = DEFAULT_UNKNOWN_TAIL_MASS,
    ) -> None:
        format_key = canonical_id(format_id)
        if format_key != DEFAULT_FORMAT_ID:
            raise ValueError(
                f"Randbats source supports only {DEFAULT_FORMAT_ID!r}, "
                f"got {format_key!r}."
            )
        tail = float(unknown_tail_mass)
        if not 0.0 < tail < 1.0:
            raise ValueError(
                "Randbats role-data unknown_tail_mass must be within (0, 1)."
            )
        if sets_path and not Path(sets_path).exists():
            raise FileNotFoundError(
                f"Configured Randbats sets path does not exist: {sets_path}"
            )

        index, selected_path, warnings = load_randbats_index(sets_path=sets_path)
        if selected_path == "missing":
            raise FileNotFoundError(
                "; ".join(warnings) or "Randbats sets source is missing."
            )
        path = Path(selected_path).resolve()
        payload = path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()

        self._index = index
        self._source_path = path
        self._source_locator = _stable_source_locator(path)
        self._unknown_tail_mass = tail
        self._metadata = MetaPriorMetadata(
            source_kind=SourceKind.RANDBATS_GENERATOR,
            source_version=f"checked-in-gen9-role-data:{digest[:16]}",
            source_sha256=digest,
            generated_at_utc="unspecified",
            format_id=DEFAULT_FORMAT_ID,
            source_locator=self._source_locator,
            adapter_version=RANDBATS_META_PRIOR_ADAPTER_VERSION,
            data_version=f"sha256:{digest}",
            sample_count=0,
            mechanics_catalog_version="pokemon-showdown-gen9-randbats-role-data",
        )

    @property
    def metadata(self) -> MetaPriorMetadata:
        return self._metadata

    @property
    def source_path(self) -> Path:
        return self._source_path

    def prior_for(
        self,
        format_id: str,
        species_form_key: str,
        context: Optional[Mapping[str, Any]] = None,
    ) -> Optional[SetPrior]:
        del context
        format_key = canonical_id(format_id)
        if format_key != self.metadata.format_id:
            raise ValueError(
                f"Meta-prior format mismatch: expected {self.metadata.format_id!r}, "
                f"got {format_key!r}."
            )
        species_key = canonical_id(species_form_key)
        candidates = self._index.get(species_key)
        if not candidates:
            return None
        return _prior_from_role_candidates(
            species_key,
            candidates,
            unknown_tail_mass=self._unknown_tail_mass,
        )


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _stable_source_locator(path: Path) -> str:
    try:
        return path.relative_to(_repo_root()).as_posix()
    except ValueError:
        return path.as_posix()


def _nonempty(values: Any) -> Tuple[str, ...]:
    if not isinstance(values, list):
        return ()
    return tuple(
        sorted({canonical_id(value) for value in values if canonical_id(value)})
    )


def _prior_from_role_candidates(
    species_key: str,
    candidates: List[Dict[str, Any]],
    *,
    unknown_tail_mass: float,
) -> SetPrior:
    expansions: List[Tuple[int, str, str, str, Tuple[str, ...]]] = []
    warnings = {
        "role_declarations_are_not_complete_generated_sets",
        "movepool_is_not_an_exact_four_move_set",
        "items_absent_from_existing_role_data",
        "role_weights_unavailable_equal_weight_assumption",
        f"unvalidated_unknown_tail_policy:{unknown_tail_mass:g}",
    }

    for candidate_index, candidate in enumerate(candidates):
        abilities = _nonempty(candidate.get("abilities")) or ("",)
        tera_types = _nonempty(candidate.get("tera_types")) or ("",)
        moves = _nonempty(candidate.get("moves"))
        role = canonical_id(candidate.get("role"))
        if len(abilities) > 1 or len(tera_types) > 1:
            warnings.add("ability_tera_alternatives_factorized_uniformly")
        for ability in abilities:
            for tera_type in tera_types:
                expansions.append((candidate_index, role, ability, tera_type, moves))

    if not expansions:
        return SetPrior(
            species_form_key=species_key,
            hypotheses=(),
            other_mass=1.0,
            joint_quality=JointQuality.FACTORIZED,
            coverage_warnings=tuple(sorted(warnings | {"no_usable_role_declarations"})),
        )

    represented_mass = 1.0 - unknown_tail_mass
    role_weights: Dict[int, float] = {}
    for candidate_index, *_ in expansions:
        role_weights[candidate_index] = float(
            candidates[candidate_index].get("weight", 1.0)
        )
    total_role_weight = sum(role_weights.values()) or 1.0
    expansion_counts: Dict[int, int] = {}
    for candidate_index, *_ in expansions:
        expansion_counts[candidate_index] = expansion_counts.get(candidate_index, 0) + 1

    hypotheses = []
    for candidate_index, role, ability, tera_type, moves in expansions:
        role_mass = represented_mass * role_weights[candidate_index] / total_role_weight
        probability = role_mass / expansion_counts[candidate_index]
        hypotheses.append(
            SetHypothesis(
                hypothesis_id=(
                    f"role-{candidate_index}:{role or 'unspecified'}:"
                    f"{ability or 'unknown'}:{tera_type or 'unknown'}"
                ),
                probability=probability,
                ability=ability or None,
                item=None,
                moves=moves,
                tera_type=tera_type or None,
                roles=(role,) if role else (),
            )
        )

    return SetPrior(
        species_form_key=species_key,
        hypotheses=tuple(hypotheses),
        other_mass=unknown_tail_mass,
        joint_quality=JointQuality.FACTORIZED,
        coverage_warnings=tuple(sorted(warnings)),
    )
