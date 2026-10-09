import fs from 'node:fs';
import path from 'node:path';

type JsonObject = Record<string, unknown>;
export interface ProtocolContract {
  schema_version: 'showdown-protocol-contract/v2';
  simulator: { package: string; version: string; format: string; mod: string; game_type: string };
  source_basis: string[];
  framing_only_records: Array<{ record: string; disposition: string; evidence: string }>;
  supported_commands: string[];
  recognized_unsupported_commands: Array<{ token: string; kind: string; reason: string; source?: string }>;
  record_fixtures: Array<Record<string, unknown>>;
  rejection_fixtures: Array<{ record: string; kind: string }>;
  valid_record_controls: Array<{ token: string; record: string; evidence: string; reconstruction_scope: string }>;
  validation_rules: {
    integer: { lexeme: string; leading_zeroes: string; safe_limit: number };
    request: { root: string; rqid_presence: string; rqid_type: string; rqid_null: string; rqid_boolean: string; non_finite_numbers: string; other_properties: string };
    health_condition: { fainted: string; ratio: string; numerator_limit: string; statuses: string[] };
    major_status: {
      ids: string[];
      active_target: 'canonical-singles-active';
      bare_commands: string[];
      apply_forms: Array<{tags: string[]; statuses?: string[]}>;
      cure_forms: Array<{tags: string[]; statuses?: string[]}>;
    };
    player_ident: { side_ids: string[]; slots: string[]; separator: string; name: string };
    hitcount: { target_roles: Array<'active' | 'side-only'>; count_values: number[] };
    entry_hazard: { layers: Record<string, number>; start_forms: Record<string, string>; removal_sources: string[] };
    screen: { ids: string[]; start_forms: Record<string, string>; end_forms: Record<string, string>; excluded_forms: string[] };
    court_change: { command: '-swapsideconditions'; activation_command: '-activate'; activation_effect: 'move: Court Change'; transferred_ids: string[]; excluded_ids: string[] };
    weather: { ids: string[]; ability_origins: Record<string, string[]>; move_origins: Record<string, string[]> };
    terrain: { ids: string[]; public_names: Record<string, string>; ability_origins: Record<string, string[]> };
    trick_room: { effect: string; start_command: '-fieldstart'; end_command: '-fieldend'; source_tag: string; source_role: 'active' };
    switch_drag: { optional_tag: string };
    boost_event: { stats: string[]; delta_min: number; delta_max: number; set_min: number; set_max: number; tags: string[]; tag_order: string[] };
    health_event_tags: Record<'damage' | 'heal' | 'sethp', string[]>;
    health_event_tag_order: Record<'damage' | 'heal' | 'sethp', string[]>;
    event_tag_cardinality: Record<'damage' | 'heal' | 'sethp' | 'boost', string[]>;
    heal_wisher_dependency: { required_from: string; required_tag_order: string[] };
    healing_wish_heal: { required_from: string; required_tag_order: string[]; target_role: 'active'; health: string };
    future_sight: { effect: string; activation_command: '-start'; resolution_command: '-end'; target_role: 'active'; payload_fields: number };
    repeat_use_hint: { messages: string[]; payload_fields: number };
    item: {
      payloads: string[];
      active_target: 'canonical-singles-active';
      dash_item_forms: Array<{tags: string[]; payloads?: string[]}>;
      dash_enditem_forms: Array<{tags: string[]; payloads?: string[]}>;
      bare_commands: string[];
      bare_tags: string[];
    };
    ability: {
      dash_templates: string[];
      bare_templates: string[];
      trace_source_tag: string;
      trace_of_tag: string;
      trace_actor_role: 'active';
      trace_source_role: 'opposing-active';
      payload_domains: Record<'dash_reveal' | 'dash_boost' | 'dash_trace_copy' | 'bare_reveal', string[]>;
      source_evidence: Record<'dash_reveal' | 'dash_boost' | 'dash_trace_copy' | 'bare_reveal', string>;
    };
    detailschange: { condition: string };
    trapped_activation: { token: '-activate'; target_role: 'active'; effect: 'trapped'; payload_fields: number };
    singleturn: { untagged_effects: string[]; tagged_forms: Array<{ effect: string; tag: string; tag_value: string; ident_role?: 'active' | 'side-or-active' }> };
    singlemove: { forms: string[][] };
    anim: { forms: string[][]; actor_role: 'active'; target_role: 'active' };
    tier: { payload_fields: number; label: string };
    bigerror: { auto_tie: string; turns_left_values: number[] };
  };
}

export class ProtocolContractError extends Error {}

const EXPECTED_RULES = {
  integer: { lexeme: 'ascii-decimal', leading_zeroes: 'reject', safe_limit: 9007199254740991 },
  request: {
    root: 'object', rqid_presence: 'optional', rqid_type: 'safe-integer', rqid_null: 'reject',
    rqid_boolean: 'reject', non_finite_numbers: 'reject', other_properties: 'transient-private',
  },
  health_condition: {
    fainted: '0 fnt', ratio: 'positive-safe-integer-pair', numerator_limit: 'at-most-denominator',
    statuses: ['brn', 'par', 'slp', 'psn', 'tox', 'frz'],
  },
  // `Conditions.<major>.onStart` emits only these public forms. Plain
  // records cover ordinary move effects and Synchronize; the tagged rows are
  // the finite generated item/ability and Rest paths. Status counters,
  // sources, selectors, and timing never enter the public model.
  major_status: {
    ids: ['brn', 'par', 'slp', 'psn', 'tox', 'frz'],
    active_target: 'canonical-singles-active',
    // Pinned Gen 9 emitters use only dashed status commands. Bare aliases are
    // rejected before they can mutate the public status projection.
    bare_commands: [],
    apply_forms: [
      { tags: [] },
      { tags: ['[from] move: Rest'], statuses: ['slp'] },
      { tags: ['[from] item: Flame Orb'], statuses: ['brn'] },
      { tags: ['[from] item: Toxic Orb'], statuses: ['tox'] },
      { tags: ['[from] ability: Effect Spore', '[of] opposing-active'], statuses: ['slp', 'par', 'psn'] },
      { tags: ['[from] ability: Flame Body', '[of] opposing-active'], statuses: ['brn'] },
      { tags: ['[from] ability: Static', '[of] opposing-active'], statuses: ['par'] },
      { tags: ['[from] ability: Toxic Chain', '[of] opposing-active'], statuses: ['tox'] },
      { tags: ['[from] ability: Poison Touch', '[of] opposing-active'], statuses: ['psn'] },
      { tags: ['[from] move: Sleep Powder'], statuses: ['slp'] },
      { tags: ['[from] move: Hypnosis'], statuses: ['slp'] },
      { tags: ['[from] move: Spore'], statuses: ['slp'] },
    ],
    cure_forms: [
      { tags: ['[msg]'] },
      { tags: ['[from] ability: Natural Cure'] },
      { tags: ['[from] move: Flare Blitz'], statuses: ['frz'] },
      { tags: ['[from] move: Fusion Flare'], statuses: ['frz'] },
      { tags: ['[from] move: Pyro Ball'], statuses: ['frz'] },
      { tags: ['[from] move: Sacred Fire'], statuses: ['frz'] },
      { tags: ['[from] move: Scald'], statuses: ['frz'] },
      { tags: ['[from] move: Scorching Sands'], statuses: ['frz'] },
      { tags: ['[from] move: Hydro Steam'], statuses: ['frz'] },
      { tags: ['[from] move: Matcha Gotcha'], statuses: ['frz'] },
      { tags: ['[from] move: Steam Eruption'], statuses: ['frz'] },
    ],
  },
  player_ident: {
    side_ids: ['p1', 'p2'], slots: ['', 'a', 'b', 'c', 'd', 'e', 'f'],
    separator: ': ', name: 'trimmed-nonempty-text',
  },
  // BattleActions emits -hitcount only for an ordinary multi-hit target. In
  // Gen 9 Random Battle singles it is active (`p1a`/`p2a`) unless the final
  // hit has already fainted it, when Pokemon.toString() emits `p1`/`p2`.
  hitcount: { target_roles: ['active', 'side-only'], count_values: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] },
  switch_drag: { optional_tag: '[from] trimmed-nonempty-text' },
  // Direct Gen 9 Random Battle hazards only. Spikes and Toxic Spikes emit one
  // -sidestart per layer; Stealth Rock and Sticky Web are one-layer conditions.
  entry_hazard: {
    layers: { spikes: 3, toxicspikes: 2, stealthrock: 1, stickyweb: 1 },
    start_forms: { spikes: 'Spikes', toxicspikes: 'move: Toxic Spikes', stealthrock: 'move: Stealth Rock', stickyweb: 'move: Sticky Web' },
    removal_sources: ['Rapid Spin', 'Mortal Spin', 'Defog'],
  },
  // Each generated screen is a nonstacking Side condition. Side.addSideCondition
  // suppresses duplicate SideStart; every real removal calls its SideEnd callback
  // and emits exactly the matching tagless form. No duration/source/item is public.
  screen: {
    ids: ['reflect', 'lightscreen', 'auroraveil'],
    start_forms: { reflect: 'Reflect', lightscreen: 'move: Light Screen', auroraveil: 'move: Aurora Veil' },
    end_forms: { reflect: 'Reflect', lightscreen: 'move: Light Screen', auroraveil: 'move: Aurora Veil' },
    excluded_forms: ['Safeguard', 'Mist'],
  },
  // Court Change has one source-emitted atomic public boundary. Its no-payload
  // record carries no side/actor fields; the following activation identifies the
  // canonical active user. Only these pinned Side condition IDs move in singles.
  court_change: {
    command: '-swapsideconditions', activation_command: '-activate', activation_effect: 'move: Court Change',
    transferred_ids: ['mist', 'lightscreen', 'reflect', 'spikes', 'safeguard', 'tailwind', 'toxicspikes', 'stealthrock', 'waterpledge', 'firepledge', 'grasspledge', 'stickyweb', 'auroraveil', 'luckychant'],
    excluded_ids: ['gmaxsteelsurge', 'gmaxcannonade', 'gmaxvinelash', 'gmaxwildfire', 'gmaxvolcalith'],
  },
  // Pinned conditions.ts emits one public -weather family. In the operative
  // Gen 9 Random Battle singles domain, move starts are untagged, ability
  // starts identify the revealed active setter, upkeep has one literal tag,
  // and natural expiry emits only `none`. Weather rocks affect only private
  // duration and therefore do not create another public grammar form.
  weather: {
    ids: ['RainDance', 'SunnyDay', 'Sandstorm', 'Snowscape'],
    ability_origins: {
      RainDance: ['Drizzle'],
      SunnyDay: ['Drought', 'Orichalcum Pulse'],
      Sandstorm: ['Sand Stream'],
      Snowscape: ['Snow Warning'],
    },
    move_origins: {
      RainDance: ['Rain Dance'],
      SunnyDay: ['Sunny Day'],
      Snowscape: ['Snowscape', 'Chilly Reception'],
    },
  },
  // The operative Gen 9 Random Battle set domain has no terrain move root.
  // Pinned terrain conditions expose only active ability setters and untagged
  // field-end records; duration/source state stays in Field.terrainState.
  terrain: {
    ids: ['electricterrain', 'grassyterrain', 'psychicterrain'],
    public_names: {
      electricterrain: 'move: Electric Terrain',
      grassyterrain: 'move: Grassy Terrain',
      psychicterrain: 'move: Psychic Terrain',
    },
    ability_origins: {
      electricterrain: ['Electric Surge', 'Hadron Engine'],
      grassyterrain: ['Grassy Surge', 'Seed Sower'],
      psychicterrain: ['Psychic Surge'],
    },
  },
  // Trick Room is the sole generated pseudo-weather setter. Its FieldStart
  // names the active move user; reapplication and expiry both use the bare
  // FieldEnd form. Persistent's extra tag has no generated Gen 9 RB root.
  trick_room: {
    effect: 'move: Trick Room',
    start_command: '-fieldstart',
    end_command: '-fieldend',
    source_tag: '[of]',
    source_role: 'active',
  },
  boost_event: {
    stats: ['atk', 'def', 'spa', 'spd', 'spe', 'accuracy', 'evasion'],
    delta_min: 0, delta_max: 12, set_min: -6, set_max: 6,
    tags: ['[from] trimmed-nonempty-text', '[silent]', '[zeffect]'],
    tag_order: ['[from]', '[silent]', '[zeffect]'],
  },
  health_event_tags: {
    damage: ['[from] trimmed-nonempty-text', '[of] player-ident', '[silent]', '[partiallytrapped]'],
    heal: ['[from] trimmed-nonempty-text', '[of] player-ident', '[silent]', '[zeffect]', '[wisher] trimmed-nonempty-text'],
    sethp: ['[from] trimmed-nonempty-text', '[silent]'],
  },
  health_event_tag_order: {
    damage: ['[from]', '[of]', '[partiallytrapped]', '[silent]'],
    heal: ['[from]', '[of]', '[wisher]', '[zeffect]', '[silent]'],
    sethp: ['[from]', '[silent]'],
  },
  event_tag_cardinality: {
    damage: ['[from]', '[of]', '[silent]', '[partiallytrapped]'],
    heal: ['[from]', '[of]', '[silent]', '[zeffect]', '[wisher]'],
    sethp: ['[from]', '[silent]'],
    boost: ['[from]', '[silent]', '[zeffect]'],
  },
  // Pinned data/moves.ts Moves.wish.onEnd is the sole base-package [wisher]
  // emitter. Its provenance tags form one indivisible public raw record.
  heal_wisher_dependency: {
    required_from: '[from] move: Wish',
    required_tag_order: ['[from]', '[wisher]'],
  },
  // Pinned data/moves.ts Moves.healingwish.condition.onSwap first restores
  // full HP and clears status, then emits this one-tag public record.
  healing_wish_heal: {
    required_from: '[from] move: Healing Wish',
    required_tag_order: ['[from]'],
    target_role: 'active',
    health: '100/100',
  },
  // Pinned data/moves.ts Moves.futuresight.onTry and
  // data/conditions.ts Conditions.futuremove.onEnd emit these two exact
  // active-target records. The later damage event intentionally has no Future
  // Sight provenance tag, so it remains ordinary public HP evidence.
  future_sight: {
    effect: 'move: Future Sight',
    activation_command: '-start',
    resolution_command: '-end',
    target_role: 'active',
    payload_fields: 1,
  },
  // BattleActions emits this only after its cantusetwice guard creates and
  // removes the repeated move volatile. These are the generated move IDs.
  repeat_use_hint: {
    messages: [
      'Some effects can force a Pokemon to use Blood Moon again in a row.',
      'Some effects can force a Pokemon to use Gigaton Hammer again in a row.',
    ],
    payload_fields: 1,
  },
  // CE-04F1: these are the finite outputs of the operative singles
  // getPriorityItem/getItem selectors (including generated required items).
  // Only the documented public item emitters may disclose one of them.
  item: {
    payloads: [
      'Aguav Berry', 'Adamant Crystal', 'Air Balloon', 'Assault Vest', 'Binding Band', 'Blunder Policy', 'Booster Energy', 'Chesto Berry', 'Choice Band', 'Choice Scarf', 'Choice Specs', 'Clear Amulet', 'Cornerstone Mask', 'Custap Berry', 'Draco Plate', 'Dread Plate', 'Earth Plate', 'Eviolite', 'Figy Berry', 'Fist Plate', 'Flame Orb', 'Flame Plate', 'Focus Sash', 'Griseous Core', 'Heavy-Duty Boots', 'Hearthflame Mask', 'Iapapa Berry', 'Icicle Plate', 'Iron Plate', 'Leppa Berry', 'Leftovers', 'Light Ball', 'Light Clay', 'Loaded Dice', 'Lum Berry', 'Lustrous Globe', 'Lustrous Orb', 'Mago Berry', 'Magnet', 'Meadow Plate', 'Mind Plate', 'Mystic Water', 'Passho Berry', 'Pixie Plate', 'Power Herb', 'Rindo Berry', 'Rocky Helmet', 'Salac Berry', 'Scope Lens', 'Silk Scarf', 'Silver Powder', 'Sky Plate', 'Soul Dew', 'Splash Plate', 'Spooky Plate', 'Sitrus Berry', 'Stone Plate', 'Throat Spray', 'Toxic Orb', 'Toxic Plate', 'Weakness Policy', 'Wellspring Mask', 'White Herb', 'Wide Lens', 'Wiki Berry', 'Zap Plate',
    ],
    active_target: 'canonical-singles-active',
    dash_item_forms: [
      {tags: [], payloads: ['Air Balloon']},
      {tags: ['[from] ability: Frisk', '[of] opposing-active']},
      {tags: ['[from] move: Trick']},
      {tags: ['[from] move: Switcheroo']},
      {tags: ['[from] move: Recycle'], payloads: ['White Herb']},
    ],
    dash_enditem_forms: [
      // Air Balloon pops directly in data/items.ts. Pinned Pokemon.useItem also
      // emits the same tagless grammar for the finite generated non-Gem
      // consumption roots listed here; tags distinguish neither source.
      {tags: [], payloads: ['Air Balloon', 'Booster Energy', 'Focus Sash', 'Power Herb', 'Throat Spray', 'Weakness Policy', 'White Herb']},
      // Pokemon.eatItem emits this only for selector-reachable edible items.
      // Resist berries additionally emit their own [weaken] record, which is
      // outside this bounded CE-04F1 grammar.
      {tags: ['[eat]'], payloads: ['Aguav Berry', 'Chesto Berry', 'Custap Berry', 'Figy Berry', 'Iapapa Berry', 'Leppa Berry', 'Lum Berry', 'Mago Berry', 'Passho Berry', 'Rindo Berry', 'Salac Berry', 'Sitrus Berry', 'Wiki Berry']},
      {tags: ['[from] move: Knock Off', '[of] opposing-active']},
      {tags: ['[silent]', '[from] move: Trick']},
      {tags: ['[silent]', '[from] move: Switcheroo']},
    ],
    bare_commands: ['item', 'enditem'],
    bare_tags: [],
  },
  // The operative Gen 9 Random Battle singles path has three source-backed
  // -ability templates: a reveal, boost reveal, and Trace copy. Bare ability
  // is retained only as its old plain raw-only spelling. Move replacements,
  // Gastro Acid suppression, weather failure, Receiver, and Power of Alchemy
  // have no generated singles route and remain outside this published grammar.
  ability: {
    dash_templates: ['reveal', 'boost', 'trace-copy'],
    bare_templates: ['reveal'],
    trace_source_tag: '[from] ability: Trace',
    trace_of_tag: '[of] ',
    trace_actor_role: 'active',
    trace_source_role: 'opposing-active',
    payload_domains: {
      dash_reveal: ['Air Lock', 'As One', 'Beads of Ruin', 'Cloud Nine', 'Comatose', 'Gooey', 'Mirror Armor', 'Mold Breaker', 'Pressure', 'Sturdy', 'Sword of Ruin', 'Tablets of Ruin', 'Tangling Hair', 'Teraform Zero', 'Teravolt', 'Turboblaze', 'Unnerve', 'Vessel of Ruin'],
      dash_boost: ['Anger Shell', 'Battle Bond', 'Berserk', 'Chilling Neigh', 'Competitive', 'Dauntless Shield', 'Defiant', 'Download', 'Embody Aspect (Cornerstone)', 'Embody Aspect (Hearthflame)', 'Embody Aspect (Teal)', 'Embody Aspect (Wellspring)', 'Gooey', 'Grim Neigh', 'Gulp Missile', 'Intimidate', 'Intrepid Sword', 'Justified', 'Lightning Rod', 'Mirror Armor', 'Motor Drive', 'Moxie', 'Rattled', 'Sap Sipper', 'Soul-Heart', 'Speed Boost', 'Stamina', 'Storm Drain', 'Tangling Hair', 'Thermal Exchange', 'Water Compaction', 'Weak Armor', 'Well-Baked Body', 'Wind Rider'],
      dash_trace_copy: ['Adaptability', 'Aftermath', 'Air Lock', 'Analytic', 'Anger Shell', 'Arena Trap', 'Aroma Veil', 'Bad Dreams', 'Beads of Ruin', 'Berserk', 'Big Pecks', 'Blaze', 'Bulletproof', 'Cheek Pouch', 'Chilling Neigh', 'Chlorophyll', 'Clear Body', 'Cloud Nine', 'Competitive', 'Compound Eyes', 'Contrary', 'Corrosion', 'Cud Chew', 'Cursed Body', 'Cute Charm', 'Damp', 'Dancer', 'Dauntless Shield', 'Defiant', 'Download', "Dragon's Maw", 'Drizzle', 'Drought', 'Dry Skin', 'Early Bird', 'Earth Eater', 'Effect Spore', 'Electric Surge', 'Electromorphosis', 'Filter', 'Flame Body', 'Flash Fire', 'Flower Veil', 'Fluffy', 'Frisk', 'Full Metal Body', 'Fur Coat', 'Galvanize', 'Good as Gold', 'Gooey', 'Grassy Surge', 'Grim Neigh', 'Gulp Missile', 'Guts', 'Hadron Engine', 'Harvest', 'Heatproof', 'Heavy Metal', 'Huge Power', 'Hustle', 'Hydration', 'Ice Body', 'Ice Scales', 'Infiltrator', 'Inner Focus', 'Insomnia', 'Intimidate', 'Intrepid Sword', 'Iron Fist', 'Justified', 'Keen Eye', 'Leaf Guard', 'Levitate', 'Libero', 'Light Metal', 'Lightning Rod', 'Limber', 'Liquid Ooze', 'Liquid Voice', 'Magic Bounce', 'Magic Guard', 'Magician', 'Magnet Pull', 'Mega Launcher', "Mind's Eye", 'Mirror Armor', 'Mold Breaker', 'Motor Drive', 'Moxie', 'Multiscale', 'Mycelium Might', 'Natural Cure', 'No Guard', 'Oblivious', 'Orichalcum Pulse', 'Overcoat', 'Overgrow', 'Own Tempo', 'Pickpocket', 'Pixilate', 'Poison Heal', 'Poison Touch', 'Power Spot', 'Prankster', 'Pressure', 'Prism Armor', 'Protean', 'Psychic Surge', 'Punk Rock', 'Pure Power', 'Purifying Salt', 'Queenly Majesty', 'Quick Feet', 'Rattled', 'Reckless', 'Regenerator', 'Rock Head', 'Rocky Payload', 'Rough Skin', 'Sand Force', 'Sand Rush', 'Sand Stream', 'Sap Sipper', 'Scrappy', 'Seed Sower', 'Serene Grace', 'Shadow Shield', 'Shadow Tag', 'Sharpness', 'Shed Skin', 'Sheer Force', 'Shell Armor', 'Shield Dust', 'Skill Link', 'Slow Start', 'Slush Rush', 'Sniper', 'Snow Warning', 'Solid Rock', 'Soul-Heart', 'Soundproof', 'Speed Boost', 'Stakeout', 'Stamina', 'Static', 'Steely Spirit', 'Sticky Hold', 'Storm Drain', 'Strong Jaw', 'Sturdy', 'Supreme Overlord', 'Surge Surfer', 'Swarm', 'Swift Swim', 'Sword of Ruin', 'Synchronize', 'Tablets of Ruin', 'Tangling Hair', 'Technician', 'Teravolt', 'Thermal Exchange', 'Thick Fat', 'Tinted Lens', 'Torrent', 'Tough Claws', 'Toxic Boost', 'Toxic Chain', 'Toxic Debris', 'Transistor', 'Triage', 'Truant', 'Turboblaze', 'Unaware', 'Unburden', 'Unnerve', 'Unseen Fist', 'Vessel of Ruin', 'Vital Spirit', 'Volt Absorb', 'Water Absorb', 'Water Bubble', 'Water Compaction', 'Water Veil', 'Weak Armor', 'Well-Baked Body', 'Wind Rider'],
      bare_reveal: ['Air Lock', 'As One', 'Beads of Ruin', 'Cloud Nine', 'Comatose', 'Gooey', 'Mirror Armor', 'Mold Breaker', 'Pressure', 'Sturdy', 'Sword of Ruin', 'Tablets of Ruin', 'Tangling Hair', 'Teraform Zero', 'Teravolt', 'Turboblaze', 'Unnerve', 'Vessel of Ruin'],
    },
    source_evidence: {
      dash_reveal: 'data/random-battles/gen9/sets.json candidate abilities plus generated permanent form defaults intersect literal data/abilities.ts -ability emitters',
      dash_boost: 'data/random-battles/gen9/sets.json generated callbacks plus permanent form defaults reaching sim/battle.ts Battle#boost, enumerated by emitted effect.name rather than holder ability name',
      dash_trace_copy: 'data/random-battles/gen9/sets.json candidate abilities filtered by Abilities.trace.onUpdate notrace guard',
      bare_reveal: 'B02 compatibility spelling restricted to the same finite public reveal domain',
    },
  },
  detailschange: { condition: 'optional-health-condition' },
  trapped_activation: { token: '-activate', target_role: 'active', effect: 'trapped', payload_fields: 2 },
  singleturn: {
    untagged_effects: [
      'move: Protect', 'move: Beak Blast', 'Crafty Shield', 'move: Electrify', 'move: Endure',
      'move: Focus Punch', 'move: Follow Me', 'Protect', 'move: Magic Coat', 'Mat Block',
      'Max Guard', 'Powder', 'Quick Guard', 'move: Rage Powder', 'move: Roost', 'move: Shell Trap',
      'Snatch', 'move: Spotlight', 'Wide Guard',
    ],
    tagged_forms: [
      { effect: 'move: Follow Me', tag: '[zeffect]', tag_value: 'none' },
      // Helping Hand receives its source as the acting Pokemon, whose
      // Pokemon.toString() form includes an active slot.
      { effect: 'Helping Hand', tag: '[of]', tag_value: 'player-ident', ident_role: 'active' },
    ],
  },
  singlemove: { forms: [['Destiny Bond'], ['Glaive Rush', '[silent]'], ['Grudge'], ['Rage']] },
  // All four forms are exactly three payload fields: active actor, literal
  // source animation label, active target. Spectral Thief remains the
  // separately reviewed compatibility form; the other three are the complete
  // directly generated Gen 9 Random Battle family.
  anim: {
    forms: [['Spectral Thief'], ['Solar Beam'], ['Meteor Beam'], ['Dragon Darts']],
    actor_role: 'active', target_role: 'active',
  },
  tier: { payload_fields: 1, label: 'nonempty-text' },
  bigerror: {
    auto_tie: 'You will auto-tie if the battle doesn\'t end in <N> turn(s) (on turn 1000).',
    turns_left_values: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 200, 300, 400, 500],
  },
};
const ROOT_KEYS = [
  'schema_version', 'simulator', 'source_basis', 'framing_only_records', 'supported_commands', 'recognized_unsupported_commands',
  'record_fixtures', 'rejection_fixtures', 'disposition_rules', 'validation_rules', 'valid_record_controls',
];
const SIMULATOR = { package: 'pokemon-showdown', version: '0.11.10', format: 'gen9randombattle', mod: 'gen9', game_type: 'singles' };
const DISPOSITION_KEYS = ['supported', 'recognized_unsupported', 'malformed_supported', 'unknown', 'privacy'];
const CLASSIFICATIONS = new Set(['raw-only', 'represented', 'represented (bounded Topsy-Turvy)']);
const UNSUPPORTED_KINDS = new Set(['unresolved_alias', 'internal_alias', 'unsupported_stop']);
const REJECTION_KINDS = new Set(['malformed', 'unknown', ...UNSUPPORTED_KINDS]);

function fail(detail: string): never {
  throw new ProtocolContractError(`Invalid shared protocol contract: ${detail}.`);
}

function isObject(value: unknown): value is JsonObject {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function exactKeys(value: JsonObject, required: string[], optional: string[], label: string): void {
  const keys = Object.keys(value);
  const missing = required.filter((key) => !Object.hasOwn(value, key));
  const extra = keys.filter((key) => !required.includes(key) && !optional.includes(key));
  if (missing.length || extra.length) fail(`${label} keys (missing: ${missing.join(',') || 'none'}; unsupported: ${extra.join(',') || 'none'})`);
}

function string(value: unknown, label: string): asserts value is string {
  if (typeof value !== 'string' || value.trim() === '') fail(`${label} must be nonempty text`);
}

function stringArray(value: unknown, label: string, nonempty = true): asserts value is string[] {
  if (!Array.isArray(value) || (nonempty && value.length === 0) || value.some((item) => typeof item !== 'string' || !item.trim())) {
    fail(`${label} must be ${nonempty ? 'a nonempty ' : 'an '}array of nonempty strings`);
  }
}

function sameJson(left: unknown, right: unknown): boolean {
  if (Array.isArray(left) || Array.isArray(right)) {
    return Array.isArray(left) && Array.isArray(right) && left.length === right.length
      && left.every((item, index) => sameJson(item, right[index]));
  }
  if (isObject(left) || isObject(right)) {
    if (!isObject(left) || !isObject(right)) return false;
    const leftKeys = Object.keys(left).sort();
    const rightKeys = Object.keys(right).sort();
    return sameJson(leftKeys, rightKeys) && leftKeys.every((key) => sameJson(left[key], right[key]));
  }
  return left === right;
}

function commandToken(value: unknown, label: string): asserts value is string {
  if (typeof value !== 'string' || !(value === 't:' || /^-?[a-z][a-z0-9]*$/.test(value))) fail(`${label} is not a supported protocol token`);
}

function recordToken(record: unknown, label: string): string {
  if (typeof record !== 'string' || !record.startsWith('|') || record.includes('\n') || record.includes('\r')) {
    fail(`${label} must be one protocol record`);
  }
  return record.split('|')[1] ?? '';
}

function validateContract(value: unknown): ProtocolContract {
  if (!isObject(value)) fail('root must be an object');
  exactKeys(value, ROOT_KEYS, [], 'root');
  if (value.schema_version !== 'showdown-protocol-contract/v2') fail('unsupported schema_version');
  if (!isObject(value.simulator)) fail('simulator must be an object');
  exactKeys(value.simulator, Object.keys(SIMULATOR), [], 'simulator');
  if (!sameJson(value.simulator, SIMULATOR)) fail('simulator provenance must match pokemon-showdown@0.11.10 gen9randombattle singles');
  stringArray(value.source_basis, 'source_basis');
  if (!Array.isArray(value.framing_only_records) || value.framing_only_records.length !== 1) fail('framing_only_records must define the single pinned separator record');
  const framing = value.framing_only_records[0];
  if (!isObject(framing)) fail('framing_only_records[0] must be an object');
  exactKeys(framing, ['record', 'disposition', 'evidence'], [], 'framing_only_records[0]');
  if (framing.record !== '|' || framing.disposition !== 'validate then filter from public prefixes'
    || framing.evidence !== 'pinned sim/battle.ts:1451,2754,2881 emits empty separator records') {
    fail('framing_only_records contains an unsupported or unproven record');
  }
  if (!isObject(value.validation_rules) || !sameJson(value.validation_rules, EXPECTED_RULES)) fail('validation_rules contains unsupported or inconsistent definitions');
  if (!isObject(value.disposition_rules)) fail('disposition_rules must be an object');
  exactKeys(value.disposition_rules, DISPOSITION_KEYS, [], 'disposition_rules');
  for (const [key, rule] of Object.entries(value.disposition_rules)) string(rule, `disposition_rules.${key}`);

  if (!Array.isArray(value.supported_commands) || value.supported_commands.length === 0) fail('supported_commands must be a nonempty array');
  value.supported_commands.forEach((token, index) => commandToken(token, `supported_commands[${index}]`));
  const supported = value.supported_commands as string[];
  const supportedSet = new Set(supported);
  if (supportedSet.size !== supported.length) fail('supported_commands contains duplicate tokens');

  if (!Array.isArray(value.recognized_unsupported_commands)) fail('recognized_unsupported_commands must be an array');
  const unsupported = new Map<string, string>();
  value.recognized_unsupported_commands.forEach((entry, index) => {
    if (!isObject(entry)) fail(`recognized_unsupported_commands[${index}] must be an object`);
    exactKeys(entry, ['token', 'kind', 'reason'], ['source'], `recognized_unsupported_commands[${index}]`);
    commandToken(entry.token, `recognized_unsupported_commands[${index}].token`);
    if (typeof entry.kind !== 'string' || !UNSUPPORTED_KINDS.has(entry.kind)) fail(`recognized_unsupported_commands[${index}].kind is unsupported`);
    string(entry.reason, `recognized_unsupported_commands[${index}].reason`);
    if (Object.hasOwn(entry, 'source')) string(entry.source, `recognized_unsupported_commands[${index}].source`);
    if (supportedSet.has(entry.token)) fail(`token ${entry.token} has conflicting supported/unsupported entries`);
    if (unsupported.has(entry.token)) fail(`duplicate recognized-unsupported token ${entry.token}`);
    unsupported.set(entry.token, entry.kind);
  });
  if (!supportedSet.has('-singlemove')) fail('-singlemove must have exact raw-evidence support');

  if (!Array.isArray(value.record_fixtures)) fail('record_fixtures must be an array');
  const fixtureTokens = new Set<string>();
  value.record_fixtures.forEach((fixture, index) => {
    const label = `record_fixtures[${index}]`;
    if (!isObject(fixture)) fail(`${label} must be an object`);
    exactKeys(fixture, ['token', 'record', 'inventory_classification', 'grammar_summary', 'evidence', 'inventory_grammar', 'fixture_reference'], ['pinned_emitter_sources', 'pinned_dynamic_emitter_source'], label);
    commandToken(fixture.token, `${label}.token`);
    if (recordToken(fixture.record, `${label}.record`) !== fixture.token) fail(`${label}.token does not match its record token`);
    if (!supportedSet.has(fixture.token)) fail(`${label}.token is not in supported_commands`);
    if (fixtureTokens.has(fixture.token)) fail(`duplicate record fixture for ${fixture.token}`);
    fixtureTokens.add(fixture.token);
    if (typeof fixture.inventory_classification !== 'string' || !CLASSIFICATIONS.has(fixture.inventory_classification)) fail(`${label}.inventory_classification is unsupported`);
    for (const key of ['grammar_summary', 'evidence', 'fixture_reference']) string(fixture[key], `${label}.${key}`);
    if (!isObject(fixture.inventory_grammar)) fail(`${label}.inventory_grammar must be an object`);
    exactKeys(fixture.inventory_grammar, ['required', 'optional', 'shape'], [], `${label}.inventory_grammar`);
    for (const [key, item] of Object.entries(fixture.inventory_grammar)) string(item, `${label}.inventory_grammar.${key}`);
    if (Object.hasOwn(fixture, 'pinned_emitter_sources')) stringArray(fixture.pinned_emitter_sources, `${label}.pinned_emitter_sources`);
    if (Object.hasOwn(fixture, 'pinned_dynamic_emitter_source')) string(fixture.pinned_dynamic_emitter_source, `${label}.pinned_dynamic_emitter_source`);
  });
  if (fixtureTokens.size !== supportedSet.size || [...supportedSet].some((token) => !fixtureTokens.has(token))) fail('record_fixtures must contain exactly one fixture per supported token');

  if (!Array.isArray(value.valid_record_controls) || value.valid_record_controls.length === 0) fail('valid_record_controls must be a nonempty array');
  value.valid_record_controls.forEach((control, index) => {
    const label = `valid_record_controls[${index}]`;
    if (!isObject(control)) fail(`${label} must be an object`);
    exactKeys(control, ['token', 'record', 'evidence', 'reconstruction_scope'], [], label);
    commandToken(control.token, `${label}.token`);
    if (!supportedSet.has(control.token) || recordToken(control.record, `${label}.record`) !== control.token) fail(`${label} has inconsistent command and record tokens`);
    string(control.evidence, `${label}.evidence`);
    string(control.reconstruction_scope, `${label}.reconstruction_scope`);
  });

  if (!Array.isArray(value.rejection_fixtures)) fail('rejection_fixtures must be an array');
  value.rejection_fixtures.forEach((fixture, index) => {
    const label = `rejection_fixtures[${index}]`;
    if (!isObject(fixture)) fail(`${label} must be an object`);
    exactKeys(fixture, ['record', 'kind'], [], label);
    if (typeof fixture.record !== 'string' || typeof fixture.kind !== 'string' || !REJECTION_KINDS.has(fixture.kind)) fail(`${label} has an unsupported rejection definition`);
    const token = fixture.record.startsWith('|') ? recordToken(fixture.record, `${label}.record`) : null;
    if (token === null && fixture.kind !== 'malformed') fail(`${label}.record must be a protocol record for its rejection kind`);
    if (fixture.kind === 'malformed' && token !== null && !supportedSet.has(token)) fail(`${label} marks an unsupported token as malformed`);
    if (fixture.kind === 'unknown' && token !== null && (supportedSet.has(token) || unsupported.has(token))) fail(`${label} marks a classified token unknown`);
    if (UNSUPPORTED_KINDS.has(fixture.kind) && (token === null || unsupported.get(token) !== fixture.kind)) fail(`${label} does not match its recognized-unsupported disposition`);
  });
  return value as unknown as ProtocolContract;
}

export function validateProtocolContract(value: unknown): ProtocolContract {
  return validateContract(value);
}

export function loadProtocolContract(assetPath?: string): ProtocolContract {
  if (assetPath !== undefined) {
    try {
      return validateContract(JSON.parse(fs.readFileSync(assetPath, 'utf8')) as unknown);
    } catch (error) {
      if (error instanceof ProtocolContractError) throw error;
      throw new ProtocolContractError(`Unable to load shared protocol contract at ${assetPath}: ${(error as Error).message}`);
    }
  }
  let directory = __dirname;
  for (let depth = 0; depth < 8; depth += 1) {
    const candidate = path.join(directory, 'trainer', 'src', 'neural', 'protocol_contract.json');
    if (fs.existsSync(candidate)) {
      try {
        return validateContract(JSON.parse(fs.readFileSync(candidate, 'utf8')) as unknown);
      } catch (error) {
        if (error instanceof ProtocolContractError) throw error;
        throw new ProtocolContractError(`Unable to load shared protocol contract at ${candidate}: ${(error as Error).message}`);
      }
    }
    const parent = path.dirname(directory);
    if (parent === directory) break;
    directory = parent;
  }
  throw new ProtocolContractError('Shared trainer/src/neural/protocol_contract.json was not found.');
}

export const PROTOCOL_CONTRACT = loadProtocolContract();
export const SUPPORTED_RAW_COMMANDS = new Set(PROTOCOL_CONTRACT.supported_commands);
export const RECOGNIZED_UNSUPPORTED_RAW_COMMANDS = new Map(
  PROTOCOL_CONTRACT.recognized_unsupported_commands.map((entry) => [entry.token, entry]),
);

/** Checks the source-emitted Pokemon.toString() spelling without repairing it. */
export function isCanonicalPlayerIdent(value: unknown, activeRequired = false): value is string {
  if (typeof value !== 'string' || value !== value.trim() || value.includes('|')) return false;
  const rule = PROTOCOL_CONTRACT.validation_rules.player_ident;
  const separatorIndex = value.indexOf(rule.separator);
  if (separatorIndex < 0) return false;
  const prefix = value.slice(0, separatorIndex);
  const name = value.slice(separatorIndex + rule.separator.length);
  const side = prefix.slice(0, 2);
  const slot = prefix.slice(2);
  return rule.side_ids.includes(side) && rule.slots.includes(slot)
    && (!activeRequired || slot !== '') && name !== '' && name === name.trim();
}

export function isCanonicalSideOnlyPlayerIdent(value: unknown): value is string {
  const rule = PROTOCOL_CONTRACT.validation_rules.player_ident;
  return isCanonicalPlayerIdent(value)
    && rule.side_ids.some((side) => value.startsWith(side + rule.separator));
}
