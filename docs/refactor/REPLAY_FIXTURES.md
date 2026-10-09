# Replay Fixture Policy

Replay-backed tests are opt-in environment checks. Missing raw fixtures are not
a production-code failure and must produce a clear pytest skip.

## Required fixture contract

- Expected local path: `data/replays/raw/gen9randombattle/`.
- Required file format: public Pokemon Showdown protocol `.log` files.
- Required ruleset/generation: `gen9randombattle` (Gen 9 Random Battles).
- Source: public saved replays from
  `https://replay.pokemonshowdown.com`.
- Provenance: keep the generated `metadata.jsonl` beside the logs. Each record
  should retain the replay ID, source URL, format, upload time when supplied by
  the source, and `downloaded_at`.
- Acquisition date: use the `downloaded_at` field in `metadata.jsonl`; do not
  infer it from a file timestamp.
- License/usage restrictions: use only replays that are publicly available under
  the source site's applicable terms. Do not add private, authenticated, or
  redistributed replay data to this directory without confirming permission.
- Checksum/manifest: when fixtures are shared or archived, create a manifest
  containing each relative path and SHA-256 checksum (for example with
  `shasum -a 256`) and retain it with the fixture bundle.

No replay fixtures are committed by this repository baseline.

## Commands

Replay-independent validation (default and CI-safe):

```bash
PYTHONPATH="$PWD/trainer/src" python3 -m pytest \
  trainer/tests/test_state_provenance_no_leakage_contracts.py \
  trainer/tests/test_tactical_state.py \
  trainer/tests/test_public_information_belief_contracts.py \
  -q
```

Replay-backed validation, only after fixtures are present:

```bash
PYTHONPATH="$PWD/trainer/src" python3 -m pytest trainer/tests -q -m replay
```

The replay-backed command does not acquire data. The existing opt-in acquisition
workflow, which performs network access and must not be part of default tests or
CI, is:

```powershell
.\scripts\run_windows.ps1 -Action fetch-replays -Format gen9randombattle -MaxReplays 1000 -DelaySec 0.5 -SimCoreMode native
```

Live/network validation is separate from replay tests:

```powershell
.\scripts\run_windows.ps1 -Action test-live-eval -SimCoreMode native
```

Expensive training/evaluation is separate as well; examples include:

```powershell
.\scripts\run_windows.ps1 -Action train-replay-value -Format gen9randombattle -SimCoreMode native
.\scripts\run_windows.ps1 -Action eval -EvalConfig .\configs\gen9randombattle_eval.dev.windows.yaml -SimCoreMode native
```

Those commands are never implied by `pytest`, `npm test`, or the replay-backed
validation command.
