// ==UserScript==
// @name         Showdown Local Eval Overlay
// @match        https://play.pokemonshowdown.com/*
// @match        https://china.psim.us/*
// @grant        unsafeWindow
// ==/UserScript==

(function () {
  "use strict";

  const SERVER = "http://127.0.0.1:8765/evaluate";
  const POLL_MS = 500;

  let inFlight = false;
  let requestSeq = 0;
  let lastRenderedSeq = 0;
  let currentRoomKey = null;
  let sentDecisionKeys = new Set();

  function makeOverlay() {
    let box = document.getElementById("local-eval-overlay");
    if (box) return box;

    box = document.createElement("div");
    box.id = "local-eval-overlay";
    box.style.position = "fixed";
    box.style.right = "12px";
    box.style.top = "90px";
    box.style.zIndex = "999999";
    box.style.width = "245px";
    box.style.background = "rgba(20, 20, 20, 0.92)";
    box.style.color = "white";
    box.style.padding = "10px";
    box.style.borderRadius = "10px";
    box.style.fontFamily = "Arial, sans-serif";
    box.style.fontSize = "13px";
    box.style.boxShadow = "0 2px 12px rgba(0,0,0,0.4)";
    box.innerHTML = `
      <div id="eval-title" style="font-weight:bold;margin-bottom:6px;cursor:pointer;"
           title="Click to allow one resend for this decision">
        Local Eval
      </div>
      <div id="eval-status">Waiting for battle...</div>
      <div style="height:14px;background:#555;border-radius:8px;overflow:hidden;margin:8px 0;">
        <div id="eval-bar" style="height:100%;width:50%;background:#4caf50;"></div>
      </div>
      <div id="eval-actions"></div>
    `;
    document.body.appendChild(box);

    document.getElementById("eval-title").addEventListener("click", () => {
      const room = getCurrentRoom();
      const request = getRequest(room);
      const roomId = getRoomId(room);
      const player = request?.side?.id || "unknown-player";
      const turn = getBattleTurn(room);
      const phase = getDecisionPhase(room, request).phase;
      const key = makeDecisionKey(roomId, player, turn, phase);

      sentDecisionKeys.delete(key);
      setStatus(`Manual resend enabled for Turn ${turn ?? "?"} ${phase}.`);
      sendEval();
    });

    return box;
  }

  function setTitle(turn, phase = null) {
    makeOverlay();
    const suffix = turn ? `Turn ${turn}${phase === "force-switch" ? " Switch" : ""}` : "";
    document.getElementById("eval-title").innerText = suffix ? `Local Eval (${suffix})` : "Local Eval";
  }

  function setStatus(text) {
    makeOverlay();
    document.getElementById("eval-status").innerText = text;
  }

  function setActionsHtml(html) {
    makeOverlay();
    document.getElementById("eval-actions").innerHTML = html;
  }

  function getWindow() {
    return typeof unsafeWindow !== "undefined" ? unsafeWindow : window;
  }

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
      return battle.stepQueue.slice(-400).map(x => String(x));
    }

    const lines = [...document.querySelectorAll(".battle-log div, .battle-log p, .battle-log h2")]
      .map(el => el.innerText?.trim())
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
    return pokemon.find(p => p.active) || null;
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
    return pokemon.some(p => p.terastallized || p.teraUsed);
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
      return { ok: false, phase: "none", reason: `Not a battle room: ${roomId}`, turn };
    }

    if (!request) {
      return { ok: false, phase: "none", reason: "No live request yet.", turn };
    }

    if (request.wait) {
      return { ok: false, phase: "none", reason: "Waiting for opponent.", turn };
    }

    if (request.teamPreview) {
      return { ok: false, phase: "team-preview", reason: "Team preview; no eval.", turn };
    }

    const pendingSide = pendingReplacementSide(room);
    const forceSwitch = requestHasForceSwitch(request);

    // The important fix:
    // Pending faint replacement only blocks eval if it is NOT our side.
    // If it is our side and Showdown has forceSwitch/switch buttons, we should evaluate switches.
    if (pendingSide && pendingSide !== player) {
      return {
        ok: false,
        phase: "none",
        reason: `Waiting for ${pendingSide} replacement after faint.`,
        turn,
      };
    }

    if (forceSwitch) {
      const switches = getLegalSwitchActions(request);
      if (!switches.length) {
        return { ok: false, phase: "force-switch", reason: "Forced switch but no switch choices found.", turn };
      }
      return { ok: true, phase: "force-switch", reason: "Forced switch decision.", turn };
    }

    const active = request.active?.[0] || null;
    if (!active) {
      return { ok: false, phase: "none", reason: "No active move request.", turn };
    }

    const activeMon = getActiveSidePokemon(request);
    if (activeMon && conditionIsFainted(activeMon.condition)) {
      return { ok: false, phase: "none", reason: "Active Pokémon is fainted; waiting for replacement.", turn };
    }

    const moves = active.moves || [];
    if (!moves.length) {
      return { ok: false, phase: "none", reason: "No active moves available.", turn };
    }

    return { ok: true, phase: "move", reason: "Regular move decision.", turn };
  }

  async function sendEval() {
    if (inFlight) return;

    const room = getCurrentRoom();

    if (!room) {
      setTitle(null);
      setStatus("No current room found.");
      return;
    }

    const request = getRequest(room);
    const roomId = getRoomId(room);
    const player = request?.side?.id || null;
    const decision = getDecisionPhase(room, request);
    const turn = decision.turn;

    setTitle(turn, decision.phase);

    const roomKey = `${roomId || "unknown-room"}::${player || "unknown-player"}`;
    if (roomKey !== currentRoomKey) {
      currentRoomKey = roomKey;
      sentDecisionKeys = new Set();
      lastRenderedSeq = 0;
    }

    if (!decision.ok) {
      setStatus(decision.reason);
      setActionsHtml(`<div style="color:#aaa;">No eval request sent.</div>`);
      return;
    }

    const decisionKey = makeDecisionKey(roomId, player, turn, decision.phase);
    if (sentDecisionKeys.has(decisionKey)) {
      return;
    }

    const legalActions = getLegalActionsFromRequest(request, decision.phase);

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
      setTitle(turn, decision.phase);
      setStatus(`Evaluating Turn ${turn ?? "?"}${decision.phase === "force-switch" ? " switch" : ""}...`);

      const res = await fetch(SERVER, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();

      if (seq > lastRenderedSeq) {
        lastRenderedSeq = seq;
        renderEval(data, turn, decision.phase);
      }
    } catch (err) {
      renderError(err, turn, decision.phase);
    } finally {
      inFlight = false;
    }
  }

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

  function renderEval(data, turn, phase) {
    makeOverlay();
    setTitle(turn ?? data.turn ?? data.debug?.latest_turn ?? null, phase);

    const p1Raw = data.p1_win_prob ?? 0.5;
    const p2Raw = data.p2_win_prob ?? 0.5;
    const p1 = Math.round(p1Raw * 100);
    const p2 = Math.round(p2Raw * 100);

    document.getElementById("eval-status").innerText =
      `P1 ${p1}% / P2 ${p2}% | ${data.model_type || "model"}`;

    document.getElementById("eval-bar").style.width = `${p1}%`;

    const actions = data.top_actions || [];
    document.getElementById("eval-actions").innerHTML = actions.length
      ? actions.map((a, i) => {
          const method = a.method || "";
          const policyProb = a.policy_prob ?? a.prob ?? null;
          const rankerScore = a.ranker_score ?? null;
          const score = a.final_score ?? a.score ?? null;
          const expectedValue = a.expected_value ?? a.estimated_value ?? null;

          let mainMetric = "";
          if (score !== null && score !== undefined) {
            mainMetric = `score ${Number(score).toFixed(2)}`;
          } else if (rankerScore !== null && rankerScore !== undefined) {
            mainMetric = `ranker ${Number(rankerScore).toFixed(2)}`;
          } else if (policyProb !== null && policyProb !== undefined) {
            mainMetric = `policy ${formatPct(policyProb)}`;
          }

          const policyLine =
            policyProb !== null && policyProb !== undefined
              ? `policy=${formatPct(policyProb)}`
              : "";

          const valueLine =
            expectedValue === null || expectedValue === undefined
              ? ""
              : ` value=${Number(expectedValue).toFixed(3)}`;

          const damageLine = formatDamage(a);

          return `
            <div style="margin-top:6px;">
              <div><strong>${i + 1}. ${a.label}</strong></div>
              <div style="color:#ddd;font-size:12px;">
                ${mainMetric} <span style="color:#aaa;">${method}</span>
              </div>
              <div style="color:#aaa;font-size:11px;">
                ${policyLine} ${score !== null && score !== undefined ? `score=${Number(score).toFixed(3)}` : ""}${valueLine}
              </div>
              ${damageLine ? `<div style="color:#9fd3ff;font-size:11px;">${damageLine}</div>` : ""}
            </div>
          `;
        }).join("")
      : `<div>No action suggestions yet.</div>`;
  }

  function renderError(err, turn, phase) {
    makeOverlay();
    setTitle(turn, phase);
    document.getElementById("eval-status").innerText =
      `Local server not connected${turn ? ` (Turn ${turn})` : ""}.`;
    document.getElementById("eval-actions").innerHTML =
      `<div style="color:#ffb3b3;">${String(err).slice(0, 120)}</div>
       <div style="color:#aaa;margin-top:4px;">Click “Local Eval” to allow one resend for this decision.</div>`;
  }

  makeOverlay();
  setInterval(sendEval, POLL_MS);
  sendEval();
})();