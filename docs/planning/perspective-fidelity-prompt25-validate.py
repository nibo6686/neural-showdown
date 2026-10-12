import os,sys,pathlib,subprocess,json,re
root=pathlib.Path(__file__).resolve().parents[2]; out=root/'docs/planning'; stem='perspective-fidelity-prompt25-'; env=dict(os.environ)
for k in list(env):
 if k in ('PYTHONUTF8','PYTHONIOENCODING','PERSPECTIVE_REPLAY_REQUIREMENTS') or 'REPORT' in k or k.startswith('PROMPT'):env.pop(k,None)
env['PYTHON']=r'D:\Anaconda\envs\neuralgpu\python.exe';env['PYTHONPATH']=str(root/'trainer/src')
rows=[]
def run(name,args,cwd=root,expected=0,changes=None):
 e=dict(env);e.update(changes or {});p=subprocess.run(args,cwd=cwd,env=e,stdout=subprocess.PIPE,stderr=subprocess.STDOUT); data=p.stdout.decode('utf-8',errors='replace'); (out/(stem+name+'.log')).write_text(data,encoding='utf-8'); row={'name':name,'cwd':str(cwd),'command':args,'exit':p.returncode,'expected_exit':expected,'counts':re.findall(r'(?:tests|pass|fail|skipped) \d+|Ran \d+ tests?',data)}; rows.append(row); print(json.dumps(row),flush=True);(out/(stem+'commands.json')).write_text(json.dumps({'environment':{'PYTHON':env['PYTHON'],'PYTHONPATH':env['PYTHONPATH'],'unset':['PYTHONUTF8','PYTHONIOENCODING','historical REPORT/PROMPT variables']},'commands':rows},indent=2)+'\n',encoding='utf-8');return p.returncode
if run('build',['node','node_modules/typescript/bin/tsc','-p','tsconfig.json'],root/'sim-core')!=0:sys.exit(1)
for name in ['request_delivery_ledger','request_emission_trace','original_owner_provider','env_manager','pipeline_integration','settling','pipeline_episode_stop_repair','perspective_knowledge_source','active_request_restore','public_move_history','replay_import','original_owner_provider_characterization','perspective_replay_characterization']:
 run(name,['node','--test',f'sim-core/dist/tests/{name}.test.js'])
run('episode-cleanup',['node','--test','--test-name-pattern=initialization failure|invalid budgets/policy|invalid continuation|cleanup preserves','sim-core/dist/tests/pipeline_episode.test.js'])
run('loader',['D:/Anaconda/envs/neuralgpu/python.exe','-m','unittest','discover','-s','trainer/tests','-p','test_local_replay_html_transport.py','-v'])
run('python-characterization',['D:/Anaconda/envs/neuralgpu/python.exe','-m','unittest','discover','-s','trainer/tests','-p','test_perspective_replay_characterization.py','-v'])
run('ts-requirements',['node','--test','sim-core/dist/tests/perspective_replay_characterization.test.js'],expected=1,changes={'PERSPECTIVE_REPLAY_REQUIREMENTS':'1'})
run('python-requirements',['D:/Anaconda/envs/neuralgpu/python.exe','-m','unittest','discover','-s','trainer/tests','-p','test_perspective_replay_characterization.py','-v'],expected=1,changes={'PERSPECTIVE_REPLAY_REQUIREMENTS':'1'})
run('literal-witnesses',['node','docs/planning/perspective-fidelity-prompt25-witnesses.cjs'])
run('wire',['node','docs/planning/perspective-fidelity-prompt25-wire.cjs','check'])
run('diff-check',['git','diff','--check'])
sys.exit(any(r['exit']!=r['expected_exit'] for r in rows))
