import dataclasses
import hashlib
import tempfile
import unittest
from pathlib import Path

from neural.meta_prior import JointQuality, SourceKind
from neural.opponent_set_belief_replay_adapter import build_replay_prefix_beliefs
from neural.parse_replay_logs import parse_protocol_log
from neural.randbats_meta_prior_source import (
    DEFAULT_UNKNOWN_TAIL_MASS,
    RANDBATS_META_PRIOR_ADAPTER_VERSION,
    RandbatsMetaPriorSource,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
SETS_PATH = REPO_ROOT / "data" / "random-battles" / "gen9" / "sets.json"
FORMAT = "gen9randombattle"


class RandbatsMetaPriorSourceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = RandbatsMetaPriorSource()

    def test_uses_existing_old_shortcut_source_path_and_pinned_checksum(self):
        self.assertEqual(self.source.source_path, SETS_PATH.resolve())
        self.assertEqual(
            self.source.metadata.source_locator,
            "data/random-battles/gen9/sets.json",
        )
        expected = hashlib.sha256(SETS_PATH.read_bytes()).hexdigest()
        self.assertEqual(self.source.metadata.source_sha256, expected)
        self.assertEqual(self.source.metadata.data_version, f"sha256:{expected}")
        self.assertEqual(
            self.source.metadata.adapter_version,
            RANDBATS_META_PRIOR_ADAPTER_VERSION,
        )
        self.assertEqual(
            self.source.metadata.source_kind, SourceKind.RANDBATS_GENERATOR
        )
        self.assertEqual(self.source.metadata.sample_count, 0)

    def test_dondozo_role_prior_is_factorized_and_incomplete(self):
        prior = self.source.prior_for(FORMAT, "Dondozo")
        self.assertEqual(prior.joint_quality, JointQuality.FACTORIZED)
        self.assertEqual(prior.other_mass, DEFAULT_UNKNOWN_TAIL_MASS)
        self.assertEqual(len(prior.hypotheses), 2)
        self.assertEqual(
            {hypothesis.ability for hypothesis in prior.hypotheses}, {"unaware"}
        )
        self.assertEqual(
            {hypothesis.tera_type for hypothesis in prior.hypotheses},
            {"dragon", "fairy"},
        )
        self.assertTrue(
            all(
                hypothesis.moves
                == ("curse", "rest", "sleeptalk", "wavecrash")
                for hypothesis in prior.hypotheses
            )
        )
        self.assertTrue(
            all(hypothesis.item is None for hypothesis in prior.hypotheses)
        )
        self.assertIn(
            "items_absent_from_existing_role_data", prior.coverage_warnings
        )

    def test_hatterene_and_great_tusk_are_deterministic(self):
        first_hatterene = self.source.prior_for(FORMAT, "Hatterene")
        second_source = RandbatsMetaPriorSource()
        self.assertEqual(
            first_hatterene, second_source.prior_for(FORMAT, "hatterene")
        )
        self.assertEqual(len(first_hatterene.hypotheses), 4)
        self.assertEqual(
            {role for row in first_hatterene.hypotheses for role in row.roles},
            {"avpivot", "bulkysetup"},
        )
        self.assertEqual(
            {row.ability for row in first_hatterene.hypotheses},
            {"magicbounce"},
        )

        great_tusk = self.source.prior_for(FORMAT, "Great Tusk")
        self.assertEqual(len(great_tusk.hypotheses), 6)
        self.assertEqual(
            {row.ability for row in great_tusk.hypotheses},
            {"protosynthesis"},
        )

    def test_missing_species_and_format_mismatch_fail_closed(self):
        self.assertIsNone(self.source.prior_for(FORMAT, "MissingNo"))
        with self.assertRaisesRegex(ValueError, "format mismatch"):
            self.source.prior_for("gen9ou", "Dondozo")

    def test_metadata_and_prior_do_not_accept_hidden_truth_fields(self):
        prior_a = self.source.prior_for(
            FORMAT,
            "Hatterene",
            context={"hidden_opponent_truth": {"item": "Choice Band"}},
        )
        prior_b = self.source.prior_for(
            FORMAT,
            "Hatterene",
            context={"hidden_opponent_truth": {"item": "Leftovers"}},
        )
        self.assertEqual(prior_a, prior_b)
        self.assertFalse(
            {"hidden_truth", "actual_set", "packed_team"}
            & {field.name for field in dataclasses.fields(self.source.metadata)}
        )

    def test_replay_hidden_truth_perturbation_cannot_change_prefix_belief(self):
        trace = parse_protocol_log(
            [
                "|switch|p2a: Hatterene|Hatterene, L85, F|100/100",
                "|turn|1",
                "|move|p2a: Hatterene|Psychic|p1a: Dondozo",
            ],
            replay_id="randbats-prior-no-leakage",
            format_name=FORMAT,
        )
        trace_a = dict(trace)
        trace_b = dict(trace)
        trace_a["hidden_opponent_truth"] = {
            "item": "Choice Band",
            "moves": ["Splash"],
        }
        trace_b["hidden_opponent_truth"] = {
            "item": "Leftovers",
            "moves": ["Psychic"],
        }
        first = build_replay_prefix_beliefs(
            trace_a, self.source, perspective_side="p1"
        )
        second = build_replay_prefix_beliefs(
            trace_b, self.source, perspective_side="p1"
        )
        self.assertEqual(first.slots, second.slots)

    def test_explicit_path_uses_same_adapter_without_discovery(self):
        explicit = RandbatsMetaPriorSource(sets_path=str(SETS_PATH))
        self.assertEqual(explicit.metadata, self.source.metadata)
        with tempfile.TemporaryDirectory() as tmpdir:
            missing = Path(tmpdir) / "missing.json"
            with self.assertRaises(FileNotFoundError):
                RandbatsMetaPriorSource(sets_path=str(missing))


if __name__ == "__main__":
    unittest.main()
