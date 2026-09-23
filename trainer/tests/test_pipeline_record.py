import hashlib
import json
import unittest

from neural.canonical_action import canonical_action_from_legal_action
from neural.pipeline_record import (
    PipelineRecordError,
    validate_pipeline_bundle,
)


def _typescript_hash(value):
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _observation(battle_id, perspective, observation_id, prefix, rqid):
    legal = {"index": 0, "kind": "move", "slot": 1, "choice": "move 1", "label": "Move 1"}
    return {
        "schema_version": "observable-battle-state/v1",
        "source_kind": "sim_core",
        "battle_id": battle_id,
        "perspective": perspective,
        "event_cursor": len(prefix),
        "protocol_prefix_hash": _typescript_hash(prefix),
        "snapshot_phase": "pre_decision",
        "other_phase": None,
        "request": {
            "player": perspective,
            "wait": False,
            "team_preview": False,
            "force_switch": False,
            "rqid": rqid,
            "legal_actions": {
                "actions": [legal] + [None] * 12,
                "mask": [True] + [False] * 12,
                "available_indices": [0],
            },
        },
        "decision_availability": {"available": True, "reason": "request", "legal_action_indices": [0]},
        "protocol_prefix": prefix,
        "view": {"terminated": False},
        "observation_id": observation_id,
    }


def _belief(battle_id, perspective, belief_id, observation_id, prefix, snapshot, parent_id=None, lineage=None):
    return {
        "schema_version": "belief-state/v1",
        "belief_id": belief_id,
        "information_regime": "player",
        "battle_id": battle_id,
        "perspective": perspective,
        "observation": {"observation_id": observation_id},
        "source_protocol_prefix": prefix,
        "parent_belief_id": parent_id,
        "simulator_snapshot": snapshot,
        "transition_lineage": lineage,
    }


def _bundle(unicode_prefix=False):
    battle_id = "pipeline-python-fixture"
    prefix = ["|gen|9", "|turn|1"]
    if unicode_prefix:
        prefix.append("|message|Pokémon")
    successor_prefix = prefix + ["|move|p1a: Pikachu|Tackle|p2a: Eevee", "|turn|2"]
    input_observation = _observation(battle_id, "p1", "obs-" + "1" * 64, prefix, 12)
    successor_observation = _observation(battle_id, "p1", "obs-" + "2" * 64, successor_prefix, 13)
    request = {
        "player": "p1",
        "rqid": 12,
        "force_switch": False,
        "legal_actions": {"0": {"index": 0, "kind": "move", "slot": 1, "choice": "move 1", "label": "Move 1"}},
    }
    action = canonical_action_from_legal_action(request["legal_actions"]["0"], request, "p1")
    transition_id = "transition-" + "5" * 64
    input_belief_id = "belief-" + "3" * 64
    successor_belief_id = "belief-" + "4" * 64
    parent_branch = "branch-input"
    output_branch = "branch-output"
    input_fingerprint = "a" * 64
    output_fingerprint = "b" * 64
    input_belief = _belief(
        battle_id,
        "p1",
        input_belief_id,
        input_observation["observation_id"],
        prefix,
        {"branch_id": parent_branch, "state_fingerprint": input_fingerprint, "parent_branch_id": None, "transition_id": None},
    )
    transition = {
        "schema_version": "pipeline-transition-reference/v1",
        "transition_id": transition_id,
        "parent_branch_id": parent_branch,
        "branch_id": output_branch,
        "input_state_fingerprint": input_fingerprint,
        "output_state_fingerprint": output_fingerprint,
        "simulator_revision": "sim-core@0.1.0+pokemon-showdown@0.11.10",
        "step_index": 0,
        "action_id": action["action_id"],
    }
    lineage = {
        "transition_id": transition_id,
        "parent_branch_id": parent_branch,
        "branch_id": output_branch,
        "input_state_fingerprint": input_fingerprint,
        "output_state_fingerprint": output_fingerprint,
        "simulator_revision": transition["simulator_revision"],
        "step_index": 0,
        "input_observation_id": input_observation["observation_id"],
        "output_observation_id": successor_observation["observation_id"],
    }
    successor_belief = _belief(
        battle_id,
        "p1",
        successor_belief_id,
        successor_observation["observation_id"],
        successor_prefix,
        {"branch_id": output_branch, "state_fingerprint": output_fingerprint, "parent_branch_id": parent_branch, "transition_id": transition_id},
        parent_id=input_belief_id,
        lineage=lineage,
    )
    return {
        "schema_version": "pipeline-linked-record/v1",
        "battle_id": battle_id,
        "source_ref": f"sim-core://{battle_id}",
        "ruleset": "gen9randombattle",
        "perspective": "p1",
        "input_observation": input_observation,
        "input_belief": input_belief,
        "action": action,
        "transition": transition,
        "successor_observation": successor_observation,
        "successor_belief": successor_belief,
    }


class PipelineRecordTest(unittest.TestCase):
    def test_valid_linked_bundle_builds_checkpoint_free_data_record(self):
        record = validate_pipeline_bundle(_bundle())
        self.assertEqual(record["schema_version"], "dataset-record/v1")
        self.assertEqual(record["perspective"], "p1")
        self.assertEqual(record["feature_cursor"], 0)
        self.assertEqual(record["input_fields"], [])
        self.assertEqual(record["private_data_provenance"], "acting_player_request")
        self.assertEqual(record["feature_input_eligibility"], "acting_player_private")
        self.assertTrue(record["record_id"].startswith("datarec-"))

    def test_broken_prefix_action_join_and_private_payload_fail_closed(self):
        prefix = _bundle()
        prefix["successor_observation"]["protocol_prefix"][0] = "|gen|8"
        prefix["successor_observation"]["protocol_prefix_hash"] = _typescript_hash(prefix["successor_observation"]["protocol_prefix"])
        with self.assertRaisesRegex(PipelineRecordError, "not an exact extension"):
            validate_pipeline_bundle(prefix)

        action = _bundle()
        action["transition"]["action_id"] = "act-" + "9" * 64
        with self.assertRaisesRegex(PipelineRecordError, "does not match canonical action"):
            validate_pipeline_bundle(action)

        private = _bundle()
        private["transition"]["simulator_state"] = {"private": True}
        with self.assertRaisesRegex(PipelineRecordError, "private or raw simulator data"):
            validate_pipeline_bundle(private)

    def test_unicode_prefix_hashes_keep_typescript_and_data_envelopes_distinct(self):
        bundle = _bundle(unicode_prefix=True)
        record = validate_pipeline_bundle(bundle)
        observable_hash = bundle["input_observation"]["protocol_prefix_hash"]
        self.assertNotEqual(record["observation_prefix_hash"], observable_hash)
        self.assertEqual(record["observation_cursor"], len(bundle["input_observation"]["protocol_prefix"]))

    def test_simulator_truth_and_swapped_perspective_fail_closed(self):
        research = _bundle()
        research["successor_belief"]["information_regime"] = "simulator_research"
        with self.assertRaisesRegex(PipelineRecordError, "player information regime"):
            validate_pipeline_bundle(research)

        swapped = _bundle()
        swapped["successor_observation"]["perspective"] = "p2"
        with self.assertRaisesRegex(PipelineRecordError, "perspective disagrees"):
            validate_pipeline_bundle(swapped)


if __name__ == "__main__":
    unittest.main()
