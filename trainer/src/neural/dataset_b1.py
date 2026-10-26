"""Transactional per-battle compact storage and streaming JSONL feature worker."""
import argparse
import json
import os
from pathlib import Path
import sys
import numpy as np
from .feature_v1 import featurize, FEATURE_VERSION, VOCAB_SHA256


def atomic_npz(path, arrays):
    temporary = path.with_suffix('.tmp')
    with temporary.open('wb') as stream:
        np.savez_compressed(stream, **arrays)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def padded(features):
    result = {}
    for name, array in features.items():
        if name.startswith('action_'):
            shape = (13, *array.shape[1:])
            value = np.full(shape, -1 if name in ('action_indices', 'action_target') else 0, array.dtype)
            value[:len(array)] = array
            result[name] = value
        else:
            result[name] = array
    return result


class Builder:
    def __init__(self, output):
        self.output = Path(output)
        self.battles = self.output / 'battles'
        self.battles.mkdir(parents=True, exist_ok=True)
        self.pending = {}

    def call(self, message):
        kind = message['type']
        if kind == 'begin':
            self.pending[message['id']] = {'metadata': message, 'examples': []}
        elif kind == 'frame':
            frame = message['frame']
            if 'action' not in frame:
                return {}
            examples = self.pending[frame['battle_id']]['examples']
            features = padded(featurize(frame['observation'], frame['observation']['request']))
            legal = frame['legal_actions']
            index = next((i for i, a in enumerate(legal) if a == frame['action']), None)
            if index is None:
                raise ValueError('dataset/noncanonical-human-action')
            meta = self.pending[frame['battle_id']]['metadata']
            features.update(human_action=np.array(index, np.int32),
                            outcome=np.array(meta['outcomes'][frame['owner']], np.float32),
                            ending=np.array(meta['ending']), rating=np.array(meta['rating'] if meta['rating'] is not None else 0, np.float32),
                            rating_known=np.array(meta['rating'] is not None, np.bool_),
                            battle_id=np.array(frame['battle_id']), step=np.array(frame['step_index'], np.int32),
                            owner=np.array(frame['owner']))
            examples.append(features)
        elif kind == 'abort':
            self.pending.pop(message['id'], None)
        elif kind == 'end':
            entry = self.pending.pop(message['id'])
            examples = entry['examples']
            if examples:
                arrays = {key: np.stack([row[key] for row in examples]) for key in examples[0]}
                atomic_npz(self.battles / (message['id'] + '.npz'), arrays)
            return {'examples': len(examples)}
        elif kind == 'finalize':
            shards, counts = [], {}
            for split in ('train', 'validation', 'test'):
                buffer, count, part = [], 0, 0
                def flush():
                    nonlocal buffer, part
                    if not buffer:
                        return
                    name = f'{split}-{part:05d}.npz'
                    atomic_npz(self.output / name, {k: np.stack([r[k] for r in buffer]) for k in buffer[0]})
                    shards.append({'file': name, 'split': split, 'examples': len(buffer)})
                    part += 1
                    buffer = []
                for row in sorted(message['rows'], key=lambda r: r['id']):
                    if row['split'] != split or not row['ok'] or not row['examples']:
                        continue
                    with np.load(self.battles / (row['id'] + '.npz'), allow_pickle=False) as archive:
                        arrays = {k: archive[k] for k in archive.files}
                    for i in range(row['examples']):
                        buffer.append({k: v[i] for k, v in arrays.items()})
                        count += 1
                        if len(buffer) == message['shard_size']:
                            flush()
                flush()
                counts[split] = count
            return {'counts': counts, 'shards': shards, 'feature_version': FEATURE_VERSION, 'vocabulary_sha256': VOCAB_SHA256}
        else:
            raise ValueError('dataset/unknown-message')
        return {}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    builder = Builder(parser.parse_args().output)
    for raw in sys.stdin.buffer:
        request = json.loads(raw)
        try:
            response = {'rpc': request['rpc'], 'result': builder.call(request)}
        except Exception as error:
            response = {'rpc': request['rpc'], 'error': str(error)}
        sys.stdout.buffer.write((json.dumps(response, ensure_ascii=True) + '\n').encode('utf-8'))
        sys.stdout.buffer.flush()


if __name__ == '__main__':
    main()
