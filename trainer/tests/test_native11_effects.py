"""Native source review is a per-ID gate, independent of historical decoding."""
import pytest
from neural.protocol_contract import validate_protocol_record
from neural.version_profile import NATIVE11_CONTEXT, HISTORICAL10_CONTEXT


def test_native_effect_shapes_and_source_delta_rejections():
    for record in ('|cant|p1a: Pikachu|par', '|heal|p1a: Pikachu|100/100',
                   '|-weather|none', '|-fieldstart|move: Gravity', '|-fieldend|move: Gravity'):
        validate_protocol_record(record, reader_rules=NATIVE11_CONTEXT)
    for row in NATIVE11_CONTEXT.inventory['effect_source_comparison']['entries']:
        if not row.get('blocked_reason') or row['category'] == 'major_status':
            continue
        category = row['category']
        command = '-weather' if category == 'weather' else '-fieldstart' if category in ('terrain', 'pseudo_weather') else '-sidestart' if category == 'side_condition' else '-start'
        target = '' if command in ('-weather', '-fieldstart') else 'p1: Alice|' if command == '-sidestart' else 'p1a: Pikachu|'
        with pytest.raises(ValueError):
            validate_protocol_record(f'|{command}|{target}{row["id"]}', reader_rules=NATIVE11_CONTEXT)
    validate_protocol_record('|-start|p1a: Pikachu|Substitute', reader_rules=HISTORICAL10_CONTEXT)
    for record in ('|-start|p1a: Pikachu|unreviewed', '|-swapsideconditions', '|cant|p1a: Pikachu'):
        with pytest.raises(ValueError):
            validate_protocol_record(record, reader_rules=NATIVE11_CONTEXT)


def test_native_universal_forms_and_nearby_rejections():
    # Side.emitRequest / Battle.start / Harvest.onResidual / Battle.runAction.
    good = ('|request|null', '|rated|', '|rated|Rated battle',
            '|-enditem|p1a: Pikachu|Life Orb|[from] move: Knock Off|[of] p2a: Snorlax',
            '|-item|p1a: Trevenant|Sitrus Berry|[from] ability: Harvest',
            '|-damage|p1a: Pikachu|80/100|[from] move: Whirlpool|[partiallytrapped]',
            '|detailschange|p1: Terapagos|Terapagos, L77, F|[silent]',
            '|-prepare|p1a: Slowking|Chilly Reception|[premajor]')
    for record in good:
        validate_protocol_record(record, reader_rules=NATIVE11_CONTEXT)
    for record in ('|request|', '|request| null', '|request|[]', '|request|{"rqid":null}',
                   '|rated| ', '|rated||extra',
                   '|-item|p1a: Trevenant|Life Orb|[from] ability: Harvest',
                   '|-item|p1a: Trevenant|Imaginary Orb',
                   '|detailschange|p1: Terapagos|Terapagos|[silently]',
                   '|detailschange|p3: Terapagos|Terapagos|[silent]',
                   '|detailschange|p1:  Terapagos|Terapagos|[silent]',
                   '|-damage|p1a: Pikachu|80/100|[from] move: Splash|[partiallytrapped]',
                   '|-damage|p1a: Pikachu|80/100|[partiallytrapped]'):
        with pytest.raises(ValueError):
            validate_protocol_record(record, reader_rules=NATIVE11_CONTEXT)


def test_request_clear_is_not_a_fabricated_request_and_silent_details_are_not_hp():
    from neural.pipeline_record import _prefix
    from neural.public_health import project_public_health
    import hashlib, json
    def seal(value):
        value["protocol_prefix_hash"] = hashlib.sha256(json.dumps(value["protocol_prefix"],ensure_ascii=False,separators=(",", ":")).encode()).hexdigest()
        return value
    clear = {'protocol_prefix': ['|request|null'], 'event_cursor': 1, 'request': None}
    _prefix(seal(clear), 'clear', reader_rules=NATIVE11_CONTEXT)
    with pytest.raises(ValueError):
        _prefix({**clear, 'request': {'rqid': 1}}, 'false request', reader_rules=NATIVE11_CONTEXT)
    resumed = {'protocol_prefix': ['|request|null', '|request|{"rqid":1}'],
               'event_cursor': 2, 'request': {'rqid': 1}}
    _prefix(seal(resumed), 'resumed', reader_rules=NATIVE11_CONTEXT)
    assert project_public_health(['|detailschange|p1: Terapagos|Terapagos, L77, F|[silent]']) == {}
