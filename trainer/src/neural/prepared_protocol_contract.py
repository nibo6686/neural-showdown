"""Full fixed-profile PRE contract validation; inspection never creates authority."""
import copy
import math
from .protocol_contract import validate_protocol_contract, validate_protocol_record, ProtocolContractError, _same_json
from .version_profile import assert_prepared_inspection_available, assert_prepared_record_check_input, _freeze, HISTORICAL10_CONTEXT, NATIVE11_GRAMMAR_CONTEXT, REPLAY_COMPAT_CONTEXT
SCOPE='PRE grammar only; no native runtime, semantic closure or publication acceptance'
FRAMING='Historical separator shape reused for PRE grammar; target emission UNEXECUTED'
OLD_NC='|-curestatus|p2a: Blissey|par|[from] ability: Natural Cure'
NATIVE_NC=OLD_NC+'|[silent]'
COMMON_STOPS={'heal','cant','-swapsideconditions'}
NATIVE_STOPS={'-start','-end','-weather','-fieldstart','-fieldend','-sidestart','-sideend'}
PROVENANCE={'historical_contract_sha256':'4cbea57639e3a5d11e8387f9f84befcc531a613b13175351630b4377d087c213',
 'old_abilities_sha256':'7975eb69496fb38ec8c9f2d7288dedea14e78ec81579f6e2b58ad1c9716d3ce6','target_abilities_sha256':'175067b1e827ca11ae4728169215c9bdd27ac4cb3e35d2e83eaaaee7e9e8c842',
 'target_revision':'739a5e1fee432ad80ff7136d70cca993be358b59','source':'Prompt29 verified npm artifacts; abilities.ts old onSwitchOut and target 2868–2875; ordinary add routes shared/public','runtime':'UNEXECUTED'}
SEMANTIC={'natural_cure':'prepared-status-clear-existing-helper-path','ability_setter':'unsupported-unproved-typed-base-current-transition',
 'heal_failure':'unsupported-unproved-attribution-routing','chilly_reception':'unsupported-premajor-helper-gap','partial_trap':'unsupported-sourceEffect-semantics',
 'court_change':'unsupported-retargeted-lifecycle','magician':'unsupported-actor-source-attribution','psychic_terrain_hint':'raw-only-presentation-no-typed-consequence',
 'effect_lifecycle':'unsupported-target-closure-unproved','admin_nonselected':'unsupported-existing-stop'}
def _fail(code):raise ProtocolContractError('prepared-protocol-contract/v1/'+code)
def _keys(v,expected,label):
    if type(v) is not dict or set(v)!=set(expected):_fail(label+'-keys')
def _plain(v,active=None):
    if v is None or type(v) in (str,bool) or type(v) in (int,float) and math.isfinite(v):return
    if type(v) not in (dict,list):_fail('plain-json')
    active=set() if active is None else active
    if id(v) in active:_fail('plain-json')
    active.add(id(v))
    if type(v) is dict:
        if any(type(k) is not str for k in v):_fail('plain-json')
        children=v.values()
    else:children=v
    for child in children:_plain(child,active)
    active.remove(id(v))
def _thaw(v):
    from collections.abc import Mapping
    if isinstance(v,Mapping):return {k:_thaw(x) for k,x in v.items()}
    if isinstance(v,tuple):return [_thaw(x) for x in v]
    return v

def validate_prepared_protocol_structure(value,profile):
    if profile not in ('native11','replay-compat-v1'):_fail('profile')
    _plain(value)
    common=['schema_version','profile','adopted','provenance','protocol','inherited_raw_shape_evidence']
    _keys(value,common+(['admission_scope','semantic_dispositions'] if profile=='native11' else ['base_lookup_profile','publication','authority','changed_forms']),'container')
    if value['profile']!=profile or value['adopted'] is not False or value['schema_version']!=('inactive-native-protocol/v1' if profile=='native11' else 'importer-replay-compatibility/v1'):_fail('profile-identity')
    selected_provenance={**PROVENANCE,'target_revision':'b8f23c99629132611ba59e99480cb148ea8c5d3d','target_abilities_sha256':'52298a24ba0fa5b33750455042ce1b8d66a14d95250368f15cbdd96b356b6796','engine_integrity':'sha512-ihktUZgY1oy6U7TyCDmHg4lUlPeMb2jcedhqOnc/R0GIAeMgMFTlIDzmVsZ1xjBJ4ddaa/OM8dpfNsqo1dNe3Q==','source':'P0.4 pinned compiled abilities and gen9 set inputs; inherited finite Natural Cure, Trace and Revival grammar','runtime':'Prompt41 Trace and Prompt42 finite Revival native integration checks; broader runtime closure unproved'} if profile=='native11' else PROVENANCE
    if not _same_json(value['provenance'],selected_provenance):_fail('provenance')
    if not _same_json(value['inherited_raw_shape_evidence'],{'contract_sha256':PROVENANCE['historical_contract_sha256'],'scope':'Historical raw rule baseline; fresh PRE fixture checks, no target acceptance'}):_fail('inherited-evidence')
    if profile=='native11':
        if not _same_json(value['admission_scope'],['Inherited historical raw-shape baseline, not semantic acceptance','Natural Cure exact ordered source-tag then silent','Trace exact prior-Trace positional field and opposing active source','Revival Blessing exact public bench 50/100 heal; silent faint/status clear']) or not _same_json(value['semantic_dispositions'],{**SEMANTIC,'trace':'finite-source-qualified-current-copy; prior field is provenance only','revival':'finite-public-bench-health-status-faint-clear; owned selection remains required'}):_fail('closure-claims')
    elif value['base_lookup_profile']!='historical10' or value['publication']!='unsupported-without-persisted-profile-contract' or value['authority'] is not False or not _same_json(value['changed_forms'],['Natural Cure historical ordered from-tag','Natural Cure native11 ordered from-tag then silent']):_fail('closure-claims')
    base=_thaw(HISTORICAL10_CONTEXT.protocol);p=value['protocol'];_keys(p,base,'protocol')
    if p['source_basis']!=['Historical raw rule templates and Prompt29 Natural Cure; Prompt41 source-qualified target Trace; only finite Trace emitter/audience and owned publication controls executed, broader closure unproved; Prompt42 finite public Revival bench heal' if profile=='native11' else 'Historical raw rule templates and Prompt29 exact Natural Cure writer; PRE only, runtime/publication UNEXECUTED']:_fail('source-claims')
    if not _same_json(p['simulator'],{**base['simulator'],'version':'0.11.11' if profile=='native11' else '0.11.10',**({'engine_commit':'b8f23c99629132611ba59e99480cb148ea8c5d3d'} if profile=='native11' else {})}):_fail('simulator')
    rules=copy.deepcopy(base['validation_rules']);form={'tags':['[from] ability: Natural Cure','[silent]']}
    if profile=='native11':rules['major_status']['cure_forms']=[form if x['tags']==['[from] ability: Natural Cure'] else x for x in rules['major_status']['cure_forms']]
    else:rules['major_status']['cure_forms'].append(form)
    if profile=='native11':
        rules['ability']['dash_templates']=['reveal','boost','trace-copy-prior-Trace']
        rules['ability']['payload_domains']['dash_trace_copy']=sorted([a for a in rules['ability']['payload_domains']['dash_trace_copy'] if a!='Steely Spirit']+['Gale Wings'])
        rules['ability']['source_evidence']['dash_trace_copy']='Target 0.11.11 gen9 sets candidate abilities filtered by target Trace notrace/noability guard; Gardevoir sole Trace selector; Prompt41 finite source qualification'
    if not _same_json(p['validation_rules'],rules):_fail('rule-template')
    if not _same_json(p['framing_only_records'],[{**base['framing_only_records'][0],'evidence':FRAMING}]):_fail('framing')
    if not _same_json(p['disposition_rules'],{k:SCOPE for k in base['disposition_rules']}):_fail('disposition-claims')
    stops=COMMON_STOPS|(NATIVE_STOPS if profile=='native11' else set());wanted=[t for t in base['supported_commands'] if t not in stops]
    if type(p['supported_commands']) is not list or any(type(t) is not str for t in p['supported_commands']) or sorted(p['supported_commands'])!=sorted(wanted):_fail('token-partition')
    if type(p['recognized_unsupported_commands']) is not list:_fail('unsupported-entries')
    expected={x['token']:x['kind'] for x in base['recognized_unsupported_commands']};expected['swapsideconditions']='unproved_semantic_family'
    for token in stops:expected[token]='unproved_semantic_family'
    actual={}
    for x in p['recognized_unsupported_commands']:
        if type(x) is not dict or type(x.get('token')) is not str or x['token'] in actual or x.get('kind')!=expected.get(x['token']):_fail('unsupported-classification')
        actual[x['token']]=x['kind']
    if actual.keys()!=expected.keys():_fail('token-partition')
    entries={x['token']:x for x in base['recognized_unsupported_commands']}
    for token in stops:entries[token]={'token':token,'kind':'unproved_semantic_family','reason':'Prepared profile rejects this token; semantic/runtime closure unproved'}
    entries['swapsideconditions']={'token':'swapsideconditions','kind':'unproved_semantic_family','reason':'Prepared Court Change family quarantine, including bare alias'}
    for x in p['recognized_unsupported_commands']:
        if not _same_json(x,entries[x['token']]):_fail('unsupported-evidence')

    projection=copy.deepcopy(p);projection['simulator']=base['simulator'];projection['validation_rules']=base['validation_rules'];projection['framing_only_records']=base['framing_only_records']
    for x in projection['recognized_unsupported_commands']:
        if x['kind']=='unproved_semantic_family':x['kind']='unsupported_stop'
    if type(p['rejection_fixtures']) is not list:_fail('negative-controls')
    for i,x in enumerate(p['rejection_fixtures']):
        if type(x) is not dict:_fail('negative-controls')
        if x.get('kind')=='unproved_semantic_family':
            token=x.get('record','').split('|')[1] if type(x.get('record')) is str and '|' in x['record'] else ''
            if token not in wanted and actual.get(token)!='unproved_semantic_family':_fail('negative-classification')
            projection['rejection_fixtures'][i]['kind']='malformed' if token in wanted else 'unsupported_stop'
    try:validate_protocol_contract(projection)
    except ProtocolContractError as e:_fail('protocol-structure: '+str(e))
    for f in p['record_fixtures']:
        if f['inventory_classification']!='raw-only':_fail('fixture-acceptance-claim')
        if f['grammar_summary']!=SCOPE or f['evidence']!='Prompt37 fixed selected grammar control' or f['inventory_grammar']!={'required':'exact selected profile record','optional':'only reviewed rule-template forms','shape':'validated against fixed grammar and quarantine'} or 'pinned_emitter_sources' in f or 'pinned_dynamic_emitter_source' in f:_fail('fixture-evidence')
        import re
        m=re.fullmatch(r'control:(0|[1-9][0-9]*)',f['fixture_reference']);index=int(m[1]) if m else -1
        control=p['valid_record_controls'][index] if 0<=index<len(p['valid_record_controls']) else None
        if not control or f['record']!=control['record'] or f['token']!=control['token']:_fail('fixture-reference')
    for c in p['valid_record_controls']:
        if c['reconstruction_scope']!=SCOPE:_fail('control-scope')
        evidence='Prompt42 source-qualified Revival public bench heal and bounded held-restoration publication; no general healing or completeness acceptance' if profile=='native11' and c['record']=='|-heal|p1: First|50/100|[from] move: Revival Blessing' else 'Prompt41 source-qualified target Trace; actual native emitter/audience witness and bounded owned publication controls; no completeness or positive fidelity acceptance' if profile=='native11' and c['record']=='|-ability|p1a: Gardevoir|Natural Cure|Trace|[from] ability: Trace|[of] p2a: Blissey' else 'Verified target Natural Cure source form; PRE only' if profile=='replay-compat-v1' and c['record']==NATIVE_NC else 'Prompt37 bounded fixed-grammar fixture check; no target engine execution'
        if c['evidence']!=evidence:_fail('control-evidence')
    records=[x['record'] for x in p['valid_record_controls']]
    if profile=='native11' and '|-ability|p1a: Gardevoir|Natural Cure|Trace|[from] ability: Trace|[of] p2a: Blissey' not in records:_fail('trace-controls')
    if profile=='native11' and '|-heal|p1: First|50/100|[from] move: Revival Blessing' not in records:_fail('revival-controls')
    if NATIVE_NC not in records or profile=='replay-compat-v1' and OLD_NC not in records:_fail('natural-cure-controls')
    for kind in ('malformed','unknown','unproved_semantic_family'):
        if not any(x['kind']==kind for x in p['rejection_fixtures']):_fail('negative-coverage')

def check_prepared_protocol_records(value,profile):
    assert_prepared_record_check_input(value,profile)
    context=NATIVE11_GRAMMAR_CONTEXT if profile=='native11' else REPLAY_COMPAT_CONTEXT
    for x in value['protocol']['record_fixtures']+value['protocol']['valid_record_controls']:
        try:validate_protocol_record(x['record'],reader_rules=context)
        except ValueError as e:_fail('positive-rejected: '+x['token']+' '+str(e))
    for x in value['protocol']['rejection_fixtures']:
        try:validate_protocol_record(x['record'],reader_rules=context)
        except ValueError as e:error=e
        else:_fail('negative-accepted')
        token=x['record'].split('|')[1] if x['record'].startswith('|') else None
        declared=next((v['kind'] for v in value['protocol']['recognized_unsupported_commands'] if v['token']==token),None)
        text=str(error)
        actual=('unproved_semantic_family' if 'prepared-family-unsupported/' in text else 'malformed' if text.startswith('Malformed raw ') else (declared or 'unknown') if text.startswith('unsupported raw protocol event:') else None)
        if actual!=x['kind']:_fail('negative-reason')

def validate_prepared_protocol_asset(value,profile):
    assert_prepared_inspection_available();_plain(value);snapshot=copy.deepcopy(value)
    validate_prepared_protocol_structure(snapshot,profile);check_prepared_protocol_records(snapshot,profile);return _freeze(snapshot)
