# vNext Unmatched Action Audit — Tiny 10

- Before: 459 matched / 137 unmatched (77.0%)
- After safe fixes: 576 matched / 0 unmatched (100.0%)
- Initial-deployment non-decisions skipped: 20
- Legacy root causes: {'initial_deployment_nondecision': 20, 'move_missing_from_reconstructed_active_moves': 101, 'switch_target_missing_from_pre_action_legal_roster': 16}
- Remaining root causes: {}

No closest-candidate heuristic, guessed switch identity, or injected positive was used.

## Original Unmatched Groups

### `gen9randombattle-2589352228` turn 0 p1

- Raw: `|switch|p1a: Masquerain|Masquerain, L87, M|264/264`
- Parsed: `switch: Masquerain`
- Type: `team_preview_or_initial_deployment`
- Legacy reason: `initial_deployment_nondecision`
- Result: `intentionally_skipped_nondecision`
- Remaining reason: `skipped_nondecision`
- Legacy candidates: `[]`
- Pre-action candidates: `[]`

### `gen9randombattle-2589352228` turn 0 p2

- Raw: `|switch|p2a: Dugtrio|Dugtrio-Alola, L84, F|196/196`
- Parsed: `switch: Dugtrio-Alola`
- Type: `team_preview_or_initial_deployment`
- Legacy reason: `initial_deployment_nondecision`
- Result: `intentionally_skipped_nondecision`
- Remaining reason: `skipped_nondecision`
- Legacy candidates: `[]`
- Pre-action candidates: `[]`

### `gen9randombattle-2589352228` turn 1 p2

- Raw: `|move|p2a: Dugtrio|Stealth Rock|p1a: Masquerain`
- Parsed: `move: Stealth Rock`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Dugtrio', 'switch:switch: Azumarill', 'switch:switch: Ditto', 'switch:switch: Conkeldurr', 'switch:switch: Heracross']`
- Pre-action candidates: `['move:Stealth Rock', 'move_tera:Stealth Rock', 'switch:switch: Azumarill', 'switch:switch: Ditto', 'switch:switch: Conkeldurr', 'switch:switch: Heracross', 'switch:switch: Baxcalibur']`

### `gen9randombattle-2589352228` turn 14 p2

- Raw: `|switch|p2a: Baxcalibur|Baxcalibur, L75, F|295/295`
- Parsed: `switch: Baxcalibur`
- Type: `switch`
- Legacy reason: `switch_target_missing_from_pre_action_legal_roster`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['move:Hurricane', 'move:Zen Headbutt', 'switch:switch: Dugtrio-Alola']`
- Pre-action candidates: `['move:Hurricane', 'move:Zen Headbutt', 'switch:switch: Dugtrio-Alola', 'switch:switch: Baxcalibur']`

### `gen9randombattle-2589352228` turn 15 p2

- Raw: `|move|p2a: Baxcalibur|Icicle Crash|p1a: Hawlucha`
- Parsed: `move: Icicle Crash`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Dugtrio-Alola']`
- Pre-action candidates: `['move:Icicle Crash', 'switch:switch: Dugtrio-Alola']`

### `gen9randombattle-2592672685` turn 0 p1

- Raw: `|switch|p1a: Hippowdon|Hippowdon, L82, F|311/311`
- Parsed: `switch: Hippowdon`
- Type: `team_preview_or_initial_deployment`
- Legacy reason: `initial_deployment_nondecision`
- Result: `intentionally_skipped_nondecision`
- Remaining reason: `skipped_nondecision`
- Legacy candidates: `[]`
- Pre-action candidates: `[]`

### `gen9randombattle-2592672685` turn 0 p2

- Raw: `|switch|p2a: Diancie|Diancie, L82|216/216`
- Parsed: `switch: Diancie`
- Type: `team_preview_or_initial_deployment`
- Legacy reason: `initial_deployment_nondecision`
- Result: `intentionally_skipped_nondecision`
- Remaining reason: `skipped_nondecision`
- Legacy candidates: `[]`
- Pre-action candidates: `[]`

### `gen9randombattle-2593870030` turn 0 p1

- Raw: `|switch|p1a: Dusknoir|Dusknoir, L89, F|225/225`
- Parsed: `switch: Dusknoir`
- Type: `team_preview_or_initial_deployment`
- Legacy reason: `initial_deployment_nondecision`
- Result: `intentionally_skipped_nondecision`
- Remaining reason: `skipped_nondecision`
- Legacy candidates: `[]`
- Pre-action candidates: `[]`

### `gen9randombattle-2593870030` turn 0 p2

- Raw: `|switch|p2a: Typhlosion|Typhlosion-Hisui, L83, M|257/257`
- Parsed: `switch: Typhlosion-Hisui`
- Type: `team_preview_or_initial_deployment`
- Legacy reason: `initial_deployment_nondecision`
- Result: `intentionally_skipped_nondecision`
- Remaining reason: `skipped_nondecision`
- Legacy candidates: `[]`
- Pre-action candidates: `[]`

### `gen9randombattle-2593870030` turn 1 p2

- Raw: `|move|p2a: Typhlosion|Shadow Ball|p1a: Dusknoir`
- Parsed: `move_tera: Shadow Ball`
- Type: `move_tera`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Typhlosion', 'switch:switch: Polteageist-Antique', 'switch:switch: Meowscarada', 'switch:switch: Toxicroak', 'switch:switch: Arceus-Psychic']`
- Pre-action candidates: `['move:Shadow Ball', 'move_tera:Shadow Ball', 'switch:switch: Polteageist-Antique', 'switch:switch: Meowscarada', 'switch:switch: Toxicroak', 'switch:switch: Arceus-Psychic', 'switch:switch: Miraidon']`

### `gen9randombattle-2593870030` turn 4 p1

- Raw: `|move|p1a: Ninetales|Aurora Veil|p1a: Ninetales`
- Parsed: `move: Aurora Veil`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Dusknoir', 'switch:switch: Dragonite', 'switch:switch: Ninetales', 'switch:switch: Sceptile']`
- Pre-action candidates: `['move:Aurora Veil', 'move_tera:Aurora Veil', 'move:Blizzard', 'move_tera:Blizzard', 'move:Encore', 'move_tera:Encore', 'move:Moonblast', 'move_tera:Moonblast', 'switch:switch: Dusknoir', 'switch:switch: Dragonite', 'switch:switch: Sceptile', 'switch:switch: Ninetales']`

### `gen9randombattle-2593870030` turn 5 p1

- Raw: `|move|p1a: Ninetales|Blizzard|p2a: Meowscarada`
- Parsed: `move: Blizzard`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Dusknoir', 'switch:switch: Dragonite', 'switch:switch: Ninetales', 'switch:switch: Sceptile']`
- Pre-action candidates: `['move:Aurora Veil', 'move_tera:Aurora Veil', 'move:Blizzard', 'move_tera:Blizzard', 'move:Encore', 'move_tera:Encore', 'move:Moonblast', 'move_tera:Moonblast', 'switch:switch: Dusknoir', 'switch:switch: Dragonite', 'switch:switch: Sceptile', 'switch:switch: Ninetales']`

### `gen9randombattle-2593870030` turn 6 p1

- Raw: `|move|p1a: Ninetales|Moonblast|p2a: Meowscarada`
- Parsed: `move: Moonblast`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Dusknoir', 'switch:switch: Dragonite', 'switch:switch: Ninetales', 'switch:switch: Sceptile']`
- Pre-action candidates: `['move:Aurora Veil', 'move_tera:Aurora Veil', 'move:Blizzard', 'move_tera:Blizzard', 'move:Encore', 'move_tera:Encore', 'move:Moonblast', 'move_tera:Moonblast', 'switch:switch: Dusknoir', 'switch:switch: Dragonite', 'switch:switch: Sceptile', 'switch:switch: Ninetales']`

### `gen9randombattle-2593870030` turn 7 p1

- Raw: `|move|p1a: Ninetales|Moonblast|p2a: Toxicroak`
- Parsed: `move: Moonblast`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Dusknoir', 'switch:switch: Dragonite', 'switch:switch: Ninetales', 'switch:switch: Sceptile']`
- Pre-action candidates: `['move:Aurora Veil', 'move_tera:Aurora Veil', 'move:Blizzard', 'move_tera:Blizzard', 'move:Encore', 'move_tera:Encore', 'move:Moonblast', 'move_tera:Moonblast', 'switch:switch: Dusknoir', 'switch:switch: Dragonite', 'switch:switch: Sceptile', 'switch:switch: Ninetales']`

### `gen9randombattle-2593870030` turn 8 p1

- Raw: `|move|p1a: Ninetales|Encore|p2a: Toxicroak`
- Parsed: `move: Encore`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Dusknoir', 'switch:switch: Dragonite', 'switch:switch: Ninetales', 'switch:switch: Sceptile']`
- Pre-action candidates: `['move:Aurora Veil', 'move_tera:Aurora Veil', 'move:Blizzard', 'move_tera:Blizzard', 'move:Encore', 'move_tera:Encore', 'move:Moonblast', 'move_tera:Moonblast', 'switch:switch: Dusknoir', 'switch:switch: Dragonite', 'switch:switch: Sceptile', 'switch:switch: Ninetales']`

### `gen9randombattle-2593870030` turn 10 p2

- Raw: `|move|p2a: Arceus|Recover|p2a: Arceus`
- Parsed: `move: Recover`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Typhlosion-Hisui', 'switch:switch: Polteageist-Antique', 'switch:switch: Toxicroak']`
- Pre-action candidates: `['move:Cosmic Power', 'move:Recover', 'move:Stored Power', 'switch:switch: Typhlosion-Hisui', 'switch:switch: Polteageist-Antique', 'switch:switch: Toxicroak', 'switch:switch: Miraidon']`

### `gen9randombattle-2593870030` turn 11 p2

- Raw: `|move|p2a: Arceus|Stored Power|p1a: Sceptile`
- Parsed: `move: Stored Power`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Typhlosion-Hisui', 'switch:switch: Polteageist-Antique', 'switch:switch: Toxicroak']`
- Pre-action candidates: `['move:Cosmic Power', 'move:Recover', 'move:Stored Power', 'switch:switch: Typhlosion-Hisui', 'switch:switch: Polteageist-Antique', 'switch:switch: Toxicroak', 'switch:switch: Miraidon']`

### `gen9randombattle-2593870030` turn 12 p2

- Raw: `|move|p2a: Arceus|Recover|p2a: Arceus`
- Parsed: `move: Recover`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Typhlosion-Hisui', 'switch:switch: Polteageist-Antique', 'switch:switch: Toxicroak']`
- Pre-action candidates: `['move:Cosmic Power', 'move:Recover', 'move:Stored Power', 'switch:switch: Typhlosion-Hisui', 'switch:switch: Polteageist-Antique', 'switch:switch: Toxicroak', 'switch:switch: Miraidon']`

### `gen9randombattle-2593870030` turn 13 p2

- Raw: `|move|p2a: Arceus|Stored Power|p1a: Ninetales`
- Parsed: `move: Stored Power`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Typhlosion-Hisui', 'switch:switch: Polteageist-Antique', 'switch:switch: Toxicroak']`
- Pre-action candidates: `['move:Cosmic Power', 'move:Recover', 'move:Stored Power', 'switch:switch: Typhlosion-Hisui', 'switch:switch: Polteageist-Antique', 'switch:switch: Toxicroak', 'switch:switch: Miraidon']`

### `gen9randombattle-2593870030` turn 14 p1

- Raw: `|move|p1a: Ninetales|Aurora Veil|p1a: Ninetales`
- Parsed: `move: Aurora Veil`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Dusknoir', 'switch:switch: Dragonite', 'switch:switch: Ninetales', 'switch:switch: Sceptile']`
- Pre-action candidates: `['move:Aurora Veil', 'move_tera:Aurora Veil', 'move:Blizzard', 'move_tera:Blizzard', 'move:Encore', 'move_tera:Encore', 'move:Moonblast', 'move_tera:Moonblast', 'switch:switch: Dusknoir', 'switch:switch: Dragonite', 'switch:switch: Sceptile', 'switch:switch: Ninetales']`

### `gen9randombattle-2593870030` turn 14 p2

- Raw: `|move|p2a: Arceus|Cosmic Power|p2a: Arceus`
- Parsed: `move: Cosmic Power`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Typhlosion-Hisui', 'switch:switch: Polteageist-Antique', 'switch:switch: Toxicroak']`
- Pre-action candidates: `['move:Cosmic Power', 'move:Recover', 'move:Stored Power', 'switch:switch: Typhlosion-Hisui', 'switch:switch: Polteageist-Antique', 'switch:switch: Toxicroak', 'switch:switch: Miraidon']`

### `gen9randombattle-2593870030` turn 15 p1

- Raw: `|move|p1a: Ninetales|Blizzard|p2a: Arceus`
- Parsed: `move: Blizzard`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Dusknoir', 'switch:switch: Dragonite', 'switch:switch: Ninetales', 'switch:switch: Sceptile']`
- Pre-action candidates: `['move:Aurora Veil', 'move_tera:Aurora Veil', 'move:Blizzard', 'move_tera:Blizzard', 'move:Encore', 'move_tera:Encore', 'move:Moonblast', 'move_tera:Moonblast', 'switch:switch: Dusknoir', 'switch:switch: Dragonite', 'switch:switch: Sceptile', 'switch:switch: Ninetales']`

### `gen9randombattle-2593870030` turn 15 p2

- Raw: `|move|p2a: Arceus|Stored Power|p1a: Ninetales`
- Parsed: `move: Stored Power`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Typhlosion-Hisui', 'switch:switch: Polteageist-Antique', 'switch:switch: Toxicroak']`
- Pre-action candidates: `['move:Cosmic Power', 'move:Recover', 'move:Stored Power', 'switch:switch: Typhlosion-Hisui', 'switch:switch: Polteageist-Antique', 'switch:switch: Toxicroak', 'switch:switch: Miraidon']`

### `gen9randombattle-2593870030` turn 16 p1

- Raw: `|move|p1a: Ninetales|Blizzard|p2a: Polteageist`
- Parsed: `move: Blizzard`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Dusknoir', 'switch:switch: Dragonite', 'switch:switch: Ninetales', 'switch:switch: Sceptile']`
- Pre-action candidates: `['move:Aurora Veil', 'move_tera:Aurora Veil', 'move:Blizzard', 'move_tera:Blizzard', 'move:Encore', 'move_tera:Encore', 'move:Moonblast', 'move_tera:Moonblast', 'switch:switch: Dusknoir', 'switch:switch: Dragonite', 'switch:switch: Sceptile', 'switch:switch: Ninetales']`

### `gen9randombattle-2593870030` turn 17 p1

- Raw: `|move|p1a: Ninetales|Moonblast|p2a: Polteageist`
- Parsed: `move: Moonblast`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Dusknoir', 'switch:switch: Dragonite', 'switch:switch: Ninetales', 'switch:switch: Sceptile']`
- Pre-action candidates: `['move:Aurora Veil', 'move_tera:Aurora Veil', 'move:Blizzard', 'move_tera:Blizzard', 'move:Encore', 'move_tera:Encore', 'move:Moonblast', 'move_tera:Moonblast', 'switch:switch: Dusknoir', 'switch:switch: Dragonite', 'switch:switch: Sceptile', 'switch:switch: Ninetales']`

### `gen9randombattle-2593870030` turn 17 p2

- Raw: `|move|p2a: Polteageist|Shell Smash|p2a: Polteageist`
- Parsed: `move: Shell Smash`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Typhlosion-Hisui', 'switch:switch: Toxicroak', 'switch:switch: Arceus-Psychic']`
- Pre-action candidates: `['move:Shell Smash', 'switch:switch: Typhlosion-Hisui', 'switch:switch: Toxicroak', 'switch:switch: Arceus-Psychic', 'switch:switch: Miraidon']`

### `gen9randombattle-2593870030` turn 20 p2

- Raw: `|move|p2a: Arceus|Cosmic Power|p2a: Arceus`
- Parsed: `move: Cosmic Power`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Typhlosion-Hisui', 'switch:switch: Polteageist-Antique', 'switch:switch: Toxicroak']`
- Pre-action candidates: `['move:Cosmic Power', 'move:Recover', 'move:Stored Power', 'switch:switch: Typhlosion-Hisui', 'switch:switch: Polteageist-Antique', 'switch:switch: Toxicroak', 'switch:switch: Miraidon']`

### `gen9randombattle-2593870030` turn 21 p2

- Raw: `|move|p2a: Arceus|Cosmic Power|p2a: Arceus`
- Parsed: `move: Cosmic Power`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Typhlosion-Hisui', 'switch:switch: Polteageist-Antique', 'switch:switch: Toxicroak']`
- Pre-action candidates: `['move:Cosmic Power', 'move:Recover', 'move:Stored Power', 'switch:switch: Typhlosion-Hisui', 'switch:switch: Polteageist-Antique', 'switch:switch: Toxicroak', 'switch:switch: Miraidon']`

### `gen9randombattle-2593870030` turn 25 p2

- Raw: `|switch|p2a: Miraidon|Miraidon, L65|238/238`
- Parsed: `switch: Miraidon`
- Type: `switch`
- Legacy reason: `switch_target_missing_from_pre_action_legal_roster`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Typhlosion-Hisui', 'switch:switch: Arceus-Psychic']`
- Pre-action candidates: `['move:Shell Smash', 'switch:switch: Typhlosion-Hisui', 'switch:switch: Arceus-Psychic', 'switch:switch: Miraidon']`

### `gen9randombattle-2588074888` turn 0 p1

- Raw: `|switch|p1a: Ninetales|Ninetales, L85, M|263/263`
- Parsed: `switch: Ninetales`
- Type: `team_preview_or_initial_deployment`
- Legacy reason: `initial_deployment_nondecision`
- Result: `intentionally_skipped_nondecision`
- Remaining reason: `skipped_nondecision`
- Legacy candidates: `[]`
- Pre-action candidates: `[]`

### `gen9randombattle-2588074888` turn 0 p2

- Raw: `|switch|p2a: Quagsire|Quagsire, L84, F|297/297`
- Parsed: `switch: Quagsire`
- Type: `team_preview_or_initial_deployment`
- Legacy reason: `initial_deployment_nondecision`
- Result: `intentionally_skipped_nondecision`
- Remaining reason: `skipped_nondecision`
- Legacy candidates: `[]`
- Pre-action candidates: `[]`

### `gen9randombattle-2588074888` turn 7 p1

- Raw: `|move|p1a: Vivillon|Quiver Dance|p1a: Vivillon`
- Parsed: `move: Quiver Dance`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Ninetales', 'switch:switch: Vivillon']`
- Pre-action candidates: `['move:Hurricane', 'move_tera:Hurricane', 'move:Quiver Dance', 'move_tera:Quiver Dance', 'switch:switch: Ninetales', 'switch:switch: Uxie']`

### `gen9randombattle-2588074888` turn 8 p1

- Raw: `|move|p1a: Vivillon|Hurricane|p2a: Charizard`
- Parsed: `move: Hurricane`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Ninetales', 'switch:switch: Vivillon']`
- Pre-action candidates: `['move:Hurricane', 'move_tera:Hurricane', 'move:Quiver Dance', 'move_tera:Quiver Dance', 'switch:switch: Ninetales', 'switch:switch: Uxie']`

### `gen9randombattle-2588074888` turn 9 p1

- Raw: `|move|p1a: Vivillon|Hurricane|p2a: Ogerpon`
- Parsed: `move: Hurricane`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Ninetales', 'switch:switch: Vivillon']`
- Pre-action candidates: `['move:Hurricane', 'move_tera:Hurricane', 'move:Quiver Dance', 'move_tera:Quiver Dance', 'switch:switch: Ninetales', 'switch:switch: Uxie']`

### `gen9randombattle-2588074888` turn 9 p2

- Raw: `|move|p2a: Ogerpon|Ivy Cudgel|p1a: Vivillon|[anim] Ivy Cudgel Fire`
- Parsed: `move_tera: Ivy Cudgel`
- Type: `move_tera`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Ogerpon', 'switch:switch: Gengar', 'switch:switch: Espathra']`
- Pre-action candidates: `['move:Ivy Cudgel', 'move_tera:Ivy Cudgel', 'move:Knock Off', 'move_tera:Knock Off', 'switch:switch: Gengar', 'switch:switch: Espathra', 'switch:switch: Necrozma']`

### `gen9randombattle-2588074888` turn 10 p2

- Raw: `|move|p2a: Ogerpon|Knock Off|p1a: Ninetales`
- Parsed: `move: Knock Off`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Ogerpon', 'switch:switch: Gengar', 'switch:switch: Espathra']`
- Pre-action candidates: `['move:Ivy Cudgel', 'move:Knock Off', 'switch:switch: Gengar', 'switch:switch: Espathra', 'switch:switch: Necrozma']`

### `gen9randombattle-2588074888` turn 12 p1

- Raw: `|switch|p1a: Uxie|Uxie, L83|260/260`
- Parsed: `switch: Uxie`
- Type: `switch`
- Legacy reason: `switch_target_missing_from_pre_action_legal_roster`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['move:Nasty Plot', 'move_tera:Nasty Plot', 'move:Scorching Sands', 'move_tera:Scorching Sands', 'move:Solar Beam', 'move_tera:Solar Beam', 'switch:switch: Vivillon-Jungle']`
- Pre-action candidates: `['move:Nasty Plot', 'move_tera:Nasty Plot', 'move:Scorching Sands', 'move_tera:Scorching Sands', 'move:Solar Beam', 'move_tera:Solar Beam', 'switch:switch: Vivillon-Jungle', 'switch:switch: Uxie']`

### `gen9randombattle-2588074888` turn 13 p1

- Raw: `|move|p1a: Uxie|Knock Off|p2a: Gengar`
- Parsed: `move_tera: Knock Off`
- Type: `move_tera`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Vivillon-Jungle']`
- Pre-action candidates: `['move:Encore', 'move_tera:Encore', 'move:Knock Off', 'move_tera:Knock Off', 'move:Psychic Noise', 'move_tera:Psychic Noise', 'move:Stealth Rock', 'move_tera:Stealth Rock', 'switch:switch: Vivillon-Jungle']`

### `gen9randombattle-2588074888` turn 14 p1

- Raw: `|move|p1a: Uxie|Knock Off|p2a: Gengar`
- Parsed: `move: Knock Off`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Vivillon-Jungle']`
- Pre-action candidates: `['move:Encore', 'move:Knock Off', 'move:Psychic Noise', 'move:Stealth Rock', 'switch:switch: Vivillon-Jungle']`

### `gen9randombattle-2588074888` turn 15 p1

- Raw: `|move|p1a: Uxie|Psychic Noise|p2a: Espathra`
- Parsed: `move: Psychic Noise`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Vivillon-Jungle']`
- Pre-action candidates: `['move:Encore', 'move:Knock Off', 'move:Psychic Noise', 'move:Stealth Rock', 'switch:switch: Vivillon-Jungle']`

### `gen9randombattle-2588074888` turn 16 p1

- Raw: `|move|p1a: Uxie|Encore|p2a: Espathra`
- Parsed: `move: Encore`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Vivillon-Jungle']`
- Pre-action candidates: `['move:Encore', 'move:Knock Off', 'move:Psychic Noise', 'move:Stealth Rock', 'switch:switch: Vivillon-Jungle']`

### `gen9randombattle-2588074888` turn 17 p2

- Raw: `|switch|p2a: Necrozma|Necrozma, L80|286/286`
- Parsed: `switch: Necrozma`
- Type: `switch`
- Legacy reason: `switch_target_missing_from_pre_action_legal_roster`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['move:Calm Mind', 'move:Stored Power', 'switch:switch: Ogerpon-Hearthflame']`
- Pre-action candidates: `['move:Calm Mind', 'move:Stored Power', 'switch:switch: Ogerpon-Hearthflame', 'switch:switch: Necrozma']`

### `gen9randombattle-2588074888` turn 17 p1

- Raw: `|move|p1a: Uxie|Stealth Rock|p2a: Necrozma`
- Parsed: `move: Stealth Rock`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Vivillon-Jungle']`
- Pre-action candidates: `['move:Encore', 'move:Knock Off', 'move:Psychic Noise', 'move:Stealth Rock', 'switch:switch: Vivillon-Jungle']`

### `gen9randombattle-2588074888` turn 18 p1

- Raw: `|move|p1a: Uxie|Knock Off|p2a: Necrozma`
- Parsed: `move: Knock Off`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Vivillon-Jungle']`
- Pre-action candidates: `['move:Encore', 'move:Knock Off', 'move:Psychic Noise', 'move:Stealth Rock', 'switch:switch: Vivillon-Jungle']`

### `gen9randombattle-2588074888` turn 18 p2

- Raw: `|move|p2a: Necrozma|Earth Power|p1a: Uxie`
- Parsed: `move: Earth Power`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Ogerpon-Hearthflame', 'switch:switch: Espathra']`
- Pre-action candidates: `['move:Earth Power', 'move:Photon Geyser', 'switch:switch: Ogerpon-Hearthflame', 'switch:switch: Espathra']`

### `gen9randombattle-2588074888` turn 19 p1

- Raw: `|move|p1a: Uxie|Encore|p2a: Necrozma`
- Parsed: `move: Encore`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Vivillon-Jungle']`
- Pre-action candidates: `['move:Encore', 'move:Knock Off', 'move:Psychic Noise', 'move:Stealth Rock', 'switch:switch: Vivillon-Jungle']`

### `gen9randombattle-2588074888` turn 19 p2

- Raw: `|move|p2a: Necrozma|Earth Power|p1a: Uxie`
- Parsed: `move: Earth Power`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Ogerpon-Hearthflame', 'switch:switch: Espathra']`
- Pre-action candidates: `['move:Earth Power', 'move:Photon Geyser', 'switch:switch: Ogerpon-Hearthflame', 'switch:switch: Espathra']`

### `gen9randombattle-2588074888` turn 20 p1

- Raw: `|move|p1a: Uxie|Knock Off|p2a: Espathra`
- Parsed: `move: Knock Off`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Vivillon-Jungle']`
- Pre-action candidates: `['move:Encore', 'move:Knock Off', 'move:Psychic Noise', 'move:Stealth Rock', 'switch:switch: Vivillon-Jungle']`

### `gen9randombattle-2588074888` turn 21 p1

- Raw: `|move|p1a: Uxie|Knock Off|p2a: Espathra`
- Parsed: `move: Knock Off`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Vivillon-Jungle']`
- Pre-action candidates: `['move:Encore', 'move:Knock Off', 'move:Psychic Noise', 'move:Stealth Rock', 'switch:switch: Vivillon-Jungle']`

### `gen9randombattle-2588074888` turn 21 p2

- Raw: `|switch|p2a: Necrozma|Necrozma, L80|201/286`
- Parsed: `switch: Necrozma`
- Type: `switch`
- Legacy reason: `switch_target_missing_from_pre_action_legal_roster`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['move:Calm Mind', 'move:Stored Power', 'switch:switch: Ogerpon-Hearthflame']`
- Pre-action candidates: `['move:Calm Mind', 'move:Stored Power', 'switch:switch: Ogerpon-Hearthflame', 'switch:switch: Necrozma']`

### `gen9randombattle-2588074888` turn 22 p1

- Raw: `|move|p1a: Uxie|Knock Off|p2a: Necrozma`
- Parsed: `move: Knock Off`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Vivillon-Jungle']`
- Pre-action candidates: `['move:Encore', 'move:Knock Off', 'move:Psychic Noise', 'move:Stealth Rock', 'switch:switch: Vivillon-Jungle']`

### `gen9randombattle-2588074888` turn 22 p2

- Raw: `|move|p2a: Necrozma|Photon Geyser|p1a: Uxie`
- Parsed: `move: Photon Geyser`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Ogerpon-Hearthflame']`
- Pre-action candidates: `['move:Earth Power', 'move:Photon Geyser', 'switch:switch: Ogerpon-Hearthflame']`

### `gen9randombattle-2588074888` turn 23 p1

- Raw: `|move|p1a: Uxie|Knock Off|p2a: Necrozma`
- Parsed: `move: Knock Off`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Vivillon-Jungle']`
- Pre-action candidates: `['move:Encore', 'move:Knock Off', 'move:Psychic Noise', 'move:Stealth Rock', 'switch:switch: Vivillon-Jungle']`

### `gen9randombattle-2588074888` turn 23 p2

- Raw: `|move|p2a: Necrozma|Photon Geyser|p1a: Uxie`
- Parsed: `move: Photon Geyser`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Ogerpon-Hearthflame']`
- Pre-action candidates: `['move:Earth Power', 'move:Photon Geyser', 'switch:switch: Ogerpon-Hearthflame']`

### `gen9randombattle-2588074888` turn 24 p1

- Raw: `|move|p1a: Uxie|Knock Off|p2a: Necrozma`
- Parsed: `move: Knock Off`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Vivillon-Jungle']`
- Pre-action candidates: `['move:Encore', 'move:Knock Off', 'move:Psychic Noise', 'move:Stealth Rock', 'switch:switch: Vivillon-Jungle']`

### `gen9randombattle-2588414109` turn 0 p1

- Raw: `|switch|p1a: Vivillon|Vivillon-Archipelago, L83, M|268/268`
- Parsed: `switch: Vivillon-Archipelago`
- Type: `team_preview_or_initial_deployment`
- Legacy reason: `initial_deployment_nondecision`
- Result: `intentionally_skipped_nondecision`
- Remaining reason: `skipped_nondecision`
- Legacy candidates: `[]`
- Pre-action candidates: `[]`

### `gen9randombattle-2588414109` turn 0 p2

- Raw: `|switch|p2a: Qwilfish|Qwilfish, L86, M|252/252`
- Parsed: `switch: Qwilfish`
- Type: `team_preview_or_initial_deployment`
- Legacy reason: `initial_deployment_nondecision`
- Result: `intentionally_skipped_nondecision`
- Remaining reason: `skipped_nondecision`
- Legacy candidates: `[]`
- Pre-action candidates: `[]`

### `gen9randombattle-2588414109` turn 8 p2

- Raw: `|move|p2a: Polteageist|Shell Smash|p2a: Polteageist`
- Parsed: `move: Shell Smash`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Qwilfish', 'switch:switch: Inteleon', 'switch:switch: Polteageist', 'switch:switch: Breloom', 'switch:switch: Bisharp']`
- Pre-action candidates: `['move:Shadow Ball', 'move_tera:Shadow Ball', 'move:Shell Smash', 'move_tera:Shell Smash', 'move:Stored Power', 'move_tera:Stored Power', 'switch:switch: Qwilfish', 'switch:switch: Inteleon', 'switch:switch: Breloom', 'switch:switch: Bisharp', 'switch:switch: Ditto']`

### `gen9randombattle-2588414109` turn 9 p2

- Raw: `|move|p2a: Polteageist|Shadow Ball|p1a: Torkoal`
- Parsed: `move: Shadow Ball`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Qwilfish', 'switch:switch: Inteleon', 'switch:switch: Polteageist', 'switch:switch: Breloom', 'switch:switch: Bisharp']`
- Pre-action candidates: `['move:Shadow Ball', 'move_tera:Shadow Ball', 'move:Shell Smash', 'move_tera:Shell Smash', 'move:Stored Power', 'move_tera:Stored Power', 'switch:switch: Qwilfish', 'switch:switch: Inteleon', 'switch:switch: Breloom', 'switch:switch: Bisharp', 'switch:switch: Ditto']`

### `gen9randombattle-2588414109` turn 10 p2

- Raw: `|move|p2a: Polteageist|Stored Power|p1a: Toedscruel`
- Parsed: `move: Stored Power`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Qwilfish', 'switch:switch: Inteleon', 'switch:switch: Polteageist', 'switch:switch: Breloom', 'switch:switch: Bisharp']`
- Pre-action candidates: `['move:Shadow Ball', 'move_tera:Shadow Ball', 'move:Shell Smash', 'move_tera:Shell Smash', 'move:Stored Power', 'move_tera:Stored Power', 'switch:switch: Qwilfish', 'switch:switch: Inteleon', 'switch:switch: Breloom', 'switch:switch: Bisharp', 'switch:switch: Ditto']`

### `gen9randombattle-2588414109` turn 25 p2

- Raw: `|switch|p2a: Ditto|Ditto, L87|225/225`
- Parsed: `switch: Ditto`
- Type: `switch`
- Legacy reason: `switch_target_missing_from_pre_action_legal_roster`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['move:Gunk Shot', 'move:Thunder Wave', 'switch:switch: Inteleon', 'switch:switch: Polteageist-Antique', 'switch:switch: Bisharp']`
- Pre-action candidates: `['move:Gunk Shot', 'move:Thunder Wave', 'switch:switch: Inteleon', 'switch:switch: Polteageist-Antique', 'switch:switch: Bisharp', 'switch:switch: Ditto']`

### `gen9randombattle-2588414109` turn 26 p2

- Raw: `|move|p2a: Ditto|Psychic|p1a: Gothitelle`
- Parsed: `move: Psychic`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Inteleon', 'switch:switch: Polteageist-Antique', 'switch:switch: Bisharp']`
- Pre-action candidates: `['move:Hurricane', 'move:Psychic', 'switch:switch: Inteleon', 'switch:switch: Polteageist-Antique', 'switch:switch: Bisharp']`

### `gen9randombattle-2588414109` turn 27 p2

- Raw: `|move|p2a: Ditto|Psychic|p1a: Vivillon`
- Parsed: `move: Psychic`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Inteleon', 'switch:switch: Polteageist-Antique', 'switch:switch: Bisharp']`
- Pre-action candidates: `['move:Hurricane', 'move:Psychic', 'switch:switch: Inteleon', 'switch:switch: Polteageist-Antique', 'switch:switch: Bisharp']`

### `gen9randombattle-2588414109` turn 27 p1

- Raw: `|move|p1a: Vivillon|Quiver Dance|p1a: Vivillon`
- Parsed: `move: Quiver Dance`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Vivillon']`
- Pre-action candidates: `['move:Hurricane', 'move:Quiver Dance', 'move:Sleep Powder', 'move:Tera Blast', 'switch:switch: Calyrex-Shadow']`

### `gen9randombattle-2588414109` turn 28 p1

- Raw: `|move|p1a: Vivillon|Hurricane|p2a: Bisharp`
- Parsed: `move: Hurricane`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Vivillon']`
- Pre-action candidates: `['move:Hurricane', 'move:Quiver Dance', 'move:Sleep Powder', 'move:Tera Blast', 'switch:switch: Calyrex-Shadow']`

### `gen9randombattle-2588414109` turn 29 p1

- Raw: `|move|p1a: Vivillon|Sleep Powder|p2a: Inteleon`
- Parsed: `move: Sleep Powder`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Vivillon']`
- Pre-action candidates: `['move:Hurricane', 'move:Quiver Dance', 'move:Sleep Powder', 'move:Tera Blast', 'switch:switch: Calyrex-Shadow']`

### `gen9randombattle-2588414109` turn 30 p1

- Raw: `|move|p1a: Vivillon|Hurricane|p2a: Inteleon`
- Parsed: `move: Hurricane`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Vivillon']`
- Pre-action candidates: `['move:Hurricane', 'move:Quiver Dance', 'move:Sleep Powder', 'move:Tera Blast', 'switch:switch: Calyrex-Shadow']`

### `gen9randombattle-2588414109` turn 31 p1

- Raw: `|move|p1a: Vivillon|Tera Blast|p2a: Inteleon`
- Parsed: `move: Tera Blast`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Vivillon']`
- Pre-action candidates: `['move:Hurricane', 'move:Quiver Dance', 'move:Sleep Powder', 'move:Tera Blast', 'switch:switch: Calyrex-Shadow']`

### `gen9randombattle-2588414109` turn 31 p2

- Raw: `|switch|p2a: Ditto|Ditto, L87|121/225`
- Parsed: `switch: Ditto`
- Type: `switch`
- Legacy reason: `switch_target_missing_from_pre_action_legal_roster`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['move:U-turn', 'switch:switch: Polteageist-Antique']`
- Pre-action candidates: `['move:U-turn', 'switch:switch: Polteageist-Antique', 'switch:switch: Ditto']`

### `gen9randombattle-2588414109` turn 32 p2

- Raw: `|move|p2a: Ditto|Hurricane|p1a: Vivillon`
- Parsed: `move: Hurricane`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Polteageist-Antique']`
- Pre-action candidates: `['move:Hurricane', 'move:Psychic', 'switch:switch: Polteageist-Antique']`

### `gen9randombattle-2588414109` turn 32 p1

- Raw: `|switch|p1a: Calyrex|Calyrex-Shadow, L64|235/235`
- Parsed: `switch: Calyrex-Shadow`
- Type: `switch`
- Legacy reason: `switch_target_missing_from_pre_action_legal_roster`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Vivillon']`
- Pre-action candidates: `['move:Hurricane', 'move:Quiver Dance', 'move:Sleep Powder', 'move:Tera Blast', 'switch:switch: Calyrex-Shadow']`

### `gen9randombattle-2588414109` turn 33 p2

- Raw: `|move|p2a: Ditto|Hurricane|p1a: Calyrex`
- Parsed: `move: Hurricane`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Polteageist-Antique']`
- Pre-action candidates: `['move:Hurricane', 'move:Psychic', 'switch:switch: Polteageist-Antique']`

### `gen9randombattle-2592203110` turn 0 p1

- Raw: `|switch|p1a: Uxie|Uxie, L83|260/260`
- Parsed: `switch: Uxie`
- Type: `team_preview_or_initial_deployment`
- Legacy reason: `initial_deployment_nondecision`
- Result: `intentionally_skipped_nondecision`
- Remaining reason: `skipped_nondecision`
- Legacy candidates: `[]`
- Pre-action candidates: `[]`

### `gen9randombattle-2592203110` turn 0 p2

- Raw: `|switch|p2a: Azelf|Azelf, L82|257/257`
- Parsed: `switch: Azelf`
- Type: `team_preview_or_initial_deployment`
- Legacy reason: `initial_deployment_nondecision`
- Result: `intentionally_skipped_nondecision`
- Remaining reason: `skipped_nondecision`
- Legacy candidates: `[]`
- Pre-action candidates: `[]`

### `gen9randombattle-2592203110` turn 18 p1

- Raw: `|move|p1a: Indeedee|Dazzling Gleam|p2a: Samurott`
- Parsed: `move: Dazzling Gleam`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `[]`
- Pre-action candidates: `['move:Dazzling Gleam', 'move_tera:Dazzling Gleam', 'move:Psychic', 'move_tera:Psychic']`

### `gen9randombattle-2592203110` turn 19 p2

- Raw: `|move|p2a: Arceus|Cosmic Power|p2a: Arceus`
- Parsed: `move: Cosmic Power`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Arceus']`
- Pre-action candidates: `['move:Cosmic Power', 'switch:switch: Eternatus']`

### `gen9randombattle-2592203110` turn 19 p1

- Raw: `|move|p1a: Indeedee|Psychic|p2a: Arceus`
- Parsed: `move_tera: Psychic`
- Type: `move_tera`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `[]`
- Pre-action candidates: `['move:Dazzling Gleam', 'move_tera:Dazzling Gleam', 'move:Psychic', 'move_tera:Psychic']`

### `gen9randombattle-2592203110` turn 19 p2

- Raw: `|switch|p2a: Eternatus|Eternatus, L69|308/308`
- Parsed: `switch: Eternatus`
- Type: `switch`
- Legacy reason: `switch_target_missing_from_pre_action_legal_roster`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Arceus']`
- Pre-action candidates: `['move:Cosmic Power', 'switch:switch: Eternatus']`

### `gen9randombattle-2592203110` turn 20 p2

- Raw: `|move|p2a: Eternatus|Meteor Beam||[still]`
- Parsed: `move: Meteor Beam`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Arceus-Fighting']`
- Pre-action candidates: `['move:Meteor Beam', 'switch:switch: Arceus-Fighting']`

### `gen9randombattle-2592203110` turn 20 p1

- Raw: `|move|p1a: Indeedee|Psychic|p2a: Eternatus`
- Parsed: `move: Psychic`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `[]`
- Pre-action candidates: `['move:Dazzling Gleam', 'move:Psychic']`

### `gen9randombattle-2592477403` turn 0 p1

- Raw: `|switch|p1a: Indeedee|Indeedee-F, L90, F|272/272`
- Parsed: `switch: Indeedee-F`
- Type: `team_preview_or_initial_deployment`
- Legacy reason: `initial_deployment_nondecision`
- Result: `intentionally_skipped_nondecision`
- Remaining reason: `skipped_nondecision`
- Legacy candidates: `[]`
- Pre-action candidates: `[]`

### `gen9randombattle-2592477403` turn 0 p2

- Raw: `|switch|p2a: Pachirisu|Pachirisu, L96, M|271/271`
- Parsed: `switch: Pachirisu`
- Type: `team_preview_or_initial_deployment`
- Legacy reason: `initial_deployment_nondecision`
- Result: `intentionally_skipped_nondecision`
- Remaining reason: `skipped_nondecision`
- Legacy candidates: `[]`
- Pre-action candidates: `[]`

### `gen9randombattle-2592477403` turn 1 p1

- Raw: `|move|p1a: Indeedee|Psychic|p2a: Meowscarada`
- Parsed: `move: Psychic`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Indeedee', 'switch:switch: Shaymin', 'switch:switch: Malamar', 'switch:switch: Iron Treads', 'switch:switch: Houndoom']`
- Pre-action candidates: `['move:Psychic', 'move_tera:Psychic', 'switch:switch: Shaymin', 'switch:switch: Malamar', 'switch:switch: Iron Treads', 'switch:switch: Houndoom', 'switch:switch: Eternatus']`

### `gen9randombattle-2592477403` turn 9 p2

- Raw: `|move|p2a: Dudunsparce|Boomburst|p1a: Malamar`
- Parsed: `move_tera: Boomburst`
- Type: `move_tera`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Pachirisu', 'switch:switch: Dudunsparce', 'switch:switch: Deoxys-Defense', 'switch:switch: Deoxys']`
- Pre-action candidates: `['move:Boomburst', 'move_tera:Boomburst', 'switch:switch: Pachirisu', 'switch:switch: Deoxys-Defense', 'switch:switch: Kingdra', 'switch:switch: Vigoroth']`

### `gen9randombattle-2592477403` turn 10 p2

- Raw: `|move|p2a: Dudunsparce|Boomburst|p1a: Malamar`
- Parsed: `move: Boomburst`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Pachirisu', 'switch:switch: Dudunsparce', 'switch:switch: Deoxys-Defense', 'switch:switch: Deoxys']`
- Pre-action candidates: `['move:Boomburst', 'switch:switch: Pachirisu', 'switch:switch: Deoxys-Defense', 'switch:switch: Kingdra', 'switch:switch: Vigoroth']`

### `gen9randombattle-2592477403` turn 16 p2

- Raw: `|move|p2a: Deoxys|Stealth Rock|p1a: Houndoom`
- Parsed: `move: Stealth Rock`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Pachirisu', 'switch:switch: Dudunsparce-Three-Segment', 'switch:switch: Dudunsparce', 'switch:switch: Deoxys']`
- Pre-action candidates: `['move:Psychic Noise', 'move:Stealth Rock', 'switch:switch: Pachirisu', 'switch:switch: Dudunsparce-Three-Segment', 'switch:switch: Kingdra', 'switch:switch: Vigoroth']`

### `gen9randombattle-2592477403` turn 17 p2

- Raw: `|switch|p2a: Kingdra|Kingdra, L84, F|263/263`
- Parsed: `switch: Kingdra`
- Type: `switch`
- Legacy reason: `switch_target_missing_from_pre_action_legal_roster`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Pachirisu', 'switch:switch: Dudunsparce-Three-Segment', 'switch:switch: Dudunsparce', 'switch:switch: Deoxys']`
- Pre-action candidates: `['move:Discharge', 'move:Encore', 'move:Super Fang', 'move:U-turn', 'switch:switch: Dudunsparce-Three-Segment', 'switch:switch: Deoxys-Defense', 'switch:switch: Kingdra', 'switch:switch: Vigoroth']`

### `gen9randombattle-2592477403` turn 18 p2

- Raw: `|move|p2a: Kingdra|Rain Dance|p2a: Kingdra`
- Parsed: `move: Rain Dance`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Dudunsparce-Three-Segment', 'switch:switch: Dudunsparce', 'switch:switch: Deoxys-Defense', 'switch:switch: Deoxys']`
- Pre-action candidates: `['move:Rain Dance', 'move:Wave Crash', 'switch:switch: Dudunsparce-Three-Segment', 'switch:switch: Deoxys-Defense', 'switch:switch: Vigoroth']`

### `gen9randombattle-2592477403` turn 19 p2

- Raw: `|move|p2a: Kingdra|Wave Crash|p1a: Houndoom`
- Parsed: `move: Wave Crash`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Dudunsparce-Three-Segment', 'switch:switch: Dudunsparce', 'switch:switch: Deoxys-Defense', 'switch:switch: Deoxys']`
- Pre-action candidates: `['move:Rain Dance', 'move:Wave Crash', 'switch:switch: Dudunsparce-Three-Segment', 'switch:switch: Deoxys-Defense', 'switch:switch: Vigoroth']`

### `gen9randombattle-2592477403` turn 19 p2

- Raw: `|switch|p2a: Vigoroth|Vigoroth, L85, F|275/275`
- Parsed: `switch: Vigoroth`
- Type: `switch`
- Legacy reason: `switch_target_missing_from_pre_action_legal_roster`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Dudunsparce-Three-Segment', 'switch:switch: Dudunsparce', 'switch:switch: Deoxys-Defense', 'switch:switch: Deoxys']`
- Pre-action candidates: `['move:Rain Dance', 'move:Wave Crash', 'switch:switch: Dudunsparce-Three-Segment', 'switch:switch: Deoxys-Defense', 'switch:switch: Vigoroth']`

### `gen9randombattle-2592477403` turn 20 p2

- Raw: `|move|p2a: Vigoroth|Bulk Up|p2a: Vigoroth`
- Parsed: `move: Bulk Up`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Dudunsparce-Three-Segment', 'switch:switch: Dudunsparce', 'switch:switch: Deoxys-Defense', 'switch:switch: Deoxys']`
- Pre-action candidates: `['move:Bulk Up', 'move:Knock Off', 'move:Slack Off', 'switch:switch: Dudunsparce-Three-Segment', 'switch:switch: Deoxys-Defense']`

### `gen9randombattle-2592477403` turn 21 p1

- Raw: `|switch|p1a: Eternatus|Eternatus, L69|308/308`
- Parsed: `switch: Eternatus`
- Type: `switch`
- Legacy reason: `switch_target_missing_from_pre_action_legal_roster`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['move:Earthquake', 'move:Iron Head', 'move:Rapid Spin', 'move:Stealth Rock', 'switch:switch: Indeedee-F']`
- Pre-action candidates: `['move:Earthquake', 'move:Iron Head', 'move:Rapid Spin', 'move:Stealth Rock', 'switch:switch: Indeedee-F', 'switch:switch: Eternatus']`

### `gen9randombattle-2592477403` turn 21 p2

- Raw: `|move|p2a: Vigoroth|Bulk Up|p2a: Vigoroth`
- Parsed: `move: Bulk Up`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Dudunsparce-Three-Segment', 'switch:switch: Dudunsparce', 'switch:switch: Deoxys-Defense', 'switch:switch: Deoxys']`
- Pre-action candidates: `['move:Bulk Up', 'move:Knock Off', 'move:Slack Off', 'switch:switch: Dudunsparce-Three-Segment', 'switch:switch: Deoxys-Defense']`

### `gen9randombattle-2592477403` turn 22 p1

- Raw: `|move|p1a: Eternatus|Meteor Beam||[still]`
- Parsed: `move: Meteor Beam`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Indeedee-F', 'switch:switch: Iron Treads']`
- Pre-action candidates: `['move:Dynamax Cannon', 'move:Meteor Beam', 'move:Sludge Bomb', 'switch:switch: Indeedee-F', 'switch:switch: Iron Treads']`

### `gen9randombattle-2592477403` turn 22 p2

- Raw: `|move|p2a: Vigoroth|Slack Off|p2a: Vigoroth`
- Parsed: `move: Slack Off`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Dudunsparce-Three-Segment', 'switch:switch: Dudunsparce', 'switch:switch: Deoxys-Defense', 'switch:switch: Deoxys']`
- Pre-action candidates: `['move:Bulk Up', 'move:Knock Off', 'move:Slack Off', 'switch:switch: Dudunsparce-Three-Segment', 'switch:switch: Deoxys-Defense']`

### `gen9randombattle-2592477403` turn 23 p1

- Raw: `|move|p1a: Eternatus|Dynamax Cannon|p2a: Vigoroth`
- Parsed: `move: Dynamax Cannon`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Indeedee-F', 'switch:switch: Iron Treads']`
- Pre-action candidates: `['move:Dynamax Cannon', 'move:Meteor Beam', 'move:Sludge Bomb', 'switch:switch: Indeedee-F', 'switch:switch: Iron Treads']`

### `gen9randombattle-2592477403` turn 23 p2

- Raw: `|move|p2a: Vigoroth|Knock Off|p1a: Eternatus`
- Parsed: `move: Knock Off`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Dudunsparce-Three-Segment', 'switch:switch: Dudunsparce', 'switch:switch: Deoxys-Defense', 'switch:switch: Deoxys']`
- Pre-action candidates: `['move:Bulk Up', 'move:Knock Off', 'move:Slack Off', 'switch:switch: Dudunsparce-Three-Segment', 'switch:switch: Deoxys-Defense']`

### `gen9randombattle-2592477403` turn 24 p1

- Raw: `|move|p1a: Eternatus|Sludge Bomb|p2a: Dudunsparce`
- Parsed: `move: Sludge Bomb`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Indeedee-F', 'switch:switch: Iron Treads']`
- Pre-action candidates: `['move:Dynamax Cannon', 'move:Meteor Beam', 'move:Sludge Bomb', 'switch:switch: Indeedee-F', 'switch:switch: Iron Treads']`

### `gen9randombattle-2592477403` turn 25 p1

- Raw: `|move|p1a: Eternatus|Dynamax Cannon|p2a: Deoxys`
- Parsed: `move: Dynamax Cannon`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Indeedee-F', 'switch:switch: Iron Treads']`
- Pre-action candidates: `['move:Dynamax Cannon', 'move:Meteor Beam', 'move:Sludge Bomb', 'switch:switch: Indeedee-F', 'switch:switch: Iron Treads']`

### `gen9randombattle-2592477403` turn 25 p2

- Raw: `|move|p2a: Deoxys|Psychic Noise|p1a: Eternatus`
- Parsed: `move: Psychic Noise`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Dudunsparce-Three-Segment', 'switch:switch: Deoxys']`
- Pre-action candidates: `['move:Psychic Noise', 'move:Stealth Rock', 'switch:switch: Dudunsparce-Three-Segment', 'switch:switch: Vigoroth']`

### `gen9randombattle-2592477403` turn 26 p1

- Raw: `|move|p1a: Eternatus|Dynamax Cannon|p2a: Deoxys`
- Parsed: `move: Dynamax Cannon`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Indeedee-F', 'switch:switch: Iron Treads']`
- Pre-action candidates: `['move:Dynamax Cannon', 'move:Meteor Beam', 'move:Sludge Bomb', 'switch:switch: Indeedee-F', 'switch:switch: Iron Treads']`

### `gen9randombattle-2592477403` turn 26 p2

- Raw: `|switch|p2a: Vigoroth|Vigoroth, L85, F|72/275`
- Parsed: `switch: Vigoroth`
- Type: `switch`
- Legacy reason: `switch_target_missing_from_pre_action_legal_roster`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Dudunsparce-Three-Segment', 'switch:switch: Deoxys']`
- Pre-action candidates: `['move:Psychic Noise', 'move:Stealth Rock', 'switch:switch: Dudunsparce-Three-Segment', 'switch:switch: Vigoroth']`

### `gen9randombattle-2592477403` turn 27 p1

- Raw: `|move|p1a: Eternatus|Dynamax Cannon|p2a: Vigoroth`
- Parsed: `move: Dynamax Cannon`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Indeedee-F', 'switch:switch: Iron Treads']`
- Pre-action candidates: `['move:Dynamax Cannon', 'move:Meteor Beam', 'move:Sludge Bomb', 'switch:switch: Indeedee-F', 'switch:switch: Iron Treads']`

### `gen9randombattle-2588641014` turn 0 p1

- Raw: `|switch|p1a: Registeel|Registeel, L81|262/262`
- Parsed: `switch: Registeel`
- Type: `team_preview_or_initial_deployment`
- Legacy reason: `initial_deployment_nondecision`
- Result: `intentionally_skipped_nondecision`
- Remaining reason: `skipped_nondecision`
- Legacy candidates: `[]`
- Pre-action candidates: `[]`

### `gen9randombattle-2588641014` turn 0 p2

- Raw: `|switch|p2a: Hippowdon|Hippowdon, L82, M|311/311`
- Parsed: `switch: Hippowdon`
- Type: `team_preview_or_initial_deployment`
- Legacy reason: `initial_deployment_nondecision`
- Result: `intentionally_skipped_nondecision`
- Remaining reason: `skipped_nondecision`
- Legacy candidates: `[]`
- Pre-action candidates: `[]`

### `gen9randombattle-2588641014` turn 5 p2

- Raw: `|move|p2a: Tauros|Close Combat|p1a: Girafarig`
- Parsed: `move: Close Combat`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Hippowdon', 'switch:switch: Grafaiai', 'switch:switch: Tauros', 'switch:switch: Alomomola', 'switch:switch: Arboliva']`
- Pre-action candidates: `['move:Bulk Up', 'move_tera:Bulk Up', 'move:Close Combat', 'move_tera:Close Combat', 'switch:switch: Hippowdon', 'switch:switch: Grafaiai', 'switch:switch: Alomomola', 'switch:switch: Arboliva', 'switch:switch: Kyogre']`

### `gen9randombattle-2588641014` turn 6 p2

- Raw: `|move|p2a: Tauros|Close Combat|p1a: Girafarig`
- Parsed: `move: Close Combat`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Hippowdon', 'switch:switch: Grafaiai', 'switch:switch: Tauros', 'switch:switch: Alomomola', 'switch:switch: Arboliva']`
- Pre-action candidates: `['move:Bulk Up', 'move_tera:Bulk Up', 'move:Close Combat', 'move_tera:Close Combat', 'switch:switch: Hippowdon', 'switch:switch: Grafaiai', 'switch:switch: Alomomola', 'switch:switch: Arboliva', 'switch:switch: Kyogre']`

### `gen9randombattle-2588641014` turn 7 p1

- Raw: `|move|p1a: Giratina|Will-O-Wisp|p2a: Grafaiai`
- Parsed: `move: Will-O-Wisp`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Registeel', 'switch:switch: Glalie', 'switch:switch: Giratina', 'switch:switch: Vaporeon']`
- Pre-action candidates: `['move:Draco Meteor', 'move_tera:Draco Meteor', 'move:Poltergeist', 'move_tera:Poltergeist', 'move:Shadow Sneak', 'move_tera:Shadow Sneak', 'move:Will-O-Wisp', 'move_tera:Will-O-Wisp', 'switch:switch: Registeel', 'switch:switch: Glalie', 'switch:switch: Vaporeon', 'switch:switch: Shiftry']`

### `gen9randombattle-2588641014` turn 10 p2

- Raw: `|move|p2a: Tauros|Bulk Up|p2a: Tauros`
- Parsed: `move: Bulk Up`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Hippowdon', 'switch:switch: Grafaiai', 'switch:switch: Tauros', 'switch:switch: Alomomola', 'switch:switch: Arboliva']`
- Pre-action candidates: `['move:Bulk Up', 'move_tera:Bulk Up', 'move:Close Combat', 'move_tera:Close Combat', 'switch:switch: Hippowdon', 'switch:switch: Grafaiai', 'switch:switch: Alomomola', 'switch:switch: Arboliva', 'switch:switch: Kyogre']`

### `gen9randombattle-2588641014` turn 11 p1

- Raw: `|move|p1a: Giratina|Will-O-Wisp|p2a: Grafaiai|[miss]`
- Parsed: `move: Will-O-Wisp`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Registeel', 'switch:switch: Glalie', 'switch:switch: Giratina', 'switch:switch: Vaporeon']`
- Pre-action candidates: `['move:Draco Meteor', 'move_tera:Draco Meteor', 'move:Poltergeist', 'move_tera:Poltergeist', 'move:Shadow Sneak', 'move_tera:Shadow Sneak', 'move:Will-O-Wisp', 'move_tera:Will-O-Wisp', 'switch:switch: Registeel', 'switch:switch: Glalie', 'switch:switch: Vaporeon', 'switch:switch: Shiftry']`

### `gen9randombattle-2588641014` turn 20 p2

- Raw: `|switch|p2a: Kyogre|Kyogre, L71|259/259`
- Parsed: `switch: Kyogre`
- Type: `switch`
- Legacy reason: `switch_target_missing_from_pre_action_legal_roster`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['move:Earth Power', 'move_tera:Earth Power', 'move:Energy Ball', 'move_tera:Energy Ball', 'switch:switch: Hippowdon', 'switch:switch: Tauros-Paldea-Combat', 'switch:switch: Tauros', 'switch:switch: Alomomola']`
- Pre-action candidates: `['move:Earth Power', 'move_tera:Earth Power', 'move:Energy Ball', 'move_tera:Energy Ball', 'switch:switch: Hippowdon', 'switch:switch: Tauros-Paldea-Combat', 'switch:switch: Alomomola', 'switch:switch: Kyogre']`

### `gen9randombattle-2588641014` turn 20 p1

- Raw: `|move|p1a: Giratina|Will-O-Wisp|p2a: Kyogre`
- Parsed: `move: Will-O-Wisp`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Registeel', 'switch:switch: Giratina', 'switch:switch: Vaporeon']`
- Pre-action candidates: `['move:Draco Meteor', 'move_tera:Draco Meteor', 'move:Poltergeist', 'move_tera:Poltergeist', 'move:Shadow Sneak', 'move_tera:Shadow Sneak', 'move:Will-O-Wisp', 'move_tera:Will-O-Wisp', 'switch:switch: Registeel', 'switch:switch: Vaporeon', 'switch:switch: Shiftry']`

### `gen9randombattle-2588641014` turn 21 p2

- Raw: `|move|p2a: Kyogre|Calm Mind|p2a: Kyogre`
- Parsed: `move: Calm Mind`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Hippowdon', 'switch:switch: Tauros-Paldea-Combat', 'switch:switch: Tauros', 'switch:switch: Alomomola', 'switch:switch: Arboliva']`
- Pre-action candidates: `['move:Calm Mind', 'move_tera:Calm Mind', 'move:Ice Beam', 'move_tera:Ice Beam', 'move:Thunder', 'move_tera:Thunder', 'switch:switch: Hippowdon', 'switch:switch: Tauros-Paldea-Combat', 'switch:switch: Alomomola', 'switch:switch: Arboliva']`

### `gen9randombattle-2588641014` turn 22 p2

- Raw: `|move|p2a: Kyogre|Thunder|p1a: Vaporeon`
- Parsed: `move: Thunder`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Hippowdon', 'switch:switch: Tauros-Paldea-Combat', 'switch:switch: Tauros', 'switch:switch: Alomomola', 'switch:switch: Arboliva']`
- Pre-action candidates: `['move:Calm Mind', 'move_tera:Calm Mind', 'move:Ice Beam', 'move_tera:Ice Beam', 'move:Thunder', 'move_tera:Thunder', 'switch:switch: Hippowdon', 'switch:switch: Tauros-Paldea-Combat', 'switch:switch: Alomomola', 'switch:switch: Arboliva']`

### `gen9randombattle-2588641014` turn 23 p1

- Raw: `|switch|p1a: Shiftry|Shiftry, L89, F|305/305`
- Parsed: `switch: Shiftry`
- Type: `switch`
- Legacy reason: `switch_target_missing_from_pre_action_legal_roster`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['move:Flip Turn', 'move_tera:Flip Turn', 'move:Scald', 'move_tera:Scald', 'move:Wish', 'move_tera:Wish', 'switch:switch: Registeel', 'switch:switch: Giratina-Origin', 'switch:switch: Giratina']`
- Pre-action candidates: `['move:Flip Turn', 'move_tera:Flip Turn', 'move:Scald', 'move_tera:Scald', 'move:Wish', 'move_tera:Wish', 'switch:switch: Registeel', 'switch:switch: Giratina-Origin', 'switch:switch: Shiftry']`

### `gen9randombattle-2588641014` turn 23 p2

- Raw: `|move|p2a: Kyogre|Calm Mind|p2a: Kyogre`
- Parsed: `move: Calm Mind`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Hippowdon', 'switch:switch: Tauros-Paldea-Combat', 'switch:switch: Tauros', 'switch:switch: Alomomola', 'switch:switch: Arboliva']`
- Pre-action candidates: `['move:Calm Mind', 'move_tera:Calm Mind', 'move:Ice Beam', 'move_tera:Ice Beam', 'move:Thunder', 'move_tera:Thunder', 'switch:switch: Hippowdon', 'switch:switch: Tauros-Paldea-Combat', 'switch:switch: Alomomola', 'switch:switch: Arboliva']`

### `gen9randombattle-2588641014` turn 24 p1

- Raw: `|move|p1a: Shiftry|Knock Off|p2a: Kyogre`
- Parsed: `move: Knock Off`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Registeel', 'switch:switch: Giratina-Origin', 'switch:switch: Giratina', 'switch:switch: Vaporeon']`
- Pre-action candidates: `['move:Knock Off', 'move_tera:Knock Off', 'switch:switch: Registeel', 'switch:switch: Giratina-Origin', 'switch:switch: Vaporeon']`

### `gen9randombattle-2588641014` turn 24 p2

- Raw: `|move|p2a: Kyogre|Ice Beam|p1a: Shiftry`
- Parsed: `move_tera: Ice Beam`
- Type: `move_tera`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Hippowdon', 'switch:switch: Tauros-Paldea-Combat', 'switch:switch: Tauros', 'switch:switch: Alomomola', 'switch:switch: Arboliva']`
- Pre-action candidates: `['move:Calm Mind', 'move_tera:Calm Mind', 'move:Ice Beam', 'move_tera:Ice Beam', 'move:Thunder', 'move_tera:Thunder', 'switch:switch: Hippowdon', 'switch:switch: Tauros-Paldea-Combat', 'switch:switch: Alomomola', 'switch:switch: Arboliva']`

### `gen9randombattle-2588641014` turn 25 p1

- Raw: `|move|p1a: Giratina|Draco Meteor|p2a: Kyogre`
- Parsed: `move: Draco Meteor`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Registeel', 'switch:switch: Giratina', 'switch:switch: Vaporeon']`
- Pre-action candidates: `['move:Draco Meteor', 'move_tera:Draco Meteor', 'move:Poltergeist', 'move_tera:Poltergeist', 'move:Shadow Sneak', 'move_tera:Shadow Sneak', 'move:Will-O-Wisp', 'move_tera:Will-O-Wisp', 'switch:switch: Registeel', 'switch:switch: Vaporeon']`

### `gen9randombattle-2588641014` turn 26 p1

- Raw: `|move|p1a: Giratina|Will-O-Wisp|p2a: Alomomola`
- Parsed: `move: Will-O-Wisp`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Registeel', 'switch:switch: Giratina', 'switch:switch: Vaporeon']`
- Pre-action candidates: `['move:Draco Meteor', 'move_tera:Draco Meteor', 'move:Poltergeist', 'move_tera:Poltergeist', 'move:Shadow Sneak', 'move_tera:Shadow Sneak', 'move:Will-O-Wisp', 'move_tera:Will-O-Wisp', 'switch:switch: Registeel', 'switch:switch: Vaporeon']`

### `gen9randombattle-2588641014` turn 33 p1

- Raw: `|move|p1a: Giratina|Poltergeist|p2a: Alomomola|[miss]`
- Parsed: `move: Poltergeist`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Registeel', 'switch:switch: Giratina', 'switch:switch: Vaporeon']`
- Pre-action candidates: `['move:Draco Meteor', 'move_tera:Draco Meteor', 'move:Poltergeist', 'move_tera:Poltergeist', 'move:Shadow Sneak', 'move_tera:Shadow Sneak', 'move:Will-O-Wisp', 'move_tera:Will-O-Wisp', 'switch:switch: Registeel', 'switch:switch: Vaporeon']`

### `gen9randombattle-2588641014` turn 37 p1

- Raw: `|move|p1a: Giratina|Poltergeist|p2a: Alomomola`
- Parsed: `move: Poltergeist`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Registeel', 'switch:switch: Giratina', 'switch:switch: Vaporeon']`
- Pre-action candidates: `['move:Draco Meteor', 'move_tera:Draco Meteor', 'move:Poltergeist', 'move_tera:Poltergeist', 'move:Shadow Sneak', 'move_tera:Shadow Sneak', 'move:Will-O-Wisp', 'move_tera:Will-O-Wisp', 'switch:switch: Registeel', 'switch:switch: Vaporeon']`

### `gen9randombattle-2588641014` turn 38 p1

- Raw: `|move|p1a: Giratina|Draco Meteor|p2a: Alomomola`
- Parsed: `move: Draco Meteor`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Registeel', 'switch:switch: Giratina', 'switch:switch: Vaporeon']`
- Pre-action candidates: `['move:Draco Meteor', 'move_tera:Draco Meteor', 'move:Poltergeist', 'move_tera:Poltergeist', 'move:Shadow Sneak', 'move_tera:Shadow Sneak', 'move:Will-O-Wisp', 'move_tera:Will-O-Wisp', 'switch:switch: Registeel', 'switch:switch: Vaporeon']`

### `gen9randombattle-2588641014` turn 39 p1

- Raw: `|move|p1a: Giratina|Shadow Sneak|p2a: Alomomola`
- Parsed: `move: Shadow Sneak`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Registeel', 'switch:switch: Giratina', 'switch:switch: Vaporeon']`
- Pre-action candidates: `['move:Draco Meteor', 'move_tera:Draco Meteor', 'move:Poltergeist', 'move_tera:Poltergeist', 'move:Shadow Sneak', 'move_tera:Shadow Sneak', 'move:Will-O-Wisp', 'move_tera:Will-O-Wisp', 'switch:switch: Registeel', 'switch:switch: Vaporeon']`

### `gen9randombattle-2588641014` turn 45 p2

- Raw: `|move|p2a: Tauros|Close Combat|p1a: Registeel`
- Parsed: `move: Close Combat`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Hippowdon', 'switch:switch: Tauros', 'switch:switch: Alomomola']`
- Pre-action candidates: `['move:Bulk Up', 'move:Close Combat', 'switch:switch: Hippowdon', 'switch:switch: Alomomola']`

### `gen9randombattle-2589135265` turn 0 p1

- Raw: `|switch|p1a: Giratina|Giratina-Origin, L72|335/335`
- Parsed: `switch: Giratina-Origin`
- Type: `team_preview_or_initial_deployment`
- Legacy reason: `initial_deployment_nondecision`
- Result: `intentionally_skipped_nondecision`
- Remaining reason: `skipped_nondecision`
- Legacy candidates: `[]`
- Pre-action candidates: `[]`

### `gen9randombattle-2589135265` turn 0 p2

- Raw: `|switch|p2a: Abomasnow|Abomasnow, L84, M|287/287`
- Parsed: `switch: Abomasnow`
- Type: `team_preview_or_initial_deployment`
- Legacy reason: `initial_deployment_nondecision`
- Result: `intentionally_skipped_nondecision`
- Remaining reason: `skipped_nondecision`
- Legacy candidates: `[]`
- Pre-action candidates: `[]`

### `gen9randombattle-2589135265` turn 22 p1

- Raw: `|move|p1a: Alcremie|Alluring Voice|p2a: Lapras`
- Parsed: `move: Alluring Voice`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Giratina-Origin', 'switch:switch: Alcremie', 'switch:switch: Arboliva']`
- Pre-action candidates: `['move:Alluring Voice', 'move_tera:Alluring Voice', 'switch:switch: Giratina-Origin', 'switch:switch: Arboliva', 'switch:switch: Kingambit']`

### `gen9randombattle-2589135265` turn 24 p1

- Raw: `|move|p1a: Giratina|Poltergeist|p2a: Lapras`
- Parsed: `move: Poltergeist`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Alcremie-Salted-Cream']`
- Pre-action candidates: `['move:Poltergeist', 'move_tera:Poltergeist', 'switch:switch: Alcremie-Salted-Cream', 'switch:switch: Kingambit']`

### `gen9randombattle-2589135265` turn 25 p1

- Raw: `|move|p1a: Giratina|Poltergeist|p2a: Enamorus`
- Parsed: `move: Poltergeist`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Alcremie-Salted-Cream']`
- Pre-action candidates: `['move:Poltergeist', 'move_tera:Poltergeist', 'switch:switch: Alcremie-Salted-Cream', 'switch:switch: Kingambit']`

### `gen9randombattle-2589135265` turn 26 p1

- Raw: `|switch|p1a: Kingambit|Kingambit, L74, F|270/270`
- Parsed: `switch: Kingambit`
- Type: `switch`
- Legacy reason: `switch_target_missing_from_pre_action_legal_roster`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Alcremie-Salted-Cream']`
- Pre-action candidates: `['move:Poltergeist', 'move_tera:Poltergeist', 'switch:switch: Alcremie-Salted-Cream', 'switch:switch: Kingambit']`

### `gen9randombattle-2589912457` turn 0 p1

- Raw: `|switch|p1a: Clawitzer|Clawitzer, L87, F|265/265`
- Parsed: `switch: Clawitzer`
- Type: `team_preview_or_initial_deployment`
- Legacy reason: `initial_deployment_nondecision`
- Result: `intentionally_skipped_nondecision`
- Remaining reason: `skipped_nondecision`
- Legacy candidates: `[]`
- Pre-action candidates: `[]`

### `gen9randombattle-2589912457` turn 0 p2

- Raw: `|switch|p2a: Vikavolt|Vikavolt, L83, F|263/263`
- Parsed: `switch: Vikavolt`
- Type: `team_preview_or_initial_deployment`
- Legacy reason: `initial_deployment_nondecision`
- Result: `intentionally_skipped_nondecision`
- Remaining reason: `skipped_nondecision`
- Legacy candidates: `[]`
- Pre-action candidates: `[]`

### `gen9randombattle-2589912457` turn 2 p1

- Raw: `|move|p1a: Tauros|Flare Blitz|p2a: Vikavolt`
- Parsed: `move: Flare Blitz`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Clawitzer', 'switch:switch: Tauros', 'switch:switch: Malamar']`
- Pre-action candidates: `['move:Flare Blitz', 'move_tera:Flare Blitz', 'switch:switch: Clawitzer', 'switch:switch: Malamar']`

### `gen9randombattle-2589912457` turn 3 p1

- Raw: `|move|p1a: Tauros|Flare Blitz|p2a: Sableye`
- Parsed: `move: Flare Blitz`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Clawitzer', 'switch:switch: Tauros', 'switch:switch: Malamar']`
- Pre-action candidates: `['move:Flare Blitz', 'move_tera:Flare Blitz', 'switch:switch: Clawitzer', 'switch:switch: Malamar', 'switch:switch: Tauros']`

### `gen9randombattle-2589912457` turn 4 p1

- Raw: `|move|p1a: Tauros|Flare Blitz|p2a: Sableye`
- Parsed: `move: Flare Blitz`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Clawitzer', 'switch:switch: Tauros', 'switch:switch: Malamar']`
- Pre-action candidates: `['move:Flare Blitz', 'move_tera:Flare Blitz', 'switch:switch: Clawitzer', 'switch:switch: Malamar', 'switch:switch: Tauros']`

### `gen9randombattle-2589912457` turn 5 p1

- Raw: `|move|p1a: Tauros|Flare Blitz|p2a: Ursaring`
- Parsed: `move: Flare Blitz`
- Type: `move`
- Legacy reason: `move_missing_from_reconstructed_active_moves`
- Result: `fixed_by_exact_pre_action_event_prefix`
- Remaining reason: `None`
- Legacy candidates: `['switch:switch: Clawitzer', 'switch:switch: Tauros', 'switch:switch: Malamar']`
- Pre-action candidates: `['move:Flare Blitz', 'move_tera:Flare Blitz', 'switch:switch: Clawitzer', 'switch:switch: Malamar', 'switch:switch: Tauros']`
