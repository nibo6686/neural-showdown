"""Package owned additions and verify all starting work without staging."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'docs/planning'
PREFIX = 'perspective-fidelity-prompt22-'
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
files = [ROOT/'sim-core/tests/original_owner_provider_characterization.test.ts']
files += sorted(p for p in OUT.glob(PREFIX+'*') if p.is_file()
                and p.name not in [PREFIX+'candidate.diff',PREFIX+'hash-inventory.json']
                and p.relative_to(ROOT).as_posix() not in BASE['protected'])
current_paths = set(subprocess.check_output(['git','ls-files','-z','--cached','--others','--exclude-standard'],cwd=ROOT).decode().split('\0')) - {''}
allowed_new = {p.relative_to(ROOT).as_posix() for p in files} | {
    'docs/planning/'+PREFIX+'candidate.diff','docs/planning/'+PREFIX+'hash-inventory.json'}
unexpected_new = sorted(current_paths - set(BASE['protected']) - allowed_new)
assert not unexpected_new, 'Unowned additions: '+json.dumps(unexpected_new)
pinned = [{'path':name,'before':before,'after':digest(ROOT/name)}
          for category in ['pinned_sources','runtime_dependencies'] for name,before in BASE[category].items()]
assert all(row['before'] == row['after'] for row in pinned), 'Pinned dependency drift'
assert not deleted
assert len(compiler_changes) == 1 and compiler_changes[0]['path'] == 'sim-core/dist/tests/original_owner_provider_characterization.test.js'
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
    protected_count=len(protected),protected_mismatches=mismatches,protected=protected,config=config,pinned_dependencies=pinned,unexpected_new_files=unexpected_new,
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
