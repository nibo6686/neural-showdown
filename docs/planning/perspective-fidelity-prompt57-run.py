from pathlib import Path
import subprocess,os,signal,time,json,threading,sys
R=Path('/Users/nbolger/Documents/Codex/2026-09-24/files-mentioned-by-the-user-neural/native11-recovery-2026-10-14/candidate');D=Path('/Users/nbolger/Desktop/neural-showdown/docs/planning');node='/Users/nbolger/.nvm/versions/node/v24.21.0/bin/node';python='/Users/nbolger/Desktop/neural-showdown/.venv-simulator/bin/python'
def run(name,args,cwd=R):
 env=dict(os.environ)
 for k in list(env):
  if k in ('PYTHONUTF8','PYTHONIOENCODING') or k.startswith(('REPORT_','PROMPT')):env.pop(k)
 env.update(PYTHON=python,PYTHONPATH=str(R/'trainer/src'));print('RUN',name,args,flush=True);start=time.monotonic();p=subprocess.Popen(args,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,start_new_session=True)
 def kill():
  try:os.killpg(p.pid,signal.SIGKILL)
  except ProcessLookupError:pass
 timer=threading.Timer(180,kill);timer.start();lines=[]
 try:
  for line in p.stdout:print(line,end='',flush=True);lines.append(line)
  code=p.wait()
 finally:timer.cancel()
 stem='perspective-fidelity-prompt57-'+name;log=D/(stem+'.log');counter=1
 while log.exists():log=D/(stem+'-attempt'+str(counter)+'.log');counter+=1
 log.write_text(''.join(lines));f=D/'perspective-fidelity-prompt57-commands.json';commands=json.loads(f.read_text()) if f.exists() else [];commands.append({'name':name,'args':args,'cwd':str(cwd),'exit':code,'seconds':round(time.monotonic()-start,3),'timeout_seconds':180,'log':log.name});f.write_text(json.dumps(commands,indent=2)+'\n');return code
if __name__=='__main__':
 if sys.argv[1]=='build':raise SystemExit(run('build',[node,'node_modules/typescript/bin/tsc','-p','tsconfig.json'],R/'sim-core'))
 if sys.argv[1]=='ts':raise SystemExit(run(sys.argv[2].replace(' ','-'),[node,'--test','--test-reporter=spec','--test-name-pattern=^'+sys.argv[2]+'$','sim-core/dist/tests/'+sys.argv[3]+'.test.js']))
