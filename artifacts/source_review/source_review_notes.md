# External Source Review Notes

**Date:** 2026-06-18
**Method:** Grounded review of the locally-installed `pokemon-showdown@0.11.10` source plus a
knowledge-based assessment of poke-env, PokeLLMon, PokéChamp, and Showdex. **Only Pokémon
Showdown was read from source in this pass** (it is vendored, free to read, and highest
signal). The other four are assessed from their published designs; each carries a
"verify-before-adapting" flag and the specific files to open if a recommendation is pursued.
No external repos were cloned and no dependencies were added.

---

## 1. Pokémon Showdown — REVIEWED FROM SOURCE ✅

**Path reviewed:** `sim-core/node_modules/pokemon-showdown/sim/` — `state.ts`, `battle.ts`,
`battle-stream.ts`, `prng.ts`, `teams.ts`, and our own `sim-core/src/belief_fork.ts`.

**Key finding — clean branching already exists and we already use it.**
- `sim/state.ts` exports `State.serializeBattle(battle)` / `State.deserializeBattle(state)`,
  a purpose-built deep serializer that handles the object graph via typed references. This is
  the *intended* clean way to snapshot and fork a battle.
- `Battle.prototype.toJSON()` wraps `serializeBattle`. Our `belief_fork.ts` **already** forks
  via `new Battle(...).toJSON()` + `structuredClone(serialized)`, and reseeds opponent teams
  with `Teams.generate(format, { seed: seedWithOffset(...) })`. So the answer to "is there a
  cleaner way to branch than replay-from-seed?" is **yes — serialize/deserialize — and the
  belief fork already adopted it.**

**Relevant ideas:**
- `inputLog` (on `Battle`) + a fixed PRNG seed gives a second, independent reconstruction path
  (replay the recorded choices). Useful as a **parity cross-check**: snapshot-fork vs.
  inputLog-replay should produce identical states. Worth a single regression test in
  `mechanics_parity.test.ts` to harden the fork.
- `sim/prng.ts` exposes the seed as a readable/writable array; our `seedWithOffset` helper is
  consistent with how PS derives sub-seeds. No change needed.
- `data/random-battles/` is the ground truth our randbats beliefs approximate. When Task 5
  (public-evidence calibration) enumerates candidate sets, it should read from the **installed
  generator's set tables**, not a hand-maintained copy, to stay version-locked to 0.11.10.

**Not relevant:** `battle-stream.ts` multiplexing, the login/ladder server layers — we drive
the sim directly over our own RPC.

**Adapt?** No new code to import — we already use the right API. **Action:** add an
inputLog-replay vs. serialize-fork parity test; source Task-5 candidate sets from the
installed `Teams` generator.

**License:** MIT (same as our pinned dependency). No concern.

---

## 2. poke-env — assessed (not cloned)

**Relevant ideas:**
- The `Player`/`AbstractPlayer` abstraction and the `Battle` observation object (which tracks
  *revealed* opponent info separately from hidden info) are a mature reference for the exact
  public/private boundary we enforce in belief mode. Worth comparing field-by-field against
  `live_private_state.py` to catch any leak we missed.
- `cross_evaluate` (round-robin win-rate matrix with sample counts) is a clean template for
  `run_agent_tournament.py` — particularly reporting **paired** results and confidence on
  small N, which our 20-battle audits currently lack.

**Not relevant:** poke-env drives a *live* Showdown websocket server with real account/challenge
flow and gymnasium wrappers. We deliberately run seeded, in-process, offline sims — adopting
its server/gym layer would add a network dependency and break determinism.

**Adapt?** Pattern only (no code): mirror its revealed-vs-hidden split as a checklist, and
borrow the round-robin/paired-CI reporting shape for tournaments.

**License:** MIT — safe to read and re-implement patterns. Verify before copying code.

---

## 3. PokeLLMon — assessed (not cloned), DIAGNOSTICS ONLY

**Relevant ideas:**
- Its **panic-switching** analysis (the agent repeatedly switching under pressure) is exactly
  the kind of pathology our `tactical_failure_report.md` already hunts. Their consistency
  metric (penalize oscillating switch decisions) is adaptable as a **diagnostic counter** in
  the audit, independent of any LLM.
- Battle-state→text translation is a useful reference *if* we ever want human-readable position
  dumps in audits, but not required.

**Not relevant / explicitly excluded:** live LLM move selection, knowledge-augmented prompting,
and the LLM opponent-reasoning loop. Out of scope per the task's hard limits.

**Adapt?** Concept only: add a panic/oscillation diagnostic to the audit. No code, no
dependency.

**License:** research code — **verify license before copying any source.** Concept reuse is
fine.

---

## 4. PokéChamp — assessed (not cloned), MOST RELEVANT TO SEARCH

**Relevant ideas:**
- **Minimax framing under partial observability** maps directly onto our 1-ply → 2-ply → belief
  progression. The key transferable idea is **bounding the branching factor by sampling a small
  set of candidate opponent actions/sets** rather than expanding all — which is precisely the
  direction Task 5 (weighted belief particles) is heading.
- **Opponent modeling via belief sampling at internal nodes** (not just the root) is the next
  conceptual step beyond our current root-only 3-particle aggregation.
- Their **benchmark/puzzle design** (fixed positions with a known best action) is a strong model
  for turning our seeded audits into a stable regression suite rather than win-rate-only smoke.

**Not relevant / excluded now:** LLM-based action proposal and LLM value estimation. We keep
material/HP leaf scoring; the lesson is the *search structure*, not the LLM.

**Adapt?** Design influence on Task 5 and on a future internal-node belief expansion. Consider a
small fixed-position puzzle set as a deterministic regression benchmark.

**License:** research code — **verify before copying.** Framing reuse is fine.

---

## 5. Showdex — assessed (not cloned), RELEVANT TO TASK 5

**Relevant ideas:**
- Showdex infers **damage ranges, sets, items, abilities, and spreads from public info** in the
  live UI using `@smogon/calc` (the same calc we pin). Its public-evidence inference is the
  closest existing analog to the **public-evidence belief calibration** designed in Task 5:
  eliminate impossible sets, weight candidates by observed damage ranges and speed order.
- Worth a targeted look at *how* it narrows spreads from an observed damage roll (the inverse
  damage-range problem) before we implement our own weighting.

**Not relevant:** the React/browser-extension UI layer and Showdown client integration.

**Adapt?** Inference *logic* could inform Task 5's weighting, but **do not vendor code.**

**License — CONCERN:** Showdex is distributed under a copyleft license (AGPL-family). Copying
its source into this repo would impose strong obligations. **Treat as read-for-ideas only;
re-implement independently.** Confirm the exact license on the maintained repo before any code
reuse.

---

## Bottom line for Neural Showdown

**Does external review suggest any immediate code change? Essentially no — one small, optional
hardening test.** The most important question ("cleaner way to branch than replay-from-seed")
is already answered and already implemented via `State.serializeBattle`/`Battle.toJSON()` in
`belief_fork.ts`. Concrete, low-risk takeaways:

1. **(Optional, small)** Add an `inputLog`-replay vs. serialize-fork parity test to
   `mechanics_parity.test.ts` to harden the fork. Pure correctness, no behavior change.
2. **(Task 5 input)** Source candidate randbats sets from the installed `Teams` generator
   (version-locked) and let Showdex/PokéChamp inference framing inform the weighting design.
3. **(Audit quality)** Borrow poke-env's paired/round-robin CI reporting and PokeLLMon's
   panic-switch diagnostic for `run_agent_tournament.py` — reporting only, no live behavior.
4. **No new dependencies, no LLM move selection, no copyleft code** vendored.

None of these block the current checkpoint; items 2–3 fold naturally into the next research
task (Task 5).
