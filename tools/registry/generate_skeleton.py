"""Print a missing-only coverage skeleton from the normative property applications.

Usage: python tools/registry/generate_skeleton.py [--output PATH]
Existing curated statuses are never read or overwritten unless --output names them.
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / 'docs/contracts/fixtures/perspective-knowledge-v1'


def skeleton():
    applications = json.loads((FIXTURES / 'property-contexts.json').read_text(encoding='utf-8'))
    profiles = json.loads((FIXTURES / 'profiles.json').read_text(encoding='utf-8'))
    families = {}
    for profile in profiles:
        for obligation in profile['obligations']:
            for prop in obligation['properties']:
                if prop in families and families[prop] != obligation['family']:
                    raise ValueError(f'Conflicting family for {prop}')
                families[prop] = obligation['family']
    rows = []
    for prop, entries in applications.items():
        for entry in entries:
            if entry['scope'] not in ('owner', 'both'):
                raise ValueError(f'Unsupported scope: {entry["scope"]}')
            for perspective in (('own', 'opponent') if entry['scope'] == 'both' else ('own',)):
                rows.append(dict(property=prop, family=families[prop], context=entry['context'],
                                 perspective=perspective, status='missing', provider=None,
                                 tests=[], limits='No adopted provider recorded.', blocked_by=None,
                                 impact='medium'))
    keys = [(row['property'], row['context'], row['perspective']) for row in rows]
    if len(set(keys)) != len(keys):
        raise ValueError('Duplicate property application')
    return dict(schema='knowledge-coverage/v1', rows=rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    payload = json.dumps(skeleton(), indent=2, ensure_ascii=False) + '\n'
    if args.output:
        args.output.write_text(payload, encoding='utf-8')
    else:
        print(payload, end='')
