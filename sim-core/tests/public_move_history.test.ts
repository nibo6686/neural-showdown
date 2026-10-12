import assert from 'node:assert/strict';
import test from 'node:test';
import { importReplayPrefix, importReplayPrefixWithMoveHistory } from '../src/replay_import';
import { reconstructPublicMoveHistory, PublicMoveHistoryError } from '../src/public_move_history';

const ctx = { env_id: 'prompt21', format: 'gen9randombattle', perspective: 'p1' as const };
const history = (records: string[], cursor = records.length) => importReplayPrefixWithMoveHistory(records,cursor,ctx).public_move_history;
function reject(records: string[], index: number) {
  assert.throws(() => importReplayPrefixWithMoveHistory(records,records.length,ctx), (error: unknown) => {
    assert.ok(error instanceof PublicMoveHistoryError);
    assert.equal(error.stage,'history'); assert.equal(error.source_index,index);
    assert.equal(error.code,'unresolved_appearance');
    for (const key of ['replay','public_move_history','appearances','executions']) assert.ok(!(key in error));
    return true;
  });
}

test('literal closure/context oracle: replace preserves stint; drag, faint and winner close exact source indices', () => {
  const records = ['|switch|p1a: Ditto|Ditto, L80|100/100','|switch|p2a: Target|Garchomp, L80|100/100',
    '|-transform|p1a: Ditto|p2a: Target','|move|p1a: Ditto|Earthquake|p2a: Target|[from] move: Sleep Talk',
    '|replace|p1a: Fox|Zoroark, L80|100/100','|drag|p1a: Bench|Pikachu, L80|100/100',
    '|move|p1a: Bench|Tackle|p2a: Target','|faint|p1a: Bench','|win|Alice'];
  const at4 = history(records,4), at5 = history(records,5), at6 = history(records,6), result = history(records);
  assert.equal(at4.appearances[0].end_source_index,null);
  assert.deepEqual(at4.appearances[0].disclosure_source_indices,[]);
  assert.equal(at5.appearances[0].end_source_index,null);
  assert.deepEqual(at5.appearances[0].disclosure_source_indices,[4]);
  assert.equal(at6.appearances[0].end_source_index,5);
  assert.deepEqual(result.appearances,[
    {subject:'p1:appearance:1',side:'p1',start_source_index:0,end_source_index:5,disclosure_source_indices:[4],carrier:null},
    {subject:'p2:appearance:1',side:'p2',start_source_index:1,end_source_index:8,disclosure_source_indices:[],carrier:null},
    {subject:'p1:appearance:2',side:'p1',start_source_index:5,end_source_index:7,disclosure_source_indices:[],carrier:null},
  ]);
  assert.deepEqual(result.executions,[
    {appearance:'p1:appearance:1',source_index:3,observed_at:4,record:records[3],move:'Earthquake',
      origin_tags:['[from] move: Sleep Talk'],context_witnesses:[
        {source_index:2,record:records[2],kind:'transform'},{source_index:3,record:records[3],kind:'called_move'}],origin_status:'classified'},
    {appearance:'p1:appearance:2',source_index:6,observed_at:7,record:records[6],move:'Tackle',
      origin_tags:[],context_witnesses:[],origin_status:'unannotated'},
  ]);
  assert.deepEqual(result.executions[0],at4.executions[0]);
  assert.deepEqual(result.issues,[{source_index:0,code:'missing_carrier_provider'},
    {source_index:1,code:'missing_carrier_provider'},{source_index:5,code:'missing_carrier_provider'}]);
});

test('duplicate and Illusion/restoration oracle keeps indexed receipts and chronological appearance subjects', () => {
  const move = '|move|p1a: Mask|Thunderbolt|p2a: Target';
  const records = ['|switch|p1a: Mask|Pikachu, L80|100/100',move,
    '|switch|p1a: Other|Eevee, L80|100/100','|switch|p1a: Mask|Pikachu, L80|100/100',
    '|move|p1a: Mask|Night Daze|p2a: Target','|replace|p1a: Fox|Zoroark, L80|100/100',
    '|switch|p1a: Mask|Pikachu, L80|100/100',move,'|tie'];
  const result = history(records);
  assert.deepEqual(result.appearances.map(a => [a.start_source_index,a.end_source_index,a.disclosure_source_indices]),
    [[0,2,[]],[2,3,[]],[3,6,[5]],[6,8,[]]]);
  assert.deepEqual(result.executions.map(e => [e.source_index,e.observed_at,e.appearance]),
    [[1,2,'p1:appearance:1'],[4,5,'p1:appearance:3'],[7,8,'p1:appearance:4']]);
  assert.equal(result.executions[0].record,result.executions[2].record);
  assert.notEqual(result.executions[0],result.executions[2]);
  assert.ok(result.appearances.every(a => a.carrier === null));
  assert.deepEqual(history(records),result);
});

test('supported call/Transform evidence coexists; unknown tags and Sketch retain receipts with blocking issues', () => {
  const records = ['|switch|p1a: Artist|Smeargle, L80|100/100','|switch|p2a: Target|Pikachu, L80|100/100',
    '|-transform|p1a: Artist|p2a: Target|[from] ability: Imposter',
    '|move|p1a: Artist|Thunderbolt|p2a: Target|[from] move: Metronome',
    '|-activate|p1a: Artist|move: Sketch|Ice Beam',
    '|move|p1a: Artist|Ice Beam|p2a: Target|[from] ability: Dancer'];
  const result = history(records);
  assert.equal(result.executions[0].origin_status,'classified');
  assert.deepEqual(result.executions[0].context_witnesses.map(w => [w.source_index,w.kind]),[[2,'transform'],[3,'called_move']]);
  assert.deepEqual(result.executions[1].origin_tags,['[from] ability: Dancer']);
  assert.equal(result.executions[1].origin_status,'unsupported');
  assert.deepEqual(result.executions[1].context_witnesses.map(w => [w.source_index,w.kind]),[[2,'transform'],[4,'unsupported_writer']]);
  assert.ok(result.issues.some(i => i.source_index === 4 && i.code === 'unsupported_writer'));
  assert.ok(result.issues.some(i => i.source_index === 5 && i.code === 'unsupported_execution_origin'));
  assert.deepEqual(history(records,4).executions[0],result.executions[0]);
  const unknownTransform = [...records.slice(0,2),'|-transform|p1a: Artist|p2a: Target|[from] ability: Unknown',
    '|move|p1a: Artist|Ice Beam|p2a: Target'];
  assert.equal(history(unknownTransform).executions[0].origin_status,'unsupported');
  assert.equal(history(unknownTransform).executions[0].context_witnesses[0].kind,'unsupported_writer');
  const legacyTransform = [...records.slice(0,2),'|transform|p1a: Artist|p2a: Target',
    '|move|p1a: Artist|Ice Beam|p2a: Target'];
  assert.equal(history(legacyTransform).executions[0].origin_status,'unsupported');
  assert.deepEqual(history(legacyTransform).executions[0].context_witnesses,
    [{source_index:2,record:legacyTransform[2],kind:'unsupported_writer'}]);
  const unknownOrigin = [...records.slice(0,2),'|move|p1a: Artist|Ice Beam|p2a: Target|[from] ability: Dancer'];
  assert.deepEqual(history(unknownOrigin).executions[0].context_witnesses,[]);
  assert.equal(history(unknownOrigin).executions[0].origin_status,'unsupported');
  assert.ok(history(unknownOrigin).issues.some(i => i.source_index === 2 && i.code === 'unsupported_execution_origin'));
  const legacySketch = [...records.slice(0,2),'|activate|p1a: Artist|move: Sketch|Ice Beam',
    '|move|p1a: Artist|Ice Beam|p2a: Target'];
  assert.deepEqual(history(legacySketch).executions[0].context_witnesses,
    [{source_index:2,record:legacySketch[2],kind:'unsupported_writer'}]);
  assert.equal(history(legacySketch).executions[0].origin_status,'unsupported');
});

test('orphan, closed and unsupported-slot lifecycle errors are atomic and identify original source positions', () => {
  reject(['|rated|','|move|p1a: Missing|Tackle|p2a: Target'],1);
  reject(['|rated|','|replace|p1a: Missing|Pikachu, L80|100/100'],1);
  reject(['|switch|p1a: A|Pikachu, L80|100/100','|faint|p1a: A','|move|p1a: A|Tackle|p2a: B'],2);
  reject(['|switch|p1a: A|Pikachu, L80|100/100','|tie','|replace|p1a: A|Pikachu, L80|100/100'],2);
  reject(['|tie','|switch|p1a: A|Pikachu, L80|100/100'],1);
  reject(['|switch|p1a: A|Pikachu, L80|100/100','|-transform|p1a: A|p2a: Missing'],1);
  reject(['|switch|p1b: A|Pikachu, L80|100/100'],0);
});

test('malformed selected history input rejects, while empty/metadata-only history has no invented appearances', () => {
  const replay = importReplayPrefix(['|rated|','|'],2,ctx);
  assert.deepEqual(reconstructPublicMoveHistory(replay),{source_cursor:2,appearances:[],executions:[],issues:[]});
  assert.deepEqual(history([],0),{source_cursor:0,appearances:[],executions:[],issues:[]});
  for (const malformed of [null,{...replay,source_cursor:.5},{...replay,source_to_routed:[]},
    {...replay,source_rows:[{...replay.source_rows[0],record:'|move|p1a: A|Tackle|p2a: B'},replay.source_rows[1]]}]) {
    assert.throws(() => reconstructPublicMoveHistory(malformed as any),PublicMoveHistoryError);
  }
  const routed = importReplayPrefix(['|switch|p1a: A|Pikachu, L80|100/100'],1,ctx);
  assert.throws(() => reconstructPublicMoveHistory({...routed,routed_to_source:[1]}), (e: unknown) => {
    assert.ok(e instanceof PublicMoveHistoryError); assert.equal(e.source_index,0); return true;
  });
});

test('frozen companion ignores suffix reads and identical public prefixes yield both-owner identical histories', () => {
  const records = ['|switch|p1a: A|Pikachu, L80|100/100','|move|p1a: A|Tackle|p2a: B','|unknown|future'];
  const guarded = new Proxy(records,{get(target,key,receiver) {
    if (typeof key === 'string' && /^\d+$/.test(key) && Number(key) >= 2) throw new Error('Suffix read');
    return Reflect.get(target,key,receiver);
  }});
  const companion = importReplayPrefixWithMoveHistory(guarded,2,ctx);
  assert.deepEqual(companion.replay,importReplayPrefix(records,2,ctx));
  assert.deepEqual(companion.public_move_history,importReplayPrefixWithMoveHistory(guarded,2,{...ctx,perspective:'p2'}).public_move_history);
  assert.throws(() => (companion as any).replay = null,TypeError);
  assert.throws(() => (companion.public_move_history.appearances[0] as any).carrier = 'p1:roster:1',TypeError);
  assert.throws(() => (companion.public_move_history.executions[0].origin_tags as string[]).push('fake'),TypeError);
  records[0] = '|unknown|mutated';
  assert.equal(companion.public_move_history.appearances[0].start_source_index,0);
  assert.equal(companion.public_move_history.executions[0].record,'|move|p1a: A|Tackle|p2a: B');
});
