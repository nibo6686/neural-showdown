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
            if context is NATIVE11_GRAMMAR_CONTEXT and family in ('heal-failure','chilly-reception','partial-trap'):
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
