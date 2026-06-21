"""Characterization tests for the Randbats joint-set posterior fidelity audit.

These tests document the *current* behavior of the pinned role-data source plus
the public-prefix posterior on real ``sets.json`` species.  They show which joint
set correlations the existing factorized adapter already preserves (role-bundled
move/ability/Tera collapse) and the one source-faithfulness gap it does not
(item reveals falsely contradicting a role-only source).  They are not a v8
feature/schema change and assert behavior only on the checked-in source.
"""

import unittest

from neural.opponent_set_belief import (
    EvidenceKind,
    PublicEvidence,
    initialize_belief,
    public_evidence_from_protocol_lines,
)
from neural.opponent_set_belief_replay_adapter import build_replay_prefix_beliefs
from neural.parse_replay_logs import parse_protocol_log
from neural.randbats_meta_prior_audit import _classify_contradiction
from neural.randbats_meta_prior_source import RandbatsMetaPriorSource

FORMAT = "gen9randombattle"


def _roles(belief):
    return {role for hyp in belief.hypotheses for role in hyp.roles}


class RandbatsJointSetPosteriorFidelityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = RandbatsMetaPriorSource()

    def test_ability_reveal_rules_out_alternative_ability(self):
        # Clodsire lists Unaware and Water Absorb in both sets.  Revealing one
        # rules out the other while leaving every role hypothesis alive.
        belief = initialize_belief(
            self.source, format_id=FORMAT, species_form_key="Clodsire"
        )
        self.assertEqual(belief.possible_abilities, {"unaware", "waterabsorb"})
        updated = belief.update(
            PublicEvidence(EvidenceKind.ABILITY_REVEALED, "Water Absorb", 1)
        )
        self.assertEqual(updated.possible_abilities, {"waterabsorb"})
        self.assertIn("unaware", updated.ruled_out.abilities)
        self.assertEqual(_roles(updated), {"bulkyattacker", "bulkysupport"})
        self.assertFalse(updated.prior_contradiction)

    def test_move_reveal_collapses_to_compatible_role(self):
        # Curse appears only in Clodsire's Bulky Attacker movepool and Spikes
        # only in Bulky Support, so one move reveal collapses the posterior to a
        # coherent role rather than merely updating an independent move marginal.
        belief = initialize_belief(
            self.source, format_id=FORMAT, species_form_key="Clodsire"
        )
        self.assertEqual(_roles(belief), {"bulkyattacker", "bulkysupport"})

        curse = belief.update(
            PublicEvidence(EvidenceKind.MOVE_REVEALED, "Curse", 1)
        )
        self.assertEqual(_roles(curse), {"bulkyattacker"})
        self.assertIn("curse", curse.confirmed.moves)

        spikes = belief.update(
            PublicEvidence(EvidenceKind.MOVE_REVEALED, "Spikes", 1)
        )
        self.assertEqual(_roles(spikes), {"bulkysupport"})

    def test_tera_reveal_filters_role_specific_support(self):
        # Gholdengo's two sets carry different Tera lists; Tera Fighting only
        # appears on the Bulky Attacker set, so the reveal filters the posterior
        # down to that role's joint hypothesis.
        belief = initialize_belief(
            self.source, format_id=FORMAT, species_form_key="Gholdengo"
        )
        self.assertEqual(_roles(belief), {"bulkyattacker", "bulkysupport"})
        updated = belief.update(
            PublicEvidence(EvidenceKind.TERA_TYPE_REVEALED, "Fighting", 1)
        )
        self.assertEqual(updated.possible_tera_types, {"fighting"})
        self.assertEqual(_roles(updated), {"bulkyattacker"})
        self.assertFalse(updated.prior_contradiction)

    def test_reflected_move_does_not_pollute_reflector_moveset(self):
        # A move row attributed to Magic Bounce confirms the reflector's ability
        # but must not be admitted as one of the reflector's own moves.
        lines = [
            "|switch|p2a: Hatterene|Hatterene, L85, F|100/100",
            "|turn|1",
            "|move|p1a: Ting-Lu|Stealth Rock|p2a: Hatterene",
            "|move|p2a: Hatterene|Stealth Rock|p1a: Ting-Lu"
            "|[from] ability: Magic Bounce|[of] p1a: Ting-Lu",
        ]
        evidence = public_evidence_from_protocol_lines(lines, opponent_side="p2")
        kinds = {(e.kind, e.value) for e in evidence}
        self.assertIn((EvidenceKind.ABILITY_REVEALED, "magicbounce"), kinds)
        self.assertNotIn((EvidenceKind.MOVE_REVEALED, "stealthrock"), kinds)

    def test_item_reveal_on_source_without_items_preserves_posterior(self):
        # Items are absent from sets.json (source-absent dimension).  An item
        # reveal must be recorded as a confirmed public fact while leaving the
        # role/ability/move/Tera posterior and the unknown tail untouched -- no
        # false contradiction.
        belief = initialize_belief(
            self.source, format_id=FORMAT, species_form_key="Gholdengo"
        )
        before_roles = _roles(belief)
        before_tera = belief.possible_tera_types
        before_abilities = belief.possible_abilities
        before_tail = belief.other_mass

        updated = belief.update(
            PublicEvidence(EvidenceKind.ITEM_REVEALED, "Leftovers", 1)
        )
        self.assertFalse(updated.prior_contradiction)
        self.assertEqual(updated.confirmed.item, "leftovers")
        self.assertEqual(len(updated.hypotheses), len(belief.hypotheses))
        self.assertEqual(_roles(updated), before_roles)
        self.assertEqual(updated.possible_tera_types, before_tera)
        self.assertEqual(updated.possible_abilities, before_abilities)
        self.assertEqual(updated.other_mass, before_tail)
        # The ledger marks the dimension as not source-covered.
        self.assertFalse(updated.evidence_ledger[-1].source_covered)
        self.assertEqual(updated.ruled_out.items, frozenset())

    def test_item_reveal_then_move_reveal_still_collapses_role(self):
        # An earlier source-absent item reveal must not block a later
        # source-covered move reveal from collapsing the role.
        belief = initialize_belief(
            self.source, format_id=FORMAT, species_form_key="Clodsire"
        )
        with_item = belief.update(
            PublicEvidence(EvidenceKind.ITEM_REVEALED, "Leftovers", 1)
        )
        collapsed = with_item.update(
            PublicEvidence(EvidenceKind.MOVE_REVEALED, "Curse", 2)
        )
        self.assertEqual(_roles(collapsed), {"bulkyattacker"})
        self.assertEqual(collapsed.confirmed.item, "leftovers")
        self.assertIn("curse", collapsed.confirmed.moves)

    def test_poltergeist_item_confirms_without_nuking_posterior(self):
        # Poltergeist reveals the holder's item via -activate move: Poltergeist.
        trace = parse_protocol_log(
            [
                "|switch|p2a: Gholdengo|Gholdengo, L77|100/100",
                "|turn|1",
                "|-activate|p2a: Gholdengo|move: Poltergeist|Leftovers",
            ],
            replay_id="poltergeist-item-no-nuke",
            format_name=FORMAT,
        )
        snapshot = build_replay_prefix_beliefs(
            trace, self.source, perspective_side="p1"
        )
        slot = snapshot.slots_for_species("Gholdengo")[0]
        self.assertEqual(slot.belief.confirmed.item, "leftovers")
        self.assertFalse(slot.belief.prior_contradiction)
        self.assertEqual(len(slot.belief.hypotheses), 6)
        self.assertEqual(slot.belief.possible_abilities, {"goodasgold"})

    def test_item_activation_confirms_without_nuking_posterior(self):
        # A plain item activation row is also source-absent for Randbats.
        trace = parse_protocol_log(
            [
                "|switch|p2a: Gholdengo|Gholdengo, L77|100/100",
                "|turn|1",
                "|-activate|p2a: Gholdengo|item: Leftovers",
            ],
            replay_id="item-activation-no-nuke",
            format_name=FORMAT,
        )
        snapshot = build_replay_prefix_beliefs(
            trace, self.source, perspective_side="p1"
        )
        slot = snapshot.slots_for_species("Gholdengo")[0]
        self.assertEqual(slot.belief.confirmed.item, "leftovers")
        self.assertFalse(slot.belief.prior_contradiction)
        self.assertEqual(len(slot.belief.hypotheses), 6)

    def test_source_covered_ability_contradiction_still_explicit(self):
        # Abilities are source-covered: a reveal incompatible with every
        # hypothesis must still produce an explicit contradiction routed to the
        # unknown tail, so real source/data mismatches stay visible.
        belief = initialize_belief(
            self.source, format_id=FORMAT, species_form_key="Gholdengo"
        )
        updated = belief.update(
            PublicEvidence(EvidenceKind.ABILITY_REVEALED, "Levitate", 1)
        )
        self.assertTrue(updated.prior_contradiction)
        self.assertEqual(updated.hypotheses, ())
        self.assertEqual(updated.other_mass, 1.0)
        self.assertTrue(updated.evidence_ledger[-1].source_covered)
        self.assertTrue(updated.evidence_ledger[-1].contradiction)
        self.assertEqual(updated.confirmed.ability, "levitate")

    def test_missing_species_records_facts_and_keeps_unknown_mass(self):
        belief = initialize_belief(
            self.source, format_id=FORMAT, species_form_key="MissingNo"
        )
        self.assertFalse(belief.source_available)
        updated = belief.update(
            PublicEvidence(EvidenceKind.ITEM_REVEALED, "Choice Band", 1)
        ).update(PublicEvidence(EvidenceKind.MOVE_REVEALED, "Splash", 2))
        self.assertFalse(updated.prior_contradiction)
        self.assertEqual(updated.other_mass, 1.0)
        self.assertEqual(updated.confirmed.item, "choiceband")
        self.assertEqual(updated.confirmed.moves, {"splash"})

    def test_item_evidence_never_consults_prior_hidden_truth(self):
        # Differing hidden-truth annotations must not change the public belief
        # produced after an item reveal.
        lines = [
            "|switch|p2a: Gholdengo|Gholdengo, L77|100/100",
            "|turn|1",
            "|-item|p2a: Gholdengo|Leftovers",
        ]
        trace_a = parse_protocol_log(
            list(lines), replay_id="item-no-leak-a", format_name=FORMAT
        )
        trace_b = parse_protocol_log(
            list(lines), replay_id="item-no-leak-b", format_name=FORMAT
        )
        trace_a["hidden_opponent_truth"] = {"item": "Choice Specs"}
        trace_b["hidden_opponent_truth"] = {"item": "Air Balloon"}
        first = build_replay_prefix_beliefs(
            trace_a, self.source, perspective_side="p1"
        )
        second = build_replay_prefix_beliefs(
            trace_b, self.source, perspective_side="p1"
        )
        self.assertEqual(first.slots, second.slots)
        self.assertEqual(
            first.slots_for_species("Gholdengo")[0].belief.confirmed.item,
            "leftovers",
        )


class RandbatsContradictionClassifierTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = RandbatsMetaPriorSource()

    def test_classifier_buckets_remaining_contradictions(self):
        # Trace marker and Imposter/Trace-carrier displayed copies are dynamic
        # copied state, not base-set facts.
        self.assertEqual(
            _classify_contradiction("bellossom", "ability_revealed", "trace", self.source),
            "dynamic_or_copied_state",
        )
        self.assertEqual(
            _classify_contradiction("gardevoir", "ability_revealed", "sapsipper", self.source),
            "dynamic_or_copied_state",
        )
        self.assertEqual(
            _classify_contradiction("ditto", "move_revealed", "closecombat", self.source),
            "dynamic_or_copied_state",
        )
        # Forme/identity-tied abilities stored under the base forme key.
        self.assertEqual(
            _classify_contradiction("calyrexice", "ability_revealed", "asone", self.source),
            "composite_or_forme_ability",
        )
        self.assertEqual(
            _classify_contradiction("terapagos", "ability_revealed", "terashell", self.source),
            "composite_or_forme_ability",
        )
        # Struggle is never a set move.
        self.assertEqual(
            _classify_contradiction("dragalge", "move_revealed", "struggle", self.source),
            "universal_move_noise",
        )
        # A genuinely undeclared ability is a real source limitation.
        self.assertEqual(
            _classify_contradiction("leavanny", "ability_revealed", "pickpocket", self.source),
            "true_source_limitation",
        )


if __name__ == "__main__":
    unittest.main()
