# Track B — learned models

2026-10-26. Plan of record for the ML track, under `LONG-TERM-PLAN.md`
(Phase 2) and the same lean slice process (§1, `AGENTS.md`). Track A
(knowledge) continues in parallel; models are retrained as knowledge lands.
The final model waits for W10.

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
| **B2** | M1 model and training; held-out metrics (agreement by rating band, NLL, Brier, reliability); baseline-agent agreement on the same frames; **Python agent bridge** for `tools/bench` (subprocess, JSON lines, legal-only); benchmark M1 vs random/greedy/heuristic, 500 pairs each |
| B3 | Error analysis: categorize benchmark losses and disagreements (missing info, belief, tactical, strategic); pick the next lever |
| Later | `feature-v2` (K projection, born-session benchmark agents); B2 belief model (random-set priors and posteriors); one-turn search; self-play/RL with an opponent pool; larger datasets after the full-corpus run |

## Compute and time budgets
- Dataset build for 3,000 battles: background and supervised, a few hours.
  Nothing waits on it; B1's code is tested on the committed fixtures first.
- Training M1: about an hour on the GPU. Benchmark: about 15–30 min per
  matchup set.
- No long job runs without the supervisor, and none blocks a slice.
