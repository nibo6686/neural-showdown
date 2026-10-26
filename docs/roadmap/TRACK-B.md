# Track B — learned models

2026-10-26. Plan of record for the ML track, under `LONG-TERM-PLAN.md`
(Phase 2) and the same lean slice process (§1, `AGENTS.md`). Track A
(knowledge) continues in parallel; models are retrained as knowledge lands.
The final model waits for W10.

**Paused (owner decision, 2026-10-26).** Track A comes first. After B1's code
(`a55f614`), nothing in this track runs until W10: no dataset build, B2 or
training. Resuming starts with fixing the builder's overhead
(`LONG-TERM-PLAN.md`, Phase 2). The rest of this file is the plan for when it
resumes.

## First milestone: M1, a learned imitation policy with a value head

**Goal.** A model trained on reproduced human battles that plays legal Gen 9
Random Battles through the benchmark harness, with measurable numbers:
action agreement with humans on held-out battles, value calibration, and win
rates with confidence intervals against `random`, `greedy` and `heuristic`.
M1 is a baseline to improve on, not a target strength. The point is to have the
whole pipeline (data → features → model → evaluation) working end to end, so
every later change is measured.

**M1 success criteria**
- Beats `random` with the 95% CI entirely above 90%.
- Held-out top-1 agreement with human choices **above every baseline agent's
  agreement on the same frames** (heuristic, greedy, random). Those agreements
  are computed and reported.
- The value head is better calibrated than a constant 50% (lower Brier score)
  on held-out battles. The reliability table is reported.
- Win rates against `greedy` and `heuristic` are reported with CIs. No
  threshold for M1; these are the numbers later milestones must beat.
- Every result reproduces from committed code, a dataset manifest and a seed.

## Decisions (Claude, as planner; the owner can override)

1. **Data: reproduced human battles first.** The 29,404 admitted corpus
   battles have exact private requests, legal sets and true choices for both
   players. M1 uses the **seeded 3,000-battle sample**
   (`sample-3000-seed20261024.json`, already used for gating): both owners,
   every decision, about 240k owner-decisions. Battles are split 90/5/5 by
   battle ID with a fixed seed, so no battle spans splits. The full corpus
   comes with the pre-dataset full run (plan policy). Self-play data comes
   later (RL stage); weak self-play is never used as imitation labels.
2. **Labels.** Policy: the human's chosen canonical action at that boundary,
   from frames. Value: the battle outcome from the owner's perspective (win 1,
   loss 0, tie 0.5). Forfeit and inactivity endings count as losses for the
   player who left, and are flagged so they can be excluded or weighted later.
   Rating is stored per example; M1 trains on all ratings and reports
   held-out agreement by rating band.
3. **Feature source for M1 (`feature-v1`):** only what the benchmark agent
   also receives, which is **the owner's v2 observation (public view plus own
   view) and own request**. That's the validated observable layer (0 public
   mismatches over 123M checks), and it includes public opponent state and
   the own team. The K projection's extra content (provenance, `last_known`
   PP history, emitted flag presence) waits for **`feature-v2`**, which comes
   when the benchmark can run born-session agents. **Unknown is never a
   default:** every feature that can be unknown carries an explicit
   known/unknown/absent indicator, and unrevealed opponent Pokémon are
   distinct placeholder tokens, not zeros.
4. **Model `M1` (action-conditioned entity transformer):**
   - **Tokens:** 12 Pokémon tokens (6 own, 6 opponent slots, with
     unrevealed placeholders), 1 field/side token, and one token per **legal
     action**. Categorical ids (species, items, abilities, moves, types, Tera
     types, status, weather/terrain/conditions) use learned embeddings from a
     **generated, versioned vocabulary** built from the pinned engine's dex.
     Numerics are normalized (HP fraction, level, boosts, stats for own only,
     PP fraction or unknown, turn).
   - **Encoder:** 3 layers, d=128, 4 heads (about 1–2M parameters), over
     Pokémon and field tokens.
   - **Policy:** each legal-action token (move: move id/type/category/base
     power/priority/accuracy/PP/disabled/Tera variant; switch: pointer to the
     target's Pokémon token) is scored with an MLP over [pooled state, action
     embedding, active and target tokens]. Softmax runs over **legal actions
     only**, using canonical legal actions with no fixed 13-slot output.
   - **Value:** an MLP over the pooled state gives the win probability
     (sigmoid).
   - **Loss:** CE(policy) + 0.5·BCE(value). AdamW, early stopping on held-out
     policy NLL. PyTorch on the RTX 2060 SUPER (8 GB, `neuralgpu`).
5. **Storage:** frames are about 89 KB each, mostly protocol history, so they
   are **featurized while streaming** and never stored in bulk. The dataset is
   compact sharded tensors (`.npz` or `.pt`) under git-ignored
   `data/datasets/`, plus a committed **manifest**: battle IDs, split, commit,
   engine, frame schema, feature version, vocabulary hash, label definitions
   and counts.
6. **Leakage.** The featurizer must pass the plan's invariance rule: the W9L
   invariance cases must give **byte-identical feature tensors** for the
   viewer before the reveal.

## Slices

| Slice | Content |
|---|---|
| **B1** (brief `briefs/B1.md`) | Vocabulary generator; `feature-v1` contract and Python featurizer; streaming dataset builder (born frames → features → shards) under the R1 supervisor; 3,000-battle dataset in the background; split/manifest; feature tests including leakage invariance |
| **B2** | M1 model and training; held-out metrics (agreement by rating band, NLL, Brier, reliability); baseline-agent agreement on the same frames; **auxiliary heads** (opponent hidden set, opponent next action; L1 below); **Python agent bridge** for `tools/bench` (subprocess, JSON lines, legal-only); benchmark M1 vs random/greedy/heuristic, 500 pairs each |
| B3 | Error analysis: categorize benchmark losses and disagreements (missing info, belief, tactical, strategic); pick the next lever |
| Later | `feature-v2` (K projection, born-session benchmark agents); B2 belief model (random-set priors and posteriors); one-turn search; self-play/RL with an opponent pool; larger datasets after the full-corpus run |

## Lessons from other bots (2026-10-26)

Taken from the 2026 Smogon bot threads: Jaxcalibur and Eevenator (Gen 9
randbats, #1 on the ladder at 2557 and 2626 Elo), and mikumiku37, Nessie123
and qtipsa's bot (VGC). All of them use small transformers trained mostly by
self-play, with search on top.

- **L1. Auxiliary heads (B2).** Add heads for each opponent Pokémon's item,
  ability, moves and Tera type, and for the opponent's next action.
  Jaxcalibur says the next-action head made its bot "substantially stronger".
  Reproduced battles give **exact labels** for both, from the other owner's
  own view and choice at the same step. These are targets only, never
  inputs. The opponent-set head is also M1's first learned belief model,
  which matches Eevenator's approach: hard deductions plus a learned
  posterior from the opponent's behavior.
- **L2. Measure throughput before planning RL.** Jaxcalibur played about
  100M games (a week on one H100, in a JAX engine it rewrote itself);
  mikumiku37 about 330M games (48 h, on a simulator 650× faster than
  Showdown). Before the RL stage, measure self-play games per second on the
  pinned engine (in-process, batched GPU inference) and decide: Showdown with
  more cores, or a fast engine checked against the corpus. The admitted
  replays are an exact differential oracle for a fast engine.
- **L3. Search: start with one turn, solved as a matrix game.** mikumiku37
  and Nessie build a payoff table of top-k actions against the opponent's
  top-k replies in each sampled world, and solve it for a mixed strategy.
  That's simpler than pUCT and fits our one-turn search slot. Jaxcalibur
  estimates search adds 100–150 Elo; the net does most of the work, so the
  order (model, then search) stays.
- **L4. No hidden-information leaks inside search.** A simulated opponent
  must not act on our private information. Jaxcalibur truncates the
  opponent's search once we do something surprising from their view (an
  unrevealed switch-in, or a move they'd predict below 65%); after that, the
  opponent uses the policy prior only. This is the plan §1 perspective rule
  applied to search. Every search slice must have a leakage test.
- **L5. RL-stage details.** Use a zero-avoiding regularizer (KL toward
  uniform) so situational moves like Encore never drop to zero probability.
  Small models trained longer beat larger ones (8.5M parameters); M1's size
  is fine. Jaxcalibur's known weaknesses are PP stalling and predictability:
  `feature-v2` exact PP tracking addresses the first, and mixed strategies
  from L3 the second.
- **L6. Evaluation and use: offline only.** All five developers stopped
  laddering or held back their releases over ladder-integrity concerns. Our
  bots never play the public ladder. For strength beyond the in-repo
  baselines, add **Foul Play** (open source; about 2341 Elo peak) as a
  local benchmark opponent. That needs the owner's approval to download it.
  Challenge matches against public bots are the owner's call. The product
  direction stays post-battle analysis: an evaluation bar and a "what it
  was thinking" view, as Nessie and Jaxcalibur show.

## B1 review checklist (beyond the brief's done-when)
- Opponent-set and next-action labels (L1) can be rebuilt **without raw
  frames**: each example has a join key (battle ID, step, owner), and the
  other owner's example at the same step has its full own-team features
  (species, item, ability, moves, Tera type) and its chosen action. If not,
  B2 adds those label columns to the builder before the full-corpus build.
- Own-team PP and the opponent's revealed moves are encoded with
  known/unknown kept distinct, so L5's PP-stalling fix has the data.
- The leakage-invariance test covers the featurized tensors, not only the
  frames.

## Compute and time budgets
- Dataset build for 3,000 battles: background and supervised, a few hours.
  Nothing waits on it; B1's code is tested on the committed fixtures first.
- Training M1: about an hour on the GPU. Benchmark: about 15–30 min per
  matchup set.
- No long job runs without the supervisor, and none blocks a slice.
