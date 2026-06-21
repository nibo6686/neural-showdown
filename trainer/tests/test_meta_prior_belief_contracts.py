import dataclasses
import unittest

from neural.meta_prior import (
    FixtureMetaPriorSource,
    JointQuality,
    SetHypothesis,
    SetPrior,
    SourceKind,
)
from neural.opponent_set_belief import (
    EvidenceKind,
    PublicEvidence,
    belief_from_public_prefix,
    initialize_belief,
    public_evidence_from_protocol_lines,
)


FORMAT = "gen9fixture"
SPECIES = "Hatterene"


def _source(*, other_mass=0.0):
    known_mass = 1.0 - other_mass
    prior = SetPrior(
        species_form_key=SPECIES,
        hypotheses=(
            SetHypothesis(
                "bounce-boots",
                known_mass * 0.6,
                ability="Magic Bounce",
                item="Heavy-Duty Boots",
                moves=("Psychic", "Nuzzle", "Mystical Fire", "Healing Wish"),
                tera_type="Water",
                roles=("utility",),
            ),
            SetHypothesis(
                "healer-leftovers",
                known_mass * 0.4,
                ability="Healer",
                item="Leftovers",
                moves=("Psychic", "Dazzling Gleam", "Calm Mind", "Draining Kiss"),
                tera_type="Fairy",
                roles=("setup",),
            ),
        ),
        other_mass=other_mass,
        joint_quality=JointQuality.EXACT,
    )
    return FixtureMetaPriorSource(format_id=FORMAT, priors={SPECIES: prior})


class MetaPriorContractTest(unittest.TestCase):
    def test_fixture_source_has_version_checksum_and_source_metadata(self):
        source = _source()
        self.assertEqual(source.metadata.source_kind, SourceKind.FIXTURE)
        self.assertEqual(len(source.metadata.source_sha256), 64)
        self.assertEqual(source.metadata.format_id, FORMAT)
        self.assertEqual(source.metadata.sample_count, 2)
        self.assertEqual(
            source.metadata.source_sha256, _source().metadata.source_sha256
        )

    def test_prior_preserves_joint_hypotheses(self):
        prior = _source().prior_for(FORMAT, SPECIES)
        self.assertEqual(prior.support_size, 2)
        bounce = prior.hypotheses[0]
        self.assertEqual(bounce.ability, "magicbounce")
        self.assertEqual(bounce.item, "heavydutyboots")
        self.assertIn("nuzzle", bounce.moves)

    def test_format_mismatch_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "format mismatch"):
            _source().prior_for("gen9ou", SPECIES)


class OpponentSetBeliefUpdateTest(unittest.TestCase):
    def test_initialization_exposes_possible_not_confirmed_facts(self):
        belief = initialize_belief(
            _source(), format_id=FORMAT, species_form_key=SPECIES
        )
        self.assertEqual(
            belief.possible_abilities, {"magicbounce", "healer"}
        )
        self.assertIsNone(belief.confirmed.ability)
        self.assertEqual(belief.other_mass, 0.0)

    def test_revealed_move_filters_joint_hypotheses(self):
        belief = initialize_belief(
            _source(), format_id=FORMAT, species_form_key=SPECIES
        )
        updated = belief.update(
            PublicEvidence(EvidenceKind.MOVE_REVEALED, "Nuzzle", 3)
        )
        self.assertEqual(
            [hypothesis.hypothesis_id for hypothesis in updated.hypotheses],
            ["bounce-boots"],
        )
        self.assertEqual(updated.confirmed.moves, {"nuzzle"})
        self.assertEqual(updated.possible_items, {"heavydutyboots"})
        self.assertIn("healer-leftovers", updated.ruled_out.hypothesis_ids)
        self.assertIn("calmmind", updated.ruled_out.moves)
        self.assertNotIn("psychic", updated.ruled_out.moves)

    def test_ability_item_and_tera_reveals_confirm_and_rule_out(self):
        ability_belief = initialize_belief(
            _source(), format_id=FORMAT, species_form_key=SPECIES
        )
        ability_belief = ability_belief.update(
            PublicEvidence(EvidenceKind.ABILITY_REVEALED, "Magic Bounce", 1)
        )
        item_belief = initialize_belief(
            _source(), format_id=FORMAT, species_form_key=SPECIES
        )
        item_belief = item_belief.update(
            PublicEvidence(EvidenceKind.ITEM_REVEALED, "Heavy-Duty Boots", 1)
        )
        tera_belief = initialize_belief(
            _source(), format_id=FORMAT, species_form_key=SPECIES
        )
        tera_belief = tera_belief.update(
            PublicEvidence(EvidenceKind.TERA_TYPE_REVEALED, "Water", 1)
        )
        self.assertEqual(ability_belief.confirmed.ability, "magicbounce")
        self.assertEqual(item_belief.confirmed.item, "heavydutyboots")
        self.assertEqual(tera_belief.confirmed.tera_type, "water")
        self.assertIn("healer", ability_belief.ruled_out.abilities)
        self.assertIn("leftovers", item_belief.ruled_out.items)
        self.assertIn("fairy", tera_belief.ruled_out.tera_types)

    def test_unknown_tail_is_retained_and_renormalized(self):
        belief = initialize_belief(
            _source(other_mass=0.2), format_id=FORMAT, species_form_key=SPECIES
        )
        updated = belief.update(
            PublicEvidence(EvidenceKind.MOVE_REVEALED, "Nuzzle", 1)
        )
        self.assertAlmostEqual(updated.hypotheses[0].probability, 0.48 / 0.68)
        self.assertAlmostEqual(updated.other_mass, 0.2 / 0.68)

    def test_contradictory_prior_falls_back_to_unknown_tail(self):
        belief = initialize_belief(
            _source(), format_id=FORMAT, species_form_key=SPECIES
        )
        updated = belief.update(
            PublicEvidence(EvidenceKind.MOVE_REVEALED, "Spore", 1)
        )
        self.assertTrue(updated.prior_contradiction)
        self.assertEqual(updated.hypotheses, ())
        self.assertEqual(updated.other_mass, 1.0)
        self.assertEqual(updated.confirmed.moves, {"spore"})

    def test_missing_prior_is_explicit_unknown_not_contradiction(self):
        belief = initialize_belief(
            _source(), format_id=FORMAT, species_form_key="MissingNo"
        )
        self.assertFalse(belief.source_available)
        self.assertFalse(belief.prior_contradiction)
        self.assertEqual(belief.hypotheses, ())
        self.assertEqual(belief.other_mass, 1.0)
        updated = belief.update(
            PublicEvidence(EvidenceKind.MOVE_REVEALED, "Splash", 1)
        )
        self.assertEqual(updated.confirmed.moves, {"splash"})
        self.assertEqual(updated.other_mass, 1.0)
        self.assertFalse(updated.prior_contradiction)

    def test_updates_are_immutable_and_ordered(self):
        original = initialize_belief(
            _source(), format_id=FORMAT, species_form_key=SPECIES
        )
        updated = original.update(
            PublicEvidence(EvidenceKind.MOVE_REVEALED, "Nuzzle", 5)
        )
        self.assertEqual(len(original.hypotheses), 2)
        self.assertEqual(len(updated.hypotheses), 1)
        same_line = updated.update(
            PublicEvidence(EvidenceKind.ITEM_REVEALED, "Heavy-Duty Boots", 5)
        )
        self.assertEqual(same_line.confirmed.item, "heavydutyboots")
        with self.assertRaisesRegex(ValueError, "non-decreasing"):
            updated.update(
                PublicEvidence(EvidenceKind.ITEM_REVEALED, "Leftovers", 4)
            )


def _itemless_source(*, other_mass=0.0):
    known_mass = 1.0 - other_mass
    prior = SetPrior(
        species_form_key=SPECIES,
        hypotheses=(
            SetHypothesis(
                "bounce",
                known_mass * 0.5,
                ability="Magic Bounce",
                item=None,
                moves=("Psychic", "Nuzzle"),
                tera_type="Water",
                roles=("utility",),
            ),
            SetHypothesis(
                "healer",
                known_mass * 0.5,
                ability="Healer",
                item=None,
                moves=("Calm Mind", "Draining Kiss"),
                tera_type="Fairy",
                roles=("setup",),
            ),
        ),
        other_mass=other_mass,
        joint_quality=JointQuality.FACTORIZED,
    )
    return FixtureMetaPriorSource(format_id=FORMAT, priors={SPECIES: prior})


class SourceAbsentDimensionTest(unittest.TestCase):
    def test_item_reveal_on_itemless_prior_preserves_hypotheses(self):
        belief = initialize_belief(
            _itemless_source(other_mass=0.2),
            format_id=FORMAT,
            species_form_key=SPECIES,
        )
        updated = belief.update(
            PublicEvidence(EvidenceKind.ITEM_REVEALED, "Choice Specs", 1)
        )
        self.assertFalse(updated.prior_contradiction)
        self.assertEqual(updated.confirmed.item, "choicespecs")
        self.assertEqual(len(updated.hypotheses), 2)
        self.assertEqual(updated.other_mass, belief.other_mass)
        self.assertEqual(updated.ruled_out.items, frozenset())
        self.assertFalse(updated.evidence_ledger[-1].source_covered)

    def test_source_covered_move_contradiction_still_explicit(self):
        belief = initialize_belief(
            _itemless_source(), format_id=FORMAT, species_form_key=SPECIES
        )
        updated = belief.update(
            PublicEvidence(EvidenceKind.MOVE_REVEALED, "Spore", 1)
        )
        self.assertTrue(updated.prior_contradiction)
        self.assertEqual(updated.hypotheses, ())
        self.assertEqual(updated.other_mass, 1.0)
        self.assertTrue(updated.evidence_ledger[-1].source_covered)

    def test_current_state_only_evidence_never_filters_or_contradicts(self):
        belief = initialize_belief(
            _itemless_source(), format_id=FORMAT, species_form_key=SPECIES
        )
        # A copied/forme current-state reveal incompatible with every hypothesis
        # is recorded in the ledger but must not filter, rule out, or contradict.
        updated = belief.update(
            PublicEvidence(
                EvidenceKind.ABILITY_REVEALED,
                "Volt Absorb",
                1,
                current_state_only=True,
            )
        )
        self.assertFalse(updated.prior_contradiction)
        self.assertEqual(len(updated.hypotheses), len(belief.hypotheses))
        self.assertEqual(updated.other_mass, belief.other_mass)
        self.assertIsNone(updated.confirmed.ability)
        self.assertEqual(updated.ruled_out.abilities, frozenset())
        self.assertTrue(updated.evidence_ledger[-1].current_state_only)


class PublicPrefixNoLeakageTest(unittest.TestCase):
    def test_safe_protocol_evidence_and_reflection_attribution(self):
        lines = [
            "|turn|1",
            "|move|p2a: Hatterene|Psychic|p1a: Tauros",
            "|-ability|p2a: Hatterene|Magic Bounce",
            "|-item|p2a: Hatterene|Heavy-Duty Boots",
            "|-terastallize|p2a: Hatterene|Water",
            "|move|p2a: Hatterene|Defog|p1a: Tauros|[from] ability: Magic Bounce",
            "|-activate|p2a: Hatterene|ability: Magic Bounce",
            "|-activate|p2a: Hatterene|item: Heavy-Duty Boots",
            "|-immune|p2a: Hatterene",
        ]
        evidence = public_evidence_from_protocol_lines(lines, opponent_side="p2")
        self.assertEqual(
            [(row.kind, row.value) for row in evidence],
            [
                (EvidenceKind.MOVE_REVEALED, "psychic"),
                (EvidenceKind.ABILITY_REVEALED, "magicbounce"),
                (EvidenceKind.ITEM_REVEALED, "heavydutyboots"),
                (EvidenceKind.TERA_TYPE_REVEALED, "water"),
                (EvidenceKind.ABILITY_REVEALED, "magicbounce"),
                (EvidenceKind.ABILITY_REVEALED, "magicbounce"),
                (EvidenceKind.ITEM_REVEALED, "heavydutyboots"),
            ],
        )
        self.assertNotIn("defog", [row.value for row in evidence])

    def test_future_reveal_does_not_change_earlier_belief(self):
        prefix = [
            "|turn|1",
            "|move|p2a: Hatterene|Psychic|p1a: Tauros",
        ]
        full = [
            *prefix,
            "|turn|2",
            "|-ability|p2a: Hatterene|Magic Bounce",
        ]
        from_prefix = belief_from_public_prefix(
            _source(),
            format_id=FORMAT,
            species_form_key=SPECIES,
            protocol_lines=prefix,
            opponent_side="p2",
        )
        from_full_at_prefix = belief_from_public_prefix(
            _source(),
            format_id=FORMAT,
            species_form_key=SPECIES,
            protocol_lines=full,
            opponent_side="p2",
            through_line=len(prefix),
        )
        self.assertEqual(from_prefix, from_full_at_prefix)
        after_reveal = belief_from_public_prefix(
            _source(),
            format_id=FORMAT,
            species_form_key=SPECIES,
            protocol_lines=full,
            opponent_side="p2",
        )
        self.assertIsNone(from_prefix.confirmed.ability)
        self.assertEqual(after_reveal.confirmed.ability, "magicbounce")

    def test_hidden_truth_perturbation_cannot_change_public_belief(self):
        lines = [
            "|turn|1",
            "|move|p2a: Hatterene|Psychic|p1a: Tauros",
        ]
        hidden_a = {
            "ability": "Magic Bounce",
            "item": "Heavy-Duty Boots",
            "moves": ["Nuzzle"],
            "tera_type": "Water",
        }
        hidden_b = {
            "ability": "Truant",
            "item": "Choice Band",
            "moves": ["Splash"],
            "tera_type": "Bug",
        }
        first = belief_from_public_prefix(
            _source(),
            format_id=FORMAT,
            species_form_key=SPECIES,
            protocol_lines=lines,
            opponent_side="p2",
        )
        second = belief_from_public_prefix(
            _source(),
            format_id=FORMAT,
            species_form_key=SPECIES,
            protocol_lines=lines,
            opponent_side="p2",
        )
        self.assertNotEqual(hidden_a, hidden_b)
        self.assertEqual(first, second)
        self.assertFalse(
            {"hidden_truth", "actual_set", "packed_team"}
            & {field.name for field in dataclasses.fields(first)}
        )

    def test_switch_damage_speed_and_generic_immunity_are_non_evidence(self):
        lines = [
            "|turn|1",
            "|switch|p2a: Hatterene|Hatterene, L80|100/100",
            "|-damage|p2a: Hatterene|60/100",
            "|-immune|p2a: Hatterene",
            "|turn|2",
        ]
        evidence = public_evidence_from_protocol_lines(lines, opponent_side="p2")
        self.assertEqual(evidence, ())


if __name__ == "__main__":
    unittest.main()
