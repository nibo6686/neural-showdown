"""Source-neutral meta-prior contracts for opponent set beliefs.

This module contains no Randbats/Smogon ingestion and no model features.  It
defines the immutable prior representation plus a tiny fixture source used by
tests.  Consumers receive joint set hypotheses; marginals are derived later.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple


PRIOR_SCHEMA_VERSION = "meta-prior-v1"


def canonical_id(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def _canonical_tuple(values: Sequence[Any]) -> Tuple[str, ...]:
    return tuple(sorted({canonical_id(value) for value in values if canonical_id(value)}))


class SourceKind(str, Enum):
    RANDBATS_GENERATOR = "randbats_generator"
    SMOGON_USAGE = "smogon_usage"
    REPLAY_EMPIRICAL = "replay_empirical"
    FIXTURE = "fixture"


class JointQuality(str, Enum):
    EXACT = "exact"
    SAMPLED = "sampled"
    RECONSTRUCTED = "reconstructed"
    FACTORIZED = "factorized"


@dataclass(frozen=True)
class MetaPriorMetadata:
    source_kind: SourceKind
    source_version: str
    source_sha256: str
    generated_at_utc: str
    format_id: str
    source_locator: str = ""
    adapter_version: str = ""
    data_version: Optional[str] = None
    effective_from: Optional[str] = None
    effective_through: Optional[str] = None
    sample_count: int = 0
    species_key_policy: str = "showdown_id"
    mechanics_catalog_version: str = "unspecified"
    prior_schema_version: str = PRIOR_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.source_version:
            raise ValueError("Meta-prior source_version is required.")
        if not re.fullmatch(r"[0-9a-f]{64}", self.source_sha256):
            raise ValueError("Meta-prior source_sha256 must be a lowercase SHA-256 hex digest.")
        if not canonical_id(self.format_id):
            raise ValueError("Meta-prior format_id is required.")
        if self.sample_count < 0:
            raise ValueError("Meta-prior sample_count cannot be negative.")


@dataclass(frozen=True)
class SetHypothesis:
    hypothesis_id: str
    probability: float
    ability: Optional[str] = None
    item: Optional[str] = None
    moves: Tuple[str, ...] = ()
    tera_type: Optional[str] = None
    roles: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.hypothesis_id:
            raise ValueError("Set hypothesis_id is required.")
        probability = float(self.probability)
        if not math.isfinite(probability) or probability < 0.0:
            raise ValueError("Set hypothesis probability must be finite and non-negative.")
        object.__setattr__(self, "probability", probability)
        object.__setattr__(self, "ability", canonical_id(self.ability) or None)
        object.__setattr__(self, "item", canonical_id(self.item) or None)
        object.__setattr__(self, "moves", _canonical_tuple(self.moves))
        object.__setattr__(self, "tera_type", canonical_id(self.tera_type) or None)
        object.__setattr__(self, "roles", _canonical_tuple(self.roles))


@dataclass(frozen=True)
class SetPrior:
    species_form_key: str
    hypotheses: Tuple[SetHypothesis, ...]
    other_mass: float = 0.0
    joint_quality: JointQuality = JointQuality.EXACT
    coverage_warnings: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "species_form_key", canonical_id(self.species_form_key))
        object.__setattr__(self, "hypotheses", tuple(self.hypotheses))
        object.__setattr__(self, "coverage_warnings", tuple(self.coverage_warnings))
        if not self.species_form_key:
            raise ValueError("Set prior species_form_key is required.")
        if len({hypothesis.hypothesis_id for hypothesis in self.hypotheses}) != len(
            self.hypotheses
        ):
            raise ValueError("Set prior hypothesis IDs must be unique.")
        other_mass = float(self.other_mass)
        if not math.isfinite(other_mass) or not 0.0 <= other_mass <= 1.0:
            raise ValueError("Set prior other_mass must be finite and within [0, 1].")
        object.__setattr__(self, "other_mass", other_mass)
        total = sum(hypothesis.probability for hypothesis in self.hypotheses) + other_mass
        if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1.0e-9):
            raise ValueError(f"Set prior probability mass must sum to 1, got {total}.")

    @property
    def support_size(self) -> int:
        return len(self.hypotheses)


class MetaPriorSource(ABC):
    """Interface implemented later by Randbats, Smogon, or replay sources."""

    @property
    @abstractmethod
    def metadata(self) -> MetaPriorMetadata:
        raise NotImplementedError

    @abstractmethod
    def prior_for(
        self,
        format_id: str,
        species_form_key: str,
        context: Optional[Mapping[str, Any]] = None,
    ) -> Optional[SetPrior]:
        raise NotImplementedError


def _fixture_payload(priors: Mapping[str, SetPrior]) -> Dict[str, Any]:
    return {
        key: {
            **asdict(prior),
            "joint_quality": prior.joint_quality.value,
            "hypotheses": [asdict(hypothesis) for hypothesis in prior.hypotheses],
        }
        for key, prior in sorted(priors.items())
    }


class FixtureMetaPriorSource(MetaPriorSource):
    """Deterministic in-memory source for contract and no-leakage tests."""

    def __init__(
        self,
        *,
        format_id: str,
        priors: Mapping[str, SetPrior],
        source_version: str = "fixture-v1",
        generated_at_utc: str = "2000-01-01T00:00:00Z",
    ) -> None:
        normalized = {canonical_id(key): value for key, value in priors.items()}
        for key, prior in normalized.items():
            if key != prior.species_form_key:
                raise ValueError(
                    f"Fixture prior key {key!r} does not match {prior.species_form_key!r}."
                )
        payload = {
            "format_id": canonical_id(format_id),
            "source_version": source_version,
            "priors": _fixture_payload(normalized),
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self._priors = normalized
        self._metadata = MetaPriorMetadata(
            source_kind=SourceKind.FIXTURE,
            source_version=source_version,
            source_sha256=digest,
            generated_at_utc=generated_at_utc,
            format_id=canonical_id(format_id),
            sample_count=sum(prior.support_size for prior in normalized.values()),
            mechanics_catalog_version="fixture",
        )

    @property
    def metadata(self) -> MetaPriorMetadata:
        return self._metadata

    def prior_for(
        self,
        format_id: str,
        species_form_key: str,
        context: Optional[Mapping[str, Any]] = None,
    ) -> Optional[SetPrior]:
        del context
        if canonical_id(format_id) != canonical_id(self.metadata.format_id):
            raise ValueError(
                f"Meta-prior format mismatch: expected {self.metadata.format_id!r}, "
                f"got {canonical_id(format_id)!r}."
            )
        return self._priors.get(canonical_id(species_form_key))
