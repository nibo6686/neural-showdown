import json
from pathlib import Path
import subprocess
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / 'sim-core/tests/fixtures/replay-real'
IDS = ['2695493840', '2695512325', '2695618222']
SCRIPT = "require('./tools/dataset/build_b1.cjs').build(process.argv.slice(1)).then(r=>console.log(JSON.stringify(r))).catch(e=>{console.error(e);process.exitCode=1})"


def run(directory, files, output, resume=False):
    result = subprocess.run(['node', '-e', SCRIPT, str(directory), '--files=' + str(files),
                             '--output=' + str(output), '--workers=2', '--shard-size=3',
                             *(['--resume'] if resume else [])], cwd=ROOT, capture_output=True, timeout=45)
    assert result.returncode == 0, result.stderr.decode(errors='replace')
    return json.loads(result.stdout)


def test_fixture_shards_labels_atomic_failure_and_resume(tmp_path):
    directory = tmp_path / 'replays';directory.mkdir()
    names = []
    for name in IDS:
        file = 'gen9randombattle-' + name + '.json'
        (directory / file).write_bytes((FIXTURES / file).read_bytes());names.append(file)
    bad = json.loads((FIXTURES / names[1]).read_text(encoding='utf-8'))
    bad['id'] = 'gen9randombattle-9000000000'
    bad['log'] = bad['log'].replace('Knock Off', 'Tackle')
    file = bad['id'] + '.json';(directory / file).write_text(json.dumps(bad), encoding='utf-8');names.append(file)
    files = tmp_path / 'files.json';files.write_text(json.dumps(names))
    output = tmp_path / 'dataset'
    manifest = run(directory, files, output)
    assert manifest['battles'] == 4 and len(manifest['failures']) == 1
    assert 'public-log-diverged' in manifest['failures'][0]['reason']
    assert not (output / 'battles' / (bad['id'] + '.npz')).exists()
    assert len((output / 'sample.jsonl').read_text(encoding='utf-8').splitlines()) <= 50
    total = 0
    for shard in manifest['shards']:
        with np.load(output / shard['file'], allow_pickle=False) as arrays:
            total += len(arrays['owner'])
            for i, (battle, owner) in enumerate(zip(arrays['battle_id'], arrays['owner'])):
                assert battle in manifest['split_battle_ids'][shard['split']]
                replay = json.loads((directory / (battle + '.json')).read_text(encoding='utf-8'))
                players = {line.split(' ')[1]: json.loads(line.split(' ', 2)[2])['name'] for line in replay['inputlog'].splitlines() if line.startswith('>player ')}
                winner = next(line[5:] for line in replay['log'].splitlines() if line.startswith('|win|'))
                assert arrays['outcome'][i] == (1 if players[str(owner)] == winner else 0)
                target = arrays['human_action'][i]
                assert arrays['action_mask'][i, target]
                assert arrays['action_indices'][i, target] >= 0
                assert arrays['ending'][i] in ('normal', 'forfeit', 'inactivity')
    assert total == sum(manifest['counts'].values()) and total > 0
    journal = (output / 'build.jsonl').read_bytes()
    # Recover an incomplete final append; never duplicate examples after resume.
    with (output / 'build.jsonl').open('ab') as stream:stream.write(b'{"torn":')
    resumed = run(directory, files, output, resume=True)
    assert resumed['counts'] == manifest['counts']
    assert (output / 'build.jsonl').read_bytes() == journal
    assert not set(manifest['split_battle_ids']['train']) & set(manifest['split_battle_ids']['test'])


def test_seeded_split_is_order_independent():
    script = "const {splitIds}=require('./tools/dataset/build_b1.cjs');const ids=Array.from({length:100},(_,i)=>'id'+i);console.log(JSON.stringify([splitIds(ids,'a'),splitIds([...ids].reverse(),'a'),splitIds(ids,'b')]))"
    result = subprocess.run(['node', '-e', script], cwd=ROOT, capture_output=True, check=True, timeout=10)
    a, b, c = json.loads(result.stdout)
    assert a == b and a != c
    assert {s: list(a.values()).count(s) for s in set(a.values())} == {'train': 90, 'validation': 5, 'test': 5}
