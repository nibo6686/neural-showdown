"""Prompt 15: protected-baseline verification (prompt14 style) + hashes.json/validation.json. No production file is written."""
import hashlib, json, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; PLAN = ROOT / 'docs/planning'; PREFIX = 'perspective-fidelity-prompt15-'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
base = json.loads((PLAN / 'perspective-fidelity-prompt12-source-baseline.json').read_bytes())
accepted = {}
for n in ('prompt12-source', 'prompt13', 'prompt14'):
    accepted.update(json.loads((PLAN / f'perspective-fidelity-{n}-hashes.json').read_bytes())['candidate_files'])
mine = lambda p: p.startswith('docs/planning/' + PREFIX)
changes = {p: h for p, h in base['hashes'].items() if not (ROOT / p).is_file() or sha(ROOT / p) != h}
lead_drift = [p for p in changes if p.startswith('docs/planning/') and not mine(p)]
prod_changes = {p: c for p, c in changes.items() if p not in lead_drift}
acc = {p: v['after'] for p, v in accepted.items() if p.startswith(('sim-core/', 'trainer/', 'docs/contracts/'))}
acc_bad = [p for p, h in acc.items() if not (ROOT / p).is_file() or sha(ROOT / p) != h]
listed = subprocess.check_output(['git', 'ls-files', '-o', '-m', '--exclude-standard'], cwd=ROOT, text=True).splitlines()
known = set(base['hashes']) | set(base['post_12c_planning_files_not_in_the_12c_inventory']) | set(acc)
unexpected = sorted(p for p in listed if p not in known and not mine(p) and not p.startswith(('docs/planning/', '.claude/')))
out = {'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(), 'protected_entries': len(base['hashes']),
       'protected_unchanged': len(base['hashes']) - len(changes), 'lead_planning_drift': lead_drift, 'protected_production_changes': list(prod_changes),
       'accepted_p12_p14_files_checked': len(acc), 'accepted_changed': acc_bad, 'unexpected_files_outside_scope': unexpected,
       'owned_hashes': {p.name: sha(p) for p in sorted(PLAN.glob(PREFIX + '*')) if p.is_file() and p.name != PREFIX + 'hashes.json'}}
(PLAN / (PREFIX + 'hashes.json')).write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: v for k, v in out.items() if k != 'owned_hashes'}, indent=1))
assert not prod_changes and not acc_bad and not unexpected
