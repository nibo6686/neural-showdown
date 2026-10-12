"""Reproduce the six lead findings from immutable PK-01 baseline snapshots."""
from pathlib import Path
import json
import copy

repo=Path(__file__).resolve().parents[2]
base=repo/'docs/planning/perspective-fidelity-prompt10-baseline-files'
fixtures=base/'docs/contracts/fixtures/perspective-knowledge-v1'
def module(name):
    path=fixtures/name; namespace={'__file__':str(path),'__name__':'baseline_inspection'}
    exec(compile(path.read_bytes(),str(path),'exec'),namespace); return namespace
a=module('author_fixtures.py'); c=module('check_contract.py')
def rejects(value):
    try: c['check'](value)
    except AssertionError as error: return str(error)
    return None
schema=json.loads((fixtures/'schema.json').read_text(encoding='utf-8'))
properties=schema['$defs']['fact']['properties']['property']['enum']
replay=json.loads((fixtures/'replay-full.json').read_text(encoding='utf-8'))
starts={s['id']:s for s in replay['tables']['starting']}
cross=next(s for s in starts.values() if s['parent'] is not None)
projection=json.loads((fixtures/'sim-p1-consumer.json').read_text(encoding='utf-8'))
projection['starting'][0]['value']['data']='audit_store restoration_handle full_replay_url'
projection.pop('id'); projection=a['seal']('projection',**{k:v for k,v in projection.items() if k!='kind'})
audit=json.loads((fixtures/'sim-full.json').read_text(encoding='utf-8'))
next(f for f in audit['tables']['fact'] if f['property']=='boundary_kind')['value']['data']='sha256:'+'e'*64
audit=a['reseal'](audit)
report=[
 {'finding':1,'observed_gap':'prose says all control hex; implementations use short escapes','contract_has_hex_only': 'control chars lower-case hex' in (base/'docs/contracts/PERSPECTIVE_KNOWLEDGE.md').read_text(encoding='utf-8'),'actual_lf_json':a['canonical']('\n').decode()},
 {'finding':2,'observed_gap':'cross-source parent accepted','sources_differ':cross['source']!=starts[cross['parent']]['source'],'rejection':rejects(replay)},
 {'finding':3,'observed_gap':'required layer/power properties unrepresentable','missing_properties':[p for p in ['side_condition_layers','pending_power'] if p not in properties]},
 {'finding':4,'observed_gap':'field_remaining only interval with null effect key; no target union','old_types':json.loads((fixtures/'property-types.json').read_text(encoding='utf-8'))['field_remaining']},
 {'finding':5,'observed_gap':'inert text incorrectly rejects','projection_rejection':rejects(projection),'inert_hash_rejection':rejects(audit)},
 {'finding':6,'observed_gap':'family flags cannot expand per-property/context/subject','has_property_context_manifest':(fixtures/'property-contexts.json').exists()}
]
(repo/'docs/planning/perspective-fidelity-prompt10-red-results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'scope':'immutable baseline reproduction','lead_findings_reproduced':6,'details':report}))
raise SystemExit(1)
