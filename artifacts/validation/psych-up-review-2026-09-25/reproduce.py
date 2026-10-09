import json,copy,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
from neural.ts_identity import digest,observation_digest,belief_digest
base=json.load(open(HERE/'valid-control.json'))
control=subprocess.run([sys.executable,'-m','neural.pipeline_record'],input=json.dumps(base),text=True,capture_output=True)
assert control.returncode==0,control.stderr
print('valid control passes')
for line in ['|-copyboost||p1a: Mew|[from] move: Psych Up','|-copyboost|garbage|p1a: Mew|[from] move: Psych Up','|-copyboost|p2a: |p1a: Mew|[from] move: Psych Up']:
 b=copy.deepcopy(base);o=b['successor_observation'];o['protocol_prefix'].append(line);o['event_cursor']=len(o['protocol_prefix']);o['protocol_prefix_hash']=digest(o['protocol_prefix']);o['observation_id']=observation_digest(o)
 belief=b['successor_belief'];ref={k:o[k] for k in belief['observation']};belief['observation']=ref;belief['observation_history'][-1]=dict(ref);belief['source_protocol_prefix']=list(o['protocol_prefix']);belief['transition_lineage']['output_observation_id']=o['observation_id'];belief['transition_history'][-1]['output_observation_id']=o['observation_id'];belief['belief_id']=belief_digest(belief)
 p=subprocess.run([sys.executable,'-m','neural.pipeline_record'],input=json.dumps(b),text=True,capture_output=True)
 assert p.returncode==0 and p.stdout, (p.returncode,p.stderr)
 print(line,'exit',p.returncode,'published',bool(p.stdout),p.stderr.strip())
 json.dump(b,open(HERE/('malformed-'+str(len(line))+'.json'),'w'))

# TS must reject the same fully rehashed observation content.
root=HERE.parents[2]
for path in sorted(HERE.glob('malformed-*.json')):
 code="const fs=require('fs');const {projectBeliefState}=require(process.cwd()+'/sim-core/dist/src/belief_state');const b=JSON.parse(fs.readFileSync(process.argv[1]));try{projectBeliefState({observation:b.successor_observation,parent:b.input_belief});process.exit(1)}catch(e){console.log('TS rejects',e.message)}"
 result=subprocess.run(['node','-e',code,str(path)],cwd=root,text=True,capture_output=True)
 assert result.returncode==0,result.stderr
 print(result.stdout.strip())
