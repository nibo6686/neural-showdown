# Showdown Extension UI + vNext Shadow Display Report

## Purpose and Scope

Improve the existing recommendation-only Showdown userscript overlay
(`Showdown Local Eval Overlay.user.js`) so it is non-obstructive, draggable,
collapsible, and clearer, and add an **opt-in** display of the vNext shadow
recommendation (`/evaluate-vnext-dry-run`). The overlay remains strictly
display-only: it never auto-clicks or auto-submits a Showdown command, and the
user always chooses manually. Normal `/evaluate` behavior is preserved; vNext is
never required for normal use.

## Files Changed

- `Showdown Local Eval Overlay.user.js` — UI rewrite (collapse/pill, drag,
  persistence, recommendation layout, status states, opt-in vNext shadow section).
  Decision/legal-action/log/dedupe/payload logic is preserved verbatim.
- `README.md` — short note on the overlay's collapse/drag and the opt-in vNext
  shadow toggle.
- `artifacts/training_plan/showdown_extension_ui_shadow_mode_report.md` (this report).
- `artifacts/training_plan/diagnostic_training_gate.md` — checklist line added; gate stays closed.

No Python / live-server code changed. The `/evaluate-vnext-dry-run` route and the
default `/evaluate` path are unchanged.

## UI Behavior Changes

1. **Non-obstructive overlay**
   - Replaced the always-open fixed panel with a compact **pill** + expandable
     **panel**. Default state is collapsed (pill only).
   - Collapsed/expanded state persists in `localStorage` (`lev_collapsed`).
   - Outside battle rooms the pill shows `no battle` and the full panel is not
     shown; expanding shows a compact "Not in a battle" message.
   - If a Showdown popup/login/modal element is detected, the panel auto-collapses
     to the pill so it cannot cover login/home/modal/team-builder controls.
2. **Positioning**
   - Panel is **draggable by its header**; position persists in `localStorage`
     (`lev_pos`).
   - Added a **reset-position** control (`⌖`).
   - Lowered `z-index` from `999999` to `9000` so Showdown's own popups render
     above the overlay (we never cover modals).
3. **Recommendation display**
   - One compact **top recommendation** is shown first (highlighted).
   - **Top 3** actions by default; the full list appears when **details** is on.
   - Action list is **scrollable** with a `max-height` (~170px).
   - Damage/debug text is secondary (smaller, greyed) and only shown under details.
4. **Server status (compact)**
   - Pill states: `offline` (red), `waiting`/`team preview` (amber),
     `no battle` (grey), or win% (green) when evaluating.
   - **Manual resend** is now an explicit `↻` button in the header (no longer a
     title click).
5. **vNext shadow display**
   - A `vNext shadow` checkbox (off by default, persisted as `lev_vnext`) enables
     a **secondary** call to `/evaluate-vnext-dry-run` alongside the normal eval.
   - Shows the vNext recommended command, selected candidate, and
     **candidate kind counts** (`move / tera / switch`), plus a latency value with
     a **slow warning** (orange) when `total_ms > 1500`.
   - On fail-closed, shows the compact `fallback: <reason>` (+ missing fields).
   - If the route is disabled (`vnext_inference_disabled`) or missing (HTTP 404),
     it shows a small badge and stops sending (no spam) until the toggle is
     re-enabled.
   - The section is labeled "display only — not submitted".

## Opt-In vNext Display Behavior

- vNext shadow requests are sent **only** when the user enables the toggle, the
  route is available, and the decision is actionable (same gating + dedupe as the
  main eval). When disabled/missing it degrades silently to a small badge.
- The vNext recommendation is informational; the overlay never executes it.

## Request Payload Behavior

- **Unchanged** payload contract (`room_id`, `url`, `player`, `turn`,
  `decision_phase`, `request`, `log`, `legal_actions`).
- Dedupe by decision key is preserved; the vNext shadow request piggybacks on the
  same once-per-actionable-decision cadence, so request volume to the server does
  not increase per poll (at most one extra request per decision, only when the
  toggle is on).
- `localStorage` stores only UI state (collapsed, position, toggles) — never
  cookies, tokens, session IDs, or payloads. `fetch` does not send credentials.

## Auto-Action Behavior

- **None added.** The overlay has no code path that clicks Showdown buttons or
  submits a choice. Both the normal and vNext sections are display-only.

## Manual Checks (documented; no browser-extension test harness exists)

The userscript passes `node --check` (syntax valid). Behavioral checks to run in
the browser with the userscript installed:

- [ ] Login page: panel collapsed to pill; login buttons not covered.
- [ ] Home page: pill only; main content not covered.
- [ ] Battle, waiting for opponent: pill shows `waiting`, compact status.
- [ ] Regular move decision: top recommendation + top-3 appear.
- [ ] Force-switch decision: switch recommendations appear.
- [ ] Server offline: pill `offline`, compact error with `↻` hint.
- [ ] Drag the panel, refresh: position persists.
- [ ] Collapse/expand, refresh: state persists.
- [ ] Normal `/evaluate` still renders win% + actions with vNext toggle off.
- [ ] vNext toggle off: no vNext section requests; UI unaffected.
- [ ] vNext toggle on, route enabled (`NEURAL_VNEXT_INFERENCE=1`): shadow
      recommendation + kind counts shown; slow-latency warning appears on cold
      calls.
- [ ] vNext toggle on, route disabled: small "disabled" badge, no spam.
- [ ] No Showdown command is auto-submitted in any case.

## Known Limitations

- vNext shadow cold latency is high (~3s; impact resolution dominates), so the
  shadow section can lag the main eval by a few seconds on the first call of a
  decision; flagged with a slow-latency warning. Warm-client latency is still to
  be measured/optimized.
- Modal/login detection uses a heuristic selector set; client updates could
  change selectors. The low z-index + collapse-on-modal behavior is the primary
  safeguard.
- Switch/move slot indexing in serialized vNext commands is display-only and not
  yet validated against live Showdown choice acceptance.

## Safety Confirmations

- No command sent to Showdown; no battle run by the model; no auto-click/submit.
- Live defaults unchanged; no model trained; no checkpoint promoted.
- Gate remains closed.

## Recommended Next Task

Measure warm-client vNext shadow latency from the live server using real
extension requests, then optimize impact resolution (persistent sim-core client /
batched per-candidate damage calls) if warm latency is still too slow for
practical manual recommendation use.
