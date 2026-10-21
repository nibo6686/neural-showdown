import copy
import pytest
from neural.version_profile import NATIVE11_CONTEXT as C
from neural.protocol_contract import validate_protocol_record
from neural.typed_state import project_public_typed_state, validate_public_typed_state

START='|-start|p1a: Regigigas|ability: Slow Start'
SWITCH='|switch|p1a: Regigigas|Regigigas, L100|100/100'

@pytest.mark.parametrize('end',['|-end|p1a: Regigigas|Slow Start','|-end|p1a: Regigigas|Slow Start|[silent]'])
def test_ability_presence_and_clear(end):
    prefix=[SWITCH,START]
    for line in prefix+[end]:
        validate_protocol_record(line, reader_rules=C)
    assert project_public_typed_state(prefix,reader_rules=C)['ability_effects_by_ident']=={'p1: Regigigas':['slowstart']}
    obs={'perspective':'p1','protocol_prefix':prefix,'view':{'self_team':[{'ident':'p1: Regigigas','volatiles':[], 'ability_effects':['slowstart']}]}}
    validate_public_typed_state(obs, reader_rules=C)
    bad=copy.deepcopy(obs);bad['view']['self_team'][0]['ability_effects']=[]
    with pytest.raises(ValueError,match='Ability state'):
        validate_public_typed_state(bad,reader_rules=C)
    obs['protocol_prefix'].append(end);obs['view']['self_team'][0]['ability_effects']=[]
    validate_public_typed_state(obs,reader_rules=C)
    assert project_public_typed_state(prefix,reader_rules=C)['ability_effects_by_ident']=={'p1: Regigigas':[]}

@pytest.mark.parametrize('line',['|-start|p1a: Regigigas|Slow Start','|-start|p1a: Regigigas|move: Slow Start','|-end|p1a: Regigigas|ability: Slow Start','|-end|p1a: Regigigas|Slow Start|[silent]|extra','|-end|p1a: Regigigas|slowstart'])
def test_malformed_ability_lifecycle(line):
    with pytest.raises(ValueError):
        validate_protocol_record(line,reader_rules=C)
