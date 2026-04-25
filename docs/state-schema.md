# State Schema

Each `StepResult` contains:

- `views`: `{p1, p2}` player-legal `BattleView`s
- `requests`: normalized `ChoiceRequestView`s or `null`
- `rewards`: sparse terminal rewards
- `terminated`: whether the battle ended
- `winner`: `p1`, `p2`, `tie`, or `null`
- `log_delta`: public spectator log lines since the previous snapshot

`BattleView` includes:

- format, gen, turn, player ids, names
- active self and opponent slot indices
- field weather / terrain / pseudo-weather
- side conditions for self and opponent
- self team array with exact information from the latest request
- opponent team array containing only publicly revealed information

`ChoiceRequestView` includes:

- `wait`, `teamPreview`, `forceSwitch`, `trapped`, `rqid`
- the active move list when available
- side team snapshot from the latest request
- `legal_actions` with fixed-size action mask and concrete Showdown choices
