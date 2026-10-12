"""Prompt 12 (PK-02B-Source) scoped validation/preservation. Reproduces the commands in validation.json.

Run from anywhere: python docs/planning/perspective-fidelity-prompt12-source-check-candidate.py
Encoding overrides are removed from the child environment. No historical evidence is regenerated.
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
PREFIX = 'perspective-fidelity-prompt12-source-'
OWNED = ['sim-core/src/perspective_knowledge_source.ts', 'trainer/src/neural/perspective_knowledge_source.py',
         'sim-core/tests/perspective_knowledge_source.test.ts', 'trainer/tests/test_perspective_knowledge_source.py']
# Evidence helper owned by this task: shared by both runtimes' tests (real harness + audit builder).
WITNESS = 'docs/planning/perspective-fidelity-prompt12-witness.cjs'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
write = lambda name, value: (PLAN / (PREFIX + name)).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
env = {k: v for k, v in os.environ.items() if k.upper() not in ('PYTHONUTF8', 'PYTHONIOENCODING')}
env['PYTHONPATH'] = str(ROOT / 'trainer/src'); env['PYTHON'] = sys.executable

COMMANDS = [
    ('sim-core', ['npm.cmd', 'run', 'build'], 'build.log', 'fresh tsc build'),
    ('sim-core', ['node', '--test', '--test-isolation=none', 'dist/tests/perspective_knowledge_source.test.js'], 'ts-source.log', 'new TS paired suite'),
    ('.', [sys.executable, '-m', 'unittest', 'trainer.tests.test_perspective_knowledge_source'], 'python-source.log', 'new Python paired suite'),
    ('sim-core', ['node', '--test', '--test-isolation=none', 'dist/tests/perspective_knowledge.test.js'], 'ts-core.log', 'retained TS knowledge core suite'),
    ('.', [sys.executable, '-m', 'unittest', 'trainer.tests.test_perspective_knowledge'], 'python-core.log', 'retained Python knowledge core suite'),
    ('.', [sys.executable, 'docs/contracts/fixtures/perspective-knowledge-v1/check_contract.py'], 'contract.log', 'retained contract checker'),
    ('sim-core', ['node', '--test', '--test-isolation=none', 'dist/tests/pipeline_integration.test.js', 'dist/tests/record_identity.test.js'], 'ts-legacy.log', 'ordinary affected TS legacy validators'),
    ('.', [sys.executable, '-m', 'unittest', 'trainer.tests.test_pipeline_record'], 'python-legacy.log', 'ordinary affected Python legacy validators'),
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
    results.append({'label': label, 'cwd': cwd, 'argv': args, 'exit_code': run.returncode, 'elapsed_seconds': round(time.monotonic() - start, 3),
                    'counts': counts(run.stdout + run.stderr), 'log': PREFIX + log})
    write('validation.json', {'encoding_overrides_unset': True, 'python': sys.executable, 'commands': results})
    print(label, 'exit', run.returncode, results[-1]['counts'], flush=True)
    assert run.returncode == 0, label

# Explicit trailing-whitespace check on owned untracked files (git diff --check ignores them).
for name in OWNED + [WITNESS]:
    assert all(line.rstrip() == line for line in (ROOT / name).read_text(encoding='utf-8').splitlines()), name

base = json.loads((PLAN / (PREFIX + 'baseline.json')).read_bytes())
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == base['head']
changes = {p: {'expected': h, 'current': sha(ROOT / p) if (ROOT / p).is_file() else None}
           for p, h in base['hashes'].items() if not (ROOT / p).is_file() or sha(ROOT / p) != h}
assert not changes, changes
# Every other non-ignored change must be one of mine or a recorded lead planning file.
listed = subprocess.check_output(['git', 'ls-files', '-o', '-m', '--exclude-standard'], cwd=ROOT, text=True).splitlines()
known = set(base['hashes']) | set(base['post_12c_planning_files_not_in_the_12c_inventory']) | set(OWNED)
unexpected = sorted(p for p in listed if p not in known and not p.startswith('docs/planning/' + PREFIX) and p != WITNESS
                    and not p.startswith('.claude/'))
lead_now = {p: (sha(ROOT / p) if (ROOT / p).is_file() else None) for p in base['post_12c_planning_files_not_in_the_12c_inventory']}
lead_drift = {p: h for p, h in lead_now.items() if h != base['post_12c_planning_files_not_in_the_12c_inventory'][p]}

diff = []; candidate = {}
for name in OWNED + [WITNESS]:
    current = (ROOT / name).read_text(encoding='utf-8')
    diff.extend(difflib.unified_diff([], current.splitlines(keepends=True), fromfile='/dev/null', tofile='candidate-after/' + name))
    candidate[name] = {'before': None, 'after': sha(ROOT / name)}
(PLAN / (PREFIX + 'local.diff')).write_text(''.join(diff), encoding='utf-8')
write('hashes.json', {'head': base['head'], 'protected_entries': len(base['hashes']), 'protected_unchanged': len(base['hashes']) - len(changes),
                      'protected_changes': changes, 'candidate_files': candidate, 'diff_sha256': sha(PLAN / (PREFIX + 'local.diff')),
                      'unexpected_changed_or_untracked_files_outside_scope': unexpected,
                      'lead_planning_files_recorded': len(lead_now), 'lead_planning_files_drift_since_baseline': lead_drift})
dependency_files = ['sim-core/src/perspective_knowledge.ts', 'sim-core/src/belief_state.ts', 'sim-core/src/pipeline_integration.ts', 'sim-core/src/canonical_action.ts',
                    'trainer/src/neural/perspective_knowledge.py', 'trainer/src/neural/pipeline_record.py', 'trainer/src/neural/ts_identity.py',
                    'trainer/src/neural/typed_state.py', 'trainer/src/neural/public_boosts.py', 'trainer/src/neural/dataset_lineage.py',
                    'docs/contracts/fixtures/perspective-knowledge-v1/schema.json', 'docs/contracts/fixtures/perspective-knowledge-v1/profiles.json',
                    'docs/contracts/fixtures/perspective-knowledge-v1/property-types.json', 'docs/contracts/fixtures/perspective-knowledge-v1/property-contexts.json',
                    'docs/contracts/fixtures/perspective-knowledge-v1/typed-references.json', 'docs/contracts/fixtures/perspective-knowledge-v1/identity-vectors.json',
                    'docs/contracts/fixtures/perspective-knowledge-v1/sim-ordinary.json', 'docs/contracts/fixtures/perspective-knowledge-v1/replay-full.json',
                    'sim-core/node_modules/pokemon-showdown/package.json']
write('artifact-hashes.json', {'owned_candidate_hashes': {k: v['after'] for k, v in candidate.items()},
                               'direct_dependency_hashes_unchanged_by_this_task': {name: sha(ROOT / name) for name in dependency_files}})
print('protected', len(base['hashes']), 'changes', len(changes), 'unexpected', unexpected, 'lead drift', list(lead_drift), flush=True)
