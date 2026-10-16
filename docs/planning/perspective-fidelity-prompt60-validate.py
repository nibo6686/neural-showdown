from pathlib import Path
import os,subprocess,signal,threading,time,json,sys
r=Path('/Users/nbolger/Documents/Codex/2026-09-24/files-mentioned-by-the-user-neural/native11-recovery-2026-10-14/candidate');d=Path('/Users/nbolger/Desktop/neural-showdown/docs/planning');node='/Users/nbolger/.nvm/versions/node/v24.21.0/bin/node'
name=sys.argv[1]
selectors={
'generated':'P60 generated both owners selected delivery restore and real callbacks',
'literal':'P60 literal fields omissions and boosted stored-stat distinction',
'lifecycle':'P60 forced Revival wait and terminal availability',
'authority':'P60 altered copied row fields and post-preparation rollback'}
if name=='build':args=[node,'node_modules/typescript/bin/tsc','-p','tsconfig.json'];cwd=r/'sim-core'
elif name=='parity':args=[node,'/private/tmp/neural-prompt60/parity.cjs'];cwd=r
else:args=[node,'--test','--test-reporter=spec','--test-name-pattern=^'+selectors[name]+'$','sim-core/dist/tests/owned_request_details.test.js'];cwd=r
e=dict(os.environ)
for k in list(e):
 if k in ('PYTHONUTF8','PYTHONIOENCODING') or k.startswith(('REPORT_','PROMPT')):e.pop(k)
e.update(PYTHON='/Users/nbolger/Desktop/neural-showdown/.venv-simulator/bin/python',PYTHONPATH=str(r/'trainer/src'))
print('RUN',str(cwd),args,flush=True);start=time.monotonic();p=subprocess.Popen(args,cwd=cwd,env=e,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,start_new_session=True)
def kill():
 try:os.killpg(p.pid,signal.SIGKILL)
 except ProcessLookupError:pass
timer=threading.Timer(180,kill);timer.start();lines=[]
try:
 for line in p.stdout:print(line,end='',flush=True);lines.append(line)
 code=p.wait()
finally:timer.cancel()
log=d/('perspective-fidelity-prompt60-'+name+'.log');n=1
while log.exists():log=d/('perspective-fidelity-prompt60-'+name+'-attempt'+str(n)+'.log');n+=1
log.write_text(''.join(lines));f=d/'perspective-fidelity-prompt60-commands.json';history=json.loads(f.read_text()) if f.exists() else [];history.append(dict(name=name,args=args,cwd=str(cwd),exit=code,seconds=round(time.monotonic()-start,3),timeout_seconds=180,log=log.name));f.write_text(json.dumps(history,indent=2)+'\n');print('EXIT',code,flush=True);sys.exit(code)
