"""Native source review is a per-ID gate, independent of historical decoding."""
import pytest
from neural.protocol_contract import validate_protocol_record
from neural.version_profile import NATIVE11_CONTEXT, HISTORICAL10_CONTEXT


def test_native_effect_shapes_and_source_delta_rejections():
    for record in ('|cant|p1a: Pikachu|par', '|heal|p1a: Pikachu|100/100',
                   '|-weather|none', '|-fieldstart|move: Gravity', '|-fieldend|move: Gravity'):
        validate_protocol_record(record, reader_rules=NATIVE11_CONTEXT)
    for row in NATIVE11_CONTEXT.inventory['effect_source_comparison']['entries']:
        if row['status'] == 'unchanged' or row['category'] == 'major_status':
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
