import unittest

from neural.dynamic_move_mechanics_audit import run_audit


class DynamicMoveMechanicsAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = run_audit()
        cls.by_name = {row["mechanic"]: row for row in cls.report["mechanics"]}

    def test_schema_remains_v5_318d(self):
        self.assertEqual(self.report["action_feature_version"], "legal-action-v6")
        self.assertEqual(self.report["action_feature_dim"], 331)

    def test_rage_fist_and_last_respects_pass(self):
        self.assertEqual(self.by_name["Rage Fist"]["status"], "PASS")
        self.assertEqual(self.by_name["Last Respects"]["status"], "PASS")

    def test_stored_power_live_plumbing_passes(self):
        row = self.by_name["Stored Power / Power Trip"]
        self.assertEqual(row["status"], "PASS")
        self.assertIn("live-like", row["evidence"])

    def test_status_scaling_passes(self):
        self.assertEqual(self.by_name["Facade / Hex / Venoshock"]["status"], "PASS")

    def test_curse_context_passes(self):
        self.assertEqual(self.by_name["Curse (Ghost vs non-Ghost)"]["status"], "PASS")

    def test_variable_base_power_groups_pass(self):
        self.assertEqual(self.by_name["Eruption / Water Spout / Reversal / Flail"]["status"], "PASS")
        self.assertEqual(self.by_name["Gyro/Electro Ball and weight moves"]["status"], "PASS")

    def test_previously_unverified_groups_are_resolved(self):
        self.assertEqual(self.by_name["Weather Ball / Terrain Pulse"]["status"], "PASS")
        self.assertEqual(self.by_name["Body Press / Foul Play"]["status"], "PASS")
        self.assertEqual(self.report["summary"]["NEEDS_VERIFICATION"], 0)

    def test_repeat_chain_group_passes_under_v6(self):
        self.assertEqual(self.report["summary"], {"PASS": 12, "FAIL": 0, "NEEDS_VERIFICATION": 0})
        self.assertEqual(self.by_name["Rollout / Fury Cutter"]["status"], "PASS")

    def test_accuracy_is_represented_as_damage_plus_hit_chance(self):
        row = self.by_name["Accuracy-sensitive comparison"]
        self.assertEqual(row["status"], "PASS")
        self.assertIn("Focus Blast hit=0.70", row["evidence"])


if __name__ == "__main__":
    unittest.main()
