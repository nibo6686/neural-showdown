import json
import os
import tempfile
import unittest
from pathlib import Path

from neural.live_eval_server import EvalRequest, _maybe_capture_evaluate_payload
from neural.validate_vnext_live_captures import validate_payload_slots


class LiveEvalCaptureTest(unittest.TestCase):
    def setUp(self):
        self.saved_enabled = os.environ.get("NEURAL_CAPTURE_EVALUATE_PAYLOADS")
        self.saved_dir = os.environ.get("NEURAL_CAPTURE_EVALUATE_DIR")

    def tearDown(self):
        for key, value in (
            ("NEURAL_CAPTURE_EVALUATE_PAYLOADS", self.saved_enabled),
            ("NEURAL_CAPTURE_EVALUATE_DIR", self.saved_dir),
        ):
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _payload(self):
        return EvalRequest(
            room_id="battle-gen9randombattle-secret",
            url="https://play.pokemonshowdown.com/battle-secret",
            player="p1",
            turn=4,
            decision_phase="move",
            log=[
                "|player|p1|Account Name|1",
                "|player|p2|Opponent Name|2",
                "|c|Account Name|private chat text",
                "|turn|4",
            ],
            request={
                "side": {
                    "id": "p1",
                    "name": "Account Name",
                    "pokemon": [
                        {"ident": "p1: Pikachu", "details": "Pikachu, L80", "active": True}
                    ],
                },
                "active": [{"moves": [{"move": "Thunderbolt", "id": "thunderbolt", "pp": 24}]}],
                "sessionid": "secret",
            },
            legal_actions=[{"kind": "move", "label": "Thunderbolt", "slot": 1}],
        )

    def test_capture_is_opt_in_and_sanitized(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ["NEURAL_CAPTURE_EVALUATE_DIR"] = temp_dir
            os.environ.pop("NEURAL_CAPTURE_EVALUATE_PAYLOADS", None)
            _maybe_capture_evaluate_payload(self._payload())
            self.assertEqual(list(Path(temp_dir).glob("*.json")), [])

            os.environ["NEURAL_CAPTURE_EVALUATE_PAYLOADS"] = "1"
            _maybe_capture_evaluate_payload(self._payload())
            files = list(Path(temp_dir).glob("evaluate_*.json"))
            self.assertEqual(len(files), 1)
            captured = json.loads(files[0].read_text(encoding="utf-8"))
            self.assertEqual(captured["room_id"], "captured-room")
            self.assertEqual(captured["url"], "captured://showdown-battle")
            self.assertEqual(captured["request"]["side"]["name"], "redacted-player")
            self.assertNotIn("sessionid", captured["request"])
            self.assertFalse(any(line.startswith("|c|") for line in captured["log"]))
            self.assertIn("|player|p1|redacted-p1|1", captured["log"])

    def test_duplicate_packet_is_not_captured_twice(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ["NEURAL_CAPTURE_EVALUATE_DIR"] = temp_dir
            os.environ["NEURAL_CAPTURE_EVALUATE_PAYLOADS"] = "1"
            _maybe_capture_evaluate_payload(self._payload())
            _maybe_capture_evaluate_payload(self._payload())
            self.assertEqual(len(list(Path(temp_dir).glob("evaluate_*.json"))), 1)

    def test_slot_validation_uses_request_order(self):
        payload = self._payload()
        result = {
            "choice": "move 1",
            "selected": {"move_slot": 1},
            "candidate_kind_counts": {"move_tera": 0},
        }
        validation = validate_payload_slots(payload, result)
        self.assertTrue(validation["ok"], validation["errors"])
        self.assertEqual(validation["move_actions_checked"], 1)


if __name__ == "__main__":
    unittest.main()
