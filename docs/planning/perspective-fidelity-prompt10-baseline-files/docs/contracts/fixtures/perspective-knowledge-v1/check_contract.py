"""Bounded independent document/fixture checker; NOT production validation."""
import hashlib
import json
import re
from pathlib import Path

ROOT=Path(__file__).parent


def load(path):
    def pairs(items):
        result={}
        for key,value in items:
            assert key not in result, 'duplicate JSON key'
            result[key]=value
        return result
    return json.loads(path.read_bytes().decode('utf-8'),object_pairs_hook=pairs,parse_constant=lambda s: (_ for _ in ()).throw(AssertionError(s)))


def canonical(x):
    # Independent implementation of normative bytes, not author's json.dumps.
    def encode(v):
        if v is None: return 'null'
        if type(v) is bool: return 'true' if v else 'false'
        if type(v) is int: return str(v)
        if type(v) is str:
            escapes={'"':'\\"','\\':'\\\\','\b':'\\b','\f':'\\f','\n':'\\n','\r':'\\r','\t':'\\t'}
            return '"'+''.join(escapes.get(c,'\\u%04x'%ord(c) if ord(c)<32 else c) for c in v)+'"'
        if type(v) is list: return '['+','.join(encode(i) for i in v)+']'
        assert type(v) is dict
        return '{'+','.join(encode(k)+':'+encode(v[k]) for k in sorted(v))+'}'
    return encode(x).encode('utf-8')


def expected_id(x):
    return 'sha256:'+hashlib.sha256(('pk/v1/'+x['kind']+'\n').encode()+canonical({k:v for k,v in x.items() if k!='id'})).hexdigest()


def shape(value,schema,defs,depth=0):
    assert depth<=32,'depth'
    if '$ref' in schema: return shape(value,defs[schema['$ref'].split('/')[-1]],defs,depth+1)
    if 'anyOf' in schema:
        for choice in schema['anyOf']:
            try: shape(value,choice,defs,depth+1); return
            except AssertionError: pass
        raise AssertionError('union mismatch')
    if 'const' in schema: assert type(value)==type(schema['const']) and value==schema['const'],'const'
    if 'enum' in schema: assert value in schema['enum'],'enum'
    typ=schema.get('type')
    if typ=='null': assert value is None,'null'
    if typ=='boolean': assert type(value) is bool,'boolean'
    if typ=='integer':
        assert type(value) is int,'integer'; assert schema.get('minimum',0)<=value<=schema.get('maximum',2147483647),'integer range'
    if typ=='string':
        assert type(value) is str,'string'; assert len(value)<=schema.get('maxLength',256),'string length'
        assert all(not 0xD800<=ord(c)<=0xDFFF for c in value),'surrogate'
        if 'pattern' in schema: assert re.fullmatch(schema['pattern'],value),'pattern'
    if typ=='array':
        assert type(value) is list and len(value)<=schema['maxItems'],'array'
        for entry in value: shape(entry,schema['items'],defs,depth+1)
    if typ=='object':
        assert type(value) is dict,'object'
        if schema.get('additionalProperties') is False:
            assert set(value)==set(schema['required']),'keys'
            for k,v in value.items(): shape(v,schema['properties'][k],defs,depth+1)
        else:
            assert len(value)<=schema['maxProperties'],'dictionary bound'
            for k,v in value.items(): shape(k,schema['propertyNames'],defs,depth+1); shape(v,schema['additionalProperties'],defs,depth+1)


def refs(x):
    if isinstance(x,str) and re.fullmatch(r'sha256:[0-9a-f]{64}',x): yield x
    elif isinstance(x,list):
        for v in x: yield from refs(v)
    elif isinstance(x,dict):
        for k,v in x.items():
            if k!='id': yield from refs(v)


def expanded(a):
    if a['form']=='compact':
        for rows in a['tables'].values():
            assert type(rows) is dict,'compact encoding'
            assert all(k==v['id'] for k,v in rows.items()),'compact dictionary key'
        return {k:sorted(rows.values(),key=lambda x:x['id']) for k,rows in a['tables'].items()}
    assert all(type(rows) is list for rows in a['tables'].values()),'array encoding'
    return a['tables']


def check_projection(x):
    owner=x['owner']
    allfacts=x['starting']+x['current']+([] if x['request'] is None else x['request']['facts'])
    for f in allfacts:
        assert f['owner']==owner,'projection fact owner'
        assert re.fullmatch(r'p[12]:(side|roster:[1-6]|appearance:[1-9][0-9]*|roster:[1-6]:move:[1-4]:incarnation:[0-9]+)',f['subject']),'subject capability'
        assert f['certificate'] if 'certificate' in f else True
    # Exact safe schema removes every source/proof/history traversal key.
    assert not any(k in canonical(x).decode('utf-8') for k in ['audit_store','restoration_handle','full_replay_url']), 'capability'
    for c in x['starting_crosswalk']:
        assert c['appearance'].startswith(owner+':appearance:') and c['roster'].startswith(owner+':roster:'),'crosswalk privacy'
    if x['policy']=='public-replay-owner-starting/v1': assert x['request'] is None,'replay request'
    if x['request'] is not None: assert x['request']['cursor']>=0,'safe request'


def check(a,required=None):
    schema=load(ROOT/'schema.json'); shape(a,schema,schema['$defs'])
    assert a['id']==expected_id(a),'root identity'
    if a['kind']=='projection': return check_projection(a)
    t=expanded(a); lookup={}
    for kind,rows in t.items():
        assert [x['id'] for x in rows]==sorted(set(x['id'] for x in rows)),'table duplicate/order'
        for x in rows:
            assert x['kind']==kind and x['id']==expected_id(x),'object identity'
            assert x['id'] not in lookup,'duplicate global ID'; lookup[x['id']]=x
    def get(i,kind):
        assert i in lookup and lookup[i]['kind']==kind,'dangling/wrong reference'; return lookup[i]
    origin=get(a['origin'],'origin'); profile=get(a['required_profile'],'profile')
    approved={x['id']:x for x in load(ROOT/'profiles.json')}
    assert profile['id'] in approved and profile==approved[profile['id']],'profile manifest'
    if required is not None: assert a['required_profile']==required,'weaker profile'
    authority=load(ROOT/'trusted-fixture-authority.json')
    assert origin['id'] in authority['origins'],'origin authority'
    for s in t['source']:
        assert s['origin']==origin['id'],'source origin'
        st=s['source_type']
        if st in ['owner_initialization','owner_request']:
            assert s['id'] in authority['delivered_sources'],'source-label authority forgery'
            assert s['owner'] in ['p1','p2'],'addressed owner'
            assert s['provider']==('addressed-team-provider/v1' if st=='owner_initialization' else 'addressed-request/v1'),'source provider'
        else: assert s['owner'] is None and s['provider']=='indexed-public/v1' and not s['team'] and s['raw_request'] is None,'public source shape'
        if st=='owner_initialization': assert s['phase']=='before_effects' and s['delivery_seq']==s['delivery_cursor']==0 and s['team'],'original delivery'
    for p in t['prefix']: assert p['origin']==origin['id'],'prefix origin'
    writers={'submitted-set/v1','original-possession/v1','identity-replace/v1','boundary/v1','consumption/v1','raw-request/v1','terminal-requestless/v1','appearance/v1','calculated-owner-stats/v1','original-default/v1','side-condition-start/v1'}
    for e in t['evidence']:
        s=get(e['source'],'source'); assert e['origin']==origin['id'] and s['origin']==origin['id'],'evidence origin'
        assert e['writer'] in writers,'unsupported writer'
        assert e['record_indices']==sorted(set(e['record_indices'])) and all(i<len(s['records']) for i in e['record_indices']),'record range'
        if e['scope']=='original':
            assert s['source_type'] in ['owner_initialization','public_replay'] and e['owner'] in ['p1','p2'] and e['prefix'] is None,'original scope'
            assert s['owner'] in [None,e['owner']],'original source owner'
        if e['scope']=='public': assert s['source_type']=='public_prefix' and e['owner'] is None and s['records']==get(e['prefix'],'prefix')['records'],'public future traversal'
        if e['scope']=='request': assert s['source_type']=='owner_request' and s['owner']==e['owner'] and len(get(e['prefix'],'prefix')['records'])==s['delivery_cursor'],'request proof'
    for c in t['certificate']:
        src=get(c['source'],'source'); assert src['source_type']=='public_replay','certificate source'
        assert c['scan_start']==0 and c['scan_end']==len(src['records']),'certificate scan'
        assert c['continuity']=='original_unmodified' and set(c['exclusions'])=={'transfer','copy','called','transform','acquisition','identity_ambiguity'},'certificate continuity'
        for w in c['witnesses']: assert get(w,'evidence')['owner']==c['owner'] and get(w,'evidence')['source']==src['id'],'certificate owner/source'
    obligations={r['family']:r['properties'] for r in profile['obligations']}
    for f in t['fact']:
        if f['freshness']!='immutable': assert f['certificate'] is None,'current fact/certificate'
        assert f['property'] in obligations[f['family']],'family property'
        assert re.fullmatch(r'p[12]:(side|roster:[1-6]|appearance:[1-9][0-9]*|roster:[1-6]:move:[1-4]:incarnation:[0-9]+)',f['subject']),'subject capability'
        if f['state']=='known':
            assert f['value'] is not None and f['reason']=='none' and f['evidence'],'known proof/value'
            assert f['value']['type'] in load(ROOT/'property-types.json')[f['property']],'property value tag'
            if f['value']['type']=='interval': assert f['value']['data']['min']<=f['value']['data']['max'],'interval order'
            if f['value']['type']=='effect': assert f['effect_key']==f['value']['data']['name'],'effect identity'
        else: assert f['value'] is None,'nonknown value'
        if 'effect' not in load(ROOT/'property-types.json')[f['property']]: assert f['effect_key'] is None,'effect key scope'
        if f['state']=='unknown':
            assert f['reason']!='none' and f['precision']=='not_applicable','unknown reason'
            assert not(f['reason']=='hidden_opponent' and f['subject'].startswith(f['owner']+':')),'dishonest unknown'
        if f['state']=='known_absent': assert f['reason']=='none' and f['evidence'],'absence proof'
        if f['state']=='inapplicable':
            assert f['reason']=='proved_rule_inapplicable' and f['property']=='request_presence' and f['evidence'],'dishonest inapplicable'
            assert all(get(e,'evidence')['writer']=='terminal-requestless/v1' for e in f['evidence']),'inapplicability rule'
        for eid in f['evidence']:
            e=get(eid,'evidence'); assert e['owner'] in [None,f['owner']],'foreign private proof'
            if e['record_indices'] and f['property'] not in ['boundary_kind','request_presence']:
                assert f['observed_at']==max(e['record_indices'])+1,'observation cursor'
            if e['writer']=='consumption/v1':
                s=get(e['source'],'source'); assert '|-enditem|' in s['records'][e['record_indices'][0]],'consumption raw witness'
                assert f['state']=='known_absent' and f['property']=='item','false consumed item'
            if e['writer']=='raw-request/v1' and f['property'] in ['pp','max_pp','maybe_trapped']:
                raw=json.loads(get(e['source'],'source')['raw_request']['json'])
                expected=raw['active'][0]['maybeTrapped'] if f['property']=='maybe_trapped' else raw['active'][0]['moves'][0][{'pp':'pp','max_pp':'maxpp'}[f['property']]]
                assert f['value']['data']==expected,'request value oracle'
            if e['writer']=='appearance/v1':
                assert f['subject']=='p2:appearance:1' and f['value']=={'type':'text','data':'Gengar'},'causal appearance oracle'
        if f['certificate'] is not None: assert get(f['certificate'],'certificate')['owner']==f['owner'],'certificate fact owner'
        if f['certificate'] is not None:
            c=get(f['certificate'],'certificate'); assert c['subject']==f['subject'] and c['property']==f['property'],'certificate property/subject'
    for s in t['starting']:
        assert s['facts']==sorted(set(s['facts'])),'starting fact order'
        keys=[(get(i,'fact')['owner'],get(i,'fact')['subject'],get(i,'fact')['family'],get(i,'fact')['property'],get(i,'fact')['effect_key']) for i in s['facts']]
        assert len(keys)==len(set(keys)),'logical fact conflict'
        assert s['origin']==origin['id'] and s['policy']==profile['policy'],'starting origin/policy'
        if s['source'] is not None:
            src=get(s['source'],'source'); assert src['owner'] in [None,s['owner']],'starting owner'
        if s['parent'] is None: assert s['revision']==0,'revision origin'
        else:
            old=get(s['parent'],'starting'); assert old['origin']==s['origin'] and old['owner']==s['owner'] and old['policy']==s['policy'] and s['revision']==old['revision']+1,'revision join'
            oldfacts={(get(i,'fact')['subject'],get(i,'fact')['property'],get(i,'fact')['effect_key']):get(i,'fact') for i in old['facts']}
            newfacts={(get(i,'fact')['subject'],get(i,'fact')['property'],get(i,'fact')['effect_key']):get(i,'fact') for i in s['facts']}
            assert set(oldfacts)<=set(newfacts),'immutable retention'
            for key,value in oldfacts.items():
                assert value==newfacts[key] or value['state']=='unknown' and newfacts[key]['state'] in ['known','known_absent'],'immutable refinement'
        for fid in s['facts']:
            f=get(fid,'fact'); assert f['owner']==s['owner'] and f['subject'].startswith(s['owner']+':') and f['freshness']=='immutable','starting fact'
            for eid in f['evidence']:
                e=get(eid,'evidence'); source=get(e['source'],'source')
                assert e['scope']=='original' and e['source']==s['source'],'starting evidence'
                assert source['owner'] in [None,s['owner']],'foreign original source'
                if source['source_type']=='owner_initialization' and f['state']=='known':
                    raw=source['team'][e['team_slot']-1]; prop={'item':'item','starting_moves':'moves'}[f['property']]
                    assert f['value']['data']==raw[prop],'original value oracle'
        for x in s['crosswalk']:
            c=get(x['certificate'],'certificate'); assert c['owner']==s['owner'] and x['appearance'].startswith(s['owner']+':appearance:') and x['roster']==c['subject'],'crosswalk owner'
    for c in t['current']:
        assert c['facts']==sorted(set(c['facts'])),'current fact order'
        keys=[(get(i,'fact')['owner'],get(i,'fact')['subject'],get(i,'fact')['family'],get(i,'fact')['property'],get(i,'fact')['effect_key']) for i in c['facts']]
        assert len(keys)==len(set(keys)),'logical fact conflict'
        assert c['origin']==origin['id'] and c['cursor']==len(get(c['prefix'],'prefix')['records']),'current prefix/cursor'
        for fid in c['facts']:
            f=get(fid,'fact'); assert f['owner']==c['owner'] and f['freshness']!='immutable' and f['certificate'] is None,'current fact/certificate'
            assert f['observed_at'] is None or f['observed_at']<=c['cursor'],'future fact'
            for eid in f['evidence']:
                e=get(eid,'evidence'); assert e['scope'] in ['public','request'],'current future proof'
                p=get(e['prefix'],'prefix'); assert get(c['prefix'],'prefix')['records'][:len(p['records'])]==p['records'],'proof prefix ancestry'
    for r in t['request']:
        src=get(r['source'],'source'); assert src['owner']==r['owner'] and src['source_type']=='owner_request' and src['delivery_seq']==r['sequence'] and src['delivery_cursor']==r['cursor'],'request delivery join'
        assert len(get(r['prefix'],'prefix')['records'])==r['cursor'] and r['actionable']==(not json.loads(src['raw_request']['json']).get('wait',False)),'request action authority'
        for f in r['facts']: assert get(f,'fact')['owner']==r['owner'],'request owner'
    boundaries=sorted(t['boundary'],key=lambda x:x['index']); assert boundaries and [b['index'] for b in boundaries]==list(range(len(boundaries))),'history continuity'
    assert boundaries[-1]['id']==a['target_boundary'],'target boundary'
    previous={}
    for i,b in enumerate(boundaries):
        assert b['origin']==origin['id'] and b['parent']==(None if i==0 else boundaries[i-1]['id']),'boundary parent/origin'
        assert [x['owner'] for x in b['bindings']]==['p1','p2'],'both perspectives'
        assert b['restored_from']==(b['parent'] if b['boundary_type']=='restored' else None),'restore binding'
        for row in b['bindings']:
            k=get(row['knowledge'],'knowledge'); c=get(k['current'],'current'); s=get(k['starting'],'starting'); v=get(row['verdict'],'verdict')
            assert k['origin']==origin['id'] and k['owner']==row['owner']==c['owner']==s['owner'] and k['boundary']==i and k['policy']==s['policy']==profile['policy'],'knowledge join'
            assert c['cursor']==b['cursor'] and c['parent']==previous.get(k['owner']),'current parent/cursor'; previous[k['owner']]=c['id']
            if k['request'] is not None:
                r=get(k['request'],'request'); assert r['owner']==k['owner'] and r['prefix']==c['prefix'] and r['cursor']==c['cursor'],'knowledge request'
                assert k['policy']=='simulator-causal/v1' and b['boundary_type'] in ['initial','mid','wait'],'request lifecycle'
            assert v['knowledge']==k['id'] and v['profile']==profile['id'],'verdict join'
            assert [f['family'] for f in v['families']]==['K%02d'%n for n in range(1,21)],'family coverage'
            assert v['result']=='incomplete' and all(f['result']=='unsupported' and f['reason']=='unimplemented_family' for f in v['families']),'unsupported completeness promotion'
    assert len(t['binding'])==2*(len(boundaries)-1),'binding closure'
    seen=set()
    for r in t['binding']:
        key=(r['owner'],r['successor_index']); assert key not in seen; seen.add(key)
        assert r['input_index']+1==r['successor_index'] and r['origin']==origin['id'],'binding indices'
        old=next(x for x in boundaries[r['input_index']]['bindings'] if x['owner']==r['owner']); new=next(x for x in boundaries[r['successor_index']]['bindings'] if x['owner']==r['owner'])
        for field,key2 in [('knowledge','knowledge'),('observation','observation_id'),('belief','belief_id')]:
            assert r['input_'+field]==old[key2] and r['successor_'+field]==new[key2],'history/legacy binding join'
        assert r['actor_record']==new['actor_record_id'],'actor binding'
    # Every typed reference closes; old IDs are externally validated binding commitments only.
    external_keys={'observation_id','belief_id','actor_record_id','input_observation','successor_observation','input_belief','successor_belief','transition','actor_record'}
    def walk(x):
        if isinstance(x,dict):
            for key,value in x.items():
                if key not in external_keys and key!='id':
                    if isinstance(value,str) and value.startswith('sha256:'): assert value in lookup,'reference closure'
                    else: walk(value)
        elif isinstance(x,list):
            for value in x:
                if isinstance(value,str) and value.startswith('sha256:'): assert value in lookup,'reference closure'
                else: walk(value)
    walk(t)
    visited=set()
    def reachable(i):
        if i in visited: return
        visited.add(i)
        def inner(x):
            if isinstance(x,dict):
                for key,value in x.items():
                    if key not in external_keys and key!='id': inner(value)
            elif isinstance(x,list):
                for value in x: inner(value)
            elif isinstance(x,str) and x in lookup: reachable(x)
        inner(lookup[i])
    for root in [a['origin'],a['required_profile'],a['target_boundary']]+[x['id'] for x in t['binding']]: reachable(root)
    assert visited==set(lookup),'unreachable entry'


def main():
    manifest=load(ROOT/'case-manifest.json'); counts={'positive':0,'negative':0,'vectors':0}
    for name in manifest['positive']: check(load(ROOT/name)); counts['positive']+=1
    for row in load(ROOT/'negative-manifest.json'):
        payload=load(ROOT/row['file'])
        assert payload['id']==expected_id(payload),'negative root seal'
        for entries in expanded(payload).values():
            for x in entries: assert x['id']==expected_id(x),'negative object seal'
        try: check(payload,row['required_profile'])
        except AssertionError as e:
            assert str(e)==row['rejection_code'], 'wrong rejection '+row['file']+': '+str(e)
            counts['negative']+=1
        else: raise AssertionError('negative accepted '+row['file'])
    for v in load(ROOT/'identity-vectors.json'):
        x=v['object']; preimage=('pk/v1/'+x['kind']+'\n').encode()+canonical({k:v for k,v in x.items() if k!='id'})
        assert preimage.hex()==v['preimage_utf8_hex'] and expected_id(x)==v['id'] and x['id']==v['id']; counts['vectors']+=1
    assert canonical({'z':[0,True,None],'a':'Éclair 😀\n"\\'})=='{"a":"Éclair 😀\\n\\"\\\\","z":[0,true,null]}'.encode('utf-8'),'independent escaping vector'
    canary=load(ROOT/'effect-collection-canary.json'); definitions=load(ROOT/'schema.json')['$defs']
    objects={x['id']:x for x in canary['objects']}
    for x in objects.values(): shape(x,definitions[x['kind']],definitions); assert x['id']==expected_id(x),'effect subset identity'
    for current in [x for x in objects.values() if x['kind']=='current']:
        facts=[objects[i] for i in current['facts']]
        assert sorted(f['effect_key'] for f in facts)==canary['expected_names'],'concurrent effects'
        assert len({(f['subject'],f['family'],f['property'],f['effect_key']) for f in facts})==2,'effect logical keys'
        for f in facts:
            assert f['effect_key']==f['value']['data']['name'],'effect key/value'
            proof=objects[f['evidence'][0]]; raw=objects[proof['source']]['records'][proof['record_indices'][0]]
            assert raw.endswith('|'+f['effect_key']),'effect raw oracle'
    sim=load(ROOT/'sim-full.json'); compact=load(ROOT/'sim-compact.json'); assert sim['tables']==expanded(compact),'compact parity'
    old=load(ROOT/'replay-full.json'); new=load(ROOT/'replay-suffix-full.json')
    for kind in ['prefix','evidence','current']:
        def causal(a):
            if kind=='prefix': return sorted([x for x in a['tables'][kind] if len(x['records'])<=5],key=lambda x:x['id'])
            if kind=='current': return sorted([x for x in a['tables'][kind] if x['cursor']<=5],key=lambda x:x['id'])
            return sorted([x for x in a['tables'][kind] if x['scope']=='public' and all(i<5 for i in x['record_indices']) and len(next(p['records'] for p in a['tables']['prefix'] if p['id']==x['prefix']))<=5],key=lambda x:x['id'])
        assert causal(old)==causal(new),'suffix causal invariance '+kind
    assert {x['id'] for x in old['tables']['starting']}!={x['id'] for x in new['tables']['starting']},'starting discovery identity'
    print(json.dumps({'scope':'contract fixtures only; no production semantic acceptance','counts':counts,'effect_subset_canaries':1,'compact_parity':True,'causal_suffix_invariance':True}))


if __name__=='__main__': main()
