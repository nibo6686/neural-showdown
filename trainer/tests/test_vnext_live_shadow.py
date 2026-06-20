import inspect
import os
import unittest
from pathlib import Path
from typing import Any, Dict, List

from neural import vnext_live_shadow as shadow


BASE_LOG = [
    "|start",
    "|switch|p1a: Charizard|Charizard, L80, M|100/100",
    "|switch|p2a: Blastoise|Blastoise, L80, M|100/100",
    "|turn|3",
]
_MOVES = [
    {"move": "Flamethrower", "id": "flamethrower", "pp": 24, "maxpp": 24, "target": "normal"},
    {"move": "Air Slash", "id": "airslash", "pp": 24, "maxpp": 24, "target": "normal"},
    {"move": "Roost", "id": "roost", "pp": 16, "maxpp": 16, "target": "self"},
    {"move": "Dragon Pulse", "id": "dragonpulse", "pp": 16, "maxpp": 16, "target": "normal"},
]


def _request(*, tera: bool) -> Dict[str, Any]:
    active: Dict[str, Any] = {"moves": _MOVES}
    if tera:
        active["canTerastallize"] = "Fire"
    side = {
        "id": "p1",
        "pokemon": [
            {
                "ident": "p1: Charizard",
                "details": "Charizard, L80, M",
                "condition": "200/200",
                "active": True,
                "moves": [m["id"] for m in _MOVES],
                "baseAbility": "blaze",
                "ability": "blaze",
                "teraType": "Fire",
            },
            {
                "ident": "p1: Blastoise",
                "details": "Blastoise, L80, M",
                "condition": "200/200",
                "active": False,
                "moves": ["surf"],
                "baseAbility": "torrent",
            },
            {
                "ident": "p1: Venusaur",
                "details": "Venusaur, L80, M",
                "condition": "200/200",
                "active": False,
                "moves": ["gigadrain"],
                "baseAbility": "overgrow",
            },
        ],
    }
    return {"side": side, "active": [active]}


_USE_FIXTURE = object()


def _dry_run(*, tera: bool = True, request=_USE_FIXTURE, log=None):
    payload = _request(tera=tera) if request is _USE_FIXTURE else request
    return shadow.build_dry_run(
        log=log if log is not None else BASE_LOG,
        room_id="shadow-test",
        url="cf://shadow-test",
        player="p1",
        request_payload=payload,
        legal_actions=[],
    )


class VNextLiveShadowTest(unittest.TestCase):
    def setUp(self):
        self._saved = os.environ.pop("NEURAL_VNEXT_INFERENCE", None)

    def tearDown(self):
        if self._saved is not None:
            os.environ["NEURAL_VNEXT_INFERENCE"] = self._saved
        else:
            os.environ.pop("NEURAL_VNEXT_INFERENCE", None)

    def test_shadow_disabled_by_default(self):
        self.assertFalse(shadow.shadow_enabled())
        os.environ["NEURAL_VNEXT_INFERENCE"] = "1"
        self.assertTrue(shadow.shadow_enabled())

    def test_route_requires_opt_in(self):
        from neural.live_eval_server import EvalRequest, evaluate_vnext_dry_run

        payload = EvalRequest(room_id="r", url="u", player="p1", log=BASE_LOG, request=_request(tera=True))
        # Flag off -> disabled, no command, default path untouched.
        result = evaluate_vnext_dry_run(payload)
        self.assertFalse(result["ok"])
        self.assertEqual(result["fallback_reason"], "vnext_inference_disabled")
        self.assertFalse(result["command_sent_to_showdown"])

    def test_dry_run_success_with_tera_and_switch(self):
        result = _dry_run(tera=True)
        self.assertTrue(result["ok"], result.get("fallback_reason"))
        self.assertEqual(result["schema"]["state_feature_dim"], 3208)
        self.assertEqual(result["schema"]["action_feature_dim"], 318)
        self.assertEqual(result["schema"]["fingerprint_status"], "PASS")
        counts = result["candidate_kind_counts"]
        self.assertGreaterEqual(counts["move"], 1)
        self.assertGreaterEqual(counts["move_tera"], 1)
        self.assertGreaterEqual(counts["switch"], 2)
        self.assertTrue(result["tera"]["can_tera"])
        self.assertGreaterEqual(result["tera"]["tera_candidates_generated"], 1)
        self.assertGreaterEqual(result["switch_candidate_count"], 2)
        # A successful recommendation yields a valid Showdown choice string.
        self.assertRegex(result["choice"], r"^(move \d( terastallize)?|switch \d)$")
        self.assertFalse(result["command_sent_to_showdown"])
        self.assertFalse(result["battle_played_by_model"])
        self.assertFalse(result["live_defaults_changed"])
        for key in (
            "state_feature_generation_ms",
            "action_candidate_generation_ms",
            "sim_core_impact_resolution_ms",
            "model_scoring_ms",
            "response_serialization_ms",
            "total_ms",
        ):
            self.assertIn(key, result["latency_ms"])

    def test_tera_legal_creates_move_tera_candidates(self):
        with_tera = _dry_run(tera=True)
        without_tera = _dry_run(tera=False)
        self.assertGreaterEqual(with_tera["candidate_kind_counts"]["move_tera"], 1)
        self.assertEqual(without_tera["candidate_kind_counts"]["move_tera"], 0)

    def test_missing_required_fields_fail_closed(self):
        # No request and no public reveal of the active Pokemon -> nothing to score.
        result = _dry_run(request=None, log=["|start"])
        self.assertFalse(result["ok"])
        self.assertIn(
            result["fallback_reason"], ("missing_required_live_fields", "no_legal_candidates")
        )
        self.assertEqual(result["choice"], "default")
        self.assertFalse(result["command_sent_to_showdown"])

    def test_no_command_is_sent_to_showdown(self):
        for result in (_dry_run(tera=True), _dry_run(request=None, log=["|start"])):
            self.assertFalse(result["command_sent_to_showdown"])
            self.assertFalse(result["battle_played_by_model"])
            self.assertFalse(result["live_defaults_changed"])

    def test_no_pad_or_truncate_in_shadow_source(self):
        source = Path(shadow.__file__).read_text(encoding="utf-8")
        self.assertNotIn("np.pad", source)

    def test_default_evaluate_path_does_not_reference_vnext(self):
        from neural import live_eval_server

        evaluate_source = inspect.getsource(live_eval_server.evaluate_with_model)
        self.assertNotIn("vnext", evaluate_source.lower())
        # The shadow import in the server is lazy (inside the dry-run handler only).
        server_source = Path(live_eval_server.__file__).read_text(encoding="utf-8")
        top = server_source.split("def evaluate_vnext_dry_run", 1)[0]
        self.assertNotIn("vnext_live_shadow", top)


if __name__ == "__main__":
    unittest.main()
