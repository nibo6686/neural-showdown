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

    def test_item_reveal_currently_contradicts_role_only_source(self):
        # Documented fidelity gap: items are absent from sets.json, so an item
        # reveal matches no hypothesis and the current posterior collapses the
        # entire role/move/ability/Tera support to a contradiction tail instead
        # of absorbing the item into the explicit unknown mass.
        belief = initialize_belief(
            self.source, format_id=FORMAT, species_form_key="Gholdengo"
        )
        updated = belief.update(
            PublicEvidence(EvidenceKind.ITEM_REVEALED, "Leftovers", 1)
        )
        self.assertTrue(updated.prior_contradiction)
        self.assertEqual(updated.hypotheses, ())
        self.assertEqual(updated.other_mass, 1.0)
        # The confirmed item is still retained as a public fact.
        self.assertEqual(updated.confirmed.item, "leftovers")


if __name__ == "__main__":
    unittest.main()
