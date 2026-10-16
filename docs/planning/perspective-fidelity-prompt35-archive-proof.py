from pathlib import Path
import tarfile,json,hashlib
r=Path('/Users/nbolger/Desktop/neural-showdown');s=Path('/private/tmp/neural-prompt29-20261012')
lookup=json.loads((r/'docs/planning/perspective-fidelity-prompt35-lookup-extraction.json').read_text())['inputs']
selected=json.loads((r/'docs/planning/perspective-fidelity-prompt29-source-evidence.json').read_text())['selected']
checks={}
for version in ['0.11.10','0.11.11']:
 files=list(lookup) if version=='0.11.10' else [row['file'] for row in selected]+['config/config-example.js']
 with tarfile.open(s/(version+'.tgz'),'r:gz') as archive:
  for file in files:
   raw=archive.extractfile('package/'+file).read();unpacked=(s/version/'package'/file).read_bytes();assert raw==unpacked,(version,file)
   if version=='0.11.10':assert hashlib.sha256(raw).hexdigest()==lookup[file]
 checks[version]=len(files)
print(json.dumps({'verified_tar_member_parity':checks,'no_extraction_write':True}))
