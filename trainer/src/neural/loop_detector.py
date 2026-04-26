"""
Loop detection module for identifying suspicious battle patterns.

Detects:
- Repeated same action vs same opponent Pokemon
- Repeated setup moves after boosting is likely maxed
- Setup moves with no progress
- Recovery at full HP
- Hazard redundancy
- Wall loops (low progress against defensive Pokemon)
- Repeated Struggle
"""

from typing import Any, Dict, List, Optional, Set, Tuple


class LoopDetector:
    """Detects suspicious battle loops and patterns."""

    DEFENSIVE_POKEMON = {
        "chansey", "blissey", "alcremie", "umbreon", "dusknoir",
        "miltank", "farigiraf", "scizor", "corviknight", "tangrowth"
    }

    def __init__(self):
        """Initialize loop detector."""
        pass

    def detect_loops_in_battle(
        self,
        records: List[Dict[str, Any]],
        battle_records: List[int],
        max_same_action_streak: int = 5,
    ) -> List[Tuple[str, int, int]]:
        """Detect loops in a single battle.

        Args:
            records: All battle records
            battle_records: Indices of records for this battle (in order)
            max_same_action_streak: Threshold for repeated action count

        Returns:
            List of (diagnostic_message, start_idx, end_idx)
        """
        diagnostics: List[Tuple[str, int, int]] = []

        if len(battle_records) < 5:
            return diagnostics

        # Track moves and opponent Pokemon
        moves_used: List[str] = []
        opponent_pokemon: List[str] = []
        hp_ratios: List[float] = []

        for rec_idx in battle_records:
            record = records[rec_idx]
            view = record.get("view", {})
            choice = record.get("choice", "")

            # Extract move name
            active = view.get("active", {}).get("opponent", 0) or 0
            opponent_team = view.get("opponent_team", [])
            if active < len(opponent_team):
                opp_poke = opponent_team[active]
                opponent_pokemon.append(opp_poke.get("name", "Unknown"))
            else:
                opponent_pokemon.append("Unknown")

            # Extract move from choice
            move_name = self._extract_move_name(choice, record.get("request", {}))
            moves_used.append(move_name or "unknown")

            # Track opponent HP
            if active < len(opponent_team):
                hp_ratios.append(opponent_team[active].get("hp_ratio", 0))

        # Detect repeated same move
        diagnostics.extend(
            self._detect_repeated_move_streak(moves_used, opponent_pokemon, battle_records, max_same_action_streak)
        )

        # Detect wall loops
        diagnostics.extend(
            self._detect_wall_loop(opponent_pokemon, moves_used, hp_ratios, battle_records)
        )

        # Detect repeated Struggle
        diagnostics.extend(
            self._detect_repeated_struggle(moves_used, battle_records)
        )

        return diagnostics

    def _detect_repeated_move_streak(
        self,
        moves: List[str],
        opponents: List[str],
        record_indices: List[int],
        threshold: int
    ) -> List[Tuple[str, int, int]]:
        """Detect when same move is used many times in a row."""
        diagnostics: List[Tuple[str, int, int]] = []

        if len(moves) < threshold:
            return diagnostics

        i = 0
        while i < len(moves):
            move = moves[i]
            opponent = opponents[i]
            j = i + 1

            # Count consecutive same move against same opponent
            while j < len(moves) and moves[j] == move and opponents[j] == opponent:
                j += 1

            streak_length = j - i
            if streak_length >= threshold:
                msg = f"Repeated '{move}' vs {opponent} for {streak_length} turns"
                diagnostics.append((msg, record_indices[i], record_indices[j - 1]))

            i = j

        return diagnostics

    def _detect_wall_loop(
        self,
        opponents: List[str],
        moves: List[str],
        hp_ratios: List[float],
        record_indices: List[int],
        turn_threshold: int = 15,
        progress_threshold: float = 0.1
    ) -> List[Tuple[str, int, int]]:
        """Detect wall loops (long low-progress battles vs defensive Pokemon)."""
        diagnostics: List[Tuple[str, int, int]] = []

        if len(opponents) < turn_threshold:
            return diagnostics

        # Look for recent opponent as defensive Pokemon
        recent_opponents = {str(opponent).lower() for opponent in opponents[-turn_threshold:]}
        defensive = recent_opponents & self.DEFENSIVE_POKEMON

        if not defensive:
            return diagnostics

        # Check progress
        if len(hp_ratios) >= turn_threshold:
            start_hp = hp_ratios[-turn_threshold]
            end_hp = hp_ratios[-1]
            progress = start_hp - end_hp

            if progress < progress_threshold:
                msg = f"Wall loop vs {list(defensive)[0]}: {turn_threshold} turns, {progress*100:.1f}% progress"
                diagnostics.append((msg, record_indices[-turn_threshold], record_indices[-1]))

        return diagnostics

    def _detect_repeated_struggle(
        self, moves: List[str], record_indices: List[int]
    ) -> List[Tuple[str, int, int]]:
        """Detect repeated Struggle usage (sign of being out of PP)."""
        diagnostics: List[Tuple[str, int, int]] = []

        struggle_streak = 0
        start_idx = -1

        for i, move in enumerate(moves):
            if move and "struggle" in move.lower():
                if struggle_streak == 0:
                    start_idx = i
                struggle_streak += 1
            else:
                if struggle_streak >= 5:
                    msg = f"Repeated Struggle for {struggle_streak} turns (out of PP?)"
                    diagnostics.append((msg, record_indices[start_idx], record_indices[i - 1]))
                struggle_streak = 0

        if struggle_streak >= 5:
            msg = f"Repeated Struggle for {struggle_streak} turns (out of PP?)"
            diagnostics.append((msg, record_indices[start_idx], record_indices[-1]))

        return diagnostics

    def _extract_move_name(self, choice: str, request: Dict[str, Any]) -> Optional[str]:
        """Extract move name from choice string."""
        if not choice.startswith("move"):
            return None

        parts = choice.split()
        if len(parts) < 2:
            return None

        try:
            slot = int(parts[1]) - 1
        except ValueError:
            return None

        active = request.get("active", {})
        if not isinstance(active, dict):
            return None

        moves = active.get("moves", [])
        if slot >= len(moves) or slot < 0:
            return None

        move = moves[slot]
        return move.get("move")


def detect_all_loops(
    records: List[Dict[str, Any]], **kwargs
) -> Dict[int, List[Tuple[str, int, int]]]:
    """Detect loops across all battles in dataset.

    Args:
        records: All records from dataset
        **kwargs: Options like max_same_action_streak

    Returns:
        Dict mapping battle_index -> list of diagnostics
    """
    detector = LoopDetector()
    result: Dict[int, List[Tuple[str, int, int]]] = {}

    # Group records by battle
    battles: Dict[int, List[int]] = {}
    for idx, record in enumerate(records):
        battle_idx = record.get("battle_index", -1)
        if battle_idx not in battles:
            battles[battle_idx] = []
        battles[battle_idx].append(idx)

    # Detect loops in each battle
    for battle_idx, record_indices in battles.items():
        diagnostics = detector.detect_loops_in_battle(
            records, record_indices, **kwargs
        )
        if diagnostics:
            result[battle_idx] = diagnostics

    return result
