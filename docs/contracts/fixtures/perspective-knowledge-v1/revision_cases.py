"""PK-01R independent ledgers and regression controls; no production imports."""
import copy
import hashlib
import json
from pathlib import Path
from typed_references import map_edges

ROOT=Path(__file__).parent
# Literal supplied/reviewed independently, not produced by either canonicalizer.
CONTROL_LITERAL=r'{"s":"\u0000\u0001\u0002\u0003\u0004\u0005\u0006\u0007\b\t\n\u000b\f\r\u000e\u000f\u0010\u0011\u0012\u0013\u0014\u0015\u0016\u0017\u0018\u0019\u001a\u001b\u001c\u001d\u001e\u001f\"\\/É😀"}'


def add_revision_cases(cases):
    # Imported only after the baseline author has assembled its prior canaries.
    import author_fixtures as A
    positive=json.loads((ROOT/'case-manifest.json').read_text(encoding='utf-8'))
    negative=json.loads((ROOT/'negative-manifest.json').read_text(encoding='utf-8'))
    def add(name,x): A.write(name,x); positive['positive'].append(name)
    def reject(name,base,mutate,code):
        x=copy.deepcopy(base); mutate(x); x=A.reseal(x)
        name='negative-'+name+'.json'; A.write(name,x)
        negative.append({'file':name,'required_profile':base['required_profile'],'expected':'contract_reject','fully_resealed':True,'rejection_code':code})
    replay=cases['replay-full.json']; fork=cases['replay-suffix-full.json']; sim=cases['sim-full.json']
    def cross_source(x):
        oldsrc=next(s for s in x['tables']['source'] if s['source_type']=='public_replay')
        new=copy.deepcopy(oldsrc); new['records'][-1]='|win|Other'
        new=A.seal('source',**{k:v for k,v in new.items() if k not in ['id','kind']}); x['tables']['source'].append(new)
        next(s for s in x['tables']['starting'] if s['parent'] is not None)['source']=new['id']
    reject('cross-source-parent',replay,cross_source,'revision source')
    def carry(x):
        oldsrc=next(s for s in replay['tables']['source'] if s['source_type']=='public_replay')
        x['tables']['source'].append(copy.deepcopy(oldsrc)); next(s for s in x['tables']['starting'] if s['owner']=='p2')['source']=oldsrc['id']
    reject('old-source-carryover',fork,carry,'starting evidence')
    def changed_proved(x):
        child=next(s for s in x['tables']['starting'] if s['parent'] is not None)
        proved=next(f for f in x['tables']['fact'] if f['id'] in child['facts'] and f['property']=='roster_species')
        changed=A.seal('fact',**{k:v for k,v in proved.items() if k not in ['id','kind']}|{'precision':'public_bucket'})
        x['tables']['fact'].append(changed); child['facts']=[changed['id'] if i==proved['id'] else i for i in child['facts']]
    reject('same-source-proved-change',replay,changed_proved,'immutable refinement')
    reject('false-replay-reproof',fork,lambda x:next(f for f in x['tables']['fact'] if f['freshness']=='immutable' and f['property']=='roster_species').update(value={'type':'text','data':'Gengar'}),'replay original value oracle')
    def old_proof(x,crosswalk=False):
        for kind in ['source','evidence','certificate']:
            existing={r['id'] for r in x['tables'][kind]}
            x['tables'][kind].extend(copy.deepcopy(r) for r in replay['tables'][kind] if r['id'] not in existing and (kind!='evidence' or r['scope']=='original'))
        cert=next(c for c in replay['tables']['certificate'] if c['property']=='roster_species')
        if crosswalk:
            next(s for s in x['tables']['starting'] if s['owner']=='p2')['crosswalk'][0]['certificate']=cert['id']
        else:
            next(f for f in x['tables']['fact'] if f['freshness']=='immutable' and f['property']=='roster_species')['certificate']=cert['id']
    reject('old-source-fact-certificate',fork,old_proof,'starting certificate source')
    reject('old-source-crosswalk-certificate',fork,lambda x:old_proof(x,True),'crosswalk certificate source')
    def strip_proof(x):
        next(f for f in x['tables']['fact'] if f['freshness']=='immutable' and f['property']=='roster_species').update(certificate=None,value={'type':'text','data':'Gengar'})
    reject('stripped-replay-certificate',fork,strip_proof,'replay original certificate')
    # Inert text equal to a lookup ID or a missing ID is never an edge.
    for form in ['full','ordinary','compact']:
        x=copy.deepcopy(cases['sim-'+form+'.json'])
        rows=list(x['tables']['fact'].values()) if form=='compact' else x['tables']['fact']
        next(f for f in rows if f['property']=='boundary_kind')['value']['data']=x['origin']
        x=A.reseal(x); add('inert-hash-'+form+'.json',x)
        assert any(f['value'] and f['value'].get('data')==x['origin'] for f in (x['tables']['fact'].values() if form=='compact' else x['tables']['fact']))
        selfcase=copy.deepcopy(cases['sim-'+form+'.json'])
        rows=list(selfcase['tables']['fact'].values()) if form=='compact' else selfcase['tables']['fact']
        f=next(f for f in rows if f['property']=='boundary_kind'); inert=f['id']; f['value']['data']=inert
        selfcase=A.reseal(selfcase)
        assert any(f['value'] and f['value'].get('data')==inert for f in (selfcase['tables']['fact'].values() if form=='compact' else selfcase['tables']['fact'])),'inert reseal bytes'
        add('inert-self-hash-'+form+'.json',selfcase)
    for text in ['audit_store restoration_handle full_replay_url','sha256:'+'e'*64]:
        x=copy.deepcopy(cases['sim-p1-consumer.json']); x['starting'][0]['value']['data']=text
        x.pop('id'); x=A.seal('projection',**{k:v for k,v in x.items() if k!='kind'})
        add('inert-'+('capability-words' if text.startswith('audit') else 'missing-hash')+'-consumer.json',x)
    # The inert string equals the ID of an unreachable added dictionary entry.
    for form in ['full','compact']:
        def orphan(x):
            new=A.seal('fact',**{k:v for k,v in x['tables']['fact'][0].items() if k not in ['kind','id']}|{'subject':'p1:roster:6'})
            x['tables']['fact'].append(new)
            next(f for f in x['tables']['fact'] if f['property']=='boundary_kind')['value']['data']=new['id']
        x=copy.deepcopy(sim); orphan(x); x=A.reseal(x)
        if form=='compact':
            x.pop('id'); x['form']='compact'; x['tables']={k:{v['id']:v for v in rows} for k,rows in x['tables'].items()}; x=A.seal('audit',**{k:v for k,v in x.items() if k!='kind'})
        name='negative-inert-orphan-'+form+'.json'; A.write(name,x)
        negative.append({'file':name,'required_profile':x['required_profile'],'expected':'contract_reject','fully_resealed':True,'rejection_code':'unreachable entry'})
    # Arrays of display data can also contain an ID equal to a real source ID.
    x=copy.deepcopy(cases['sim-p2-consumer.json']); x['starting'][0]['value']['data']=[sim['origin'],'audit_store']
    x.pop('id'); add('inert-array-consumer.json',A.seal('projection',**{k:v for k,v in x.items() if k!='kind'}))
    for name,mutate,code in [
      ('consumer-privileged-field',lambda p:p.update(audit_store='local-private-store'),'union mismatch'),
      ('consumer-nested-capability',lambda p:p['current'][0].update(restoration_handle='opaque'),'union mismatch'),
      ('consumer-foreign-starting',lambda p:p['starting'][0].update(subject='p2:roster:1'),'projection starting owner')]:
        x=copy.deepcopy(cases['sim-p1-consumer.json']); mutate(x); x.pop('id'); x=A.seal('projection',**{k:v for k,v in x.items() if k!='kind'})
        name='negative-'+name+'.json'; A.write(name,x)
        negative.append({'file':name,'required_profile':x['required_profile'],'expected':'contract_reject','fully_resealed':True,'rejection_code':code})
    value=''.join(chr(i) for i in range(32))+'"\\/É😀'
    assert json.loads(CONTROL_LITERAL)['s']==value
    # Build expected object-domain preimage from the reviewed literal, not encoder output.
    expected_object='{"battle_key":'+CONTROL_LITERAL[5:-1]+',"engine":"pokemon-showdown@0.11.10","format":"gen9randombattle","kind":"origin","rule_version":"pk-rules/v1"}'
    origin=A.seal('origin',battle_key=value,engine='pokemon-showdown@0.11.10',format='gen9randombattle',rule_version='pk-rules/v1')
    preimage='pk/v1/origin\n'+expected_object
    A.write('canonical-controls-vector.json',{'canonical_json_literal':CONTROL_LITERAL,'value':{'s':value},'object':origin,
       'object_canonical_literal':expected_object,'preimage_utf8_hex':preimage.encode('utf-8').hex(),'expected_id':'sha256:'+hashlib.sha256(preimage.encode('utf-8')).hexdigest()})
    A.write('case-manifest.json',positive); A.write('negative-manifest.json',negative)
    add_structural_cases(A)


def seal_subset(A,objects):
    byid={x['id']:x for x in objects}; done={}
    def visit(i):
        if i in done: return done[i]
        row=map_edges(byid[i],lambda ident,kind:visit(ident)['id'] if ident in byid else ident)
        done[i]=A.seal(row['kind'],**{k:v for k,v in row.items() if k not in ['id','kind']}); return done[i]
    return [visit(x['id']) for x in objects]


def add_structural_cases(A):
    origin=A.seal('origin',battle_key='PK-01R-ledger',format='gen9randombattle',engine='pokemon-showdown@0.11.10',rule_version='pk-rules/v1')
    representations=[]
    def case(name,ledger,property,key,value,state='known',reason='none',writer='layer-count/v1',precision='exact',subject='p1:side',owner='p1'):
        source=A.seal('source',origin=origin['id'],source_type='public_prefix',owner=None,provider='indexed-public/v1',delivery_seq=None,
          delivery_cursor=None,phase='chronological',team=[],records=ledger,raw_request=None)
        prefix=A.seal('prefix',origin=origin['id'],parser='indexed-public/v1',records=ledger)
        evidence=A.seal('evidence',origin=origin['id'],owner=None,scope='public',source=source['id'],prefix=prefix['id'],record_indices=list(range(len(ledger))),team_slot=None,writer=writer)
        fact=A.seal('fact',owner=owner,subject=subject,family='K13' if property=='side_condition_layers' else 'K14' if property=='field_remaining' else 'K15',property=property,
            effect_key=key,state=state,value=value,reason=reason,freshness='current',precision=precision,observed_at=len(ledger) if ledger else None,evidence=[evidence['id']] if ledger else [],certificate=None)
        row={'case':name,'context':'current','fact':fact['id'],'objects':[origin,source,prefix,evidence,fact],'aggregate':'incomplete','expected':'accept'}
        representations.append(row); return row
    spikes1=case('spikes-layer-one',['|-sidestart|p1: Éclair|Spikes'],'side_condition_layers','Spikes',{'type':'integer','data':1})
    spikes2=case('spikes-layer-two',['|-sidestart|p1: Éclair|Spikes','|-sidestart|p1: Éclair|Spikes'],'side_condition_layers','Spikes',{'type':'integer','data':2})
    case('toxic-spikes-two',['|-sidestart|p1: Éclair|move: Toxic Spikes']*2,'side_condition_layers','ToxicSpikes',{'type':'integer','data':2})
    case('layers-absent',['|-sideend|p1: Éclair|Spikes'],'side_condition_layers','Spikes',None,'known_absent')
    case('layers-unsupported',[],'side_condition_layers','Spikes',None,'unknown','unimplemented_family',precision='not_applicable')
    case('reflect-nonlayered',['|-sidestart|p1: Éclair|Reflect'],'side_condition_layers','Reflect',None,'inapplicable','proved_rule_inapplicable',precision='not_applicable')
    power=case('future-sight-base-power',['|move|p1a: Éclair|Future Sight|p2a: Beta','|-start|p1a: Éclair|move: Future Sight'],
       'pending_power','FutureSight',{'type':'power','data':{'basis':'base_move','amount':120}},writer='pending-base-power/v1',subject='p2:side')
    case('future-sight-effective-power-unknown',[],'pending_power','FutureSight',None,'unknown','unimplemented_family',writer='pending-base-power/v1',precision='not_applicable',subject='p2:side')
    timers=['|-weather|RainDance','|-weather|RainDance|[upkeep]','|-fieldstart|move: Electric Terrain']
    rain=case('weather-range',timers,'field_remaining','weather:RainDance',{'type':'field_timer','data':{'target_kind':'weather','name':'RainDance','remaining':{'min':4,'max':7}}},writer='field-timer-range/v1',precision='interval')
    terrain=case('terrain-range',timers,'field_remaining','terrain:ElectricTerrain',{'type':'field_timer','data':{'target_kind':'terrain','name':'ElectricTerrain','remaining':{'min':5,'max':8}}},writer='field-timer-range/v1',precision='interval')
    case('weather-exact-hidden',timers,'field_remaining','weather:RainDance',None,'unknown','hidden_timer',writer='field-timer-range/v1',precision='not_applicable')
    case('terrain-exact-hidden',timers,'field_remaining','terrain:ElectricTerrain',None,'unknown','hidden_timer',writer='field-timer-range/v1',precision='not_applicable')
    negative=[]
    def bad(name,base,change,code):
        row=copy.deepcopy(base); fact=next(x for x in row['objects'] if x['id']==row['fact']); oldid=fact['id']; change(fact)
        row['objects']=seal_subset(A,row['objects']); row['fact']=next(x['id'] for x in row['objects'] if x['kind']=='fact')
        row.update(case=name,expected='reject',rejection_code=code); negative.append(row)
    bad('wrong-layer-value',spikes2,lambda f:f.update(value={'type':'integer','data':1}),'layer ledger value')
    bad('wrong-layer-type',spikes1,lambda f:f.update(value={'type':'text','data':'1'}),'property value tag')
    bad('wrong-layer-identity',spikes2,lambda f:f.update(effect_key='ToxicSpikes'),'layer ledger identity')
    bad('wrong-layer-side',spikes2,lambda f:f.update(subject='p2:side'),'layer affected side')
    bad('layer-overflow',spikes1,lambda f:f.update(value={'type':'integer','data':4}),'layer bounds')
    bad('wrong-pending-power',power,lambda f:f['value']['data'].update(amount=80),'pending power oracle')
    bad('wrong-power-type',power,lambda f:f.update(value={'type':'integer','data':120}),'property value tag')
    bad('wrong-power-identity',power,lambda f:f.update(effect_key='Wish'),'pending power oracle')
    bad('wrong-power-recipient',power,lambda f:f.update(subject='p1:side'),'pending recipient')
    bad('unsupported-effective-power',power,lambda f:f['value']['data'].update(basis='effective_move'),'pending power oracle')
    bad('timer-cross-binding',rain,lambda f:f.update(effect_key='terrain:ElectricTerrain'),'timer target')
    bad('timer-wrong-range',rain,lambda f:f['value']['data']['remaining'].update(min=5,max=8),'timer ledger range')
    bad('timer-null-key',rain,lambda f:f.update(effect_key=None),'timer target')
    # Simultaneous timers are a separate context-key oracle.
    representations.append({'case':'simultaneous-timers','aggregate':'incomplete','expected':'accept','pair':[rain['case'],terrain['case']]})
    negative.append({'case':'timer-conflict','aggregate':'incomplete','expected':'reject','pair':[rain['case'],rain['case']],'rejection_code':'logical fact conflict'})
    A.write('representation-canaries.json',{'scope':'Independent source/rule structural subsets only; no runtime writer support','positive':representations,'negative':negative,
      'source_rules':{'Spikes':'moves.ts:18180-18190, maximum3','ToxicSpikes':'moves.ts:20526-20535, maximum2','FutureSight':'moves.ts:6615-6648, BASE power120 only',
                      'RainDance':'conditions.ts:472-482, duration5/8; one observed upkeep yields conservative4..7','ElectricTerrain':'moves.ts:4672-4680, duration5/8; no elapsed upkeep yields5..8'}})
    add_coverage_cases(A)


def add_coverage_cases(A):
    # Independent retained source universe; deleting facts never shrinks this table.
    universes={}
    cases=[]
    selected={'original':['roster_species','starting_moves'],'current':['party_position','current_moves','pp','max_pp','side_condition_layers','weather','pending_power'],
              'request':['pp','max_pp','maybe_trapped']}
    for owner in ['p1','p2']:
        roster=[owner+':roster:1',owner+':roster:2']
        moves=[r+':move:'+str(m)+':incarnation:0' for r in roster for m in [1,2]]
        other='p2' if owner=='p1' else 'p1'
        effects=[{'subject':side+':side','effect_key':n} for side in [owner,other] for n in ['Spikes','ToxicSpikes']]
        universe={'original':{'roster':roster},'current':{'roster':roster,'move':moves,'condition_effect':effects,
                  'weather_effect':[{'subject':owner+':side','effect_key':'RainDance'}],
                  'pending_effect_member':[{'subject':other+':side','effect_key':'FutureSight'}]},
                  'request':{'roster':[roster[0]],'move':moves[:2]}}
        universes[owner]=universe
        facts=[]
        for context,properties in selected.items():
            for prop in properties:
                selector='condition_effect' if prop=='side_condition_layers' else 'weather_effect' if prop=='weather' else 'pending_effect_member' if prop=='pending_power' else 'move' if prop in ['pp','max_pp'] else 'roster'
                for subject in universe[context][selector]:
                    key=None
                    if isinstance(subject,dict): key=subject['effect_key']; subject=subject['subject']
                    value={'type':'integer','data':1} if prop in ['party_position','side_condition_layers'] else {'type':'boolean','data':False} if prop=='maybe_trapped' else {'type':'texts','data':['Tackle','Protect']} if prop in ['starting_moves','current_moves'] else {'type':'text','data':'Pikachu'}
                    state='unknown' if prop in ['pp','max_pp','weather','pending_power'] else 'known'; reason='not_emitted' if state=='unknown' else 'none'
                    f=A.seal('fact',owner=owner,subject=subject,family=next(k for k,v in A.PROPERTIES.items() if prop in v),property=prop,effect_key=key,
                         state=state,value=None if state=='unknown' else value,reason=reason,freshness='immutable' if context=='original' else 'current',
                         precision='not_applicable' if state=='unknown' else 'exact',observed_at=None,evidence=[],certificate=None)
                    facts.append({'context':context,'fact':f})
        cases.append({'case':owner+'-two-roster-two-move-effects','owner':owner,'profile':A.PROFILES[2]['id'],'aggregate':'incomplete','selected':selected,'facts':facts,'expected':'accept'})
    negatives=[]
    def bad(name,change,code):
        x=copy.deepcopy(cases[0]); change(x); x.update(case=name,expected='reject',rejection_code=code); negatives.append(x)
    bad('erased-roster2',lambda x:x.update(facts=[r for r in x['facts'] if not r['fact']['subject'].startswith('p1:roster:2')]),'coverage missing subject')
    bad('erased-move2',lambda x:x.update(facts=[r for r in x['facts'] if ':move:2:' not in r['fact']['subject']]),'coverage missing subject')
    bad('erased-effect2',lambda x:x.update(facts=[r for r in x['facts'] if r['fact']['effect_key']!='ToxicSpikes']),'coverage missing subject')
    bad('missing-roster2-property',lambda x:x['facts'].remove(next(r for r in x['facts'] if r['context']=='current' and r['fact']['subject']=='p1:roster:2' and r['fact']['property']=='current_moves')),'coverage missing property')
    bad('wrong-context',lambda x:next(r for r in x['facts'] if r['fact']['property']=='starting_moves').update(context='current'),'property context')
    def sentinel(x):
        x['facts']=[r for r in x['facts'] if r['fact']['property']!='side_condition_layers']
        f=A.seal('fact',owner='p1',subject='p1:side',family='K13',property='side_condition_layers',effect_key=None,
            state='unknown',value=None,reason='unimplemented_family',freshness='current',precision='not_applicable',observed_at=None,evidence=[],certificate=None)
        x['facts'].append({'context':'current','fact':f})
    bad('collection-sentinel-not-members',sentinel,'coverage missing subject')
    # A sentinel inhabits the type but does not replace any required named member.
    from property_contexts import applies
    probe=copy.deepcopy(cases[0]['facts'][-1]['fact'])
    probe.update(subject='p1:side',property='side_condition',effect_key=None,state='unknown')
    assert applies(probe,'current'),'collection sentinel applicability'
    probe.update(state='known'); assert not applies(probe,'current'),'known collection forbidden'
    A.write('obligation-universe.json',{'status':'Independent fixture-only retained source inventory, not producer authority','owners':universes})
    A.write('obligation-canaries.json',{'scope':'Selected-property structural expansion only; all audit/profile aggregate verdicts remain incomplete','positive':cases,'negative':negatives})
