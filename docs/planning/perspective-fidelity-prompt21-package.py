"""Package this candidate against saved starting bytes, without staging."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'docs/planning'
PREFIX = 'perspective-fidelity-prompt21-'
BASE = json.loads((OUT/(PREFIX+'baseline.json')).read_text())
OWNED = {
    'sim-core/src/replay_import.ts': OUT/(PREFIX+'before-replay_import.ts.txt'),
    'sim-core/tests/replay_import.test.ts': OUT/(PREFIX+'before-replay_import.test.ts.txt'),
}

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

protected = [{'path':name,'before':before,'after':digest(ROOT/name) if (ROOT/name).is_file() else None}
             for name,before in BASE['protected'].items() if name not in OWNED]
config = [{'path':name,'before':before,'after':digest(ROOT/name)} for name,before in BASE['config'].items()]
mismatches = [row for row in protected+config if row['before'] != row['after']]
assert not mismatches, 'Protected changes: '+json.dumps(mismatches)
for name,before_path in OWNED.items():
    assert digest(before_path) == BASE['protected'][name], 'Invalid saved starting bytes: '+name

compiler = {p.relative_to(ROOT).as_posix():digest(p) for p in (ROOT/'sim-core/dist').rglob('*') if p.is_file()}
compiler_changes = [{'path':name,'before':BASE['compiler'].get(name),'after':after}
                    for name,after in compiler.items() if BASE['compiler'].get(name) != after]
deleted = [name for name in BASE['compiler'] if name not in compiler]
assert not deleted
assert {r['path'] for r in compiler_changes} == {
    'sim-core/dist/src/public_move_history.js','sim-core/dist/tests/public_move_history.test.js',
    'sim-core/dist/src/replay_import.js','sim-core/dist/tests/replay_import.test.js',
}

new_files = [ROOT/'sim-core/src/public_move_history.ts',ROOT/'sim-core/tests/public_move_history.test.ts']
new_files += sorted(p for p in OUT.glob(PREFIX+'*') if p.is_file()
                    and p.name not in [PREFIX+'candidate.diff',PREFIX+'hash-inventory.json']
                    and p.relative_to(ROOT).as_posix() not in BASE['protected'])
assert all(p.relative_to(ROOT).as_posix() not in BASE['protected'] for p in new_files)
current_paths = set(subprocess.check_output(
    ['git','ls-files','-z','--cached','--others','--exclude-standard'],cwd=ROOT).decode().split('\0')) - {''}
allowed_new = {p.relative_to(ROOT).as_posix() for p in new_files} | {
    'docs/planning/'+PREFIX+'candidate.diff','docs/planning/'+PREFIX+'hash-inventory.json',
}
unexpected_new = sorted(current_paths - set(BASE['protected']) - allowed_new)
assert not unexpected_new, 'Unowned additions: '+json.dumps(unexpected_new)
diff = bytearray()
checks = []
for p in [ROOT/name for name in OWNED]+new_files:
    name = p.relative_to(ROOT).as_posix()
    old = OWNED.get(name)
    old_name = old.relative_to(ROOT).as_posix() if old else '/dev/null'
    argv = ['git','-c','core.autocrlf=false','-c',
            'core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol',
            'diff','--no-index','--check','--',old_name,name]
    child = subprocess.run(argv,cwd=ROOT,capture_output=True)
    checks.append({'argv':argv,'exit_code':child.returncode,'output':(child.stdout+child.stderr).decode()})
    assert child.returncode in [0,1] and not child.stdout, 'Whitespace: '+name+' '+checks[-1]['output']
    child = subprocess.run(['git','-c','core.autocrlf=false','diff','--no-index','--',old_name,name],cwd=ROOT,capture_output=True)
    assert child.returncode == 1
    delta = child.stdout
    if old:
        delta = delta.replace(('a/'+old_name).encode(),('a/'+name).encode())
    diff.extend(delta)

diff_path = OUT/(PREFIX+'candidate.diff')
diff_path.write_bytes(diff)
files = [ROOT/name for name in OWNED]+new_files
inventory = dict(head=BASE['head'],branch=BASE['branch'],
    current_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),
    protected_count=len(protected),protected_mismatches=mismatches,protected=protected,config=config,
    unexpected_new_files=unexpected_new,
    existing_owned=[{'path':name,'before':BASE['protected'][name],'after':digest(ROOT/name)} for name in OWNED],
    candidate=[{'path':p.relative_to(ROOT).as_posix(),'sha256':digest(p),'bytes':p.stat().st_size} for p in files],
    compiler=compiler,compiler_changes=compiler_changes,compiler_deleted=deleted,
    candidate_whitespace_checks=checks,
    diff={'path':diff_path.relative_to(ROOT).as_posix(),'sha256':digest(diff_path),'bytes':len(diff)})
assert inventory['head'] == inventory['current_head']
assert subprocess.check_output(['git','branch','--show-current'],cwd=ROOT).decode().strip() == BASE['branch']
(OUT/(PREFIX+'hash-inventory.json')).write_bytes((json.dumps(inventory,indent=2)+'\n').encode())
print('Protected',len(protected),'config',len(config),'mismatches',len(mismatches),'candidate',len(files),
      'compiler changes',len(compiler_changes),'deleted',len(deleted))
for row in compiler_changes:
    print(row['path'],row['before'],row['after'])
