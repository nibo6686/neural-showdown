import tempfile
import unittest
from pathlib import Path

import numpy as np

from neural.live_private_features import (
    FEATURE_DIM,
    FEATURE_DIM_V3,
    FEATURE_DIM_V4,
    FEATURE_DIM_V5,
    FEATURE_NAMES,
    FEATURE_NAMES_V3,
    FEATURE_NAMES_V4,
    FEATURE_NAMES_V5,
    FEATURE_VERSION,
    FEATURE_VERSION_V5,
    V5_SLICE3_FEATURE_NAMES,
    validate_live_private_feature_metadata,
)
from neural.species_status_counterfactual_diagnostic import (
    BASE_LOG,
    _features,
    _request,
    evaluate_species_status_counterfactuals,
)


def _value(features, name):
    return float(features[FEATURE_NAMES_V5.index(name)])


class LivePrivateFeaturesV5Test(unittest.TestCase):
    def test_v5_is_immutable_extension_and_older_versions_are_unchanged(self):
        self.assertEqual(FEATURE_VERSION, "live-private-belief-v2")
        self.assertEqual(FEATURE_DIM, 115)
        self.assertEqual(FEATURE_DIM_V3, 217)
        self.assertEqual(FEATURE_DIM_V4, 765)
        self.assertEqual(FEATURE_VERSION_V5, "live-private-belief-v5")
        self.assertEqual(FEATURE_DIM_V5, 2293)
        self.assertEqual(FEATURE_NAMES_V3[:FEATURE_DIM], FEATURE_NAMES)
        self.assertEqual(FEATURE_NAMES_V4[:FEATURE_DIM_V3], FEATURE_NAMES_V3)
        self.assertEqual(FEATURE_NAMES_V5[:FEATURE_DIM_V4], FEATURE_NAMES_V4)
        self.assertEqual(FEATURE_NAMES_V5[FEATURE_DIM_V4:], V5_SLICE3_FEATURE_NAMES)

    def test_metadata_is_strict_and_live_default_remains_v2(self):
        validate_live_private_feature_metadata(
            feature_version=FEATURE_VERSION_V5,
            feature_dim=FEATURE_DIM_V5,
            expected_version=FEATURE_VERSION_V5,
        )
        with self.assertRaises(ValueError):
            validate_live_private_feature_metadata(
                feature_version=FEATURE_VERSION,
                feature_dim=FEATURE_DIM,
                expected_version=FEATURE_VERSION_V5,
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
                    {"feature_version": FEATURE_VERSION_V5, "input_size": FEATURE_DIM_V5},
                    path,
                )

    def test_active_species_and_known_unknown_states_are_distinct(self):
        pikachu = _features(request=_request("Pikachu", "Blissey"))
        raichu = _features(request=_request("Raichu", "Blissey"))
        self.assertFalse(np.allclose(pikachu, raichu))
        self.assertEqual(
            sum(
                _value(pikachu, name)
                for name in V5_SLICE3_FEATURE_NAMES
                if name.startswith("own_active_current_species_hash_")
            ),
            2.0,
        )

        unknown = _features(log=BASE_LOG[:-1])
        known = _features()
        self.assertFalse(np.allclose(unknown, known))
        self.assertEqual(_value(known, "opponent_roster_slot_1_species_state_known"), 1.0)
        self.assertEqual(_value(unknown, "opponent_roster_slot_1_species_state_unknown"), 1.0)

    def test_transform_separates_base_and_current_species(self):
        transformed = _features(
            log=[
                "|start",
                "|switch|p1a: Ditto|Ditto, L80|100/100",
                "|switch|p2a: Garchomp|Garchomp, L80|100/100",
                "|-transform|p1a: Ditto|p2a: Garchomp",
            ]
        )
        self.assertEqual(_value(transformed, "own_active_transformed"), 1.0)
        base = [
            _value(transformed, name)
            for name in V5_SLICE3_FEATURE_NAMES
            if name.startswith("own_active_base_species_hash_")
        ]
        current = [
            _value(transformed, name)
            for name in V5_SLICE3_FEATURE_NAMES
            if name.startswith("own_active_current_species_hash_")
        ]
        self.assertEqual(sum(base), 2.0)
        self.assertEqual(sum(current), 2.0)
        self.assertNotEqual(base, current)

    def test_bench_roster_identity_and_active_placement_are_represented(self):
        blissey = _features(request=_request("Pikachu", "Blissey"))
        garchomp = _features(request=_request("Pikachu", "Garchomp"))
        self.assertFalse(np.allclose(blissey, garchomp))
        self.assertEqual(_value(blissey, "own_roster_slot_1_placement_active"), 1.0)
        self.assertEqual(_value(blissey, "own_roster_slot_2_placement_bench"), 1.0)
        slot_two_active = _features(request=_request("Pikachu", "Blissey", active_slot=2))
        self.assertEqual(_value(slot_two_active, "own_roster_slot_1_placement_bench"), 1.0)
        self.assertEqual(_value(slot_two_active, "own_roster_slot_2_placement_active"), 1.0)
        self.assertFalse(np.allclose(blissey, slot_two_active))

    def test_illusion_reveal_separates_displayed_and_true_species(self):
        revealed = _features(
            log=[
                "|start",
                "|switch|p1a: Pikachu|Pikachu, L80|100/100",
                "|switch|p2a: Dragonite|Dragonite, L80|100/100",
                "|replace|p2a: Zoroark|Zoroark, L80|100/100",
            ]
        )
        self.assertEqual(_value(revealed, "opponent_active_illusion_revealed"), 1.0)
        self.assertEqual(_value(revealed, "opponent_active_displayed_species_uncertain"), 0.0)
        displayed = [
            _value(revealed, name)
            for name in V5_SLICE3_FEATURE_NAMES
            if name.startswith("opponent_active_displayed_species_hash_")
        ]
        current = [
            _value(revealed, name)
            for name in V5_SLICE3_FEATURE_NAMES
            if name.startswith("opponent_active_current_species_hash_")
        ]
        self.assertNotEqual(displayed, current)

    def test_major_statuses_none_and_unknown_are_distinct(self):
        states = {
            "none": _features(),
            **{
                status: _features(log=[*BASE_LOG, f"|-status|p1a: Pikachu|{status}"])
                for status in ("brn", "par", "slp", "psn", "tox", "frz")
            },
            "unknown": _features(log=["|start", "|switch|p2a: Charizard|Charizard, L80|100/100"]),
        }
        for status in ("brn", "par", "slp", "psn", "tox", "frz"):
            self.assertEqual(_value(states[status], f"own_active_status_{status}"), 1.0)
        self.assertEqual(_value(states["none"], "own_active_status_none"), 1.0)
        self.assertEqual(_value(states["unknown"], "own_active_status_unknown"), 1.0)
        for left, right in (
            ("none", "brn"),
            ("brn", "par"),
            ("par", "slp"),
            ("psn", "tox"),
            ("none", "frz"),
            ("unknown", "none"),
        ):
            self.assertFalse(np.allclose(states[left], states[right]))
        self.assertEqual(_value(states["slp"], "own_active_sleep_turns_public_known"), 1.0)
        self.assertEqual(_value(states["tox"], "own_active_toxic_turns_public_known"), 1.0)

    def test_status_and_roster_perspective_flip(self):
        log = [
            *BASE_LOG,
            "|-status|p1a: Pikachu|brn",
            "|switch|p1a: Blissey|Blissey, L80, F|100/100",
        ]
        p1 = _features(log=log, player="p1")
        p2 = _features(log=log, player="p2")
        self.assertEqual(_value(p1, "own_roster_slot_1_status_brn"), 1.0)
        self.assertEqual(_value(p2, "opponent_roster_slot_1_status_brn"), 1.0)
        self.assertEqual(_value(p1, "own_roster_slot_2_placement_active"), 1.0)
        self.assertEqual(_value(p2, "opponent_roster_slot_2_placement_active"), 1.0)

    def test_counterfactual_report_contains_required_distinctions(self):
        report = evaluate_species_status_counterfactuals()
        self.assertEqual(report["feature_version"], FEATURE_VERSION_V5)
        self.assertEqual(report["feature_dim"], FEATURE_DIM_V5)
        for changed in report["comparisons"].values():
            self.assertTrue(changed)


if __name__ == "__main__":
    unittest.main()
