import copy
import unittest

from neural.typed_state import validate_public_typed_state


def observation(prefix):
    return {
        "perspective": "p1",
        "protocol_prefix": prefix,
        "view": {
            "self_team": [{"ident": "p1: One", "volatiles": ["substitute"]}],
            "opponent_team": [{"ident": "p2: Two", "volatiles": []}],
            "field": {"side_conditions": {"self": {"spikes": 2, "reflect": 1}, "opponent": {}}},
        },
    }


class PublicTypedStateTests(unittest.TestCase):
    def setUp(self):
        self.valid = observation([
            "|switch|p1a: One|Cyclizar, L80|100/100",
            "|switch|p2a: Two|Snorlax, L80|100/100",
            "|-start|p1a: One|Substitute",
            "|-sidestart|p1: One|Spikes",
            "|-sidestart|p1: One|Spikes",
            "|-sidestart|p1: One|Reflect",
        ])

    def test_source_derived_control_validates_and_raw_only_evidence_stays_untyped(self):
        candidate = copy.deepcopy(self.valid)
        candidate["protocol_prefix"].append("|-start|p2a: Two|confusion")
        validate_public_typed_state(candidate)

    def test_false_volatile_and_side_maps_reject(self):
        false_volatile = copy.deepcopy(self.valid)
        false_volatile["view"]["self_team"][0]["volatiles"] = []
        with self.assertRaisesRegex(ValueError, "volatile map disagrees"):
            validate_public_typed_state(false_volatile)

        false_side = copy.deepcopy(self.valid)
        false_side["view"]["field"]["side_conditions"]["self"]["spikes"] = 1
        with self.assertRaisesRegex(ValueError, "side-condition map disagrees"):
            validate_public_typed_state(false_side)

        false_presence = copy.deepcopy(self.valid)
        false_presence["view"]["field"]["side_conditions"]["self"].pop("reflect")
        with self.assertRaisesRegex(ValueError, "side-condition map disagrees"):
            validate_public_typed_state(false_presence)

    def test_unknown_lifecycle_paths_fail_closed(self):
        candidate = copy.deepcopy(self.valid)
        candidate["protocol_prefix"].append("|-sidestart|p1: One|Mat Block")
        with self.assertRaisesRegex(ValueError, "unsupported-fail-closed side condition matblock"):
            validate_public_typed_state(candidate)

    def test_private_slot_state_is_rejected_before_publication(self):
        for key in ("slotConditions", "slot_conditions", "slot_condition_state", "pending_slots"):
            candidate = copy.deepcopy(self.valid)
            candidate["view"]["field"][key] = {"wish": {"endingTurn": 3}}
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "Private simulator slot state is not publishable"):
                validate_public_typed_state(candidate)

    def test_nonempty_prefix_volatile_requires_exactly_one_correct_perspective_roster_row(self):
        candidate = copy.deepcopy(self.valid)
        validate_public_typed_state(candidate)

        missing = copy.deepcopy(candidate)
        missing["view"]["self_team"] = []
        with self.assertRaisesRegex(ValueError, "exactly one canonical self_team roster row"):
            validate_public_typed_state(missing)

        duplicate = copy.deepcopy(candidate)
        duplicate["view"]["self_team"].append(copy.deepcopy(duplicate["view"]["self_team"][0]))
        with self.assertRaisesRegex(ValueError, "exactly one canonical self_team roster row"):
            validate_public_typed_state(duplicate)

        wrong_perspective = copy.deepcopy(candidate)
        wrong_perspective["view"]["self_team"] = []
        wrong_perspective["view"]["opponent_team"].append(
            {"ident": "p1: One", "volatiles": ["substitute"]}
        )
        with self.assertRaisesRegex(ValueError, "exactly one canonical self_team roster row"):
            validate_public_typed_state(wrong_perspective)

    def test_partial_containers_reject_only_when_the_prefix_derives_typed_state(self):
        empty_prefix = {"protocol_prefix": [], "view": {}}
        validate_public_typed_state(empty_prefix)

        volatile_prefix = ["|switch|p1a: One|Cyclizar, L80|100/100", "|-start|p1a: One|Substitute"]
        with self.assertRaisesRegex(ValueError, "exactly one canonical self_team roster row"):
            validate_public_typed_state({
                "perspective": "p1", "protocol_prefix": volatile_prefix, "view": {"field": {}}
            })
        with self.assertRaisesRegex(ValueError, "derived typed state requires a valid perspective"):
            validate_public_typed_state({"protocol_prefix": volatile_prefix, "view": {"self_team": []}})

        for view in (
            {"self_team": []},
            {"self_team": [{"ident": "p1: One"}]},
        ):
            with self.assertRaisesRegex(ValueError, "exactly one canonical self_team roster row"):
                validate_public_typed_state({"perspective": "p1", "protocol_prefix": volatile_prefix, "view": view})

        side_prefix = ["|-sidestart|p1: One|Spikes"]
        for view in (
            {},
            {"field": {}},
            {"field": {"side_conditions": {}}},
            {"field": {"side_conditions": {"self": {}}}},
            {"field": {"side_conditions": {"opponent": {"spikes": 1}}}},
        ):
            with self.assertRaisesRegex(ValueError, "Typed lifecycle evidence mismatch"):
                validate_public_typed_state({"perspective": "p1", "protocol_prefix": side_prefix, "view": view})

        opponent_prefix = ["|-sidestart|p2: Two|Reflect"]
        with self.assertRaisesRegex(ValueError, "opponent side-condition state requires"):
            validate_public_typed_state({
                "perspective": "p1", "protocol_prefix": opponent_prefix,
                "view": {"field": {"side_conditions": {"self": {}}}},
            })


if __name__ == "__main__":
    unittest.main()
