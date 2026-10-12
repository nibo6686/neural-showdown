import sys,json,subprocess,os
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from trainer.tests.test_perspective_knowledge import fixture,reseal,independent_canonical,independent_id
from neural.perspective_knowledge import check_knowledge_structure,parse_knowledge_json
root=Path.cwd(); cases={}
a=fixture('replay-full.json'); s=next(s for s in a['tables']['starting'] if s['crosswalk']); c=next(c for c in a['tables']['certificate'] if c['id']==s['crosswalk'][0]['certificate']); s['crosswalk'][0]['roster']=c['subject']='p1:roster:1'; cases['opponent-roster']=reseal(a)
a=fixture('sim-full.json'); next(f for f in a['tables']['fact'] if f['freshness']=='immutable' and f['property']=='item')['observed_at']=99; cases['initialization-cursor']=reseal(a)
a=fixture('sim-full.json'); next(s for s in a['tables']['source'] if s['raw_request'] is not None)['raw_request']['json']='['*33+']'*33; cases['raw-request-depth']=reseal(a)
node="const fs=require('fs'), k=require('./sim-core/dist/src/perspective_knowledge.js'); const a=JSON.parse(fs.readFileSync(0,'utf8')); try { console.log(JSON.stringify(k.checkKnowledgeStructure(a))); } catch(e) { console.error(e.message); process.exit(2); }"
results=[]
for name,a in cases.items():
 for rows in a['tables'].values():
  for row in rows: assert row['id']==independent_id(row)
 assert a['id']==independent_id(a)
 wire=independent_canonical(a); before=wire
 try: py={'accepted':True,'diagnostic':check_knowledge_structure(a)}
 except Exception as e: py={'accepted':False,'guard':str(e)}
 ts=subprocess.run(['node','-e',node],input=wire,capture_output=True)
 assert before==independent_canonical(a)
 results.append({'case':name,'python':py,'ts_exit':ts.returncode,'ts_stdout':ts.stdout.decode(),'ts_stderr':ts.stderr.decode()})
for leaf in ('','0'):
 raw='['*33+leaf+']'*33
 try: parse_knowledge_json(raw); accepted=True
 except Exception: accepted=False
 ts=subprocess.run(['node','-e',"const k=require('./sim-core/dist/src/perspective_knowledge.js'); try{k.parseKnowledgeJson(require('fs').readFileSync(0));process.exit(0)}catch(e){process.exit(2)}"],input=raw.encode(),capture_output=True)
 results.append({'case':'33-arrays-'+('empty' if not leaf else 'scalar'),'python_accepted':accepted,'ts_exit':ts.returncode})
stage=sys.argv[1]; (root/f'docs/planning/perspective-fidelity-prompt11r-{stage}.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8'); print(json.dumps(results,indent=2))
