"""Independent bounded PK-01R regression oracles, not production verification."""
from property_contexts import applies
from typed_references import declared_edges


def check_representations(row,C):
    if 'pair' in row: return
    objects={x['id']:x for x in row['objects']}; definitions=C.load(C.ROOT/'schema.json')['$defs']
    for x in objects.values():
        C.shape(x,definitions[x['kind']],definitions); assert x['id']==C.expected_id(x),'subset identity'
        for ident,kind in declared_edges(x): assert ident in objects and objects[ident]['kind']==kind,'subset typed closure'
    f=objects[row['fact']]; prop=f['property']; value=f['value']
    types=C.load(C.ROOT/'property-types.json')
    if f['state']=='known': assert value is not None and value['type'] in types[prop],'property value tag'
    else: assert value is None,'nonknown value'
    if prop=='field_remaining':
        assert f['effect_key'] is not None,'timer target'
        if f['state']=='known': assert f['effect_key']==value['data']['target_kind']+':'+value['data']['name'],'timer target'
    assert applies(f,row['context']),'property context'
    ledger=next(x['records'] for x in objects.values() if x['kind']=='source')
    if f['state']=='inapplicable':
        assert all(objects[i]['writer']=='layer-count/v1' for i in f['evidence']),'inapplicability rule'
    check_field_ledger(f,ledger)


def check_field_ledger(f,ledger):
    prop=f['property']; value=f['value']
    if prop=='side_condition_layers':
        name=f['effect_key']; bounds={'Spikes':3,'ToxicSpikes':2}
        if f['state']=='known':
            assert name in bounds and 1<=value['data']<=bounds[name],'layer bounds'
            rawname='move: Toxic Spikes' if name=='ToxicSpikes' else name
            starts=[line for line in ledger if line.startswith('|-sidestart|')]
            assert all(line.endswith('|'+rawname) for line in starts),'layer ledger identity'
            assert all(line.split('|')[2].split(':')[0]+':side'==f['subject'] for line in starts),'layer affected side'
            assert value['data']==len(starts),'layer ledger value'
        elif f['state']=='known_absent':
            assert ledger[-1].endswith('|'+name) and ledger[-1].startswith('|-sideend|'),'layer absence'
            assert ledger[-1].split('|')[2].split(':')[0]+':side'==f['subject'],'layer affected side'
        elif f['state']=='inapplicable':
            assert name=='Reflect' and f['reason']=='proved_rule_inapplicable' and ledger==['|-sidestart|'+f['subject'].split(':')[0]+': Éclair|Reflect'],'layer applicability'
        else: assert f['reason']=='unimplemented_family','layer unknown'
    if prop=='pending_power':
        if f['state']=='known':
            assert f['effect_key']=='FutureSight' and value['data']=={'basis':'base_move','amount':120},'pending power oracle'
            assert ledger==['|move|p1a: Éclair|Future Sight|p2a: Beta','|-start|p1a: Éclair|move: Future Sight'],'pending source'
            assert f['subject']=='p2:side','pending recipient'
        else: assert f['state']=='unknown' and f['reason']=='unimplemented_family','power unsupported'
    if prop=='field_remaining':
        assert ledger==['|-weather|RainDance','|-weather|RainDance|[upkeep]','|-fieldstart|move: Electric Terrain'],'timer source'
        if f['state']=='known':
            expected={'weather:RainDance':{'min':4,'max':7},'terrain:ElectricTerrain':{'min':5,'max':8}}
            assert value['data']['remaining']==expected[f['effect_key']],'timer ledger range'
            assert f['precision']=='interval','timer precision'
        else: assert f['state']=='unknown' and f['reason']=='hidden_timer','hidden timer'


def check_coverage(row,C):
    universe=C.load(C.ROOT/'obligation-universe.json')['owners'][row['owner']]
    profiles={p['id']:p for p in C.load(C.ROOT/'profiles.json')}
    profile=profiles[row['profile']]
    applications={r['property']:r['applications'] for family in profile['obligations'] for r in family['property_rules']}
    actual=set(); members=set()
    for entry in row['facts']:
        f=entry['fact']; C.shape(f,C.load(C.ROOT/'schema.json')['$defs']['fact'],C.load(C.ROOT/'schema.json')['$defs'])
        assert C.expected_id(f)==f['id'],'coverage identity'
        assert f['owner']==row['owner'] and applies(f,entry['context']),'property context'
        key=(entry['context'],f['subject'],f['property'],f['effect_key']); assert key not in actual,'logical fact conflict'
        actual.add(key); members.add((entry['context'],f['subject'],f['effect_key']))
    required=set()
    for context,properties in row['selected'].items():
        for prop in properties:
            rules=[r for r in applications[prop] if r['context']==context]
            assert rules,'property context'
            for rule in rules:
                for member in universe[context][rule['subject']]:
                    subject=member['subject'] if isinstance(member,dict) else member
                    effect=member['effect_key'] if isinstance(member,dict) else None
                    required.add((context,subject,prop,effect))
    missing=required-actual
    if missing:
        assert all((context,subject,effect) in members for context,subject,prop,effect in missing),'coverage missing subject'
        raise AssertionError('coverage missing property')
    assert actual==required,'coverage unexpected key'
    assert row['aggregate']=='incomplete','coverage promotion'


def run(C):
    literal=C.load(C.ROOT/'canonical-controls-vector.json')
    assert C.canonical(literal['value'])==literal['canonical_json_literal'].encode('utf-8'),'literal control mapping'
    assert [ord(c) for c in literal['value']['s'][:32]]==list(range(32)),'literal control coverage'
    obj=literal['object']; payload={k:v for k,v in obj.items() if k!='id'}
    assert C.canonical(payload)==literal['object_canonical_literal'].encode('utf-8'),'literal object bytes'
    assert (('pk/v1/origin\n').encode()+C.canonical(payload)).hex()==literal['preimage_utf8_hex'],'literal preimage'
    assert C.expected_id(obj)==obj['id']==literal['expected_id'],'literal ID'
    representation=C.load(C.ROOT/'representation-canaries.json'); byname={r['case']:r for r in representation['positive']}
    def representation_check(row):
        if 'pair' not in row: return check_representations(row,C)
        facts=[next(x for x in byname[name]['objects'] if x['id']==byname[name]['fact']) for name in row['pair']]
        keys=[(f['owner'],f['subject'],f['family'],f['property'],f['effect_key']) for f in facts]
        assert len(set(keys))==len(keys),'logical fact conflict'
    count={'representation_positive':0,'representation_negative':0,'coverage_positive':0,'coverage_negative':0}
    for row in representation['positive']: representation_check(row); count['representation_positive']+=1
    for row in representation['negative']:
        try: representation_check(row)
        except AssertionError as error: assert str(error)==row['rejection_code'],row['case']+': '+str(error); count['representation_negative']+=1
        else: raise AssertionError('representation negative accepted '+row['case'])
    coverage=C.load(C.ROOT/'obligation-canaries.json')
    for row in coverage['positive']: check_coverage(row,C); count['coverage_positive']+=1
    for row in coverage['negative']:
        try: check_coverage(row,C)
        except AssertionError as error: assert str(error)==row['rejection_code'],row['case']+': '+str(error); count['coverage_negative']+=1
        else: raise AssertionError('coverage negative accepted '+row['case'])
    # Context/expansion manifest is exact and part of every profile ID, never producer choice.
    assert C.load(C.ROOT/'property-contexts.json')==__import__('property_contexts').RULES,'context manifest'
    assert C.load(C.ROOT/'typed-references.json')=={'internal':__import__('typed_references').EDGES,'external':__import__('typed_references').EXTERNAL},'reference manifest'
    assert all(v=='all_relevant' for p in C.load(C.ROOT/'property-contexts.json').values() for r in p for k,v in r.items() if k=='coverage')
    sentinel={'owner':'p1','subject':'p1:side','property':'side_condition','effect_key':None,'state':'unknown'}
    assert applies(sentinel,'current'),'collection sentinel applicability'
    assert not applies(dict(sentinel,state='known'),'current'),'known collection forbidden'
    # Same-source refinement preserves proved byte-identical facts; source fork re-proves anew.
    old=C.load(C.ROOT/'replay-full.json'); new=C.load(C.ROOT/'replay-suffix-full.json')
    starts={x['id']:x for x in old['tables']['starting']}; facts={x['id']:x for x in old['tables']['fact']}
    child=next(s for s in starts.values() if s['parent'] is not None); parent=starts[child['parent']]
    assert child['source']==parent['source'] and any(facts[i]['state']=='known' and i in child['facts'] for i in parent['facts']),'proved retention control'
    assert any(facts[i]['state']=='unknown' for i in parent['facts']) and all(facts[i]['state']=='known' for i in child['facts']),'refinement control'
    assert all(s['parent'] is None and s['revision']==0 for s in new['tables']['starting']),'fork lineage root'
    for form in ['full','ordinary','compact']:
        left=C.expanded(C.load(C.ROOT/('replay-'+form+'.json'))); right=C.expanded(C.load(C.ROOT/('replay-suffix-'+form+'.json')))
        assert C.canonical(left)==C.canonical(C.expanded(C.load(C.ROOT/'replay-full.json'))),'all-form replay parity '+form
        assert C.canonical(right)==C.canonical(C.expanded(C.load(C.ROOT/'replay-suffix-full.json'))),'all-form fork parity '+form
        def chronological(t):
            currents=[x for x in t['current'] if x['cursor']<=5]; factids={i for c in currents for i in c['facts']}
            factrows=[f for f in t['fact'] if f['id'] in factids]; evidenceids={i for f in factrows for i in f['evidence']}
            return {'current':currents,'fact':factrows,'evidence':[e for e in t['evidence'] if e['id'] in evidenceids],
                    'prefix':[p for p in t['prefix'] if len(p['records'])<=5]}
        assert C.canonical(chronological(left))==C.canonical(chronological(right)),'all-form causal bytes '+form
    return {**count,'literal_all_controls':True,'same_source_refinement':True,'changed_source_fork':True,'all_form_suffix_invariance':True}
