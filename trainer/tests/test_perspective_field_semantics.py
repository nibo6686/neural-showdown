"""Source-ledger regressions at the real ordinary publication boundary."""

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from neural.pipeline_record import PipelineRecordError, validate_pipeline_bundle
from neural.protocol_contract import validate_protocol_record
from neural.public_field import validate_public_field
from neural.ts_identity import verify_bundle_identities
from neural.typed_state import validate_public_typed_state
from test_pipeline_record import _bundle, _seal_bundle


ROOT = Path(__file__).resolve().parents[2]
TRUTH = {"weather": "sunnyday", "terrain": "electricterrain", "pseudo_weather": []}


def source_control(family, version="v2"):
    path = ROOT / "docs/planning" / f"perspective-fidelity-prompt4-{family}-reproduction.json"
    bundle = json.loads(path.read_text(encoding="utf-8"))
    bundle["input_observation"]["view"]["field"][family] = copy.deepcopy(TRUTH[family])
    for which in ("input", "successor"):
        observation = bundle[f"{which}_observation"]
        observation["schema_version"] = f"observable-battle-state/{version}"
        if version == "v1":
            for pokemon in observation["view"]["opponent_team"]:
                pokemon.pop("public_boosts", None)
    return _seal_bundle(bundle)


def cli(payload):
    env = {key: value for key, value in os.environ.items()
           if key.upper() not in {"PYTHONUTF8", "PYTHONIOENCODING"}}
    env["PYTHONPATH"] = str(ROOT / "trainer/src")
    return subprocess.run([sys.executable, "-m", "neural.pipeline_record"],
                          input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                          capture_output=True, env=env, cwd=ROOT, timeout=30)


class PerspectiveFieldSemanticsTests(unittest.TestCase):
    def test_original_saved_witnesses_reject_atomically(self):
        for family in TRUTH:
            path = ROOT / "docs/planning" / f"perspective-fidelity-prompt4-{family}-reproduction.json"
            bundle = json.loads(path.read_text(encoding="utf-8"))
            before = copy.deepcopy(bundle)
            verify_bundle_identities(bundle)
            result = cli(bundle)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(result.stdout, b"")
            self.assertIn(b"Public field evidence mismatch", result.stderr)
            self.assertEqual(bundle, before)

    def test_source_controls_v1_v2_and_input_successor_rejections(self):
        for version in ("v1", "v2"):
            for family in TRUTH:
                control = source_control(family, version)
                original = copy.deepcopy(control)
                verify_bundle_identities(control)
                validate_pipeline_bundle(control)
                published = cli(control)
                self.assertEqual(published.returncode, 0, published.stderr)
                row = json.loads(published.stdout)
                self.assertEqual(row["observation_id"], control["input_observation"]["observation_id"])
                self.assertEqual(row["belief_id"], control["input_belief"]["belief_id"])
                for which in ("input", "successor"):
                    with self.subTest(version=version, family=family, which=which):
                        forged = copy.deepcopy(control)
                        field = forged[f"{which}_observation"]["view"]["field"]
                        field[family] = ("raindance" if field[family] != "raindance" else "sunnyday") if family == "weather" else (
                            "grassyterrain" if field[family] != "grassyterrain" else "electricterrain") if family == "terrain" else (
                            [] if "trickroom" in field[family] else ["trickroom"])
                        _seal_bundle(forged)
                        verify_bundle_identities(forged)
                        before = copy.deepcopy(forged)
                        with self.assertRaisesRegex(PipelineRecordError, "Public field evidence mismatch"):
                            validate_pipeline_bundle(forged)
                        result = cli(forged)
                        self.assertEqual(result.returncode, 2, result.stderr)
                        self.assertEqual(result.stdout, b"")
                        self.assertIn(b"Public field evidence mismatch", result.stderr)
                        self.assertEqual(forged, before)
                        validate_pipeline_bundle(control)
                self.assertEqual(control, original)

    def test_six_ordinary_exact_key_cases(self):
        for family in TRUTH:
            for mode in ("missing", "extra"):
                with self.subTest(family=family, mode=mode):
                    bundle = source_control(family)
                    field = bundle["input_observation"]["view"]["field"]
                    if mode == "missing":
                        del field[family]
                    else:
                        field["unreviewed_field"] = "trickroom"
                    _seal_bundle(bundle)
                    verify_bundle_identities(bundle)
                    with self.assertRaisesRegex(PipelineRecordError, "fields are not exact"):
                        validate_pipeline_bundle(bundle)
                    result = cli(bundle)
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertEqual(result.stdout, b"")
                    self.assertIn(b"fields are not exact", result.stderr)

    def test_field_types_are_enforced_on_both_observations(self):
        for which in ("input", "successor"):
            for field, value in (("weather", 1), ("terrain", False), ("pseudo_weather", [1]),
                                 ("side_conditions", {"self": {"spikes": True}, "opponent": {}}),
                                 ("side_conditions", {"self": [], "opponent": {}}),
                                 ("side_conditions", {"self": {}, "opponent": {}, "extra": {}})):
                with self.subTest(which=which, field=field, value=value):
                    bundle = source_control("weather")
                    bundle[f"{which}_observation"]["view"]["field"][field] = value
                    _seal_bundle(bundle)
                    verify_bundle_identities(bundle)
                    with self.assertRaises(PipelineRecordError):
                        validate_pipeline_bundle(bundle)
                    result = cli(bundle)
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertEqual(result.stdout, b"")
        observation = source_control("weather")["input_observation"]
        observation["view"]["field"]["side_conditions"]["self"]["spikes"] = 10 ** 400
        with self.assertRaisesRegex(ValueError, "finite number maps"):
            validate_public_field(observation)

    def test_sparse_v1_v2_only_when_no_field_writer_is_hidden(self):
        for version in ("v1", "v2"):
            for player in ("p1", "p2"):
                control = _bundle(perspective=player, version=version)
                verify_bundle_identities(control)
                validate_pipeline_bundle(control)
            for view_mode in ("missing-field", "missing-view"):
                bundle = source_control("weather", version)
                if view_mode == "missing-field":
                    del bundle["input_observation"]["view"]["field"]
                else:
                    del bundle["input_observation"]["view"]
                _seal_bundle(bundle)
                verify_bundle_identities(bundle)
                result = cli(bundle)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertEqual(result.stdout, b"")
                self.assertIn(b"field writers require a field view", result.stderr)
            for prefix in (["|-weather|RainDance", "|-weather|none"],
                           ["|-fieldstart|move: Electric Terrain|[from] ability: Electric Surge|[of] p1a: Pin", "|-fieldend|move: Electric Terrain"],
                           ["|-fieldstart|move: Trick Room|[of] p1a: Room", "|-fieldend|move: Trick Room"]):
                for line in prefix:
                    validate_protocol_record(line)
                observation = {"schema_version": f"observable-battle-state/{version}", "protocol_prefix": prefix, "view": {}}
                with self.assertRaisesRegex(ValueError, "field writers require a field view"):
                    validate_public_typed_state(observation)

    def test_upkeep_never_creates_or_replaces_weather(self):
        for prefix in (["|-weather|RainDance|[upkeep]"],
                       ["|-weather|RainDance", "|-weather|SunnyDay|[upkeep]"]):
            for line in prefix:
                validate_protocol_record(line)
            observation = {"protocol_prefix": prefix, "view": {"field": {
                "weather": "raindance", "terrain": None, "pseudo_weather": [],
                "side_conditions": {"self": {}, "opponent": {}}}}}
            with self.assertRaisesRegex(ValueError, "weather upkeep disagrees"):
                validate_public_field(observation)

    def test_malformed_prefix_rejects_before_field_authority(self):
        bundle = source_control("weather")
        original_input = list(bundle["input_observation"]["protocol_prefix"])
        suffix = bundle["successor_observation"]["protocol_prefix"][len(original_input):]
        bad = "|-weather|SunnyDay|[from] ability: Drizzle|[of] p1a: Sun"
        bundle["input_observation"]["protocol_prefix"] = original_input + [bad]
        bundle["successor_observation"]["protocol_prefix"] = original_input + [bad] + suffix
        for which in ("input", "successor"):
            observation = bundle[f"{which}_observation"]
            bundle[f"{which}_belief"]["source_protocol_prefix"] = list(observation["protocol_prefix"])
            observation["event_cursor"] = len(observation["protocol_prefix"])
            observation["protocol_prefix_hash"] = hashlib.sha256(json.dumps(observation["protocol_prefix"], ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
        _seal_bundle(bundle)
        verify_bundle_identities(bundle)
        with self.assertRaisesRegex(PipelineRecordError, "unsupported source grammar"):
            validate_pipeline_bundle(bundle)
        result = cli(bundle)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stdout, b"")
        self.assertNotIn(b"Public field evidence mismatch", result.stderr)


if __name__ == "__main__":
    unittest.main()
