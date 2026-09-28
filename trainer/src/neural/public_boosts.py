"""Version-two stage evidence reconstructed only from the supplied public prefix."""
import re
from neural.protocol_contract import _is_player_ident

KEYS = ('atk', 'def', 'spa', 'spd', 'spe', 'accuracy', 'evasion')

def validate_copy_boost_record(parts):
    if len(parts) != 5 or parts[4] != '[from] move: Psych Up' or any(
            not _is_player_ident(ident, active_required=True) for ident in parts[2:4]):
        raise ValueError('Unsupported or malformed public boost copy evidence')

def validate_invert_boost_record(parts):
    if len(parts) != 4 or parts[3] != '[from] move: Topsy-Turvy' or not _is_player_ident(parts[2], active_required=True):
        raise ValueError('Unsupported or malformed public stage inversion evidence')

def public_boost_evidence(prefix):
    roster, active = {}, {}
    def filled(value): return dict.fromkeys(KEYS, value)
    def key(ident): return re.sub(r'^(p[12])[a-f]:', r'\1:', ident)
    def side(ident):
        match = re.match(r'^(p[12])[a-f]:', ident)
        return match[1] if match else None
    actor_commands = {
        'switch', 'drag', 'replace', 'faint', '-boost', '-unboost', '-setboost',
        '-clearboost', '-clearnegativeboost', '-clearpositiveboost', '-copyboost',
        '-invertboost', '-transform',
    }
    for line in prefix:
        p = line.split('|')
        cmd = p[1] if len(p) > 1 else ''
        if cmd in ('boost', 'unboost', 'setboost', 'clearboost', 'clearallboost', 'clearnegativeboost', 'clearpositiveboost', 'copyboost', 'swapboost', 'invertboost', 'transform'): cmd = '-' + cmd
        if cmd == 'gametype' and p[2] != 'singles': raise ValueError('Unsupported public boost evidence: non-singles')
        # Grammar precedes side routing: unresolved roster identity is not a
        # malformed identifier and must retain the existing unknown semantics.
        if cmd == '-copyboost': validate_copy_boost_record(p)
        if cmd == '-invertboost': validate_invert_boost_record(p)
        ident = p[2] if len(p) > 2 else ''
        if cmd in actor_commands and not _is_player_ident(ident, active_required=True):
            raise ValueError('Malformed public boost player identifier')
        if cmd == '-transform' and (len(p) < 4 or not _is_player_ident(p[3], active_required=True)):
            raise ValueError('Malformed public boost transform target identifier')
        if cmd == '-clearpositiveboost' and (len(p) < 4 or not _is_player_ident(p[3], active_required=True)):
            raise ValueError('Malformed public boost source identifier')
        player = side(ident)
        if cmd == '-swapboost' or (cmd == 'move' and len(p) > 3 and p[3] == 'Baton Pass'):
            raise ValueError('Unsupported public boost evidence: ' + cmd)
        if cmd == '-clearallboost':
            for entry in active.values():
                entry['stages'] = filled(0)
                roster[entry['key']] = dict(entry['stages'])
        if not player: continue
        entry = active.get(player)
        if cmd in ('switch', 'drag'):
            if entry: roster[entry['key']] = filled(0)
            prior = roster.get(key(ident))
            entry = {'key': key(ident), 'stages': filled(0)}
            if prior is not None: entry['prior'] = dict(prior)
            active[player] = entry
        elif cmd == 'replace' and entry:
            if entry['key'] != key(ident):
                if 'prior' in entry: roster[entry['key']] = entry['prior']
                else: roster.pop(entry['key'], None)
                entry['key'] = key(ident)
                entry.pop('prior', None)
        elif cmd in ('faint', '-clearboost'):
            if not entry:
                entry = {'key': key(ident), 'stages': filled(None)}
                active[player] = entry
            entry['stages'] = filled(0)
        elif cmd in ('-clearnegativeboost', '-clearpositiveboost'):
            if not entry:
                entry = {'key': key(ident), 'stages': filled(None)}
                active[player] = entry
            for stat, stage in entry['stages'].items():
                if stage is not None and (stage > 0 if cmd == '-clearpositiveboost' else stage < 0):
                    entry['stages'][stat] = 0
        elif cmd == '-invertboost':
            if not entry:
                entry = {'key': key(ident), 'stages': filled(None)}
                active[player] = entry
            entry['stages'] = {stat: value if value is None or value == 0 else -value
                               for stat, value in entry['stages'].items()}
        elif cmd == '-copyboost':
            if not entry:
                entry = {'key': key(ident), 'stages': filled(None)}
                active[player] = entry
            entry['stages'] = dict(active.get(side(p[3]), {}).get('stages', filled(None)))
        elif entry and cmd == '-transform': entry['stages'] = dict(active.get(side(p[3]), {}).get('stages', filled(None)))
        elif cmd in ('-boost', '-unboost', '-setboost'):
            if not entry:
                entry = {'key': key(ident), 'stages': filled(None)}
                active[player] = entry
            stat, amount = p[3], float(p[4])
            if not re.fullmatch(r'-?\d+', p[4]) or (cmd != '-setboost' and amount < 0) or stat not in KEYS or not amount.is_integer() or abs(amount) > (6 if cmd == '-setboost' else 12): raise ValueError('Malformed public boost evidence')
            amount = int(amount)
            if cmd == '-setboost': entry['stages'][stat] = amount
            elif entry['stages'][stat] is not None:
                entry['stages'][stat] = max(-6, min(6, entry['stages'][stat] + (-amount if cmd == '-unboost' else amount)))
        for current in active.values(): roster[current['key']] = dict(current['stages'])
    return roster


def validate_public_boosts(observation):
    if any('public_boosts' in pokemon for pokemon in observation['view']['self_team']):
        raise ValueError('public_boosts is opponent-only')
    roster = public_boost_evidence(observation['protocol_prefix'])
    allowed = set('slot ident name species base_species current_species displayed_species species_source transformed displayed_species_uncertain illusion_revealed details active fainted hp_text hp_ratio status status_source status_started_turn status_turns_public gender level types terastallized volatiles public_boosts item'.split())
    for pokemon in observation['view']['opponent_team']:
        if set(pokemon) - allowed or (pokemon.get('item') is not None and pokemon['item'] != 'has-item'):
            raise ValueError('Opponent contains fields outside public schema')
        actual = pokemon.get('public_boosts')
        if not isinstance(actual, dict) or set(actual) != set(KEYS) or any(v is not None and (type(v) is not int or not -6 <= v <= 6) for v in actual.values()):
            raise ValueError('Malformed public opponent stages')
        expected = roster.get(re.sub(r'^(p[12])[a-f]:', r'\1:', pokemon['ident']), dict.fromkeys(KEYS, None))
        if actual != expected: raise ValueError('Public opponent stages disagree with exact prefix')


# Kept as an import for existing consumers; one canonical identity implementation.
from neural.ts_identity import observation_digest
