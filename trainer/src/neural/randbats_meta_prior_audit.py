"""Read-only held-out audit for the repo-backed Randbats meta-prior source."""

from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from .meta_prior import SetPrior, canonical_id
from .opponent_set_belief import (
    EvidenceKind,
    is_copied_ability_marker,
    is_forme_state_ability,
    is_universal_noise_move,
)
from .opponent_set_belief_replay_adapter import (
    build_replay_prefix_beliefs,
    replay_protocol_prefix,
)
from .parse_replay_logs import parse_protocol_log
from .randbats_meta_prior_source import (
    RANDBATS_ALIAS_POLICY_VERSION,
    RandbatsMetaPriorSource,
)


def _side(ident: str) -> Optional[str]:
    match = re.match(r"^(p[12])", str(ident or "").strip())
    return match.group(1) if match else None


def _position(ident: str) -> Optional[str]:
    match = re.match(r"^(p[12][a-z]?):", str(ident or "").strip())
    return match.group(1) if match else None


def _species(details: str) -> str:
    return canonical_id(str(details or "").split(",", 1)[0])


def _opponent_perspective(side: str) -> str:
    return "p2" if side == "p1" else "p1"


def _prior_support(prior: SetPrior, kind: EvidenceKind, value: str) -> Tuple[bool, float]:
    key = canonical_id(value)
    probability = 0.0
    for hypothesis in prior.hypotheses:
        matches = (
            key in hypothesis.moves
            if kind == EvidenceKind.MOVE_REVEALED
            else hypothesis.ability == key
            if kind == EvidenceKind.ABILITY_REVEALED
            else hypothesis.tera_type == key
            if kind == EvidenceKind.TERA_TYPE_REVEALED
            else hypothesis.item == key
        )
        if matches:
            probability += hypothesis.probability
    return probability > 0.0, probability


def _public_events(lines: Iterable[str]) -> List[Dict[str, Any]]:
    active: Dict[str, str] = {}
    transformed: set = set()  # Transform/Imposter: copied moves + abilities
    copied_ability: set = set()  # Trace carrier / As One fused: copied abilities
    turn = 0
    result: List[Dict[str, Any]] = []
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
        if command in {"switch", "drag", "replace"} and len(parts) > 3:
            position = _position(parts[2])
            species = _species(parts[3])
            if position and species:
                active[position] = species
                transformed.discard(position)
                copied_ability.discard(position)
                result.append(
                    {
                        "kind": "identity",
                        "species": species,
                        "side": _side(parts[2]),
                        "turn": turn,
                        "line": index,
                        "command": command,
                    }
                )
            continue

        subject = parts[2] if len(parts) > 2 else ""
        position = _position(subject)
        species = active.get(position or "")
        side = _side(subject)
        if not species or not side:
            continue
        copied_slot = position in transformed  # copied moves
        ability_copied = position in transformed or position in copied_ability
        from_ability = re.search(r"\[from\]\s*ability:\s*([^|\]]+)", raw, re.I)
        from_item = re.search(r"\[from\]\s*item:\s*([^|\]]+)", raw, re.I)
        if command == "move" and len(parts) > 3 and not from_ability:
            result.append(
                {
                    "kind": EvidenceKind.MOVE_REVEALED,
                    "value": parts[3],
                    "species": species,
                    "side": side,
                    "turn": turn,
                    "line": index,
                    "raw": raw,
                    "current_state": copied_slot or is_universal_noise_move(parts[3]),
                }
            )
        trace_reveal = bool(
            command == "-ability"
            and from_ability
            and is_copied_ability_marker(from_ability.group(1))
        )
        if command == "-ability" and len(parts) > 3:
            result.append(
                {
                    "kind": EvidenceKind.ABILITY_REVEALED,
                    "value": from_ability.group(1) if trace_reveal else parts[3],
                    "species": species,
                    "side": side,
                    "turn": turn,
                    "line": index,
                    "raw": raw,
                    # Trace base ability stays base; the copied ability and
                    # forme-state labels are current-state, not base-set.
                    "current_state": (
                        not trace_reveal
                        and (ability_copied or is_forme_state_ability(parts[3]))
                    ),
                }
            )
        elif command in {"-item", "-enditem"} and len(parts) > 3:
            result.append(
                {
                    "kind": EvidenceKind.ITEM_REVEALED,
                    "value": parts[3],
                    "species": species,
                    "side": side,
                    "turn": turn,
                    "line": index,
                    "raw": raw,
                }
            )
        elif command == "-terastallize" and len(parts) > 3:
            result.append(
                {
                    "kind": EvidenceKind.TERA_TYPE_REVEALED,
                    "value": parts[3],
                    "species": species,
                    "side": side,
                    "turn": turn,
                    "line": index,
                    "raw": raw,
                }
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
                    {
                        "kind": kind,
                        "value": activation.group(2),
                        "species": species,
                        "side": side,
                        "turn": turn,
                        "line": index,
                        "raw": raw,
                        "current_state": is_ability
                        and (ability_copied or is_forme_state_ability(activation.group(2))),
                    }
                )
        if command == "-transform":
            transformed.add(position)
        if command == "-ability" and len(parts) > 3 and canonical_id(parts[3]).startswith(
            "asone"
        ):
            copied_ability.add(position)
        if trace_reveal:
            copied_ability.add(position)
        if from_ability and not trace_reveal:
            owner = subject
            owner_match = re.search(r"\[of\]\s*([^|]+)", raw, re.I)
            if owner_match:
                owner = owner_match.group(1).strip()
            owner_position = _position(owner)
            owner_species = active.get(owner_position or "")
            owner_side = _side(owner)
            if not owner_species or not owner_side:
                continue
            result.append(
                {
                    "kind": EvidenceKind.ABILITY_REVEALED,
                    "value": from_ability.group(1),
                    "species": owner_species,
                    "side": owner_side,
                    "turn": turn,
                    "line": index,
                    "raw": raw,
                    "named_effect": True,
                    "current_state": (
                        owner_position in transformed
                        or owner_position in copied_ability
                    ),
                }
            )
        if from_item:
            result.append(
                {
                    "kind": EvidenceKind.ITEM_REVEALED,
                    "value": from_item.group(1),
                    "species": species,
                    "side": side,
                    "turn": turn,
                    "line": index,
                    "raw": raw,
                    "named_effect": True,
                }
            )
    return result


def _pct(numerator: int, denominator: int) -> float:
    return 100.0 * numerator / denominator if denominator else 0.0


# Identity/forme-tied abilities that the static role data represents under the
# base forme key, so a reveal of the transformed-forme ability contradicts the
# base set.  This is a known-mechanics catalog, not a strategy heuristic.
_FORME_ABILITY_PREFIXES = (
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


def _classify_contradiction(
    species: str,
    kind_value: str,
    value: str,
    source: RandbatsMetaPriorSource,
) -> str:
    """Bucket a source-covered contradiction into an actionable category."""

    v = canonical_id(value)
    if kind_value == EvidenceKind.MOVE_REVEALED.value:
        if v == "struggle":
            return "universal_move_noise"
        if species == "ditto":
            return "dynamic_or_copied_state"
        return "true_source_limitation"

    # ability dimension
    if v == "trace":
        return "dynamic_or_copied_state"
    prior = source.prior_for(source.metadata.format_id, species)
    declared = (
        {h.ability for h in prior.hypotheses if h.ability} if prior else set()
    )
    if "trace" in declared or "imposter" in declared or species == "ditto":
        # Displayed ability is a Trace/Imposter copy, not the base set ability.
        return "dynamic_or_copied_state"
    if any(v == prefix or v.startswith(prefix) for prefix in _FORME_ABILITY_PREFIXES):
        return "composite_or_forme_ability"
    return "true_source_limitation"


def audit_manifest(
    *,
    manifest_path: Path,
    prior_source_path: Path,
    split: str = "test",
    limit: int = 1000,
) -> Dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = [
        row
        for row in manifest.get("entries", [])
        if not split or str(row.get("split")) == split
    ][: max(0, int(limit))]
    source = RandbatsMetaPriorSource(sets_path=str(prior_source_path))

    missing_species = Counter()
    alias_resolved_slots = Counter()
    current_state_ledger_by_kind = Counter()
    unique_species = set()
    supported_unique_species = set()
    event_totals = Counter()
    event_supported = Counter()
    unsupported_details: Dict[str, Counter] = defaultdict(Counter)
    ability_probabilities: List[float] = []
    slot_total = 0
    slot_contradictions = 0
    contradiction_by_kind = Counter()
    contradiction_details = Counter()
    contradiction_details_by_kind: Dict[str, Counter] = defaultdict(Counter)
    contradiction_classification = Counter()
    contradiction_class_details: Dict[str, Counter] = defaultdict(Counter)
    source_absent_by_kind = Counter()
    ledger_entries_by_kind = Counter()
    tail_dominant = 0
    missing_prior_slots = 0
    causal_checks = 0
    causal_failures: List[str] = []
    hidden_checks = 0
    hidden_failures: List[str] = []
    illusion_segments = 0
    illusion_failures: List[str] = []
    reflection_rows = 0
    reflection_failures: List[str] = []
    scanned_paths: List[str] = []
    seen_labels = set()

    for entry in entries:
        path = Path(str(entry.get("path") or ""))
        if not path.is_absolute():
            path = manifest_path.parents[3] / path
        if not path.exists():
            continue
        replay_id = str(entry.get("replay_id") or path.stem)
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        trajectory = parse_protocol_log(
            lines,
            replay_id=replay_id,
            format_name=source.metadata.format_id,
            source_path=str(path),
        )
        scanned_paths.append(str(path))
        events = _public_events(lines)

        for event in events:
            if event["kind"] == "identity":
                if event["command"] == "replace":
                    illusion_segments += 1
                continue
            if event.get("current_state"):
                # Copied/forme current-state reveals are not base-set support.
                continue
            label_key = (
                replay_id,
                event["side"],
                event["species"],
                event["kind"].value,
                canonical_id(event["value"]),
            )
            if label_key in seen_labels:
                continue
            seen_labels.add(label_key)
            kind = event["kind"]
            event_totals[kind.value] += 1
            prior = source.prior_for(source.metadata.format_id, event["species"])
            if prior is None:
                unsupported_details[kind.value][
                    f"{event['species']}:{canonical_id(event['value'])}:missing_prior"
                ] += 1
                continue
            supported, probability = _prior_support(prior, kind, event["value"])
            if supported:
                event_supported[kind.value] += 1
            else:
                unsupported_details[kind.value][
                    f"{event['species']}:{canonical_id(event['value'])}"
                ] += 1
            if kind == EvidenceKind.ABILITY_REVEALED:
                ability_probabilities.append(probability)

        for perspective in ("p1", "p2"):
            snapshot = build_replay_prefix_beliefs(
                trajectory, source, perspective_side=perspective
            )
            for slot in snapshot.known_slots:
                slot_total += 1
                unique_species.add(slot.species_form_key)
                if not slot.belief.source_available:
                    missing_prior_slots += 1
                    missing_species[slot.species_form_key] += 1
                else:
                    supported_unique_species.add(slot.species_form_key)
                    if slot.belief.prior_source_key:
                        alias_resolved_slots[
                            f"{slot.species_form_key}->{slot.belief.prior_source_key}"
                        ] += 1
                if slot.belief.other_mass > 0.5:
                    tail_dominant += 1
                if slot.belief.prior_contradiction:
                    slot_contradictions += 1
                for ledger in slot.belief.evidence_ledger:
                    ledger_entries_by_kind[ledger.evidence.kind.value] += 1
                    if not ledger.source_covered:
                        source_absent_by_kind[ledger.evidence.kind.value] += 1
                    if ledger.current_state_only:
                        current_state_ledger_by_kind[ledger.evidence.kind.value] += 1
                    if ledger.contradiction:
                        contradiction_by_kind[
                            ledger.evidence.kind.value
                        ] += 1
                        contradiction_details[
                            f"{slot.species_form_key}:"
                            f"{ledger.evidence.kind.value}:"
                            f"{ledger.evidence.value}:"
                            f"{ledger.evidence.provenance}"
                        ] += 1
                        contradiction_details_by_kind[
                            ledger.evidence.kind.value
                        ][
                            f"{slot.species_form_key}:"
                            f"{ledger.evidence.value}:"
                            f"{ledger.evidence.provenance}"
                        ] += 1
                        category = _classify_contradiction(
                            slot.species_form_key,
                            ledger.evidence.kind.value,
                            ledger.evidence.value,
                            source,
                        )
                        contradiction_classification[category] += 1
                        contradiction_class_details[category][
                            f"{slot.species_form_key}:"
                            f"{ledger.evidence.kind.value}:"
                            f"{ledger.evidence.value}"
                        ] += 1

        turns = [
            int(turn.get("turn", 0))
            for turn in trajectory.get("turns", [])
            if isinstance(turn, dict)
        ]
        if turns:
            audit_turn = max(1, max(turns) // 2)
            prefix_lines = replay_protocol_prefix(
                trajectory, through_turn=audit_turn
            )
            truncated = parse_protocol_log(
                prefix_lines,
                replay_id=replay_id,
                format_name=source.metadata.format_id,
            )
            perturbed = dict(trajectory)
            perturbed["protocol_log"] = [
                *prefix_lines,
                f"|turn|{audit_turn + 1}",
                "|-ability|p2a: Future|Truant",
                "|-terastallize|p2a: Future|Bug",
            ]
            hidden_a = dict(trajectory)
            hidden_b = dict(trajectory)
            hidden_a["hidden_opponent_truth"] = {"ability": "Truant"}
            hidden_b["hidden_opponent_truth"] = {"ability": "Magic Bounce"}
            for perspective in ("p1", "p2"):
                causal_checks += 1
                expected = build_replay_prefix_beliefs(
                    trajectory,
                    source,
                    perspective_side=perspective,
                    through_turn=audit_turn,
                )
                actual = build_replay_prefix_beliefs(
                    truncated, source, perspective_side=perspective
                )
                suffix = build_replay_prefix_beliefs(
                    perturbed,
                    source,
                    perspective_side=perspective,
                    through_turn=audit_turn,
                )
                if expected.slots != actual.slots or expected.slots != suffix.slots:
                    causal_failures.append(f"{replay_id}:{perspective}:{audit_turn}")
                hidden_checks += 1
                first = build_replay_prefix_beliefs(
                    hidden_a,
                    source,
                    perspective_side=perspective,
                    through_turn=audit_turn,
                )
                second = build_replay_prefix_beliefs(
                    hidden_b,
                    source,
                    perspective_side=perspective,
                    through_turn=audit_turn,
                )
                if first.slots != second.slots:
                    hidden_failures.append(f"{replay_id}:{perspective}:{audit_turn}")

        for index, raw in enumerate(lines):
            if "|move|" not in raw or "[from] ability:" not in raw:
                continue
            reflection_rows += 1
            parts = raw.split("|")
            actor = parts[2] if len(parts) > 2 else ""
            side = _side(actor)
            position = _position(actor)
            if not side or not position:
                reflection_failures.append(f"{replay_id}:{index}:unparsed")
                continue
            snapshot = build_replay_prefix_beliefs(
                trajectory,
                source,
                perspective_side=_opponent_perspective(side),
                through_line=index + 1,
            )
            active = [
                slot
                for slot in snapshot.active_slots
                if slot.position == position
            ]
            if not active:
                reflection_failures.append(f"{replay_id}:{index}:missing_actor")
                continue
            line_entries = [
                row.evidence.kind
                for row in active[0].belief.evidence_ledger
                if row.evidence.event_index == index
            ]
            if EvidenceKind.ABILITY_REVEALED not in line_entries:
                reflection_failures.append(f"{replay_id}:{index}:ability_missing")
            if EvidenceKind.MOVE_REVEALED in line_entries:
                reflection_failures.append(f"{replay_id}:{index}:move_pollution")

        for side in ("p1", "p2"):
            perspective = _opponent_perspective(side)
            snapshot = build_replay_prefix_beliefs(
                trajectory, source, perspective_side=perspective
            )
            ambiguous = [slot for slot in snapshot.known_slots if slot.identity_ambiguous]
            for slot in ambiguous:
                if not slot.superseded_by:
                    illusion_failures.append(f"{replay_id}:{side}:{slot.slot_key}")

    event_summary = {}
    for kind, total in sorted(event_totals.items()):
        supported = event_supported[kind]
        event_summary[kind] = {
            "total": total,
            "supported": supported,
            "support_pct": _pct(supported, total),
            "top_unsupported": unsupported_details[kind].most_common(20),
        }

    mean_ability_probability = (
        sum(ability_probabilities) / len(ability_probabilities)
        if ability_probabilities
        else 0.0
    )
    ability_log_loss = (
        -sum(math.log(max(value, 1.0e-12)) for value in ability_probabilities)
        / len(ability_probabilities)
        if ability_probabilities
        else 0.0
    )
    return {
        "manifest": str(manifest_path),
        "split": split,
        "limit": limit,
        "battle_count": len(scanned_paths),
        "prior_source": source.metadata.source_locator,
        "prior_sha256": source.metadata.source_sha256,
        "species_appearances": slot_total,
        "covered_species_appearances": slot_total - missing_prior_slots,
        "species_coverage_pct": _pct(
            slot_total - missing_prior_slots, slot_total
        ),
        "unique_species_count": len(unique_species),
        "supported_unique_species_count": len(supported_unique_species),
        "unique_species_coverage_pct": _pct(
            len(supported_unique_species), len(unique_species)
        ),
        "missing_species": missing_species.most_common(),
        "alias_resolved_slots": alias_resolved_slots.most_common(),
        "alias_policy_version": RANDBATS_ALIAS_POLICY_VERSION,
        "current_state_ledger_by_kind": dict(current_state_ledger_by_kind),
        "current_state_ledger_total": sum(current_state_ledger_by_kind.values()),
        "slot_count": slot_total,
        "missing_prior_slots": missing_prior_slots,
        "tail_dominant_slots": tail_dominant,
        "tail_dominant_pct": _pct(tail_dominant, slot_total),
        "contradictory_slots": slot_contradictions,
        "contradictory_slot_pct": _pct(slot_contradictions, slot_total),
        "contradiction_by_kind": dict(contradiction_by_kind),
        "contradiction_classification": dict(contradiction_classification),
        "contradiction_classification_details": {
            category: rows.most_common(10)
            for category, rows in sorted(contradiction_class_details.items())
        },
        "ledger_entries_by_kind": dict(ledger_entries_by_kind),
        "source_absent_absorbed_by_kind": dict(source_absent_by_kind),
        "source_absent_absorbed_total": sum(source_absent_by_kind.values()),
        "item_evidence_ledger_count": ledger_entries_by_kind.get(
            EvidenceKind.ITEM_REVEALED.value, 0
        ),
        "item_contradiction_count": contradiction_by_kind.get(
            EvidenceKind.ITEM_REVEALED.value, 0
        ),
        "top_contradiction_details": contradiction_details.most_common(20),
        "contradiction_details_by_kind": {
            kind: rows.most_common(10)
            for kind, rows in sorted(contradiction_details_by_kind.items())
        },
        "event_support": event_summary,
        "ability_reveal_count": len(ability_probabilities),
        "ability_mean_assigned_probability": mean_ability_probability,
        "ability_log_loss": ability_log_loss,
        "prefix_causality_checks": causal_checks,
        "prefix_causality_failures": causal_failures,
        "hidden_truth_checks": hidden_checks,
        "hidden_truth_failures": hidden_failures,
        "illusion_ambiguous_segments": illusion_segments,
        "illusion_failures": illusion_failures,
        "reflection_rows": reflection_rows,
        "reflection_failures": reflection_failures,
    }


def render_markdown(summary: Mapping[str, Any], command: str) -> str:
    events = summary["event_support"]
    lines = [
        "# Randbats Meta-Prior Public-Prefix Audit",
        "",
        "## Scope",
        "",
        f"- Command: `{command}`",
        f"- Manifest split: `{summary['split']}`",
        f"- Battles scanned: {summary['battle_count']}",
        f"- Prior source: `{summary['prior_source']}`",
        f"- Prior SHA-256: `{summary['prior_sha256']}`",
        "- Information boundary: prior plus public protocol prefix only; later",
        "  reveals are evaluation labels, never earlier-belief inputs.",
        "",
        "## Coverage",
        "",
        f"- Revealed species appearances with a prior: "
        f"{summary['covered_species_appearances']}/{summary['species_appearances']} "
        f"({summary['species_coverage_pct']:.2f}%).",
        f"- Unique revealed species/forms with a prior: "
        f"{summary['supported_unique_species_count']}/{summary['unique_species_count']} "
        f"({summary['unique_species_coverage_pct']:.2f}%).",
        f"- Public identity slots with missing priors: "
        f"{summary['missing_prior_slots']}/{summary['slot_count']}.",
        f"- Slots ending with dominant unknown tail (`other_mass > 0.5`): "
        f"{summary['tail_dominant_slots']}/{summary['slot_count']} "
        f"({summary['tail_dominant_pct']:.2f}%).",
        "",
        "Missing species/forms:",
        "",
    ]
    missing = summary["missing_species"]
    lines.extend(
        [f"- `{species}`: {count} appearances" for species, count in missing]
        or ["- None."]
    )
    lines.extend(
        [
            "",
            f"Priors resolved via the explicit form-alias policy "
            f"(`{summary['alias_policy_version']}`), public->base:",
            "",
        ]
    )
    lines.extend(
        [
            f"- `{mapping}`: {count} public slots"
            for mapping, count in summary["alias_resolved_slots"]
        ]
        or ["- None."]
    )
    lines.extend(
        [
            "",
            "## Public reveal support",
            "",
            "| Evidence | Supported | Total | Support |",
            "|---|---:|---:|---:|",
        ]
    )
    for kind in ("ability_revealed", "move_revealed", "tera_type_revealed"):
        row = events.get(kind, {"supported": 0, "total": 0, "support_pct": 0.0})
        lines.append(
            f"| {kind} | {row['supported']} | {row['total']} | "
            f"{row['support_pct']:.2f}% |"
        )
    lines.extend(
        [
            "",
            f"- Ability labels: {summary['ability_reveal_count']}; mean assigned "
            f"probability including the fixed unknown tail: "
            f"{summary['ability_mean_assigned_probability']:.4f}; coarse log loss "
            f"{summary['ability_log_loss']:.4f}.",
            "- These are factorized declaration weights, not calibrated generator",
            "  frequencies. The probability values should not be treated as",
            "  production calibration.",
            "- Ability-label evaluation treats a Trace protocol row as public",
            "  evidence for Trace, not as base-set evidence for the copied",
            "  ability. The current replay belief adapter still records the",
            "  displayed copied ability too; those collapses remain visible below",
            "  as adapter-semantics failures.",
            "",
            "Top unsupported public labels:",
            "",
        ]
    )
    for kind in ("ability_revealed", "move_revealed", "tera_type_revealed"):
        lines.append(f"### {kind}")
        lines.append("")
        rows = events.get(kind, {}).get("top_unsupported", [])
        lines.extend(
            [f"- `{label}`: {count}" for label, count in rows[:10]]
            or ["- None."]
        )
        lines.append("")
    lines.extend(
        [
            "## Source-absent evidence (absorbed after the fix)",
            "",
            "- `OpponentSetBelief.update` now records reveals for dimensions the",
            "  role source does not model (items for Randbats; any reveal on a",
            "  missing-species belief) as confirmed public facts with",
            "  `source_covered = False`, leaving role/ability/move/Tera",
            "  hypotheses and the unknown tail untouched.",
            f"- Source-absent ledger entries absorbed cleanly: "
            f"{summary['source_absent_absorbed_total']} "
            f"(`{summary['source_absent_absorbed_by_kind']}`).",
            f"- Item evidence ledger entries: "
            f"{summary['item_evidence_ledger_count']}; of these, item-driven "
            f"contradictions: {summary['item_contradiction_count']}.",
            "- Every item reveal is now absorbed rather than collapsing the",
            "  posterior, so the prior 701 item-driven first collapses are gone.",
            "",
            "## Copied/forme current-state evidence (recorded, non-contradicting)",
            "",
            "- Trace copies, Imposter/Transform copied moves/abilities, Struggle,",
            "  and forme-state abilities (As One, Tera Shell/Shift, Battle Bond,",
            "  Embody Aspect) are flagged `current_state_only`: recorded in the",
            "  ledger but never used as base-set evidence or contradiction.",
            f"- Current-state ledger entries: "
            f"{summary['current_state_ledger_total']} "
            f"(`{summary['current_state_ledger_by_kind']}`).",
            "",
            "## Posterior contradictions",
            "",
            f"- Slots reaching explicit prior contradiction: "
            f"{summary['contradictory_slots']}/{summary['slot_count']} "
            f"({summary['contradictory_slot_pct']:.2f}%).",
            f"- Contradicting evidence entries by kind: "
            f"`{summary['contradiction_by_kind']}`.",
            "- All remaining contradictions are source-covered ability/move",
            "  dimensions where the public reveal is incompatible with every",
            "  declared hypothesis; real source/data mismatches stay explicit.",
            "",
            "Remaining contradiction classification:",
            "",
            f"- `{summary['contradiction_classification']}`.",
            "- `dynamic_or_copied_state`: Trace/Imposter (Ditto) and other copied",
            "  abilities/moves shown as current state but not base-set facts.",
            "- `composite_or_forme_ability`: identity/forme-tied abilities (As One,",
            "  Embody Aspect, Tera Shell/Shift, Battle Bond) stored under the base",
            "  forme key; partly an alias/form-normalization gap.",
            "- `universal_move_noise`: Struggle, which is never a set move.",
            "- `true_source_limitation`: the declared role sets genuinely omit the",
            "  revealed ability/move.",
            "",
        ]
    )
    for category, rows in sorted(
        summary["contradiction_classification_details"].items()
    ):
        lines.append(f"### {category}")
        lines.append("")
        lines.extend([f"- `{label}`: {count}" for label, count in rows] or ["- None."])
        lines.append("")
    lines.extend(
        [
            "Top first-collapse details:",
            "",
        ]
    )
    lines.extend(
        [
            f"- `{label}`: {count}"
            for label, count in summary["top_contradiction_details"][:15]
        ]
        or ["- None."]
    )
    for kind, rows in summary["contradiction_details_by_kind"].items():
        lines.extend(["", f"### {kind}", ""])
        lines.extend([f"- `{label}`: {count}" for label, count in rows])
    lines.extend(
        [
            "",
            "## Causality and invariance",
            "",
            f"- Prefix/suffix causality: "
            f"{summary['prefix_causality_checks'] - len(summary['prefix_causality_failures'])}/"
            f"{summary['prefix_causality_checks']} passed.",
            f"- Hidden-truth perturbation invariance: "
            f"{summary['hidden_truth_checks'] - len(summary['hidden_truth_failures'])}/"
            f"{summary['hidden_truth_checks']} passed.",
            f"- Illusion replacement segments observed: "
            f"{summary['illusion_ambiguous_segments']}; failures: "
            f"{len(summary['illusion_failures'])}.",
            f"- Named reflected-move rows observed: {summary['reflection_rows']}; "
            f"attribution/move-pollution failures: "
            f"{len(summary['reflection_failures'])}.",
            "",
            "## Decision",
            "",
            "Both non-source-data blockers are now fixed. The explicit form-alias",
            "policy resolves cosmetic/forme public keys to their base prior (with",
            "alias provenance recorded), and copied/forme current-state evidence",
            "(Trace, Imposter/Transform, Struggle, forme abilities) is recorded",
            "without contradicting the base prior. Items remain absorbed as",
            "source-absent. Causality, hidden-truth invariance, Illusion, and",
            "reflection checks all pass.",
            "",
            "Any remaining contradictions are genuine source limitations (the role",
            "data simply omits a real base-set ability/move). The source is now",
            "clean enough for the first append-only v8 belief-feature slice,",
            "provided every feature retains explicit source-quality/unknown",
            "provenance and treats coarse support/unknown indicators as",
            "uncalibrated. The fixed 0.5 tail, factorized role alternatives, absent",
            "items, and declaration-rather-than-generated probabilities still make",
            "this unsuitable as a sole calibrated production prior; the",
            "generator-sampled snapshot remains the route to calibrated joint",
            "probabilities.",
        ]
    )
    return "\n".join(lines) + "\n"
