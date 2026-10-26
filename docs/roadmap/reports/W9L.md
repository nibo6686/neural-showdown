# W9L - real replay regressions and decision frames

Selected the shortest admitted battle per public target, tied by ID; actual
pivot/drag handoffs and repeated moves under a revealed Choice item are required.
The manifest pins rating, server commit and selection reason. IDs below have
prefix `gen9randombattle-`. **29 fast fixtures + one opt-in long fixture**;
all selected fixtures pass, so no expected-failure entries are needed. Tests
support exact `expected_failure` reasons and check every adopted registry row.

| Target | ID | Target | ID |
|---|---|---|---|
| inactivity | 2695493840 | screens | 2700039370 |
| Knock Off | 2695512325 | Roar/Whirlwind | 2700729650 |
| forfeit | 2695618222 | Chilly Reception | 2701359770 |
| terrain | 2696005427 | Slow Start | 2701669079 |
| Terastallization | 2696024561 | hazards and removal | 2696255276 |
| Transform/Imposter | 2696035327 | Encore | 2696430584 |
| weather | 2696251026 | choice lock | 2701368829 |
| Volt Switch | 2697579755 | Pickpocket | 2696954386 |
| Illusion reveal/Trick/Switcheroo | 2699135667 | Revival Blessing | 2700299922 |
| U-turn | 2701474337 | Trick Room | 2700410206 |
| Parting Shot | 2695579524 | Recharge | 2696527591 |
| Flip Turn | 2695820606 | Magician | 2700105460 |
| Outrage/locked move | 2696390296 | Struggle | 2698390167 |
| Shed Tail | 2697300503 | Teleport | 2701424134 |
| Dragon Tail/Circle Throw | 2699896566 | 40+ turns | 2695498848* |

*40-turn fixture retained behind `NEURAL_LONG_TESTS=1`: the initial full set
exceeded its fast deadline; dropping the slowest case is allowed by the brief.
It passed the focused replay/K probe. Red Card, Eject Button/Pack and Emergency
Exit/Wimp Out were absent from admitted public logs. Exact shortest selection
produced 30 distinct battles rather than the estimated 20-25.

`decision-frame/v1` JSONL contains battle/step/owner, v2 addressed observation,
recipient-bound `native-owner-moves/v1` projection and observation binding,
canonical legal actions, and an optional canonical human action. CLI:
`node tools/replay_repro/export_frames.cjs replay.json [...] > frames.jsonl`.
Born self-play uses `sessionFrames(session, recipients, actions)` with v2
observations and the owner-moves profile. Python `read_frames(path)` reuses
existing observation, action and knowledge contracts, rejects extra/foreign
fields, mismatched identities/requests/legal sets and fabricated known values,
and returns values unchanged. It validates structure/consistency, not source
provenance or simulator truth; no vectors or dataset pipeline were added.

Both-owner born-team invariance passes in TS and Python: changing the opponent's
unrevealed bench species, moves, item, ability and Tera type leaves every frame
byte-identical before reveal; frames differ after the scripted reveal. Three
committed replay round trips pass. Focused Node: **4 pass, 1 long skip**;
Python: **17 pass** (including malformed/private/unknown/false-zero controls).

Fast gate: recorded before **134.44 s**; final **152.88 s** / 175 s (+18.44 s).
The first loaded attempt hit 175 s; after the owner stopped W1.3, the first idle
run passed in **150.89 s** (+16.45 s). Final build/gate and diff checks pass.
Node: 478 pass, 21 skip (+ producer 3 pass, 1 skip); Python: 265 pass,
5,484 subtests. All 38 adopted K rows exercised; zero mismatches.
No full suite or corpus job ran; the stopped W1.3 run was not restarted.
The pre-existing untracked `scripts/package-lock.json` is excluded from this slice.
