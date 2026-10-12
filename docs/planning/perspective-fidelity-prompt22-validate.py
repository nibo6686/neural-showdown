"""Focused Prompt22 runner; no historical report regeneration or publication."""
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
ENV = dict(os.environ,PYTHON=PYTHON,PYTHONPATH=str(ROOT/'trainer/src'))
for key in ['PYTHONUTF8','PYTHONIOENCODING','PERSPECTIVE_REPLAY_REPORT','LOCAL_REPLAY_HTML_REPORT',
            'PERSPECTIVE_REPLAY_REQUIREMENTS','PROMPT19_REPORT','PROMPT20_REPORT','PROMPT21_REPORT','PROMPT22_REPORT']:
    ENV.pop(key,None)
checks = [
    ('build',['node','node_modules/typescript/bin/tsc','-p','tsconfig.json'],ROOT/'sim-core',{},0),
    ('source-characterization',['node','--test','--test-isolation=none','sim-core/dist/tests/original_owner_provider_characterization.test.js'],ROOT,
     {'PROMPT22_REPORT':str(OUT/'perspective-fidelity-prompt22-source-matrix.json')},0),
    ('accepted-source-seam',['node','--test','--test-isolation=none','sim-core/dist/tests/perspective_knowledge_source.test.js'],ROOT,{},0),
    ('accepted-restoration',['node','--test','--test-isolation=none','sim-core/dist/tests/active_request_restore.test.js'],ROOT,{},0),
    ('accepted-history-adapter',['node','--test','--test-isolation=none','sim-core/dist/tests/public_move_history.test.js','sim-core/dist/tests/replay_import.test.js'],ROOT,{},0),
    ('python-characterization',[PYTHON,'-m','unittest','-v','trainer.tests.test_perspective_replay_characterization'],ROOT,{},0),
    ('ts-characterization',['node','--test','--test-isolation=none','sim-core/dist/tests/perspective_replay_characterization.test.js'],ROOT,{},0),
    ('python-requirements',[PYTHON,'-m','unittest','-v','trainer.tests.test_perspective_replay_characterization'],ROOT,
     {'PERSPECTIVE_REPLAY_REQUIREMENTS':'1'},1),
    ('ts-requirements',['node','--test','--test-isolation=none','sim-core/dist/tests/perspective_replay_characterization.test.js'],ROOT,
     {'PERSPECTIVE_REPLAY_REQUIREMENTS':'1'},1),
    ('git-diff-check',['git','diff','--check'],ROOT,{},0),
]
results = []
for label,argv,cwd,extra,expected in checks:
    start = time.monotonic()
    child = subprocess.run(argv,cwd=cwd,env=dict(ENV,**extra),capture_output=True,timeout=60)
    raw = child.stdout+child.stderr
    text = raw.decode('utf-8',errors='replace')
    results.append(dict(label=label,argv=argv,cwd=str(cwd),extra_environment=extra,
        encoding_overrides='both unset',PYTHON=PYTHON,PYTHONPATH=ENV['PYTHONPATH'],exit_code=child.returncode,
        expected_exit=expected,seconds=round(time.monotonic()-start,3),output=text,
        counts=re.findall(r'(?:Ran \d+ tests?|(?:tests|pass|fail) \d+)',text),
        raw_output_sha256=hashlib.sha256(raw).hexdigest(),raw_output_base64=base64.b64encode(raw).decode()))
    (OUT/'perspective-fidelity-prompt22-validation.json').write_bytes((json.dumps(results,indent=2)+'\n').encode())
    print(label,child.returncode,results[-1]['counts'],flush=True)
    if child.returncode != expected:
        raise SystemExit('Unexpected result: '+label)
