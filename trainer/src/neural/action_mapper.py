"""
Trajectory action mapper: Maps public replay action labels to fixed 13-action Showdown indices.

Public replays store action labels as strings (e.g., "move:Thunderbolt", "switch:Pikachu").
This mapper reconstructs Pokémon Showdown's protocol events to infer:
- Move slot index (0-3) from revealed move history
- Switch bench slot (0-5) from team state reconstruction
- Confidence and failure reasons for unmapped actions

Key principles:
- Accuracy over coverage: unmapped actions are documented, not guessed
- Protocol-driven: uses |move|, |switch|, |faint|, |replace| events to track state
- Confidence scoring: high confidence for observed moves; lower for inferred slots
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


def normalize_pokemon_name(name: str) -> str:
    """
    Normalize Pokémon name by stripping level, gender, shiny, tera type annotations.

    Examples:
        "Blissey, L85, F" → "Blissey"
        "Moltres-Galar, L79" → "Moltres-Galar"
        "Rillaboom, M, shiny" → "Rillaboom"
        "Charizard, Tera Water" → "Charizard"
    """
    if not name:
        return name

    # Split by commas to separate base name from annotations
    parts = [p.strip() for p in name.split(",")]
    base_name = parts[0]

    # Remove level annotations (e.g., "L85", "Level 85")
    base_name = base_name.replace(" L ", " ").replace("-L", "")  # handles "L85" prefix/suffix

    # The base_name might now have trailing level info; clean it
    # Pattern: ends with "L" followed by digits
    import re
    base_name = re.sub(r'\s*L\d+\s*$', '', base_name)
    base_name = re.sub(r'\s*Level\s*\d+\s*$', '', base_name, flags=re.IGNORECASE)

    return base_name.strip()


def safe_forme_alias(name: str, roster: List[str]) -> Optional[str]:
    """
    Find a safe forme alias for a Pokémon if it exists in the roster.
    Safe aliases include forme variations without evolutionary changes.

    Examples (safe):
        "Palafin-Hero" → "Palafin" (same species, forme change)
        "Terapagos-Terastal" → "Terapagos" (forme variant)
        "Squawkabilly-White" → "Squawkabilly" (color form)
        "Mimikyu-Busted" → "Mimikyu" (state variant)

    Examples (unsafe - not handled):
        "Conkeldurr" ← "Gurdurr" (different species, evolution)

    Returns:
        Base species name if a safe alias exists in roster, else None
    """
    # List of (variant, base_species) pairs where variant is safe to alias to base
    safe_aliases = [
        ("Palafin-Hero", "Palafin"),
        ("Terapagos-Terastal", "Terapagos"),
        ("Terapagos-Stellar", "Terapagos"),
        ("Squawkabilly-White", "Squawkabilly"),
        ("Squawkabilly-Blue", "Squawkabilly"),
        ("Squawkabilly-Yellow", "Squawkabilly"),
        ("Squawkabilly-Green", "Squawkabilly"),
        ("Mimikyu-Busted", "Mimikyu"),
        ("Eiscue-Noice", "Eiscue"),
        ("Oinkologne-F", "Oinkologne"),
        ("Oinkologne-M", "Oinkologne"),
    ]

    # Check if name matches any safe alias
    for variant, base in safe_aliases:
        if name == variant:
            # Verify base species exists in roster (normalized)
            for roster_entry in roster:
                if normalize_pokemon_name(roster_entry) == base:
                    return base
            return None

    return None


def best_matching_pokemon(
    target_name: str, roster: List[str], normalize: bool = True
) -> Tuple[Optional[int], bool, Optional[str]]:
    """
    Find best matching Pokémon in roster, trying normalized, exact, and safe aliases.

    Returns:
        (roster_index, is_normalized_match, match_type)
        - roster_index: 0-5 if found, None otherwise
        - is_normalized_match: True if match required normalization, False if exact
        - match_type: "exact", "normalized", or "safe_alias"
    """
    if normalize:
        normalized_target = normalize_pokemon_name(target_name)
        # Try normalized match first
        for idx, roster_name in enumerate(roster):
            if normalize_pokemon_name(roster_name) == normalized_target:
                return idx, True, "normalized"

    # Try exact match
    for idx, roster_name in enumerate(roster):
        if roster_name == target_name:
            return idx, False, "exact"

    # Try safe forme aliases
    base_alias = safe_forme_alias(normalize_pokemon_name(target_name), roster)
    if base_alias:
        for idx, roster_name in enumerate(roster):
            if normalize_pokemon_name(roster_name) == base_alias:
                return idx, True, "safe_alias"

    return None, False, None


def extract_actor_species(actor_str: str) -> Optional[str]:
    """
    Extract species name from protocol actor field.

    Examples:
        "p2a: Sudowoodo" → "Sudowoodo"
        "p1a: Blissey, L85, F" → "Blissey, L85, F"
        "p2: Trainer" → None (not a Pokémon)
    """
    if not actor_str or ": " not in actor_str:
        return None

    # Format: "p1a: Species" or "p1: Species"
    parts = actor_str.split(": ", 1)
    if len(parts) != 2:
        return None

    side_part = parts[0]  # "p1a" or "p1"
    species = parts[1].strip()

    # Only handle "pXa: Species" format (active Pokémon)
    if not side_part.endswith("a"):
        return None

    # Skip non-Pokémon entries
    if species.lower() in ("trainer", "player"):
        return None

    return species if species else None


@dataclass
class TeamTracker:
    """Tracks active and bench Pokémon for one side across protocol events."""

    side: str  # "p1" or "p2"
    active_pokemon: Optional[str] = None  # Current active Pokémon name
    active_moves: Set[str] = field(default_factory=set)  # Moves revealed for active Pokémon
    team_roster: List[str] = field(default_factory=list)  # Team order: [p0, p1, ..., p5]
    fainted: Set[str] = field(default_factory=set)  # Names of fainted Pokémon
    active_pokemon_move_count: int = 0  # How many moves have been used by active Pokemon

    def apply_switch_event(self, pokemon_name: str) -> None:
        """Handle |switch| event: new active Pokémon and optionally update team order."""
        self.active_pokemon = pokemon_name
        self.active_moves = set()
        self.active_pokemon_move_count = 0
        if pokemon_name not in self.team_roster:
            # Unseen team member; add if we have space
            if len(self.team_roster) < 6:
                self.team_roster.append(pokemon_name)

    def apply_move_event(self, pokemon_name: str, move_name: str) -> None:
        """Handle |move| event: track revealed moves for Pokémon."""
        if pokemon_name == self.active_pokemon:
            self.active_moves.add(move_name)
            self.active_pokemon_move_count += 1

    def apply_faint_event(self, pokemon_name: str) -> None:
        """Handle |faint| event: mark Pokémon as fainted and clear from active."""
        self.fainted.add(pokemon_name)
        if self.active_pokemon == pokemon_name:
            self.active_pokemon = None
            self.active_moves = set()
            self.active_pokemon_move_count = 0

    def apply_replace_event(self, old_pokemon: str, new_pokemon: str) -> None:
        """Handle |replace| event (e.g., mid-switch after Trick Room): update active."""
        # |replace| typically indicates a replacement mid-turn
        self.active_pokemon = new_pokemon
        self.active_moves = set()
        self.active_pokemon_move_count = 0
        if new_pokemon not in self.team_roster and len(self.team_roster) < 6:
            self.team_roster.append(new_pokemon)

    def bench_index_of(self, pokemon_name: str) -> Optional[int]:
        """
        Returns bench index (0-5) for a Pokémon name if known in roster.
        Tries exact, normalized, and safe alias matching.
        Returns None if not found or if Pokémon is the active one.
        """
        if pokemon_name == self.active_pokemon:
            return None

        # Try best matching (exact, normalized, safe aliases)
        idx, _, _ = best_matching_pokemon(pokemon_name, self.team_roster, normalize=True)
        return idx if idx is not None and idx < 6 else None

    def apply_actor_fallback_for_move(self, actor_str: str) -> bool:
        """
        If active_pokemon is unknown, try to extract it from the actor field of a move event.

        Returns True if fallback was applied, False otherwise.
        """
        if self.active_pokemon is not None:
            return False  # Already know active Pokémon

        actor_species = extract_actor_species(actor_str)
        if actor_species:
            self.active_pokemon = actor_species
            self.active_moves = set()
            self.active_pokemon_move_count = 0
            # Ensure it's in roster if not already
            if actor_species not in self.team_roster and len(self.team_roster) < 6:
                self.team_roster.append(actor_species)
            return True

        return False

    def move_slot_of(self, move_name: str) -> Tuple[Optional[int], float, Optional[str]]:
        """
        Returns (move_slot, confidence, mapping_type).
        - move_slot: 0-3 if found, None if unmapped
        - confidence: 0.0-1.0
        - mapping_type: "revealed" or "inferred" (first move in new slot) or None

        Strategy:
        - If move in revealed set: slot with high confidence (1.0, "revealed")
        - If active Pokémon just switched and hasn't revealed moves yet:
          Assign next available slot with lower confidence (0.6, "inferred_first_move")
        - Otherwise: unmapped
        """
        if not self.active_pokemon or move_name is None:
            return None, 0.0, None

        # Direct match in revealed moves: highest confidence
        if move_name in self.active_moves:
            sorted_moves = sorted(list(self.active_moves))
            try:
                slot = sorted_moves.index(move_name)
                return slot, 1.0, "revealed"
            except ValueError:
                pass

        # Inference: if this is the first move being revealed after a switch,
        # assign to the next available slot (0, 1, 2, or 3)
        if self.active_pokemon_move_count == 0 and len(self.active_moves) == 0:
            # This is the first move we're seeing; use slot 0 with lower confidence
            return 0, 0.6, "inferred_first_move"

        # If we've seen N moves revealed, next unseen move goes to slot N (if N < 4)
        if len(self.active_moves) < 4:
            # Infer next available slot
            return len(self.active_moves), 0.5, "inferred_next_slot"

        # Ambiguous: 4 moves already revealed, can't infer which slot this is
        return None, 0.0, None


@dataclass
class TrajectoryActionMapper:
    """Maps public replay action labels to Showdown's fixed 13-action encoding."""

    p1_tracker: TeamTracker = field(default_factory=lambda: TeamTracker("p1"))
    p2_tracker: TeamTracker = field(default_factory=lambda: TeamTracker("p2"))
    mapping_log: List[Dict[str, Any]] = field(default_factory=list)

    def _tracker_for(self, side: str) -> TeamTracker:
        """Get tracker for p1 or p2."""
        return self.p1_tracker if side == "p1" else self.p2_tracker

    def track_events_in_turn(self, events: List[Dict[str, Any]]) -> None:
        """
        Process all protocol events in a turn to update team state.
        Call this before mapping actions for that turn.
        """
        for event in events:
            if not isinstance(event, dict):
                continue
            event_type = event.get("type")
            side = event.get("side")

            if side not in ("p1", "p2"):
                continue

            tracker = self._tracker_for(side)

            if event_type == "switch":
                details = event.get("details", "")
                pokemon_name = details.split(",")[0].strip() if "," in details else details.strip()
                if pokemon_name:
                    tracker.apply_switch_event(pokemon_name)

            elif event_type == "move":
                actor = event.get("actor", "")
                move_name = event.get("move", "")
                pokemon_name = actor.split(": ")[1] if ": " in actor else ""
                if pokemon_name and move_name:
                    tracker.apply_move_event(pokemon_name, move_name)

            elif event_type == "faint":
                target = event.get("target", "")
                pokemon_name = target.split(": ")[1] if ": " in target else ""
                if pokemon_name:
                    tracker.apply_faint_event(pokemon_name)

            elif event_type == "replace":
                old_pokemon = event.get("from", "")
                new_pokemon = event.get("details", "")
                if old_pokemon and new_pokemon:
                    tracker.apply_replace_event(old_pokemon, new_pokemon)

    def map_move_action(
        self, move_name: str, side: str, actor_str: Optional[str] = None, confidence_threshold: float = 0.5
    ) -> Tuple[Optional[int], float, Optional[str], Optional[str]]:
        """
        Map a move action to a move slot (0-3).

        Args:
            move_name: Name of the move (from "move:MoveXyz" label)
            side: "p1" or "p2"
            actor_str: Optional raw actor field from protocol (e.g., "p2a: Sudowoodo")
            confidence_threshold: Minimum confidence (0-1) to accept mapping

        Returns:
            (slot_index, confidence, mapping_type, failure_reason)
            - slot_index: 0-3 if mapped, None if unmapped
            - confidence: 0.0-1.0 estimate
            - mapping_type: "revealed", "inferred_first_move", "inferred_next_slot", "actor_fallback_move", or None
            - failure_reason: Explanation if unmapped
        """
        tracker = self._tracker_for(side)

        # If active Pokémon unknown, try actor fallback
        if tracker.active_pokemon is None and actor_str:
            if tracker.apply_actor_fallback_for_move(actor_str):
                # Fallback applied; now try mapping
                slot, conf, map_type = tracker.move_slot_of(move_name)
                if slot is not None:
                    # Lower confidence for actor-fallback moves (slightly less reliable)
                    return slot, conf * 0.85, "actor_fallback_move", None

        if tracker.active_pokemon is None:
            return None, 0.0, None, "active_pokemon_unknown"

        slot, conf, map_type = tracker.move_slot_of(move_name)

        if slot is not None and conf >= confidence_threshold:
            return slot, conf, map_type, None

        # Move not found or confidence too low
        if slot is None:
            reason = f"move_not_revealed ({move_name} not in {sorted(list(tracker.active_moves))})"
            return None, 0.0, None, reason

        # Confidence too low
        reason = f"low_confidence (conf={conf:.2f} < {confidence_threshold})"
        return None, conf, map_type, reason

    def map_switch_action(
        self, pokemon_name: str, side: str, confidence_threshold: float = 0.8
    ) -> Tuple[Optional[int], float, Optional[str], Optional[str]]:
        """
        Map a switch action to a bench slot (0-5).

        Args:
            pokemon_name: Name of Pokémon to switch to (from "switch:PokemonXyz" label)
            side: "p1" or "p2"
            confidence_threshold: Minimum confidence (0-1) to accept mapping

        Returns:
            (bench_index, confidence, match_type, failure_reason)
            - bench_index: 0-5 if mapped, None if unmapped
            - confidence: 0.0-1.0 estimate
            - match_type: "exact" or "normalized" (stripped level/gender/etc)
            - failure_reason: Explanation if unmapped
        """
        tracker = self._tracker_for(side)

        # Try best matching (normalized first, then exact)
        bench_idx, is_normalized, *_ = best_matching_pokemon(
            pokemon_name,
            tracker.team_roster,
            normalize=True,
        )

        if bench_idx is not None:
            # Found a match
            confidence = 0.95 if not is_normalized else 0.85  # Normalized match is slightly less confident
            match_type = "exact" if not is_normalized else "normalized"
            return bench_idx, confidence, match_type, None

        # Pokémon not in revealed team state
        reason = f"pokemon_not_in_roster (normalized:{normalize_pokemon_name(pokemon_name)} not in roster:{[normalize_pokemon_name(p) for p in tracker.team_roster]})"
        return None, 0.0, None, reason

    def map_action(
        self, action_label: str, side: str, actor_str: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Map a single public action label to fixed 13-action encoding.

        Args:
            action_label: e.g., "move:Thunderbolt" or "switch:Pikachu"
            side: "p1" or "p2"
            actor_str: Optional raw actor field from protocol

        Returns:
            {
                "action_label": str,
                "action_type": "move" | "switch",
                "action_name": str,
                "mapped_slot_index": int | None,
                "confidence": float,
                "mapping_type": str | None,
                "failure_reason": str | None,
                "mapped": bool,
            }
        """
        parts = action_label.split(":", 1)
        if len(parts) != 2:
            return {
                "action_label": action_label,
                "action_type": "unknown",
                "action_name": action_label,
                "mapped_slot_index": None,
                "confidence": 0.0,
                "mapping_type": None,
                "failure_reason": "malformed_action_label",
                "mapped": False,
            }

        action_type, action_name = parts
        action_type = action_type.strip()
        action_name = action_name.strip()

        if action_type == "move":
            slot, conf, map_type, reason = self.map_move_action(action_name, side, actor_str=actor_str)
            return {
                "action_label": action_label,
                "action_type": "move",
                "action_name": action_name,
                "mapped_slot_index": slot,
                "confidence": conf,
                "mapping_type": map_type,
                "failure_reason": reason,
                "mapped": slot is not None,
            }
        elif action_type == "switch":
            bench_idx, conf, match_type, reason = self.map_switch_action(action_name, side)
            # In Showdown's 13-action space, switch actions are slots 4-9 for bench indices 0-5
            mapped_slot = (4 + bench_idx) if bench_idx is not None else None
            return {
                "action_label": action_label,
                "action_type": "switch",
                "action_name": action_name,
                "bench_index": bench_idx,
                "mapped_slot_index": mapped_slot,
                "confidence": conf,
                "mapping_type": match_type,
                "failure_reason": reason,
                "mapped": mapped_slot is not None,
            }
        else:
            return {
                "action_label": action_label,
                "action_type": action_type,
                "action_name": action_name,
                "mapped_slot_index": None,
                "confidence": 0.0,
                "mapping_type": None,
                "failure_reason": f"unsupported_action_type ({action_type})",
                "mapped": False,
            }

    def map_trajectory_actions(self, trajectory: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map all actions in a trajectory.

        Returns mapping summary:
        {
            "total_actions": int,
            "mapped_count": int,
            "unmapped_count": int,
            "mapped_percentage": float,
            "mapping_failures": {
                "failure_reason": count, ...
            },
            "details": [
                {
                    "turn": int,
                    "side": str,
                    "action_label": str,
                    "mapping_result": {...},
                }
            ]
        }
        """
        self.p1_tracker = TeamTracker("p1")
        self.p2_tracker = TeamTracker("p2")
        self.mapping_log = []

        turns = trajectory.get("turns", [])
        total_actions = 0
        mapped_count = 0
        unmapped_count = 0
        failure_counts = defaultdict(int)
        details = []

        for turn_record in sorted(turns, key=lambda t: int(t.get("turn", 0) or 0)):
            turn_number = int(turn_record.get("turn", 0) or 0)
            events = turn_record.get("events", [])

            # First pass: track state from all events
            self.track_events_in_turn(events)

            # Second pass: map actions
            for event in events:
                if not isinstance(event, dict):
                    continue
                if event.get("type") not in ("move", "switch"):
                    continue

                side = event.get("side")
                if side not in ("p1", "p2"):
                    continue

                action_label = _action_label_from_event(event)

                # For move actions, pass the actor field for fallback resolution
                actor_str = None
                if event.get("type") == "move":
                    actor_str = event.get("actor")

                mapping_result = self.map_action(action_label, side, actor_str=actor_str)

                total_actions += 1
                if mapping_result["mapped"]:
                    mapped_count += 1
                else:
                    unmapped_count += 1
                    if mapping_result["failure_reason"]:
                        failure_counts[mapping_result["failure_reason"]] += 1

                details.append(
                    {
                        "turn": turn_number,
                        "side": side,
                        "action_label": action_label,
                        "mapping_result": mapping_result,
                    }
                )

        mapped_pct = (100.0 * mapped_count / total_actions) if total_actions > 0 else 0.0

        return {
            "total_actions": total_actions,
            "mapped_count": mapped_count,
            "unmapped_count": unmapped_count,
            "mapped_percentage": mapped_pct,
            "mapping_failures": dict(failure_counts),
            "details": details,
        }


def _action_label_from_event(event: Dict[str, Any]) -> str:
    """Reconstruct action label from trajectory event."""
    event_type = event.get("type", "unknown")
    if event_type == "move":
        return f"move:{event.get('move', 'unknown')}"
    elif event_type == "switch":
        return f"switch:{event.get('details', 'unknown')}"
    return str(event_type)
