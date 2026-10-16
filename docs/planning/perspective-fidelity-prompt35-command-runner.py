from pathlib import Path
import subprocess,os,signal,time,json,threading,hashlib,sys
R=Path('/Users/nbolger/Desktop/neural-showdown');O=R/'docs/planning';node='/Users/nbolger/.nvm/versions/node/v24.21.0/bin/node';python=str(R/'.venv-simulator/bin/python');env=dict(os.environ)
for k in list(env):
 if k in ('PYTHONUTF8','PYTHONIOENCODING') or k.startswith(('REPORT_','PROMPT')):env.pop(k)
env.update(PYTHON=python,PYTHONPATH=str(R/'trainer/src'))
def run(name,args,cwd=R):
 print('RUN',name,args,flush=True);started=time.monotonic();p=subprocess.Popen(args,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,start_new_session=True)
 def kill():
  try:os.killpg(p.pid,signal.SIGKILL)
  except ProcessLookupError:pass
 timer=threading.Timer(180,kill);timer.start();lines=[]
 try:
  for line in p.stdout:print(line,end='',flush=True);lines.append(line)
  code=p.wait()
 finally:timer.cancel()
 (O/('perspective-fidelity-prompt35-'+name+'.log')).write_text(''.join(lines));f=O/'perspective-fidelity-prompt35-commands.json';commands=json.loads(f.read_text()) if f.exists() else [];commands.append({'name':name,'args':args,'cwd':str(cwd),'exit':code,'seconds':round(time.monotonic()-started,3),'timeout_seconds':180});f.write_text(json.dumps(commands,indent=2)+'\n');return code
if __name__=='__main__':
 mode=sys.argv[1]
 if mode=='build':raise SystemExit(run(sys.argv[2] if len(sys.argv)>2 else 'build',[node,'node_modules/typescript/bin/tsc','-p','tsconfig.json'],R/'sim-core'))
 if mode=='ts':raise SystemExit(run(sys.argv[2].replace(' ','-'),[node,'--test','--test-reporter=spec','--test-name-pattern=^P35 '+sys.argv[2]+'$','sim-core/dist/tests/target_inventory.test.js']))
 if mode=='py':raise SystemExit(run(sys.argv[2],[python,'-m','pytest','-s','-vv','trainer/tests/test_target_inventory.py::'+sys.argv[2]]))
