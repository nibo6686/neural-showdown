# vNext Real Packet Shadow Validation Report

- Existing replayable captures before this task: **no** (server logs contained access lines only).
- Capture mechanism: **added**, opt-in via `NEURAL_CAPTURE_EVALUATE_PAYLOADS=1`, default off, maximum 3 distinct actionable packets.
- Packets replayed: **1** (move: 1).
- Sanitization: room ID and URL replaced; account/player names redacted from request metadata and protocol player/win lines; chat/auth-like lines and token/session keys omitted.
- Dry-run successes: **1**; fail-closed cases: **0**.
- Command sent to Showdown: **no**.
- Battle played by the model: **no**.
- Live defaults changed: **no**.

## Packet Results

### `evaluate_001.json`

- Phase/turn: `move` / `1`
- Result: `ok=True`, fail-closed reason: `None`
- v7 state: `live-private-belief-v7`, **3208D**
- v5 candidates: `legal-action-v5`, **318D**
- Candidate kinds: move=4, move_tera=4, switch=5
- Tera candidates: `4`; switch candidates: `5`
- Selected command: `move 1 terastallize`
- Latency: `3772.930399994948` ms (cold standalone replay without the live server's persistent sim-core client)
- Slot validation: `ok=True`; move=8, Tera=4, switch=5; errors=[]

## Remaining Blocker

A force-switch real packet remains recommended coverage before manual recommendation testing. This packet already validates both a normal move decision and Tera legality. Use the existing warm-server measurement (~35–60 ms), rather than this cold standalone replay, for interactive latency expectations.
