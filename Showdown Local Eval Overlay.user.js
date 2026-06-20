// ==UserScript==
// @name         Showdown Local Eval Overlay
// @match        https://play.pokemonshowdown.com/*
// @match        https://china.psim.us/*
// @grant        unsafeWindow
// ==/UserScript==
//
// Recommendation-only overlay. It calls a local eval server and DISPLAYS
// suggestions. It NEVER auto-clicks or auto-submits a Showdown command; the user
// always chooses manually. An optional vNext "shadow" recommendation is shown for
// comparison only when the local server route is enabled.

(function () {
  "use strict";

  const SERVER_BASE = "http://127.0.0.1:8765";
  const SERVER_EVAL = `${SERVER_BASE}/evaluate`;
  const SERVER_VNEXT = `${SERVER_BASE}/evaluate-vnext-dry-run`;
  const POLL_MS = 500;
  const Z_INDEX = 9000; // below Showdown's own popups/modals so we never cover them
  const VNEXT_SLOW_MS = 1500;

  const LS = {
    collapsed: "lev_collapsed",
    pos: "lev_pos",
    vnext: "lev_vnext",
    details: "lev_details",
  };

  let inFlight = false;
  let requestSeq = 0;
  let lastRenderedSeq = 0;
  let currentRoomKey = null;
  let sentDecisionKeys = new Set();
  let vnextRouteDisabled = false; // set once the route reports disabled/missing
  let lastDecision = { turn: null, phase: "none" };

  // ---- localStorage helpers (UI state only; never payloads/cookies/tokens) ----
  function lsGet(key, fallback) {
    try {
      const v = localStorage.getItem(key);
      return v === null ? fallback : v;
    } catch (_) {
      return fallback;
    }
  }
  function lsSet(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch (_) {}
  }
  function isCollapsed() {
    return lsGet(LS.collapsed, "1") === "1";
  }
  function setCollapsed(v) {
    lsSet(LS.collapsed, v ? "1" : "0");
    applyVisibility();
  }
  function vnextEnabled() {
    return lsGet(LS.vnext, "0") === "1";
  }
  function detailsOpen() {
    return lsGet(LS.details, "0") === "1";
  }

  function getWindow() {
    return typeof unsafeWindow !== "undefined" ? unsafeWindow : window;
  }

  // ---------------------------- UI construction ----------------------------
  function el(id) {
    return document.getElementById(id);
  }

  function buildPanel() {
    if (el("local-eval-overlay")) return el("local-eval-overlay");
    if (!document.body) return null;

    const box = document.createElement("div");
    box.id = "local-eval-overlay";
    box.style.position = "fixed";
    box.style.zIndex = String(Z_INDEX);
    box.style.fontFamily = "Arial, sans-serif";
    box.style.fontSize = "13px";

    const pos = readPos();
    box.style.left = pos.left;
    box.style.top = pos.top;
    box.style.right = "auto";

    box.innerHTML = `
      <div id="eval-pill" style="
          display:inline-flex;align-items:center;gap:6px;cursor:pointer;
          background:rgba(20,20,20,0.92);color:#fff;padding:5px 9px;border-radius:14px;
          box-shadow:0 1px 6px rgba(0,0,0,0.4);user-select:none;white-space:nowrap;">
        <span style="width:8px;height:8px;border-radius:50%;background:#4caf50;" id="eval-pill-dot"></span>
        <span id="eval-pill-text">Eval</span>
        <span style="color:#9ad;">▸</span>
      </div>
      <div id="eval-panel" style="
          display:none;width:250px;background:rgba(20,20,20,0.94);color:#fff;
          padding:8px 10px 10px;border-radius:10px;box-shadow:0 2px 12px rgba(0,0,0,0.45);">
        <div id="eval-header" style="display:flex;align-items:center;gap:6px;cursor:move;user-select:none;margin-bottom:6px;">
          <strong id="eval-title" style="flex:1;font-size:13px;">Local Eval</strong>
          <button id="eval-resend" title="Resend this decision" style="${btnStyle()}">↻</button>
          <button id="eval-reset" title="Reset panel position" style="${btnStyle()}">⌖</button>
          <button id="eval-collapse" title="Collapse" style="${btnStyle()}">▾</button>
        </div>
        <div id="eval-status" style="color:#ddd;">Waiting for battle…</div>
        <div style="height:12px;background:#555;border-radius:7px;overflow:hidden;margin:7px 0;">
          <div id="eval-bar" style="height:100%;width:50%;background:#4caf50;"></div>
        </div>
        <div id="eval-top" style="margin:4px 0;"></div>
        <div id="eval-actions" style="max-height:170px;overflow-y:auto;"></div>
        <div style="margin-top:6px;display:flex;gap:10px;align-items:center;">
          <label style="cursor:pointer;color:#bbb;font-size:11px;">
            <input type="checkbox" id="eval-details-toggle"> details
          </label>
          <label style="cursor:pointer;color:#bbb;font-size:11px;" title="Compare a vNext (v7/v5) shadow recommendation (display only)">
            <input type="checkbox" id="eval-vnext-toggle"> vNext shadow
          </label>
        </div>
        <div id="eval-vnext" style="margin-top:6px;border-top:1px solid #333;padding-top:6px;display:none;"></div>
      </div>
    `;
    document.body.appendChild(box);

    el("eval-pill").addEventListener("click", () => setCollapsed(false));
    el("eval-collapse").addEventListener("click", (e) => {
      e.stopPropagation();
      setCollapsed(true);
    });
    el("eval-resend").addEventListener("click", (e) => {
      e.stopPropagation();
      manualResend();
    });
    el("eval-reset").addEventListener("click", (e) => {
      e.stopPropagation();
      resetPos();
    });

    const detailsToggle = el("eval-details-toggle");
    detailsToggle.checked = detailsOpen();
    detailsToggle.addEventListener("change", () => {
      lsSet(LS.details, detailsToggle.checked ? "1" : "0");
    });

    const vnextToggle = el("eval-vnext-toggle");
    vnextToggle.checked = vnextEnabled();
    vnextToggle.addEventListener("change", () => {
      lsSet(LS.vnext, vnextToggle.checked ? "1" : "0");
      vnextRouteDisabled = false; // allow a re-probe after the user re-enables
      const section = el("eval-vnext");
      if (section) {
        section.style.display = vnextToggle.checked ? "block" : "none";
        if (vnextToggle.checked) section.innerHTML = `<div style="color:#9ad;">vNext shadow: waiting for next decision…</div>`;
      }
    });

    enableDrag(el("eval-header"), box);
    applyVisibility();
    return box;
  }

  function btnStyle() {
    return "background:#333;color:#ddd;border:none;border-radius:5px;padding:1px 6px;cursor:pointer;font-size:12px;";
  }

  // ------------------------------ positioning ------------------------------
  function readPos() {
    try {
      const raw = JSON.parse(lsGet(LS.pos, "null"));
      if (raw && typeof raw.left === "string" && typeof raw.top === "string") return raw;
    } catch (_) {}
    return { left: `${Math.max(0, window.innerWidth - 270)}px`, top: "90px" };
  }
  function resetPos() {
    lsSet(LS.pos, "null");
    const box = el("local-eval-overlay");
    if (box) {
      const def = readPos();
      box.style.left = def.left;
      box.style.top = def.top;
    }
  }
  function enableDrag(handle, box) {
    let startX = 0, startY = 0, originLeft = 0, originTop = 0, dragging = false;
    handle.addEventListener("mousedown", (e) => {
      dragging = true;
      startX = e.clientX;
      startY = e.clientY;
      const rect = box.getBoundingClientRect();
      originLeft = rect.left;
      originTop = rect.top;
      e.preventDefault();
    });
    document.addEventListener("mousemove", (e) => {
      if (!dragging) return;
      const left = Math.max(0, Math.min(window.innerWidth - 40, originLeft + (e.clientX - startX)));
      const top = Math.max(0, Math.min(window.innerHeight - 20, originTop + (e.clientY - startY)));
      box.style.left = `${left}px`;
      box.style.top = `${top}px`;
      box.style.right = "auto";
    });
    document.addEventListener("mouseup", () => {
      if (!dragging) return;
      dragging = false;
      lsSet(LS.pos, JSON.stringify({ left: box.style.left, top: box.style.top }));
    });
  }

  // --------------------- visibility / non-obstruction ----------------------
  function showdownModalOpen() {
    // Avoid covering login/name/popups. Showdown popups vary by client; check a
    // broad set and bail out (collapse) if any blocking overlay is present.
    return !!document.querySelector(
      ".ps-overlay, .ps-popup, .pfx-overlay, [data-popup], .ps-room-opaque .login, button[name='login']"
    );
  }

  function applyVisibility() {
    const box = el("local-eval-overlay");
    if (!box) return;
    const pill = el("eval-pill");
    const panel = el("eval-panel");

    const modal = showdownModalOpen();
    const collapsed = isCollapsed() || modal; // auto-collapse near modals/login

    pill.style.display = collapsed ? "inline-flex" : "none";
    panel.style.display = collapsed ? "none" : "block";

    const vnextSection = el("eval-vnext");
    if (vnextSection) vnextSection.style.display = vnextEnabled() ? "block" : "none";
  }

  function setPill(text, color) {
    buildPanel();
    const t = el("eval-pill-text");
    const dot = el("eval-pill-dot");
    if (t) t.innerText = text;
    if (dot && color) dot.style.background = color;
  }

  function setTitle(turn, phase = null) {
    buildPanel();
    const suffix = turn ? `Turn ${turn}${phase === "force-switch" ? " Switch" : ""}` : "";
    const title = el("eval-title");
    if (title) title.innerText = suffix ? `Local Eval (${suffix})` : "Local Eval";
  }

  function setStatus(text) {
    buildPanel();
    const s = el("eval-status");
    if (s) s.innerText = text;
  }

  function setActionsHtml(topHtml, listHtml) {
    buildPanel();
    if (el("eval-top")) el("eval-top").innerHTML = topHtml || "";
    if (el("eval-actions")) el("eval-actions").innerHTML = listHtml || "";
  }

  // --------------------- room / request / log helpers ----------------------
  function getCurrentRoom() {
    return getWindow().app?.curRoom || null;
  }

  function getRoomId(room) {
    if (room?.id) return room.id;
    if (room?.battle?.id) return room.battle.id;
    const hash = location.hash.replace(/^#/, "");
    if (hash) return hash;
    const pathBattle = location.pathname.match(/battle-[^/]+/);
    if (pathBattle) return pathBattle[0];
    return "unknown-room";
  }

  function getRequest(room) {
    return room?.request || room?.battle?.request || null;
  }

  function getBattleLog(room) {
    const battle = room?.battle;
    if (battle?.stepQueue && Array.isArray(battle.stepQueue)) {
      return battle.stepQueue.slice(-400).map((x) => String(x));
    }
    const lines = [...document.querySelectorAll(".battle-log div, .battle-log p, .battle-log h2")]
      .map((elm) => elm.innerText?.trim())
      .filter(Boolean);
    return lines.slice(-400);
  }

  function getBattleTurn(room) {
    const battleTurn = room?.battle?.turn;
    if (Number.isFinite(Number(battleTurn)) && Number(battleTurn) > 0) {
      return Number(battleTurn);
    }
    const lines = getBattleLog(room);
    for (let i = lines.length - 1; i >= 0; i--) {
      const line = String(lines[i]);
      let m = line.match(/^\|turn\|(\d+)/);
      if (m) return Number(m[1]);
      m = line.match(/^Turn\s+(\d+)/i);
      if (m) return Number(m[1]);
    }
    return null;
  }

  function makeDecisionKey(roomId, player, turn, phase) {
    return `${roomId || "unknown-room"}::${player || "unknown-player"}::turn-${turn ?? "unknown"}::${phase || "unknown-phase"}`;
  }

  function isBattleRoom(roomId) {
    return String(roomId || "").includes("battle");
  }

  function conditionIsFainted(condition) {
    return String(condition || "").includes("fnt");
  }

  function getActiveSidePokemon(request) {
    const pokemon = request?.side?.pokemon || [];
    return pokemon.find((p) => p.active) || null;
  }

  function requestHasForceSwitch(request) {
    const fs = request?.forceSwitch;
    if (fs === true) return true;
    if (Array.isArray(fs) && fs.some(Boolean)) return true;
    return false;
  }

  function sideFromProtocolIdent(text) {
    const m = String(text || "").match(/\|(?:faint|switch|drag)\|p([12])a?:/);
    return m ? `p${m[1]}` : null;
  }

  function pendingReplacementSide(room) {
    const lines = getBattleLog(room);
    if (!lines.length) return null;
    let lastTurnIdx = -1;
    for (let i = lines.length - 1; i >= 0; i--) {
      if (/^\|turn\|\d+/.test(lines[i]) || /^Turn\s+\d+/i.test(lines[i])) {
        lastTurnIdx = i;
        break;
      }
    }
    const recent = lastTurnIdx >= 0 ? lines.slice(lastTurnIdx + 1) : lines.slice(-80);
    const pending = new Set();
    for (const raw of recent) {
      const line = String(raw || "");
      if (line.startsWith("|faint|")) {
        const side = sideFromProtocolIdent(line);
        if (side) pending.add(side);
      }
      if (line.startsWith("|switch|") || line.startsWith("|drag|")) {
        const side = sideFromProtocolIdent(line);
        if (side) pending.delete(side);
      }
      if (/^\|turn\|\d+/.test(line)) {
        pending.clear();
      }
    }
    return pending.size ? [...pending][0] : null;
  }

  function sideHasUsedTera(request) {
    const pokemon = request?.side?.pokemon || [];
    return pokemon.some((p) => p.terastallized || p.teraUsed);
  }

  function getCanTeraInfo(request) {
    const active = request?.active?.[0];
    const activeMon = getActiveSidePokemon(request);
    const teraUsed = sideHasUsedTera(request);
    const raw =
      active?.canTerastallize ??
      active?.canTera ??
      activeMon?.canTerastallize ??
      activeMon?.canTera ??
      false;
    const canTera = !!raw && !teraUsed;
    const teraType =
      typeof raw === "string"
        ? raw
        : active?.teraType || active?.tera_type || activeMon?.teraType || activeMon?.tera_type || null;
    return { canTera, teraType, teraUsed };
  }

  function getLegalSwitchActions(request) {
    const actions = [];
    let switchIndex = 0;
    const pokemon = request?.side?.pokemon || [];
    pokemon.forEach((p, i) => {
      const condition = p.condition || "";
      const active = !!p.active;
      const fainted = conditionIsFainted(condition);
      if (!active && !fainted) {
        actions.push({
          index: 8 + switchIndex,
          kind: "switch",
          label: p.details || p.ident || `Switch ${i + 1}`,
          choice: `switch ${i + 1}`,
          slot: i + 1,
          species: p.details || p.ident || null,
          disabled: false,
          is_tera_action: false,
          tera_type: null,
        });
        switchIndex++;
      }
    });
    return actions;
  }

  function getLegalActionsFromRequest(request, phase) {
    const actions = [];
    if (!request) return actions;
    if (phase === "force-switch") {
      return getLegalSwitchActions(request);
    }
    const active = request.active?.[0] || null;
    const trapped = !!(active?.trapped || active?.maybeTrapped);
    const { canTera, teraType } = getCanTeraInfo(request);
    const moves = active?.moves || [];
    moves.forEach((m, i) => {
      const moveName = m.move || m.name || m.id || `Move ${i + 1}`;
      const disabled = !!m.disabled || Number(m.pp) === 0;
      actions.push({
        index: i,
        kind: "move",
        label: moveName,
        choice: `move ${i + 1}`,
        move: moveName,
        slot: i + 1,
        disabled,
        pp: m.pp,
        maxpp: m.maxpp,
        target: m.target,
        is_tera_action: false,
        tera_type: null,
      });
      if (canTera && !disabled) {
        actions.push({
          index: 4 + i,
          kind: "move_tera",
          label: `${moveName} (Tera)`,
          choice: `move ${i + 1} terastallize`,
          move: moveName,
          slot: i + 1,
          disabled: false,
          pp: m.pp,
          maxpp: m.maxpp,
          target: m.target,
          is_tera_action: true,
          tera_type: teraType,
        });
      }
    });
    if (!trapped) {
      actions.push(...getLegalSwitchActions(request));
    }
    return actions;
  }

  function getDecisionPhase(room, request) {
    const roomId = getRoomId(room);
    const turn = getBattleTurn(room);
    const player = request?.side?.id || null;
    if (!isBattleRoom(roomId)) {
      return { ok: false, phase: "none", reason: `Not a battle room.`, turn };
    }
    if (!request) {
      return { ok: false, phase: "none", reason: "No live request yet.", turn };
    }
    // Our live force-switch request takes priority over simultaneous opponent
    // replacement/wait state (for example, both active Pokémon fainting).
    const forceSwitch = requestHasForceSwitch(request);
    if (forceSwitch) {
      const switches = getLegalSwitchActions(request);
      if (!switches.length) {
        return { ok: false, phase: "force-switch", reason: "Forced switch but no choices.", turn };
      }
      return { ok: true, phase: "force-switch", reason: "Forced switch decision.", turn };
    }
    if (request.wait) {
      return { ok: false, phase: "none", reason: "Waiting for opponent.", turn };
    }
    if (request.teamPreview) {
      return { ok: false, phase: "team-preview", reason: "Team preview; no eval.", turn };
    }
    const pendingSide = pendingReplacementSide(room);
    if (pendingSide && pendingSide !== player) {
      return { ok: false, phase: "none", reason: `Waiting for ${pendingSide} replacement.`, turn };
    }
    const active = request.active?.[0] || null;
    if (!active) {
      return { ok: false, phase: "none", reason: "No active move request.", turn };
    }
    const activeMon = getActiveSidePokemon(request);
    if (activeMon && conditionIsFainted(activeMon.condition)) {
      return { ok: false, phase: "none", reason: "Active fainted; waiting.", turn };
    }
    const moves = active.moves || [];
    if (!moves.length) {
      return { ok: false, phase: "none", reason: "No active moves available.", turn };
    }
    return { ok: true, phase: "move", reason: "Regular move decision.", turn };
  }

  // ------------------------------ requests ---------------------------------
  function manualResend() {
    const room = getCurrentRoom();
    const request = getRequest(room);
    const roomId = getRoomId(room);
    const player = request?.side?.id || "unknown-player";
    const turn = getBattleTurn(room);
    const phase = getDecisionPhase(room, request).phase;
    const key = makeDecisionKey(roomId, player, turn, phase);
    sentDecisionKeys.delete(key);
    setStatus(`Manual resend for Turn ${turn ?? "?"} ${phase}.`);
    sendEval();
  }

  async function sendEval() {
    buildPanel();
    applyVisibility();
    if (inFlight) return;

    const room = getCurrentRoom();
    const roomId = getRoomId(room);

    if (!room || !isBattleRoom(roomId)) {
      setPill("no battle", "#888");
      setTitle(null);
      setStatus("Not in a battle.");
      setActionsHtml("", `<div style="color:#aaa;">Open a battle to see recommendations.</div>`);
      return;
    }

    const request = getRequest(room);
    const player = request?.side?.id || null;
    const decision = getDecisionPhase(room, request);
    const turn = decision.turn;
    lastDecision = { turn, phase: decision.phase };
    setTitle(turn, decision.phase);

    const roomKey = `${roomId || "unknown-room"}::${player || "unknown-player"}`;
    if (roomKey !== currentRoomKey) {
      currentRoomKey = roomKey;
      sentDecisionKeys = new Set();
      lastRenderedSeq = 0;
    }

    if (!decision.ok) {
      setPill(decision.phase === "team-preview" ? "team preview" : "waiting", "#c9a227");
      setStatus(decision.reason);
      setActionsHtml("", `<div style="color:#aaa;">No eval request sent.</div>`);
      return;
    }

    const decisionKey = makeDecisionKey(roomId, player, turn, decision.phase);
    if (sentDecisionKeys.has(decisionKey)) {
      return;
    }

    const legalActions = getLegalActionsFromRequest(request, decision.phase);
    // Payload mirrors the existing contract (no cookies/tokens/session data).
    const payload = {
      room_id: roomId,
      url: location.href,
      player: player,
      turn: turn,
      decision_phase: decision.phase,
      request: request,
      log: getBattleLog(room),
      legal_actions: legalActions,
    };

    sentDecisionKeys.add(decisionKey);
    const seq = ++requestSeq;
    inFlight = true;

    try {
      setPill(`T${turn ?? "?"}`, "#4caf50");
      setStatus(`Evaluating Turn ${turn ?? "?"}${decision.phase === "force-switch" ? " switch" : ""}…`);
      const res = await fetch(SERVER_EVAL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (seq > lastRenderedSeq) {
        lastRenderedSeq = seq;
        renderEval(data, turn, decision.phase);
      }
      // Optional vNext shadow request: only on actionable, deduped decisions.
      if (vnextEnabled() && !vnextRouteDisabled && decision.ok) {
        await sendVNextShadow(payload, turn, decision.phase);
      }
    } catch (err) {
      renderError(err, turn, decision.phase);
    } finally {
      inFlight = false;
    }
  }

  async function sendVNextShadow(payload, turn, phase) {
    const section = el("eval-vnext");
    if (section) section.innerHTML = `<div style="color:#9ad;">vNext shadow: evaluating…</div>`;
    try {
      const res = await fetch(SERVER_VNEXT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (res.status === 404) {
        vnextRouteDisabled = true;
        renderVNextBadge("route unavailable");
        return;
      }
      const data = await res.json();
      if (data && data.fallback_reason === "vnext_inference_disabled") {
        vnextRouteDisabled = true;
        renderVNextBadge("disabled (set NEURAL_VNEXT_INFERENCE=1)");
        return;
      }
      renderVNext(data);
    } catch (err) {
      renderVNextBadge("server error");
    }
  }

  // ------------------------------ rendering --------------------------------
  function formatPct(x) {
    if (x === null || x === undefined || Number.isNaN(Number(x))) return "";
    return `${(Number(x) * 100).toFixed(1)}%`;
  }

  function formatDamage(a) {
    const method = a.damage_method || a.diagnostics?.damage?.damage_method || "";
    const avg = a.average_percent ?? a.diagnostics?.damage?.average_percent;
    const immune = a.immune ?? a.diagnostics?.damage?.immune;
    if (!method && avg === undefined && immune === undefined) return "";
    const bits = [];
    if (method) bits.push(method);
    if (immune) bits.push("immune");
    if (avg !== undefined && avg !== null) bits.push(`avg ${Number(avg).toFixed(1)}%`);
    return bits.join(" | ");
  }

  function actionMainMetric(a) {
    const score = a.final_score ?? a.score ?? null;
    const rankerScore = a.ranker_score ?? null;
    const policyProb = a.policy_prob ?? a.prob ?? null;
    if (score !== null && score !== undefined) return `score ${Number(score).toFixed(2)}`;
    if (rankerScore !== null && rankerScore !== undefined) return `ranker ${Number(rankerScore).toFixed(2)}`;
    if (policyProb !== null && policyProb !== undefined) return `policy ${formatPct(policyProb)}`;
    return "";
  }

  function renderEval(data, turn, phase) {
    buildPanel();
    setTitle(turn ?? data.turn ?? data.debug?.latest_turn ?? null, phase);

    const p1 = Math.round((data.p1_win_prob ?? 0.5) * 100);
    const p2 = Math.round((data.p2_win_prob ?? 0.5) * 100);
    setStatus(`P1 ${p1}% / P2 ${p2}% | ${data.model_type || "model"}`);
    if (el("eval-bar")) el("eval-bar").style.width = `${p1}%`;
    setPill(`${p1}%`, "#4caf50");

    const actions = data.top_actions || [];
    if (!actions.length) {
      setActionsHtml(`<div style="color:#aaa;">No action suggestions yet.</div>`, "");
      return;
    }

    const top = actions[0];
    const topHtml = `
      <div style="background:#1f3a1f;border-radius:8px;padding:6px 8px;">
        <div style="font-size:11px;color:#9f9;">recommended</div>
        <div style="font-weight:bold;">${top.label ?? "?"}</div>
        <div style="color:#cfc;font-size:11px;">${actionMainMetric(top)} <span style="color:#9a9;">${top.method || ""}</span></div>
      </div>`;

    const showDetails = detailsOpen();
    const visible = showDetails ? actions : actions.slice(0, 3);
    const listHtml = visible
      .map((a, i) => {
        const metric = actionMainMetric(a);
        const damageLine = showDetails ? formatDamage(a) : "";
        const detailLine =
          showDetails && (a.policy_prob ?? a.prob) != null
            ? `<div style="color:#888;font-size:10px;">policy=${formatPct(a.policy_prob ?? a.prob)}</div>`
            : "";
        return `
          <div style="margin-top:5px;border-top:1px solid #2a2a2a;padding-top:4px;">
            <div><strong>${i + 1}. ${a.label ?? "?"}</strong></div>
            <div style="color:#ddd;font-size:11px;">${metric} <span style="color:#999;">${a.method || ""}</span></div>
            ${damageLine ? `<div style="color:#9fd3ff;font-size:10px;">${damageLine}</div>` : ""}
            ${detailLine}
          </div>`;
      })
      .join("");
    setActionsHtml(topHtml, listHtml);
  }

  function renderVNextBadge(text) {
    const section = el("eval-vnext");
    if (!section) return;
    section.innerHTML = `<div style="color:#888;font-size:11px;">vNext shadow: <span style="color:#bbb;">${text}</span></div>`;
  }

  function renderVNext(data) {
    const section = el("eval-vnext");
    if (!section) return;
    if (!data || typeof data !== "object") {
      renderVNextBadge("no response");
      return;
    }
    const counts = data.candidate_kind_counts || {};
    const countLine = `move ${counts.move ?? 0} / tera ${counts.move_tera ?? 0} / switch ${counts.switch ?? 0}`;
    const totalMs = data.latency_ms?.total_ms;
    const slow =
      typeof totalMs === "number" && totalMs > VNEXT_SLOW_MS
        ? `<span style="color:#ffb35c;"> (slow ${Math.round(totalMs)}ms)</span>`
        : typeof totalMs === "number"
        ? `<span style="color:#888;"> ${Math.round(totalMs)}ms</span>`
        : "";

    if (data.ok) {
      const sel = data.selected || {};
      section.innerHTML = `
        <div style="font-size:11px;color:#9ad;">vNext shadow${slow}</div>
        <div style="font-weight:bold;">→ ${data.choice ?? "?"}</div>
        <div style="color:#cdd;font-size:11px;">${sel.label ?? ""} <span style="color:#9a9;">${sel.kind ?? ""}</span></div>
        <div style="color:#999;font-size:10px;">${countLine}</div>
        <div style="color:#666;font-size:10px;">display only — not submitted</div>`;
    } else {
      section.innerHTML = `
        <div style="font-size:11px;color:#9ad;">vNext shadow${slow}</div>
        <div style="color:#ffb3b3;font-size:11px;">fallback: ${data.fallback_reason || "unavailable"}</div>
        ${data.missing_fields && data.missing_fields.length ? `<div style="color:#caa;font-size:10px;">missing: ${data.missing_fields.join(", ")}</div>` : ""}
        <div style="color:#999;font-size:10px;">${countLine}</div>`;
    }
  }

  function renderError(err, turn, phase) {
    buildPanel();
    setTitle(turn, phase);
    setPill("offline", "#d33");
    setStatus(`Local server not connected${turn ? ` (Turn ${turn})` : ""}.`);
    setActionsHtml(
      "",
      `<div style="color:#ffb3b3;font-size:11px;">${String(err).slice(0, 120)}</div>
       <div style="color:#aaa;font-size:11px;margin-top:4px;">Use ↻ to resend this decision.</div>`
    );
  }

  // -------------------------------- boot -----------------------------------
  function boot() {
    if (!document.body) {
      setTimeout(boot, 200);
      return;
    }
    buildPanel();
    setInterval(() => {
      applyVisibility();
      sendEval();
    }, POLL_MS);
    sendEval();
  }
  boot();
})();
