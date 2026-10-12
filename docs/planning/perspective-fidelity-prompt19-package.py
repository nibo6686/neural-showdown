"""Check preservation and package only Prompt19's local additions."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs/planning'
PREFIX = 'perspective-fidelity-prompt19-'
BASE = json.loads((OUT / (PREFIX+'baseline.json')).read_text())

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

protected = [{'path': name, 'before': before,
              'after': digest(ROOT/name) if (ROOT/name).is_file() else None}
             for name, before in BASE['protected'].items()]
mismatches = [item for item in protected if item['before'] != item['after']]
if mismatches:
    raise SystemExit('Protected files changed: '+json.dumps(mismatches))
lead = OUT / (PREFIX+'plan-review.md')
late = {'path': lead.relative_to(ROOT).as_posix(), 'sha256': digest(lead),
        'last_write_ns': lead.stat().st_mtime_ns,
        'note': 'Preexisting lead evidence omitted by initial filename-prefix exclusion; late pin, not a preimplementation hash comparison.'}
compiler = {p.relative_to(ROOT).as_posix():digest(p) for p in (ROOT/'sim-core/dist').rglob('*') if p.is_file()}
compiler_changes = [{'path': name, 'before': BASE['compiler'].get(name), 'after': after}
                    for name, after in compiler.items() if BASE['compiler'].get(name) != after]
compiler_deleted = [name for name in BASE['compiler'] if name not in compiler]
files = [ROOT/'sim-core/src/replay_import.ts', ROOT/'sim-core/tests/replay_import.test.ts']
files += sorted(p for p in OUT.glob(PREFIX+'*') if p.is_file()
                and p.name not in [PREFIX+'plan-review.md', PREFIX+'candidate.diff', PREFIX+'hash-inventory.json'])
diff = bytearray()
checks = []
for p in files:
    name = p.relative_to(ROOT).as_posix()
    cmd = ['git','-c','core.autocrlf=false','-c',
           'core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol',
           'diff','--no-index','--check','--','/dev/null',name]
    check = subprocess.run(cmd,cwd=ROOT,capture_output=True)
    checks.append({'argv':cmd,'exit_code':check.returncode,'output':check.stdout.decode()+check.stderr.decode()})
    if check.returncode not in [0,1] or check.stdout:
        raise SystemExit('New-file whitespace error: '+name+' '+checks[-1]['output'])
    child = subprocess.run(['git','-c','core.autocrlf=false','diff','--no-index','--','/dev/null',name],cwd=ROOT,capture_output=True)
    if child.returncode != 1:
        raise SystemExit('Unexpected new-file diff result: '+name)
    diff.extend(child.stdout)
diff_path = OUT / (PREFIX+'candidate.diff')
diff_path.write_bytes(diff)
inventory = dict(head=BASE['head'],current_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),
                 protected_count=len(protected),protected_mismatches=mismatches,protected=protected,
                 late_pinned_preexisting_evidence=late,
                 candidate=[{'path':p.relative_to(ROOT).as_posix(),'sha256':digest(p),'bytes':p.stat().st_size} for p in files],
                 compiler_changes=compiler_changes,compiler_deleted=compiler_deleted,compiler=compiler,
                 diff={'path':diff_path.relative_to(ROOT).as_posix(),'sha256':digest(diff_path),'bytes':len(diff)},
                 new_file_whitespace_checks=checks)
assert inventory['head']==inventory['current_head']
(OUT / (PREFIX+'hash-inventory.json')).write_bytes((json.dumps(inventory,indent=2)+'\n').encode())
print('Protected',len(protected),'mismatches',len(mismatches),'candidate',len(files),'compiler changes',len(compiler_changes),'deleted',len(compiler_deleted))
for item in compiler_changes:
    print(item['path'],item['before'],item['after'])
