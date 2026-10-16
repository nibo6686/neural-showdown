from pathlib import Path
import hashlib,json,tarfile,io,stat
pending=Path('/Users/nbolger/Desktop/neural-showdown/docs/planning/perspective-fidelity-prompt59-pending-retention.json')
p=json.loads(pending.read_text());r=Path(p['candidate']); archive=Path(p['proposed_archive']);manifest=Path(p['proposed_manifest']);h=lambda b:hashlib.sha256(b).hexdigest()
assert len(p['files'])==7 and len(p['expected_members'])==7
assert archive.name=='unreviewed-prompt59-source-overlay.tar.gz' and manifest.name=='unreviewed-prompt59-overlay-manifest.json' and archive.parent==r.parent==manifest.parent
assert not archive.exists() and not manifest.exists(), 'Do not overwrite retention destinations'
protected=[r.parent/n for n in ['native11-source-prompt54.tar.gz','retention-manifest.json','unreviewed-prompt57-source-overlay.tar.gz','unreviewed-prompt57-overlay-manifest.json']]+[pending,Path('/Users/nbolger/Desktop/neural-showdown/docs/planning/perspective-fidelity-prompt59-lead-review.md')]
preserve={str(x):h(x.read_bytes()) for x in protected};assert preserve[str(r.parent/'native11-source-prompt54.tar.gz')]==p['accepted_base_sha256']
contents={}
for name,expected in p['files'].items():
 assert not Path(name).is_absolute() and '..' not in Path(name).parts
 source=r/name;assert not source.is_symlink() and stat.S_ISREG(source.stat().st_mode)
 data=source.read_bytes();assert h(data)==expected,name
 contents['candidate/'+name]=data
assert set(contents)==set(p['expected_members'])
with archive.open('xb') as output:
 with tarfile.open(fileobj=output,mode='w:gz') as tar:
  for name,data in contents.items():
   info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o644;info.mtime=0;tar.addfile(info,io.BytesIO(data))
readback={}
with tarfile.open(archive,'r:gz') as tar:
 members=tar.getmembers();assert len(members)==7 and all(m.isfile() for m in members)
 for m in members:readback[m.name]=h(tar.extractfile(m).read())
assert readback=={'candidate/'+n:v for n,v in p['files'].items()}
assert preserve=={str(x):h(x.read_bytes()) for x in protected}
record={'status':'RETAINED AND READ-BACK VERIFIED','authorization':str(pending),'candidate':str(r),'archive':str(archive),'archive_sha256':h(archive.read_bytes()),'archive_bytes':archive.stat().st_size,'members':readback,'preserved':preserve,'scope':'exact seven-file local overlay only; no authority capabilities or dependencies; no source implementation acceptance'}
with manifest.open('x') as f:f.write(json.dumps(record,indent=2)+'\n')
receipt={**record,'manifest':str(manifest),'manifest_sha256':h(manifest.read_bytes())}
Path('/Users/nbolger/Desktop/neural-showdown/docs/planning/perspective-fidelity-prompt60-retention-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:receipt[k] for k in ['status','archive','archive_sha256','archive_bytes','manifest','manifest_sha256']},indent=2));print('Verified seven source hashes and seven read-back member hashes; six protected records unchanged')
