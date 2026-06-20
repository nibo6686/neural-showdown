# Manual vNext Recommendation Test Plan

## Scope

Run a short, display-only comparison of the existing v2/v3 recommendation and
the opt-in vNext shadow recommendation on real Showdown decisions. The user
manually chooses every action. No command is submitted by the model or overlay.

## Launch

From the repository root, restart the live eval server with vNext shadow enabled:

```powershell
$env:NEURAL_VNEXT_INFERENCE='1'
.\scripts\run_windows.ps1 -Action live-eval -SimCoreMode native
```

`NEURAL_CAPTURE_EVALUATE_PAYLOADS=1` is optional and only needed to capture up to
three sanitized packets for later replay. It is not required for this manual test.

## Browser Overlay

1. Keep the existing userscript/browser extension enabled.
2. Open a Showdown battle and expand the draggable recommendation overlay.
3. Enable the **vNext shadow** checkbox. It is off by default.
4. At each decision, compare the normal v2/v3 recommendation with the vNext
   shadow recommendation.
5. Choose the actual Showdown action manually using the visible battle controls.

## Decisions to Cover

Aim for several real decisions, including:

- a normal move decision;
- a decision where Tera is legal;
- a decision where switching is available;
- optionally, a forced-switch decision (the remaining packet-validation gap).

One decision may cover multiple cases, such as a normal move with Tera and
switching available.

## Record Per Decision

Record one row per decision:

| Field | Record |
| --- | --- |
| Turn / phase | Turn number and move or force-switch phase |
| v2/v3 recommendation | Displayed recommendation |
| vNext recommendation | Displayed shadow recommendation |
| Candidate kinds/counts | Move, Tera-move and switch counts |
| Selected command | Exact vNext command string |
| Latency | Displayed or observed shadow latency |
| UI match | Whether command slot/type matches visible Showdown buttons |
| Sanity | Brief judgment: sane, questionable, or clearly wrong |
| Followed manually | Yes/no; the user still clicks the action |
| Outcome notes | Immediate tactical result or relevant observation |

## Safety and Stop Rules

- The user manually chooses and clicks every action.
- Do not enable auto-clicking or automatic command submission.
- Stop if vNext repeatedly fails closed instead of producing a recommendation.
- Stop if latency becomes disruptive to normal play.
- Stop immediately if any move, Tera or switch slot appears inconsistent with
  the visible Showdown controls.
- Keep `NEURAL_VNEXT_INFERENCE` opt-in; do not change live defaults or promote
  the checkpoint.

## Success Criteria

This phase succeeds when:

- several real decisions display both recommendation paths correctly;
- warm vNext latency remains interactive, consistent with the measured
  approximately 35–60 ms range;
- `move <slot>`, `move <slot> terastallize`, and `switch <slot>` strings match
  the visible Showdown controls whenever those action types appear;
- no command is sent automatically;
- the overlay causes no crashes, blocked controls, or disruptive UI behavior.

Recommendation quality observations are evidence for later review, not approval
for automatic play or checkpoint promotion.

## Remaining Blocker

Force-switch packet validation remains optional but recommended if it has not
yet been captured. The diagnostic/training gate stays closed throughout this
display-only test.
