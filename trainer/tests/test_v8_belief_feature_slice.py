"""Tests for the first append-only v8 belief feature slice."""

import unittest

from neural.benchmark_vnext_featuregen import _names_fingerprint
from neural.live_private_features import (
    FEATURE_DIM_V7,
    FEATURE_DIM_V8,
    FEATURE_NAMES_V7,
    FEATURE_NAMES_V8,
    FEATURE_VERSION_V7,
    FEATURE_VERSION_V8,
    V8_SLICE6_FEATURE_NAMES,
    active_opponent_set_belief,
    feature_schema,
)
from neural.opponent_set_belief import (
    EvidenceKind,
    PublicEvidence,
    initialize_belief,
)
from neural.parse_replay_logs import parse_protocol_log
from neural.randbats_meta_prior_source import RandbatsMetaPriorSource
from neural.v8_belief_features import (
    V8_BELIEF_FEATURE_NAMES,
    v8_belief_slice_feature_vector,
)

FORMAT = "gen9randombattle"

# Pinned frozen v7 state schema identity; v8 must not change it.
V7_FROZEN_DIM = 3208
V7_FROZEN_FINGERPRINT = (
    "0a697b427d64c4487e7513ae8a35d76387af6824f6f4404f62bac218a5e36fbf"
)


def _named(vector):
    return dict(zip(V8_BELIEF_FEATURE_NAMES, [float(x) for x in vector]))


class V7SchemaUnchangedTest(unittest.TestCase):
    def test_v7_dim_and_fingerprint_are_frozen(self):
        self.assertEqual(FEATURE_DIM_V7, V7_FROZEN_DIM)
        self.assertEqual(_names_fingerprint(FEATURE_NAMES_V7), V7_FROZEN_FINGERPRINT)

    def test_v8_is_append_only_relative_to_v7(self):
        self.assertEqual(FEATURE_NAMES_V8[:FEATURE_DIM_V7], FEATURE_NAMES_V7)
        self.assertEqual(FEATURE_DIM_V8, FEATURE_DIM_V7 + len(V8_SLICE6_FEATURE_NAMES))
        self.assertNotEqual(
            _names_fingerprint(FEATURE_NAMES_V8),
            _names_fingerprint(FEATURE_NAMES_V7),
        )

    def test_v8_slice_names_are_stable_and_ordered(self):
        # The wired slice equals the slice module's names, in order.
        self.assertEqual(V8_SLICE6_FEATURE_NAMES, V8_BELIEF_FEATURE_NAMES)
        self.assertEqual(len(V8_BELIEF_FEATURE_NAMES), len(set(V8_BELIEF_FEATURE_NAMES)))
        self.assertEqual(FEATURE_VERSION_V8, "live-private-belief-v8")

    def test_schema_exports_v8(self):
        schema = feature_schema()
        self.assertEqual(schema["v8_feature_version"], FEATURE_VERSION_V8)
        self.assertEqual(schema["v8_feature_dim"], FEATURE_DIM_V8)
        self.assertEqual(schema["v8_feature_names"][:FEATURE_DIM_V7], FEATURE_NAMES_V7)
        self.assertEqual(schema["v7_feature_version"], FEATURE_VERSION_V7)


class V8SliceValueTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = RandbatsMetaPriorSource()

    def _belief(self, species, *evidence):
        belief = initialize_belief(
            self.source, format_id=FORMAT, species_form_key=species
        )
        for ev in evidence:
            belief = belief.update(ev)
        return belief

    def test_missing_prior_is_explicit_unknown_not_silent_zeros(self):
        belief = self._belief("MissingNo")
        named = _named(v8_belief_slice_feature_vector(belief))
        self.assertEqual(named["opponent_belief_has_meta_prior"], 0.0)
        # Explicit unknown: full tail mass, not a silent zero.
        self.assertEqual(named["opponent_belief_prior_other_mass"], 1.0)

    def test_none_belief_is_explicit_unknown(self):
        named = _named(v8_belief_slice_feature_vector(None))
        self.assertEqual(named["opponent_belief_has_meta_prior"], 0.0)
        self.assertEqual(named["opponent_belief_prior_other_mass"], 1.0)

    def test_present_prior_exposes_source_quality_flags(self):
        named = _named(v8_belief_slice_feature_vector(self._belief("Gholdengo")))
        self.assertEqual(named["opponent_belief_has_meta_prior"], 1.0)
        self.assertEqual(named["opponent_belief_quality_factorized"], 1.0)
        self.assertEqual(named["opponent_belief_quality_coarse_movepool_support"], 1.0)
        self.assertEqual(named["opponent_belief_quality_item_unknown"], 1.0)
        self.assertEqual(named["opponent_belief_quality_uncalibrated_probabilities"], 1.0)
        self.assertGreater(named["opponent_belief_support_size_norm"], 0.0)

    def test_source_quality_flags_survive_supported_evidence_updates(self):
        named = _named(
            v8_belief_slice_feature_vector(
                self._belief(
                    "Clodsire",
                    PublicEvidence(EvidenceKind.MOVE_REVEALED, "Curse", 1),
                )
            )
        )
        self.assertEqual(named["opponent_belief_has_meta_prior"], 1.0)
        self.assertEqual(named["opponent_belief_quality_factorized"], 1.0)
        self.assertEqual(named["opponent_belief_quality_coarse_movepool_support"], 1.0)
        self.assertEqual(named["opponent_belief_quality_item_unknown"], 1.0)
        self.assertEqual(named["opponent_belief_quality_uncalibrated_probabilities"], 1.0)

    def test_alias_flag_is_set_for_aliased_prior(self):
        named = _named(v8_belief_slice_feature_vector(self._belief("Palafin-Hero")))
        self.assertEqual(named["opponent_belief_has_meta_prior"], 1.0)
        self.assertEqual(named["opponent_belief_prior_alias_used"], 1.0)

    def test_confirmed_and_ruled_out_counts_track_evidence(self):
        # A move reveal collapses Clodsire to a role and confirms the move.
        belief = self._belief(
            "Clodsire",
            PublicEvidence(EvidenceKind.MOVE_REVEALED, "Curse", 1),
        )
        named = _named(v8_belief_slice_feature_vector(belief))
        self.assertFalse(named["opponent_belief_prior_contradiction"])
        self.assertGreater(named["opponent_belief_confirmed_fact_count_norm"], 0.0)

    def test_source_absent_item_reveal_shows_in_slice(self):
        belief = self._belief(
            "Gholdengo",
            PublicEvidence(EvidenceKind.ITEM_REVEALED, "Leftovers", 1),
        )
        named = _named(v8_belief_slice_feature_vector(belief))
        self.assertFalse(named["opponent_belief_prior_contradiction"])
        self.assertGreater(named["opponent_belief_source_absent_fact_count_norm"], 0.0)
        self.assertEqual(named["opponent_belief_confirmed_item_known"], 1.0)

    def test_true_source_limitation_remains_visible_as_contradiction(self):
        belief = self._belief(
            "Leavanny",
            PublicEvidence(EvidenceKind.ABILITY_REVEALED, "Pickpocket", 1),
        )
        named = _named(v8_belief_slice_feature_vector(belief))
        self.assertEqual(named["opponent_belief_prior_contradiction"], 1.0)


class V8NoLeakageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = RandbatsMetaPriorSource()

    def _slice_from_lines(self, lines, *, through_turn=None):
        trace = parse_protocol_log(lines, replay_id="v8-leak", format_name=FORMAT)
        belief = active_opponent_set_belief(
            trace, player_side="p1", through_turn=through_turn
        )
        return v8_belief_slice_feature_vector(belief)

    def test_hidden_truth_perturbation_does_not_change_v8_features(self):
        lines = [
            "|switch|p2a: Gholdengo|Gholdengo, L77|100/100",
            "|turn|1",
            "|move|p2a: Gholdengo|Make It Rain|p1a: Koraidon",
        ]
        trace_a = parse_protocol_log(list(lines), replay_id="a", format_name=FORMAT)
        trace_b = parse_protocol_log(list(lines), replay_id="b", format_name=FORMAT)
        trace_a["hidden_opponent_truth"] = {"item": "Choice Specs", "ability": "X"}
        trace_b["hidden_opponent_truth"] = {"item": "Air Balloon", "ability": "Y"}
        first = v8_belief_slice_feature_vector(
            active_opponent_set_belief(trace_a, player_side="p1")
        )
        second = v8_belief_slice_feature_vector(
            active_opponent_set_belief(trace_b, player_side="p1")
        )
        self.assertEqual(first.tolist(), second.tolist())

    def test_future_reveal_truncation_does_not_change_earlier_features(self):
        prefix = [
            "|switch|p2a: Gholdengo|Gholdengo, L77|100/100",
            "|turn|1",
            "|move|p2a: Gholdengo|Make It Rain|p1a: Koraidon",
        ]
        full = [
            *prefix,
            "|turn|2",
            "|-terastallize|p2a: Gholdengo|Steel",
            "|-ability|p2a: Gholdengo|Good as Gold",
        ]
        early = self._slice_from_lines(prefix)
        truncated_full = self._slice_from_lines(full, through_turn=1)
        self.assertEqual(early.tolist(), truncated_full.tolist())

    def test_copied_state_evidence_does_not_inflate_base_counts(self):
        # Ditto Transform copies a move; it must not become a confirmed base move
        # and must not contradict, but should appear as current-state.
        belief = active_opponent_set_belief(
            parse_protocol_log(
                [
                    "|switch|p2a: Ditto|Ditto, L84|100/100",
                    "|-transform|p2a: Ditto|p1a: Koraidon|[from] ability: Imposter",
                    "|turn|1",
                    "|move|p2a: Ditto|Close Combat|p1a: Koraidon",
                ],
                replay_id="ditto",
                format_name=FORMAT,
            ),
            player_side="p1",
        )
        named = _named(v8_belief_slice_feature_vector(belief))
        self.assertFalse(named["opponent_belief_prior_contradiction"])
        self.assertGreater(
            named["opponent_belief_current_state_only_fact_count_norm"], 0.0
        )


if __name__ == "__main__":
    unittest.main()
