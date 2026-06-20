# Legacy Pipeline / Contamination Audit

Report-only audit. No models trained, no live defaults changed, no artifacts
deleted, no checkpoints promoted. Findings are based on targeted reads of
configs, trainer entrypoints, model/checkpoint code, the live serving path, and
on-disk checkpoint metadata.

## Executive Summary

- The repository contains three generations of models: (1) an original
  school-project generation with **no recorded feature schema** (positional
  `featurize.py` / scalar replay features), (2) a **versioned legacy
  generation** (`live-private-belief-v1/v2`, `legal-action-v1/v3`) that includes
  the current intentional live defaults, and (3) the new **diagnostic vNext**
  generation (`live-private-belief-v7` 3208D / `legal-action-v5` 318D).
- **The user's concern is confirmed for the oldest models.** `gen9randombattle_bc.pt`
  (1163D positional features) and `replay_value.pt` / `replay_policy.pt` (31D
  scalar summaries) trained on far less battle information than v2/v3, and
  dramatically less than v7/v5. They carry no belief/privacy modeling, no
  explicit move PP/lock constraints, and no action stat-delta features.
- **Live defaults are old by intent, not accident.** Default live serving
  (`NEURAL_LIVE_MODEL=live-private`) selects `live_private_value_v2.pt`
  (`live-private-belief-v2`, 115D) for value and `action_value_ranker_v2.pt`
  (`legal-action-v3`, state 115D / action 165D) for actions. The selection
  logic explicitly prefers the v2 paths, and the main value loader **hard-fails**
  on any other `feature_version`.
- **No serious accidental contamination path into vNext training exists.**
  `train_vnext_diagnostic.py` builds a fresh `VNextDiagnosticMLP` and has **no
  external checkpoint load/resume path**. vNext checkpoints are written to
  `artifacts/diagnostic_training/`, which is **outside** the live search
  directory (`artifacts/checkpoints/`), and their payload shape is incompatible
  with the legacy loaders (would raise, not silently load).
- **The main recording weakness is the absence of feature-name fingerprints in
  every checkpoint.** Checkpoints record `feature_version` + dim but never the
  ordered-name `sha256`. Only the vNext **dataset/config/metadata** carry
  fingerprints. Matching version+dim therefore does not by itself prove
  identical feature ordering/semantics.
- **One weaker live guard:** the action-ranker loader uses
  `load_state_dict(..., strict=False)` with **no `feature_version` assertion**,
  and the recommender pads/truncates feature vectors to the checkpoint's
  declared dims. This is a live-inference robustness gap (out of scope to change
  here), not a vNext-training contamination path.

## Old School-Project Pipeline (recovered)

The earliest pipeline is the behavior-cloning (BC) path:
`build_dataset.py` → `featurize.py` → `PolicyValueMLP` → `train_bc.py`,
evaluated via `eval.py` against sim-core. `featurize.py` emits a fixed
positional vector (per-Pokémon stat/type/status blocks, side conditions, active
move slots) with **no version tag**. A scalar "replay" generation
(`replay_value.pt` / `replay_policy.pt`, 31D) and a plain `value.pt` (1179D)
also predate the versioned belief features.

The versioned belief generation introduced `live-private-belief-v*` (privacy-
aware opponent belief state) and `legal-action-v*` (legal-action candidate
features). v2/v3 are the current intentional live defaults; v1 is superseded.

## Legacy Artifact Inventory

Checkpoint metadata read directly from disk. "Tracked" = committed to git.

| Artifact | Type | State schema | Action schema | Dims | Tracked | Referenced by | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `gen9randombattle_bc.pt` | policy-value MLP | **none** (positional `featurize.py`) | n/a | in=1163 | no | agent_audit, compare_checkpoints, improve_loop / PPO/eval defaults | **obsolete** (comparison baseline only) |
| `gen9randombattle_value.pt` | value MLP | **none** | n/a | in=1179 | no | compare_checkpoints, train_value default | **obsolete** |
| `gen9randombattle_replay_value.pt` | value | **none** (31D scalar) | n/a | in=31 | yes | live `public-replay` fallback (non-default), compare_* | **intentional-legacy (opt-in)** |
| `gen9randombattle_replay_policy.pt` | policy | **none** (31D scalar) | n/a | in=31 | yes | train_action_ranker default policy input | **obsolete/legacy input** |
| `gen9randombattle_live_private_value.pt` | live-private value | `live-private-belief-v1` | n/a | 78 | no | superseded by v2 | **obsolete** |
| `gen9randombattle_live_private_value_v2.pt` | live-private value | `live-private-belief-v2` | n/a | 115 | yes | **default live value model** | **intentional-legacy (LIVE DEFAULT)** |
| `gen9randombattle_live_sim_value_v1.pt` | bounded live/sim value | `live-private-belief-v2` | n/a | 115 | no | opt-in calibrated `/evaluate` scorer | **intentional (opt-in, validated)** |
| `gen9randombattle_action_ranker.pt` | action ranker | (implicit v1 state 78) | `legal-action-v1` | s78/a56 | no | superseded by v2 | **obsolete** |
| `gen9randombattle_action_ranker_v2.pt` | action ranker | (v2 state 115) | `legal-action-v3` | s115/a165 | yes | live action fallback | **intentional-legacy** |
| `gen9randombattle_action_value_ranker_v2.pt` | action-value ranker | `live-private-belief-v2` | `legal-action-v3` | s115/a165 | yes | **default live action model** | **intentional-legacy (LIVE DEFAULT)** |
| `artifacts/backups/20260428-124418/*_v2.pt` | snapshots | v2 / v3 | — | — | no | none | **archive** |
| `gen9randombattle_bc.*.pt` (dated/dev/smoke/awbc) | BC variants | **none** | n/a | ~1163 | no | dev/smoke configs | **obsolete (dev scratch)** |
| `diagnostic_training/.../model{,.best}.pt` (vNext) | shared diagnostic MLP | `live-private-belief-v7` | `legal-action-v5` | 3208/318 | no | vNext diagnostic only; `production_eligible=false` | **current/diagnostic** |

Related legacy datasets/reports (not exhaustive):
`data/shards/gen9randombattle_bc*.npz` (BC), `data/value/*_v2.npz` (v2 value),
`data/policy/*_rank_v2.npz` (v3 action rank), `artifacts/analysis/*` and
`artifacts/eval/*` (legacy eval/analysis reports). All are legacy-schema and
should be treated as historical.

## Schema / Version per Generation

| Schema | Dim | Generation |
| --- | --- | --- |
| (positional `featurize.py`) | 1163 / 1179 | original BC / value |
| (scalar replay) | 31 | replay value/policy |
| `live-private-belief-v1` | 78 | superseded |
| `live-private-belief-v2` | 115 | **live default state** |
| `live-private-belief-v7` | 3208 | diagnostic vNext |
| `legal-action-v1` | 56 | superseded |
| `legal-action-v3` | 165 | **live default action** |
| `legal-action-v5` | 318 | diagnostic vNext |

## What Old Models Received vs v7/v5

- **bc.pt / value.pt (1163–1179D positional):** per-Pokémon stats/types/status,
  side conditions, active-move slots. No opponent-belief privacy model, no PP/
  lock/disable constraints, no action stat-delta/side-effect features.
- **replay_value/policy (31D):** coarse scalar battle summary — extremely
  information-poor.
- **v1 (78D) → v2 (115D):** added privacy-aware belief features; v2 is the
  most-informed *deployed* model but still ~28× smaller than v7 (3208D).
- **v3 action (165D) → v5 (318D):** v5 adds explicit move side-effects/stat
  deltas (e.g. Draco self-SpA −1) and resolved-impact diagnostics absent in v3.

## Reference / Live-Default Analysis

- **Default live value:** `_selected_value_checkpoint_path()` →
  `live_private_value_v2.pt`. `load_value_model_once` / `_load_policy_value_model`
  **raise** if `feature_version != live-private-belief-v2`. Strong guard.
- **Default live action:** `load_action_ranker_once()` prefers
  `action_value_ranker_v2.pt` (then `action_ranker_v2.pt`), both `legal-action-v3`.
- **`public-replay` mode** (`replay_value.pt`, 31D) is reachable only by
  explicitly setting `NEURAL_LIVE_MODEL=public-replay`; default is `live-private`.
- **Opt-in `live_sim_value_v1`** is loaded only when
  `NEURAL_EVAL_STATE_SCORER` selects it, and is validated against v2 + dim +
  `bounded_output`.

**Conclusion: the old live defaults are intentional and self-consistent at v2/v3.**

## Contamination Risk Into vNext Training

| Path | Risk | Reason |
| --- | --- | --- |
| Legacy checkpoint loaded into vNext training | **None** | `train_vnext_diagnostic.py` has no checkpoint/resume arg; builds a fresh model. (`load_state_dict` at line 1160 only restores the in-memory best epoch.) |
| vNext checkpoint silently used live | **Low** | vNext checkpoints live in `diagnostic_training/`, not in the live `checkpoints/` search path; payload lacks `input_size` and uses a different model class, so legacy loaders would raise. |
| Legacy dataset fed to vNext training | **Low** | vNext loader validates schema versions, dims, and ordered-name fingerprints against the frozen config; a legacy `.npz` fails fingerprint/version checks. |
| Wrong-schema checkpoint dropped into `checkpoints/` and served | **Medium (live only)** | Value loader hard-fails on version mismatch; **action-ranker loader does not** (`strict=False`, no version assert, pad/truncate). Live-inference concern, not vNext training. |

## Training / Live Schema Mismatch Risk

- vNext training is well-guarded by version + dim + fingerprint validation.
- Live value path is guarded by version + dim.
- **Gaps:** (1) no checkpoint records feature-name `sha256` fingerprints, so
  version+dim match does not prove identical feature ordering; (2) the
  action-ranker live loader tolerates schema drift silently.

## Recommendations

**Keep**
- v2/v3 live-default checkpoints (`live_private_value_v2`, `action_value_ranker_v2`,
  `action_ranker_v2`) and `live_sim_value_v1` (opt-in). All intentional.
- vNext diagnostic checkpoints/datasets (current work).

**Mark deprecated** (documentation only; do not delete)
- `gen9randombattle_bc.pt`, `value.pt`, `live_private_value.pt` (v1),
  `action_ranker.pt` (v1), and BC dev/smoke variants — superseded, schema-less or
  v1. They remain valid only as historical comparison baselines.

**Quarantine / label clearly**
- `replay_value.pt` / `replay_policy.pt` (31D, no schema): keep only as the
  explicit `public-replay` opt-in; document that they are not schema-versioned
  and must never be a default.

**Require explicit compatibility flag (proposed guards, not yet implemented)**
- vNext training/inference should refuse any checkpoint whose recorded
  state/action `feature_version`, dims, **and** name-fingerprint do not match,
  unless an explicit `--allow-incompatible-checkpoint` flag is set.
- Action-ranker live loader should assert `action_feature_version` /
  `state_feature_version` (parity with the value loader) instead of `strict=False`
  + pad/truncate.

**Remove later (only with explicit approval)**
- Dated BC scratch checkpoints (`gen9randombattle_bc.2026*.pt`) and old `backups/`
  snapshot once confirmed unreferenced. Not removed in this audit.

## Missing Information

- The exact feature semantics of the schema-less BC/replay vectors are only
  recoverable from `featurize.py` / `build_replay_*` code, not from the
  checkpoints themselves (no embedded schema).
- No fingerprint exists for any deployed checkpoint, so historical feature
  ordering for v1/v2/v3 models cannot be cryptographically reconfirmed from the
  artifacts alone.
- Whether every legacy `.npz` under `data/` matches its checkpoint's schema was
  not exhaustively verified (sampled only).

## Proposed Follow-up Tests / Guards (low-risk, deferred)

1. **vNext checkpoint fingerprint field** — record `state_feature_names_sha256`
   / `action_feature_names_sha256` in the vNext checkpoint payload (currently
   only version+dim). Closes the ordering-ambiguity gap for future loads.
2. **vNext load guard test** — if a load/resume path is ever added, assert it
   refuses mismatched version/dim/fingerprint unless explicitly overridden.
3. **Action-ranker version-assert test** — verify the live action loader rejects
   a non-`legal-action-v3` checkpoint (parity with the value loader). Touches
   the live path, so requires explicit approval before implementing.
4. **Live schema-report assertion** — `/healthz`/status already reports
   `live_private_feature_version` etc.; add a test pinning these to v2/v3 so an
   accidental default change is caught.

These are recommendations only; none were implemented here to honor the
"do not change live defaults / report-only" scope.

## Gate Status

Training/live promotion gate remains **CLOSED**. This audit changed no code, no
defaults, and no artifacts.
