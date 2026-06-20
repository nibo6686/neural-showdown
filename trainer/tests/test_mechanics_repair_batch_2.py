"""Mechanics repair batch 2: secondary / status / stat / volatile next-state.

Diagnostic-only. Asserts that the coarse next-state effect detector fills the
existing v6 change flags so a move with a real secondary/primary status, volatile
or stat effect is no longer encoded as a wrong-exact "no change", while ordinary
moves stay clean. Booleans only: exact type/chance/magnitude stay unrepresented,
so these moves are INEXACT, not PASS. No schema name/order/dim changes here.
"""

import unittest

from neural.action_features import (
    SLICE6_ACTION_FEATURE_NAMES,
    slice6_resolved_impact_feature_vector,
)
from neural.gen9randbats_mechanics_completeness_audit import run_audit
from neural.resolved_action_impact_diagnostic import _action


def _slice6(move):
    # Next-state effect flags derive from move metadata, not the impact, so an
    # impact is not required to exercise them.
    return slice6_resolved_impact_feature_vector(_action(move), None, None)


def _flag(vec, name):
    return float(vec[SLICE6_ACTION_FEATURE_NAMES.index(name)])


class SecondaryEffectFlagTest(unittest.TestCase):
    def test_status_secondary_flags_opponent_status(self):
        # Thunderbolt: 10% paralysis secondary.
        self.assertEqual(_flag(_slice6("Thunderbolt"), "next_opp_status_change"), 1.0)

    def test_stat_drop_secondary_flags_opponent_stat(self):
        # Crunch: 20% Defense drop secondary.
        self.assertEqual(_flag(_slice6("Crunch"), "next_opp_stat_change"), 1.0)

    def test_self_boost_secondary_flags_own_stat(self):
        # Meteor Mash: 20% self Attack boost secondary.
        self.assertEqual(_flag(_slice6("Meteor Mash"), "next_own_stat_change"), 1.0)

    def test_flinch_volatile_secondary_flags_opponent(self):
        # Iron Head: 30% flinch (volatile) secondary.
        self.assertEqual(_flag(_slice6("Iron Head"), "next_opp_status_change"), 1.0)

    def test_primary_target_status_move_flags_and_is_non_damaging(self):
        # Will-O-Wisp: guaranteed burn, non-damaging.
        vec = _slice6("Will-O-Wisp")
        self.assertEqual(_flag(vec, "next_opp_status_change"), 1.0)
        self.assertEqual(_flag(vec, "action_non_damaging"), 1.0)

    def test_weather_accuracy_move_flags_secondary(self):
        # Blizzard left FAIL only on its omitted freeze secondary; now flagged.
        self.assertEqual(_flag(_slice6("Blizzard"), "next_opp_status_change"), 1.0)

    def test_ordinary_move_unaffected(self):
        for move in ("Surf", "Earthquake", "Close Combat", "Dragon Pulse"):
            vec = _slice6(move)
            for name in (
                "next_opp_status_change",
                "next_own_status_change",
            ):
                self.assertEqual(_flag(vec, name), 0.0, f"{move}:{name}")

    def test_v7_needed_move_is_non_damaging_coarse_flag(self):
        # Trick swaps items: no v6 field; only coarse non-damaging flag, marked
        # INEXACT (needs typed v7 fields).
        vec = _slice6("Trick")
        self.assertEqual(_flag(vec, "action_non_damaging"), 1.0)
        self.assertEqual(_flag(vec, "next_opp_status_change"), 0.0)


class AuditConsistencyTest(unittest.TestCase):
    """Every batch-2 move marked INEXACT must carry an honest coarse signal."""

    BATCH2_REASONS = (
        "secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented",
        "target status/volatile coarsely flagged via next-state change fields (batch 2); exact status type not represented",
        "non-damaging status transition coarsely flagged (action_non_damaging + next-state change fields, batch 2); item-swap/copy/random-call effects need typed v7 fields",
    )
    EFFECT_FLAGS = (
        "next_own_stat_change",
        "next_opp_stat_change",
        "next_own_status_change",
        "next_opp_status_change",
        "action_non_damaging",
    )

    def test_every_batch2_move_has_a_coarse_signal(self):
        report = run_audit()
        batch2 = [m for m in report["moves"] if m["reason"] in self.BATCH2_REASONS]
        self.assertGreater(len(batch2), 100)
        for move in batch2:
            vec = _slice6(move["name"])
            self.assertTrue(
                any(_flag(vec, name) == 1.0 for name in self.EFFECT_FLAGS),
                f"{move['name']} marked INEXACT but carries no coarse next-state signal",
            )

    def test_damaging_secondary_moves_flag_a_next_state_change(self):
        # Damaging moves (action_non_damaging=0) must rely on a real change flag.
        report = run_audit()
        damaging = [
            m for m in report["moves"]
            if m["reason"] == self.BATCH2_REASONS[0] and str(m["category"]) != "Status"
        ]
        change_flags = self.EFFECT_FLAGS[:-1]  # exclude action_non_damaging
        for move in damaging:
            vec = _slice6(move["name"])
            self.assertTrue(
                any(_flag(vec, name) == 1.0 for name in change_flags),
                f"{move['name']} damaging-secondary has no next-state change flag",
            )


if __name__ == "__main__":
    unittest.main()
