# External Source Review Plan

**Date:** 2026-06-18
**Goal:** Decide whether reviewing Pokémon Showdown, poke-env, PokeLLMon, PokéChamp, or
Showdex would help Neural Showdown — **targeted, not a rabbit hole.**

## Method (scope discipline)

- This is a **plan + a knowledge-grounded notes pass**, not a clone-everything exercise.
- For each project: 30–60 min budget, read only the modules named below, answer the specific
  questions, and record a go/no-go for adapting anything.
- Do **not** add any LLM move-selection dependency in this pass. Do not add new runtime
  dependencies without a separate decision.
- One dependency is already vendored and pinned: `pokemon-showdown@0.11.10` and
  `@smogon/calc@0.11.0`. Reviewing the *installed* version's source under
  `sim-core/node_modules/pokemon-showdown/` is the cheapest, highest-signal step and needs no
  network.

## Priority order and focus questions

### 1. Pokémon Showdown (official `smogon/pokemon-showdown`) — HIGHEST VALUE
Read (local, already installed): `sim/battle.ts`, `sim/battle-stream.ts`, `sim/side.ts`,
`sim/prng.ts`, `sim/teams.ts`, `data/random-battles/`.
Answer:
- Does `Battle` expose a clean serialize/restore (`toJSON`/`fromJSON`, `inputLog`) that lets us
  **branch by snapshot instead of replay-from-seed**?
- How is the PRNG seed set/read, and can a branch fork the seed deterministically?
- How does the request/choice protocol round-trip (relevant to our 13-action codec)?
- How are random-battle sets generated (the ground truth our randbats beliefs approximate)?

### 2. poke-env — agent/eval patterns
Focus: `Player`/`AbstractPlayer` abstraction, `Battle` observation object, how revealed
opponent info is tracked, local-server config, and `cross_evaluate` round-robin harness.
Answer:
- Is their observation/hidden-info model cleaner than ours, and worth mirroring in the audit?
- Is their evaluation harness (round-robin, win-rate CIs) worth borrowing for tournaments?

### 3. PokeLLMon — diagnostics only
Focus: battle-state→text translation, "panic switching" mitigation, knowledge retrieval
(type chart / move data), opponent reasoning prompts.
Answer:
- Anything reusable as a **diagnostic** (e.g. their consistency/panic-switch metric), *not*
  live LLM move selection?

### 4. PokéChamp — search framing
Focus: minimax depth-limiting, action sampling to bound branching, opponent modeling, value
estimation under partial observability, and benchmark/puzzle design.
Answer:
- Does their minimax framing suggest improvements to our 1-ply/2-ply/belief search?
- Is their puzzle/benchmark design adaptable to our seeded-position audits?
- (Explicitly: do **not** adopt LLM move selection yet.)

### 5. Showdex — only if a maintained source repo is confirmed
Focus: damage-range inference from public info, set/item/ability/spread inference, speed-tier
inference, UI-side public-evidence modeling.
Answer:
- Does their public-evidence inference map onto our planned **public-evidence belief
  calibration** (Task 5)?
- License/dependency concerns before adapting any inference logic?

## Deliverable

`artifacts/source_review/source_review_notes.md` — per project: path/link reviewed, relevant
ideas, irrelevant ideas, whether a code/API pattern should be adapted, license/dependency
concerns, and concrete recommendations for Neural Showdown.

## Out of scope this pass

Cloning research repos, running their code, adding LLM selection, team-building, tournament
data collection, doubles support.
