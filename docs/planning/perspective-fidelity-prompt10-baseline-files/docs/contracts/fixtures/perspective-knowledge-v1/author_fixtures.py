"""Hand-authored PK-01 oracles and wire shapes. No production imports.

Run only to reproduce checked-in contract examples; not a runtime producer.
"""
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).parent
OWNER = {'enum': ['p1', 'p2']}
TEXT = {'type': 'string', 'maxLength': 256}
ID = {'type': 'string', 'pattern': '^sha256:[0-9a-f]{64}$'}
INT = {'type': 'integer', 'minimum': 0, 'maximum': 2147483647}
BOOL = {'type': 'boolean'}
NULL = {'type': 'null'}
DEFS = {}


def ref(name):
    return {'$ref': '#/$defs/' + name}


def arr(items, limit=4096):
    return {'type': 'array', 'items': items, 'maxItems': limit}


def nullable(s):
    return {'anyOf': [s, NULL]}


def obj(fields):
    return {'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}


def enum(*values):
    return {'enum': list(values)}


def entity(kind, fields):
    DEFS[kind] = obj({'kind': {'const': kind}, 'id': ID, **fields})


def canonical(value):
    # All object keys ASCII; value strings are Unicode scalar sequences, no NFC.
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def seal(kind, **fields):
    if kind=='fact': fields.setdefault('effect_key',None)
    for key in ['facts','evidence','witnesses','writers','exclusions']:
        if key in fields: fields[key]=sorted(set(fields[key]))
    result = {'kind': kind, **fields}
    result['id'] = 'sha256:' + hashlib.sha256(('pk/v1/' + kind + '\n').encode() + canonical(result)).hexdigest()
    return result


REASONS = ['none', 'hidden_opponent', 'never_revealed', 'ambiguous_carrier', 'private_request_unavailable',
           'not_emitted', 'hidden_timer', 'missing_original_authority', 'unimplemented_family',
           'unsupported_writer', 'proved_rule_inapplicable']
FAMILIES = ['K%02d' % n for n in range(1, 21)]
PROPERTIES = {
 'K01': ['roster_species', 'roster_order', 'party_position', 'active_slot', 'roster_size'],
 'K02': ['starting_moves', 'current_moves', 'move_execution', 'move_incarnation'],
 'K03': ['submitted_nature', 'submitted_evs', 'submitted_ivs', 'submitted_happiness', 'calculated_stats', 'hp_max'],
 'K04': ['level', 'gender', 'shiny', 'ball', 'details', 'starting_tera'],
 'K05': ['hp', 'fainted', 'status'], 'K06': ['status_observed_since', 'status_elapsed', 'status_remaining'],
 'K07': ['pp', 'max_pp'], 'K08': ['disabled', 'maybe_disabled', 'trapped', 'maybe_trapped', 'lock'],
 'K09': ['boosts'], 'K10': ['persistent_effect'], 'K11': ['single_turn_effect'],
 'K12': ['single_move_effect'], 'K13': ['side_condition'],
 'K14': ['weather', 'weather_effective', 'terrain', 'pseudo_weather', 'field_remaining'],
 'K15': ['pending_intent', 'pending_effect'], 'K16': ['form', 'types', 'tera', 'transformed'],
 'K17': ['appearance', 'identity_reveal'], 'K18': ['item', 'item_held', 'item_effective'],
 'K19': ['ability', 'ability_effective'], 'K20': ['boundary_kind', 'request_presence'],
}
WRITERS=['submitted-set/v1','original-possession/v1','identity-replace/v1','boundary/v1','consumption/v1','raw-request/v1','terminal-requestless/v1','appearance/v1','calculated-owner-stats/v1','original-default/v1','side-condition-start/v1']
VALUE_TYPES={p:['text'] for p in sum(PROPERTIES.values(),[])}
for p in ['roster_order','party_position','active_slot','roster_size','hp_max','level','status_observed_since','status_elapsed','pp','max_pp','move_incarnation','submitted_happiness']: VALUE_TYPES[p]=['integer']
for p in ['shiny','fainted','disabled','maybe_disabled','trapped','maybe_trapped','weather_effective','transformed','item_held','item_effective','ability_effective','request_presence']: VALUE_TYPES[p]=['boolean']
for p in ['starting_moves','current_moves','types']: VALUE_TYPES[p]=['texts']
for p in ['submitted_evs','submitted_ivs']: VALUE_TYPES[p]=['six_stats']
VALUE_TYPES['calculated_stats']=['five_stats']; VALUE_TYPES['boosts']=['stages']; VALUE_TYPES['hp']=['integer','interval']
for p in ['status_remaining','field_remaining']: VALUE_TYPES[p]=['interval']
for p in ['persistent_effect','single_turn_effect','single_move_effect','side_condition','pending_intent','pending_effect','pseudo_weather']: VALUE_TYPES[p]=['effect']
SUBJECT={'type':'string','pattern':r'^p[12]:(side|roster:[1-6]|appearance:[1-9][0-9]*|roster:[1-6]:move:[1-4]:incarnation:[0-9]+)$'}
value_shapes = {
 'text': obj({'type': {'const': 'text'}, 'data': TEXT}),
 'integer': obj({'type': {'const': 'integer'}, 'data': INT}),
 'boolean': obj({'type': {'const': 'boolean'}, 'data': BOOL}),
 'texts': obj({'type': {'const': 'texts'}, 'data': arr(TEXT, 6)}),
 'six_stats': obj({'type': {'const': 'six_stats'}, 'data': obj({s: INT for s in ['hp','atk','def','spa','spd','spe']})}),
 'five_stats': obj({'type': {'const': 'five_stats'}, 'data': obj({s: INT for s in ['atk','def','spa','spd','spe']})}),
 'stages': obj({'type': {'const': 'stages'}, 'data': obj({s: {'type':'integer','minimum':-6,'maximum':6} for s in ['atk','def','spa','spd','spe','accuracy','evasion']})}),
 'interval': obj({'type': {'const': 'interval'}, 'data': obj({'min': INT, 'max': INT})}),
 'effect': obj({'type': {'const': 'effect'}, 'data': obj({'name': TEXT,'source_subject':nullable(SUBJECT),'observed_since':INT,'elapsed':nullable(INT),'remaining':nullable(obj({'type':{'const':'interval'},'data':obj({'min':INT,'max':INT})}))})}),
}
DEFS['value'] = {'anyOf': list(value_shapes.values())}
DEFS['set'] = obj({'slot': {'type':'integer','minimum':1,'maximum':6}, 'name':TEXT,'species':TEXT,
 'moves':arr(TEXT,4),'item':TEXT,'ability':TEXT,'tera_type':nullable(TEXT),'level':nullable(INT),
 'gender':nullable(enum('M','F','N')),'shiny':nullable(BOOL),'ball':nullable(TEXT),'nature':nullable(TEXT),
 'evs':nullable(value_shapes['six_stats']),'ivs':nullable(value_shapes['six_stats']), 'happiness':nullable(INT)})
entity('origin', {'battle_key':TEXT,'format':{'const':'gen9randombattle'},'engine':{'const':'pokemon-showdown@0.11.10'},'rule_version':{'const':'pk-rules/v1'}})
entity('source', {'origin':ID,'source_type':enum('owner_initialization','public_replay','public_prefix','owner_request'),
 'owner':nullable(OWNER),'provider':enum('addressed-team-provider/v1','indexed-public/v1','addressed-request/v1'),
 'delivery_seq':nullable(INT),'delivery_cursor':nullable(INT),'phase':enum('before_effects','chronological'),
 'team':arr(ref('set'),6),'records':arr(TEXT),'raw_request':nullable(obj({'json':{'type':'string','maxLength':65536}}))})
entity('prefix', {'origin':ID,'parser':{'const':'indexed-public/v1'},'records':arr(TEXT)})
entity('evidence', {'origin':ID,'owner':nullable(OWNER),'scope':enum('original','public','request'),
 'source':ID,'prefix':nullable(ID),'record_indices':arr(INT),'team_slot':nullable(INT),'writer':enum(*WRITERS)})
entity('certificate', {'owner':OWNER,'source':ID,'subject':SUBJECT,'property':enum(*sum(PROPERTIES.values(),[])),'witnesses':arr(ID),
 'scan_start':INT,'scan_end':INT,'writers':arr(enum(*WRITERS)),'continuity':enum('original_unmodified','ambiguous','unsupported'),
 'exclusions':arr(enum('transfer','copy','called','transform','acquisition','identity_ambiguity'),6)})
entity('fact', {'owner':OWNER,'subject':SUBJECT,'family':enum(*FAMILIES),'property':enum(*sum(PROPERTIES.values(),[])),
 'effect_key':nullable(TEXT),
 'state':enum('known','known_absent','unknown','inapplicable'),'value':nullable(ref('value')),
 'reason':enum(*REASONS),'freshness':enum('immutable','current','last_known'),
 'precision':enum('exact','public_bucket','interval','not_applicable'),'observed_at':nullable(INT),
 'evidence':arr(ID,32),'certificate':nullable(ID)})
DEFS['crosswalk'] = obj({'appearance':{'type':'string','pattern':r'^p[12]:appearance:[1-9][0-9]*$'},'roster':{'type':'string','pattern':r'^p[12]:roster:[1-6]$'},'certificate':ID})
entity('starting', {'origin':ID,'owner':OWNER,'policy':enum('simulator-causal/v1','public-replay-owner-starting/v1'),
 'source':nullable(ID),'revision':INT,'parent':nullable(ID),'facts':arr(ID),'crosswalk':arr(ref('crosswalk'),6)})
entity('current', {'origin':ID,'owner':OWNER,'prefix':ID,'cursor':INT,'parent':nullable(ID),'facts':arr(ID)})
entity('request', {'origin':ID,'owner':OWNER,'source':ID,'prefix':ID,'sequence':INT,'cursor':INT,'actionable':BOOL,'facts':arr(ID)})
entity('knowledge', {'origin':ID,'owner':OWNER,'policy':enum('simulator-causal/v1','public-replay-owner-starting/v1'),
 'starting':ID,'current':ID,'request':nullable(ID),'boundary':INT})
DEFS['obligation'] = obj({'family':enum(*FAMILIES),'properties':arr(TEXT,32),'unknown':arr(enum(*REASONS),10),
 'opponent_unknown':arr(enum(*REASONS),10),'inapplicable':arr(enum('proved_rule_inapplicable'),1),'original_required':BOOL})
entity('profile', {'name':enum('addressed-owner-evidence/v1','public-replay-owner-starting-evidence/v1','owner-loadout-complete/v1'),
 'policy':enum('simulator-causal/v1','public-replay-owner-starting/v1'),'engine':{'const':'pokemon-showdown@0.11.10'},
 'source_version':enum('addressed-team-provider/v1','indexed-public/v1'),'rule_version':{'const':'pk-rules/v1'},
 'writer_version':{'const':'pk-writers/v1'},'obligations':arr(ref('obligation'),20)})
DEFS['family_verdict'] = obj({'family':enum(*FAMILIES),'result':enum('supported_complete','permitted_unknown','proved_inapplicable','blocked','unsupported'),
 'reason':enum(*REASONS)})
entity('verdict', {'knowledge':ID,'profile':ID,'families':arr(ref('family_verdict'),20),
 'result':enum('evidence_relative_complete','strong_complete','incomplete','unsupported')})
DEFS['owner_binding'] = obj({'owner':OWNER,'knowledge':ID,'verdict':ID,'observation_id':ID,'belief_id':nullable(ID),'actor_record_id':nullable(ID)})
entity('boundary', {'origin':ID,'index':INT,'cursor':INT,'boundary_type':enum('initial','mid','wait','requestless','terminal','restored'),
 'parent':nullable(ID),'restored_from':nullable(ID),'bindings':arr(ref('owner_binding'),2)})
entity('binding', {'origin':ID,'owner':OWNER,'input_index':INT,'successor_index':INT,'input_knowledge':ID,'successor_knowledge':ID,
 'input_observation':ID,'successor_observation':ID,'input_belief':nullable(ID),'successor_belief':nullable(ID),
 'transition':nullable(ID),'actor_record':nullable(ID)})
KINDS = ['origin','source','prefix','evidence','certificate','fact','starting','current','request','knowledge','profile','verdict','boundary','binding']
DEFS['tables'] = obj({k:arr(ref(k)) for k in KINDS})
DEFS['compact_tables'] = obj({k:{'type':'object','propertyNames':ID,'additionalProperties':ref(k),'maxProperties':4096} for k in KINDS})
entity('audit', {'schema':{'const':'perspective-knowledge/v1'},'form':enum('ordinary','full','compact'),
 'origin':ID,'required_profile':ID,'target_boundary':ID,'tables':{'anyOf':[ref('tables'),ref('compact_tables')]}})
audit_fields=DEFS['audit']['properties']
DEFS['audit']={'anyOf':[obj({**audit_fields,'form':{'const':form},'tables':ref('compact_tables' if form=='compact' else 'tables')}) for form in ['ordinary','full','compact']]}
DEFS['safe_fact'] = obj({k:v for k,v in DEFS['fact']['properties'].items() if k not in ['kind','id','evidence','certificate']})
DEFS['safe_crosswalk'] = obj({k:v for k,v in DEFS['crosswalk']['properties'].items() if k!='certificate'})
DEFS['safe_request'] = obj({'sequence':INT,'cursor':INT,'actionable':BOOL,'facts':arr(ref('safe_fact'))})
entity('projection', {'schema':{'const':'perspective-knowledge-consumer/v1'},'owner':OWNER,'policy':enum('simulator-causal/v1','public-replay-owner-starting/v1'),
 'boundary':INT,'required_profile':ID,'result':enum('evidence_relative_complete','strong_complete','incomplete','unsupported'),
 'starting':arr(ref('safe_fact')),'starting_crosswalk':arr(ref('safe_crosswalk'),6),'current':arr(ref('safe_fact')),'request':nullable(ref('safe_request'))})
schema = {'$schema':'https://json-schema.org/draft/2020-12/schema','$defs':DEFS,
          'anyOf':[ref('audit'),ref('projection')]}


def write(name, data):
    (ROOT/name).write_bytes(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False).encode('utf-8')+b'\n')


def profile(name, replay=False, strong=False):
    unknown = ['hidden_opponent','hidden_timer','not_emitted']
    if replay: unknown += ['never_revealed','ambiguous_carrier','private_request_unavailable']
    return seal('profile',name=name,policy='public-replay-owner-starting/v1' if replay else 'simulator-causal/v1',
        engine='pokemon-showdown@0.11.10',source_version='indexed-public/v1' if replay else 'addressed-team-provider/v1',
        rule_version='pk-rules/v1',writer_version='pk-writers/v1',obligations=[{
         'family':f,'properties':PROPERTIES[f],'unknown':[] if strong and f in ['K01','K02','K03','K04','K18','K19'] else unknown,
         'opponent_unknown':['hidden_opponent','hidden_timer'],
         'inapplicable':['proved_rule_inapplicable'],'original_required':f in ['K01','K02','K03','K04','K18','K19']
        } for f in FAMILIES])


PROFILES = [profile('addressed-owner-evidence/v1'),profile('public-replay-owner-starting-evidence/v1',True),profile('owner-loadout-complete/v1',strong=True)]


def raw_request(owner,wait,pp=None,max_pp=None,maybe_trapped=None):
    raw={'side':{'id':owner,'pokemon':[]}}
    if wait: raw['wait']=True
    else:
        raw['active']=[{'moves':[{'id':'tackle','move':'Tackle','target':'normal','disabled':False}]}]
        move=raw['active'][0]['moves'][0]
        if pp is not None: move['pp']=pp
        if max_pp is not None: move['maxpp']=max_pp
        if maybe_trapped is not None: raw['active'][0]['maybeTrapped']=maybe_trapped
    return {'json':json.dumps(raw,ensure_ascii=False,separators=(',',':'))}


def make_case(replay=False, missing=False):
    tables = {k:[] for k in KINDS}
    def put(k,**v):
        x=seal(k,**v); tables[k].append(x); return x['id']
    origin=put('origin',battle_key='fixture-Éclair-😀',format='gen9randombattle',engine='pokemon-showdown@0.11.10',rule_version='pk-rules/v1')
    records=['|start','|switch|p1a: Éclair|Pikachu, L80|100/100','|switch|p2a: Beta|Gengar, L80|100/100',
             '|-enditem|p1a: Éclair|Oran Berry|[eat]','|move|p2a: Beta|Tackle|p1a: Éclair',
             '|replace|p2a: Beta|Zoroark, L80|100/100','|win|Éclair']
    prefix_ids=[put('prefix',origin=origin,parser='indexed-public/v1',records=records[:n]) for n in [0,3,4,5,7]]
    source_replay=put('source',origin=origin,source_type='public_replay',owner=None,provider='indexed-public/v1',delivery_seq=None,
                     delivery_cursor=None,phase='chronological',team=[],records=records,raw_request=None) if replay else None
    policy='public-replay-owner-starting/v1' if replay else 'simulator-causal/v1'
    chosen=PROFILES[1 if replay else 2]; tables['profile']=[chosen]
    stats={'hp':0,'atk':0,'def':0,'spa':0,'spd':0,'spe':0}
    starts={}; prev_current={}; prev_boundary=None
    for owner in ['p1','p2']:
        set_data={'slot':1,'name':'Éclair 😀' if owner=='p1' else 'Beta','species':'Pikachu' if owner=='p1' else 'Zoroark',
          'moves':['Tackle'],'item':'Oran Berry' if owner=='p1' else 'Leftovers','ability':'Static' if owner=='p1' else 'Illusion',
          'tera_type':'Electric' if owner=='p1' else 'Dark','level':80,'gender':None,'shiny':False,'ball':None,'nature':None,
          'evs':{'type':'six_stats','data':stats},'ivs':{'type':'six_stats','data':{k:31 for k in stats}},'happiness':None}
        src=None if missing else source_replay if replay else put('source',origin=origin,source_type='owner_initialization',owner=owner,
          provider='addressed-team-provider/v1',delivery_seq=0,delivery_cursor=0,phase='before_effects',team=[set_data],records=[],raw_request=None)
        ev=None if src is None else put('evidence',origin=origin,owner=owner,scope='original',source=src,prefix=None,
          record_indices=[3] if replay and owner=='p1' else [4] if replay else [],team_slot=1,writer='original-possession/v1' if replay else 'submitted-set/v1')
        cert=None
        if replay and ev:
            cert=put('certificate',owner=owner,source=src,subject=owner+':roster:1',property='item' if owner=='p1' else 'starting_moves',
                     witnesses=[ev],scan_start=0,scan_end=len(records),writers=['original-possession/v1'],continuity='original_unmodified',
                     exclusions=['transfer','copy','called','transform','acquisition','identity_ambiguity'])
        fact=put('fact',owner=owner,subject=owner+':roster:1',family='K18' if owner=='p1' else 'K02',property='item' if owner=='p1' else 'starting_moves',
          state='unknown' if missing else 'known',value=None if missing else {'type':'text','data':'Oran Berry'} if owner=='p1' else {'type':'texts','data':['Tackle']},
          reason='missing_original_authority' if missing else 'none',freshness='immutable',precision='not_applicable' if missing else 'exact',
          observed_at=None if missing else 4 if replay and owner=='p1' else 5 if replay else 0,evidence=[] if ev is None else [ev],certificate=cert)
        initialfacts=[fact]; initialsource=src
        if replay and owner=='p2':
            initialsource=put('source',origin=origin,source_type='public_replay',owner=None,provider='indexed-public/v1',delivery_seq=None,
              delivery_cursor=None,phase='chronological',team=[],records=records[:3]+['|win|Éclair'],raw_request=None)
            initialfacts=[put('fact',owner=owner,subject='p2:roster:1',family='K02',property='starting_moves',state='unknown',value=None,
              reason='never_revealed',freshness='immutable',precision='not_applicable',observed_at=None,evidence=[],certificate=None)]
        starts[owner]=put('starting',origin=origin,owner=owner,policy=policy,source=initialsource,revision=0,parent=None,facts=initialfacts,crosswalk=[])
        if replay and owner=='p2':
            xe=put('evidence',origin=origin,owner=owner,scope='original',source=src,prefix=None,record_indices=[5],team_slot=1,writer='identity-replace/v1')
            xc=put('certificate',owner=owner,source=src,subject='p2:roster:1',property='identity_reveal',witnesses=[xe],scan_start=0,scan_end=len(records),
              writers=['identity-replace/v1'],continuity='original_unmodified',exclusions=['transfer','copy','called','transform','acquisition','identity_ambiguity'])
            starts[owner]=put('starting',origin=origin,owner=owner,policy=policy,source=src,revision=1,parent=starts[owner],facts=[fact],
               crosswalk=[{'appearance':'p2:appearance:1','roster':'p2:roster:1','certificate':xc}])
    previous_bindings={}
    for index,typ in enumerate(['initial','mid','wait','requestless','terminal','restored']):
        cursor=[0,3,4,5,7,7][index]; pid=prefix_ids[[0,1,2,3,4,4][index]]
        public_src=put('source',origin=origin,source_type='public_prefix',owner=None,provider='indexed-public/v1',delivery_seq=None,
          delivery_cursor=None,phase='chronological',team=[],records=records[:cursor],raw_request=None)
        pe=put('evidence',origin=origin,owner=None,scope='public',source=public_src,prefix=pid,record_indices=[] if cursor==0 else [cursor-1],team_slot=None,writer='boundary/v1')
        binds=[]
        for owner in ['p1','p2']:
            # Explicit unsupported family is honest; these selected examples cannot claim completeness.
            facts=[put('fact',owner=owner,subject=owner+':side',family='K20',property='boundary_kind',state='known',
               value={'type':'text','data':typ},reason='none',freshness='current',precision='exact',observed_at=cursor,evidence=[pe],certificate=None)]
            facts.append(put('fact',owner=owner,subject=owner+':roster:1',family='K07',property='pp',state='unknown',value=None,
              reason='private_request_unavailable' if replay else 'not_emitted',freshness='current',precision='not_applicable',observed_at=None,evidence=[],certificate=None))
            if owner=='p1' and cursor>=4:
                ce=put('evidence',origin=origin,owner=None,scope='public',source=public_src,prefix=pid,record_indices=[3],team_slot=None,writer='consumption/v1')
                facts.append(put('fact',owner=owner,subject=owner+':appearance:1',family='K18',property='item',state='known_absent',value=None,
                  reason='none',freshness='current',precision='exact',observed_at=4,evidence=[ce],certificate=None))
            if replay and cursor>=3 and cursor<6:
                ae=put('evidence',origin=origin,owner=None,scope='public',source=public_src,prefix=pid,record_indices=[2],team_slot=None,writer='appearance/v1')
                facts.append(put('fact',owner=owner,subject='p2:appearance:1',family='K17',property='appearance',state='known',value={'type':'text','data':'Gengar'},
                  reason='none',freshness='current',precision='exact',observed_at=3,evidence=[ae],certificate=None))
            if typ in ['terminal','restored']:
                re=put('evidence',origin=origin,owner=None,scope='public',source=public_src,prefix=pid,record_indices=[6],team_slot=None,writer='terminal-requestless/v1')
                facts.append(put('fact',owner=owner,subject=owner+':side',family='K20',property='request_presence',state='inapplicable',value=None,
                  reason='proved_rule_inapplicable',freshness='current',precision='not_applicable',observed_at=cursor,evidence=[re],certificate=None))
            if index>=2 and not replay:
                facts.append(put('fact',owner=owner,subject=owner+':roster:1:move:1:incarnation:0',family='K07',property='max_pp',state='known',
                 value={'type':'integer','data':56},reason='none',freshness='last_known',precision='exact',observed_at=3,evidence=[],certificate=None))
                # Stale value proof is supplied by an actual preceding addressed delivery.
                oldsrc=put('source',origin=origin,source_type='owner_request',owner=owner,provider='addressed-request/v1',delivery_seq=1,
                   delivery_cursor=3,phase='chronological',team=[],records=[],raw_request=raw_request(owner,False,0,56,True))
                oldev=put('evidence',origin=origin,owner=owner,scope='request',source=oldsrc,prefix=prefix_ids[1],record_indices=[],team_slot=1,writer='raw-request/v1')
                old=tables['fact'].pop(); old.pop('id'); old['evidence']=[oldev]; oldid=put('fact',**{k:v for k,v in old.items() if k!='kind'}); facts[-1]=oldid
            current=put('current',origin=origin,owner=owner,prefix=pid,cursor=cursor,parent=prev_current.get(owner),facts=sorted(facts)); prev_current[owner]=current
            request=None
            if not replay and typ in ['initial','mid','wait']:
                raw=raw_request(owner,typ=='wait',0 if typ=='mid' else None,56 if typ=='mid' else None,True if typ=='mid' else None)
                rs=put('source',origin=origin,source_type='owner_request',owner=owner,provider='addressed-request/v1',delivery_seq=index,delivery_cursor=cursor,
                  phase='chronological',team=[],records=[],raw_request=raw)
                rf=[]
                if typ=='mid':
                    er=put('evidence',origin=origin,owner=owner,scope='request',source=rs,prefix=pid,record_indices=[],team_slot=1,writer='raw-request/v1')
                    for prop,val in [('pp',{'type':'integer','data':0}),('max_pp',{'type':'integer','data':56}),('maybe_trapped',{'type':'boolean','data':True})]:
                        rf.append(put('fact',owner=owner,subject=owner+':roster:1:move:1:incarnation:0',family='K08' if prop=='maybe_trapped' else 'K07',property=prop,
                           state='known',value=val,reason='none',freshness='current',precision='exact',observed_at=cursor,evidence=[er],certificate=None))
                request=put('request',origin=origin,owner=owner,source=rs,prefix=pid,sequence=index,cursor=cursor,actionable=typ!='wait',facts=sorted(rf))
            knowledge=put('knowledge',origin=origin,owner=owner,policy=policy,starting=starts[owner],current=current,request=request,boundary=index)
            verdict=put('verdict',knowledge=knowledge,profile=chosen['id'],families=[{'family':f,'result':'unsupported','reason':'unimplemented_family'} for f in FAMILIES],result='incomplete')
            binds.append({'owner':owner,'knowledge':knowledge,'verdict':verdict,'observation_id':'sha256:'+hashlib.sha256(('legacy-'+owner+'-'+str(index)).encode()).hexdigest(),
              'belief_id':None,'actor_record_id':None})
            if owner in previous_bindings:
                old=previous_bindings[owner]; new=binds[-1]
                put('binding',origin=origin,owner=owner,input_index=index-1,successor_index=index,input_knowledge=old['knowledge'],successor_knowledge=knowledge,
                    input_observation=old['observation_id'],successor_observation=new['observation_id'],input_belief=old['belief_id'],successor_belief=new['belief_id'],transition=None,actor_record=None)
            previous_bindings[owner]=binds[-1]
        prev_boundary=put('boundary',origin=origin,index=index,cursor=cursor,boundary_type=typ,parent=prev_boundary,
          restored_from=prev_boundary if typ=='restored' else None,bindings=binds)
    # Deduplicate content-addressed entries, deterministic lexical ID ordering.
    tables={k:sorted({x['id']:x for x in xs}.values(),key=lambda x:x['id']) for k,xs in tables.items()}
    return seal('audit',schema='perspective-knowledge/v1',form='full',origin=origin,required_profile=chosen['id'],target_boundary=prev_boundary,tables=tables)


def projection(audit,owner,boundary_index=None):
    t={k:{x['id']:x for x in v} for k,v in audit['tables'].items()}
    b=t['boundary'][audit['target_boundary']] if boundary_index is None else next(x for x in t['boundary'].values() if x['index']==boundary_index)
    binding=next(x for x in b['bindings'] if x['owner']==owner)
    k=t['knowledge'][binding['knowledge']]; s=t['starting'][k['starting']]; c=t['current'][k['current']]
    def safe(fid): return {key:v for key,v in t['fact'][fid].items() if key not in ['kind','id','evidence','certificate']}
    return seal('projection',schema='perspective-knowledge-consumer/v1',owner=owner,policy=k['policy'],boundary=b['index'],
      required_profile=audit['required_profile'],result='incomplete',starting=[safe(f) for f in s['facts']],
      starting_crosswalk=[{'appearance':x['appearance'],'roster':x['roster']} for x in s['crosswalk']],current=[safe(f) for f in c['facts']],
      request=None if k['request'] is None else {key:t['request'][k['request']][key] for key in ['sequence','cursor','actionable']} | {'facts':[safe(f) for f in t['request'][k['request']]['facts']]})


def reseal(a):
    """Fixture-only DAG resealer. Values/authority oracles are not derived here."""
    a=copy.deepcopy(a)
    compact=a['form']=='compact'
    tables={k:list(rows.values()) if isinstance(rows,dict) else rows for k,rows in a['tables'].items()}
    old={x['id']:x for rows in tables.values() for x in rows}
    done={}; visiting=set()
    def rewrite(value):
        if isinstance(value,str) and value in old: return visit(value)['id']
        if isinstance(value,list): return [rewrite(v) for v in value]
        if isinstance(value,dict): return {k:rewrite(v) for k,v in value.items()}
        return value
    def visit(i):
        if i in done: return done[i]
        assert i not in visiting,'fixture cycle'; visiting.add(i)
        fields={k:rewrite(v) for k,v in old[i].items() if k not in ['id','kind']}
        x=seal(old[i]['kind'],**fields); visiting.remove(i); done[i]=x; return x
    newtables={k:sorted({visit(x['id'])['id']:visit(x['id']) for x in rows}.values(),key=lambda x:x['id']) for k,rows in tables.items()}
    fields={k:rewrite(v) for k,v in a.items() if k not in ['id','kind','tables']}
    fields['tables']={k:{x['id']:x for x in rows} for k,rows in newtables.items()} if compact else newtables
    return seal('audit',**fields)


def main():
    write('schema.json',schema); write('profiles.json',PROFILES)
    write('property-types.json',VALUE_TYPES)
    sim=make_case(); replay=make_case(True); missing=make_case(missing=True)
    origin=sim['tables']['origin'][0]
    ledger=['|start','|-sidestart|p1: Éclair|Reflect','|-sidestart|p1: Éclair|Spikes']
    prefix=seal('prefix',origin=origin['id'],parser='indexed-public/v1',records=ledger)
    source=seal('source',origin=origin['id'],source_type='public_prefix',owner=None,provider='indexed-public/v1',delivery_seq=None,
      delivery_cursor=None,phase='chronological',team=[],records=ledger,raw_request=None)
    effect_objects=[origin,prefix,source]
    for owner in ['p1','p2']:
        facts=[]
        for index,name in [(1,'Reflect'),(2,'Spikes')]:
            evidence=seal('evidence',origin=origin['id'],owner=None,scope='public',source=source['id'],prefix=prefix['id'],record_indices=[index],team_slot=None,writer='side-condition-start/v1')
            fact=seal('fact',owner=owner,subject='p1:side',family='K13',property='side_condition',effect_key=name,state='known',
              value={'type':'effect','data':{'name':name,'source_subject':None,'observed_since':index+1,'elapsed':None,'remaining':None}},
              reason='none',freshness='current',precision='exact',observed_at=index+1,evidence=[evidence['id']],certificate=None)
            effect_objects += [evidence,fact]; facts.append(fact['id'])
        effect_objects.append(seal('current',origin=origin['id'],owner=owner,prefix=prefix['id'],cursor=3,parent=None,facts=facts))
    write('effect-collection-canary.json',{'status':'Hand-authored structural/proof subset only. Relevant family unsupported; no complete audit/production acceptance.',
      'objects':list({x['id']:x for x in effect_objects}.values()),'expected_names':['Reflect','Spikes']})
    cases={'sim-full.json':sim,'replay-full.json':replay,'missing-original-full.json':missing}
    effects=copy.deepcopy(sim)
    for s in effects['tables']['source']:
        if s['source_type']=='public_prefix' and len(s['records'])>=3: s['records'][1:3]=ledger[1:3]
    for p in effects['tables']['prefix']:
        if len(p['records'])>=3: p['records'][1:3]=ledger[1:3]
    for x in effect_objects:
        if x['kind'] in ['source','prefix','evidence','fact']: effects['tables'][x['kind']].append(x)
    for c in effects['tables']['current']:
        if c['cursor']==3:
            c['facts'] += [f['id'] for f in effect_objects if f['kind']=='fact' and f['owner']==c['owner']]
    effects=reseal(effects); cases['sim-concurrent-effects-full.json']=effects
    for label,original in [('sim',sim),('replay',replay)]:
        for form in ['ordinary','compact']:
            x=copy.deepcopy(original); x.pop('id'); x['form']=form
            if form=='compact': x['tables']={k:{v['id']:v for v in xs} for k,xs in x['tables'].items()}
            cases[label+'-'+form+'.json']=seal('audit',**{k:v for k,v in x.items() if k!='kind'})
        for owner in ['p1','p2']: cases[label+'-'+owner+'-consumer.json']=projection(original,owner)
    cases['sim-p1-actionable-consumer.json']=projection(sim,'p1',1)
    cases['sim-p1-wait-consumer.json']=projection(sim,'p1',2)
    suffix=copy.deepcopy(replay)
    for s in suffix['tables']['source']:
        if s['source_type']=='public_replay' or len(s['records'])==7: s['records'][-1]='|win|Beta'
    for p in suffix['tables']['prefix']:
        if len(p['records'])==7: p['records'][-1]='|win|Beta'
    cases['replay-suffix-full.json']=reseal(suffix)
    for name,data in cases.items(): write(name,data)
    vectors=[]
    for kind,rows in sim['tables'].items():
        if rows:
            x=rows[0]; payload={k:v for k,v in x.items() if k!='id'}
            vectors.append({'kind':kind,'id':x['id'],'preimage_utf8_hex':(('pk/v1/'+kind+'\n').encode()+canonical(payload)).hex()})
    for x in [sim,cases['sim-p1-consumer.json']]:
        vectors.append({'kind':x['kind'],'id':x['id'],'preimage_utf8_hex':(('pk/v1/'+x['kind']+'\n').encode()+canonical({k:v for k,v in x.items() if k!='id'})).hex()})
    cert=replay['tables']['certificate'][0]
    vectors.append({'kind':'certificate','id':cert['id'],'preimage_utf8_hex':(('pk/v1/certificate\n').encode()+canonical({k:v for k,v in cert.items() if k!='id'})).hex()})
    allobjects={x['id']:x for a in [sim,replay] for rows in a['tables'].values() for x in rows}
    allobjects.update({x['id']:x for x in [sim,cases['sim-p1-consumer.json']]})
    for v in vectors: v['object']=allobjects[v['id']]
    write('identity-vectors.json',vectors)
    write('case-manifest.json',{'positive':list(cases),'note':'Contract fixtures, not production semantic acceptance. Legacy binding IDs are isolated opaque vector stand-ins, not valid old observation/record fixtures.'})
    write('trusted-fixture-authority.json',{'origins':[x['id'] for x in sim['tables']['origin']],
      'delivered_sources':sorted({s['id'] for a in [sim,replay] for s in a['tables']['source'] if s['source_type'] in ['owner_initialization','owner_request']}),
      'meaning':'Independent local fixture oracle ONLY. Imported transport cannot nominate or alter this authority registry.'})
    negatives=[]
    def negative(name,mutate,base=sim,compact=False):
        a=copy.deepcopy(base); mutate(a)
        # Shape-negative and semantic-negative payloads both retain valid digest closure.
        a=reseal(a)
        if compact:
            a.pop('id'); a['form']='compact'; a['tables']={k:{x['id']:x for x in rows} for k,rows in a['tables'].items()}; a=seal('audit',**{k:v for k,v in a.items() if k!='kind'})
        filename='negative-'+name+'.json'; write(filename,a)
        negatives.append({'file':filename,'required_profile':base['required_profile'],'expected':'contract_reject','fully_resealed':True})
    negative('missing-key',lambda a:a['tables']['current'][0].pop('cursor'))
    negative('extra-key',lambda a:a.update(unexpected=True))
    negative('wrong-type',lambda a:a['tables']['current'][0].update(cursor='0'))
    negative('wrong-discriminant',lambda a:a.update(form='invalid'))
    # Duplicate kept after resealing (resealer normally deduplicates equal-content rows).
    duplicate=copy.deepcopy(sim); duplicate['tables']['fact'].append(copy.deepcopy(duplicate['tables']['fact'][0])); duplicate.pop('id'); duplicate=seal('audit',**{k:v for k,v in duplicate.items() if k!='kind'})
    write('negative-duplicate.json',duplicate); negatives.append({'file':'negative-duplicate.json','required_profile':sim['required_profile'],'expected':'contract_reject','fully_resealed':True})
    negative('dangling-reference',lambda a:a['tables']['current'][0]['facts'].append('sha256:'+'f'*64))
    negative('wrong-owner',lambda a:next(e for e in a['tables']['evidence'] if e['scope']=='request').update(owner='p2' if next(e for e in a['tables']['evidence'] if e['scope']=='request')['owner']=='p1' else 'p1'))
    negative('wrong-policy',lambda a:a['tables']['knowledge'][0].update(policy='public-replay-owner-starting/v1'))
    negative('wrong-source',lambda a:next(e for e in a['tables']['evidence'] if e['scope']=='public').update(source=next(s['id'] for s in a['tables']['source'] if s['source_type']=='public_replay')),replay)
    negative('broken-origin',lambda a:a['tables']['knowledge'][0].update(origin='sha256:'+'f'*64))
    negative('broken-parent',lambda a:next(c for c in a['tables']['current'] if c['parent'] is not None).update(parent=None))
    negative('broken-request',lambda a:a['tables']['request'][0].update(sequence=99))
    negative('broken-history',lambda a:a['tables']['binding'][0].update(input_observation='sha256:'+'f'*64))
    negative('authority-label-forgery',lambda a:next(s for s in a['tables']['source'] if s['source_type']=='owner_initialization')['team'][0].update(name='Forged'))
    def weaker(a):
        old=a['tables']['profile'][0]['id']; replacement=PROFILES[0]; a['tables']['profile']=[replacement]; a['required_profile']=replacement['id']
        for v in a['tables']['verdict']: v['profile']=replacement['id']
    negative('weaker-profile',weaker)
    negative('dishonest-unknown',lambda a:next(f for f in a['tables']['fact'] if f['property']=='pp' and f['state']=='unknown').update(reason='hidden_opponent'))
    negative('dishonest-inapplicable',lambda a:next(f for f in a['tables']['fact'] if f['property']=='pp' and f['state']=='unknown').update(state='inapplicable',reason='proved_rule_inapplicable'))
    negative('false-item',lambda a:next(f for f in a['tables']['fact'] if f['state']=='known_absent').update(state='known',value={'type':'text','data':'Leftovers'}))
    negative('compact-private-traversal',lambda a:next(f for f in a['tables']['fact'] if f['freshness']=='current').update(certificate=a['tables']['certificate'][0]['id']),replay,True)
    negative('compact-future-traversal',lambda a:next(e for e in a['tables']['evidence'] if e['scope']=='public' and not e['record_indices']).update(record_indices=[5]),replay,True)
    negative('unsupported-complete',lambda a:a['tables']['verdict'][0].update(result='strong_complete'))
    negative('crosswalk-chronological-relabel',lambda a:next(f for f in a['tables']['fact'] if f['property']=='appearance').update(subject='p2:roster:1'),replay)
    negative('crosswalk-foreign-owner',lambda a:next(s for s in a['tables']['starting'] if s['crosswalk'])['crosswalk'][0].update(appearance='p1:appearance:1'),replay)
    negative('starting-revision-fork',lambda a:next(s for s in a['tables']['starting'] if s['parent'] is not None).update(revision=7),replay)
    negative('false-original-value',lambda a:next(f for f in a['tables']['fact'] if f['freshness']=='immutable' and f['property']=='item').update(value={'type':'text','data':'Leftovers'}))
    negative('certificate-property',lambda a:a['tables']['certificate'][0].update(property='ability'),replay)
    negative('foreign-original-source',lambda a:next(e for e in a['tables']['evidence'] if e['scope']=='original' and e['owner']=='p1').update(source=next(s['id'] for s in a['tables']['source'] if s['source_type']=='owner_initialization' and s['owner']=='p2')))
    negative('wrong-value-tag',lambda a:next(f for f in a['tables']['fact'] if f['property']=='pp' and f['state']=='known').update(value={'type':'text','data':'0'}))
    negative('wrong-effect-identity',lambda a:next(f for f in a['tables']['fact'] if f['property']=='side_condition').update(effect_key='Wrong'),effects)
    def ranged_future(a):
        e=next(e for e in a['tables']['evidence'] if e['scope']=='public' and not e['record_indices'])
        e['source']=next(s['id'] for s in a['tables']['source'] if s['source_type']=='public_replay'); e['record_indices']=[5]
    negative('in-range-future-source',ranged_future,replay,True)
    orphan=copy.deepcopy(sim); x=seal('fact',**{k:v for k,v in orphan['tables']['fact'][0].items() if k not in ['kind','id']} | {'subject':'p1:roster:6'})
    orphan['tables']['fact'].append(x); negative('unreachable-entry',lambda a:a['tables']['fact'].append(x))
    codes={
      'missing-key':'union mismatch','extra-key':'union mismatch','wrong-type':'union mismatch','wrong-discriminant':'union mismatch',
      'duplicate':'table duplicate/order','dangling-reference':'dangling/wrong reference','wrong-owner':'request proof',
      'wrong-policy':'knowledge join','wrong-source':'public future traversal','broken-origin':'knowledge join','broken-parent':'current parent/cursor',
      'broken-request':'request delivery join','broken-history':'history/legacy binding join','authority-label-forgery':'source-label authority forgery',
      'weaker-profile':'weaker profile','dishonest-unknown':'dishonest unknown','dishonest-inapplicable':'dishonest inapplicable',
      'false-item':'false consumed item','compact-private-traversal':'current fact/certificate','compact-future-traversal':'record range',
      'unsupported-complete':'unsupported completeness promotion','crosswalk-chronological-relabel':'causal appearance oracle',
      'crosswalk-foreign-owner':'crosswalk owner','starting-revision-fork':'revision join','false-original-value':'original value oracle',
      'certificate-property':'certificate property/subject','foreign-original-source':'original source owner','wrong-value-tag':'property value tag',
      'in-range-future-source':'public future traversal','unreachable-entry':'unreachable entry','wrong-effect-identity':'effect identity'}
    for row in negatives: row['rejection_code']=codes[row['file'][9:-5]]
    write('negative-manifest.json',negatives)


if __name__=='__main__': main()
