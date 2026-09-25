import json, copy
from neural.pipeline_record import validate_pipeline_bundle
from neural.public_boosts import observation_digest
b=json.load(open('/tmp/v2-review-compat.json'))
a=validate_pipeline_bundle(b)
d=copy.deepcopy(b)
for k in ('input_observation','successor_observation'):
    d[k]['schema_version']='observable-battle-state/v1'
    for p in d[k]['view']['opponent_team']: del p['public_boosts']
for k in ('input_belief','successor_belief'):
    for ref in [d[k]['observation']]+d[k]['observation_history']: ref['schema_version']='observable-battle-state/v1'
r=validate_pipeline_bundle(d)
json.dump(d,open('/tmp/v2-review-downgraded.json','w'))
print('v2 valid:', a['schema_fingerprints']['observation'])
print('downgrade accepted:', r['schema_fingerprints']['observation'])
print('preserved observation ID:',a['observation_id']==r['observation_id'])
print('preserved belief ID:',a['belief_id']==r['belief_id'])
print('downgraded observation ID invalid:', observation_digest(d['input_observation']) != d['input_observation']['observation_id'])
# Repair the observation identities everywhere, but retain the original v2 belief IDs.
replacements={d[k]['observation_id']:observation_digest(d[k]) for k in ('input_observation','successor_observation')}
def replace_refs(value):
    if isinstance(value,dict): return {k:replace_refs(v) for k,v in value.items()}
    if isinstance(value,list): return [replace_refs(v) for v in value]
    return replacements.get(value,value) if isinstance(value,str) else value
repaired=replace_refs(d)
r2=validate_pipeline_bundle(repaired)
json.dump(repaired,open('/tmp/v2-review-stale-belief.json','w'))
print('repaired observations with stale v2 belief IDs accepted:',r2['belief_id']==a['belief_id'])
print('repaired observation digest valid:',observation_digest(repaired['input_observation'])==repaired['input_observation']['observation_id'])
