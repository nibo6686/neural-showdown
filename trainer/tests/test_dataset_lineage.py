import json
import unittest
from pathlib import Path

from neural.dataset_lineage import (
    DATASET_RECORD_SCHEMA,
    DatasetLineageError,
    deterministic_split_for_battle,
    expected_record_id,
    make_record,
    source_metric_report,
    record_from_source_prefix,
    validate_record_prefix,
    validate_records,
    validate_record,
)


FIXTURE = Path(__file__).parents[2] / "tests" / "fixtures" / "dataset_lineage_v1.json"


class DatasetLineageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def _record(self, index=0, **updates):
        payload = dict(self.fixture["valid_inputs"][index])
        payload.pop("metric", None)
        payload.update(updates)
        return make_record(**payload)

    def test_record_identity_and_serialization_are_deterministic(self):
        first = self._record()
        second = self._record()
        self.assertEqual(first, second)
        self.assertEqual(first["record_id"], expected_record_id(first))
        self.assertEqual(first["schema_version"], DATASET_RECORD_SCHEMA)

    def test_valid_records_are_battle_and_replay_disjoint(self):
        records = validate_records([self._record(0), self._record(1)])
        self.assertEqual({record["battle_id"] for record in records}, {"fixture-battle-a", "fixture-battle-b"})

    def test_duplicate_identity_is_rejected(self):
        record = self._record()
        with self.assertRaisesRegex(DatasetLineageError, "duplicate record identity"):
            validate_records([record, dict(record)])

    def test_cross_split_battle_is_rejected(self):
        conflicting = self._record(
            observation_cursor=5,
            feature_cursor=5,
            observation_prefix_hash="eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
            split="test",
        )
        with self.assertRaisesRegex(DatasetLineageError, "battle_id crosses dataset splits"):
            validate_records([self._record(), conflicting])

    def test_cross_split_replay_identity_is_rejected(self):
        conflicting = self._record(
            battle_id="fixture-battle-c",
            observation_cursor=5,
            feature_cursor=5,
            observation_prefix_hash="ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
            split="test",
        )
        with self.assertRaisesRegex(DatasetLineageError, "replay_id crosses dataset splits"):
            validate_records([self._record(), conflicting])

    def test_future_event_cursor_is_rejected(self):
        with self.assertRaisesRegex(DatasetLineageError, "after observation"):
            self._record(feature_cursor=8)

    def test_prefix_hash_and_cursor_mismatch_are_rejected(self):
        prefix = ["|turn|1", "|move|p1a: Pikachu|Tackle|p2a: Eevee"]
        record = record_from_source_prefix(
            battle_id="prefix-battle",
            replay_id="prefix-replay",
            source_kind="replay",
            source_ref="fixture",
            ruleset="gen9randombattle",
            parser_version="fixture-parser-v1",
            perspective="p1",
            protocol_prefix=prefix,
            private_data_provenance="none",
            feature_input_eligibility="public_only",
            schema_fingerprints={
                "observation": "replay-protocol-prefix/v1",
                "belief": None,
                "transition": None,
                "feature": "fixture-feature-v1:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            },
        )
        validate_record_prefix(record, prefix)
        with self.assertRaisesRegex(DatasetLineageError, "hash"):
            validate_record_prefix(record, ["|turn|1", "|move|p1a: Pikachu|Future|p2a: Eevee"])
        with self.assertRaisesRegex(DatasetLineageError, "length"):
            validate_record_prefix(record, prefix + ["|win|Alice"])

    def test_unsupported_and_malformed_records_fail_closed(self):
        with self.assertRaisesRegex(DatasetLineageError, "unsupported dataset record schema"):
            make_record(**dict(self.fixture["valid_inputs"][0], schema_version="dataset-record/v99"))
        with self.assertRaisesRegex(DatasetLineageError, "private provenance"):
            self._record(private_data_provenance="acting_player_request", feature_input_eligibility="public_only")
        with self.assertRaisesRegex(DatasetLineageError, "private fields"):
            self._record(input_fields=["public_hp", "opponent_private"])
        with self.assertRaisesRegex(DatasetLineageError, "observation_cursor"):
            self._record(observation_cursor=-1, feature_cursor=0)
        with self.assertRaisesRegex(DatasetLineageError, "private_data_provenance"):
            self._record(private_data_provenance="")

    def test_deterministic_split_uses_battle_identity(self):
        first = deterministic_split_for_battle("battle-1", 20260923)
        second = deterministic_split_for_battle("battle-1", 20260923)
        self.assertEqual(first, second)
        self.assertIn(first, {"train", "validation", "test"})

    def test_source_metrics_are_reported_separately(self):
        records = [self._record(0), self._record(1)]
        metrics = {
            record["record_id"]: self.fixture["valid_inputs"][index]["metric"]
            for index, record in enumerate(records)
        }
        report = source_metric_report(records, metrics)
        self.assertEqual(report["record_count"], 2)
        self.assertEqual(set(report["sources"]), {"replay", "live"})
        self.assertEqual(report["sources"]["replay"]["record_count"], 1)
        self.assertEqual(report["sources"]["live"]["splits"], ["validation"])

    def test_imported_record_id_mismatch_is_rejected(self):
        record = self._record()
        record["record_id"] = "datarec-" + ("0" * 64)
        with self.assertRaisesRegex(DatasetLineageError, "does not match"):
            validate_record(record)


if __name__ == "__main__":
    unittest.main()
