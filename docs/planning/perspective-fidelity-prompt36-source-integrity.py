from pathlib import Path
import hashlib,json
r=Path('/Users/nbolger/Desktop/neural-showdown');s=Path('/private/tmp/neural-prompt29-20261012');d=r/'docs/planning';rows=json.loads((d/'perspective-fidelity-prompt29-source-evidence.json').read_text())['selected'];checked={}
for row in rows:
 if row['file'] not in ['data/abilities.ts','data/moves.ts','sim/battle.ts','sim/pokemon.ts','sim/battle-actions.ts','sim/battle-stream.ts']:continue
 for version,key in [('0.11.10','old_sha256'),('0.11.11','new_sha256')]:
  p=s/version/'package'/row['file'];h=hashlib.sha256(p.read_bytes()).hexdigest();assert h==row[key];checked[version+'/'+row['file']]=h
fixture=json.loads((d/'perspective-fidelity-prompt36-saved-prefix.json').read_text());actual=Path(fixture['source_file']).read_bytes();assert hashlib.sha256(actual).hexdigest()==fixture['source_sha256'];assert len(actual)==fixture['source_bytes']
(d/'perspective-fidelity-prompt36-source-integrity.json').write_text(json.dumps({'reused_Prompt29_source_checks':checked,'saved_HTML_hash':fixture['source_sha256'],'saved_HTML_bytes':len(actual),'target_runtime_loaded':False},indent=2)+'\n');print('P36_SOURCE_INTEGRITY',len(checked),'accepted source hashes and one saved HTML match; no target runtime loaded')
