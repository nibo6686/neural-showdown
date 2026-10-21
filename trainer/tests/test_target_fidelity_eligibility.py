"""Prompt34 local eligibility/source quarantine PRE and deferred real-target LIVE controls."""
import copy
import json
import os
import subprocess
import sys
from pathlib import Path
import pytest
from neural import version_profile as profiles
from neural import pipeline_record as reader
from neural import perspective_knowledge_source as source
from neural.version_profile import positive_fidelity_scope, assert_positive_fidelity_claim, historical_knowledge_source_scope
ROOT=Path(__file__).resolve().parents[2]
def load(p): return json.loads((ROOT/p).read_text(encoding='utf-8'))
def literal(v): return json.dumps(v,ensure_ascii=True,sort_keys=True,separators=(',',':'))+'\n'
def emit(n,**data): print('P34_WITNESS '+json.dumps(dict(name=n,**data),sort_keys=True))
def cli(value,*args):
    env=dict(os.environ)
    for k in list(env):
        if k in ('PYTHONUTF8','PYTHONIOENCODING') or k.startswith(('REPORT_','PROMPT')):env.pop(k)
    env['PYTHONPATH']=str(ROOT/'trainer/src')
    return subprocess.run([sys.executable,'-m','neural.pipeline_record',*args],input=json.dumps(value),text=True,capture_output=True,cwd=ROOT,env=env,timeout=20)

def test_pre_policy_and_old_publication():
    assert positive_fidelity_scope('historical10','gen9randombattle')
    assert not positive_fidelity_scope('native11','gen9randombattle')
    assert_positive_fidelity_claim('native11','gen9randombattle',False)
    with pytest.raises(ValueError,match='positive-unaccepted'):assert_positive_fidelity_claim('native11','gen9randombattle',True)
    with pytest.raises(ValueError,match='unknown-fidelity'):positive_fidelity_scope('caller-certificate','gen9randombattle')
    assert not historical_knowledge_source_scope('0.11.11')
    fixtures=load('docs/planning/perspective-fidelity-prompt31-reader-fixtures.json');golden=load('docs/planning/perspective-fidelity-prompt31-old-publication-goldens.json')
    for name,fn in [('result',reader.validate_historical_pipeline_episode_result),('sweep',reader.validate_historical_pipeline_episode_publication_sweep)]:
        before=literal(fixtures[name]);assert literal(fn(fixtures[name]))==golden[name]['api_literal'];assert literal(fixtures[name])==before
    conservative=copy.deepcopy(fixtures['result']);conservative['faithful_complete_episode']=False
    assert literal(reader.validate_pipeline_episode_result(conservative))==golden['result']['api_literal']
    invalid=copy.deepcopy(conservative);invalid['status']='truncated'
    with pytest.raises(ValueError):reader.validate_pipeline_episode_result(invalid)
    bad=cli(invalid);assert bad.returncode==2 and bad.stdout==''
    published=cli(fixtures['sweep']);assert published.returncode==0 and published.stdout==golden['sweep']['cli_literal']
    emit('python-policy-publication',finite_target_policy_only=True,old_true_false_and_outputs=True,false_does_not_waive_validation=True,invalid_exit=2,invalid_stdout='',target_callers='UNEXECUTED')

def test_pre_source_factory_and_metadata_fault(monkeypatch):
    origin=dict(battle_key='fixture-Éclair-😀',format='gen9randombattle',engine='pokemon-showdown@0.11.10',rule_version='pk-rules/v1')
    replay=['|start','|switch|p1a: Éclair|Pikachu, L80|100/100','|switch|p2a: Beta|Gengar, L80|100/100','|-enditem|p1a: Éclair|Oran Berry|[eat]',
            '|move|p2a: Beta|Tackle|p1a: Éclair','|replace|p2a: Beta|Zoroark, L80|100/100','|win|Éclair']
    audit=load('docs/contracts/fixtures/perspective-knowledge-v1/replay-ordinary.json');before=literal(audit)
    b=source.SourceRegistryBuilder();b.set_origin(origin);b.set_replay_source(replay);registry=b.freeze()
    checked=source.check_knowledge_source_binding(audit,registry,None,audit['required_profile']);assert checked['source_verification']['replay_source'] and not checked['published']
    assert literal(audit)==before
    with pytest.raises(ValueError,match='capability/registry'):source.check_knowledge_source_binding(audit,{},None,audit['required_profile'])
    wrong=source.SourceRegistryBuilder()
    with pytest.raises(ValueError,match='registry/origin'):wrong.set_origin(dict(origin,engine='pokemon-showdown@0.11.11'))
    with pytest.raises(ValueError,match='registry/origin'):wrong.set_origin(dict(origin,accepted_digest='forged'))
    assert source.LegacyContextBuilder().freeze().availability['pairs']==0
    count=len(source._REGISTRIES);read=Path.read_text
    def mismatched(path,*args,**kwargs):
        text=read(path,*args,**kwargs)
        if path==ROOT/'sim-core/node_modules/pokemon-showdown/package.json':
            payload=json.loads(text);payload['version']='0.11.11';return json.dumps(payload)
        return text
    monkeypatch.setattr(Path,'read_text',mismatched)
    with pytest.raises(ValueError,match='source-runtime-mismatch'):source.SourceRegistryBuilder()
    with pytest.raises(ValueError,match='source-runtime-mismatch'):source.SourceRegistry(source._TOKEN,{})
    with pytest.raises(ValueError,match='source-runtime-mismatch'):source.LegacyContext(source._TOKEN,{})
    assert len(source._REGISTRIES)==count
    emit('python-source',actual_old_factory=True,old_origin_ids_unchanged=True,metadata_fault_model=True,reject_before_registry_mutation=True,content_origin_authenticated=False)

LIVE=str(load('sim-core/node_modules/pokemon-showdown/package.json')['version'])=='0.11.11'
@pytest.mark.skipif(not LIVE,reason='UNEXECUTED: actual installed native11/context assets required')
def test_live_target_claim_source_and_atomic_cli():
    directory=os.environ.get('NEURAL_TEST_OUTPUT_DIR')
    names=['perspective-fidelity-prompt34-live-target-result.json', 'perspective-fidelity-prompt34-live-target-sweep.json']
    if not directory or not all((Path(directory)/name).is_file() for name in names):
        pytest.skip('run the Node producer with NEURAL_TEST_OUTPUT_DIR set')
    payload=json.loads((Path(directory)/names[0]).read_text(encoding='utf-8'))
    context=getattr(profiles,'NATIVE11_CONTEXT',None)
    assert context is not None and context.profile.id=='native11', 'actual adopted target reader context required'
    assert payload['status']=='completed' and payload['faithful_complete_episode'] is False
    reader.validate_pipeline_episode_result(payload,reader_rules=context)
    claim=copy.deepcopy(payload);claim['faithful_complete_episode']=True
    with pytest.raises(ValueError,match='positive-unaccepted'):reader.validate_pipeline_episode_result(claim,reader_rules=context)
    sweep=json.loads((Path(directory)/names[1]).read_text(encoding='utf-8'))
    reader.validate_pipeline_episode_publication_sweep(sweep,reader_rules=context)
    ineligible=copy.deepcopy(sweep);ineligible['result']['faithful_complete_episode']=True
    with pytest.raises(ValueError,match='positive-unaccepted'):reader.validate_pipeline_episode_publication_sweep(ineligible,reader_rules=context)
    no_rows=cli(ineligible,'--reader-profile=native11');assert no_rows.returncode==2 and no_rows.stdout=='' and 'positive-unaccepted' in no_rows.stderr
    rejected=cli(claim,'--reader-profile=native11');assert rejected.returncode==2 and rejected.stdout=='' and 'positive-unaccepted' in rejected.stderr
    with pytest.raises(ValueError,match='historical-origin-quarantined'):source.SourceRegistryBuilder()
    with pytest.raises(ValueError,match='historical-origin-quarantined'):source.LegacyContextBuilder()
    with pytest.raises(ValueError,match='historical-origin-quarantined'):source.SourceRegistry(source._TOKEN,{})
