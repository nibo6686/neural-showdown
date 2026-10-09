import json
import unittest
from pathlib import Path

from neural.canonical_action import (
    canonical_action_from_legal_action,
    deserialize_canonical_action,
    serialize_canonical_action,
)


FIXTURE = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "canonical_action_v1.json"


class CanonicalActionParityTest(unittest.TestCase):
    def test_fixture_actions_have_deterministic_serialization_and_round_trip(self):
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        for case in data["cases"]:
            legal_set = case["legal_action_set"]
            actions_array = legal_set["actions"]
            self.assertEqual(len(legal_set["mask"]), 13)
            self.assertEqual(len(actions_array), 13)
            expected_mask = [action is not None for action in actions_array]
            self.assertEqual(legal_set["mask"], expected_mask)
            self.assertEqual(legal_set["available_indices"], [index for index, enabled in enumerate(expected_mask) if enabled])
            for index, action in enumerate(actions_array):
                if action is not None:
                    self.assertEqual(action["index"], index)
            actions = {str(index): action for index, action in enumerate(actions_array) if legal_set["mask"][index]}
            request = dict(case["request"], legal_actions=actions)
            self.assertEqual(case["legal_action_set"]["mask"][case["legal_action"]["index"]], True)
            self.assertEqual(actions[str(case["legal_action"]["index"])]["label"], case["legal_action"]["label"])
            self.assertEqual(actions[str(case["legal_action"]["index"])]["choice"], case["legal_action"]["choice"])
            self.assertEqual(actions[str(case["legal_action"]["index"])]["slot"], case["legal_action"]["slot"])
            action = canonical_action_from_legal_action(case["legal_action"], request)
            self.assertEqual(action["action_id"], case["canonical_action"]["action_id"])
            serialized = serialize_canonical_action(action, request)
            self.assertEqual(serialized, case["serialized"])
            self.assertEqual(deserialize_canonical_action(serialized, request), action)
            self.assertEqual(serialize_canonical_action(action, request), serialized)

    def test_wait_and_team_preview_requests_expose_no_canonical_action(self):
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        case = data["cases"][0]
        for phase in ("wait", "team_preview"):
            request = dict(case["request"], legal_actions={}, wait=phase == "wait", team_preview=phase == "team_preview")
            with self.assertRaises(ValueError):
                canonical_action_from_legal_action(case["legal_action"], request)

    def test_invalid_request_and_target_combinations_fail_closed(self):
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        case = data["cases"][0]
        request = dict(case["request"], legal_actions={str(case["legal_action"]["index"]): case["legal_action"]})
        action = canonical_action_from_legal_action(case["legal_action"], request)
        for field, value in (("player", "p2"), ("rqid", 99), ("target", "+1"), ("kind", "switch"), ("index", 1), ("move_slot", 99), ("action_id", "act-tampered")):
            invalid = dict(action)
            invalid[field] = value
            with self.assertRaises(ValueError):
                serialize_canonical_action(invalid, request)
        with self.assertRaises(ValueError):
            serialize_canonical_action(dict(action, extra=True), request)

    def test_forced_switch_rejects_move_actions(self):
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        case = data["cases"][0]
        request = dict(case["request"], legal_actions={str(case["legal_action"]["index"]): case["legal_action"]}, force_switch=True)
        with self.assertRaises(ValueError):
            canonical_action_from_legal_action(case["legal_action"], request)


if __name__ == "__main__":
    unittest.main()
