import tempfile
import unittest
from pathlib import Path

import numpy as np

from neural.item_ability_counterfactual_diagnostic import (
    BASE_LOG,
    _features,
    _request,
    evaluate_item_ability_counterfactuals,
)
from neural.live_private_features import (
    FEATURE_DIM,
    FEATURE_DIM_V3,
    FEATURE_DIM_V4,
    FEATURE_NAMES,
    FEATURE_NAMES_V3,
    FEATURE_NAMES_V4,
    FEATURE_VERSION,
    FEATURE_VERSION_V3,
    FEATURE_VERSION_V4,
    V4_SLICE2_FEATURE_NAMES,
    validate_live_private_feature_metadata,
)


def _value(features, name):
    return float(features[FEATURE_NAMES_V4.index(name)])


class LivePrivateFeaturesV4Test(unittest.TestCase):
    def test_v4_schema_is_immutable_extension_and_older_versions_are_unchanged(self):
        self.assertEqual(FEATURE_VERSION, "live-private-belief-v2")
        self.assertEqual(FEATURE_DIM, 115)
        self.assertEqual(FEATURE_VERSION_V3, "live-private-belief-v3")
        self.assertEqual(FEATURE_DIM_V3, 217)
        self.assertEqual(FEATURE_VERSION_V4, "live-private-belief-v4")
        self.assertEqual(FEATURE_DIM_V4, 765)
        self.assertEqual(FEATURE_NAMES_V4[:FEATURE_DIM], FEATURE_NAMES)
        self.assertEqual(FEATURE_NAMES_V4[:FEATURE_DIM_V3], FEATURE_NAMES_V3)
        self.assertEqual(FEATURE_NAMES_V4[FEATURE_DIM_V3:], V4_SLICE2_FEATURE_NAMES)

    def test_metadata_rejects_cross_version_checkpoints_and_live_stays_v2(self):
        validate_live_private_feature_metadata(
            feature_version=FEATURE_VERSION_V4,
            feature_dim=FEATURE_DIM_V4,
            expected_version=FEATURE_VERSION_V4,
        )
        with self.assertRaises(ValueError):
            validate_live_private_feature_metadata(
                feature_version=FEATURE_VERSION_V3,
                feature_dim=FEATURE_DIM_V3,
                expected_version=FEATURE_VERSION_V4,
            )

        from neural.live_eval_server import _validate_live_private_checkpoint

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "metadata-only.pt"
            _validate_live_private_checkpoint(
                {"feature_version": FEATURE_VERSION, "input_size": FEATURE_DIM},
                path,
            )
            with self.assertRaises(ValueError):
                _validate_live_private_checkpoint(
                    {"feature_version": FEATURE_VERSION_V4, "input_size": FEATURE_DIM_V4},
                    path,
                )

    def test_unknown_no_item_held_removed_and_consumed_are_distinct(self):
        unknown = _features()
        no_item = _features(request=_request(item=None, base_ability=None, ability=None))
        held = _features(log=[*BASE_LOG, "|-item|p1a: Pikachu|Heavy-Duty Boots"])
        removed = _features(
            log=[
                *BASE_LOG,
                "|-item|p1a: Pikachu|Heavy-Duty Boots",
                "|-enditem|p1a: Pikachu|Heavy-Duty Boots|[from] move: Knock Off",
            ]
        )
        consumed = _features(
            log=[
                *BASE_LOG,
                "|-item|p1a: Pikachu|Sitrus Berry",
                "|-enditem|p1a: Pikachu|Sitrus Berry|[eat]",
            ]
        )

        self.assertEqual(_value(unknown, "own_active_item_state_unknown"), 1.0)
        self.assertEqual(_value(no_item, "own_active_item_state_none"), 1.0)
        self.assertEqual(_value(held, "own_active_item_state_held"), 1.0)
        self.assertEqual(_value(removed, "own_active_item_state_removed"), 1.0)
        self.assertEqual(_value(consumed, "own_active_item_state_consumed"), 1.0)
        for left, right in (
            (unknown, no_item),
            (unknown, held),
            (held, removed),
            (held, consumed),
            (removed, consumed),
        ):
            self.assertFalse(np.allclose(left, right))

    def test_boots_and_last_item_identity_are_stably_encoded(self):
        held = _features(log=[*BASE_LOG, "|-item|p1a: Pikachu|Heavy-Duty Boots"])
        removed = _features(
            log=[
                *BASE_LOG,
                "|-item|p1a: Pikachu|Heavy-Duty Boots",
                "|-enditem|p1a: Pikachu|Heavy-Duty Boots|[from] move: Knock Off",
            ]
        )
        current_bucket_values = [
            _value(held, name)
            for name in V4_SLICE2_FEATURE_NAMES
            if name.startswith("own_active_current_item_hash_")
        ]
        last_bucket_values = [
            _value(removed, name)
            for name in V4_SLICE2_FEATURE_NAMES
            if name.startswith("own_active_last_item_hash_")
        ]
        self.assertEqual(sum(current_bucket_values), 2.0)
        self.assertEqual(sum(last_bucket_values), 2.0)

    def test_ability_unknown_known_changed_none_and_suppressed_are_distinct(self):
        unknown = _features()
        none = _features(request=_request(item=None, base_ability=None, ability=None))
        known = _features(log=[*BASE_LOG, "|-ability|p1a: Pikachu|Static"])
        changed = _features(
            log=[
                *BASE_LOG,
                "|-ability|p1a: Pikachu|Static",
                "|-ability|p1a: Pikachu|Insomnia|[from] move: Worry Seed",
            ]
        )
        suppressed = _features(
            log=[
                *BASE_LOG,
                "|-ability|p1a: Pikachu|Static",
                "|-endability|p1a: Pikachu",
            ]
        )
        self.assertEqual(_value(unknown, "own_active_ability_state_unknown"), 1.0)
        self.assertEqual(_value(none, "own_active_ability_state_none"), 1.0)
        self.assertEqual(_value(known, "own_active_ability_state_known"), 1.0)
        self.assertEqual(_value(changed, "own_active_ability_state_changed"), 1.0)
        self.assertEqual(_value(suppressed, "own_active_ability_state_suppressed"), 1.0)
        self.assertEqual(_value(suppressed, "own_active_ability_suppressed"), 1.0)
        self.assertFalse(np.allclose(known, changed))
        self.assertFalse(np.allclose(known, suppressed))

        base_values = [
            _value(changed, name)
            for name in V4_SLICE2_FEATURE_NAMES
            if name.startswith("own_active_base_ability_hash_")
        ]
        current_values = [
            _value(changed, name)
            for name in V4_SLICE2_FEATURE_NAMES
            if name.startswith("own_active_current_ability_hash_")
        ]
        self.assertEqual(sum(base_values), 2.0)
        self.assertEqual(sum(current_values), 2.0)
        self.assertNotEqual(base_values, current_values)

    def test_magic_room_item_suppression_is_represented(self):
        active = _features(log=[*BASE_LOG, "|-item|p1a: Pikachu|Heavy-Duty Boots"])
        suppressed = _features(
            log=[
                *BASE_LOG,
                "|-item|p1a: Pikachu|Heavy-Duty Boots",
                "|-fieldstart|move: Magic Room",
            ]
        )
        self.assertEqual(_value(active, "own_active_item_suppressed"), 0.0)
        self.assertEqual(_value(suppressed, "own_active_item_suppressed"), 1.0)

    def test_item_and_ability_perspective_flip(self):
        log = [
            *BASE_LOG,
            "|-item|p1a: Pikachu|Heavy-Duty Boots",
            "|-ability|p1a: Pikachu|Static",
        ]
        p1 = _features(log=log, player="p1")
        p2 = _features(log=log, player="p2")
        self.assertEqual(_value(p1, "own_active_item_state_held"), 1.0)
        self.assertEqual(_value(p2, "opponent_active_item_state_held"), 1.0)
        self.assertEqual(_value(p1, "own_active_ability_state_known"), 1.0)
        self.assertEqual(_value(p2, "opponent_active_ability_state_known"), 1.0)

        p1_item = [
            _value(p1, name)
            for name in V4_SLICE2_FEATURE_NAMES
            if name.startswith("own_active_current_item_hash_")
        ]
        p2_item = [
            _value(p2, name)
            for name in V4_SLICE2_FEATURE_NAMES
            if name.startswith("opponent_active_current_item_hash_")
        ]
        self.assertEqual(p1_item, p2_item)

    def test_counterfactual_diagnostic_reports_all_required_distinctions(self):
        report = evaluate_item_ability_counterfactuals()
        self.assertEqual(report["feature_version"], FEATURE_VERSION_V4)
        self.assertEqual(report["feature_dim"], FEATURE_DIM_V4)
        for changed in report["comparisons"].values():
            self.assertTrue(changed)
        self.assertEqual(report["perspective"]["p1_own_item_state_held"], 1.0)
        self.assertEqual(report["perspective"]["p2_opponent_item_state_held"], 1.0)


if __name__ == "__main__":
    unittest.main()
