"""Independent PK-02A structure tests; fixture truth is not runtime authority."""

import copy
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import shutil
import unittest

from neural.perspective_knowledge import (
    canonical_knowledge_json, check_knowledge_structure, knowledge_identity,
    parse_knowledge_json, serialize_knowledge_wire,
)


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "docs/contracts/fixtures/perspective-knowledge-v1"
DIAGNOSTIC = {
    "structure_valid": True,
    "source_semantics_verified": False,
    "completeness": "not_established",
    "legacy_envelope_verified": False,
}
SIM_PROFILE = "sha256:b3cbd12ebcd584263135a5803ca07fe62321bda5a8f9c30e0ee2eaa4cf09bb38"
REPLAY_PROFILE = "sha256:40a8a9da38f3e5a7f7b378c3422c13575543947983a983bfa30a183d9f7743c5"


def fixture(name):
    # Read frozen data only. Never execute/import author_fixtures or check_contract.
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def independent_canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def independent_id(row):
    payload = {key: value for key, value in row.items() if key != "id"}
    preimage = ("pk/v1/" + row["kind"] + "\n").encode("ascii") + independent_canonical(payload)
    return "sha256:" + hashlib.sha256(preimage).hexdigest()


# Audited reference positions, stated here independently of runtime/schema helpers.
# External legacy digests and all ordinary string values intentionally stay inert.
REFERENCE_PATHS = {
    "origin": (), "profile": (),
    "source": ("origin",), "prefix": ("origin",),
    "evidence": ("origin", "source", "prefix"),
    "certificate": ("source", "witnesses.*"),
    "fact": ("evidence.*", "certificate"),
    "starting": ("origin", "source", "parent", "facts.*", "crosswalk.*.certificate"),
    "current": ("origin", "prefix", "parent", "facts.*"),
    "request": ("origin", "source", "prefix", "facts.*"),
    "knowledge": ("origin", "starting", "current", "request"),
    "verdict": ("knowledge", "profile"),
    "boundary": ("origin", "parent", "restored_from", "bindings.*.knowledge", "bindings.*.verdict"),
    "binding": ("origin", "input_knowledge", "successor_knowledge"),
    "audit": ("origin", "required_profile", "target_boundary"),
}


def replace_path(value, parts, replacements):
    key, *rest = parts
    if key == "*":
        for index in range(len(value)):
            if rest:
                replace_path(value[index], rest, replacements)
            elif value[index] in replacements:
                value[index] = replacements[value[index]]
    elif rest:
        replace_path(value[key], rest, replacements)
    elif value[key] in replacements:
        value[key] = replacements[value[key]]


def reseal(audit):
    """Propagate changed IDs only through declared edges, never arbitrary text."""
    rows = [row for table in audit["tables"].values() for row in table]
    pending = {}
    for _ in range(64):
        for row in rows + [audit]:
            for path in REFERENCE_PATHS[row["kind"]]:
                replace_path(row, path.split("."), pending)
            for field in ("facts", "evidence", "witnesses"):
                if field in row:
                    row[field].sort()
        changed = {}
        for row in rows:
            new_id = independent_id(row)
            if new_id != row["id"]:
                changed[row["id"]] = new_id
                row["id"] = new_id
        if not changed:
            for table in audit["tables"].values():
                table.sort(key=lambda row: row["id"])
            audit["id"] = independent_id(audit)
            return audit
        pending = changed
    raise AssertionError("test resealer did not converge")


def cli(payload, cwd=ROOT, explicit=True):
    env = {key: value for key, value in os.environ.items()
           if key.upper() not in {"PYTHONUTF8", "PYTHONIOENCODING"}}
    env["PYTHONPATH"] = str(ROOT / "trainer/src")
    argv = [sys.executable, "-m", "neural.perspective_knowledge"]
    if explicit:
        argv.append("--check-structure")
    return subprocess.run(argv, input=payload, capture_output=True,
                          cwd=cwd, env=env, timeout=30)


class KnowledgeIdentityTests(unittest.TestCase):
    def test_literal_unicode_origin_and_domain_preimage(self):
        origin = {
            "kind": "origin", "battle_key": "fixture-Éclair-😀",
            "format": "gen9randombattle", "engine": "pokemon-showdown@0.11.10",
            "rule_version": "pk-rules/v1",
        }
        literal = ('{"battle_key":"fixture-Éclair-😀","engine":"pokemon-showdown@0.11.10",'
                   '"format":"gen9randombattle","kind":"origin","rule_version":"pk-rules/v1"}').encode("utf-8")
        expected = "sha256:49f5047da5468699433a7ce46a10816402a235501e3b0276a722dcc4d2bcc58f"
        self.assertEqual(canonical_knowledge_json(origin), literal)
        self.assertEqual("sha256:" + hashlib.sha256(b"pk/v1/origin\n" + literal).hexdigest(), expected)
        self.assertEqual(knowledge_identity(origin), expected)
        origin["id"] = "sha256:" + "0" * 64
        self.assertEqual(knowledge_identity(origin), expected)

    def test_all_sixteen_frozen_preimages_and_identity_domains(self):
        vectors = fixture("identity-vectors.json")
        self.assertEqual(len(vectors), 16)
        self.assertEqual({vector["kind"] for vector in vectors},
                         set(REFERENCE_PATHS) | {"projection"})
        for vector in vectors:
            with self.subTest(kind=vector["kind"]):
                obj = vector["object"]
                before = copy.deepcopy(obj)
                literal_preimage = bytes.fromhex(vector["preimage_utf8_hex"])
                domain = ("pk/v1/" + vector["kind"] + "\n").encode("ascii")
                self.assertTrue(literal_preimage.startswith(domain))
                expected = "sha256:" + hashlib.sha256(literal_preimage).hexdigest()
                self.assertEqual(expected, vector["id"])
                self.assertEqual(canonical_knowledge_json({k: v for k, v in obj.items() if k != "id"}),
                                 literal_preimage[len(domain):])
                self.assertEqual(knowledge_identity(obj), expected)
                self.assertEqual(obj, before)

    def test_handwritten_all_control_escapes_and_no_normalization(self):
        value = "".join(chr(i) for i in range(32)) + '"\\/É😀'
        escaped = (r'\u0000\u0001\u0002\u0003\u0004\u0005\u0006\u0007\b\t\n\u000b\f\r'
                   r'\u000e\u000f\u0010\u0011\u0012\u0013\u0014\u0015\u0016\u0017'
                   r'\u0018\u0019\u001a\u001b\u001c\u001d\u001e\u001f\"\\/É😀')
        literal = ('{"s":"' + escaped + '"}').encode("utf-8")
        self.assertEqual(canonical_knowledge_json({"s": value}), literal)
        self.assertEqual(parse_knowledge_json(literal), {"s": value})
        self.assertEqual(fixture("canonical-controls-vector.json")["canonical_json_literal"].encode("utf-8"), literal)
        self.assertNotEqual(canonical_knowledge_json({"s": "É"}), canonical_knowledge_json({"s": "E\u0301"}))

    def test_ordering_nested_id_and_scalar_roundtrip(self):
        value = {"z": [2, 1], "a": {"id": "inert", "b": True, "a": None}}
        self.assertEqual(canonical_knowledge_json(value), b'{"a":{"a":null,"b":true,"id":"inert"},"z":[2,1]}')
        self.assertEqual(parse_knowledge_json(canonical_knowledge_json(value)), value)
        self.assertEqual(parse_knowledge_json(r'{"s":"\ud83d\ude00"}'), {"s": "😀"})


class KnowledgeStrictIngressTests(unittest.TestCase):
    def test_raw_duplicate_numeric_and_unicode_rejections(self):
        cases = [
            b'{"a":1,"a":2}', b'{"a":1,"\\u0061":2}',
            b'{"x":{"a":1,"a":1}}', b'{"x":-0}', b'{"x":1.0}',
            b'{"x":1e0}', b'{"x":1E+0}', b'{"x":NaN}', b'{"x":Infinity}',
            b'\xef\xbb\xbf{}', b'{"x":"\xff"}', b'{"x":"\xc0\xaf"}',
            b'{"x":"\xed\xa0\x80"}', b'{"x":"\\ud800"}', b'{"x":"\\udfff"}',
            b'{"x":"\\ud800a"}', b'{} {}', b'{"x":01}', b'{"x":+1}',
        ]
        for raw in cases:
            with self.subTest(raw=repr(raw)):
                with self.assertRaises(ValueError):
                    parse_knowledge_json(raw)
        for raw in ('\ufeff{}', '{"x":"\ud800"}'):
            with self.assertRaises(ValueError):
                parse_knowledge_json(raw)

    def test_object_api_rejects_non_json_types_scalars_cycles_and_expansion(self):
        cycle = []
        cycle.append(cycle)
        deep = 0
        for _ in range(34):
            deep = [deep]
        cases = [1.0, -0.0, math.inf, math.nan, {"x": "\ud800"},
                 {1: "key"}, {"é": "key"}, {"x": (1, 2)}, {"x": b"private"},
                 {"x": "a" * 257}, {"x": "😀" * 257}, deep, cycle]
        for value in cases:
            with self.subTest(type=type(value).__name__):
                with self.assertRaises(ValueError):
                    canonical_knowledge_json(value)
        with self.assertRaises(ValueError):
            parse_knowledge_json(b" " * (16 * 1024 * 1024) + b"{}")
        with self.assertRaises(ValueError):
            parse_knowledge_json("[" * 34 + "0" + "]" * 34)
        self.assertEqual(parse_knowledge_json(b'{"n":2147483647,"b":true}'), {"n": 2147483647, "b": True})
        self.assertEqual(len(canonical_knowledge_json({"s": "😀" * 256})), 1032)

    def test_nested_raw_request_strict_rules_and_separate_string_bound(self):
        invalid = [r'{"x":1,"x":2}', r'{"x":-0}', r'{"x":1.0}', r'{"x":1e0}',
                   r'{"x":"\ud800"}', '{"x":' + "[" * 34 + "0" + "]" * 34 + "}",
                   '{"x":"' + "a" * 65537 + '"}']
        for raw in invalid:
            audit = fixture("sim-full.json")
            source = next(row for row in audit["tables"]["source"] if row["raw_request"] is not None)
            source["raw_request"]["json"] = raw
            reseal(audit)
            before = copy.deepcopy(audit)
            with self.subTest(raw=raw[:40]):
                with self.assertRaises(ValueError):
                    check_knowledge_structure(audit)
                with self.assertRaises(ValueError):
                    serialize_knowledge_wire(audit)
                self.assertEqual(audit, before)
        audit = fixture("sim-full.json")
        source = next(row for row in audit["tables"]["source"] if row["raw_request"] is not None)
        # Whitespace is part of delivered text. The exception applies only to this field.
        source["raw_request"]["json"] += " " * 300
        reseal(audit)
        self.assertEqual(check_knowledge_structure(audit), DIAGNOSTIC)
        self.assertEqual(parse_knowledge_json(serialize_knowledge_wire(audit)), audit)


class KnowledgeStructureTests(unittest.TestCase):
    def assert_resealed_rejects(self, audit):
        reseal(audit)
        self.assertEqual(audit["id"], independent_id(audit))
        for table in audit["tables"].values():
            for row in table:
                self.assertEqual(row["id"], independent_id(row))
        before = copy.deepcopy(audit)
        with self.assertRaises(ValueError):
            check_knowledge_structure(audit)
        self.assertEqual(audit, before)

    def test_all_forms_both_owners_and_inert_text_have_only_limited_diagnostics(self):
        names = [
            "sim-full.json", "sim-ordinary.json", "sim-compact.json",
            "replay-full.json", "replay-ordinary.json", "replay-compact.json",
            "replay-suffix-full.json", "replay-suffix-ordinary.json", "replay-suffix-compact.json",
            "sim-p1-consumer.json", "sim-p2-consumer.json", "replay-p1-consumer.json", "replay-p2-consumer.json",
            "sim-p1-actionable-consumer.json", "sim-p1-wait-consumer.json",
            "missing-original-full.json", "sim-concurrent-effects-full.json",
            "inert-hash-full.json", "inert-self-hash-full.json", "inert-hash-ordinary.json",
            "inert-self-hash-ordinary.json", "inert-hash-compact.json", "inert-self-hash-compact.json",
            "inert-capability-words-consumer.json", "inert-missing-hash-consumer.json", "inert-array-consumer.json",
        ]
        for name in names:
            with self.subTest(name=name):
                value = fixture(name)
                before = copy.deepcopy(value)
                self.assertEqual(check_knowledge_structure(value, value["required_profile"]), DIAGNOSTIC)
                serialized = serialize_knowledge_wire(value)
                self.assertIsInstance(serialized, bytes)
                self.assertEqual(parse_knowledge_json(serialized), value)
                self.assertEqual(value, before)

    def test_compact_expands_to_same_content_and_suffix_keeps_causal_domains(self):
        for source in ("sim", "replay", "replay-suffix"):
            full = fixture(source + "-full.json")
            ordinary = fixture(source + "-ordinary.json")
            compact = fixture(source + "-compact.json")
            self.assertEqual(full["tables"], ordinary["tables"])
            expanded = {kind: sorted(table.values(), key=lambda row: row["id"])
                        for kind, table in compact["tables"].items()}
            self.assertEqual(expanded, full["tables"])
        for form in ("full", "ordinary", "compact"):
            base, suffix = fixture("replay-" + form + ".json"), fixture("replay-suffix-" + form + ".json")
            for kind in ("prefix", "current"):
                def causal(audit):
                    rows = audit['tables'][kind]
                    rows = list(rows.values()) if isinstance(rows, dict) else rows
                    return sorted([row for row in rows if (len(row['records']) if kind == 'prefix' else row['cursor']) <= 5], key=lambda row:row['id'])
                self.assertEqual(causal(base), causal(suffix))
            self.assertNotEqual(base["target_boundary"], suffix["target_boundary"])

    def test_frozen_structural_rejections_have_independently_verified_ids(self):
        names = [
            "missing-key", "extra-key", "wrong-type", "wrong-discriminant", "duplicate",
            "dangling-reference", "wrong-owner", "wrong-policy", "wrong-source", "broken-origin",
            "broken-parent", "broken-request", "broken-history", "weaker-profile",
            "compact-private-traversal", "compact-future-traversal", "crosswalk-foreign-owner",
            "starting-revision-fork", "certificate-property", "foreign-original-source",
            "wrong-value-tag", "wrong-effect-identity", "in-range-future-source", "unreachable-entry",
            "cross-source-parent", "old-source-carryover", "same-source-proved-change",
            "old-source-fact-certificate", "old-source-crosswalk-certificate", "stripped-replay-certificate",
            "inert-orphan-full", "inert-orphan-compact", "consumer-privileged-field",
            "consumer-nested-capability", "consumer-foreign-starting",
        ]
        for name in names:
            with self.subTest(name=name):
                value = fixture("negative-" + name + ".json")
                before = copy.deepcopy(value)
                self.assertEqual(value["id"], independent_id(value))
                if "tables" in value:
                    for table in value["tables"].values():
                        for row in (table.values() if isinstance(table, dict) else table):
                            self.assertEqual(row["id"], independent_id(row))
                with self.assertRaises(ValueError):
                    check_knowledge_structure(value, SIM_PROFILE if name == 'weaker-profile' else None)
                self.assertEqual(value, before)

    def test_resealed_wrong_kind_order_duplicates_binding_and_retention(self):
        for mutation in ("wrong_kind", "order", "duplicate", "binding", "retention", "bool_integer"):
            audit = fixture("replay-full.json")
            with self.subTest(mutation=mutation):
                if mutation == "wrong_kind":
                    audit["tables"]["current"][0]["facts"][0] = audit["tables"]["prefix"][0]["id"]
                elif mutation == "order":
                    audit["tables"]["fact"].reverse()
                    audit["id"] = independent_id(audit)
                    with self.assertRaises(ValueError):
                        check_knowledge_structure(audit)
                    continue
                elif mutation == "duplicate":
                    audit["tables"]["fact"].append(copy.deepcopy(audit["tables"]["fact"][0]))
                elif mutation == "binding":
                    row = audit["tables"]["binding"][0]
                    row["input_observation"] = "sha256:" + "0" * 64
                elif mutation == "retention":
                    child = next(row for row in audit["tables"]["starting"] if row["parent"])
                    parent = next(row for row in audit["tables"]["starting"] if row["id"] == child["parent"])
                    retained = set(parent["facts"]) & set(child["facts"])
                    self.assertTrue(retained)
                    child["facts"].remove(next(iter(retained)))
                else:
                    audit["tables"]["boundary"][0]["index"] = True
                self.assert_resealed_rejects(audit)

    def test_compact_map_key_profile_substitution_and_extra_schema_reject(self):
        audit = fixture("sim-compact.json")
        table = audit["tables"]["fact"]
        table["sha256:" + "0" * 64] = table.pop(next(iter(table)))
        audit["id"] = independent_id(audit)
        with self.assertRaises(ValueError):
            check_knowledge_structure(audit)
        for value in (fixture("sim-full.json"), fixture("sim-p1-consumer.json")):
            with self.assertRaises(ValueError):
                check_knowledge_structure(value, REPLAY_PROFILE)
        audit = fixture("sim-full.json")
        audit["schema_override"] = fixture("schema.json")
        with self.assertRaises(ValueError):
            check_knowledge_structure(audit)

    def test_source_truth_canaries_are_explicitly_unverified(self):
        # These have valid structure but false source-derived truth/authority in
        # the document checker. Accepting structure must not authenticate them.
        for name in ("authority-label-forgery", "false-item", "false-original-value", "false-replay-reproof"):
            with self.subTest(name=name):
                value = fixture("negative-" + name + ".json")
                self.assertEqual(check_knowledge_structure(value), DIAGNOSTIC)

    def test_named_representation_keys_bounds_and_projection_consistency(self):
        # Hand-authored structural claims only; these proofs do not establish truth.
        for owner in ('p1','p2'):
            audit=fixture('sim-full.json')
            current=next(r for r in audit['tables']['current'] if r['owner']==owner and r['cursor']==3)
            proof=next(r for r in audit['tables']['evidence'] if r['scope']=='public' and r['record_indices'] and max(r['record_indices'])<3)
            claims=[('K13','side_condition_layers','Spikes',{'type':'integer','data':2}),
                    ('K15','pending_power','FutureSight',{'type':'power','data':{'basis':'base_move','amount':120}}),
                    ('K14','field_remaining','weather:RainDance',{'type':'field_timer','data':{'target_kind':'weather','name':'RainDance','remaining':{'min':4,'max':7}}}),
                    ('K14','field_remaining','terrain:ElectricTerrain',{'type':'field_timer','data':{'target_kind':'terrain','name':'ElectricTerrain','remaining':{'min':5,'max':8}}})]
            for family,prop,key,value in claims:
                fact={'kind':'fact','owner':owner,'subject':owner+':side','family':family,'property':prop,'effect_key':key,'state':'known','value':value,
                      'reason':'none','freshness':'current','precision':'interval' if prop=='field_remaining' else 'exact','observed_at':max(proof['record_indices'])+1,'evidence':[proof['id']],'certificate':None}
                fact['id']=independent_id(fact); audit['tables']['fact'].append(fact); current['facts'].append(fact['id'])
            reseal(audit); self.assertEqual(check_knowledge_structure(audit),DIAGNOSTIC)
            controls=[('side_condition_layers',lambda f:f['value'].update(data=0)),
                      ('side_condition_layers',lambda f:f['value'].update(data=4)),
                      ('side_condition_layers',lambda f:f.update(value={'type':'text','data':'2'})),
                      ('pending_power',lambda f:f['value']['data'].update(amount=65536)),
                      ('field_remaining',lambda f:f.update(effect_key=None)),
                      ('field_remaining',lambda f:f.update(effect_key='terrain:Wrong')),
                      ('field_remaining',lambda f:f['value']['data']['remaining'].update(min=8,max=4))]
            for prop,mutate in controls:
                changed=copy.deepcopy(audit); mutate(next(f for f in changed['tables']['fact'] if f['property']==prop)); self.assert_resealed_rejects(changed)
        for mutate in (lambda f:f.update(family='K01'),lambda f:f.update(value={'type':'text','data':'bad'}),lambda f:f.update(state='unknown',value={'type':'integer','data':1})):
            projection=fixture('sim-p1-actionable-consumer.json')
            f=next(f for f in projection['request']['facts'] if f['property']=='pp')
            mutate(f); projection['id']=independent_id(projection)
            with self.assertRaises(ValueError): check_knowledge_structure(projection)

    def test_restoration_binding_certificate_and_delivery_controls(self):
        mutations=[
          ('restored pointer',lambda a:next(b for b in a['tables']['boundary'] if b['boundary_type']=='restored').update(restored_from=None)),
          ('missing binding',lambda a:a['tables']['binding'].pop()),
          ('duplicate binding',lambda a:a['tables']['binding'].append(copy.deepcopy(a['tables']['binding'][0]))),
          ('binding sequence',lambda a:a['tables']['binding'][0].update(successor_index=0)),
          ('belief join',lambda a:a['tables']['binding'][0].update(successor_belief='sha256:'+'0'*64)),
          ('nonactor transition',lambda a:next(b for b in a['tables']['binding'] if b['actor_record'] is None).update(transition='sha256:'+'0'*64)),
          ('request-only future',lambda a:next(f for f in a['tables']['fact'] if f['property']=='maybe_trapped' and f['state']=='known').update(observed_at=99))]
        for name,mutate in mutations:
            with self.subTest(name=name):
                audit=fixture('sim-full.json'); mutate(audit); self.assert_resealed_rejects(audit)
        for mutate in (lambda c:c.update(continuity='ambiguous'),lambda c:c['exclusions'].pop()):
            audit=fixture('replay-full.json'); mutate(audit['tables']['certificate'][0]); self.assert_resealed_rejects(audit)
        ordinary='{"raw_request.json":'+json.dumps('{"s":"'+'a'*300+'"}')+'}'
        with self.assertRaises(ValueError): parse_knowledge_json(ordinary)

    def test_restored_retention_and_evidence_free_request_lifecycle(self):
        audit=fixture('sim-full.json')
        restored=next(b for b in audit['tables']['boundary'] if b['boundary_type']=='restored')
        knowledge=next(k for k in audit['tables']['knowledge'] if k['id']==restored['bindings'][0]['knowledge'])
        current=next(c for c in audit['tables']['current'] if c['id']==knowledge['current'])
        fact=next(f for f in audit['tables']['fact'] if f['id'] in current['facts'] and f['family']!='K20')
        current['facts'].remove(fact['id']); reseal(audit)
        with self.assertRaisesRegex(ValueError,'restored fact retention'): check_knowledge_structure(audit)
        audit=fixture('sim-full.json'); request=next(r for r in audit['tables']['request'] if r['owner']=='p1' and r['cursor']==0)
        fact=copy.deepcopy(next(f for f in audit['tables']['fact'] if f['property']=='pp' and f['state']=='unknown' and f['owner']=='p1'))
        fact.update(subject='p1:roster:6:move:4:incarnation:99',observed_at=99,evidence=[]); fact['id']=independent_id(fact)
        audit['tables']['fact'].append(fact); request['facts'].append(fact['id']); reseal(audit)
        with self.assertRaisesRegex(ValueError,'request observation cursor'): check_knowledge_structure(audit)
        audit=fixture('sim-full.json'); restored=next(b for b in audit['tables']['boundary'] if b['boundary_type']=='restored')
        knowledge=next(k for k in audit['tables']['knowledge'] if k['id']==restored['bindings'][0]['knowledge'])
        current=next(c for c in audit['tables']['current'] if c['id']==knowledge['current'])
        source=copy.deepcopy(next(s for s in audit['tables']['source'] if s['source_type']=='owner_request' and s['owner']=='p1'))
        source.update(delivery_seq=3,delivery_cursor=current['cursor']); source['id']=independent_id(source)
        request=copy.deepcopy(next(r for r in audit['tables']['request'] if r['owner']=='p1'))
        request.update(source=source['id'],sequence=3,cursor=current['cursor'],prefix=current['prefix'],facts=[]); request['id']=independent_id(request)
        audit['tables']['source'].append(source); audit['tables']['request'].append(request); knowledge['request']=request['id']; reseal(audit)
        with self.assertRaisesRegex(ValueError,'restored terminal request'): check_knowledge_structure(audit)
        # Terminal requestlessness survives more than one restoration.
        knowledge['request']=None
        next_boundary=copy.deepcopy(restored); next_boundary.update(index=restored['index']+1,parent=restored['id'],restored_from=restored['id'])
        for row in next_boundary['bindings']:
            oldrow=next(r for r in restored['bindings'] if r['owner']==row['owner'])
            oldknowledge=next(k for k in audit['tables']['knowledge'] if k['id']==oldrow['knowledge'])
            oldcurrent=next(c for c in audit['tables']['current'] if c['id']==oldknowledge['current'])
            newcurrent=copy.deepcopy(oldcurrent); newcurrent['parent']=oldcurrent['id']; newcurrent['id']=independent_id(newcurrent)
            newknowledge=copy.deepcopy(oldknowledge); newknowledge.update(current=newcurrent['id'],boundary=next_boundary['index'],request=request['id'] if row['owner']=='p1' else None); newknowledge['id']=independent_id(newknowledge)
            verdict=copy.deepcopy(next(v for v in audit['tables']['verdict'] if v['id']==oldrow['verdict'])); verdict['knowledge']=newknowledge['id']; verdict['id']=independent_id(verdict)
            row.update(knowledge=newknowledge['id'],verdict=verdict['id'])
            audit['tables']['current'].append(newcurrent); audit['tables']['knowledge'].append(newknowledge); audit['tables']['verdict'].append(verdict)
            binding={'kind':'binding','origin':audit['origin'],'owner':row['owner'],'input_index':restored['index'],'successor_index':next_boundary['index'],
                     'input_knowledge':oldrow['knowledge'],'successor_knowledge':row['knowledge'],'input_observation':oldrow['observation_id'],'successor_observation':row['observation_id'],
                     'input_belief':oldrow['belief_id'],'successor_belief':row['belief_id'],'transition':None,'actor_record':None}
            binding['id']=independent_id(binding); audit['tables']['binding'].append(binding)
        next_boundary['id']=independent_id(next_boundary); audit['tables']['boundary'].append(next_boundary); audit['target_boundary']=next_boundary['id']; reseal(audit)
        with self.assertRaisesRegex(ValueError,'restored terminal request'): check_knowledge_structure(audit)

    def test_legacy_v1_v2_bytes_identities_and_entrypoints_remain_opt_in(self):
        from trainer.tests.test_pipeline_record import _bundle
        from neural.pipeline_record import validate_pipeline_bundle
        from neural.ts_identity import verify_bundle_identities
        for version in ('v1','v2'):
            for owner in ('p1','p2'):
                bundle=_bundle(unicode_prefix=True,perspective=owner,version=version)
                frozen=independent_canonical(bundle); before=independent_canonical(validate_pipeline_bundle(bundle))
                verify_bundle_identities(bundle)
                check_knowledge_structure(fixture('sim-full.json'))
                self.assertEqual(independent_canonical(validate_pipeline_bundle(bundle)),before)
                self.assertEqual(independent_canonical(bundle),frozen)
                verify_bundle_identities(bundle)
        for name in ('trainer/src/neural/pipeline_record.py','trainer/src/neural/typed_state.py',
                     'sim-core/src/observable_state.ts','sim-core/src/belief_state.ts','sim-core/src/pipeline_episode.ts'):
            self.assertNotIn('perspective_knowledge',(ROOT/name).read_text(encoding='utf-8'))


class KnowledgeCliTests(unittest.TestCase):
    def test_cold_missing_tampered_contract_fails_and_restored_copy_recovers(self):
        with tempfile.TemporaryDirectory() as temporary:
            sandbox=Path(temporary); package=sandbox/'trainer/src/neural'; package.mkdir(parents=True)
            shutil.copyfile(ROOT/'trainer/src/neural/perspective_knowledge.py',package/'perspective_knowledge.py')
            (package/'__init__.py').write_text('',encoding='utf-8')
            folder=sandbox/'docs/contracts/fixtures/perspective-knowledge-v1'; folder.mkdir(parents=True)
            names=('schema.json','profiles.json','property-types.json','property-contexts.json','typed-references.json')
            for name in names: shutil.copyfile(FIXTURES/name,folder/name)
            env={k:v for k,v in os.environ.items() if k.upper() not in ('PYTHONUTF8','PYTHONIOENCODING','PYTHONPATH')}; env['PYTHONPATH']=str(package.parent)
            def run(): return subprocess.run([sys.executable,'-m','neural.perspective_knowledge','--check-structure'],input=independent_canonical(fixture('sim-full.json')),capture_output=True,cwd=sandbox,env=env,timeout=30)
            self.assertEqual(run().returncode,0)
            original=(folder/'schema.json').read_bytes(); (folder/'schema.json').unlink()
            absent=run(); self.assertEqual(absent.returncode,2); self.assertEqual(absent.stdout,b'')
            (folder/'schema.json').write_bytes(original+b' ')
            changed=run(); self.assertEqual(changed.returncode,2); self.assertEqual(changed.stdout,b''); self.assertEqual(changed.stderr,absent.stderr)
            (folder/'schema.json').write_bytes(original); self.assertEqual(run().returncode,0)
    def test_valid_diagnostic_is_small_and_cwd_independent(self):
        value = fixture("sim-full.json")
        before = copy.deepcopy(value)
        raw = serialize_knowledge_wire(value)
        with tempfile.TemporaryDirectory() as elsewhere:
            result = cli(raw, cwd=elsewhere)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), DIAGNOSTIC)
        self.assertLess(len(result.stdout), 256)
        self.assertEqual(result.stderr, b"")
        self.assertEqual(value, before)
        self.assertNotIn(b"fixture", result.stdout)
        self.assertNotIn(b"sha256:", result.stdout)

    def test_invalid_atomic_constant_diagnostic_and_failure_cleanup(self):
        private = b'{"SECRET_PRIVATE_SOURCE":1,"SECRET_PRIVATE_SOURCE":2}'
        invalid_join = fixture("negative-broken-request.json")
        diagnostics = []
        for raw in (private, b'\xff', b'{"n":-0}', independent_canonical(invalid_join)):
            result = cli(raw)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, b"")
            self.assertNotIn(b"SECRET_PRIVATE_SOURCE", result.stderr)
            self.assertNotIn(b"sha256:", result.stderr)
            diagnostics.append(result.stderr)
        self.assertTrue(diagnostics[0])
        self.assertEqual(len(set(diagnostics)), 1)
        self.assertEqual(cli(serialize_knowledge_wire(fixture("sim-full.json"))).returncode, 0)

    def test_cli_requires_explicit_opt_in_mode(self):
        result = cli(serialize_knowledge_wire(fixture("sim-full.json")), explicit=False)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, b"")



def revision_form(audit, form):
    audit['form'] = form
    reseal(audit)
    if form == 'compact':
        audit['tables'] = {kind: {row['id']: row for row in rows}
                           for kind, rows in audit['tables'].items()}
        audit['id'] = independent_id(audit)
    return audit


def revision_crosswalk(owner, form):
    audit = fixture('replay-full.json')
    if owner == 'p1':
        start = next(s for s in audit['tables']['starting'] if s['owner'] == owner)
        cert = copy.deepcopy(next(c for c in audit['tables']['certificate'] if c['owner'] == owner))
        cert['property'] = 'identity_reveal'
        cert['id'] = independent_id(cert)
        audit['tables']['certificate'].append(cert)
        start['crosswalk'] = [{'appearance': 'p1:appearance:1', 'roster': 'p1:roster:1', 'certificate': cert['id']}]
    return revision_form(audit, form)


def revision_nested(count, style, leaf):
    # Count the terminal empty container too; scalar leaves add no container.
    value = [] if style != 'object' else {}
    if leaf != 'empty': value = [leaf] if style != 'object' else {'x': leaf}
    for index in range(1, count):
        value = {'x': value} if style == 'object' or style == 'mixed' and index % 2 else [value]
    return value


class KnowledgeRevisionTests(unittest.TestCase):
    def assert_sealed_immutable(self, audit, guard=None):
        self.assertEqual(audit['id'], independent_id(audit))
        for rows in audit['tables'].values():
            for row in rows if isinstance(rows, list) else rows.values():
                self.assertEqual(row['id'], independent_id(row))
        before = independent_canonical(audit)
        if guard:
            with self.assertRaisesRegex(ValueError, guard): check_knowledge_structure(audit)
            with self.assertRaisesRegex(ValueError, guard): serialize_knowledge_wire(audit)
        else:
            self.assertEqual(check_knowledge_structure(audit), DIAGNOSTIC)
            self.assertEqual(check_knowledge_structure(parse_knowledge_json(serialize_knowledge_wire(audit))), DIAGNOSTIC)
        self.assertEqual(independent_canonical(audit), before)

    def test_owner_crosswalk_mirrors_forms_and_exact_certificate_joins(self):
        for owner in ('p1', 'p2'):
            for form in ('full', 'ordinary', 'compact'):
                with self.subTest(owner=owner, form=form):
                    self.assert_sealed_immutable(revision_crosswalk(owner, form))
                    audit = revision_crosswalk(owner, 'full')
                    start = next(s for s in audit['tables']['starting'] if s['owner'] == owner and s['crosswalk'])
                    cross = start['crosswalk'][0]
                    cert = next(c for c in audit['tables']['certificate'] if c['id'] == cross['certificate'])
                    cross['roster'] = cert['subject'] = ('p2' if owner == 'p1' else 'p1') + ':roster:1'
                    self.assert_sealed_immutable(revision_form(audit, form), 'crosswalk owner')
            for field in ('appearance', 'subject', 'owner', 'source'):
                audit = revision_crosswalk(owner, 'full')
                start = next(s for s in audit['tables']['starting'] if s['owner'] == owner and s['crosswalk'])
                cross = start['crosswalk'][0]
                cert = next(c for c in audit['tables']['certificate'] if c['id'] == cross['certificate'])
                if field == 'appearance': cross[field] = ('p2' if owner == 'p1' else 'p1') + ':appearance:1'
                elif field == 'subject': cert[field] = owner + ':roster:2'
                elif field == 'owner': cert[field] = 'p2' if owner == 'p1' else 'p1'
                else:
                    source = copy.deepcopy(audit['tables']['source'][0]); source['records'][0] = '|turn|1'
                    source['id'] = independent_id(source); audit['tables']['source'].append(source); cert[field] = source['id']
                    witnesses = []
                    for ident in cert['witnesses']:
                        witness = copy.deepcopy(next(e for e in audit['tables']['evidence'] if e['id'] == ident))
                        witness['source'] = source['id']; witness['id'] = independent_id(witness)
                        audit['tables']['evidence'].append(witness); witnesses.append(witness['id'])
                    cert['witnesses'] = witnesses
                reseal(audit)
                self.assert_sealed_immutable(audit, 'crosswalk owner|certificate witness|crosswalk certificate source')

    def test_initialization_known_absent_unknown_delivery_cursor_both_owners(self):
        for owner in ('p1', 'p2'):
            for state in ('known', 'known_absent', 'unknown'):
                for cursor in (0, None, 99):
                    with self.subTest(owner=owner, state=state, cursor=cursor):
                        audit = fixture('sim-full.json')
                        fact = next(f for f in audit['tables']['fact'] if f['owner'] == owner and f['freshness'] == 'immutable')
                        fact['state'] = state; fact['observed_at'] = cursor
                        if state != 'known': fact.update(value=None, precision='not_applicable', reason='none' if state == 'known_absent' else 'missing_original_authority')
                        reseal(audit)
                        self.assert_sealed_immutable(audit, None if cursor == 0 or state == 'unknown' and cursor is None else 'initialization observation cursor')

    def test_retained_public_index_and_request_delivery_guards(self):
        for owner, prop, cursor in (('p1', 'item', 4), ('p2', 'roster_species', 6)):
            audit = fixture('replay-full.json')
            fact = next(f for f in audit['tables']['fact'] if f['owner'] == owner and f['property'] == prop and f['freshness'] == 'immutable')
            self.assertEqual(fact['observed_at'], cursor)
            self.assert_sealed_immutable(audit)
            fact['observed_at'] = 99; reseal(audit)
            self.assert_sealed_immutable(audit, 'observation cursor')
            audit = fixture('sim-full.json')
            fact = next(f for f in audit['tables']['fact'] if f['owner'] == owner and f['property'] == 'maybe_trapped' and f['state'] == 'known')
            self.assertEqual(fact['observed_at'], 3)
            self.assert_sealed_immutable(audit)
            fact['observed_at'] = 99; reseal(audit)
            self.assert_sealed_immutable(audit, 'request observation cursor')

    def test_exact_container_limit_parser_canonical_and_resealed_raw_request(self):
        for count in (31, 32, 33):
            for style in ('array', 'object', 'mixed'):
                for leaf in ('empty', 0, False, None, 'scalar'):
                    with self.subTest(count=count, style=style, leaf=leaf):
                        value = revision_nested(count, style, leaf)
                        wire = independent_canonical(value); before = copy.deepcopy(value)
                        if count <= 32:
                            self.assertEqual(parse_knowledge_json(wire), value)
                            self.assertEqual(canonical_knowledge_json(value), wire)
                        else:
                            with self.assertRaisesRegex(ValueError, 'depth'): parse_knowledge_json(wire)
                            with self.assertRaisesRegex(ValueError, 'depth'): canonical_knowledge_json(value)
                        self.assertEqual(value, before)
                        audit = fixture('sim-full.json')
                        source = next(s for s in audit['tables']['source'] if s['raw_request'] is not None)
                        source['raw_request']['json'] = wire.decode('utf-8'); reseal(audit)
                        self.assert_sealed_immutable(audit, None if count <= 32 else 'depth')





LEGACY_POSITIONS = {
    'observation': (('boundary', 'observation_id'), ('binding', 'input_observation'), ('binding', 'successor_observation')),
    'belief': (('boundary', 'belief_id'), ('binding', 'input_belief'), ('binding', 'successor_belief')),
    'actor': (('boundary', 'actor_record_id'), ('binding', 'actor_record')),
    'transition': (('binding', 'transition'),),
}


def native_legacy_control(version, form='full'):
    # IDs originate in four independently legacy-validated witnesses. The source
    # canary's chronology is synthetic; these are structure-only join controls.
    audit = fixture('sim-full.json')
    witnesses = {r['owner']: r for r in fixture('legacy-id-regressions.json')['witnesses'] if r['version'] == version}
    boundaries = {b['index']: b for b in audit['tables']['boundary']}
    for boundary in boundaries.values():
        for row in boundary['bindings']:
            witness = witnesses[row['owner']]
            which = 'input' if boundary['index'] == 0 else 'successor'
            row['observation_id'] = witness[which + '_observation']
            row['belief_id'] = witness[which + '_belief']
            if boundary['index'] == 1 or row['actor_record_id'] is not None: row['actor_record_id'] = witness['record_id']
    for row in audit['tables']['binding']:
        owner = row['owner']
        old = next(b for b in boundaries[row['input_index']]['bindings'] if b['owner'] == owner)
        new = next(b for b in boundaries[row['successor_index']]['bindings'] if b['owner'] == owner)
        row.update(input_observation=old['observation_id'],successor_observation=new['observation_id'],
                   input_belief=old['belief_id'],successor_belief=new['belief_id'],actor_record=new['actor_record_id'])
        row['transition'] = None if row['actor_record'] is None else witnesses[owner]['transition']
    return revision_form(audit, form)


def coordinated_legacy_scalar(audit, field, value):
    kind, name = field.split('.')
    if kind == 'owner_binding':
        target = next(row for boundary in audit['tables']['boundary'] for row in boundary['bindings']
                      if row['owner'] == 'p1' and (name != 'actor_record_id' or row[name] is not None))
    else:
        target = next(row for row in audit['tables']['binding'] if row['owner'] == 'p1'
                      and (name not in ('actor_record', 'transition') or row[name] is not None))
    category = 'actor' if 'actor' in name else 'transition' if name == 'transition' else 'belief' if 'belief' in name else 'observation'
    old = target[name]
    for table, key in LEGACY_POSITIONS[category]:
        rows = audit['tables'][table]
        if table == 'boundary': rows = [r for b in rows for r in b['bindings']]
        for row in rows:
            if row[key] == old: row[key] = value
    if value is None and category in ('actor','transition'):
        for boundary in audit['tables']['boundary']:
            for row in boundary['bindings']: row['actor_record_id'] = None
        for row in audit['tables']['binding']: row.update(actor_record=None,transition=None)
    return reseal(audit)


class NativeLegacyContractTests(unittest.TestCase):
    assert_sealed_immutable = KnowledgeRevisionTests.assert_sealed_immutable
    # Reuse sealed/immutable assertions without inheriting the revision cases.
    def test_native_correctly_joined_controls_both_owners_versions_forms(self):
        for version in ('observable-battle-state/v1', 'observable-battle-state/v2'):
            for form in ('full', 'ordinary', 'compact'):
                with self.subTest(version=version, form=form):
                    audit = native_legacy_control(version, form)
                    self.assert_sealed_immutable(audit)
                    result = cli(serialize_knowledge_wire(audit))
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(json.loads(result.stdout), DIAGNOSTIC)

    def test_field_specific_scalar_packet_and_internal_domain(self):
        for vector in fixture('legacy-id-regressions.json')['vectors']:
            with self.subTest(field=vector['field'], case=vector['case']):
                audit = native_legacy_control('observable-battle-state/v1')
                coordinated_legacy_scalar(audit, vector['field'], vector['value'])
                self.assert_sealed_immutable(audit, None if vector['accepted'] else 'schema union')
        for prefix in ('obs-', 'belief-', 'transition-', 'datarec-', 'action-'):
            for field in ('origin', 'required_profile'):
                audit = native_legacy_control('observable-battle-state/v1')
                audit[field] = prefix + '0' * 64; audit['id'] = independent_id(audit)
                self.assert_sealed_immutable(audit, 'schema union')

    def test_native_spelling_does_not_relax_inconsistent_legacy_joins(self):
        for field in ('input_observation','successor_observation','input_belief','successor_belief','actor_record'):
            audit = native_legacy_control('observable-battle-state/v1')
            row = next(r for r in audit['tables']['binding'] if r['actor_record'] is not None)
            row[field] = {'input_observation':'obs-','successor_observation':'obs-',
                          'input_belief':'belief-','successor_belief':'belief-','actor_record':'datarec-'}[field] + '0' * 64
            reseal(audit)
            self.assert_sealed_immutable(audit, 'history/legacy binding join|actor/transition join')


if __name__ == "__main__":
    unittest.main()
