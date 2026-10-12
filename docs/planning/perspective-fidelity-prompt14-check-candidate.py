"""Prompt 14 (S01b) scoped validation/preservation. Reproduces the commands in validation.json.

Run from anywhere: python docs/planning/perspective-fidelity-prompt14-check-candidate.py
Encoding overrides are removed from the child environment. No production file is written; the only
outputs are perspective-fidelity-prompt14-* evidence files.
"""
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / 'docs/planning'
PREFIX = 'perspective-fidelity-prompt14-'
OWNED = ['sim-core/src/request_knowledge.ts', 'trainer/src/neural/request_knowledge.py', 'sim-core/tests/request_knowledge.test.ts',
         'trainer/tests/test_request_knowledge.py', 'docs/contracts/REQUEST_KNOWLEDGE.md']
EVIDENCE_HELPERS = ['docs/planning/perspective-fidelity-prompt14-witness.cjs', 'docs/planning/perspective-fidelity-prompt14-check-candidate.py']
BASELINE = PLAN / 'perspective-fidelity-prompt12-source-baseline.json'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
write = lambda name, value: (PLAN / (PREFIX + name)).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
env = {k: v for k, v in os.environ.items() if k.upper() not in ('PYTHONUTF8', 'PYTHONIOENCODING')}
env['PYTHONPATH'] = str(ROOT / 'trainer/src'); env['PYTHON'] = sys.executable

COMMANDS = [
    ('sim-core', ['npm.cmd', 'run', 'build'], 'build.log', 'fresh tsc build'),
    ('sim-core', ['node', '--test', '--test-isolation=none', 'dist/tests/request_knowledge.test.js'], 'ts-validation.log', 'new TS request-knowledge suite'),
    ('.', [sys.executable, '-m', 'unittest', 'trainer.tests.test_request_knowledge', '-v'], 'python-validation.log', 'new Python request-knowledge suite'),
    ('sim-core', ['node', '--test', '--test-isolation=none', 'dist/tests/request_knowledge_characterization.test.js'], 'ts-characterization.log', 'unchanged Prompt 13 TS characterization (current observation behavior)'),
    ('.', [sys.executable, '-m', 'unittest', 'trainer.tests.test_request_knowledge_characterization'], 'python-characterization.log', 'unchanged Prompt 13 Python characterization'),
    ('sim-core', ['node', '--test', '--test-isolation=none', 'dist/tests/action_codec.test.js', 'dist/tests/observable_state.test.js',
                  'dist/tests/pipeline_integration.test.js', 'dist/tests/record_identity.test.js'], 'ts-retained.log', 'retained TS request/observation/pipeline/identity suites'),
    ('sim-core', ['node', '--test', '--test-isolation=none', 'dist/tests/perspective_knowledge.test.js', 'dist/tests/perspective_knowledge_source.test.js'], 'ts-knowledge.log', 'retained TS perspective-knowledge core + source suites (imported parser)'),
    ('.', [sys.executable, '-m', 'unittest', 'trainer.tests.test_pipeline_record', 'trainer.tests.test_perspective_knowledge', 'trainer.tests.test_perspective_knowledge_source'], 'python-retained.log', 'retained Python pipeline record + perspective-knowledge suites'),
    ('.', [sys.executable, 'docs/contracts/fixtures/perspective-knowledge-v1/check_contract.py'], 'contract.log', 'retained perspective-knowledge contract checker'),
    ('.', ['git', 'diff', '--check'], 'diff-check.log', 'tracked-file whitespace (CRLF warnings pre-existing)'),
]


def counts(log):
    text = log.decode('utf-8', errors='replace')
    out = {}
    for key in ('tests', 'pass', 'fail', 'cancelled', 'skipped'):
        match = re.search(r'ℹ ' + key + r' (\d+)', text)
        if match:
            out[key] = int(match.group(1))
    ran = re.search(r'Ran (\d+) tests? in', text)
    if ran:
        out['tests'] = int(ran.group(1)); out['fail'] = 0 if re.search(r'^OK', text, re.M) else None
    return out


results = []
for cwd, args, log, label in COMMANDS:
    start = time.monotonic()
    run = subprocess.run(args, cwd=ROOT / cwd, env=env, capture_output=True, timeout=1500)
    (PLAN / (PREFIX + log)).write_bytes(run.stdout + run.stderr)
    results.append({'label': label, 'cwd': cwd, 'argv': [Path(a).name if a == sys.executable else a for a in args], 'exit_code': run.returncode,
                    'elapsed_seconds': round(time.monotonic() - start, 3), 'counts': counts(run.stdout + run.stderr), 'log': PREFIX + log})
    write('validation.json', {'encoding_overrides_unset': True, 'python': sys.executable, 'commands': results})
    print(label, 'exit', run.returncode, results[-1]['counts'], flush=True)
    assert run.returncode == 0, label

# Evidence: ids of every record built by the TS module under test (regression pins, not independent oracles).
witness = subprocess.run(['node', str(PLAN / (PREFIX + 'witness.cjs'))], cwd=ROOT, env=env, capture_output=True, timeout=600)
assert witness.returncode == 0, witness.stderr.decode('utf-8', 'replace')[:400]
data = json.loads(witness.stdout.decode('utf-8'))
ids = {case: {key: record['id'] for key, record in records.items()} for case, records in data['records'].items()}
write('record-ids.json', {'purpose': 'rkn ids built by sim-core/dist/src/request_knowledge.js from the prompt13/14 witness (28 cases); regression pins',
                          'cases': len(data['cases']), 'records': sum(len(v) for v in ids.values()), 'ids': ids})

# Protected baseline: every protected file byte-identical; every other change is mine or a lead planning file.
base = json.loads(BASELINE.read_bytes())
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
assert head == base['head']
mine = lambda p: p.startswith('docs/planning/' + PREFIX)
changes = {p: {'expected': h, 'current': sha(ROOT / p) if (ROOT / p).is_file() else None}
           for p, h in base['hashes'].items() if not (ROOT / p).is_file() or sha(ROOT / p) != h}
# Lead planning files may drift (they are the lead's); everything else protected must be byte-identical.
lead_protected_drift = {p: c for p, c in changes.items() if p.startswith('docs/planning/') and not mine(p)}
changes = {p: c for p, c in changes.items() if p not in lead_protected_drift}
# Prompt 12-source files were accepted after the baseline was taken: must equal their accepted candidate hashes.
accepted = json.loads((PLAN / 'perspective-fidelity-prompt12-source-hashes.json').read_bytes())['candidate_files']
accepted.update(json.loads((PLAN / 'perspective-fidelity-prompt13-hashes.json').read_bytes())['candidate_files'])  # Prompt 13 accepted candidate files
accepted_check = {p: {'accepted': v['after'], 'current': sha(ROOT / p) if (ROOT / p).is_file() else None} for p, v in accepted.items() if p.startswith(('sim-core/', 'trainer/'))}
accepted_changes = {p: v for p, v in accepted_check.items() if v['accepted'] != v['current']}
listed = subprocess.check_output(['git', 'ls-files', '-o', '-m', '--exclude-standard'], cwd=ROOT, text=True).splitlines()
known = set(base['hashes']) | set(base['post_12c_planning_files_not_in_the_12c_inventory']) | set(OWNED) | set(accepted_check)
lead_new = sorted(p for p in listed if p not in known and not mine(p) and p.startswith('docs/planning/'))
unexpected = sorted(p for p in listed if p not in known and not mine(p) and not p.startswith('docs/planning/') and not p.startswith('.claude/'))
lead_now = {p: (sha(ROOT / p) if (ROOT / p).is_file() else None) for p in base['post_12c_planning_files_not_in_the_12c_inventory']}
lead_drift = {p: h for p, h in lead_now.items() if h != base['post_12c_planning_files_not_in_the_12c_inventory'][p]}

diff, candidate = [], {}
for name in OWNED + EVIDENCE_HELPERS:
    current = (ROOT / name).read_text(encoding='utf-8')
    assert all(line.rstrip() == line for line in current.splitlines()), 'trailing whitespace in ' + name
    diff.extend(difflib.unified_diff([], current.splitlines(keepends=True), fromfile='/dev/null', tofile='candidate-after/' + name))
    candidate[name] = {'before': None, 'after': sha(ROOT / name)}
(PLAN / (PREFIX + 'local.diff')).write_text(''.join(diff), encoding='utf-8')
write('hashes.json', {'head': head, 'baseline': BASELINE.name, 'protected_entries': len(base['hashes']), 'protected_unchanged': len(base['hashes']) - len(changes),
                      'protected_changes': changes, 'lead_planning_protected_drift': lead_protected_drift, 'accepted_prompt12_source_files': accepted_check,
                      'baseline_sha256': sha(BASELINE), 'candidate_files': candidate, 'diff_sha256': sha(PLAN / (PREFIX + 'local.diff')),
                      'unexpected_changed_or_untracked_files_outside_scope': unexpected,
                      'lead_planning_files_not_in_baseline_inventory': lead_new,
                      'lead_planning_files_recorded': len(lead_now), 'lead_planning_files_drift_since_baseline': lead_drift})
write('artifact-hashes.json', {'owned_candidate_hashes': {k: v['after'] for k, v in candidate.items()},
                               'direct_dependency_hashes_unchanged_by_this_task': {name: sha(ROOT / name) for name in [
                                   'sim-core/src/action_codec.ts', 'sim-core/src/observable_state.ts', 'sim-core/src/state_extractor.ts', 'sim-core/src/env_manager.ts',
                                   'sim-core/src/pipeline_integration.ts', 'sim-core/src/types.ts', 'trainer/src/neural/pipeline_record.py', 'trainer/src/neural/ts_identity.py',
                                   'sim-core/src/perspective_knowledge.ts', 'trainer/src/neural/perspective_knowledge.py', 'trainer/src/neural/ts_identity.py',
                                   'trainer/src/neural/perspective_knowledge_source.py', 'docs/contracts/PERSPECTIVE_KNOWLEDGE.md', 'docs/planning/perspective-fidelity-prompt13-witness.cjs',
                                   'sim-core/node_modules/pokemon-showdown/package.json', 'sim-core/node_modules/pokemon-showdown/dist/sim/pokemon.js']}})
print('protected', len(base['hashes']), 'changes', len(changes), 'lead drift (protected)', list(lead_protected_drift), 'unexpected', unexpected, 'lead new', lead_new, 'lead drift', list(lead_drift), flush=True)
assert not changes and not unexpected and not accepted_changes, (changes, unexpected, accepted_changes)
