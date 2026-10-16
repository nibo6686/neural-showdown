import json
import os
import subprocess
import sys
from pathlib import Path
import hashlib
import pytest
from neural.prepared_protocol_contract import validate_prepared_protocol_asset
from neural.version_profile import load_prepared_protocol_asset,protocol_context
from neural.protocol_contract import validate_protocol_contract
ROOT=Path(__file__).resolve().parents[2]
def asset(profile):
    name='protocol_contract_0_11_11.json' if profile=='native11' else 'protocol_contract_replay_compat_v1.json'
    return json.loads((ROOT/'trainer/src/neural'/name).read_text(encoding='utf-8'))
def mutate(v,c):
    p=v['protocol'];op=c['op']
    if op=='set':
        target=v
        for key in c['path'][:-1]:target=target[key]
        target[c['path'][-1]]=c['value']
    elif op=='duplicate-token':p['supported_commands'].append(p['supported_commands'][0])
    elif op=='add-token':p['supported_commands'].append('unreviewed')
    elif op=='missing-fixture':p['record_fixtures'].pop()
    elif op=='invalid-positive':
        f=next(x for x in p['record_fixtures'] if x['token']=='switch');i=int(f['fixture_reference'][8:]);f['record']='|switch|p1z: Invalid|Regice, L88|100/100';p['valid_record_controls'][i]['record']=f['record']
    elif op=='accepted-negative':p['rejection_fixtures'][0]['record']='|-curestatus|p2a: Blissey|par|[from] ability: Natural Cure|[silent]'
    elif op=='wrong-negative-reason':p['rejection_fixtures'][0]['kind']='unproved_semantic_family'
    elif op=='replay-rule':p['validation_rules']['major_status']['cure_forms'][-1]['tags'].append('[of] opposing-active')
    else:raise AssertionError(op)
def test_full_assets_mutations_and_integrity(tmp_path):
    results=[]
    for profile,count in [('native11',101),('replay-compat-v1',108)]:
        v=asset(profile);out=validate_prepared_protocol_asset(v,profile);assert out is not v
        assert len(out['protocol']['record_fixtures'])==count
        with pytest.raises(TypeError):out['adopted']=True
        with pytest.raises(ValueError,match='unsupported-context'):protocol_context(out)
        assert load_prepared_protocol_asset(profile)==out
    cases=json.loads((ROOT/'docs/planning/perspective-fidelity-prompt37-mutations.json').read_text(encoding='utf-8'))
    for c in cases:
        v=asset(c['profile']);mutate(v,c);assert len(hashlib.sha256(json.dumps(v).encode()).hexdigest())==64
        with pytest.raises(ValueError,match='prepared-protocol-contract/v1/'+c['expected']):validate_prepared_protocol_asset(v,c['profile'])
        results.append({'name':c['name'],'invariant':c['expected']})
    for profile in ['native11','replay-compat-v1']:
        v=asset(profile);v['adopted']=True;p=tmp_path/(profile+'.json');p.write_text(json.dumps(v))
        with pytest.raises(ValueError,match='version-asset-integrity'):load_prepared_protocol_asset(profile,p)
        with pytest.raises(ValueError,match='missing-version-asset'):load_prepared_protocol_asset(profile,tmp_path/'missing')
    validate_protocol_contract(json.loads((ROOT/'trainer/src/neural/protocol_contract.json').read_text()))
    print('P37_WITNESS '+json.dumps({'name':'python-full-validation','mutations':results,'fixture_counts':[101,108],'target_runtime':'UNEXECUTED'}))

def test_owned_bootstrap_threads_and_sticky_failure():
    good="""
import json,threading
from neural import version_profile as v,prepared_protocol_contract as c
original=c.check_prepared_protocol_records
entered=threading.Event();release=threading.Event();failures=[];taps=[]
def tap(asset,profile):
    if profile=='native11' and not taps:
        taps.append(1)
        assert v.protocol_context(v.NATIVE11_GRAMMAR_CONTEXT) is v.NATIVE11_GRAMMAR_CONTEXT
        for fn in (lambda:v.protocol_context(v.REPLAY_COMPAT_CONTEXT),lambda:c.validate_prepared_protocol_asset(c._thaw(asset),profile)):
            try:fn()
            except ValueError as e:assert 'prepared-validation-context' in str(e)
            else:raise AssertionError('borrowed bootstrap')
        entered.set();assert release.wait(5)
    return original(asset,profile)
c.check_prepared_protocol_records=tap
def work():
    try:v.protocol_context(v.NATIVE11_GRAMMAR_CONTEXT)
    except BaseException as e:failures.append(str(e))
t=threading.Thread(target=work)
try:
    t.start();assert entered.wait(5)
    try:v.protocol_context(v.NATIVE11_GRAMMAR_CONTEXT)
    except ValueError as e:assert 'prepared-validation-context' in str(e)
    else:raise AssertionError('other thread borrowed bootstrap')
finally:
    release.set();t.join(5);c.check_prepared_protocol_records=original
assert not t.is_alive() and not failures,failures
v.protocol_context(v.NATIVE11_GRAMMAR_CONTEXT);v.protocol_context(v.REPLAY_COMPAT_CONTEXT)
print(json.dumps({'owner_reentry':True,'other_thread_rejected':True,'other_profile_rejected':True,'arbitrary_validation_blocked':True}))
"""
    bad="""
import json
from neural import version_profile as v,prepared_protocol_contract as c
original=c.check_prepared_protocol_records;calls=[]
def fail(*args):calls.append(1);raise ValueError('P37 owned-check fault')
c.check_prepared_protocol_records=fail
try:
    for i in range(2):
        try:v.protocol_context(v.NATIVE11_GRAMMAR_CONTEXT)
        except ValueError as e:assert 'P37 owned-check fault' in str(e)
        else:raise AssertionError('failed context usable')
finally:c.check_prepared_protocol_records=original
try:v.protocol_context(v.NATIVE11_GRAMMAR_CONTEXT)
except ValueError as e:assert 'P37 owned-check fault' in str(e)
else:raise AssertionError('failure not sticky')
assert len(calls)==1
print(json.dumps({'sticky_failed_context':True,'checks':len(calls)}))
"""
    env=dict(os.environ);env['PYTHONPATH']=str(ROOT/'trainer/src')
    for k in list(env):
        if k in ('PYTHONUTF8','PYTHONIOENCODING') or k.startswith(('REPORT_','PROMPT')):env.pop(k)
    rows=[]
    for code in (good,bad):
        p=subprocess.run([sys.executable,'-c',code],cwd=ROOT,env=env,text=True,capture_output=True,timeout=20)
        assert p.returncode==0,p.stderr;rows.append(json.loads(p.stdout))
    print('P37_WITNESS '+json.dumps({'name':'python-bootstrap','controls':rows,'target_emitter':'UNEXECUTED'}))
