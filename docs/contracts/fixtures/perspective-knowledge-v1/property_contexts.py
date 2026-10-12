"""Hand-authored finite applicability/expansion contract, not runtime coverage."""

RULES={}
def add(properties,*applications):
    for prop in properties.split():
        RULES[prop]=[{'context':context,'scope':scope,'subject':subject,'coverage':'all_relevant'} for context,scope,subject in applications]

add('roster_species level gender shiny ball details',('original','owner','roster'),('current','both','roster_or_appearance'))
add('roster_order',('original','owner','roster'))
add('party_position',('current','owner','roster'))
add('active_slot',('current','both','roster_or_appearance'))
add('roster_size',('original','owner','side'),('current','both','side'))
add('starting_moves submitted_nature submitted_evs submitted_ivs submitted_happiness starting_tera',('original','owner','roster'))
add('calculated_stats hp_max',('original','owner','roster'),('current','both','roster_or_appearance'))
add('current_moves',('current','owner','roster'))
add('move_execution',('current','both','roster_or_appearance'))
add('move_incarnation',('current','owner','move'))
add('hp fainted status status_observed_since status_elapsed status_remaining boosts form types tera transformed appearance identity_reveal',('current','both','roster_or_appearance'))
add('pp max_pp disabled maybe_disabled',('current','owner','move'),('request','owner','move'))
add('trapped maybe_trapped lock',('current','owner','roster'),('request','owner','roster'))
add('persistent_effect',('current','both','persistent_effect_member'))
add('single_turn_effect',('current','both','single_turn_effect_member'))
add('single_move_effect',('current','both','single_move_effect_member'))
add('side_condition side_condition_layers',('current','both','condition_effect'))
add('weather weather_effective',('current','both','weather_effect'))
add('terrain',('current','both','terrain_effect'))
add('pseudo_weather',('current','both','room_effect'))
add('field_remaining',('current','both','field_effect'))
add('pending_intent pending_effect pending_power',('current','both','pending_effect_member'))
add('item ability',('original','owner','roster'),('current','both','roster_or_appearance'))
add('item_held item_effective ability_effective',('current','both','roster_or_appearance'))
add('boundary_kind request_presence',('current','owner','side'),('request','owner','side'))


def subject_matches(subject,selector,effect_key):
    tail=subject.split(':',1)[1]
    if selector in ['condition_effect','weather_effect','terrain_effect','room_effect','pending_effect_member','field_effect']: return tail=='side' and effect_key is not None
    if selector in ['persistent_effect_member','single_turn_effect_member','single_move_effect_member']: return (tail.startswith('roster:') or tail.startswith('appearance:')) and ':move:' not in tail and effect_key is not None
    if selector=='side': return tail=='side' and effect_key is None
    if selector=='roster': return tail.startswith('roster:') and ':move:' not in tail and effect_key is None
    if selector=='roster_or_appearance': return (tail.startswith('roster:') or tail.startswith('appearance:')) and ':move:' not in tail and effect_key is None
    if selector=='move': return ':move:' in tail and effect_key is None
    return False


def applies(fact,context):
    own=fact['subject'].startswith(fact['owner']+':')
    def match(a):
        key=fact['effect_key']
        # Collection sentinels never supply a known named member.
        if key is None and a['subject'] not in ['side','roster','roster_or_appearance','move','field_effect'] and fact['state'] in ['unknown','known_absent','inapplicable']:
            key='collection-sentinel'
        return subject_matches(fact['subject'],a['subject'],key)
    return any(a['context']==context and (a['scope']=='both' or (a['scope']=='owner')==own) and match(a) for a in RULES[fact['property']])
