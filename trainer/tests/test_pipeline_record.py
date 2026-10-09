import hashlib
import io
import json
import copy
import unittest
from unittest.mock import patch

from neural.ts_identity import observation_digest, belief_digest, REFERENCE_KEYS, verify_bundle_identities
from neural.canonical_action import canonical_action_from_legal_action
from neural.protocol_contract import (
    RECORD_FIXTURES, REJECTION_FIXTURES, SUPPORTED_COMMANDS, VALID_RECORD_CONTROLS, VALIDATION_RULES,
    ProtocolContractError, ProtocolRecordError, load_protocol_contract, validate_protocol_contract,
    validate_protocol_record,
)
from neural.pipeline_record import (
    PipelineRecordError,
    _prefix,
    main,
    validate_pipeline_bundle,
)
from neural.typed_state import project_public_typed_state
from neural.public_item import project_public_items, project_public_item_dispositions
from neural.public_health import project_public_health
from neural.public_boosts import public_boost_evidence


def _typescript_hash(value):
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _observation(battle_id, perspective, observation_id, prefix, rqid, version="v1"):
    legal = {"index": 0, "kind": "move", "slot": 1, "choice": "move 1", "label": "Move 1"}
    return {
        "schema_version": f"observable-battle-state/{version}",
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
        "view": {"terminated": False, **({"self_team": [], "opponent_team": []} if version == "v2" else {})},
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


def _seal_bundle(bundle):
    # Synthetic fixtures use actual content identities, not historical repeated-digit IDs.
    references = []
    for which in ('input', 'successor'):
        obs = bundle[which + '_observation']
        obs['observation_id'] = observation_digest(obs)
        ref = {k: obs[k] for k in REFERENCE_KEYS}
        references.append(ref)
        belief = bundle[which + '_belief']
        belief['observation'] = dict(ref)
        belief['observation_history'] = list(references)
        belief['evidence'] = []; belief['candidates'] = []
        if which == 'successor':
            belief['parent_belief_id'] = bundle['input_belief']['belief_id']
            belief['transition_lineage']['input_observation_id'] = bundle['input_observation']['observation_id']
            belief['transition_lineage']['output_observation_id'] = obs['observation_id']
        belief['belief_id'] = belief_digest(belief)
    return bundle


def _bundle(unicode_prefix=False, perspective="p1", version="v1"):
    battle_id = f"pipeline-python-fixture-{perspective}-{version}"
    prefix = ["|gen|9", "|turn|1"]
    if unicode_prefix:
        prefix.append("|message|Pokémon")
    successor_prefix = prefix + ["|move|p1a: Pikachu|Tackle|p2a: Eevee", "|turn|2"]
    input_observation = _observation(battle_id, perspective, "obs-" + "1" * 64, prefix, 12, version)
    successor_observation = _observation(battle_id, perspective, "obs-" + "2" * 64, successor_prefix, 13, version)
    request = {
        "player": perspective,
        "rqid": 12,
        "force_switch": False,
        "legal_actions": {"0": {"index": 0, "kind": "move", "slot": 1, "choice": "move 1", "label": "Move 1"}},
    }
    action = canonical_action_from_legal_action(request["legal_actions"]["0"], request, perspective)
    transition_id = "transition-" + "5" * 64
    input_belief_id = "belief-" + "3" * 64
    successor_belief_id = "belief-" + "4" * 64
    parent_branch = "branch-input"
    output_branch = "branch-output"
    input_fingerprint = "a" * 64
    output_fingerprint = "b" * 64
    input_belief = _belief(
        battle_id,
        perspective,
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
        perspective,
        successor_belief_id,
        successor_observation["observation_id"],
        successor_prefix,
        {"branch_id": output_branch, "state_fingerprint": output_fingerprint, "parent_branch_id": parent_branch, "transition_id": transition_id},
        parent_id=input_belief_id,
        lineage=lineage,
    )
    return _seal_bundle({
        "schema_version": "pipeline-linked-record/v1",
        "battle_id": battle_id,
        "source_ref": f"sim-core://{battle_id}",
        "ruleset": "gen9randombattle",
        "perspective": perspective,
        "input_observation": input_observation,
        "input_belief": input_belief,
        "action": action,
        "transition": transition,
        "successor_observation": successor_observation,
        "successor_belief": successor_belief,
    })


def _rehashed_protocol_candidate(bundle, where, record):
    candidate = copy.deepcopy(bundle)
    input_prefix = candidate["input_observation"]["protocol_prefix"]
    successor_prefix = candidate["successor_observation"]["protocol_prefix"]
    parts = record.split("|")
    context_start = None
    if len(parts) > 3 and parts[1] == "-sideend":
        side, raw_effect = parts[2], parts[3]
        effect = "".join(char.lower() for char in raw_effect.removeprefix("move: ") if char.isalnum())
        active = False
        prefix = input_prefix if where == "input" else successor_prefix
        for prior in prefix:
            prior_parts = prior.split("|")
            if len(prior_parts) <= 3 or prior_parts[2] != side:
                continue
            prior_effect = "".join(char.lower() for char in prior_parts[3].removeprefix("move: ") if char.isalnum())
            if prior_effect == effect and prior_parts[1] in ("-sidestart", "-sideend"):
                active = prior_parts[1] == "-sidestart"
        if not active:
            context_start = f"|-sidestart|{side}|{raw_effect}"
    if where == "input":
        at = len(input_prefix)
        if context_start:
            input_prefix.append(context_start)
            successor_prefix.insert(at, context_start)
            at += 1
        input_prefix.append(record)
        successor_prefix.insert(at, record)
    else:
        if context_start:
            successor_prefix.append(context_start)
        successor_prefix.append(record)
    for which in ("input", "successor"):
        observation = candidate[which + "_observation"]
        prefix = observation["protocol_prefix"]
        observation["event_cursor"] = len(prefix)
        observation["protocol_prefix_hash"] = _typescript_hash(prefix)
        candidate[which + "_belief"]["source_protocol_prefix"] = list(prefix)
        # Protocol controls must represent their derived health facts even in minimal v1.
        try:
            health = project_public_health(prefix)
        except (ValueError, TypeError, IndexError, ZeroDivisionError):
            health = {}
        for ident, facts in health.items():
            team = "self_team" if ident[:2] == observation["perspective"] else "opponent_team"
            rows = observation["view"].setdefault(team, [])
            row = next((entry for entry in rows if entry.get("ident") == ident), None)
            if row is None:
                row = {"ident": ident}; rows.append(row)
            row.update(facts)
            if observation.get("schema_version") == "observable-battle-state/v2" and team == "opponent_team":
                try:
                    stages = public_boost_evidence(prefix).get(ident)
                except ValueError:
                    stages = None
                row.setdefault("public_boosts", stages or dict.fromkeys(("atk", "def", "spa", "spd", "spe", "accuracy", "evasion"), None))
        if observation.get("schema_version") == "observable-battle-state/v2":
            try:
                projected = project_public_typed_state(prefix)
            except ValueError:
                projected = None
            if projected:
                perspective = observation["perspective"]
                own = projected["side_conditions_by_player"][perspective]
                other = "p2" if perspective == "p1" else "p1"
                opponent = projected["side_conditions_by_player"][other]
                if own or opponent:
                    observation["view"]["field"] = {"side_conditions": {"self": own, "opponent": opponent}}
    return _seal_bundle(candidate)


_REPEATED_SINGLETON_TAG_FIXTURES = (
    ("damage", "[from]", "|-damage|p1a: Pikachu|50/100|[from] move: Tackle|[from] ability: Static"),
    ("damage", "[of]", "|-damage|p1a: Pikachu|50/100|[of] p2: Eevee|[of] p1a: Pikachu"),
    ("damage", "[silent]", "|-damage|p1a: Pikachu|50/100|[silent]|[silent]"),
    ("damage", "[partiallytrapped]", "|-damage|p1a: Pikachu|50/100|[partiallytrapped]|[partiallytrapped]"),
    ("heal", "[from]", "|-heal|p1a: Pikachu|50/100|[from] move: Recover|[from] ability: Regenerator"),
    ("heal", "[of]", "|-heal|p1a: Pikachu|50/100|[of] p2: Eevee|[of] p1a: Pikachu"),
    ("heal", "[silent]", "|-heal|p1a: Pikachu|50/100|[silent]|[silent]"),
    ("heal", "[zeffect]", "|-heal|p1a: Pikachu|50/100|[zeffect]|[zeffect]"),
    ("heal", "[wisher]", "|-heal|p1a: Pikachu|50/100|[wisher] Eevee|[wisher] Blissey"),
    ("boost", "[from]", "|-boost|p1a: Pikachu|atk|1|[from] move: Swords Dance|[from] ability: Intimidate"),
    ("boost", "[silent]", "|-boost|p1a: Pikachu|atk|1|[silent]|[silent]"),
    ("boost", "[zeffect]", "|-boost|p1a: Pikachu|atk|1|[zeffect]|[zeffect]"),
)


def _forced_switch_bundle():
    bundle = _bundle()
    observation = bundle["input_observation"]
    legal = {"index": 8, "kind": "switch", "slot": 2, "choice": "switch 2", "label": "Switch 2"}
    request = observation["request"]
    request["force_switch"] = True
    request["legal_actions"] = {
        "actions": [None] * 8 + [legal] + [None] * 4,
        "mask": [False] * 8 + [True] + [False] * 4,
        "available_indices": [8],
    }
    observation["snapshot_phase"] = "forced_switch"
    observation["decision_availability"]["legal_action_indices"] = [8]
    context = {"player": "p1", "rqid": request["rqid"], "force_switch": True, "legal_actions": {"8": legal}}
    bundle["action"] = canonical_action_from_legal_action(legal, context, "p1")
    bundle["schema_version"] = "pipeline-forced-switch-record/v1"
    bundle["transition"].update({
        "schema_version": "pipeline-forced-switch-reference/v1",
        "action_id": bundle["action"]["action_id"],
        "acting_player": "p1", "waiting_player": "p2",
    })
    return _seal_bundle(bundle)


def _revival_bundle():
    bundle = _forced_switch_bundle()
    request = bundle["input_observation"]["request"]
    request["side"] = [
        {"slot": 1, "ident": "p1: Reviver", "active": True, "condition": "100/100", "reviving": True},
        {"slot": 2, "ident": "p1: Target", "active": False, "condition": "0 fnt"},
        {"slot": 3, "ident": "p1: Reserve", "active": False, "condition": "100/100"},
    ]
    bundle["input_observation"]["view"]["self_team"] = [
        {"ident": p["ident"], "active": p["active"], **project_public_health([f"|-heal|{p['ident']}|{p['condition']}"])[p["ident"]]}
        for p in request["side"]
    ]
    legal = request["legal_actions"]["actions"][8]
    legal["kind"] = "revive"
    context = {"player": "p1", "rqid": request["rqid"], "force_switch": True, "legal_actions": {"8": legal}, "side": request["side"]}
    bundle["action"] = canonical_action_from_legal_action(legal, context)
    bundle["transition"]["action_id"] = bundle["action"]["action_id"]
    bundle["schema_version"] = "pipeline-revival-record/v1"
    bundle["transition"]["schema_version"] = "pipeline-revival-reference/v1"
    return _seal_bundle(bundle)


class PipelineRecordTest(unittest.TestCase):
    def test_ce04_slots_wish_public_heal_evidence_accepts_exact_source_form_and_rejects_rehashes(self):
        source_forms = (
            ("Moves.wish.onEnd", "|-heal|p1a: Recipient|100/100|[from] move: Wish|[wisher] Wisher"),
        )
        malformed = (
            "|-heal|p1a: Recipient|100/100|[wisher] Wisher",
            "|-heal|p1a: Recipient|100/100|[from] ability: Static|[wisher] Wisher",
            "|-heal|p1a: Recipient|100/100|[wisher] Wisher|[from] move: Wish",
            "|-heal|p1a: Recipient|100/100|[from] move: Wish|[wisher] Wisher|[wisher] Other",
            "|-heal|p1a: Recipient|100/100|[from] move: Wish|[wisher] Wisher|[zeffect]",
            "|-heal|p1a: Recipient|101/100|[from] move: Wish|[wisher] Wisher",
        )
        self.assertEqual(VALIDATION_RULES["heal_wisher_dependency"], {
            "required_from": "[from] move: Wish",
            "required_tag_order": ["[from]", "[wisher]"],
        })
        validate_protocol_record("|-heal|p1a: Recipient|100/100|[from] ability: Static")
        for version in ("v1", "v2"):
            for perspective in ("p1", "p2"):
                for where in ("input", "successor"):
                    for emitter, valid in source_forms:
                        with self.subTest(version=version, perspective=perspective, where=where, emitter=emitter):
                            candidate = _rehashed_protocol_candidate(
                                _bundle(perspective=perspective, version=version), where, valid,
                            )
                            before = copy.deepcopy(candidate)
                            published = validate_pipeline_bundle(candidate)
                            self.assertEqual(published["perspective"], perspective)
                            self.assertEqual(candidate, before)
                            stdout, stderr = io.StringIO(), io.StringIO()
                            with patch("sys.stdin", io.StringIO(json.dumps(candidate))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                                self.assertEqual(main(), 0, stderr.getvalue())
                            self.assertTrue(stdout.getvalue())
                            self.assertEqual(candidate, before)
                    for record in malformed:
                        with self.subTest(version=version, perspective=perspective, where=where, evidence=record):
                            candidate = _rehashed_protocol_candidate(
                                _bundle(perspective=perspective, version=version), where, record,
                            )
                            before = copy.deepcopy(candidate)
                            with self.assertRaises(ProtocolRecordError):
                                validate_protocol_record(record)
                            with self.assertRaises(PipelineRecordError):
                                validate_pipeline_bundle(candidate)
                            self.assertEqual(candidate, before)
                            stdout, stderr = io.StringIO(), io.StringIO()
                            with patch("sys.stdin", io.StringIO(json.dumps(candidate))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                                self.assertEqual(main(), 2, stderr.getvalue())
                            self.assertEqual(stdout.getvalue(), "")
                            self.assertEqual(candidate, before)

    def test_ce04d1_entry_hazard_records_publish_only_pinned_forms(self):
        valid = (
            "|-sidestart|p1: One|Spikes",
            "|-sidestart|p2: Two|move: Toxic Spikes",
            "|-sidestart|p1: One|move: Stealth Rock",
            "|-sidestart|p2: Two|move: Sticky Web",
            "|-sideend|p1: One|Spikes|[from] move: Rapid Spin|[of] p1a: Spinner",
            "|-sideend|p2: Two|move: Toxic Spikes|[of] p2a: Poison",
        )
        rejected = (
            "|-sidestart|p1a: One|Spikes", "|-sidestart|p1: One|move: Spikes",
            "|-sideend|p1: One|Spikes|[from] move: Court Change|[of] p1a: Spinner",
            "|-sideend|p1: One|Spikes|[of] p1a: Spinner", "|-sideend|p1: One|Stealth Rock|[from] move: Rapid Spin|[of] p1: Spinner",
        )
        for version in ("v2",):
            for perspective in ("p1", "p2"):
                for where in ("input", "successor"):
                    for record in valid:
                        candidate = _rehashed_protocol_candidate(_bundle(perspective=perspective, version=version), where, record)
                        before = copy.deepcopy(candidate)
                        validate_protocol_record(record)
                        self.assertEqual(validate_pipeline_bundle(candidate)["perspective"], perspective)
                        self.assertEqual(candidate, before)
                    for record in rejected:
                        candidate = _rehashed_protocol_candidate(_bundle(perspective=perspective, version=version), where, record)
                        before = copy.deepcopy(candidate)
                        with self.assertRaises(ProtocolRecordError): validate_protocol_record(record)
                        with self.assertRaises(PipelineRecordError): validate_pipeline_bundle(candidate)
                        stdout, stderr = io.StringIO(), io.StringIO()
                        with patch("sys.stdin", io.StringIO(json.dumps(candidate))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                            self.assertEqual(main(), 2, stderr.getvalue())
                        self.assertEqual(stdout.getvalue(), "")
                        self.assertEqual(candidate, before)

    def test_ce04d2_screen_records_publish_only_pinned_generated_forms(self):
        valid = (
            "|-sidestart|p1: One|Reflect",
            "|-sidestart|p2: Two|move: Light Screen",
            "|-sidestart|p1: One|move: Aurora Veil",
            "|-sideend|p1: One|Reflect",
            "|-sideend|p2: Two|move: Light Screen",
            "|-sideend|p1: One|move: Aurora Veil",
        )
        rejected = (
            "|sidestart|p1: One|Reflect", "|-sidestart|p1a: One|Reflect",
            "|-sidestart|p1: One|move: Reflect", "|-sidestart|p1: One|Reflect|[from] move: Reflect",
            "|-sideend|p1: One|Reflect|[from] move: Defog", "|-sideend|p1: One|Aurora Veil",
            "|-sidestart|p1: One|Safeguard", "|-sidestart|p1: One|Mist",
            "|-sidestart|p1: One|Reflect ", "|-sideend|p1: One|move: Light Screen|extra",
        )
        self.assertEqual(VALIDATION_RULES["screen"], {
            "ids": ["reflect", "lightscreen", "auroraveil"],
            "start_forms": {"reflect": "Reflect", "lightscreen": "move: Light Screen", "auroraveil": "move: Aurora Veil"},
            "end_forms": {"reflect": "Reflect", "lightscreen": "move: Light Screen", "auroraveil": "move: Aurora Veil"},
            "excluded_forms": ["Safeguard", "Mist"],
        })
        for version in ("v2",):
            for perspective in ("p1", "p2"):
                for where in ("input", "successor"):
                    for record in valid:
                        candidate = _rehashed_protocol_candidate(_bundle(perspective=perspective, version=version), where, record)
                        before = copy.deepcopy(candidate)
                        validate_protocol_record(record)
                        self.assertEqual(validate_pipeline_bundle(candidate)["perspective"], perspective)
                        self.assertEqual(candidate, before)
                    for record in rejected:
                        candidate = _rehashed_protocol_candidate(_bundle(perspective=perspective, version=version), where, record)
                        before = copy.deepcopy(candidate)
                        with self.assertRaises(ProtocolRecordError): validate_protocol_record(record)
                        with self.assertRaises(PipelineRecordError): validate_pipeline_bundle(candidate)
                        stdout, stderr = io.StringIO(), io.StringIO()
                        with patch("sys.stdin", io.StringIO(json.dumps(candidate))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                            self.assertEqual(main(), 2, stderr.getvalue())
                        self.assertEqual(stdout.getvalue(), "")
                        self.assertEqual(candidate, before)

    def test_ce04d3_court_change_records_publish_only_the_pinned_atomic_swap(self):
        valid = (
            "|-swapsideconditions",
            "|-activate|p1a: Changer|move: Court Change",
        )
        rejected = (
            "|swapsideconditions", "|-swapsideconditions|p1: One|p2: Two",
            "|-swapsideconditions|[silent]", "|-swapsideconditions|",
            "|-swapsideconditions|p1b: One", "|-swapsideconditions|extra",
            "|-activate|p1: Changer|move: Court Change", "|-activate|p1b: Changer|move: Court Change",
            "|-activate|p1a: Changer|move: Court Change|[silent]",
            "|-activate|p1a: Changer|move: Court  Change",
        )
        self.assertEqual(VALIDATION_RULES["court_change"], {
            "command": "-swapsideconditions",
            "activation_command": "-activate",
            "activation_effect": "move: Court Change",
            "transferred_ids": ["mist", "lightscreen", "reflect", "spikes", "safeguard", "tailwind", "toxicspikes", "stealthrock", "waterpledge", "firepledge", "grasspledge", "stickyweb", "auroraveil", "luckychant"],
            "excluded_ids": ["gmaxsteelsurge", "gmaxcannonade", "gmaxvinelash", "gmaxwildfire", "gmaxvolcalith"],
        })
        for version in ("v1", "v2"):
            for perspective in ("p1", "p2"):
                for where in ("input", "successor"):
                    for record in valid:
                        candidate = _rehashed_protocol_candidate(_bundle(perspective=perspective, version=version), where, record)
                        before = copy.deepcopy(candidate)
                        validate_protocol_record(record)
                        self.assertEqual(validate_pipeline_bundle(candidate)["perspective"], perspective)
                        self.assertEqual(candidate, before)
                    for record in rejected:
                        candidate = _rehashed_protocol_candidate(_bundle(perspective=perspective, version=version), where, record)
                        before = copy.deepcopy(candidate)
                        with self.assertRaises(ProtocolRecordError): validate_protocol_record(record)
                        with self.assertRaises(PipelineRecordError): validate_pipeline_bundle(candidate)
                        self.assertEqual(candidate, before)
                        stdout, stderr = io.StringIO(), io.StringIO()
                        with patch("sys.stdin", io.StringIO(json.dumps(candidate))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                            self.assertEqual(main(), 2, stderr.getvalue())
                        self.assertEqual(stdout.getvalue(), "")
                        self.assertEqual(candidate, before)

    def test_ce04e1_weather_records_publish_only_pinned_generated_forms(self):
        valid = (
            "|-weather|RainDance",
            "|-weather|SunnyDay|[upkeep]",
            "|-weather|Sandstorm|[from] ability: Sand Stream|[of] p2a: Setter",
            "|-weather|Snowscape|[from] ability: Snow Warning|[of] p1a: Setter",
            "|-weather|SunnyDay|[from] ability: Orichalcum Pulse|[of] p1a: Setter",
            "|-weather|none",
        )
        rejected = (
            "|-weather|Hail", "|-weather|Sandstorm", "|-weather|raindance",
            "|-weather|PrimordialSea",
            "|-weather|RainDance|[from] ability: Drought|[of] p1a: Setter",
            "|-weather|SunnyDay|[from] ability: Drought|[of] p1: Setter",
            "|-weather|Sandstorm|[from] ability: Sand Stream|[of] p1b: Setter",
            "|-weather|RainDance|[upkeep]|[of] p1a: Setter",
            "|-weather|SunnyDay|[of] p1a: Setter|[from] ability: Drought",
            "|-weather|SunnyDay|[from] ability: Drought|[of] p1a: Setter|[upkeep]",
            "|-weather|none|[upkeep]",
            "|-weather| RainDance",
        )
        self.assertEqual(VALIDATION_RULES["weather"], {
            "ids": ["RainDance", "SunnyDay", "Sandstorm", "Snowscape"],
            "ability_origins": {
                "RainDance": ["Drizzle"], "SunnyDay": ["Drought", "Orichalcum Pulse"],
                "Sandstorm": ["Sand Stream"], "Snowscape": ["Snow Warning"],
            },
            "move_origins": {
                "RainDance": ["Rain Dance"], "SunnyDay": ["Sunny Day"],
                "Snowscape": ["Snowscape", "Chilly Reception"],
            },
        })
        for version in ("v1", "v2"):
            for perspective in ("p1", "p2"):
                for where in ("input", "successor"):
                    for record in valid:
                        with self.subTest(version=version, perspective=perspective, where=where, record=record):
                            candidate = _rehashed_protocol_candidate(_bundle(perspective=perspective, version=version), where, record)
                            before = copy.deepcopy(candidate)
                            validate_protocol_record(record)
                            self.assertEqual(validate_pipeline_bundle(candidate)["perspective"], perspective)
                            stdout, stderr = io.StringIO(), io.StringIO()
                            with patch("sys.stdin", io.StringIO(json.dumps(candidate))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                                self.assertEqual(main(), 0, stderr.getvalue())
                            self.assertTrue(stdout.getvalue())
                            self.assertEqual(candidate, before)
                    for record in rejected:
                        with self.subTest(version=version, perspective=perspective, where=where, record=record):
                            candidate = _rehashed_protocol_candidate(_bundle(perspective=perspective, version=version), where, record)
                            before = copy.deepcopy(candidate)
                            with self.assertRaises(ProtocolRecordError):
                                validate_protocol_record(record)
                            with self.assertRaises(PipelineRecordError):
                                validate_pipeline_bundle(candidate)
                            stdout, stderr = io.StringIO(), io.StringIO()
                            with patch("sys.stdin", io.StringIO(json.dumps(candidate))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                                self.assertEqual(main(), 2, stderr.getvalue())
                            self.assertEqual(stdout.getvalue(), "")
                            self.assertEqual(candidate, before)

    def test_ce04e2_terrain_records_publish_only_pinned_generated_forms(self):
        valid = (
            "|-fieldstart|move: Electric Terrain|[from] ability: Electric Surge|[of] p1a: Pincurchin",
            "|-fieldstart|move: Electric Terrain|[from] ability: Hadron Engine|[of] p2a: Miraidon",
            "|-fieldstart|move: Grassy Terrain|[from] ability: Grassy Surge|[of] p1a: Rillaboom",
            "|-fieldstart|move: Grassy Terrain|[from] ability: Seed Sower|[of] p2a: Arboliva",
            "|-fieldstart|move: Psychic Terrain|[from] ability: Psychic Surge|[of] p1a: Indeedee",
            "|-fieldend|move: Electric Terrain",
            "|-fieldend|move: Grassy Terrain",
            "|-fieldend|move: Psychic Terrain",
        )
        rejected = (
            "|-fieldstart|move: Electric Terrain",
            "|fieldstart|move: Electric Terrain|[from] ability: Electric Surge|[of] p1a: Pincurchin",
            "|-fieldactivate|move: Electric Terrain",
            "|-fieldstart|move: Misty Terrain|[from] ability: Misty Surge|[of] p1a: Weezing",
            "|-fieldstart|move: Grassy Terrain|[from] ability: Electric Surge|[of] p1a: Pincurchin",
            "|-fieldstart|move: Electric Terrain|[of] p1a: Pincurchin|[from] ability: Electric Surge",
            "|-fieldstart|move: Electric Terrain|[from] ability: Electric Surge|[of] p1: Pincurchin",
            "|-fieldstart|move: Electric Terrain|[from] ability: Electric Surge|[of] p1b: Pincurchin",
            "|-fieldstart|move: Electric Terrain|[from] ability: Electric Surge|[of] p1a: Pincurchin|[upkeep]",
            "|-fieldend|move: Grassy Terrain|[from] move: Ice Spinner",
            "|-fieldstart|move:  Electric Terrain|[from] ability: Electric Surge|[of] p1a: Pincurchin",
        )
        self.assertEqual(VALIDATION_RULES["terrain"], {
            "ids": ["electricterrain", "grassyterrain", "psychicterrain"],
            "public_names": {
                "electricterrain": "move: Electric Terrain",
                "grassyterrain": "move: Grassy Terrain",
                "psychicterrain": "move: Psychic Terrain",
            },
            "ability_origins": {
                "electricterrain": ["Electric Surge", "Hadron Engine"],
                "grassyterrain": ["Grassy Surge", "Seed Sower"],
                "psychicterrain": ["Psychic Surge"],
            },
        })
        for version in ("v1", "v2"):
            for perspective in ("p1", "p2"):
                for where in ("input", "successor"):
                    for record in valid:
                        with self.subTest(version=version, perspective=perspective, where=where, record=record):
                            candidate = _rehashed_protocol_candidate(_bundle(perspective=perspective, version=version), where, record)
                            before = copy.deepcopy(candidate)
                            validate_protocol_record(record)
                            self.assertEqual(validate_pipeline_bundle(candidate)["perspective"], perspective)
                            stdout, stderr = io.StringIO(), io.StringIO()
                            with patch("sys.stdin", io.StringIO(json.dumps(candidate))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                                self.assertEqual(main(), 0, stderr.getvalue())
                            self.assertTrue(stdout.getvalue())
                            self.assertEqual(candidate, before)
                    for record in rejected:
                        with self.subTest(version=version, perspective=perspective, where=where, record=record):
                            candidate = _rehashed_protocol_candidate(_bundle(perspective=perspective, version=version), where, record)
                            before = copy.deepcopy(candidate)
                            with self.assertRaises(ProtocolRecordError):
                                validate_protocol_record(record)
                            with self.assertRaises(PipelineRecordError):
                                validate_pipeline_bundle(candidate)
                            stdout, stderr = io.StringIO(), io.StringIO()
                            with patch("sys.stdin", io.StringIO(json.dumps(candidate))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                                self.assertEqual(main(), 2, stderr.getvalue())
                            self.assertEqual(stdout.getvalue(), "")
                            self.assertEqual(candidate, before)

    def test_ce04e3_trick_room_records_publish_only_pinned_generated_forms(self):
        valid = (
            "|-fieldstart|move: Trick Room|[of] p1a: Room",
            "|-fieldend|move: Trick Room",
        )
        rejected = (
            "|-fieldstart|move: Trick Room",
            "|fieldstart|move: Trick Room|[of] p1a: Room",
            "|-fieldactivate|move: Trick Room",
            "|-fieldstart|move: Trick Room|[of] p1: Room",
            "|-fieldstart|move: Trick Room|[of] p1b: Room",
            "|-fieldstart|move: Trick Room|[persistent]|[of] p1a: Room",
            "|-fieldstart|move: Trick Room|[of] p1a: Room|[persistent]",
            "|-fieldend|move: Trick Room|[of] p1a: Room",
            "|-fieldstart|move:  Trick Room|[of] p1a: Room",
        )
        self.assertEqual(VALIDATION_RULES["trick_room"], {
            "effect": "move: Trick Room", "start_command": "-fieldstart", "end_command": "-fieldend",
            "source_tag": "[of]", "source_role": "active",
        })
        for version in ("v1", "v2"):
            for perspective in ("p1", "p2"):
                for where in ("input", "successor"):
                    for record in valid:
                        with self.subTest(version=version, perspective=perspective, where=where, record=record):
                            candidate = _rehashed_protocol_candidate(_bundle(perspective=perspective, version=version), where, record)
                            before = copy.deepcopy(candidate)
                            validate_protocol_record(record)
                            self.assertEqual(validate_pipeline_bundle(candidate)["perspective"], perspective)
                            stdout, stderr = io.StringIO(), io.StringIO()
                            with patch("sys.stdin", io.StringIO(json.dumps(candidate))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                                self.assertEqual(main(), 0, stderr.getvalue())
                            self.assertTrue(stdout.getvalue())
                            self.assertEqual(candidate, before)
                    for record in rejected:
                        with self.subTest(version=version, perspective=perspective, where=where, record=record):
                            candidate = _rehashed_protocol_candidate(_bundle(perspective=perspective, version=version), where, record)
                            before = copy.deepcopy(candidate)
                            with self.assertRaises(ProtocolRecordError):
                                validate_protocol_record(record)
                            with self.assertRaises(PipelineRecordError):
                                validate_pipeline_bundle(candidate)
                            stdout, stderr = io.StringIO(), io.StringIO()
                            with patch("sys.stdin", io.StringIO(json.dumps(candidate))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                                self.assertEqual(main(), 2, stderr.getvalue())
                            self.assertEqual(stdout.getvalue(), "")
                            self.assertEqual(candidate, before)

    def test_ce04f1_item_records_publish_only_pinned_generated_forms(self):
        valid = (
            "|-item|p2a: Target|Leftovers|[from] ability: Frisk|[of] p1a: Frisker",
            "|-item|p2a: Target|Choice Scarf|[from] move: Trick",
            "|-item|p1a: Swapper|Leftovers|[from] move: Switcheroo",
            "|-item|p1a: Holder|White Herb|[from] move: Recycle",
            "|-enditem|p2a: Target|Sitrus Berry|[eat]",
            "|-enditem|p2a: Target|Aguav Berry|[eat]",
            "|-enditem|p2a: Target|Air Balloon",
            "|-enditem|p2a: Target|Booster Energy",
            "|-enditem|p2a: Target|Focus Sash",
            "|-enditem|p2a: Target|Power Herb",
            "|-enditem|p2a: Target|Throat Spray",
            "|-enditem|p2a: Target|Weakness Policy",
            "|-enditem|p2a: Target|White Herb",
            "|-enditem|p2a: Target|Leftovers|[from] move: Knock Off|[of] p1a: Thief",
            "|-enditem|p1a: Swapper|Choice Scarf|[silent]|[from] move: Trick",
            "|-item|p1a: Balloon|Air Balloon",
            "|item|p1a: Holder|Leftovers",
            "|enditem|p1a: Holder|Leftovers",
        )
        rejected = (
            "|-item|p2a: Target|Definitely Not An Item|[from] move: Trick",
            "|-item|p2: Target|Leftovers|[from] move: Trick",
            "|-item|p2b: Target|Leftovers|[from] move: Trick",
            "|-item|p2a: Target|Leftovers|[from] ability: Frisk|[of] p2a: Ally",
            "|-item|p2a: Target|Leftovers|[of] p1a: Frisker|[from] ability: Frisk",
            "|-enditem|p2a: Target|Leftovers|[of] p1a: Thief|[from] move: Knock Off",
            "|-enditem|p2a: Target|Sitrus Berry|[eat]|[silent]",
            "|-enditem|p2a: Target|Choice Scarf|[eat]",
            "|-enditem|p2a: Target|Air Balloon|[eat]",
            "|-enditem|p2a: Target|Choice Scarf",
            "|-enditem|p2a: Target|Leftovers",
            "|-enditem|p2: Target|Power Herb",
            "|-enditem|p2b: Target|Power Herb",
            "|-enditem|p2a: Target| Power Herb",
            "|-enditem|p2a: Target|Power Herb|[silent]",
            "|-enditem|p2a: Target|Power Herb|extra",
            "|-enditem|p2: Target|Air Balloon",
            "|-enditem|p2b: Target|Air Balloon",
            "|-enditem|p2a: Target| Air Balloon",
            "|-enditem|p2a: Target|Air Balloon|[silent]",
            "|-enditem|p2a: Target|Air Balloon|extra",
            "|-item|p2a: Target| Leftovers|[from] move: Trick",
            "|-item|p2a: Target|Leftovers|[from] move: Trick|[of] p1a: Source",
            "|-item|p2a: Target|Leftovers|[from] move: Recycle",
            "|-item|p2a: Target|White Herb|[from] move: Recycle|[silent]",
            "|item|p1a: Holder|Leftovers|[from] ability: Frisk",
        )
        self.assertEqual(VALIDATION_RULES["item"]["active_target"], "canonical-singles-active")
        self.assertIn("Leftovers", VALIDATION_RULES["item"]["payloads"])
        for version in ("v1", "v2"):
            for perspective in ("p1", "p2"):
                for where in ("input", "successor"):
                    for record in valid:
                        with self.subTest(version=version, perspective=perspective, where=where, record=record):
                            candidate = _rehashed_protocol_candidate(_bundle(perspective=perspective, version=version), where, record)
                            # Grammar controls must represent every established item fact.
                            for which in ("input", "successor"):
                                observation = candidate[which + "_observation"]
                                for target, item in project_public_items(observation["protocol_prefix"]).items():
                                    team = "self_team" if target[:2] == perspective else "opponent_team"
                                    row = {"ident": target}
                                    if team == "self_team": row.update(item=item, item_suppressed=False, **project_public_item_dispositions(observation["protocol_prefix"])[target])
                                    elif item is not None: row["item"] = "has-item"
                                    if version == "v2" and team == "opponent_team": row["public_boosts"] = public_boost_evidence(observation["protocol_prefix"]).get(target, dict.fromkeys(("atk", "def", "spa", "spd", "spe", "accuracy", "evasion"), None))
                                    observation["view"].setdefault(team, []).append(row)
                            _seal_bundle(candidate)
                            before = copy.deepcopy(candidate)
                            validate_protocol_record(record)
                            self.assertEqual(validate_pipeline_bundle(candidate)["perspective"], perspective)
                            stdout, stderr = io.StringIO(), io.StringIO()
                            with patch("sys.stdin", io.StringIO(json.dumps(candidate))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                                self.assertEqual(main(), 0, stderr.getvalue())
                            self.assertTrue(stdout.getvalue())
                            self.assertEqual(candidate, before)
                    for record in rejected:
                        with self.subTest(version=version, perspective=perspective, where=where, record=record):
                            candidate = _rehashed_protocol_candidate(_bundle(perspective=perspective, version=version), where, record)
                            before = copy.deepcopy(candidate)
                            with self.assertRaises(ProtocolRecordError):
                                validate_protocol_record(record)
                            with self.assertRaises(PipelineRecordError):
                                validate_pipeline_bundle(candidate)
                            stdout, stderr = io.StringIO(), io.StringIO()
                            with patch("sys.stdin", io.StringIO(json.dumps(candidate))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                                self.assertEqual(main(), 2, stderr.getvalue())
                            self.assertEqual(stdout.getvalue(), "")
                            self.assertEqual(candidate, before)

    def test_ce04f2_status_records_rehash_and_publish_only_pinned_source_forms(self):
        valid = (
            "|-status|p1a: Target|psn|[from] ability: Poison Touch|[of] p2a: Source",
            "|-status|p1a: Target|slp|[from] move: Sleep Powder",
            "|-status|p1a: Target|slp|[from] move: Hypnosis",
            "|-status|p1a: Target|slp|[from] move: Spore",
            "|-curestatus|p1a: Target|frz|[from] move: Flare Blitz",
            "|-curestatus|p1a: Target|frz|[from] move: Fusion Flare",
            "|-curestatus|p1a: Target|frz|[from] move: Hydro Steam",
            "|-curestatus|p1a: Target|frz|[from] move: Matcha Gotcha",
            "|-curestatus|p1a: Target|frz|[from] move: Pyro Ball",
            "|-curestatus|p1a: Target|frz|[from] move: Sacred Fire",
            "|-curestatus|p1a: Target|frz|[from] move: Scald",
            "|-curestatus|p1a: Target|frz|[from] move: Scorching Sands",
            "|-curestatus|p1a: Target|frz|[from] move: Steam Eruption",
        )
        rejected = (
            "|status|p1a: Target|brn",
            "|curestatus|p2a: Target|frz",
            "|-status|p1a: Target|slp|[from] move: Yawn",
            "|-status|p1a: Target|psn|[from] ability: Poison Touch|[of] p1a: Source",
            "|-curestatus|p1a: Target|frz|[from] move: Flamethrower",
        )
        for version in ("v1", "v2"):
            for perspective in ("p1", "p2"):
                for where in ("input", "successor"):
                    for record in valid:
                        with self.subTest(version=version, perspective=perspective, where=where, record=record):
                            candidate = _rehashed_protocol_candidate(_bundle(perspective=perspective, version=version), where, record)
                            before = copy.deepcopy(candidate)
                            validate_protocol_record(record)
                            self.assertEqual(validate_pipeline_bundle(candidate)["perspective"], perspective)
                            stdout, stderr = io.StringIO(), io.StringIO()
                            with patch("sys.stdin", io.StringIO(json.dumps(candidate))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                                self.assertEqual(main(), 0, stderr.getvalue())
                            self.assertTrue(stdout.getvalue())
                            self.assertEqual(candidate, before)
                    for record in rejected:
                        with self.subTest(version=version, perspective=perspective, where=where, record=record):
                            candidate = _rehashed_protocol_candidate(_bundle(perspective=perspective, version=version), where, record)
                            before = copy.deepcopy(candidate)
                            with self.assertRaises(ProtocolRecordError):
                                validate_protocol_record(record)
                            with self.assertRaises(PipelineRecordError):
                                validate_pipeline_bundle(candidate)
                            stdout, stderr = io.StringIO(), io.StringIO()
                            with patch("sys.stdin", io.StringIO(json.dumps(candidate))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                                self.assertEqual(main(), 2, stderr.getvalue())
                            self.assertEqual(stdout.getvalue(), "")
                            self.assertEqual(candidate, before)

    def test_ce04_slots_healing_wish_public_heal_evidence_accepts_only_pinned_full_restore_form(self):
        exact = "|-heal|p1a: Recipient|100/100|[from] move: Healing Wish"
        rejected = (
            "|-heal|p1a: Recipient|100/100|[from] move: Healing Wisp",
            "|-heal|p1a: Recipient|100/100|[from] move: Healing Wishful",
            "|-heal|p1: Recipient|100/100|[from] move: Healing Wish",
            "|-heal|p1a: Recipient|99/100|[from] move: Healing Wish",
            "|-heal|p1a: Recipient|1/1|[from] move: Healing Wish",
            "|-heal|p1a: Recipient|100/100 brn|[from] move: Healing Wish",
            "|-heal|p1a: Recipient|100/100|[from] move: Healing Wish|[silent]",
            "|-heal|p1a: Recipient|100/100|[silent]|[from] move: Healing Wish",
            "|-heal|p1a: Recipient|100/100|[from] move: Healing Wish|[from] move: Healing Wish",
            "|-heal|p1a: Recipient|100/100|[from] move: Healing Wish|[wisher] Wisher",
        )
        self.assertEqual(VALIDATION_RULES["healing_wish_heal"], {
            "required_from": "[from] move: Healing Wish",
            "required_tag_order": ["[from]"], "target_role": "active", "health": "100/100",
        })
        validate_protocol_record(exact)
        validate_protocol_record("|-heal|p1a: Recipient|50/100|[from] move: Recover")
        for version in ("v1", "v2"):
            for perspective in ("p1", "p2"):
                for where in ("input", "successor"):
                    with self.subTest(version=version, perspective=perspective, where=where, record=exact):
                        candidate = _rehashed_protocol_candidate(_bundle(perspective=perspective, version=version), where, exact)
                        before = copy.deepcopy(candidate)
                        published = validate_pipeline_bundle(candidate)
                        self.assertEqual(published["perspective"], perspective)
                        stdout, stderr = io.StringIO(), io.StringIO()
                        with patch("sys.stdin", io.StringIO(json.dumps(candidate))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                            self.assertEqual(main(), 0, stderr.getvalue())
                        self.assertTrue(stdout.getvalue())
                        self.assertEqual(candidate, before)
                    for record in rejected:
                        with self.subTest(version=version, perspective=perspective, where=where, record=record):
                            candidate = _rehashed_protocol_candidate(_bundle(perspective=perspective, version=version), where, record)
                            before = copy.deepcopy(candidate)
                            with self.assertRaises(ProtocolRecordError):
                                validate_protocol_record(record)
                            with self.assertRaises(PipelineRecordError):
                                validate_pipeline_bundle(candidate)
                            stdout, stderr = io.StringIO(), io.StringIO()
                            with patch("sys.stdin", io.StringIO(json.dumps(candidate))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                                self.assertEqual(main(), 2, stderr.getvalue())
                            self.assertEqual(stdout.getvalue(), "")
                            self.assertEqual(candidate, before)

    def test_ce04_slots_future_sight_public_boundaries_publish_only_the_pinned_forms(self):
        records = (
            "|-start|p1a: Seer|move: Future Sight",
            "|-end|p2a: Target|move: Future Sight",
            "|-damage|p2a: Target|50/100",
        )
        malformed = (
            "|-start|p1: Seer|move: Future Sight",
            "|-start|p1a: Seer|move: Future Sight|[silent]",
            "|-start|p1a: Seer|move: Future Sigh",
            "|-end|p2: Target|move: Future Sight",
            "|-end|p2a: Target|move: Future Sight|[from] move: Future Sight",
            "|-end|p2a: Target|move: Future Sightful",
            "|-start|p1a: Seer|move:  Future Sight",
            "|-start|p1a: Seer|move : Future Sight",
            "|-end|p2a: Target| move: Future Sight",
        )
        self.assertEqual(VALIDATION_RULES["future_sight"], {
            "effect": "move: Future Sight", "activation_command": "-start", "resolution_command": "-end",
            "target_role": "active", "payload_fields": 1,
        })
        for record in records:
            validate_protocol_record(record)
        # Future Sight's damage emitter supplies no provenance tag. Keep the
        # established ordinary damage grammar rather than making a generic
        # delayed-effect family from this bounded source proof.
        validate_protocol_record("|-damage|p2a: Target|50/100|[from] move: Tackle")
        for version in ("v1", "v2"):
            for perspective in ("p1", "p2"):
                for where in ("input", "successor"):
                    for record in records:
                        with self.subTest(version=version, perspective=perspective, where=where, record=record):
                            candidate = _rehashed_protocol_candidate(
                                _bundle(perspective=perspective, version=version), where, record,
                            )
                            before = copy.deepcopy(candidate)
                            published = validate_pipeline_bundle(candidate)
                            self.assertEqual(published["perspective"], perspective)
                            stdout, stderr = io.StringIO(), io.StringIO()
                            with patch("sys.stdin", io.StringIO(json.dumps(candidate))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                                self.assertEqual(main(), 0, stderr.getvalue())
                            self.assertTrue(stdout.getvalue())
                            self.assertEqual(candidate, before)
                    for record in malformed:
                        with self.subTest(version=version, perspective=perspective, where=where, record=record):
                            candidate = _rehashed_protocol_candidate(
                                _bundle(perspective=perspective, version=version), where, record,
                            )
                            before = copy.deepcopy(candidate)
                            with self.assertRaises(ProtocolRecordError):
                                validate_protocol_record(record)
                            with self.assertRaises(PipelineRecordError):
                                validate_pipeline_bundle(candidate)
                            stdout, stderr = io.StringIO(), io.StringIO()
                            with patch("sys.stdin", io.StringIO(json.dumps(candidate))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                                self.assertEqual(main(), 2, stderr.getvalue())
                            self.assertEqual(stdout.getvalue(), "")
                            self.assertEqual(candidate, before)

    def test_ce04_callback_a_ability_templates_publish_only_generated_singles_forms(self):
        valid = (
            "|-ability|p1a: Rayquaza|Air Lock",
            "|-ability|p2a: Arcanine|Intimidate|boost",
            "|-ability|p1a: Calyrex|Chilling Neigh|boost",
            "|-ability|p2a: Calyrex|Grim Neigh|boost",
            "|-ability|p1a: Gardevoir|Static|[from] ability: Trace|[of] p2a: Pikachu",
            "|ability|p2a: Rayquaza|Air Lock",
        )
        rejected = (
            "|-ability|p1a: Pikachu|Static|[from] ability: Receiver|[of] p1a: Eevee",
            "|-ability|p1a: Pikachu|Static|[from] ability: Power of Alchemy|[of] p1a: Eevee",
            "|-ability|p1a: Pikachu|Insomnia|[from] move: Worry Seed",
            "|-endability|p1a: Pikachu|Static|[from] move: Worry Seed",
            "|-endability|p1a: Pikachu",
            "|-ability|p1a: Torkoal|Drought|[from] sunnyday|[fail]",
            "|ability|p1a: Pikachu|Static|[from] ability: Trace|[of] p2a: Eevee",
            "|ability|p1a: Pikachu|Static|boost",
            "|-ability|p1a: Pikachu|Static|[from] ability: Trace",
            "|-ability|p1a: Gardevoir|Static|[from] ability: Trace|[of] p1a: Eevee",
            "|-ability|p1a: Gardevoir|Definitely Not An Ability",
            "|ability|p1a: Gardevoir|Definitely Not An Ability",
            "|-ability|p1a: Pikachu|Static",
            "|ability|p1a: Pikachu|Static",
            "|-ability|p1a: Pikachu|Air Lock|boost",
            "|-ability|p1a: Calyrex|As One (Glastrier)|boost",
            "|-ability|p2a: Calyrex|As One (Spectrier)|boost",
        )
        self.assertEqual(VALIDATION_RULES["ability"]["trace_source_role"], "opposing-active")
        self.assertIn("Air Lock", VALIDATION_RULES["ability"]["payload_domains"]["dash_reveal"])
        for version in ("v1", "v2"):
            for perspective in ("p1", "p2"):
                for where in ("input", "successor"):
                    for record in valid:
                        with self.subTest(version=version, perspective=perspective, where=where, record=record):
                            candidate = _rehashed_protocol_candidate(_bundle(perspective=perspective, version=version), where, record)
                            before = copy.deepcopy(candidate)
                            validate_protocol_record(record)
                            published = validate_pipeline_bundle(candidate)
                            self.assertEqual(published["perspective"], perspective)
                            stdout, stderr = io.StringIO(), io.StringIO()
                            with patch("sys.stdin", io.StringIO(json.dumps(candidate))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                                self.assertEqual(main(), 0, stderr.getvalue())
                            self.assertTrue(stdout.getvalue())
                            self.assertEqual(candidate, before)
                    for record in rejected:
                        with self.subTest(version=version, perspective=perspective, where=where, record=record):
                            candidate = _rehashed_protocol_candidate(_bundle(perspective=perspective, version=version), where, record)
                            before = copy.deepcopy(candidate)
                            with self.assertRaises(ProtocolRecordError):
                                validate_protocol_record(record)
                            with self.assertRaises(PipelineRecordError):
                                validate_pipeline_bundle(candidate)
                            stdout, stderr = io.StringIO(), io.StringIO()
                            with patch("sys.stdin", io.StringIO(json.dumps(candidate))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                                self.assertEqual(main(), 2, stderr.getvalue())
                            self.assertEqual(stdout.getvalue(), "")
                            self.assertEqual(candidate, before)

    def test_ce02_repeated_singleton_tags_reject_before_python_publication(self):
        for version in ("v1", "v2"):
            for perspective in ("p1", "p2"):
                for where in ("input", "successor"):
                    for family, kind, record in _REPEATED_SINGLETON_TAG_FIXTURES:
                        with self.subTest(version=version, perspective=perspective, where=where, family=family, kind=kind):
                            self.assertIn(kind, VALIDATION_RULES["event_tag_cardinality"][family])
                            candidate = _rehashed_protocol_candidate(_bundle(perspective=perspective, version=version), where, record)
                            before = copy.deepcopy(candidate)
                            verify_bundle_identities(candidate)
                            with self.assertRaisesRegex(ProtocolRecordError, "duplicate singleton tag kind"):
                                validate_protocol_record(record)
                            with self.assertRaisesRegex(PipelineRecordError, "duplicate singleton tag kind"):
                                validate_pipeline_bundle(candidate)
                            self.assertEqual(candidate, before)
                            stdout, stderr = io.StringIO(), io.StringIO()
                            with patch("sys.stdin", io.StringIO(json.dumps(candidate))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                                result = main()
                            self.assertEqual(result, 2, stderr.getvalue())
                            self.assertEqual(stdout.getvalue(), "")
                            self.assertEqual(candidate, before)

    def test_shared_protocol_contract_fixtures_cover_every_supported_command(self):
        self.assertEqual({fixture["token"] for fixture in RECORD_FIXTURES}, SUPPORTED_COMMANDS)
        self.assertEqual(len(RECORD_FIXTURES), len(SUPPORTED_COMMANDS))
        validate_protocol_record("|")
        for fixture in RECORD_FIXTURES:
            with self.subTest(token=fixture["token"]):
                self.assertEqual(fixture["record"].split("|")[1], fixture["token"])
                validate_protocol_record(fixture["record"])
        for control in VALID_RECORD_CONTROLS:
            with self.subTest(control=control["record"]):
                self.assertEqual(control["record"].split("|")[1], control["token"])
                validate_protocol_record(control["record"])
        typed_bare_stage_tokens = {"boost", "unboost", "setboost", "clearboost", "clearallboost", "transform"}
        classifications = {fixture["token"]: fixture["inventory_classification"] for fixture in RECORD_FIXTURES}
        self.assertEqual({token for token in typed_bare_stage_tokens if classifications[token] == "represented"}, typed_bare_stage_tokens)
        for fixture in REJECTION_FIXTURES:
            with self.subTest(record=fixture["record"]):
                with self.assertRaises(ProtocolRecordError) as caught:
                    validate_protocol_record(fixture["record"])
                self.assertEqual(caught.exception.kind, fixture["kind"])

    def test_hitcount_source_grammar_rehashes_across_versions_perspectives_and_prefixes(self):
        valid = (
            "|-hitcount|p1a: Maushold|1",
            "|-hitcount|p2a: Maushold|10",
            "|-hitcount|p1: Target|1",
            "|-hitcount|p2: Houndstone|10",
        )
        malformed = (
            "|-hitcount|p1b: Example|2",
            "|-hitcount|p2b: Example|2",
            "|-hitcount|p1: Example|0",
            "|-hitcount|p1: Example|11",
            "|-hitcount|p3a: Example|2",
            "|-hitcount|p1a:Example|2",
            "|-hitcount|p1a: Example |2",
            "|-hitcount|p1a: Example|02",
            "|-hitcount|p1a: Example|2|[silent]",
        )
        self.assertEqual(VALIDATION_RULES["hitcount"], {
            "target_roles": ["active", "side-only"],
            "count_values": list(range(1, 11)),
        })
        for record in valid:
            validate_protocol_record(record)
        for record in malformed:
            with self.subTest(record=record), self.assertRaises(ProtocolRecordError):
                validate_protocol_record(record)

        for version in ("v1", "v2"):
            for perspective in ("p1", "p2"):
                for where in ("input", "successor"):
                    original = _bundle(perspective=perspective, version=version)
                    for record in valid:
                        candidate = _rehashed_protocol_candidate(original, where, record)
                        verify_bundle_identities(candidate)
                        with self.subTest(version=version, perspective=perspective, where=where, record=record):
                            validate_pipeline_bundle(candidate)
                            stdout, stderr = io.StringIO(), io.StringIO()
                            with patch("sys.stdin", io.StringIO(json.dumps(candidate))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                                self.assertEqual(main(), 0, stderr.getvalue())
                            self.assertNotEqual(stdout.getvalue(), "")
                    for record in malformed:
                        candidate = _rehashed_protocol_candidate(original, where, record)
                        verify_bundle_identities(candidate)
                        before = copy.deepcopy(candidate)
                        with self.subTest(version=version, perspective=perspective, where=where, record=record):
                            with self.assertRaises(PipelineRecordError):
                                validate_pipeline_bundle(candidate)
                            self.assertEqual(candidate, before)
                            stdout, stderr = io.StringIO(), io.StringIO()
                            with patch("sys.stdin", io.StringIO(json.dumps(candidate))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                                self.assertEqual(main(), 2, stderr.getvalue())
                            self.assertEqual(stdout.getvalue(), "")
                            self.assertEqual(candidate, before)

    def test_ce02_private_diagnostics_cannot_be_rehashed_into_publication(self):
        for version in ("v1", "v2"):
            for perspective in ("p1", "p2"):
                for where in ("input", "successor"):
                    with self.subTest(version=version, perspective=perspective, where=where):
                        candidate = _rehashed_protocol_candidate(
                            _bundle(perspective=perspective, version=version), where, "|error|[Invalid choice]"
                        )
                        with self.assertRaisesRegex(PipelineRecordError, "private error evidence"):
                            validate_pipeline_bundle(candidate)

    def test_ce02d_only_source_shaped_auto_tie_bigerror_publishes_after_rehash(self):
        warning = "|bigerror|You will auto-tie if the battle doesn't end in 10 turns (on turn 1000)."
        rejected = (
            ("EV warning", "|bigerror|Warning: One player isn't adhering to a 510 EV limit, and the other player is."),
            ("wrong turn", "|bigerror|You will auto-tie if the battle doesn't end in 10 turns (on turn 1001)."),
            ("field count", warning + "|unexpected"),
            ("whitespace", warning.replace("10 turns", " 10 turns")),
            ("tag suffix", warning + "|[from] move: Tackle"),
        )
        for version in ("v1", "v2"):
            for perspective in ("p1", "p2"):
                for where in ("input", "successor"):
                    control = _rehashed_protocol_candidate(_bundle(perspective=perspective, version=version), where, warning)
                    verify_bundle_identities(control)
                    published = validate_pipeline_bundle(control)
                    stdout, stderr = io.StringIO(), io.StringIO()
                    with patch("sys.stdin", io.StringIO(json.dumps(control))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                        self.assertEqual(main(), 0, stderr.getvalue())
                    row = json.loads(stdout.getvalue())
                    self.assertEqual(row, published)
                    self.assertEqual(row["schema_version"], "dataset-record/v1")
                    self.assertIn("observation_prefix_hash", row)
                    self.assertNotIn("protocol_prefix", row)
                    self.assertNotIn("request", row)
                    self.assertNotIn("simulator_snapshot", row)
                    self.assertNotIn("seed", row)
                    self.assertNotIn("team", row)
                    self.assertNotIn("hidden_set", row)
                    self.assertNotIn("bigerror", json.dumps(row))

                    for kind, record in rejected:
                        candidate = _rehashed_protocol_candidate(
                            _bundle(perspective=perspective, version=version), where, record
                        )
                        verify_bundle_identities(candidate)
                        prefix = candidate[where + "_observation"]["protocol_prefix"]
                        self.assertGreater(prefix.index(record), 0, kind)
                        before = copy.deepcopy(candidate)
                        with self.subTest(version=version, perspective=perspective, where=where, kind=kind):
                            with self.assertRaises(PipelineRecordError):
                                validate_pipeline_bundle(candidate)
                            self.assertEqual(candidate, before)
                            stdout, stderr = io.StringIO(), io.StringIO()
                            with patch("sys.stdin", io.StringIO(json.dumps(candidate))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                                self.assertEqual(main(), 2, stderr.getvalue())
                            self.assertEqual(stdout.getvalue(), "")
                            self.assertEqual(candidate, before)

    def test_rehashed_protocol_rejections_cover_versions_perspectives_and_prefixes(self):
        original_controls = {}
        cases = 0
        original_review_rejections = 0
        review_records = {"|turn|١", '|request|{"rqid":null}'}
        for version in ("v1", "v2"):
            for perspective in ("p1", "p2"):
                original = _bundle(perspective=perspective, version=version)
                original_controls[(version, perspective)] = validate_pipeline_bundle(original)
                for where in ("input", "successor"):
                    for fixture in REJECTION_FIXTURES:
                        candidate = _rehashed_protocol_candidate(original, where, fixture["record"])
                        verify_bundle_identities(candidate)
                        with self.subTest(version=version, perspective=perspective, where=where, kind=fixture["kind"]):
                            stdout = io.StringIO()
                            stderr = io.StringIO()
                            with patch("sys.stdin", io.StringIO(json.dumps(candidate))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                                result = main()
                            self.assertEqual(result, 2, stderr.getvalue())
                            self.assertEqual(stdout.getvalue(), "")
                        cases += 1
                        original_review_rejections += fixture["record"] in review_records
                self.assertEqual(validate_pipeline_bundle(original), original_controls[(version, perspective)])
        self.assertEqual(cases, len(REJECTION_FIXTURES) * 8)
        self.assertEqual(original_review_rejections, 16)

    def test_rehashed_empty_protocol_segments_reject_before_publication(self):
        for version in ("v1", "v2"):
            for perspective in ("p1", "p2"):
                original = _bundle(perspective=perspective, version=version)
                control = validate_pipeline_bundle(original)
                for where in ("input", "successor"):
                    candidate = _rehashed_protocol_candidate(original, where, "")
                    verify_bundle_identities(candidate)
                    with self.subTest(version=version, perspective=perspective, where=where):
                        with self.assertRaisesRegex(PipelineRecordError, "protocol prefix is malformed"):
                            validate_pipeline_bundle(candidate)
                        stdout, stderr = io.StringIO(), io.StringIO()
                        with patch("sys.stdin", io.StringIO(json.dumps(candidate))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                            result = main()
                        self.assertEqual(result, 2, stderr.getvalue())
                        self.assertEqual(stdout.getvalue(), "")
                self.assertEqual(validate_pipeline_bundle(original), control)

    def test_rehashed_sanitized_request_records_are_canonical_and_join_rqid(self):
        for version in ("v1", "v2"):
            for perspective in ("p1", "p2"):
                original = _bundle(perspective=perspective, version=version)
                for where, record, successor_rqid in (
                    ("input", '|request|{}', None),
                    ("input", '|request|{"rqid":12}', 12),
                    ("successor", '|request|{}', None),
                    ("successor", '|request|{"rqid":13}', None),
                ):
                    candidate = _rehashed_protocol_candidate(original, where, record)
                    if successor_rqid is not None:
                        candidate["successor_observation"]["request"]["rqid"] = successor_rqid
                        _seal_bundle(candidate)
                    verify_bundle_identities(candidate)
                    with self.subTest(version=version, perspective=perspective, where=where, record=record):
                        stdout, stderr = io.StringIO(), io.StringIO()
                        with patch("sys.stdin", io.StringIO(json.dumps(candidate))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                            result = main()
                        self.assertEqual(result, 0, stderr.getvalue())
                        published = json.loads(stdout.getvalue())
                        self.assertEqual(published["observation_id"], candidate["input_observation"]["observation_id"])
                        self.assertNotIn("request|", stdout.getvalue())

                invalid = (
                    ("input", '|request|{ "rqid": 12 }', "noncanonical request"),
                    ("input", '|request|{"rqid":12,"rqid":12}', "noncanonical request"),
                    ("input", '|request|{"private":true,"rqid":12}', "private request"),
                    ("input", '|request|{"rqid":12,"private":true}', "private request"),
                    ("input", '|request|{"rqid":13}', "rqid disagrees"),
                    ("successor", '|request|{"rqid":13 }', "noncanonical request"),
                    ("successor", '|request|{"rqid":12}', "rqid disagrees"),
                    ("successor", '|request|{"rqid":null}', "Malformed raw request"),
                )
                for where, record, reason in invalid:
                    candidate = _rehashed_protocol_candidate(original, where, record)
                    verify_bundle_identities(candidate)
                    with self.subTest(version=version, perspective=perspective, where=where, record=record):
                        stdout, stderr = io.StringIO(), io.StringIO()
                        with patch("sys.stdin", io.StringIO(json.dumps(candidate))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                            result = main()
                        self.assertEqual(result, 2, stderr.getvalue())
                        self.assertEqual(stdout.getvalue(), "")
                        self.assertIn(reason.lower(), stderr.getvalue().lower())

    def test_rehashed_observation_requests_are_object_or_null(self):
        scalar_requests = ("invalid", [], 12, False)
        for version in ("v1", "v2"):
            for perspective in ("p1", "p2"):
                original = _bundle(perspective=perspective, version=version)
                for where in ("input", "successor"):
                    # A null request is valid for requestless observations. The
                    # input still cannot publish an action without a request.
                    null_candidate = _rehashed_protocol_candidate(original, where, "|turn|2")
                    null_observation = null_candidate[where + "_observation"]
                    null_observation["request"] = None
                    _seal_bundle(null_candidate)
                    verify_bundle_identities(null_candidate)
                    with self.subTest(version=version, perspective=perspective, where=where, request=None):
                        self.assertEqual(list(_prefix(null_observation, where)), null_observation["protocol_prefix"])
                        stdout, stderr = io.StringIO(), io.StringIO()
                        with patch("sys.stdin", io.StringIO(json.dumps(null_candidate))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                            result = main()
                        if where == "successor":
                            self.assertEqual(result, 0, stderr.getvalue())
                            self.assertNotEqual(stdout.getvalue(), "")
                        else:
                            self.assertEqual(result, 2, stderr.getvalue())
                            self.assertEqual(stdout.getvalue(), "")

                    for request_value in scalar_requests:
                        candidate = _rehashed_protocol_candidate(original, where, "|turn|2")
                        candidate[where + "_observation"]["request"] = request_value
                        _seal_bundle(candidate)
                        verify_bundle_identities(candidate)
                        before = copy.deepcopy(candidate)
                        with self.subTest(version=version, perspective=perspective, where=where, request=request_value):
                            with self.assertRaisesRegex(PipelineRecordError, "request must be an object or null"):
                                _prefix(candidate[where + "_observation"], where)
                            stdout, stderr = io.StringIO(), io.StringIO()
                            with patch("sys.stdin", io.StringIO(json.dumps(candidate))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                                result = main()
                            self.assertEqual(result, 2, stderr.getvalue())
                            self.assertEqual(stdout.getvalue(), "")
                            self.assertEqual(candidate, before)

                # A retained rqid has to join to a request object with that rqid.
                candidate = _rehashed_protocol_candidate(original, "successor", '|request|{"rqid":12}')
                candidate["successor_observation"]["request"] = None
                _seal_bundle(candidate)
                verify_bundle_identities(candidate)
                stdout, stderr = io.StringIO(), io.StringIO()
                with patch("sys.stdin", io.StringIO(json.dumps(candidate))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                    result = main()
                self.assertEqual(result, 2, stderr.getvalue())
                self.assertEqual(stdout.getvalue(), "")
                self.assertIn("no associated request object", stderr.getvalue())

    def test_fully_rehashed_private_slot_maps_reject_before_publication(self):
        for perspective in ("p1", "p2"):
            for where in ("input", "successor"):
                for key in ("slotConditions", "slot_conditions", "slot_condition_state", "pending_slots"):
                    candidate = _bundle(perspective=perspective, version="v2")
                    observation = candidate[where + "_observation"]
                    observation["view"][key] = {"wish": {"endingTurn": 3}}
                    _seal_bundle(candidate)
                    verify_bundle_identities(candidate)
                    stdout, stderr = io.StringIO(), io.StringIO()
                    with self.subTest(perspective=perspective, where=where, key=key), \
                            patch("sys.stdin", io.StringIO(json.dumps(candidate))), \
                            patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                        result = main()
                    self.assertEqual(result, 2, stderr.getvalue())
                    self.assertEqual(stdout.getvalue(), "")
                    self.assertIn("private simulator slot state is not publishable", stderr.getvalue().lower())

    def test_player_ident_rejections_cover_singleturn_event_tags_and_side_targets(self):
        rejected = {fixture["record"] for fixture in REJECTION_FIXTURES}
        for record in (
            "|-singleturn|p1a: Pikachu|Helping Hand|[of] p2a:Eevee",
            "|-singleturn|p1a: Pikachu|Helping Hand|[of] p1: Eevee",
            "|-singleturn|p1a: Pikachu|Helping Hand|[of] p2: Eevee",
            "|-singleturn|p1a: Pikachu|Helping Hand|[of] p: Eevee",
            "|-singleturn|p1a: Pikachu|Helping Hand|[of]",
            "|-singleturn|p1a: Pikachu|Helping Hand|[of] Eevee",
            "|-damage|p1a: Pikachu|50/100|[of] p2:Eevee",
            "|-heal|p1a: Pikachu|50/100|[of] p2a:Eevee",
            "|move|p1a: Pikachu|Tackle|p2:Eevee",
            "|faint|p1a: Pikachu ",
            "|-clearboost|p1a: Pikachu ",
            "|-endability|p1a: Pikachu ",
            "|-transform|p1a: Ditto|p2a:Eevee",
            "|-transform|p1a: Ditto|p2a: Eevee ",
            "|-transform|p1a: Ditto|p2a:  Eevee",
            "|-transform|p1a: Ditto|p2a:\tEevee",
            "|-transform|p1a: Ditto|p2a:\u00a0Eevee",
            "|-transform|p1a: Ditto|p2a:\u2009Eevee",
            "|-transform|p1a: Ditto|p2: Eevee",
        ):
            self.assertIn(record, rejected)
        for record in (
            "|move|p1a: Pikachu|Tackle|p2: Eevee",
            "|move|p1a: Mr: Mime|Tackle|p2a: Farfetch'd",
        ):
            validate_protocol_record(record)

    def test_rehashed_singleturn_and_singlemove_source_controls_publish_across_versions_and_prefixes(self):
        controls = [control for control in VALID_RECORD_CONTROLS if control["token"] == "-singleturn"]
        player_ident_controls = [
            control for control in VALID_RECORD_CONTROLS
            if control["reconstruction_scope"].startswith("raw-only player-ident grammar control")
            or control["token"] == "-transform"
        ]
        rules = VALIDATION_RULES["singleturn"]
        parts = [control["record"].split("|") for control in controls]
        self.assertEqual(
            sorted(row[3] for row in parts if len(row) == 4),
            sorted(rules["untagged_effects"]),
        )
        tagged_forms = []
        for row in parts:
            if len(row) != 5:
                continue
            no_payload_tag = row[4] == "[zeffect]"
            tagged_form = {
                "effect": row[3],
                "tag": row[4] if no_payload_tag else "[of]",
                "tag_value": "none" if no_payload_tag else "player-ident",
                **({} if no_payload_tag else {"ident_role": "active"}),
            }
            if tagged_form not in tagged_forms:
                tagged_forms.append(tagged_form)
        self.assertEqual(tagged_forms, rules["tagged_forms"])
        self.assertEqual(
            len([row for row in parts if len(row) == 4]),
            len(rules["untagged_effects"]),
        )
        self.assertEqual(
            sorted(row[4][len("[of] "):] for row in parts
                   if len(row) == 5 and row[3] == "Helping Hand"),
            ["p1a: Pikachu", "p2a: Eevee"],
        )
        cases = 0
        singlemove_controls = [control for control in VALID_RECORD_CONTROLS if control["token"] == "-singlemove"]
        self.assertEqual([control["record"].split("|")[3:] for control in singlemove_controls], VALIDATION_RULES["singlemove"]["forms"])
        anim_controls = [control for control in VALID_RECORD_CONTROLS if control["token"] == "-anim"]
        self.assertEqual([[control["record"].split("|")[3]] for control in anim_controls], VALIDATION_RULES["anim"]["forms"])
        controls = controls + [
            {**control, "record": control["record"].replace("p1a: Pikachu", target)}
            for control in singlemove_controls for target in ("p1a: Pikachu", "p2a: Eevee")
        ]
        controls = controls + [
            {**control, "record": control["record"].replace("p1a: Pikachu", "p2a: Pikachu").replace("p2a: Eevee", "p1a: Eevee")}
            for control in anim_controls
        ]
        for version in ("v1", "v2"):
            for perspective in ("p1", "p2"):
                original = _bundle(perspective=perspective, version=version)
                for where in ("input", "successor"):
                    for control in (*controls, *player_ident_controls):
                        candidate = _rehashed_protocol_candidate(original, where, control["record"])
                        verify_bundle_identities(candidate)
                        validate_pipeline_bundle(candidate)
                        stdout = io.StringIO()
                        stderr = io.StringIO()
                        with patch("sys.stdin", io.StringIO(json.dumps(candidate))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                            result = main()
                        with self.subTest(version=version, perspective=perspective, where=where, record=control["record"]):
                            self.assertEqual(result, 0, stderr.getvalue())
                            self.assertTrue(stdout.getvalue())
                        cases += 1
        self.assertEqual(cases, (len(controls) + len(player_ident_controls)) * 8)

    def test_viewless_v1_replays_prefix_before_historical_compatibility(self):
        def strip_typed_view(bundle):
            for which in ("input", "successor"):
                view = bundle[which + "_observation"]["view"]
                for key in ("self_team", "opponent_team", "field"):
                    view.pop(key, None)
            return _seal_bundle(bundle)

        cases = []
        substitute = _rehashed_protocol_candidate(
            _bundle(version="v1"), "input", "|switch|p1a: Pikachu|Pikachu, L80|100/100"
        )
        substitute = _rehashed_protocol_candidate(substitute, "input", "|-start|p1a: Pikachu|Substitute")
        cases.append(("substitute missing row", strip_typed_view(substitute), True))

        side_condition = _rehashed_protocol_candidate(
            _bundle(version="v1"), "input", "|-sidestart|p1: Pikachu|Spikes"
        )
        cases.append(("side condition unrepresented", strip_typed_view(side_condition), True))

        valid = strip_typed_view(_bundle(version="v1"))
        cases.append(("empty typed projection", valid, False))

        for label, candidate, rejects in cases:
            with self.subTest(label=label):
                verify_bundle_identities(candidate)
                before = copy.deepcopy(candidate)
                stdout, stderr = io.StringIO(), io.StringIO()
                with patch("sys.stdin", io.StringIO(json.dumps(candidate))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                    result = main()
                self.assertEqual(candidate, before)
                if rejects:
                    self.assertEqual(result, 2, stderr.getvalue())
                    self.assertEqual(stdout.getvalue(), "")
                    self.assertIn("Typed lifecycle evidence mismatch", stderr.getvalue())
                else:
                    self.assertEqual(result, 0, stderr.getvalue())
                    self.assertTrue(stdout.getvalue())

    def test_spirit_shackle_trap_evidence_publishes_raw_without_a_public_link(self):
        record = "|-activate|p1a: Warden|trapped"
        for version in ("v1", "v2"):
            for perspective in ("p1", "p2"):
                for where in ("input", "successor"):
                    with self.subTest(version=version, perspective=perspective, where=where, record=record):
                        candidate = _rehashed_protocol_candidate(
                            _bundle(perspective=perspective, version=version), where, record
                        )
                        validate_protocol_record(record)
                        validate_pipeline_bundle(candidate)
                        self.assertNotIn("trapper", json.dumps(candidate))
                        stdout, stderr = io.StringIO(), io.StringIO()
                        with patch("sys.stdin", io.StringIO(json.dumps(candidate))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                            self.assertEqual(main(), 0, stderr.getvalue())
                        self.assertTrue(stdout.getvalue())
        for malformed in (
            "|-activate|p2a: Target|trapped|[of] p1a: Warden",
            "|-activate|p2a: Target|trapped|[from] move: Spirit Shackle",
            "|-activate|p2a: Target|trapped|source",
            "|-activate|p2a: Target |trapped",
            "|-activate|p2a: Target|trapped ",
            "|-activate|p2: Target|trapped",
        ):
            with self.subTest(malformed=malformed):
                with self.assertRaises(ProtocolRecordError):
                    validate_protocol_record(malformed)
                for version in ("v1", "v2"):
                    for perspective in ("p1", "p2"):
                        for where in ("input", "successor"):
                            candidate = _rehashed_protocol_candidate(
                                _bundle(perspective=perspective, version=version), where, malformed
                            )
                            before = json.dumps(candidate, sort_keys=True)
                            with self.assertRaises(PipelineRecordError):
                                validate_pipeline_bundle(candidate)
                            self.assertEqual(json.dumps(candidate, sort_keys=True), before)
                            stdout, stderr = io.StringIO(), io.StringIO()
                            with patch("sys.stdin", io.StringIO(json.dumps(candidate))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                                self.assertEqual(main(), 2, stderr.getvalue())
                            self.assertEqual(stdout.getvalue(), "")
        with self.assertRaises(ProtocolRecordError):
            validate_protocol_record("|-activate|p1: Warden|trapped")

    def test_ce05_repeat_use_hint_is_exact_raw_evidence_across_versions_and_prefixes(self):
        valid = tuple(VALIDATION_RULES["repeat_use_hint"]["messages"])
        malformed = (
            "Some effects can force a Pokemon to use Blood Moon again in a row.|extra",
            "Some effects can force a Pokemon to use Blood Moon again in a row. ",
            "Some effects can force a Pokemon to use bloodmoon again in a row.",
            "Some effects can force a Pokemon to use Thunderbolt again in a row.",
            " Some effects can force a Pokemon to use Gigaton Hammer again in a row.",
        )
        for version in ("v1", "v2"):
            for perspective in ("p1", "p2"):
                for where in ("input", "successor"):
                    for message in valid:
                        record = "|-hint|" + message
                        with self.subTest(valid=True, version=version, perspective=perspective, where=where, record=record):
                            candidate = _rehashed_protocol_candidate(_bundle(perspective=perspective, version=version), where, record)
                            validate_protocol_record(record)
                            validate_pipeline_bundle(candidate)
                            stdout, stderr = io.StringIO(), io.StringIO()
                            with patch("sys.stdin", io.StringIO(json.dumps(candidate))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                                self.assertEqual(main(), 0, stderr.getvalue())
                            self.assertTrue(stdout.getvalue())
                    for message in malformed:
                        record = "|-hint|" + message
                        with self.subTest(valid=False, version=version, perspective=perspective, where=where, record=record):
                            candidate = _rehashed_protocol_candidate(_bundle(perspective=perspective, version=version), where, record)
                            before = json.dumps(candidate, sort_keys=True)
                            with self.assertRaises(ProtocolRecordError):
                                validate_protocol_record(record)
                            with self.assertRaises(PipelineRecordError):
                                validate_pipeline_bundle(candidate)
                            self.assertEqual(json.dumps(candidate, sort_keys=True), before)
                            stdout, stderr = io.StringIO(), io.StringIO()
                            with patch("sys.stdin", io.StringIO(json.dumps(candidate))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                                self.assertEqual(main(), 2, stderr.getvalue())
                            self.assertEqual(stdout.getvalue(), "")

    def test_shared_contract_loader_rejects_inconsistent_and_unsupported_shapes(self):
        from pathlib import Path
        contract_path = Path(__file__).parents[1] / "src/neural/protocol_contract.json"
        base = json.loads(contract_path.read_text(encoding="utf-8"))
        invalid = []
        wrong_type = copy.deepcopy(base); wrong_type["supported_commands"] = "move"; invalid.append(wrong_type)
        unknown_rule = copy.deepcopy(base); unknown_rule["validation_rules"]["integer"]["lexeme"] = "unicode-decimal"; invalid.append(unknown_rule)
        invalid_ident = copy.deepcopy(base); invalid_ident["validation_rules"]["player_ident"]["separator"] = ":"; invalid.append(invalid_ident)
        invalid_hitcount = copy.deepcopy(base); invalid_hitcount["validation_rules"]["hitcount"]["count_values"].pop(); invalid.append(invalid_hitcount)
        mismatched_singleturn = copy.deepcopy(base); mismatched_singleturn["validation_rules"]["singleturn"]["tagged_forms"][0]["tag"] = "[of]"; invalid.append(mismatched_singleturn)
        mismatched_singlemove = copy.deepcopy(base); mismatched_singlemove["validation_rules"]["singlemove"]["forms"][1].pop(); invalid.append(mismatched_singlemove)
        invented_singlemove = copy.deepcopy(base); invented_singlemove["validation_rules"]["singlemove"]["forms"].append(["Future Mechanic"]); invalid.append(invented_singlemove)
        unknown_rule_key = copy.deepcopy(base); unknown_rule_key["validation_rules"]["future"] = {}; invalid.append(unknown_rule_key)
        duplicate = copy.deepcopy(base); duplicate["supported_commands"].append(duplicate["supported_commands"][0]); invalid.append(duplicate)
        mismatched_fixture = copy.deepcopy(base); next(row for row in mismatched_fixture["record_fixtures"] if row["token"] == "ability")["token"] = "-ability"; invalid.append(mismatched_fixture)
        conflict = copy.deepcopy(base); conflict["supported_commands"].append("clearstatus"); invalid.append(conflict)
        for candidate in invalid:
            with self.subTest(candidate=invalid.index(candidate)):
                with self.assertRaises(ProtocolContractError):
                    validate_protocol_contract(candidate)

        with self.assertRaises(ProtocolContractError):
            load_protocol_contract(contract_path.with_name("missing-contract.json"))
        with self.assertRaises(ProtocolContractError):
            load_protocol_contract(contract_path.with_name("protocol_contract.py"))

    def test_rehashed_valid_tier_and_private_request_cannot_be_published(self):
        original = _bundle(version="v2")
        for record, message in (
            ('|tier|[Gen 9] Random Battle', "filtered ruleset metadata"),
            ('|request|{"rqid":7,"secret":"private"}', "private request"),
        ):
            candidate = _rehashed_protocol_candidate(original, "successor", record)
            verify_bundle_identities(candidate)
            with self.subTest(record=record), self.assertRaisesRegex(PipelineRecordError, message):
                validate_pipeline_bundle(candidate)
            stdout, stderr = io.StringIO(), io.StringIO()
            with patch("sys.stdin", io.StringIO(json.dumps(candidate))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                result = main()
            self.assertEqual(result, 2, stderr.getvalue())
            self.assertEqual(stdout.getvalue(), "")

    def test_fully_rehashed_unknown_command_regression(self):
        bundle = _bundle(version="v2")
        candidate = _rehashed_protocol_candidate(bundle, "input", "|futuremechanic|opaque")
        verify_bundle_identities(candidate)
        with self.assertRaisesRegex(PipelineRecordError, "(?i)unsupported raw protocol event: futuremechanic"):
            validate_pipeline_bundle(candidate)

    def test_unknown_effect_values_fail_closed_before_python_publication(self):
        original = _bundle(version="v2")
        for record, family in (
            ("|-start|p1a: Pikachu|futurevolatile", "move_volatile"),
            ("|-fieldstart|futurefield", "field"),
            ("|-sidestart|p1: P1|futuresidecondition", "side_condition"),
        ):
            with self.subTest(record=record):
                with self.assertRaises(ProtocolRecordError) as raised:
                    validate_protocol_record(record)
                self.assertEqual(raised.exception.code, "simulator-coverage/v1/unclassified-effect-value")
                self.assertEqual(raised.exception.family, family)
                self.assertEqual(raised.exception.disposition, "unknown")

                candidate = _rehashed_protocol_candidate(original, "input", record)
                verify_bundle_identities(candidate)
                with self.assertRaisesRegex(PipelineRecordError, "simulator-coverage/v1/unclassified-effect-value"):
                    validate_pipeline_bundle(candidate)
                stdout, stderr = io.StringIO(), io.StringIO()
                with patch("sys.stdin", io.StringIO(json.dumps(candidate))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                    result = main()
                self.assertEqual(result, 2, stderr.getvalue())
                self.assertIn("simulator-coverage/v1/unclassified-effect-value", stderr.getvalue())
                self.assertEqual(stdout.getvalue(), "")

    def test_represented_effect_in_wrong_family_fails_before_python_publication(self):
        original = _bundle(version="v2")
        record = "|-start|p1a: Pikachu|stealthrock"
        with self.assertRaises(ProtocolRecordError) as raised:
            validate_protocol_record(record)
        self.assertEqual(raised.exception.code, "simulator-coverage/v1/unclassified-effect-value")
        self.assertEqual(raised.exception.family, "move_volatile")
        self.assertEqual(raised.exception.disposition, "family-mismatch:side_condition")

        candidate = _rehashed_protocol_candidate(original, "input", record)
        verify_bundle_identities(candidate)
        before = json.dumps(candidate, sort_keys=True)
        with self.assertRaisesRegex(PipelineRecordError, "family-mismatch:side_condition"):
            validate_pipeline_bundle(candidate)
        self.assertEqual(json.dumps(candidate, sort_keys=True), before)
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("sys.stdin", io.StringIO(json.dumps(candidate))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
            result = main()
        self.assertEqual(result, 2, stderr.getvalue())
        self.assertIn("simulator-coverage/v1/unclassified-effect-value", stderr.getvalue())
        self.assertIn("family-mismatch:side_condition", stderr.getvalue())
        self.assertEqual(stdout.getvalue(), "")

    def test_integral_float_cursors_preserve_javascript_number_identities(self):
        bundle = _bundle()
        original = validate_pipeline_bundle(bundle)
        for which in ('input', 'successor'):
            bundle[which + '_observation']['event_cursor'] = float(bundle[which + '_observation']['event_cursor'])
            belief = bundle[which + '_belief']
            for ref in [belief['observation']] + belief['observation_history']:
                ref['event_cursor'] = float(ref['event_cursor'])
        self.assertEqual(validate_pipeline_bundle(bundle), original)


    def test_revival_identity_and_target_validation(self):
        bundle = _revival_bundle()
        record = validate_pipeline_bundle(bundle)
        self.assertEqual(record, validate_pipeline_bundle(bundle))
        self.assertEqual(bundle["action"]["schema_version"], "canonical-revival/v1")
        self.assertEqual(record["schema_fingerprints"]["transition"], "seeded-revival/v1")
        mutations = [
            lambda b: b["input_observation"]["request"].update(side=None),
            lambda b: b["input_observation"]["request"]["side"][1].update(condition=123),
            lambda b: b["input_observation"]["request"]["side"][1].update(condition="100/100"),
            lambda b: b["input_observation"]["request"]["side"][1].update(slot=3),
            lambda b: b["input_observation"]["request"]["side"][0].update(reviving=False),
            lambda b: b["action"].update(schema_version="canonical-action/v1"),
            lambda b: b["transition"].update(waiting_player="p1"),
            lambda b: b.update(schema_version="pipeline-forced-switch-record/v1"),
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                bad = _revival_bundle(); mutate(bad)
                with self.assertRaises(PipelineRecordError):
                    validate_pipeline_bundle(bad)

    def test_forced_switch_bundle_preserves_identity_and_uses_distinct_transition_schema(self):
        bundle = _forced_switch_bundle()
        record = validate_pipeline_bundle(bundle)
        self.assertEqual(record, validate_pipeline_bundle(json.loads(json.dumps(bundle))))
        self.assertEqual(record["schema_fingerprints"]["transition"], "seeded-forced-switch/v1")
        for key in ("perspective", "battle_id"):
            self.assertEqual(record[key], bundle[key])
        self.assertEqual(record["action_id"], bundle["action"]["action_id"])
        self.assertEqual(record["transition_id"], bundle["transition"]["transition_id"])

    def test_forced_switch_rejects_role_schema_request_and_lineage_corruption(self):
        mutations = [
            lambda b: b["transition"].update(acting_player="p2"),
            lambda b: b["transition"].update(waiting_player="p1"),
            lambda b: b["transition"].update(waiting_player="p3"),
            lambda b: b["transition"].update(schema_version="pipeline-transition-reference/v1"),
            lambda b: b.update(schema_version="pipeline-linked-record/v1"),
            lambda b: b.update(schema_version="pipeline-forced-switch-record/v9"),
            lambda b: b["input_observation"]["request"].update(force_switch=False),
            lambda b: b["input_observation"]["request"].update(wait=True),
            lambda b: b["input_observation"]["request"].update(team_preview=True),
            lambda b: b["input_observation"].update(snapshot_phase="pre_decision"),
            lambda b: b["input_observation"]["view"].update(terminated=True),
            lambda b: b["action"].update(kind="default"),
            lambda b: b["transition"].update(action_id="act-" + "0" * 64),
            lambda b: b["successor_belief"]["transition_lineage"].update(branch_id="wrong"),
            lambda b: b["successor_belief"]["simulator_snapshot"].update(state_fingerprint="0" * 64),
            lambda b: b.update(waiting_observation={"perspective": "p2", "request": {"player": "p2"}}),
            lambda b: b["transition"].update(waiting_action_id="act-" + "0" * 64),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                bundle = _forced_switch_bundle()
                mutate(bundle)
                with self.assertRaises(PipelineRecordError):
                    validate_pipeline_bundle(bundle)

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

    def test_unresolved_aliases_are_blocked_before_record_creation(self):
        for alias in ("clearstatus", "-clearstatus", "nothing"):
            bundle = _bundle()
            observation = bundle["input_observation"]
            prefix = observation["protocol_prefix"] + [f"|{alias}|audit"]
            observation["protocol_prefix"] = prefix
            observation["event_cursor"] = len(prefix)
            observation["protocol_prefix_hash"] = _typescript_hash(prefix)

            with self.subTest(alias=alias):
                with self.assertRaises(PipelineRecordError) as caught:
                    validate_pipeline_bundle(bundle)
                self.assertEqual(
                    caught.exception.diagnostic,
                    {
                        "schema_version": "pipeline-diagnostic/v1",
                        "code": "pipeline/v1/unresolved-protocol-alias",
                        "detail": f'input observation protocol prefix has unresolved alias "{alias}" at record 2',
                        "record_index": 2,
                        "record_command": alias,
                    },
                )

    def test_source_emitted_nothing_variant_remains_valid_raw_evidence(self):
        bundle = _bundle()
        input_prefix = bundle["input_observation"]["protocol_prefix"] + ["|-nothing"]
        successor_prefix = input_prefix + bundle["successor_observation"]["protocol_prefix"][2:]
        for observation, prefix in (
            (bundle["input_observation"], input_prefix),
            (bundle["successor_observation"], successor_prefix),
        ):
            observation["protocol_prefix"] = prefix
            observation["event_cursor"] = len(prefix)
            observation["protocol_prefix_hash"] = _typescript_hash(prefix)
        bundle["input_belief"]["source_protocol_prefix"] = input_prefix
        bundle["successor_belief"]["source_protocol_prefix"] = successor_prefix

        record = validate_pipeline_bundle(_seal_bundle(bundle))
        self.assertEqual(record["observation_cursor"], len(input_prefix))
        self.assertEqual(bundle["input_observation"]["protocol_prefix"][-1], "|-nothing")

    def test_cli_returns_structured_unresolved_alias_diagnostic(self):
        bundle = _bundle()
        observation = bundle["successor_observation"]
        prefix = observation["protocol_prefix"] + ["|-clearstatus|legacy-token"]
        observation["protocol_prefix"] = prefix
        observation["event_cursor"] = len(prefix)
        observation["protocol_prefix_hash"] = _typescript_hash(prefix)

        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch("sys.stdin", io.StringIO(json.dumps(bundle))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
            result = main()

        self.assertEqual(result, 2)
        response = json.loads(stderr.getvalue())
        self.assertEqual(response["diagnostic"]["schema_version"], "pipeline-diagnostic/v1")
        self.assertEqual(response["diagnostic"]["code"], "pipeline/v1/unresolved-protocol-alias")
        self.assertEqual(response["diagnostic"]["record_command"], "-clearstatus")
        self.assertEqual(response["diagnostic"]["record_index"], 4)

    def test_unicode_prefix_hashes_keep_typescript_and_data_envelopes_distinct(self):
        bundle = _bundle(unicode_prefix=True)
        record = validate_pipeline_bundle(bundle)
        observable_hash = bundle["input_observation"]["protocol_prefix_hash"]
        self.assertNotEqual(record["observation_prefix_hash"], observable_hash)
        self.assertEqual(record["observation_cursor"], len(bundle["input_observation"]["protocol_prefix"]))

    def test_cli_reads_node_json_as_utf8_independent_of_windows_text_encoding(self):
        bundle = _bundle(unicode_prefix=True)
        encoded = json.dumps(bundle, ensure_ascii=False).encode("utf-8")
        stdin = io.TextIOWrapper(io.BytesIO(encoded), encoding="cp1252")
        stdout = io.StringIO()
        stderr = io.StringIO()

        with patch("sys.stdin", stdin), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
            result = main()

        self.assertEqual(result, 0, stderr.getvalue())
        self.assertEqual(json.loads(stdout.getvalue())["observation_id"], bundle["input_observation"]["observation_id"])

    def test_cli_reports_malformed_bytes_and_json_without_a_traceback(self):
        for encoded in (b'{"prefix":"\xff"}', b"{"):
            with self.subTest(encoded=encoded):
                stdin = io.TextIOWrapper(io.BytesIO(encoded), encoding="cp1252")
                stdout = io.StringIO()
                stderr = io.StringIO()

                with patch("sys.stdin", stdin), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                    result = main()

                self.assertEqual(result, 2)
                self.assertEqual(stdout.getvalue(), "")
                self.assertTrue(stderr.getvalue().startswith("pipeline-record validation failed:"))
                self.assertNotIn("Traceback", stderr.getvalue())

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
