import copy
import unittest

from neural.meta_prior import JointQuality, SetHypothesis, SetPrior
from neural.opponent_set_belief_replay_adapter import (
    build_replay_prefix_beliefs,
    fixture_source_for_species,
)
from neural.parse_replay_logs import parse_protocol_log


FORMAT = "gen9randombattle"


def _prior(species, *hypotheses, other_mass=0.0):
    return SetPrior(
        species_form_key=species,
        hypotheses=tuple(hypotheses),
        other_mass=other_mass,
        joint_quality=JointQuality.EXACT,
    )


def _hypothesis(
    hypothesis_id,
    probability,
    *,
    ability=None,
    item=None,
    moves=(),
    tera_type=None,
):
    return SetHypothesis(
        hypothesis_id,
        probability,
        ability=ability,
        item=item,
        moves=moves,
        tera_type=tera_type,
    )


def _source():
    return fixture_source_for_species(
        format_id=FORMAT,
        priors={
            "Hatterene": _prior(
                "Hatterene",
                _hypothesis(
                    "bounce",
                    0.75,
                    ability="Magic Bounce",
                    item="Leftovers",
                    moves=("Psychic", "Nuzzle", "Mystical Fire", "Draining Kiss"),
                    tera_type="Steel",
                ),
                _hypothesis(
                    "healer",
                    0.25,
                    ability="Healer",
                    item="Heavy-Duty Boots",
                    moves=("Psychic", "Calm Mind", "Dazzling Gleam"),
                    tera_type="Fairy",
                ),
            ),
            "Chi-Yu": _prior(
                "Chi-Yu",
                _hypothesis(
                    "boots",
                    0.6,
                    ability="Beads of Ruin",
                    item="Heavy-Duty Boots",
                    moves=("Dark Pulse", "Nasty Plot"),
                ),
                _hypothesis(
                    "specs",
                    0.4,
                    ability="Beads of Ruin",
                    item="Choice Specs",
                    moves=("Dark Pulse", "Overheat"),
                ),
            ),
            "Avalugg": _prior(
                "Avalugg",
                _hypothesis(
                    "physical",
                    1.0,
                    ability="Sturdy",
                    item="Heavy-Duty Boots",
                    moves=("Body Press", "Recover", "Rapid Spin", "Avalanche"),
                ),
            ),
            "Zoroark-Hisui": _prior(
                "Zoroark-Hisui",
                _hypothesis(
                    "illusion",
                    1.0,
                    ability="Illusion",
                    item="Life Orb",
                    moves=("Will-O-Wisp", "Poltergeist", "Focus Blast"),
                ),
            ),
        },
    )


def _trajectory(replay_id, lines):
    return parse_protocol_log(
        lines,
        replay_id=replay_id,
        format_name=FORMAT,
    )


class RealReplayPrefixParityTest(unittest.TestCase):
    def test_magic_bounce_reflected_defog_is_ability_not_move(self):
        # Exact public rows from gen9randombattle-2589608300.
        trace = _trajectory(
            "gen9randombattle-2589608300",
            [
                "|switch|p2a: Hatterene|Hatterene, L85, F|236/236|[from] Flip Turn",
                "|turn|6",
                "|move|p1a: Weezing|Defog|p2a: Hatterene",
                "|move|p2a: Hatterene|Defog|p1a: Weezing|[from] ability: Magic Bounce",
                "|-unboost|p1a: Weezing|evasion|1",
                "|turn|24",
                "|move|p2a: Hatterene|Psychic|p1a: Bastiodon",
            ],
        )
        before_psychic = build_replay_prefix_beliefs(
            trace, _source(), perspective_side="p1", through_turn=6
        )
        belief = before_psychic.active_slots[0].belief
        self.assertEqual(belief.confirmed.ability, "magicbounce")
        self.assertNotIn("defog", belief.confirmed.moves)
        self.assertNotIn("psychic", belief.confirmed.moves)

        full = build_replay_prefix_beliefs(trace, _source(), perspective_side="p1")
        self.assertIn("psychic", full.active_slots[0].belief.confirmed.moves)

    def test_magic_bounce_will_o_wisp_and_tera_reveal_share_correct_actor(self):
        # Exact public rows from gen9randombattle-2594129364.
        trace = _trajectory(
            "gen9randombattle-2594129364",
            [
                "|switch|p2a: Hatterene|Hatterene, L85, F|236/236",
                "|turn|2",
                "|-terastallize|p2a: Hatterene|Steel",
                "|move|p1a: Misdreavus|Will-O-Wisp|p2a: Hatterene",
                "|move|p2a: Hatterene|Will-O-Wisp|p1a: Misdreavus|[from] ability: Magic Bounce",
                "|-status|p1a: Misdreavus|brn",
                "|move|p2a: Hatterene|Nuzzle|p1a: Misdreavus",
            ],
        )
        snapshot = build_replay_prefix_beliefs(
            trace, _source(), perspective_side="p1"
        )
        belief = snapshot.active_slots[0].belief
        self.assertEqual(belief.confirmed.ability, "magicbounce")
        self.assertEqual(belief.confirmed.tera_type, "steel")
        self.assertEqual(belief.confirmed.moves, {"nuzzle"})
        self.assertNotIn("willowisp", belief.confirmed.moves)

    def test_illusion_replace_does_not_rewrite_earlier_displayed_species(self):
        # Exact public rows from gen9randombattle-2593348981.
        lines = [
            "|switch|p1a: Avalugg|Avalugg, L88, F|219/219",
            "|switch|p2a: Froslass|Froslass, L87, F|263/263",
            "|turn|1",
            "|move|p1a: Avalugg|Will-O-Wisp|p2a: Froslass",
            "|turn|8",
            "|move|p1a: Avalugg|Focus Blast|p2a: Chi-Yu|[miss]",
            "|move|p2a: Chi-Yu|Dark Pulse|p1a: Avalugg",
            "|-damage|p1a: Avalugg|0 fnt",
            "|replace|p1a: Zoroark|Zoroark-Hisui, L80, M",
            "|-end|p1a: Zoroark|Illusion",
            "|faint|p1a: Zoroark",
        ]
        trace = _trajectory("gen9randombattle-2593348981", lines)
        prefix = build_replay_prefix_beliefs(
            trace, _source(), perspective_side="p2", through_line=8
        )
        self.assertEqual(len(prefix.known_slots), 1)
        self.assertEqual(prefix.known_slots[0].species_form_key, "avalugg")
        self.assertEqual(
            prefix.known_slots[0].belief.confirmed.moves,
            {"willowisp", "focusblast"},
        )

        revealed = build_replay_prefix_beliefs(
            trace, _source(), perspective_side="p2"
        )
        self.assertEqual(
            [slot.species_form_key for slot in revealed.known_slots],
            ["avalugg", "zoroarkhisui"],
        )
        disguise, actual = revealed.known_slots
        self.assertTrue(disguise.identity_ambiguous)
        self.assertEqual(disguise.superseded_by, actual.slot_key)
        self.assertEqual(actual.belief.confirmed.moves, frozenset())
        self.assertEqual(prefix.known_slots[0].belief, disguise.belief)

    def test_ordinary_ability_item_and_move_reveals(self):
        # Exact public rows from gen9randombattle-2593348981.
        trace = _trajectory(
            "gen9randombattle-2593348981",
            [
                "|switch|p2a: Chi-Yu|Chi-Yu, L77|211/211",
                "|-ability|p2a: Chi-Yu|Beads of Ruin",
                "|turn|7",
                "|move|p1a: Avalugg|Poltergeist|p2a: Chi-Yu",
                "|-activate|p2a: Chi-Yu|move: Poltergeist|Heavy-Duty Boots",
                "|move|p2a: Chi-Yu|Nasty Plot|p2a: Chi-Yu",
            ],
        )
        snapshot = build_replay_prefix_beliefs(
            trace, _source(), perspective_side="p1"
        )
        belief = snapshot.active_slots[0].belief
        self.assertEqual(belief.confirmed.ability, "beadsofruin")
        self.assertEqual(belief.confirmed.item, "heavydutyboots")
        self.assertEqual(belief.confirmed.moves, {"nastyplot"})


class PrefixCausalityAndNoLeakageTest(unittest.TestCase):
    def test_future_reveal_cannot_change_earlier_snapshot(self):
        prefix = [
            "|switch|p2a: Hatterene|Hatterene, L85, F|236/236",
            "|turn|1",
            "|move|p2a: Hatterene|Psychic|p1a: Hitmontop",
        ]
        lines = [
            *prefix,
            "|turn|2",
            "|-terastallize|p2a: Hatterene|Steel",
            "|-ability|p2a: Hatterene|Magic Bounce",
        ]
        trace = _trajectory("future-reveal", lines)
        early = build_replay_prefix_beliefs(
            trace, _source(), perspective_side="p1", through_line=len(prefix)
        )
        same_prefix = build_replay_prefix_beliefs(
            _trajectory("future-reveal-mutated", [*lines, "|-item|p2a: Hatterene|Leftovers"]),
            _source(),
            perspective_side="p1",
            through_line=len(prefix),
        )
        self.assertEqual(early.slots, same_prefix.slots)
        self.assertIsNone(early.active_slots[0].belief.confirmed.ability)
        self.assertIsNone(early.active_slots[0].belief.confirmed.tera_type)

    def test_hidden_truth_fields_are_never_read(self):
        lines = [
            "|switch|p2a: Hatterene|Hatterene, L85, F|236/236",
            "|turn|1",
            "|move|p2a: Hatterene|Psychic|p1a: Hitmontop",
        ]
        first_trace = _trajectory("hidden-a", lines)
        second_trace = copy.deepcopy(first_trace)
        first_trace["hidden_opponent_truth"] = {
            "ability": "Magic Bounce",
            "item": "Leftovers",
        }
        second_trace["hidden_opponent_truth"] = {
            "ability": "Truant",
            "item": "Choice Band",
        }
        first = build_replay_prefix_beliefs(
            first_trace, _source(), perspective_side="p1"
        )
        second = build_replay_prefix_beliefs(
            second_trace, _source(), perspective_side="p1"
        )
        self.assertEqual(first.slots, second.slots)

    def test_non_evidence_rows_do_not_update_belief(self):
        trace = _trajectory(
            "non-evidence",
            [
                "|switch|p2a: Hatterene|Hatterene, L85, F|236/236",
                "|turn|1",
                "|-damage|p2a: Hatterene|120/236",
                "|-immune|p2a: Hatterene",
                "|switch|p2a: Hatterene|Hatterene, L85, F|120/236",
                "|move|p1a: Fastmon|Tackle|p2a: Hatterene",
            ],
        )
        snapshot = build_replay_prefix_beliefs(
            trace, _source(), perspective_side="p1"
        )
        belief = snapshot.active_slots[0].belief
        self.assertEqual(belief.evidence_ledger, ())
        self.assertEqual(belief.confirmed.moves, frozenset())
        self.assertIsNone(belief.confirmed.ability)
        self.assertIsNone(belief.confirmed.item)

    def test_named_immunity_is_safe_but_generic_immunity_is_not(self):
        source = fixture_source_for_species(
            format_id=FORMAT,
            priors={
                "Mismagius": _prior(
                    "Mismagius",
                    _hypothesis("levitate", 0.5, ability="Levitate"),
                    _hypothesis("other", 0.5, ability="Pressure"),
                )
            },
        )
        trace = _trajectory(
            "named-immunity",
            [
                "|switch|p2a: Mismagius|Mismagius, L84, F|100/100",
                "|-immune|p2a: Mismagius",
                "|-immune|p2a: Mismagius|[from] ability: Levitate",
            ],
        )
        snapshot = build_replay_prefix_beliefs(
            trace, source, perspective_side="p1"
        )
        belief = snapshot.active_slots[0].belief
        self.assertEqual(belief.confirmed.ability, "levitate")
        self.assertEqual(len(belief.evidence_ledger), 1)

    def test_missing_prior_preserves_explicit_unknown_tail(self):
        trace = _trajectory(
            "missing-prior",
            [
                "|switch|p2a: MissingNo|MissingNo, L100|100/100",
                "|move|p2a: MissingNo|Splash|p1a: Hatterene",
            ],
        )
        snapshot = build_replay_prefix_beliefs(
            trace, _source(), perspective_side="p1"
        )
        belief = snapshot.active_slots[0].belief
        self.assertFalse(belief.source_available)
        self.assertEqual(belief.other_mass, 1.0)
        self.assertEqual(belief.confirmed.moves, {"splash"})
        self.assertFalse(belief.prior_contradiction)


class TransformCopiedStateTest(unittest.TestCase):
    def _ditto_source(self):
        return fixture_source_for_species(
            format_id=FORMAT,
            priors={
                "Ditto": _prior(
                    "Ditto",
                    _hypothesis("imposter", 1.0, ability="Imposter", moves=("Transform",)),
                )
            },
        )

    def test_transform_copied_moves_and_abilities_are_current_state(self):
        trace = _trajectory(
            "ditto-transform",
            [
                "|switch|p2a: Ditto|Ditto, L84|100/100",
                "|-transform|p2a: Ditto|p1a: Koraidon|[from] ability: Imposter",
                "|turn|1",
                "|move|p2a: Ditto|Close Combat|p1a: Koraidon",
                "|-ability|p2a: Ditto|Orichalcum Pulse",
            ],
        )
        belief = build_replay_prefix_beliefs(
            trace, self._ditto_source(), perspective_side="p1"
        ).active_slots[0].belief
        # Base Imposter stays confirmed; copied move/ability never contradict and
        # are not added to Ditto's base confirmed facts.
        self.assertEqual(belief.confirmed.ability, "imposter")
        self.assertFalse(belief.prior_contradiction)
        self.assertNotIn("closecombat", belief.confirmed.moves)
        copied = [
            row.evidence.value
            for row in belief.evidence_ledger
            if row.current_state_only
        ]
        self.assertIn("closecombat", copied)
        self.assertIn("orichalcumpulse", copied)

    def test_switch_out_reverts_copied_state(self):
        trace = _trajectory(
            "ditto-transform-revert",
            [
                "|switch|p2a: Ditto|Ditto, L84|100/100",
                "|-transform|p2a: Ditto|p1a: Koraidon|[from] ability: Imposter",
                "|move|p2a: Ditto|Close Combat|p1a: Koraidon",
                "|switch|p2a: Gholdengo|Gholdengo, L77|100/100",
                "|switch|p2a: Ditto|Ditto, L84|50/100",
                "|move|p2a: Ditto|Transform|p1a: Koraidon",
            ],
        )
        # After switching back in (before re-transforming) the base Transform move
        # is real base evidence, not copied state.
        belief = build_replay_prefix_beliefs(
            trace, self._ditto_source(), perspective_side="p1"
        ).active_slots[0].belief
        self.assertFalse(belief.prior_contradiction)
        self.assertIn("transform", belief.confirmed.moves)


if __name__ == "__main__":
    unittest.main()
