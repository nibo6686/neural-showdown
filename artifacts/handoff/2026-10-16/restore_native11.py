"""Restore the retained candidate without depending on old machine paths."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--verify-only', action='store_true')
    parser.add_argument('--verify-runtime', action='store_true',
                        help='Also check pinned Showdown files after npm installation.')
    args = parser.parse_args()
    package = Path(__file__).resolve().parent
    manifest = json.loads((package / 'native11-source-manifest.json').read_text(encoding='utf-8'))
    archive = package / manifest['archive']['name']
    if digest(archive) != manifest['archive']['sha256'] or archive.stat().st_size != manifest['archive']['bytes']:
        raise ValueError('Archive size/hash mismatch; do not restore.')
    destination = args.destination.expanduser().absolute()
    if destination.is_symlink():
        raise ValueError('Use a real destination directory, not a symlink.')
    files = manifest['files']
    support = manifest.get('support_files', {})
    repository = package.parents[2]
    for name, expected in support.items():
        origin = repository / name
        if not origin.is_file() or digest(origin) != expected['sha256']:
            raise ValueError('Supplemental repository input mismatch: ' + name)
    with tarfile.open(archive, 'r:gz') as source:
        entries = source.getmembers()
        if len(entries) != len(files) or {entry.name for entry in entries} != set(files):
            raise ValueError('Archive member set differs from the manifest.')
        for entry in entries:
            name = PurePosixPath(entry.name)
            if (not entry.isfile() or name.is_absolute() or '..' in name.parts
                    or '\\' in entry.name or ':' in entry.name):
                raise ValueError('Unsafe archive member: ' + entry.name)
            data = source.extractfile(entry).read()
            expected = files[entry.name]
            if len(data) != expected['bytes'] or hashlib.sha256(data).hexdigest() != expected['sha256']:
                raise ValueError('Archive member hash mismatch: ' + entry.name)
        if not args.verify_only:
            if destination.exists() and any(destination.iterdir()):
                raise ValueError('Destination must be absent or empty; existing work is never overwritten.')
            destination.mkdir(parents=True, exist_ok=True)
            for entry in entries:
                target = destination.joinpath(*PurePosixPath(entry.name).parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('xb') as output:
                    output.write(source.extractfile(entry).read())
                target.chmod(files[entry.name]['mode'])
            for name in support:
                target = destination / name
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('xb') as output:
                    output.write((repository / name).read_bytes())
    for name, expected in {**files, **support}.items():
        path = destination.joinpath(*PurePosixPath(name).parts)
        if not path.is_file() or path.is_symlink() or digest(path) != expected['sha256']:
            raise ValueError('Restored source mismatch: ' + name)
    if args.verify_runtime:
        runtime = destination / 'sim-core' / 'node_modules' / 'pokemon-showdown'
        for name, expected in manifest['installed_showdown_files'].items():
            path = runtime / name
            if not path.is_file() or digest(path) != expected:
                raise ValueError('Installed Showdown input mismatch: ' + name)
        print('Pinned installed Showdown inputs verified.')
    print('Verified {} accepted source files and {} supplemental fixture/lock files at {}'.format(
        len(files), len(support), destination))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, tarfile.TarError) as error:
        raise SystemExit('Handoff restore failed: ' + str(error))
