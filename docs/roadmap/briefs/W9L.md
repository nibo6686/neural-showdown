> **Slice W9L — curated real-replay fixtures in the fast gate, and W9-lite (decision frames to Python).**
> Repo: `C:\Users\cloud\Downloads\neural\final` (main tree), branch
> `main-native11`, after `93e95f5`. Read `AGENTS.md` first: no delegation, no
> full suites, no known timeouts, and **no routine corpus runs**. This slice
> runs no corpus job. The W1.3 sample run may still be finishing in its own
> worktree; leave it alone.
>
> ### Part A — curated real-replay regression set (replaces per-slice corpus gates)
> 1. Write `tools/replay_repro/select_fixtures.cjs`. It scans the **admitted**
>    corpus (`data/replays/corpus-2026-10-21/admission.jsonl` plus the public
>    logs) and, for each coverage target below, picks the **shortest** admitted
>    battle that contains it. Make it deterministic and record why each one was
>    picked. Targets:
>    - pivots: U-turn, Volt Switch, Flip Turn, Parting Shot, Shed Tail,
>      Teleport, Chilly Reception;
>    - drags: Roar/Whirlwind, Dragon Tail/Circle Throw, Red Card;
>    - Eject Button/Pack, Emergency Exit/Wimp Out (if present);
>    - Illusion reveal, Transform/Imposter;
>    - item transfer: Trick/Switcheroo, Knock Off, Magician, Pickpocket;
>    - Revival Blessing, Encore, a choice-locked turn, Recharge (Hyper Beam or
>      Giga Impact), Struggle, Outrage/locked move;
>    - Slow Start;
>    - weather, terrain and Trick Room;
>    - hazards plus Rapid Spin or Defog, screens;
>    - Terastallization;
>    - a forfeit ending and an inactivity ending;
>    - one long (40+ turn) battle.
>
>    Expect about 20–25 battles; one battle can cover several targets.
> 2. Copy the chosen replay JSONs into `sim-core/tests/fixtures/replay-real/`,
>    with a `manifest.json` (id, rating, server commit, targets covered).
> 3. Add `sim-core/tests/replay_real.test.ts` to **`test:fast`**. Each fixture
>    runs through `replaySession` with the **K differential for all adopted
>    rows, including the owner-moves/flags rows**, and requires:
>    - exact public-log match;
>    - every boundary validates;
>    - **0 K mismatches**;
>    - the human's choices all map to canonical actions.
>
>    Run the fixtures in parallel workers. **Budget:** the set adds at most
>    about 20 s to the fast gate's wall time; drop the slowest fixture if
>    needed.
> 4. A fixture that currently fails (for example, a known W4/W5 public-evidence
>    case) goes in the manifest as `expected_failure` with its reason, and the
>    test asserts **that exact failure**. When the owning workstream fixes it,
>    flipping it to pass is part of that workstream's acceptance.
>
> ### Part B — W9-lite: adopted knowledge to Python, per decision
> Track B starts after W9-lite. It needs the adopted K snapshot at each
> decision, readable from Python, with privacy guaranteed.
> 1. **Export.** Add `tools/replay_repro/export_frames.cjs`. For given replays
>    (born via `replaySession`) or a born self-play session, write JSONL
>    **decision frames**, one per owner per boundary: battle id, step index,
>    owner, the owner's observation (public view, own request,
>    **owner-addressed K projection** with the adopted profiles), the canonical
>    legal action set, and, where it exists, the human's chosen canonical
>    action. Nothing from the other owner's private data, and nothing from the
>    future.
> 2. **Python reader.** Add `trainer/src/neural/decision_frames.py`, which
>    loads and validates frames:
>    - schema/version check;
>    - `owner` consistent throughout the frame;
>    - no field from the other owner's private request or projection;
>    - known/unknown/absent preserved exactly, with **no default filling**;
>    - legal actions match the request.
>
>    Malformed or privacy-violating frames are **rejected**, never repaired.
>    Use the existing Python readers and contracts where they apply; don't
>    duplicate the TS decoders' logic beyond what's needed to validate.
> 3. **Leakage invariance test** (plan §1 rule). Build two born sessions with
>    injected teams that are **identical in everything p1 can legitimately
>    know**, but differ in p2's hidden information: an unrevealed bench
>    member's species, set, item or Tera type. Play the same legal script.
>    **Every p1 frame must be byte-identical between the two sessions** up to
>    the point where the difference is publicly revealed, and must differ only
>    after the reveal. Mirror it for p2. Run it in TS (frame export) and in
>    Python (reader output).
> 4. **Tests:** the export/reader round trip on 3 committed fixtures; reader
>    rejections (a foreign-owner field, a fabricated known value, a legal-set
>    mismatch, a wrong version); the invariance test.
>
> **Out of scope.** Featurization or encoding into vectors (Track B's B3);
> dataset writing at scale; any corpus run.
>
> **Done when:**
> 1. Part A: the curated set is committed with its manifest and runs in
>    `test:fast` with 0 K mismatches (expected failures asserted exactly),
>    adding at most about 20 s.
> 2. Part B: export, reader and invariance test pass in TS and Python.
> 3. `tools/test_fast.ps1` passes under 175 s, and `git status` is clean.
> 4. There's one commit: "Curated real-replay fixtures and decision frames
>    (W9L)". Don't push. Stop for review.
>
> **Report.** One page, `docs/roadmap/reports/W9L.md`: the fixture table
> (target → replay ID), the fast-gate time before/after, the frame schema
> summary, and the invariance result.
