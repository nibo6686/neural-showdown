from pathlib import Path
import shutil,json,hashlib,subprocess
r=Path('/Users/nbolger/Desktop/neural-showdown');c=Path('/private/tmp/neural-showdown-native11-prompt38');o=r/'docs/planning';c.mkdir(exist_ok=False);files=set()
for base in ['sim-core/src','sim-core/tests','sim-core/scripts','sim-core/simulator_coverage','trainer/src/neural','trainer/tests','docs/contracts']:
 for p in (r/base).rglob('*'):
  if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and p.stat().st_size<2000000:files.add(p)
for p in (r/'docs/planning').glob('perspective-fidelity-prompt*'):
 if p.suffix in ('.md','.json') and p.stat().st_size<2000000:files.add(p)
for f in ['AGENTS.md','docs/refactor/AGENT_PROTOCOL.md','sim-core/package.json','sim-core/package-lock.json','sim-core/tsconfig.json','trainer/pyproject.toml','pytest.ini']:files.add(r/f)
hashes={}
for p in sorted(files):
 f=p.relative_to(r);dst=c/f;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dst);hashes[str(f)]=hashlib.sha256(p.read_bytes()).hexdigest()
record={'origin':str(r),'candidate':str(c),'branch':subprocess.check_output(['git','branch','--show-current'],cwd=r,text=True).strip(),'HEAD':subprocess.check_output(['git','rev-parse','HEAD'],cwd=r,text=True).strip(),'files':hashes,'exclusions':['.git','environments','node_modules','compiled outputs','private captures','files >=2MB','unrelated owner documents']}
(o/'perspective-fidelity-prompt38-snapshot.json').write_text(json.dumps(record,indent=2)+'\n')
deps={}
for p in (r/'sim-core/node_modules').rglob('*'):
 if p.is_file():deps[str(p.relative_to(r))]=hashlib.sha256(p.read_bytes()).hexdigest()
(o/'perspective-fidelity-prompt38-original-dependencies.json').write_text(json.dumps(deps,indent=2)+'\n')
print('Snapshot inputs',len(hashes),'original dependency files',len(deps),'HEAD',record['HEAD'])
