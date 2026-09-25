"""Review reproduction: Python publishes unsupported copyboost aliases; TS rejects."""
import json,subprocess,sys
from pathlib import Path
from neural.ts_identity import digest,observation_digest,belief_digest,verify_bundle_identities
HERE=Path(__file__).resolve().parent
for version,line in [('v1','|copyboost||p2a: Donor|[from] move: Psych Up'),('v2','|copyboost|p2a: Gengar|p1a: Mew|[from] move: Psych Up')]:
 b=json.loads((HERE/f'valid-{version}.json').read_text())
 good=subprocess.run([sys.executable,'-m','neural.pipeline_record'],input=json.dumps(b),text=True,capture_output=True)
 assert good.returncode==0,good.stderr
 o=b['successor_observation'];o['protocol_prefix'].append(line);o['event_cursor']=len(o['protocol_prefix']);o['protocol_prefix_hash']=digest(o['protocol_prefix']);o['observation_id']=observation_digest(o)
 bel=b['successor_belief'];ref={k:o[k] for k in bel['observation']};bel['observation']=ref;bel['observation_history'][-1]=dict(ref);bel['source_protocol_prefix']=list(o['protocol_prefix']);bel['transition_lineage']['output_observation_id']=o['observation_id'];bel['transition_history'][-1]['output_observation_id']=o['observation_id'];bel['belief_id']=belief_digest(bel)
 verify_bundle_identities(b)
 result=subprocess.run([sys.executable,'-m','neural.pipeline_record'],input=json.dumps(b),text=True,capture_output=True)
 assert result.returncode==0 and result.stdout,result.stderr
 file=HERE/f'alias-{version}.json';file.write_text(json.dumps(b))
 print(version,'identities verified; Python accepted and published',line)
 code="const b=require(process.argv[1]);const {projectBeliefState}=require('./sim-core/dist/src/belief_state');try{projectBeliefState({observation:b.successor_observation,parent:b.input_belief});process.exit(1)}catch(e){console.log('TS rejects:',e.message)}"
 ts=subprocess.run(['node','-e',code,str(file)],cwd=HERE.parents[2],text=True,capture_output=True)
 assert ts.returncode==0,ts.stderr
 print(ts.stdout.strip())
