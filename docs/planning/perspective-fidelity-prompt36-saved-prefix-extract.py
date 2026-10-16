from pathlib import Path
import json,hashlib,re,html
r=Path('/Users/nbolger/Desktop/neural-showdown');d=r/'docs/planning';pref='perspective-fidelity-prompt36-'
meta=json.loads((d/'perspective-fidelity-five-replay-inputs.json').read_text());item=meta['files'][0];p=Path(meta['local_root'])/item['file'];b=p.read_bytes();assert hashlib.sha256(b).hexdigest()==item['sha256'];assert len(b)==item['bytes']
text=re.search(r'<script type="text/plain" class="battle-log-data">\s*\n(.*?)</script>',b.decode(),re.S).group(1)
# Same bounded saved HTML transport unescape used by the old importer input loader; no event repair.
records=html.unescape(text).replace('\\/','/').splitlines();idx=next(i for i,v in enumerate(records) if 'Natural Cure' in v);assert idx==44
fixture={'source_file':str(p),'source_sha256':item['sha256'],'source_bytes':len(b),'selected_cursor':idx+1,'natural_cure_source_index':idx,'transport_decode':'HTML text unescape and escaped slash decoding; protocol tags retained','records':records[:idx+1]}
(d/(pref+'saved-prefix.json')).write_text(json.dumps(fixture,indent=2,ensure_ascii=False)+'\n');print('saved-prefix hash verified, cursor',idx+1)
