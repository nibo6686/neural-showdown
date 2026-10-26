'use strict';
// Builds docs/status/index.html from git history, the knowledge registry and
// docs/roadmap/status.json. Usage: node tools/status/build_status.cjs
const fs = require('node:fs');
const path = require('node:path');
const {execFileSync} = require('node:child_process');

const root = path.resolve(__dirname, '../..');
const REGISTRY = 'docs/contracts/knowledge-coverage.json';
const START = 'f316a15'; // first lean-plan commit, 2026-10-16
const git = (...args) => execFileSync('git', args, {cwd: root, encoding: 'utf8', maxBuffer: 1 << 28, stdio: ['ignore', 'pipe', 'ignore']}).trim();
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'})[c]);
const status = JSON.parse(fs.readFileSync(path.join(root, 'docs/roadmap/status.json'), 'utf8'));

const FAMILIES = {
  K01: 'Team roster and positions', K02: 'Moves known and used', K03: 'Stats, EVs, IVs',
  K04: 'Pokemon details (level, gender, shiny, ball)', K05: 'HP and fainting', K06: 'Status timing (sleep, toxic counters)',
  K07: 'PP', K08: 'Move restrictions (disabled, trapped, locked)', K09: 'Stat boosts',
  K10: 'Lasting volatiles (Substitute, Leech Seed, Taunt...)', K11: 'Single-turn effects (Protect...)',
  K12: 'Single-move effects (Destiny Bond...)', K13: 'Side conditions (hazards, screens, Tailwind)',
  K14: 'Weather, terrain and field, with turns left', K15: 'Pending effects (Future Sight, Wish)',
  K16: 'Form, types, Tera, Transform', K17: 'Appearance and Illusion reveal', K18: 'Items', K19: 'Abilities',
  K20: 'Decision-point kind (normal, forced switch, end)'
};

// Registry row -> owning slice, following the plan's remaining-slice table
// (LONG-TERM-PLAN.md, Phase 1). Adopted rows map to where they would belong.
function slice(r) {
  const own = r.perspective === 'own';
  switch (r.family) {
    case 'K07': case 'K08': return 'W1';
    case 'K02': return r.property === 'move_execution' ? 'W7.1' : 'W1';
    case 'K01': case 'K17': return 'W3.3';
    case 'K03': case 'K04': return own && r.context === 'original' ? 'W2.1' : 'W3.4';
    case 'K16': return 'W3.4';
    case 'K05': case 'K09': return 'W4.1';
    case 'K06': return 'W4.2';
    case 'K18': return 'W5.1';
    case 'K19': return 'W5.2';
    case 'K20': return 'W2.1';
    case 'K13': return 'W6.1';
    case 'K14': return 'W6.2';
    case 'K15': return 'W6.4';
    default: return 'W6.3'; // K10-K12
  }
}
const workstream = r => slice(r).split('.')[0];

// --- git history -----------------------------------------------------------
const commits = git('log', '--reverse', '--format=%h%x09%cI%x09%s', `${START}^..HEAD`).split('\n')
  .map(line => { const [hash, date, subject] = line.split('\t'); return {hash, date: new Date(date), subject}; });
const head = commits[commits.length - 1];
const earlier = Number(git('rev-list', '--count', `${START}^`));

function registryAt(ref) {
  try {
    const rows = JSON.parse(git('show', `${ref}:${REGISTRY}`)).rows;
    const counts = {adopted: 0, missing: 0, blocked: 0, legitimately_unknown: 0};
    for (const r of rows) counts[r.status]++;
    return counts;
  } catch { return null; }
}
const registryHistory = git('log', '--reverse', '--format=%h%x09%cI', `${START}^..HEAD`, '--', REGISTRY).split('\n').filter(Boolean)
  .map(line => { const [hash, date] = line.split('\t'); return {hash, date: new Date(date), counts: registryAt(hash)}; });

const firstAdding = file => git('log', '--diff-filter=A', '--format=%h', '--', file).split('\n').filter(Boolean).pop();
const byHash = new Map(commits.map((c, i) => [c.hash, {...c, i}]));
const slices = fs.readdirSync(path.join(root, 'docs/roadmap/briefs')).filter(f => f.endsWith('.md')).map(f => {
  const id = f.slice(0, -3);
  const brief = byHash.get(firstAdding(`docs/roadmap/briefs/${f}`));
  const impl = byHash.get(firstAdding(`docs/roadmap/reports/${f}`));
  const name = id.replace('.', '\\.');
  const review = impl && commits.slice(impl.i + 1).find(c => new RegExp(`\\b${name} review|accept ${name}\\b`, 'i').test(c.subject));
  let delta = null;
  if (impl) {
    const after = registryAt(impl.hash), before = registryAt(impl.hash + '^');
    if (after) delta = after.adopted - (before ? before.adopted : 0);
  }
  return {id, brief, impl, review, delta, summary: status.slices[id] || ''};
}).sort((a, b) => (a.brief?.i ?? 1e9) - (b.brief?.i ?? 1e9));
// A slice with no review commit counts as accepted once a later slice's code has landed.
for (const s of slices) s.state = s.review || (s.impl && slices.some(t => t.impl && t.impl.i > s.impl.i)) ? 'accepted' : s.impl ? 'in review' : 'brief written';

// --- current registry --------------------------------------------------------
const rows = JSON.parse(fs.readFileSync(path.join(root, REGISTRY), 'utf8')).rows;
const total = rows.length;
const count = s => rows.filter(r => r.status === s).length;
const families = Object.keys(FAMILIES).map(f => {
  const fr = rows.filter(r => r.family === f);
  return {f, n: fr.length, adopted: fr.filter(r => r.status === 'adopted').length,
    blocked: fr.filter(r => r.status === 'blocked').length, unknown: fr.filter(r => r.status === 'legitimately_unknown').length,
    ws: [...new Set(fr.map(workstream))].join(', ')};
});

// --- formatting helpers ------------------------------------------------------
const day = d => d.toLocaleDateString('en-CA', {timeZone: 'America/Chicago'});
const stamp = d => d.toLocaleString('en-US', {timeZone: 'America/Chicago', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit'});
const hours = ms => ms / 36e5;
const dur = ms => { const h = hours(ms); return h < 1 ? `${Math.round(h * 60)} min` : h < 48 ? `${h.toFixed(1)} h` : `${(h / 24).toFixed(1)} d`; };
const human = p => p.replace(/_/g, ' ');
const pill = s => `<span class="pill ${esc(s.replace(/[^a-z]+/gi, '-').toLowerCase())}">${esc(s)}</span>`;

// --- pace numbers ------------------------------------------------------------
const span = head.date - commits[0].date;
const gaps = [];
for (let i = 1; i < commits.length; i++) {
  const ms = commits[i].date - commits[i - 1].date;
  if (hours(ms) >= 6) gaps.push({from: commits[i - 1], to: commits[i], ms});
}
const waiting = gaps.reduce((n, g) => n + g.ms, 0);
const done = slices.filter(s => s.impl);
const cycle = done.filter(s => s.brief && s.review).map(s => s.review.date - s.brief.date).sort((a, b) => a - b);
const median = cycle.length ? cycle[Math.floor(cycle.length / 2)] : 0;

// --- charts ------------------------------------------------------------------
function adoptedChart() {
  const W = 640, H = 170, P = 34, t0 = commits[0].date.getTime(), t1 = Math.max(head.date.getTime(), Date.now());
  const x = t => P + (t - t0) / (t1 - t0) * (W - 2 * P), y = v => H - P + 8 - v / total * (H - 2 * P);
  let d = '', last = null;
  for (const r of registryHistory) {
    if (!r.counts) continue;
    const X = x(r.date.getTime()).toFixed(1), Y = y(r.counts.adopted).toFixed(1);
    d += last === null ? `M${X},${Y}` : `H${X}V${Y}`; last = r.counts.adopted;
  }
  d += `H${x(t1).toFixed(1)}`;
  const dots = registryHistory.filter(r => r.counts).map(r =>
    `<circle cx="${x(r.date.getTime()).toFixed(1)}" cy="${y(r.counts.adopted).toFixed(1)}" r="3.5" class="dot"><title>${esc(stamp(r.date))}: ${r.counts.adopted} adopted</title></circle>`).join('');
  const ticks = [];
  for (let t = new Date(commits[0].date); t.getTime() <= t1; t.setDate(t.getDate() + 2))
    ticks.push(`<text x="${x(t.getTime()).toFixed(1)}" y="${H - 6}" class="tick" text-anchor="middle">${esc(day(t).slice(5))}</text>`);
  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Adopted registry rows over time">
<line x1="${P}" x2="${W - P}" y1="${y(total)}" y2="${y(total)}" class="goal"/><text x="${W - P}" y="${y(total) - 5}" class="tick" text-anchor="end">goal ${total}</text>
<line x1="${P}" x2="${W - P}" y1="${y(0)}" y2="${y(0)}" class="axis"/>
<path d="${d}" class="line"/>${dots}${ticks.join('')}
<text x="${x(t1) - 4}" y="${y(last) - 8}" class="tick" text-anchor="end">${last} now</text></svg>`;
}

function dailyChart(days) {
  const W = 640, H = 120, P = 24, bw = (W - 2 * P) / days.length, max = Math.max(...days.map(d => d.commits.length), 1);
  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Commits per day">${days.map((d, i) => {
    const h = d.commits.length / max * (H - 2 * P), X = P + i * bw;
    return `<rect x="${(X + 2).toFixed(1)}" y="${(H - P - h).toFixed(1)}" width="${(bw - 4).toFixed(1)}" height="${h.toFixed(1)}" class="${d.commits.length ? 'bar' : 'bar idle'}"><title>${d.date}: ${d.commits.length} commits</title></rect>
<text x="${(X + bw / 2).toFixed(1)}" y="${H - 8}" class="tick" text-anchor="middle">${d.date.slice(5)}</text>${d.commits.length ? `<text x="${(X + bw / 2).toFixed(1)}" y="${(H - P - h - 4).toFixed(1)}" class="tick" text-anchor="middle">${d.commits.length}</text>` : ''}`;
  }).join('')}</svg>`;
}

// --- sections ----------------------------------------------------------------
const days = [];
for (let t = new Date(day(commits[0].date) + 'T12:00:00'); day(t) <= day(new Date()); t.setDate(t.getDate() + 1)) {
  const date = day(t);
  const dc = commits.filter(c => day(c.date) === date);
  const rh = registryHistory.filter(r => day(r.date) === date && r.counts);
  const prev = registryHistory.filter(r => day(r.date) < date && r.counts).pop();
  const adoptedDelta = rh.length ? rh[rh.length - 1].counts.adopted - (prev ? prev.counts.adopted : 0) : 0;
  const accepted = slices.filter(s => s.impl && day(s.impl.date) === date).map(s => s.id);
  days.push({date, commits: dc, adoptedDelta, accepted});
}

const list = items => `<ul>${items.map(i => `<li>${esc(i)}</li>`).join('')}</ul>`;
const pct = n => (n / total * 100).toFixed(0);

const workstreamRows = status.workstreams.map(w => {
  const wr = rows.filter(r => workstream(r) === w.id);
  const shipped = slices.filter(s => s.impl && (s.id.startsWith(w.id + '.') || s.id === w.id + 'L' || (w.id === 'P0' && s.id.startsWith('P0')) || (w.id === 'TB' && s.id.startsWith('B')))).map(s => s.id);
  const rowsCell = wr.length ? `${wr.filter(r => r.status === 'adopted').length} / ${wr.length}` : '-';
  return `<tr><td><b>${esc(w.id)}</b></td><td><b>${esc(w.name)}</b><div class="sub">${esc(w.covers)}</div></td><td>${pill(w.status)}</td>
<td class="num">${rowsCell}</td><td class="num">${status.red_tests[w.id] ?? '-'}</td><td>${shipped.length ? esc(shipped.join(', ')) : '-'}<div class="sub">est. ${esc(w.slices_est)}</div></td></tr>`;
}).join('');

const familyRows = families.map(f => {
  const a = f.adopted / f.n * 100, b = f.blocked / f.n * 100, u = f.unknown / f.n * 100;
  return `<tr><td><b>${f.f}</b></td><td>${esc(FAMILIES[f.f])}</td><td>${esc(f.ws)}</td>
<td><div class="stack" title="${f.adopted} adopted, ${f.blocked} blocked, ${f.unknown} legitimately unknown, ${f.n - f.adopted - f.blocked - f.unknown} missing">
<span class="s-adopted" style="width:${a}%"></span><span class="s-blocked" style="width:${b}%"></span><span class="s-unknown" style="width:${u}%"></span></div></td>
<td class="num">${f.adopted} / ${f.n}</td></tr>`;
}).join('');

const sliceRows = slices.map(s => {
  const c = s.brief && s.review ? dur(s.review.date - s.brief.date) : s.brief && s.impl ? dur(s.impl.date - s.brief.date) + ' (to code)' : '-';
  const state = s.state;
  const report = s.impl ? `<a href="../roadmap/reports/${esc(s.id)}.md">report</a>` : '';
  return `<tr><td><b>${esc(s.id)}</b></td><td>${esc(s.summary)}</td><td>${pill(state)}</td>
<td>${s.brief ? esc(stamp(s.brief.date)) : '-'}</td><td>${s.impl ? esc(stamp(s.impl.date)) : '-'}</td><td class="num">${c}</td>
<td class="num">${s.delta === null ? '-' : s.delta > 0 ? '+' + s.delta : s.delta}</td><td><a href="../roadmap/briefs/${esc(s.id)}.md">brief</a> ${report}</td></tr>`;
}).join('');

const dayBlocks = days.slice().reverse().map(d => `<details${d === days[days.length - 1] ? ' open' : ''}><summary><b>${d.date}</b>
<span class="sub">${d.commits.length} commits${d.accepted.length ? ' · slices landed: ' + esc(d.accepted.join(', ')) : ''}${d.adoptedDelta ? ` · registry ${d.adoptedDelta > 0 ? '+' : ''}${d.adoptedDelta} rows` : ''}</span></summary>
${status.days[d.date] ? `<p>${esc(status.days[d.date])}</p>` : d.commits.length ? '' : '<p class="sub">No commits.</p>'}
${d.commits.length ? `<ul class="commits">${d.commits.map(c => `<li><code>${c.hash}</code> <span class="sub">${esc(stamp(c.date).split(', ').pop())}</span> ${esc(c.subject)}</li>`).join('')}</ul>` : ''}</details>`).join('');

const gapRows = gaps.map(g => `<tr><td>${esc(stamp(g.from.date))}</td><td>${esc(stamp(g.to.date))}</td><td class="num">${dur(g.ms)}</td>
<td>${esc(status.gaps[g.from.hash] || 'Between sessions (no recorded cause).')}</td></tr>`).join('');

const rowTable = wr => `<table class="rows"><tr><th>Family</th><th>Property</th><th>Context</th><th>Whose</th><th>Impact</th><th>Status</th></tr>
${wr.map(r => `<tr><td>${r.family}</td><td>${esc(human(r.property))}</td><td>${esc(r.context)}</td><td>${esc(r.perspective)}</td><td>${esc(r.impact)}</td><td>${pill(r.status)}${r.status === 'blocked' ? `<div class="sub">${esc(r.blocked_by || '')}</div>` : ''}</td></tr>`).join('')}</table>`;
const open = r => r.status === 'missing' || r.status === 'blocked';
const remaining = [...status.planned, {id: 'W1', covers: 'Own move restrictions left blocked after W1.3.', rows: 0}].map(p => {
  const wr = rows.filter(r => slice(r) === p.id && open(r));
  if (p.id === 'W1' && !wr.length) return '';
  const s = slices.find(x => x.id === p.id);
  const state = s ? s.state : fs.existsSync(path.join(root, `docs/roadmap/briefs/${p.id}.md`)) ? 'brief written' : 'not started';
  return `<details><summary><b>${esc(p.id)}</b> ${pill(state)} ${esc(p.covers)} <span class="sub">${wr.length ? wr.length + ' rows left' : 'no registry rows'}</span></summary>
${wr.length ? rowTable(wr) : '<p class="sub">Infrastructure or final check; no registry rows.</p>'}</details>`;
}).join('');
const plannedLeft = rows.filter(open).length;

const html = `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Neural Showdown Status</title>
<style>
:root{--bg:#f7f7f5;--card:#fff;--ink:#1d1d1b;--sub:#6b6b66;--line:#e3e2dd;--accent:#2f6fde;--ok:#2e8b57;--warn:#c9831a;--bad:#c2453a;--muted:#d9d8d2}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#151514;--card:#1f1f1d;--ink:#ecebe6;--sub:#a3a29b;--line:#34342f;--accent:#6c9cf0;--ok:#4fb67d;--warn:#e0a13e;--bad:#e06b5f;--muted:#3a3a35}}
:root[data-theme="dark"]{--bg:#151514;--card:#1f1f1d;--ink:#ecebe6;--sub:#a3a29b;--line:#34342f;--accent:#6c9cf0;--ok:#4fb67d;--warn:#e0a13e;--bad:#e06b5f;--muted:#3a3a35}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:1100px;margin:0 auto;padding:24px 16px 64px}h1{font-size:26px;margin:0 0 4px}h2{font-size:19px;margin:36px 0 10px}
.sub{color:var(--sub);font-size:13px}.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}.card h3{margin:0 0 6px;font-size:15px}
.card ul{margin:0;padding-left:18px}.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-top:16px}
.kpi b{display:block;font-size:26px}.bar-big{height:12px;border-radius:6px;background:var(--muted);overflow:hidden;display:flex;margin-top:8px}
.bar-big span,.stack span{display:block;height:100%}.s-adopted{background:var(--ok)}.s-blocked{background:var(--bad)}.s-unknown{background:var(--warn)}
.stack{height:10px;width:100%;min-width:90px;border-radius:5px;background:var(--muted);overflow:hidden;display:flex}
.scroll{overflow-x:auto}table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:10px;font-size:14px}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}th{font-size:12px;color:var(--sub);font-weight:600}
td.num{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
.pill{display:inline-block;padding:1px 8px;border-radius:99px;font-size:12px;white-space:nowrap;background:var(--muted)}
.pill.done,.pill.accepted,.pill.adopted,.pill.lite-done{background:color-mix(in srgb,var(--ok) 22%,transparent)}
.pill.in-progress,.pill.in-review,.pill.partly-done-w-born-replays-{background:color-mix(in srgb,var(--accent) 22%,transparent)}
.pill.blocked,.pill.paused-until-w{background:color-mix(in srgb,var(--bad) 22%,transparent)}
details{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 14px;margin-bottom:8px}summary{cursor:pointer}
details p{margin:8px 0}.commits{margin:6px 0 0;padding-left:18px;font-size:13px}code{font-size:12px;color:var(--sub)}
svg{width:100%;height:auto;display:block}.line{fill:none;stroke:var(--accent);stroke-width:2.5}.dot{fill:var(--accent)}
.axis{stroke:var(--line)}.goal{stroke:var(--ok);stroke-dasharray:4 4}.tick{fill:var(--sub);font-size:11px}
.bar{fill:var(--accent)}.bar.idle{fill:var(--muted)}.rows{margin-top:8px}a{color:var(--accent)}
.legend span{display:inline-block;width:10px;height:10px;border-radius:2px;margin:0 4px 0 12px;vertical-align:-1px}
</style></head><body><main>
<h1>Neural Showdown status</h1>
<div class="sub">Generated ${esc(stamp(new Date()))} at <code>${head.hash}</code> (${esc(head.subject)}). Hand-maintained notes: <code>docs/roadmap/status.json</code>, last edited ${esc(status.updated)}. Regenerate: <code>node tools/status/build_status.cjs</code></div>

<div class="kpis">
<div class="card kpi"><span class="sub">Knowledge rows adopted</span><b>${count('adopted')} / ${total}</b><span class="sub">${pct(count('adopted'))}% · goal is all ${total}</span></div>
<div class="card kpi"><span class="sub">Rows missing</span><b>${count('missing')}</b><span class="sub">plus ${count('blocked')} blocked, ${count('legitimately_unknown')} legitimately unknown</span></div>
<div class="card kpi"><span class="sub">Slices landed since ${esc(day(commits[0].date))}</span><b>${done.length}</b><span class="sub">median brief to accepted ${dur(median)}</span></div>
<div class="card kpi"><span class="sub">Calendar time spent in gaps of 6 h+</span><b>${(waiting / span * 100).toFixed(0)}%</b><span class="sub">${dur(waiting)} of ${dur(span)}</span></div>
</div>
<div class="bar-big" title="adopted / blocked / legitimately unknown / missing"><span class="s-adopted" style="width:${pct(count('adopted'))}%"></span><span class="s-blocked" style="width:${pct(count('blocked'))}%"></span><span class="s-unknown" style="width:${pct(count('legitimately_unknown'))}%"></span></div>
<div class="sub legend"><span class="s-adopted"></span>adopted<span class="s-blocked"></span>blocked<span class="s-unknown"></span>legitimately unknown<span style="background:var(--muted)"></span>missing</div>

<h2>Right now</h2>
<div class="grid">
<div class="card"><h3>In progress</h3>${list(status.now.in_progress)}</div>
<div class="card"><h3>Next</h3>${list(status.now.next)}</div>
<div class="card"><h3>Blocked or waiting</h3>${list(status.now.blocked)}</div>
</div>

<h2>What "done" means</h2>
<div class="card"><p style="margin:0">The bot may only use what a real player could know at each decision. The <b>knowledge registry</b> lists ${total} rows: each is one fact (like "opponent's current item" or "turns of weather left"), for one player, at one point in time (team as submitted, current state, or the request Showdown sends). A row is <b>adopted</b> when a provider produces it from legitimate sources and tests prove it never leaks hidden information or invents a value. Track A ends at <b>W10</b>, when no row is missing.</p></div>

<h2>Adopted rows over time</h2>
<div class="card">${adoptedChart()}<div class="sub">Each dot is a commit that changed the registry. Before ${esc(day(commits[0].date))}: ${earlier} commits, including Prompts 1-62.</div></div>

<h2>Workstreams</h2>
<div class="scroll"><table><tr><th>ID</th><th>What it covers</th><th>Status</th><th>Rows adopted</th><th>Red tests</th><th>Slices landed</th></tr>${workstreamRows}</table></div>
<div class="sub" style="margin-top:6px">${esc(status.red_tests._as_of)}</div>

<h2>Knowledge by family</h2>
<div class="scroll"><table><tr><th>Family</th><th>Facts</th><th>Owner</th><th>Progress</th><th>Adopted</th></tr>${familyRows}</table></div>

<h2>Slices</h2>
<div class="sub" style="margin-bottom:6px">A slice is one brief that Codex implements and Claude reviews. Times are commit times (US Central). "Cycle" is brief to accepted review.</div>
<div class="scroll"><table><tr><th>Slice</th><th>What it did</th><th>State</th><th>Brief</th><th>Code landed</th><th>Cycle</th><th>Rows</th><th>Docs</th></tr>${sliceRows}</table></div>

<h2>Daily progress</h2>
<div class="card">${dailyChart(days)}</div>
<div style="margin-top:10px">${dayBlocks}</div>

<h2>Pace: where the time goes</h2>
<div class="card">${list(status.pace)}</div>
<h3 style="margin:18px 0 8px;font-size:15px">Gaps of 6 hours or more between commits</h3>
<div class="scroll"><table><tr><th>From</th><th>To</th><th>Length</th><th>What was happening</th></tr>${gapRows}</table></div>

<h2>Remaining work (known so far)</h2>
<div class="sub" style="margin-bottom:8px">The plan's remaining Track A slices, in dependency order: W3.3, then W3.4, W4, W5; W6 after W3.3; W2 and W7 any time after W3.3. Open each one to see its ${plannedLeft} missing or blocked rows. Splits can happen at review.</div>
${remaining}
</main></body></html>
`;
fs.mkdirSync(path.join(root, 'docs/status'), {recursive: true});
fs.writeFileSync(path.join(root, 'docs/status/index.html'), html);
console.log('wrote docs/status/index.html');
