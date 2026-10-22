# Neural Showdown — Long-Term Implementation Plan

2026-10-16, revision 3. Revision 2 added input-log replay reproduction, an
early evaluation harness and an ML/belief track. Revision 3 records the replay
probe result (re-pin the engine to the server commit) and the P0.2 baseline,
which reorders Phase 0. Supersedes the "next step" sections of
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
3. **One engine for everything: Showdown server commit `b8f23c99`** (re-pinned
   from npm 0.11.11 in P0.4) for self-play, replays and live use. There's no
   multi-version support; future corpus refreshes re-pin.
4. **Lean process** (§1).

**Replay facts (measured 2026-10-16).** Public gen9randombattle replays include
an `inputlog`: `>version <server git commit>`, the battle seed, per-player team
seeds and every choice. That was true of all 15,001 replays in the old April
2026 corpus. Teams are regenerated from the seeds, so a replay reproduces only
on simulator code whose team generator and mechanics match its server commit.
**The old corpus is not used.** We tested a probe of 198 current replays
(2026-10-16), all on server commit
`b8f23c99629132611ba59e99480cb148ea8c5d3d`. **198/198 reproduce exactly on that
commit** (about 52 ms each); only **132/198 do on npm 0.11.11**, which was built
from the older upstream commit `739a5e1f`. The causes are drifted random-battle
levels for about 13 species, set/move changes and protocol text. Both
packages report version "0.11.11", so pins must name the commit. The ~30k
corpus is downloaded after the re-pin, and only exact reproductions are kept.

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

**Testing.** Codex runs the focused tests plus `tools/test_fast.ps1` before each
report, and does not run full suites unless a brief asks. Claude runs the full
Node/Python comparison against `docs/roadmap/baseline.md` during review, when
a slice touches shared infrastructure or ends a workstream.

**Cost.** Codex works each slice itself in one session: no sub-agent
delegation, project-lead or model-routing skills (see `AGENTS.md`). P0.4 hit
usage limits three times largely because of those, plus full-suite runs inside
Codex.

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

**Capability: the benchmark** (Phase 0.7). It reports win rate with confidence
intervals against fixed opponents on paired teams. Every model or
search change reports its numbers here.

A property moving to `adopted` is progress on correctness. A benchmark gain is
progress on strength. Both are tracked; neither substitutes for the other.

---

## Phase 0 — Consolidate, measure, de-risk (≈9 slices)

**0.1 Adopt the native11 candidate — done** (`35b9342`). It copied 75 manifest
files and replaced the restrictive `AGENTS.md` with a lean one.

**0.2 Windows full-suite baseline — done** (`76ea89e`,
`docs/roadmap/baseline.md`). Node had 455 passing and 572 failing tests;
Python had 891 passing and 63 failing. W fixes are applied. The classes are
595 S (stale), 12 R, 23 E, 2 T and 27 ?. The two dominant stale causes are
(a) about 363 tests using an old raw-snapshot restore helper that lacks
native11's occurrence-bound restore authority, and (b) about 65 fixed-seed
generator witnesses recorded under 0.11.10. Both are fixed **once, after the
re-pin** (0.5), because (b) changes again with the engine.

**0.3 Fast suite and coverage registry.** Add `npm run test:fast` (under 3
minutes), curated from tests that are green in the baseline and covering
knowledge, identity, delivery and legality. Also add the §2 registry and its
test.

**0.4 Re-pin the engine to `b8f23c99` — done** (`6fd0672`). 198/198 replays
reproduce, and no baseline-green test went red. The engine is a 5.1 MB
LFS-vendored tarball whose integrity and per-file hashes are verified at
runtime. Originally planned as: the brief is
`docs/roadmap/briefs/P0.4.md`. The engine is built from the commit by
`tools/engine/build_engine.ps1`, packed into an LFS-tracked
`vendor/pokemon-showdown-b8f23c99.tgz`, and installed as a `file:` dependency.
`version_profile.{ts,py}` pins the commit plus integrity, and the
engine-derived assets are regenerated by script. `tools/replay_repro` moves into
the repo; it must show 198/198 on the probe set. The profile id stays
`native11`. No baseline-green test may turn red except the listed fixed-seed
witnesses.

**0.5 Test migration on the final engine.** **0.5a** (brief `P0.5a.md`) adds a
*simulation-only* env mode: raw restore is allowed but there's no identity or
knowledge authority, and authoritative consumers reject it. The mechanics
tests move onto it with assertions unchanged. The same mode later serves
search and rollouts (B4). **0.5b** (brief `P0.5b.md`) re-adopts the ten
effect-lifecycle protocol families (`-start`/`-end`, side conditions, weather,
field, `cant`, `heal`) that native11 had quarantined as "unproved". 90% of real
replays contain them, so the extractor failed on almost every realistic battle.
The b8f23c99 effect inventory is generated from source and diffed against
0.11.10, the replay corpus is the acceptance oracle, root causes are surfaced
in settling diagnostics, and test randomness is seeded. **0.5b — done, partially** (`9faa5c0`): the
generated inventory, root causes and seeded tests landed, but 0/198 replays
extract cleanly, because shared engine-method diffs marked nearly every effect
"changed". **0.5b2** (brief `P0.5b2.md`) reviews each change class once,
closes the `|request|`/`|rated|`/item grammar gaps that hit nearly every
replay, adds a public-state differential check against the simulator, and
moves the settling cause to `Error.cause`. Target: at least 190/198 clean.
**0.5b2 — done** (`86460c3`): 190/198 probe replays
extract cleanly, with 0 mismatches across 797,186 public-state checks against
the simulator. **0.5b3** (brief `P0.5b3.md`) covers the Slow Start lifecycle
(the last residual), a shared `NEURAL_TEST_OUTPUT_DIR` for the Node→Python
test-output handoff, and the `request_emission_trace` hang. **0.5b3 — done** (`35d10ba`): all 198 probe replays extract cleanly, with
0 mismatches across 842,652 checks. **0.5c1** (brief `P0.5c1.md`) makes the
mechanical updates: fixed-seed witnesses re-found on b8f23c99, historical-10
reader tests switched or retired, current profiles, the Wish tuple fix and the
`ability_effects` contract doc. **0.5c2** (brief `P0.5c2.md`) moves about 336
authority tests from raw restore to *born sessions*: injected teams, real
session creation and scripted legal play, the pattern P48/P59 already use.
Both promote registry rows as their proof tests turn green. Then: This brings the suite back to
green-or-explained:

- migrate the shared raw-snapshot restore helpers to native11
  occurrence-bound restore (about 363 tests);
- regenerate the fixed-seed witnesses on `b8f23c99`;
- update the P48/P50/P59 tests to the current profiles (the decoders stay
  fixed);
- fix the Wish/Healing Wish tuple-vs-list comparison (R);
- resolve the 27 `?` items;
- fix the `request_emission_trace` timeout.

Tests that only assert 0.11.10-historical reader behavior can be kept as a
historical suite or deleted, with a reason for each file. Expect this to take
two or three slices, split by helper family. *Done when:* every red test is
fixed, deleted with a reason, or listed as `E`.

**0.5c2 — done** (`b0afaa0`): `born_session` helper, `pipeline_episode`
migrated, 1,634 passing / 389 failing. **0.5c3** (brief `P0.5c3.md`, owner
decision) migrates only the four core infrastructure files
(`active_request_restore`, `env_manager`, `request_delivery_ledger`,
`pipeline_integration`) and updates the Trace/Destiny Bond expectations. That
ends P0.5.

**Red-test ownership.** Every remaining red test file belongs to a Phase 1
workstream. Migrating it to born sessions, simulation-only, or retirement with
a reason is part of that workstream's first slice, and **a workstream can't be
marked done while it owns red tests**:

| Owner | Red files (failing tests at `b0afaa0`) |
|---|---|
| W1 moves & request info | `request_knowledge` (12), `request_knowledge_characterization` (19), `test_request_knowledge.py` (19), `test_request_knowledge_characterization.py` (8), `request_emission_trace` (4) |
| W2 owned residue / identity / boundaries | `original_owner_provider` (3), `original_owner_provider_characterization` (2), `owner_identity_birth` (2), `owner_identity_source_characterization` (2), `owner_identity_restore` (1), `owner_identity_events` (1), `snapshot_admission` (1), `settling` (2), `transition` (2), `pipeline_utf8_transport` (2), `revival` (9) |
| W3 public actor association | `illusion` (24), `transform_types` (2), `transform_boosts` (2), `added_types` (2), `forced_switch` (3), `roost` (8), `pipeline_episode` unbound switch source (4) |
| W4 health / status / boosts | `public_stages` (14), `selective_boosts` (4), `psych_up` (2), `topsy_turvy` (2), `public_consequences` (8), `pipeline_episode` Healing Wish health (2) |
| W5 items & abilities | `item_identity` (37), `item` (22) |
| W6 effect ledgers | `entry_hazard` (10), `screen` (6), `court_change` (14), `weather` (2), `terrain` (2), `trick_room` (2), `future_sight` (10), `wish` (10), `healing_wish` (8), `singlemove` (8), `repeat_use` (4), `spirit_shackle` (4), `perspective_field_semantics` (2) |
| W9 publication | `protocol_contract_validation` (3) |
| W10 assurance | `soak` (30), `test_gen9randbats_mechanics_completeness_audit.py` (2) |
| Track B (B2 beliefs/search) | `belief_fork` (3); belief forks are blocked on native11 until search needs them |

**Next after 0.5c3:** 0.7 benchmark, then W1. 0.6 (corpus) is downloading in
the background and is processed once complete.

**0.6 Fresh replay corpus — downloaded and reproduction-verified (2026-10-21).**
`data/replays/corpus-2026-10-21/` holds 29,666 main-server replays, all with
input logs (plus 325 side-server replays, which are excluded). They span five
server commits: `b8f23c99` 14,902, `942cda71` 10,738, `7332b60e` 2,196,
`de1cf598` 1,158 and `51ad80fa` 672. **29,620 (99.8%) reproduce exactly on the
pinned `b8f23c99`.** `de1cf598` is at 97.6% because of the No Retreat change;
the other commits are at 99.9–100%, and the residual mismatches are mostly
moderation lines. That leaves 25,340 exactly reproduced rated battles (median
rating 1,626; 11,107 rated 1,800+). No re-pin is needed. **Admission rule
change:** `tools/replay_repro` should admit any replay that reproduces exactly
on the pinned engine, whatever its `>version`, and record the server commit as
provenance, instead of requiring `>version == engine_commit`. Remaining 0.6
work (one small slice, after W1 starts): that rule change, running `--extract`
and `--diff` over the corpus, and recording rating, outcome, length, ending and
commit per battle.

Original 0.6 text, for reference: Download about 30k gen9randombattle replays in
as short a window as possible (rate-limited `replay_fetch.py`, about 1 replay
per second, so roughly 9 hours; run it in the background). Reproduce each one
with `tools/replay_repro` and keep only exact matches on the pinned commit.
Record rating, outcome, length, ending and commit per battle. If the server
moves to a new commit partway through, keep the `b8f23c99` portion and decide
later whether to re-pin.
*Done when:* the reproduced corpus and its stats are in
`docs/roadmap/benchmarks.md`.

**0.7 Evaluation harness (benchmark).** Build `tools/bench` with:

- fixed seeds and paired teams (each matchup played twice with sides swapped);
- opponents: `baselines/random.ts`, a damage-greedy agent,
  `baselines/heuristic.ts`, and the best historical checkpoint as a control;
- win rate with a 95% CI, battle length, illegal-choice count and wall time.

N=1,000 paired games gives roughly ±3 points. It needs no K work.
*Done when:* a reproducible baseline table is in `docs/roadmap/benchmarks.md`.

**0.8 Throughput profile.** Measure battles per second and decisions per second
for (i) the full evidence/capture path, (ii) a lean path (protocol, requests and
legal actions only), and (iii) input-log replay reproduction (about 52 ms per
battle today), plus memory per battle. This sets how much self-play or RL is
feasible on one machine, and whether a lean path is needed (it must share
semantics with the audited path).

Ordering: 0.3 → 0.4 → 0.5 come first. 0.6 can start as soon as 0.4 lands,
since the download runs in the background. 0.7 and 0.8 can run alongside 0.5.
W1 starts after 0.5.

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

- Self-play on the pinned engine with exact legal actions, sharded with lineage and
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
| 0.6 | Go-ahead for the ~30k replay download (probe already done) |
| Corpus refresh | Re-pin to the server's newer commit, or keep the existing reproducible slice |
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
> (after Phase 0.5). Read `docs/roadmap/LONG-TERM-PLAN.md` §1–2, then
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
