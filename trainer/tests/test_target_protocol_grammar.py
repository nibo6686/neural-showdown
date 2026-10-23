"""Prompt36 PRE grammar and historical publication controls; no target execution."""
import copy
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
import pytest
from neural.protocol_contract import validate_protocol_record
from neural.version_profile import (HISTORICAL10_CONTEXT, REPLAY_COMPAT_CONTEXT, NATIVE11_GRAMMAR_CONTEXT,
    load_prepared_protocol_asset, reader_context, select_reader_profile)
ROOT=Path(__file__).resolve().parents[2]
OLD='|-curestatus|p2a: Blissey|par|[from] ability: Natural Cure'
TARGET=OLD+'|[silent]'
def test_exact_profile_grammar_and_immutability(tmp_path):
    validate_protocol_record(OLD)
    with pytest.raises(ValueError,match='major-status source grammar'):validate_protocol_record(TARGET)
    validate_protocol_record(TARGET,reader_rules=NATIVE11_GRAMMAR_CONTEXT)
    with pytest.raises(ValueError,match='major-status source grammar'):validate_protocol_record(OLD,reader_rules=NATIVE11_GRAMMAR_CONTEXT)
    for record in (OLD,TARGET):validate_protocol_record(record,reader_rules=REPLAY_COMPAT_CONTEXT)
    negatives=[TARGET+'|[silent]',OLD+'|[of] p1a: Regice',TARGET+'|[of] p1a: Regice',
      '|-curestatus|p2a: Blissey|par|[silent]|[from] ability: Natural Cure',
      '|-curestatus|p2a: Blissey|par|[silent]',TARGET.replace('Natural Cure','Regenerator'),
      TARGET.replace('Natural Cure','natural cure'),TARGET.replace('p2a: Blissey','p2: Blissey'),
      TARGET.replace('p2a: Blissey','p2b: Blissey'),TARGET.replace('par|','???|'),TARGET+'|extra']
    for context in (NATIVE11_GRAMMAR_CONTEXT,REPLAY_COMPAT_CONTEXT):
        for record in negatives:
            with pytest.raises(ValueError,match='Malformed raw .*record'):validate_protocol_record(record,reader_rules=context)
    for context in (NATIVE11_GRAMMAR_CONTEXT,REPLAY_COMPAT_CONTEXT):
        with pytest.raises(ValueError,match='unsupported raw protocol event: curestatus'):validate_protocol_record(TARGET.replace('-curestatus','curestatus'),reader_rules=context)
    for profile in ('native11','replay-compat-v1'):
        asset=load_prepared_protocol_asset(profile)
        for control in asset['protocol']['valid_record_controls']:
            if profile=='native11' and control['record']=='|-swapsideconditions':
                with pytest.raises(ValueError,match='prepared-family-unsupported/court-change'):validate_protocol_record(control['record'],reader_rules=NATIVE11_GRAMMAR_CONTEXT)
            else:
                validate_protocol_record(control['record'],reader_rules=NATIVE11_GRAMMAR_CONTEXT if profile=='native11' else REPLAY_COMPAT_CONTEXT)
        with pytest.raises(TypeError):asset['adopted']=True
        # Coherent JSON rewrite/digest cannot replace the locally reviewed code pin.
        ordinary=json.loads((ROOT/'trainer/src/neural'/('protocol_contract_b8f23c99.json' if profile=='native11' else 'protocol_contract_replay_compat_v1.json')).read_text(encoding='utf-8'))
        del ordinary['protocol']['validation_rules']['major_status'];p=tmp_path/(profile+'.json');p.write_text(json.dumps(ordinary));assert len(hashlib.sha256(p.read_bytes()).hexdigest())==64
        with pytest.raises(ValueError,match='version-asset-integrity'):load_prepared_protocol_asset(profile,p)
        with pytest.raises(ValueError,match='missing-version-asset'):load_prepared_protocol_asset(profile,tmp_path/'missing')
    with pytest.raises(ValueError,match='unsupported-context'):reader_context(NATIVE11_GRAMMAR_CONTEXT)
    with pytest.raises(ValueError,match='unsupported-context'):reader_context(REPLAY_COMPAT_CONTEXT)
    assert select_reader_profile({},'native11').id=='native11'
    families=[('|-ability|p1a: Regice|Insomnia|Clear Body|[from] move: Worry Seed|[of] p2a: Blissey','ability-setter'),
      ('|-heal|p1a: Regice|90/100|[from] ability: Regenerator','heal-failure'),
      ('|cant|p1a: Regice|move: Heal Block|Pollen Puff','heal-failure'),
      ('|-prepare|p1a: Regice|Chilly Reception|[premajor]','chilly-reception'),
      ('|-damage|p1a: Regice|80/100|[from] move: Whirlpool|[partiallytrapped]','partial-trap'),
      ('|-swapsideconditions','court-change'),('|-item|p1a: Regice|Leftovers|[from] ability: Magician|[of] p2a: Blissey','magician')]
    for context in (NATIVE11_GRAMMAR_CONTEXT,REPLAY_COMPAT_CONTEXT):
        for record,family in families:
            if context is NATIVE11_GRAMMAR_CONTEXT and family in ('heal-failure','chilly-reception','partial-trap','magician'):
                validate_protocol_record(record,reader_rules=context)
            else:
                with pytest.raises(ValueError,match='prepared-family-unsupported/'+family):validate_protocol_record(record,reader_rules=context)
    validate_protocol_record('|-sidestart|p1: Player|move: Stealth Rock',reader_rules=NATIVE11_GRAMMAR_CONTEXT)
    validate_protocol_record("|-hint|Psychic Terrain doesn't affect airborne Pokémon.",reader_rules=NATIVE11_GRAMMAR_CONTEXT)
    print('P36_WITNESS '+json.dumps({'name':'python-exact-grammar','negative_forms':len(negatives),'blocked_forms':len(families),'target_runtime':'UNEXECUTED'}))

def test_historical_publication_and_replay_rejection():
    from neural import pipeline_record as r
    fixtures=json.loads((ROOT/'docs/planning/perspective-fidelity-prompt31-reader-fixtures.json').read_text(encoding='utf-8'))
    goldens=json.loads((ROOT/'docs/planning/perspective-fidelity-prompt31-old-publication-goldens.json').read_text(encoding='utf-8'))
    for name,fn in [('result',r.validate_historical_pipeline_episode_result),('sweep',r.validate_historical_pipeline_episode_publication_sweep)]:
        output=json.dumps(fn(fixtures[name]),ensure_ascii=True,sort_keys=True,separators=(',',':'))+'\n'
        assert output==goldens[name]['api_literal']
    with pytest.raises(ValueError,match='unsupported-context'):r.validate_pipeline_episode_result(fixtures['result'],reader_rules=REPLAY_COMPAT_CONTEXT)
    with pytest.raises(ValueError,match='unsupported-context'):r.validate_pipeline_episode_result(fixtures['result'],reader_rules=NATIVE11_GRAMMAR_CONTEXT)
    env=dict(os.environ);env['PYTHONPATH']=str(ROOT/'trainer/src')
    for k in list(env):
        if k in ('PYTHONUTF8','PYTHONIOENCODING') or k.startswith(('REPORT_','PROMPT')):env.pop(k)
    child=subprocess.run([sys.executable,'-m','neural.pipeline_record','--reader-profile=replay-compat-v1'],input=json.dumps(fixtures['result']),text=True,capture_output=True,env=env,cwd=ROOT,timeout=20)
    assert child.returncode==2 and child.stdout==''
    print('P36_WITNESS '+json.dumps({'name':'python-publication-boundary','literal_historical_outputs':True,'replay_context_rejected':True,'cli_exit':child.returncode,'stdout':child.stdout,'native11_publication':'UNEXECUTED'}))


CORPUS_FORMS=[
 '|-enditem|p2a: Sableye|Leftovers|[silent]|[from] ability: Pickpocket|[of] p2a: Sableye',
 '|-curestatus|p2: Probopass|par|[msg]',
 '|-anim|p1a: Glimmora|Meteor Beam|p2a: Vikavolt|[miss]',
 '|-status|p1a: Scream Tail|slp|[from] move: Relic Song',
 '|teampreview|6',
]

def test_native_corpus_emitter_forms_and_rejection_controls():
    negatives=[CORPUS_FORMS[0].replace('[of] p2a: Sableye','[of] p1a: Weavile'),
      CORPUS_FORMS[0].replace('[silent]|[from]','[from]'),CORPUS_FORMS[1].replace('[msg]','[from] ability: Natural Cure'),
      CORPUS_FORMS[1].replace('p2:','p2b:'),CORPUS_FORMS[1]+'|extra',CORPUS_FORMS[2]+'|[miss]',
      CORPUS_FORMS[2].replace('[miss]','[MISS]'),CORPUS_FORMS[2].replace('Meteor Beam','Imaginary Beam'),
      CORPUS_FORMS[3].replace('|slp|','|par|'),CORPUS_FORMS[3].replace('Relic Song','relic song'),
      '|teampreview|25','|teampreview|06','|teampreview|6|extra']
    for row in CORPUS_FORMS:validate_protocol_record(row,reader_rules=NATIVE11_GRAMMAR_CONTEXT)
    for row in negatives:
        with pytest.raises(ValueError,match='Malformed raw'):validate_protocol_record(row,reader_rules=NATIVE11_GRAMMAR_CONTEXT)
    with pytest.raises(ValueError,match='court-change'):validate_protocol_record('|-swapsideconditions',reader_rules=NATIVE11_GRAMMAR_CONTEXT)

def test_bench_cure_keeps_active_status():
    from neural.public_health import project_public_health
    health=project_public_health(['|switch|p2a: Probopass|Probopass, L88|100/100 par',
      '|switch|p2a: Chansey|Chansey, L88|100/100 brn',CORPUS_FORMS[1]])
    assert health['p2: Probopass']['status'] is None
    assert health['p2: Chansey']['status']=='brn'


def test_additional_corpus_forms_and_controls():
    forms=[
      '|-item|p2a: Weavile|Assault Vest|[from] ability: Pickpocket|[of] p1a: Dewgong',
      '|-enditem|p1a: Golem|Custap Berry|[from] stealeat|[move] Bug Bite|[of] p2a: Scyther',
      '|-ability|p2a: Obliteryx|Opportunist|boost',
      '|-anim|p1a: Glimmora|Meteor Beam|p2: Basculin|[notarget]',
      '|teampreview|8',
      '|-hitcount|p2: Terapagos|10',
    ]
    negatives=[forms[0].replace('p1a: Dewgong','p2a: Dewgong'),forms[1].replace('Custap Berry','Leftovers'),
      forms[1].replace('Bug Bite','Bite'),forms[2].replace('Opportunist','Illusion'),
      forms[3].replace('p2: Basculin','p1: Basculin'),forms[3].replace('p2: Basculin','p2a: Basculin'),
      forms[3].replace('[notarget]','[miss]'),forms[3]+'|[miss]','|-hitcount|p2: Terapagos|11']
    for row in forms:validate_protocol_record(row,reader_rules=NATIVE11_GRAMMAR_CONTEXT)
    for row in negatives:
        with pytest.raises(ValueError,match='Malformed raw'):validate_protocol_record(row,reader_rules=NATIVE11_GRAMMAR_CONTEXT)

    for row in ['|-start|p1a: Equilibra|Doom Desire','|-end|p2a: Jumbao|move: Doom Desire']:
        with pytest.raises(ValueError,match='unclassified-effect-value'):validate_protocol_record(row,reader_rules=NATIVE11_GRAMMAR_CONTEXT)


def test_native_magician_grammar_and_public_donor_history():
    from neural.public_item import project_public_items,project_public_item_dispositions,project_public_item_history
    row='|-item|p1a: Hoopa|Choice Scarf|[from] ability: Magician|[of] p2a: Porygon-Z'
    for donor in ['p2a: Porygon-Z','p2: Porygon-Z']:
        record=row.replace('p2a: Porygon-Z',donor)
        validate_protocol_record(record,reader_rules=NATIVE11_GRAMMAR_CONTEXT)
        prefix=['|switch|p1a: Hoopa|Hoopa, L80|100/100','|switch|p2a: Porygon-Z|Porygon-Z, L80|100/100',record]
        assert project_public_items(prefix)=={'p1: Hoopa':'choicescarf','p2: Porygon-Z':None}
        assert project_public_item_dispositions(prefix)['p2: Porygon-Z']=={'item_state':'removed','last_item':'choicescarf'}
        assert project_public_item_history(prefix)['p2: Porygon-Z']=={'item_state':'removed','last_item':'choicescarf'}
    for bad in [row.replace('p2a:','p1a:'),row.replace('p2a:','p2b:'),row.replace('[of] ','[source] '),row+'|extra',row.replace('|Choice Scarf|','|Imaginary Item|')]:
        with pytest.raises(ValueError,match='Malformed raw'):validate_protocol_record(bad,reader_rules=NATIVE11_GRAMMAR_CONTEXT)
    with pytest.raises(ValueError,match='prepared-family-unsupported/magician'):validate_protocol_record(row,reader_rules=REPLAY_COMPAT_CONTEXT)
