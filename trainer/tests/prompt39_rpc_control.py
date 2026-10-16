from pathlib import Path
import json,time
from neural.env_client import SimCoreClient,SimCoreError
ROOT=Path('/private/tmp/neural-showdown-native11-prompt38')
node='/Users/nbolger/.nvm/versions/node/v24.21.0/bin/node'
client=SimCoreClient([node,'--require',str(ROOT/'sim-core/tests/native11_rpc_counters.cjs'),'dist/src/server.js'],cwd=str(ROOT/'sim-core'))
try:
    client.ping(timeout_sec=10)
    env_id=client.create_env(seed=[1,2,3,4],timeout_sec=10)
    try:client.fork_belief_env(env_id,'p1',[5,6,7,8],timeout_sec=10)
    except SimCoreError as error:assert 'snapshot-admission/v1/belief-fork-unsupported' in str(error)
    else:raise AssertionError('target RPC must reject belief fork')
    rows=[line for line in client._stderr_lines if line.startswith('P39_RPC_COUNTERS ')]
    assert len(rows)==1,client._stderr_lines
    payload=json.loads(rows[0].split(' ',1)[1]);assert payload['before']==payload['after']==dict(reconstruct=0,sample=0,dispose=0)
    assert payload['map_unchanged'] and payload['open_envs']==1
    client.close_env(env_id,timeout_sec=10)
    print('P39_WITNESS '+json.dumps(dict(name='actual-stdio-RPC',belief_guard=payload,raw_restore_RPC='NO SUCH ENTRY POINT; direct target guard reused from Prompt38',candidate_client_path=__import__('neural.env_client',fromlist=['x']).__file__)))
finally:client.close()
assert client._process.poll() is not None
