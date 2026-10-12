"""Package owned additions and verify all starting work without staging."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'docs/planning'
PREFIX = 'perspective-fidelity-prompt20-'
BASE = json.loads((OUT/(PREFIX+'baseline.json')).read_text())
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

protected = [{'path':name,'before':before,'after':digest(ROOT/name) if (ROOT/name).is_file() else None}
             for name,before in BASE['protected'].items()]
config = [{'path':name,'before':before,'after':digest(ROOT/name)} for name,before in BASE['config'].items()]
mismatches = [row for row in protected+config if row['before'] != row['after']]
if mismatches:
    raise SystemExit('Protected changes: '+json.dumps(mismatches))
compiler = {p.relative_to(ROOT).as_posix():digest(p) for p in (ROOT/'sim-core/dist').rglob('*') if p.is_file()}
compiler_changes = [{'path':name,'before':BASE['compiler'].get(name),'after':after}
                    for name,after in compiler.items() if BASE['compiler'].get(name) != after]
deleted = [name for name in BASE['compiler'] if name not in compiler]
files = [ROOT/'sim-core/tests/public_move_retention_characterization.test.ts']
files += [OUT/(PREFIX+suffix) for suffix in ['baseline.json','progress.md','design.md','examples.md',
    'test-plan-review.md','validate.py','validation.json','first-validation.json','result-matrix.json',
    'review.md','report.md','package.py']]
diff = bytearray()
checks = []
for p in files:
    name = p.relative_to(ROOT).as_posix()
    assert name not in BASE['protected'], 'Owned additions cannot overwrite preexisting evidence.'
    argv = ['git','-c','core.autocrlf=false','-c',
            'core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol',
            'diff','--no-index','--check','--','/dev/null',name]
    child = subprocess.run(argv,cwd=ROOT,capture_output=True)
    checks.append({'argv':argv,'exit_code':child.returncode,'output':(child.stdout+child.stderr).decode()})
    if child.returncode not in [0,1] or child.stdout:
        raise SystemExit('Whitespace error: '+name+' '+checks[-1]['output'])
    child = subprocess.run(['git','-c','core.autocrlf=false','diff','--no-index','--','/dev/null',name],cwd=ROOT,capture_output=True)
    assert child.returncode == 1
    diff.extend(child.stdout)
diff_path = OUT/(PREFIX+'candidate.diff')
diff_path.write_bytes(diff)
inventory = dict(head=BASE['head'],branch=BASE['branch'],
    current_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),
    protected_count=len(protected),protected_mismatches=mismatches,protected=protected,config=config,
    candidate=[{'path':p.relative_to(ROOT).as_posix(),'sha256':digest(p),'bytes':p.stat().st_size} for p in files],
    compiler=compiler,compiler_changes=compiler_changes,compiler_deleted=deleted,
    new_file_whitespace_checks=checks,
    diff={'path':diff_path.relative_to(ROOT).as_posix(),'sha256':digest(diff_path),'bytes':len(diff)})
assert inventory['head'] == inventory['current_head']
assert subprocess.check_output(['git','branch','--show-current'],cwd=ROOT).decode().strip() == BASE['branch']
(OUT/(PREFIX+'hash-inventory.json')).write_bytes((json.dumps(inventory,indent=2)+'\n').encode())
print('Protected',len(protected),'config',len(config),'mismatches',len(mismatches),'candidate',len(files),
      'compiler changes',len(compiler_changes),'deleted',len(deleted))
for row in compiler_changes:
    print(row['path'],row['before'],row['after'])
