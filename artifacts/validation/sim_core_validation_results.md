# sim-core Validation Results

- Overall: `PASS`
- Generated: `2026-06-18T20:41:04-0600`
- pokemon-showdown: `0.11.10`
- @smogon/calc: `0.11.0`

## Commands

- `C:\Program Files\nodejs\npm.CMD test`: `PASS` (4.05s)
- `D:\Anaconda\envs\neuralgpu\python.exe -m unittest discover -s C:\Users\cloud\Downloads\neural\final\trainer\tests -p test_sim_core_parity.py`: `PASS` (1.30s)

## Damage healthcheck

- Result: `PASS`
- Heuristic fallback seen: `False`
- Exact attacker stats used: `True`
- Exact defender stats used: `True`

## Replay sanity

- Replays checked: `5`
- `dawn-gen9randombattle-305017.log`: turns=19 moves=30 switches=14 seed=False private_request=False
- `eternity-gen9randombattle-108.log`: turns=1 moves=0 switches=2 seed=False private_request=False
- `gen9randombattle-2587963818.log`: turns=31 moves=44 switches=28 seed=False private_request=False
- `gen9randombattle-2587966474.log`: turns=29 moves=46 switches=10 seed=False private_request=False
- `gen9randombattle-2587967313.log`: turns=119 moves=202 switches=35 seed=False private_request=False
