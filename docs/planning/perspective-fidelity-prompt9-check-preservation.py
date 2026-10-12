"""Read-only PK-01 preservation/provenance comparison; no attestation updates."""
import hashlib
import json
import subprocess
from pathlib import Path

root=Path(__file__).resolve().parents[2]
base=json.loads((root/'docs/planning/perspective-fidelity-prompt9-baseline.json').read_text(encoding='utf-8'))
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()==base['head']
changed=[]
for name,expected in base['hashes'].items():
    file=root/name
    if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest()!=expected: changed.append(name)
assert sorted(changed)==sorted(base['owned_existing']),changed
for name in base['owned_existing']:
    before=(root/'docs/planning'/('perspective-fidelity-prompt9-baseline-'+Path(name).name)).read_bytes()
    assert (root/name).read_bytes().startswith(before),'nonadditive contract edit '+name
dependencies=json.loads((root/'docs/planning/perspective-fidelity-prompt9-dependencies.json').read_text(encoding='utf-8'))
for name,expected in dependencies['sources'].items(): assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected,name
packet=json.loads((root/'docs/planning/perspective-fidelity-prompt7-digest-inputs.json').read_text(encoding='utf-8'))
digest=hashlib.sha256(); drift=[]
for row in packet['inputs']:
    raw=(root/row['repo_path']).read_bytes()
    digest.update(row['manifest_path'].encode('utf-8')+b'\0'+raw.replace(b'\r\n',b'\n')+b'\0')
    if hashlib.sha256(raw).hexdigest()!=row['raw_sha256']: drift.append(row['repo_path'])
assert drift==['docs/contracts/OBSERVABLE_STATE.md','docs/contracts/PIPELINE_EPISODE.md'],drift
assert digest.hexdigest()=='8424f64d539a6528a18531f91ee5606200b69c0f98193d4c3e6fd86de2e0c7fc'
print(json.dumps({'protected_unchanged':len(base['hashes'])-len(changed),'authorized_additive_changes':changed,
                  'provenance_comparison_digest':digest.hexdigest(),'expected_drift_inputs':drift,'attestation_updated':False}))
