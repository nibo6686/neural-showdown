# Neural Showdown — Long-Term Implementation Plan

2026-10-16, revision 2. Revision 2 adds input-log replay reproduction, an
early evaluation harness and an ML/belief track, based on an external review
and a check of the local replay corpus. Supersedes the "next step" sections of
the `docs/planning/perspective-fidelity-*` prompts; their requirements and
accepted evidence still stand.

**Goal.** A Gen 9 Random Battle agent that makes strong decisions under
imperfect information, shows measurable competitive improvement, and explains
its recommendations using only information legitimately available to the
player. Complete perspective knowledge (all 61 properties) is a required part
of the finished system, not an optional extra.

**Roles.** Claude plans and reviews. Codex implements one slice at a time from
this plan. The owner approves phase changes and the **DECIDE** points.

**Owner decisions behind this plan**

1. **Full perspective knowledge is required.** All 61 properties in
   `docs/contracts/fixtures/perspective-knowledge-v1/property-contexts.json`,
   for both owners, from origin through terminal.
2. **Both data sources.** Self-play and the downloaded public replays.
3. **One main line on Showdown 0.11.11** for self-play and live use. Replay
   reproduction may need additional engine versions (§Phase 0.4).
4. **Lean process** (§1).

**Replay facts (measured 2026-10-16).** Public gen9randombattle replays include
an `inputlog`: `>version <server git commit>`, the battle seed, per-player team
seeds and every choice. That was true of all 15,001 replays in the old April
2026 corpus. Teams are regenerated from the seeds, so a replay reproduces only
on simulator code whose team generator and mechanics match its server commit.
One April replay diverges on npm 0.11.11 at the first switch. **The old corpus
is not used.** We download a fresh ~30k corpus and keep only replays that
reproduce exactly on the main-line engine (Phase 0.4). npm 0.11.11 was built
from upstream `739a5e1fee432ad80ff7136d70cca993be358b59`, while the live server
runs later master commits.

---

## 1. How work runs (lean process)

**A slice** is one Codex task with:

- **Goal:** one or two sentences naming the properties or behavior it delivers.
- **Files:** expected write set. Adjacent edits are allowed if the report
  mentions them.
- **Done when:** named tests that must pass, plus the coverage-registry rows
  (§2) or benchmark numbers it moves.
- **Report:** at most one page in `docs/roadmap/reports/<slice-id>.md`, covering
  what changed, what's supported or blocked, commands and results, and open
  questions. No hash-sealed evidence packets, retention receipts or per-slice
  planning docs.

**Rules that stay** (these are the real correctness requirements):

- Unknown is never a default. Omitted ≠ false ≠ zero. Hidden opponent facts and
  hidden timers stay unknown.
- No future or suffix information at a decision cursor. No foreign-owner
  private data.
- Canonical legal actions remain the only action authority.
- If a route isn't supported, block that property honestly in the registry.
- Never weaken validators to make a test pass.
- **Leakage invariance test:** changing hidden simulator state without changing
  a player's observations must not change that player's features. This is
  enforced by a test that every featurizer must pass.

**Dropped:** one-rerun limits, frozen-input attestations, byte-preservation of
evidence during ordinary development, mandatory second reviewers and
process-group ceremony. Use timeouts where tests can hang.

**Testing.** Codex runs the focused tests plus `npm run test:fast` before each
report. The full suite runs at the end of each workstream or when shared
infrastructure changes.

**Review.** Claude reviews each slice's diff and report for semantics,
privacy/causality, test adequacy and scope creep. Verdicts are accept,
fix-list or re-plan. Nits don't block acceptance.

**Commits.** One commit (or a short PR) per accepted slice. Push only when the
owner says so.

---

## 2. Two scoreboards

**Correctness: the coverage registry.** `docs/contracts/knowledge-coverage.json`
has one row per (property × context × perspective), with fields `status`
(`adopted` | `blocked` | `legitimately_unknown` | `missing`), `provider`,
`tests`, `limits`, `blocked_by` and `impact` (`high` | `medium` | `low`;
§Phase 1 ordering). `sim-core/tests/knowledge_coverage.test.ts` requires a row
for every contract property-context. Every `adopted` row must name at least one
positive test and one negative (unknown/omitted/foreign) test, and
`legitimately_unknown` is allowed only where the profile permits it. The
initial content comes from the Prompt58 table, adjusted for Prompts 59–60.

**Capability: the benchmark** (Phase 0.5). It reports win rate with confidence
intervals against fixed opponents on paired teams. Every model or
search change reports its numbers here.

A property moving to `adopted` is progress on correctness. A benchmark gain is
progress on strength. Both are tracked; neither substitutes for the other.

---

## Phase 0 — Consolidate, measure, de-risk (≈6 slices)

**0.1 Adopt 0.11.11 as main line.** Create branch `main-native11` from
`codex/machine-handoff-2026-10-16`. Overlay the restored candidate
(`C:\dev\neural-native11`): 30 files differ and 46 are new (`sim-core/src`
15+6, `sim-core/tests` 2+18, `trainer/src` 8, `docs/contracts` 3+18, package
files). Keep the repo's newer `docs/planning/`. No repo files need removing (all
repo files in the candidate's directories are in the candidate). Brief:
`docs/roadmap/briefs/P0.1.md`.
*Done when:* 0.11.11 is pinned, `npm ci` and the build succeed, the P57 canary
passes from the repo root, and `C:\dev\neural-native11` is retired.

**0.2 Windows full-suite baseline.** Run the whole `sim-core` suite (per file,
with timeouts) and `trainer/tests` with
`D:\Anaconda\envs\neuralgpu\python.exe`. Record green, red and hang counts per
file, and classify each red as a Windows/path issue, a known historical
failure, or a real defect. Fix only the Windows/path issues.

**0.3 Fast suite and coverage registry.** Add `npm run test:fast` (under 3
minutes) and the §2 registry and its test.

**0.4 Fresh replay corpus that reproduces on the main-line engine.** Reproduced
replays become exact native episodes, with private requests, legal sets and
true choices for both players, and they need no special replay knowledge path.

- **Probe:** download about 200 current gen9randombattle replays with
  `trainer/src/neural/replay_fetch.py`, keeping `inputlog`. Write
  `tools/replay_repro.ts`, which feeds the input log (minus `>version`/`>chat`)
  to the main-line `BattleStream` and compares the spectator-filtered output to
  the public log line by line (the public log is the exact-match oracle; a
  scratch prototype exists). Report the full-match rate per `>version` commit
  and the first divergence class for each failure (team generation, RNG,
  mechanics, protocol formatting).
- **If current server commits reproduce on 0.11.11:** keep 0.11.11.
- **If not:** **DECIDE** whether to re-pin the main line to the server's
  current commit, built from `smogon/pokemon-showdown` at that hash instead of
  the npm release. This is a single engine bump that re-validates the
  `version_profile.ts` pins and native hooks; it is not multi-version support.
  It is cheapest now, before Phase 1 adds more native hooks.
- **Then:** download about 30k replays in a short window (so they share one or
  two commits), keep only exact reproductions on the main-line engine, and drop
  the rest.
- *Done when:* the reproduction rate is known and a reproduced corpus exists
  with rating, outcome, length and commit recorded per battle.

Later replay refreshes repeat this. If the server's engine has moved, either
re-pin or accept a smaller reproducible slice. The system never supports old
engines retroactively.

**0.5 Evaluation harness (benchmark).** Build `tools/bench` with:

- fixed seeds and paired teams (each matchup is played twice with sides
  swapped);
- opponents: `baselines/random.ts`, a damage-greedy agent, `baselines/heuristic.ts`,
  and the best historical checkpoint as a control;
- reported win rate with a 95% CI, battle length, illegal-choice count and
  wall time.

N=1,000 paired games gives roughly ±3 points. The harness runs on 0.11.11 and
needs no K work.
*Done when:* a reproducible baseline table is committed to
`docs/roadmap/benchmarks.md`.

**0.6 Throughput profile.** Measure battles per second and decisions per second
for (i) the full evidence/capture path and (ii) a lean training path (protocol,
requests and legal actions only), plus memory per battle. This sets how much
self-play or RL is feasible on one machine, and whether a lean path is needed
(it must share semantics with the audited path).

---

## Phase 1 — Full perspective knowledge (Track A, ≈35–50 slices)

All 61 properties are required. The registry's `impact` column sets the order
within each workstream: properties that affect many decisions (hazards, HP,
status, boosts, items, abilities, Tera, choice lock, speed-relevant facts)
before rare ones (move incarnation through Mimic/Sketch/Transform; ball and
shiny cosmetics). Rare cases stay `blocked` until their turn, never faked.

Reproduced replays (0.4) flow through the same knowledge providers as
self-play, so Phase 1 only needs to support one engine.

| WS | Properties (Prompt58 IDs) | Reuse | Rough slices |
|---|---|---|---|
| W1 Owned moves & request info | K02 `current_moves`, `move_incarnation`; K07 `pp`/`max_pp` Req+Cur; K08 `disabled`, `maybe_disabled`, `trapped`, `maybe_trapped`, `lock` | Prompt61 design, P57 caller, `owned_request_health.ts` | 3–5 |
| W2 Owned current residue | K01 `party_position`, `roster_size` Cur O; K18 `item_held`; K05 terminal/precision; K20 terminal/requestless; the Prompt59 blockers (partial EV/IV, random gender) | Prompt59/60 interpreters | 3–4 |
| W3 Public actor association | K01 `roster_species`/`active_slot`/`roster_size` Cur B; K17 `appearance`, `identity_reveal`; K16 `form`, `types`, `transformed`, `tera` | B3 direct-switch, Illusion/replace subset, `owner_identity_*` | 5–7 |
| W4 Public health, status, boosts | K05 opponent (public precision); K06 status timing; K09 `boosts` | `public_health.ts`, `public_boosts.ts` | 4–5 |
| W5 Items & abilities | K18/K19 opponent current and `*_effective`; consumption/transfer/copy histories | `public_item.ts`, `public_ability.ts` | 4–6 |
| W6 Effect ledgers | K10–K15: persistent, single-turn, single-move, side conditions and layers, weather/terrain/pseudo-weather/effectiveness/remaining, pending intent/effect/power | `public_field.ts`, `effect_inventory.ts` | 8–12 |
| W7 Move execution history | K02 `move_execution` | `public_move_history.ts` | 2–3 |
| W8 Replay ingestion | FAC-04, R01–R05: a reproduced replay runs as a native episode, so its knowledge comes from the same providers as self-play. Add replay provenance to episodes (id, rating, commit, reproduction check) and retire the old unsafe replay callers (`build_action_rank_dataset.py`, `build_replay_*`). Non-reproducible replays are dropped, with no public-only path. | `replay_import.ts`, 0.4 tool | 2–3 |
| W9 Publication & Python bridge | FAC-06 TS→Python K snapshots, all-form parity, tamper rejection | `pipeline_episode_evidence.ts` | 3–4 |
| W10 Final assurance | Registry at zero `missing`; one integrated origin → wait → restore → forced/Revival → terminal test for both owners; Claude's final review | — | 2 |

```
Phase 0 ─► W1 ─► W9-lite ─► W2 ──► W7 ─────┐
        ├► W3 ─► W4 ─► W5 ─────────────────┤
        └► W6 (after W3 association) ──────┼─► W8 ─► W9 ─► W10
```

Workstream notes:

- **W1:** implement Prompt61 in lean slices (Appendix A). Copied, virtual and
  Transform incarnations stay `blocked` until W7.
- **W3:** a single public-association provider queried by every later public
  property. This is the biggest correctness risk.
- **W6:** one ledger design with per-effect-ID rule tables and tests; hidden
  durations are intervals or unknown.
- **W9:** comes after W3–W6 so it publishes a stable schema once.

---

## Phase 2 — ML (Track B)

**Ordering (owner decision, 2026-10-16): parallel tracks.** Track B begins
after Phase 0, W1 and **W9-lite** (Python read access to the currently adopted
subset, without the full publication schema). It trains on the honest adopted
subset while Track A continues, with missing properties as explicit `unknown`
inputs. That gives the model less information, never wrong information. Models
are retrained as properties land. **The final model is trained only after W10**
closes all 61 properties.

Why parallel: the model architecture decides what the knowledge layer must
expose (per-action features, belief inputs), and those interfaces are cheaper
to get right while Track A is still being built. The benchmark shows which
missing properties actually cost games, which feeds the `impact` ordering
without changing the scope.

**W9-lite** (Track A, right after W1): expose the adopted K snapshot per
decision to Python through the existing episode path, plus the leakage
invariance test. The full W9 replaces it later.

**B1. Data.**

- Self-play on 0.11.11 with exact legal actions, sharded with lineage and
  split by battle.
- Reproduced replays (0.4/W8) carry exact requests and legal sets for
  both players. Record rating, outcome, length, engine commit and
  reproduction status per battle.
- Human replays are imitation labels. Self-play from weak policies is RL
  experience, not imitation labels.

**B2. Belief model (not in the 61 properties; new).** Opponent hidden-set
posteriors from the gen9 random-set data (`data/random-battles/gen9/sets.json`
and generator rules) of the main-line engine, updated on reveals. Moves
are not independent: roles constrain them. Represent it as particles or a
compact candidate-set list. Beliefs stay separate from facts (REQ-022/023).
*Done when:* posterior calibration on held-out reproduced replays, where the
true sets are known from reproduction, beats a uniform prior.

**B3. Model.** An action-conditioned scorer Q(o, a) over canonical legal
actions, with action embeddings (type, category, priority, damage
distribution, Tera, switch target). It comes in two sizes: an MLP ranker first,
then a small permutation-aware transformer over the two teams, the field and
the actions. A joint value head predicts the outcome, and its calibration
(Brier score, reliability) is reported separately. The 13-slot codec is kept
only for compatibility.

**B4. Training stages.** (1) Imitation on reproduced high-rated replays plus
the value head; (2) one-turn expected-outcome search over belief samples;
(3) limited multi-turn rollouts; (4) belief-conditioned search; (5)
search-distilled policy. Each stage must beat the previous one on the
benchmark.

**B5. Opponent pool for self-play/RL:** frozen checkpoints, heuristics, the
imitation policy and search agents. This avoids self-play overfitting to its
own weaknesses.

**B6. Failure-driven loop.** Benchmark losses are categorized (missing
information, wrong belief, tactical miss, strategic miss) and feed the next
Track A or Track B priority.

## Phase 3 — Product

The first interface is **post-battle analysis**: replay review with ranked
alternatives, win probability over time and key uncertainties. A live
recommendation overlay comes later, after the owner confirms Showdown's rules
allow it. Latency and UX are **DECIDE** at that point.

---

## Decision points (owner)

| When | Decision |
|---|---|
| Now | Permission to download the probe replays (and later about 30k) for 0.4 |
| After 0.4 | Keep 0.11.11, or re-pin to the server's current commit |
| After W1 | Unblock copied/Transform incarnations in W7 or keep them blocked |
| End of Phase 1 | Sign off any `blocked` rows |
| B3 | Model size and compute budget (one local GPU assumed: torch 2.5.1+cu121 in `neuralgpu`) |
| Phase 3 | Live overlay vs analysis-only |

## Risks

- **Engine-version coupling.** The K layer hard-pins its engine
  (`version_profile.ts` integrity checks). Replays reproduce only on a matching
  engine, so each future corpus refresh means a re-pin or a smaller
  reproducible slice. Re-pinning is cheaper now than after Phase 1.
- **W3 and W6 scope.** If a slice balloons, Claude splits it.
- **Codex drift.** Each slice names the registry rows or benchmark numbers it
  moves; anything else needs a sentence of justification.
- **Outcome variance.** Use paired teams and enough games. Don't treat small
  win-rate deltas as real without CIs.
- **Corpus skew.** Public replays are a selected sample. The April corpus had
  a median rating of 1300, so expect the same; weight or filter by rating.

---

## Briefs

Ready-to-run Codex briefs live in `docs/roadmap/briefs/`:
`P0.1.md` (consolidation). W1.1 is below until it moves there.

## Appendix A — W1.1 brief for Codex (replaces Prompt62)

> **Slice W1.1 — owned move possession, incarnation continuity, PP freshness.**
> Repo: `C:\Users\cloud\Downloads\neural\final`, branch `main-native11`
> (after Phase 0.1–0.3). Read `docs/roadmap/LONG-TERM-PLAN.md` §1–2, then
> `docs/planning/perspective-fidelity-prompt61-design.md` and its lead review.
>
> **Goal.** Make the P57 owner-addressed decision callback receive each owner's
> current move possession, a stable ordinary/base move incarnation per slot,
> and PP/maxPP with freshness (`fresh` from an authenticated linked emission;
> `last_known` after an executed successor; omitted ≠ 0). This applies through
> bench, wait and held restore.
>
> **Files (expected).** New `sim-core/src/owned_request_moves.ts`; narrow
> changes in `owned_request_health.ts`, `env_manager.ts`,
> `native_owner_knowledge.ts` and `perspective_knowledge.ts`; profile
> `perspective-knowledge-native11-owner-moves-v1`; tests in
> `sim-core/tests/owned_request_moves.test.ts`.
>
> **Out of scope (mark `blocked`).** Copied, virtual, Mimic, Sketch and
> Transform incarnations; flags and lock (W1.2).
>
> **Done when:**
> 1. A generated both-owner battle shows the callback seeing possession and PP,
>    and the knowledge changes a legal ordering.
> 2. Decrement → bench → held return keeps the same incarnation, with stale
>    then refreshed PP and zero vs omitted vs never-emitted distinctions.
> 3. A constructed Transform interval blocks, then a qualified reset resumes
>    the base history. No copied PP.
> 4. A post-preparation failure leaves committed state unchanged, and a fresh
>    retry works.
> 5. Default (non-opt-in) output is byte-identical to before.
> 6. `npm run test:fast` is green and the K02/K07 registry rows are updated.
>
> **Report.** One page in `docs/roadmap/reports/W1.1.md`. Stop for review.
