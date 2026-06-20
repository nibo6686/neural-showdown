import unittest

from neural.gen9randbats_mechanics_completeness_audit import run_audit


class Gen9RandbatsMechanicsCompletenessAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = run_audit()
        cls.by_id = {row["id"]: row for row in cls.report["moves"]}

    def test_enumerates_complete_current_randbats_pool(self):
        self.assertEqual(self.report["species_entries"], 507)
        self.assertEqual(self.report["moves_audited"], 350)
        self.assertEqual(len(self.by_id), 350)

    def test_schema_remains_v6(self):
        self.assertEqual(self.report["schema"], {"version": "legal-action-v6", "dim": 331})

    def test_known_correct_dynamic_mechanics_pass(self):
        for move_id in (
            "ragefist", "storedpower", "powertrip", "eruption", "waterspout",
            "grassknot", "lowkick", "heavyslam", "bodypress", "foulplay",
        ):
            self.assertEqual(self.by_id[move_id]["status"], "PASS", move_id)

    def test_no_wrong_exact_failures_remain(self):
        # After batch 5 every material move-impact mechanic is PASS or INEXACT.
        self.assertEqual(self.report["summary"]["FAIL"], 0)
        self.assertFalse([m["name"] for m in self.report["moves"] if m["status"] == "FAIL"])

    def test_batch5_final_failures(self):
        # PASS: guaranteed crit, Freeze-Dry special effectiveness, Photon Geyser.
        for move_id in ("flowertrick", "wickedblow", "freezedry", "photongeyser"):
            self.assertEqual(self.by_id[move_id]["status"], "PASS", move_id)
        # INEXACT: damage-wrong-exact (fail-closed) and exact-damage-with-gap.
        for move_id in ("beatup", "ficklebeam", "knockoff", "bugbite", "grassyglide"):
            self.assertEqual(self.by_id[move_id]["status"], "INEXACT", move_id)

    def test_drawback_and_coarse_transition_groups_are_inexact(self):
        for move_id in ("bravebird", "gigadrain", "explosion", "uturn", "recover", "stealthrock"):
            self.assertEqual(self.by_id[move_id]["status"], "INEXACT", move_id)

    def test_batch1_fixed_damage_multihit_and_accuracy(self):
        # Fixed-damage routed to the oracle.
        for move_id in ("seismictoss", "nightshade"):
            self.assertEqual(self.by_id[move_id]["status"], "PASS", move_id)
        # Fixed-damage target/counter context and multi-hit fail closed (INEXACT).
        for move_id in (
            "superfang", "ruination", "endeavor", "mirrorcoat",
            "bulletseed", "rockblast", "tripleaxel", "surgingstrikes",
        ):
            self.assertEqual(self.by_id[move_id]["status"], "INEXACT", move_id)
    def test_batch2_secondary_status_volatile_inexact(self):
        # Damaging secondary (status / stat / volatile), primary target status,
        # and non-damaging status transitions are coarsely flagged -> INEXACT.
        for move_id in (
            "thunderbolt", "scald", "crunch", "ironhead", "meteormash",
            "willowisp", "thunderwave", "toxic", "taunt", "leechseed",
            "substitute", "trick", "transform", "sleeptalk",
        ):
            self.assertEqual(self.by_id[move_id]["status"], "INEXACT", move_id)
        # Weather-accuracy moves keep their dynamic_accuracy bucket and now leave
        # FAIL on the same secondary-effect basis.
        for move_id in ("blizzard", "thunder", "hurricane", "bleakwindstorm"):
            self.assertIn("dynamic_accuracy", self.by_id[move_id]["buckets"], move_id)
            self.assertEqual(self.by_id[move_id]["status"], "INEXACT", move_id)

    def test_batch3_dynamic_type_and_charge(self):
        # Dynamic-type moves resolve their type from state -> PASS.
        for move_id in (
            "weatherball", "judgment", "ivycudgel", "ragingbull",
            "revelationdance", "aurawheel", "terablast",
        ):
            self.assertEqual(self.by_id[move_id]["status"], "PASS", move_id)
        # Stellar can't be represented -> INEXACT (fail-closed).
        self.assertEqual(self.by_id["terastarstorm"]["status"], "INEXACT")
        # Two-turn charge / delayed -> INEXACT; Beak Blast (same-turn) -> PASS.
        for move_id in ("solarbeam", "meteorbeam", "futuresight"):
            self.assertEqual(self.by_id[move_id]["status"], "INEXACT", move_id)
        self.assertEqual(self.by_id["beakblast"]["status"], "PASS")

    def test_batch4_conditional_execution_and_history_power(self):
        # Conditional execution/success and same-turn/history power fail closed.
        for move_id in (
            "fakeout", "firstimpression", "suckerpunch", "thunderclap", "focuspunch",
            "doubleshock", "hyperspacefury", "poltergeist",
            "payback", "avalanche", "lashout", "stompingtantrum", "temperflare",
        ):
            self.assertEqual(self.by_id[move_id]["status"], "INEXACT", move_id)
        # Singles-exact moves stay PASS; Brick Break / Psychic Fangs keep exact
        # damage with a coarse field-change flag (INEXACT).
        for move_id in ("fusionbolt", "fusionflare", "pollenpuff"):
            self.assertEqual(self.by_id[move_id]["status"], "PASS", move_id)
        for move_id in ("brickbreak", "psychicfangs"):
            self.assertEqual(self.by_id[move_id]["status"], "INEXACT", move_id)

    def test_all_moves_classified_and_no_wrong_exact(self):
        summary = self.report["summary"]
        self.assertEqual(summary["FAIL"], 0)
        self.assertEqual(sum(summary.values()), 350)
        self.assertEqual(summary["NOT_RELEVANT"], 0)
        self.assertGreater(summary["PASS"], 0)
        self.assertGreater(summary["INEXACT"], 0)


if __name__ == "__main__":
    unittest.main()
