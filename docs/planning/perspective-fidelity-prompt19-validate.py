"""Bounded, non-publishing Prompt19 evidence runner. Historical reports stay untouched."""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs/planning'
PYTHON = r'D:\Anaconda\envs\neuralgpu\python.exe'
ENV = dict(os.environ, PYTHON=PYTHON, PYTHONPATH=str(ROOT / 'trainer/src'))
for key in ['PYTHONUTF8', 'PYTHONIOENCODING', 'PERSPECTIVE_REPLAY_REPORT',
            'LOCAL_REPLAY_HTML_REPORT', 'PERSPECTIVE_REPLAY_REQUIREMENTS', 'PROMPT19_REPORT']:
    ENV.pop(key, None)

checks = [
    ('build', ['node', 'node_modules/typescript/bin/tsc', '-p', 'tsconfig.json'], ROOT / 'sim-core', {}, 0),
    ('adapter', ['node', '--test', '--test-isolation=none', 'sim-core/dist/tests/replay_import.test.js'], ROOT,
     {'PROMPT19_REPORT': str(OUT / 'perspective-fidelity-prompt19-result-matrix.json')}, 0),
    ('loader', [PYTHON, '-m', 'unittest', '-v', 'trainer.tests.test_local_replay_html_transport'], ROOT, {}, 0),
    ('python-characterization', [PYTHON, '-m', 'unittest', '-v', 'trainer.tests.test_perspective_replay_characterization'], ROOT, {}, 0),
    ('python-requirements', [PYTHON, '-m', 'unittest', '-v', 'trainer.tests.test_perspective_replay_characterization'], ROOT,
     {'PERSPECTIVE_REPLAY_REQUIREMENTS': '1'}, 1),
    ('parser', [PYTHON, '-m', 'unittest', '-v',
        'trainer.tests.test_public_replays.PublicReplayParserTest.test_protocol_log_parser_extracts_battle_events',
        'trainer.tests.test_public_replays.PublicReplayParserTest.test_disconnect_line_followed_by_win_preserves_winner',
        'trainer.tests.test_public_replays.PublicReplayParserTest.test_inactive_timer_line_followed_by_win_preserves_winner'], ROOT, {}, 0),
    ('ts-characterization', ['node', '--test', '--test-isolation=none', 'sim-core/dist/tests/perspective_replay_characterization.test.js'], ROOT, {}, 0),
    ('ts-requirements', ['node', '--test', '--test-isolation=none', 'sim-core/dist/tests/perspective_replay_characterization.test.js'], ROOT,
     {'PERSPECTIVE_REPLAY_REQUIREMENTS': '1'}, 1),
    ('git-diff-check', ['git', 'diff', '--check'], ROOT, {}, 0),
]
results = []
for label, argv, cwd, extra, expected in checks:
    start = time.monotonic()
    child = subprocess.run(argv, cwd=cwd, env=dict(ENV, **extra), capture_output=True, timeout=60)
    raw = child.stdout + child.stderr
    text = raw.decode('utf-8', errors='replace')
    item = dict(label=label, argv=argv, cwd=str(cwd), extra_environment=extra,
                encoding_overrides='both unset', PYTHON=PYTHON, PYTHONPATH=ENV['PYTHONPATH'],
                exit_code=child.returncode, expected_exit=expected, seconds=round(time.monotonic()-start, 3),
                counts=re.findall(r'(?:Ran \d+ tests?|(?:tests|pass|fail) \d+)', text), output=text,
                raw_output_sha256=hashlib.sha256(raw).hexdigest(), raw_output_base64=base64.b64encode(raw).decode())
    results.append(item)
    (OUT / 'perspective-fidelity-prompt19-validation.json').write_bytes((json.dumps(results, indent=2)+'\n').encode())
    print(label, child.returncode, item['counts'], flush=True)
    if child.returncode != expected:
        raise SystemExit(f'Unexpected {label} result; inspect validation.json')
