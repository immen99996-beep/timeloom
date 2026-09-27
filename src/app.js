(function () {
"use strict";

const DAYS = ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"];
const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const POPULAR = ["new-york","london","tokyo","seoul","singapore","sydney","berlin","dubai"];
const DEFAULT_WORK = [540,1080];
const SLOT = 30;

let DATA, COUNTRY, CITIES, CITY, PRIMARY, COUNTRY_LIST;

const pad = n => String(n).padStart(2,"0");
const esc = s => String(s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const flag = (cc, cls="") => `<img class="flag ${cls}" src="/flags/${cc.toLowerCase()}.svg" alt="" width="24" height="18" loading="lazy">`;
const icon = (id, cls="icon") => `<svg class="${cls}" aria-hidden="true"><use href="#i-${id}"/></svg>`;
const norm = s => s.normalize("NFD").replace(/\p{Diacritic}/gu,"").toLowerCase();
const weekendOf = cc => DATA.weekend[cc] || [0,6];
const $ = id => document.getElementById(id);

/* ---------- time math ---------- */
const fmtCache = {};
function parts(ms, tz){
  const f = fmtCache[tz] || (fmtCache[tz] = new Intl.DateTimeFormat("en-US",{timeZone:tz,hourCycle:"h23",year:"numeric",month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit"}));
  const o = {};
  for (const p of f.formatToParts(ms)) o[p.type] = p.value;
  const y=+o.year, m=+o.month, d=+o.day, mi=+o.minute;
  let h=+o.hour; if (h===24) h=0;
  const dayNum = Date.UTC(y,m-1,d)/864e5;
  return {y,m,d,h,mi,dow:new Date(dayNum*864e5).getUTCDay(),key:`${y}${pad(m)}${pad(d)}`,dayNum,min:h*60+mi};
}
function offsetMin(ms, tz){
  const p = parts(ms,tz);
  return Math.round((Date.UTC(p.y,p.m-1,p.d,p.h,p.mi) - Math.floor(ms/6e4)*6e4)/6e4);
}
function zonedToUtc(y,m,d,h,mi,tz){
  const guess = Date.UTC(y,m-1,d,h,mi);
  const o1 = offsetMin(guess,tz);
  let t = guess - o1*6e4;
  const o2 = offsetMin(t,tz);
  if (o2 !== o1) t = guess - o2*6e4;
  return t;
}
function offLabel(min){
  if (min === 0) return "UTC+0";
  const a = Math.abs(min);
  return `UTC${min<0?"−":"+"}${Math.floor(a/60)}${a%60?":"+pad(a%60):""}`;
}
function fmtClock(h, mi){
  if (state.h24) return `${pad(h)}:${pad(mi)}`;
  return `${(h+11)%12+1}:${pad(mi)} ${h<12?"AM":"PM"}`;
}
const fmtMin = m => m >= 1440 ? (state.h24 ? "24:00" : "12:00 AM") : fmtClock(Math.floor(m/60), m%60);
const fmtDateLong = p => `${DAYS[p.dow]}, ${MONTHS[p.m-1]} ${p.d}, ${p.y}`;
const fmtDateShort = p => `${DAYS[p.dow].slice(0,3)}, ${MONTHS[p.m-1]} ${p.d}`;
function keyParts(key){
  const y=+key.slice(0,4), m=+key.slice(4,6), d=+key.slice(6,8);
  const dayNum = Date.UTC(y,m-1,d)/864e5;
  return {y,m,d,dow:new Date(dayNum*864e5).getUTCDay(),dayNum};
}

/* ---------- state ---------- */
const store = {
  get(k, fb){ try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : fb; } catch { return fb; } },
  set(k, v){ try { localStorage.setItem(k, JSON.stringify(v)); } catch {} }
};
const state = { locs:[], base:null, t:0, h24:true, work:{}, editing:null, excludeOff:true };
let favorites = [];

const roundNow = () => Math.floor(Date.now()/6e4)*6e4;
function defaultTime(baseId){
  const c = CITY[baseId], now = parts(Date.now(), c.tz), we = weekendOf(c.cc);
  for (let k=0;k<7;k++){
    const d = new Date(Date.UTC(now.y,now.m-1,now.d+k));
    if (!we.includes(d.getUTCDay())) return zonedToUtc(d.getUTCFullYear(), d.getUTCMonth()+1, d.getUTCDate(), 15, 0, c.tz);
  }
  return roundNow();
}
function saveSession(){
  store.set("tzp:last", {locs:state.locs, base:state.base, h24:state.h24, work:state.work, excludeOff:state.excludeOff});
}

/* Plan code: p.<ids joined by _>.<base index>.<YYYYMMDD>-<HHMM>.<12|24>, time in the base location */
function shareCode(){
  if (!state.locs.length) return "";
  const p = parts(state.t, CITY[state.base].tz);
  return `p.${state.locs.join("_")}.${state.locs.indexOf(state.base)}.${p.key}-${pad(p.h)}${pad(p.mi)}.${state.h24?24:12}`;
}
function applyCode(raw){
  const m = String(raw || "").trim().match(/p\.([a-z0-9_-]+)\.(\d+)\.(\d{8})-(\d{4})\.(12|24)/);
  if (!m) return false;
  const locs = [...new Set(m[1].split("_"))].filter(id => CITY[id]);
  if (!locs.length) return false;
  const base = locs[+m[2]] || locs[0], k = m[3], hm = m[4];
  Object.assign(state, {locs, base, h24: m[5] === "24", editing: null});
  state.t = zonedToUtc(+k.slice(0,4), +k.slice(4,6), +k.slice(6,8), +hm.slice(0,2), +hm.slice(2,4), CITY[base].tz);
  return true;
}
const shareLink = () => { const c = shareCode(); return c ? `${location.origin}/#${c}` : ""; };

/* ---------- evaluation ---------- */
function evaluate(id, t){
  const c = CITY[id], p = parts(t, c.tz);
  const holiday = DATA.holidays[c.cc]?.[p.key] || null;
  const weekend = weekendOf(c.cc).includes(p.dow);
  const w = state.work[id] || DEFAULT_WORK;
  const inHours = p.min >= w[0] && p.min < w[1];
  const day = holiday ? "holiday" : weekend ? "weekend" : "working";
  const time = inHours ? "in" : p.min < 420 ? "early" : p.min >= 1320 ? "late" : "out";
  return {c, p, holiday, weekend, day, time, inHours, w, off: offsetMin(t, c.tz), avail: inHours && (!state.excludeOff || day === "working")};
}

/* ---------- actions ---------- */
function addLoc(id){
  if (!CITY[id] || state.locs.includes(id)) return;
  const first = !state.locs.length;
  state.locs.push(id);
  if (first){ state.base = id; state.t = state.t || defaultTime(id); }
  render(); toast(`Added ${CITY[id].name}`);
}
function removeLoc(id){
  state.locs = state.locs.filter(x => x !== id);
  if (state.base === id) state.base = state.locs[0] || null;
  if (state.editing === id) state.editing = null;
  render();
}
function toggleFav(id){
  favorites = favorites.includes(id) ? favorites.filter(x => x !== id) : [...favorites, id];
  store.set("tzp:favs", favorites);
  render();
  toast(favorites.includes(id) ? `Saved ${CITY[id].name}` : `Removed ${CITY[id].name} from saved`);
}

/* ---------- rendering ---------- */
function render(){
  $("fmt12").setAttribute("aria-pressed", String(!state.h24));
  $("fmt24").setAttribute("aria-pressed", String(state.h24));
  renderChips(); renderMeet(); renderCards(); renderTimeline(); renderHolidays();
  if (!$("sharePanel").hidden) $("shareLink").value = shareLink();
  saveSession();
}

function renderChips(){
  const el = $("savedChips");
  const list = favorites.length ? favorites : POPULAR;
  let html = favorites.length ? `<span class="chips-label">${icon("star","icon sm")}Saved</span>` : `<span class="chips-label">Popular</span>`;
  html += list.map(id => {
    const c = CITY[id], added = state.locs.includes(id);
    const x = favorites.length ? `<button type="button" class="x" data-action="unfav" data-id="${id}" aria-label="Remove ${esc(c.name)} from saved">${icon("close","icon sm")}</button>` : "";
    return `<span class="chip ${added?"added":""} ${x?"":"plain"}"><button type="button" class="add" data-action="add" data-id="${id}" ${added?'aria-disabled="true"':""}>${flag(c.cc,"sm")}${esc(c.name)}</button>${x}</span>`;
  }).join("");
  if (favorites.length && favorites.some(id => !state.locs.includes(id))) html += `<button type="button" class="btn sm" data-action="add-all-favs">Add all saved</button>`;
  if (!favorites.length) html += `<span class="hint">Tap ${icon("star","icon sm")} on a card to keep a location here.</span>`;
  el.innerHTML = html;
}

function timeSelects(prefix, p, dataId){
  const extra = dataId ? ` data-id="${dataId}"` : "";
  let hours = "";
  for (let h=0; h<24; h++) hours += `<option value="${h}" ${h===p.h?"selected":""}>${state.h24?pad(h):`${(h+11)%12+1} ${h<12?"AM":"PM"}`}</option>`;
  const mins = [0,15,30,45]; if (!mins.includes(p.mi)) mins.push(p.mi); mins.sort((a,b)=>a-b);
  const mm = mins.map(x => `<option value="${x}" ${x===p.mi?"selected":""}>${pad(x)}</option>`).join("");
  return `<div class="ctl-time"><select id="${prefix}-h" aria-label="Hour" data-role="time"${extra}>${hours}</select><select id="${prefix}-m" aria-label="Minute" data-role="time"${extra}>${mm}</select></div>`;
}

function renderMeet(){
  const el = $("meet");
  if (!state.locs.length){
    el.innerHTML = `<div class="empty-state"><b>No locations yet</b><span>Search above, or pick one of the popular cities.</span></div>`;
    return;
  }
  const b = CITY[state.base], p = parts(state.t, b.tz);
  const evs = state.locs.map(id => evaluate(id, state.t));
  const alerts = [];
  for (const e of evs){
    if (e.holiday) alerts.push(["holiday","event",`<b>Public Holiday in ${esc(e.c.country)}</b> · ${esc(e.holiday)} (${fmtDateShort(e.p)}, ${esc(e.c.name)})`]);
    else if (e.weekend) alerts.push(["weekend","event",`<b>Weekend in ${esc(e.c.name)}</b> · it is ${DAYS[e.p.dow]} there`]);
  }
  for (const e of evs){
    const at = `${fmtClock(e.p.h,e.p.mi)} local time`;
    if (e.time === "early") alerts.push(["bad","block",`<b>Too early in ${esc(e.c.name)}</b> · ${at}`]);
    else if (e.time === "late") alerts.push(["bad","block",`<b>Too late in ${esc(e.c.name)}</b> · ${at}`]);
    else if (e.time === "out") alerts.push(["out","warn",`<b>Outside working hours in ${esc(e.c.name)}</b> · ${at} (hours ${fmtMin(e.w[0])}–${fmtMin(e.w[1])})`]);
  }
  for (const e of evs){
    const diff = e.p.dayNum - p.dayNum;
    if (diff) alerts.push(["info","info",`<b>${esc(e.c.name)} is ${diff>0?"a day ahead":"a day behind"}</b> · ${fmtDateLong(e.p)} there`]);
  }
  const hard = evs.filter(e => e.time === "early" || e.time === "late");
  const hasWarn = evs.some(e => e.day !== "working" || e.time === "out");
  const nIn = evs.filter(e => e.inHours && e.day === "working").length;
  const verdict = hard.length
    ? ["bad","block",`Hard time for ${hard.map(e => esc(e.c.name)).join(", ")}. ${nIn} of ${evs.length} locations are in working hours.`]
    : hasWarn
      ? ["warn","warn",`Works for ${nIn} of ${evs.length} locations. See the alerts below.`]
      : ["ok","ok",`Works for everyone. All ${evs.length} locations are on a working day, inside working hours.`];

  const opts = state.locs.map(id => `<option value="${id}" ${id===state.base?"selected":""}>${esc(CITY[id].name)} (${esc(CITY[id].country)})</option>`).join("");
  el.innerHTML = `
    <div class="meet-row">
      <label class="ctl"><span>Meeting time in</span><select id="baseSel" data-role="base">${opts}</select></label>
      <label class="ctl"><span>Date</span><input type="date" id="base-date" data-role="date" value="${p.y}-${pad(p.m)}-${pad(p.d)}"></label>
      <div class="ctl"><span>Time</span>${timeSelects("base", p)}</div>
      <div class="steps">
        <button type="button" class="btn sm" data-action="step" data-v="-60">−1h</button>
        <button type="button" class="btn sm" data-action="step" data-v="60">+1h</button>
        <button type="button" class="btn sm" data-action="now">Now</button>
      </div>
    </div>
    <div class="verdict ${verdict[0]}" role="status">${icon(verdict[1])}<span>${verdict[2]}</span></div>
    ${alerts.length ? `<ul class="alerts" aria-label="Holiday and time alerts">${alerts.map(([c,i,h]) => `<li class="alert ${c}">${icon(i)}<span>${h}</span></li>`).join("")}</ul>` : ""}`;
}

const dayBadge = e => e.day === "holiday" ? `<span class="badge b-orange"><span class="dot"></span>Public Holiday</span>`
  : e.day === "weekend" ? `<span class="badge b-orange"><span class="dot"></span>Weekend</span>`
  : `<span class="badge b-green"><span class="dot"></span>Working Day</span>`;
const timeBadge = e => ({in:`<span class="badge b-green">In working hours</span>`, out:`<span class="badge b-orange">Outside working hours</span>`,
  early:`<span class="badge b-red">Too early</span>`, late:`<span class="badge b-red">Too late</span>`})[e.time];

function renderCards(){
  const el = $("cards");
  if (!state.locs.length){ el.innerHTML = ""; return; }
  const bp = parts(state.t, CITY[state.base].tz), now = Date.now();
  el.innerHTML = state.locs.map(id => {
    const e = evaluate(id, state.t), c = e.c, p = e.p, isBase = id === state.base, fav = favorites.includes(id);
    const diff = p.dayNum - bp.dayNum, np = parts(now, c.tz);
    const hourOpts = sel => Array.from({length:25},(_,h) => `<option value="${h*60}" ${h*60===sel?"selected":""}>${fmtMin(h*60)}</option>`).join("");
    const editor = state.editing === id ? `
      <div class="editor">
        <div class="editor-row">
          <label class="ctl"><span>Date in ${esc(c.name)}</span><input type="date" id="ed-${id}-date" data-role="date" data-id="${id}" value="${p.y}-${pad(p.m)}-${pad(p.d)}"></label>
          <div class="ctl"><span>Time</span>${timeSelects("ed-"+id, p, id)}</div>
        </div>
        <div class="editor-row">
          <label class="ctl"><span>Work starts</span><select id="ed-${id}-ws" data-role="work" data-id="${id}" data-i="0">${hourOpts(e.w[0])}</select></label>
          <label class="ctl"><span>Work ends</span><select id="ed-${id}-we" data-role="work" data-id="${id}" data-i="1">${hourOpts(e.w[1])}</select></label>
          <button type="button" class="btn sm" data-action="edit" data-id="${id}">Done</button>
        </div>
      </div>` : "";
    return `<article class="panel loc ${isBase?"base":""}">
      <div class="loc-head">
        ${flag(c.cc,"lg")}
        <div class="who"><h3>${esc(c.name)}</h3><p>${esc(c.country)}</p></div>
        <div class="loc-acts">
          <button type="button" class="icon-btn ${fav?"on":""}" data-action="fav" data-id="${id}" aria-pressed="${fav}" aria-label="${fav?"Remove from saved":"Save location"}" title="${fav?"Saved":"Save for next time"}">${icon("star")}</button>
          <button type="button" class="icon-btn" data-action="remove" data-id="${id}" aria-label="Remove ${esc(c.name)}" title="Remove">${icon("close")}</button>
        </div>
      </div>
      <div class="loc-time-row">
        <button type="button" class="loc-time num" data-action="edit" data-id="${id}" title="Change the time in ${esc(c.name)}">${fmtClock(p.h,p.mi)}</button>
        ${diff ? `<span class="daydiff">${diff>0?"+":"−"}${Math.abs(diff)} day</span>` : ""}
      </div>
      <p class="loc-date"><b>${DAYS[p.dow]}</b>, ${MONTHS[p.m-1]} ${p.d}, ${p.y} · <span class="num">${offLabel(e.off)}</span></p>
      <div class="badges">${dayBadge(e)}${timeBadge(e)}</div>
      ${e.holiday ? `<p class="hname">${icon("event","icon sm")} ${esc(e.holiday)}</p>` : ""}
      ${editor}
      <div class="loc-foot">
        <span class="num">Now ${fmtClock(np.h,np.mi)}${np.key!==p.key?` · ${fmtDateShort(np)}`:""} · Work ${fmtMin(e.w[0])}–${fmtMin(e.w[1])}</span>
        ${isBase ? `<span class="badge b-blue">${icon("pin","icon sm")}Base</span>` : `<button type="button" class="linkbtn" data-action="base" data-id="${id}">Set as base</button>`}
      </div>
    </article>`;
  }).join("");
}

function renderTimeline(){
  const el = $("timeline");
  if (!state.locs.length){ el.innerHTML = `<div class="empty-state"><span>Add a location to see shared working hours.</span></div>`; return; }
  const b = CITY[state.base], p = parts(state.t, b.tz);
  const start = zonedToUtc(p.y,p.m,p.d,0,0,b.tz);
  const nd = new Date(Date.UTC(p.y,p.m-1,p.d+1));
  const end = zonedToUtc(nd.getUTCFullYear(), nd.getUTCMonth()+1, nd.getUTCDate(), 0, 0, b.tz);
  const n = Math.round((end-start)/(SLOT*6e4));
  const slots = Array.from({length:n}, (_,i) => start + i*SLOT*6e4);
  const grid = state.locs.map(id => slots.map(t => evaluate(id, t)));
  const common = slots.map((_,i) => grid.every(row => row[i].avail));
  const selIdx = Math.floor((state.t - start)/(SLOT*6e4));
  const cols = `grid-template-columns:repeat(${n},minmax(0,1fr))`;
  const cellCls = e => e.inHours ? (e.day === "working" ? "work" : "off") : (e.time === "early" || e.time === "late") ? "night" : "";
  const tick = (t, tz) => { const q = parts(t, tz); return q.mi === 0 && q.h % 3 === 0 ? (state.h24 ? pad(q.h) : `${(q.h+11)%12+1}${q.h<12?"am":"pm"}`) : ""; };

  const axis = `<div class="tl-row"><div class="tl-label" style="color:var(--muted)">${esc(b.name)} time</div><div class="tl-cells" style="${cols}">${slots.map((t,i) => { const l = tick(t, b.tz); return l ? `<span class="tl-tick" style="grid-column:${i+1} / span ${Math.min(6,n-i)}">${l}</span>` : ""; }).join("")}</div></div>`;
  const rows = state.locs.map((id, r) => {
    const c = CITY[id];
    return `<div class="tl-row"><div class="tl-label">${flag(c.cc,"sm")}<span class="t" title="${esc(c.name)}">${esc(c.name)}</span></div>
      <div class="tl-cells" style="${cols}">${grid[r].map((e,i) => `<button type="button" class="tl-cell ${cellCls(e)} ${i===selIdx?"sel":""}" data-action="slot" data-t="${slots[i]}" title="${esc(c.name)} ${fmtClock(e.p.h,e.p.mi)} · ${fmtDateShort(e.p)}${e.holiday?" · "+esc(e.holiday):e.weekend?" · Weekend":""}" aria-label="${esc(c.name)} ${fmtClock(e.p.h,e.p.mi)}"></button>`).join("")}</div></div>`;
  }).join("");
  const commonRow = `<div class="tl-row"><div class="tl-label" style="color:var(--blue-text)">${icon("groups","icon sm")}Everyone</div><div class="tl-cells" style="${cols}">${common.map((ok,i) => `<button type="button" class="tl-cell ${ok?"common":""} ${i===selIdx?"sel":""}" data-action="slot" data-t="${slots[i]}" title="${ok?"Everyone is available":"Not everyone is available"}" aria-label="${ok?"Everyone available":"Not everyone available"}"></button>`).join("")}</div></div>`;

  const wins = [];
  common.forEach((ok,i) => { if (!ok) return; const last = wins[wins.length-1]; if (last && last[1] === i) last[1] = i+1; else wins.push([i,i+1]); });
  let winHtml;
  if (wins.length){
    winHtml = wins.map(([a,z]) => {
      const t0 = slots[a], t1 = start + z*SLOT*6e4, bp0 = parts(t0,b.tz), bp1 = parts(t1,b.tz), dur = (z-a)*SLOT;
      const others = state.locs.filter(id => id !== state.base).map(id => { const q0 = parts(t0, CITY[id].tz), q1 = parts(t1, CITY[id].tz); return `${esc(CITY[id].name)} ${fmtClock(q0.h,q0.mi)}–${fmtClock(q1.h,q1.mi)}`; }).join(" · ");
      const len = dur >= 60 ? `${Math.floor(dur/60)}h${dur%60 ? " "+dur%60+"m" : ""}` : dur+"m";
      return `<div class="window"><div><div class="w-main num">${fmtClock(bp0.h,bp0.mi)} – ${fmtClock(bp1.h,bp1.mi)} ${esc(b.name)} <span class="badge b-green">${len}</span></div>${others?`<div class="w-sub num">${others}</div>`:""}</div><button type="button" class="btn sm" data-action="slot" data-t="${t0}">Use ${fmtClock(bp0.h,bp0.mi)}</button></div>`;
    }).join("");
  } else {
    const score = slots.map((_,i) => grid.reduce((s,row) => s + (row[i].avail?10:0) - ((row[i].time==="early"||row[i].time==="late")?1:0), 0));
    const best = score.indexOf(Math.max(...score));
    const bp0 = parts(slots[best], b.tz), cnt = grid.filter(row => row[best].avail).length;
    const offDay = state.excludeOff && grid.some(row => row[best].day !== "working");
    winHtml = `<div class="alert bad">${icon("block")}<span><b>No shared working hours on ${fmtDateShort(p)}.</b> ${offDay ? "A holiday or weekend rules out at least one location. " : ""}Closest option: <b class="num">${fmtClock(bp0.h,bp0.mi)} ${esc(b.name)}</b>, when ${cnt} of ${state.locs.length} locations are available.</span></div>
      <div class="window"><div class="w-sub num">${grid.map((row,r) => `${esc(CITY[state.locs[r]].name)} ${fmtClock(row[best].p.h,row[best].p.mi)}`).join(" · ")}</div><button type="button" class="btn sm" data-action="slot" data-t="${slots[best]}">Use ${fmtClock(bp0.h,bp0.mi)}</button></div>`;
  }

  el.innerHTML = `
    <div class="sec-head" style="margin:0"><p class="hint">${fmtDateLong(p)} in ${esc(b.name)}. Click a slot to pick that time.</p>
      <label class="check"><input type="checkbox" id="excludeOff" data-role="exclude" ${state.excludeOff?"checked":""}>Skip holidays and weekends</label></div>
    <div class="tl-scroll"><div class="tl">${axis}${rows}${commonRow}</div></div>
    <div class="legend"><span><i style="background:var(--green-cell)"></i>Working hours</span><span><i style="background:var(--orange-cell)"></i>Working hours on a holiday or weekend</span><span><i style="background:var(--gray-cell)"></i>Outside hours</span><span><i style="background:var(--red-cell)"></i>Before 7:00 or after 22:00</span><span><i style="background:var(--blue)"></i>Everyone available</span></div>
    <div class="windows">${winHtml}</div>`;
}

function renderHolidays(){
  const el = $("holList");
  const seen = new Set(), refs = [];
  for (const id of state.locs){ const cc = CITY[id].cc; if (!seen.has(cc)){ seen.add(cc); refs.push(id); } }
  if (!refs.length){ el.innerHTML = `<div class="panel empty-state"><span>Holiday details appear here for each country you add.</span></div>`; return; }
  el.innerHTML = refs.map(id => {
    const c = CITY[id], e = evaluate(id, state.t), hol = DATA.holidays[c.cc] || {};
    const keys = Object.keys(hol).filter(k => k >= e.p.key).sort().slice(0,5);
    const today = e.holiday
      ? `<div class="hol-today b-orange"><b>Public Holiday</b> on ${fmtDateShort(e.p)}: ${esc(e.holiday)}</div>`
      : e.weekend
        ? `<div class="hol-today b-orange"><b>Weekend</b> on ${fmtDateShort(e.p)} (${DAYS[e.p.dow]})</div>`
        : `<div class="hol-today b-green"><b>Working Day</b> on ${fmtDateShort(e.p)}. No public holiday.</div>`;
    const list = keys.length ? `<ul>${keys.map(k => {
      const q = keyParts(k), days = q.dayNum - e.p.dayNum;
      return `<li class="${days===0?"hit":""}"><span class="d num">${DAYS[q.dow].slice(0,3)}, ${MONTHS[q.m-1]} ${q.d}${q.y!==e.p.y?" "+q.y:""}</span><span>${esc(hol[k])}</span><span class="in num">${days===0?"selected day":days===1?"tomorrow":`in ${days} days`}</span></li>`;
    }).join("")}</ul>` : `<p class="hint">No holiday data after this date.</p>`;
    const wk = DATA.weekend[c.cc] ? `<p class="hint">Weekend: ${[...DATA.weekend[c.cc]].sort((a,b) => (a+6)%7 - (b+6)%7).map(d => DAYS[d]).join(" and ")}</p>` : "";
    return `<article class="panel hol"><div class="hol-head">${flag(c.cc)}<h3>${esc(c.country)}</h3><a href="/holidays/${COUNTRY[c.cc].slug}/">All holidays</a></div>${today}<div><p class="hint" style="margin-bottom:6px">Upcoming public holidays</p>${list}</div>${wk}</article>`;
  }).join("");
}

/* ---------- search ---------- */
let results = [], active = -1;
function search(q){
  q = norm(q.trim());
  if (!q) return [];
  const scored = [];
  for (const c of CITIES){
    const name = norm(c.name), country = norm(c.country), al = norm(c.al), ko = norm(COUNTRY[c.cc].ko);
    let s = 0;
    if (name.startsWith(q)) s = 100; else if (name.includes(q)) s = 70;
    if (country.startsWith(q)) s = Math.max(s, c.primary ? 65 : 60); else if (country.includes(q)) s = Math.max(s, 40);
    if (c.cc.toLowerCase() === q) s = Math.max(s, 55);
    if (ko && ko.split(" ").some(w => w.startsWith(q))) s = Math.max(s, c.primary ? 65 : 60);
    if (country === q || (ko && ko.split(" ").includes(q))) s = Math.max(s, c.primary ? 95 : 90);
    if (al && al.split(" ").some(w => w && w.startsWith(q))) s = Math.max(s, 50);
    if (s) scored.push([s, c]);
  }
  scored.sort((a,b) => b[0]-a[0] || a[1].idx - b[1].idx);
  return scored.slice(0,12).map(x => x[1]);
}
function resultRow(c, i, now){
  const p = parts(now, c.tz), added = state.locs.includes(c.id);
  return `<button type="button" class="result" role="option" id="res-${i}" aria-selected="${i===active}" data-action="add-result" data-id="${c.id}" ${added?"disabled":""}>
    ${flag(c.cc)}<span class="r-main"><span class="r-name">${esc(c.name)}</span><span class="r-sub"> · ${esc(c.country)}</span></span>
    <span class="r-time num">${added?"Added":`${fmtClock(p.h,p.mi)} · ${offLabel(offsetMin(now,c.tz))}`}</span></button>`;
}
function renderResults(show){
  const box = $("results"), q = $("q").value.trim(), now = Date.now();
  if (!show){ box.hidden = true; return; }
  if (!q){
    results = COUNTRY_LIST.map(cc => CITY[PRIMARY[cc]]);
    box.innerHTML = `<div class="results-head">All ${COUNTRY_LIST.length} countries and territories, A–Z</div>` + results.map((c,i) => {
      const p = parts(now, c.tz), added = state.locs.includes(c.id);
      return `<button type="button" class="result" role="option" id="res-${i}" aria-selected="${i===active}" data-action="add-result" data-id="${c.id}" ${added?"disabled":""}>
        ${flag(c.cc)}<span class="r-main"><span class="r-name">${esc(c.country)}</span><span class="r-sub"> · ${esc(c.name)}</span></span>
        <span class="r-time num">${added?"Added":`${fmtClock(p.h,p.mi)} · ${offLabel(offsetMin(now,c.tz))}`}</span></button>`;
    }).join("");
  } else {
    box.innerHTML = results.length ? results.map((c,i) => resultRow(c, i, now)).join("")
      : `<div class="empty">No match for “${esc(q)}”. Try a country name or a large city nearby.</div>`;
  }
  box.hidden = false;
}
function pickResult(id){ addLoc(id); $("q").value = ""; results = []; active = -1; renderResults(false); $("q").blur(); }

/* ---------- events ---------- */
function bindEvents(){
  const q = $("q");
  q.addEventListener("input", () => { results = search(q.value); active = q.value.trim() ? results.findIndex(c => !state.locs.includes(c.id)) : -1; renderResults(true); });
  q.addEventListener("focus", () => { if (!q.value.trim()) active = -1; renderResults(true); });
  q.addEventListener("keydown", e => {
    if (e.key === "ArrowDown" || e.key === "ArrowUp"){
      e.preventDefault(); if (!results.length) return;
      const dir = e.key === "ArrowDown" ? 1 : -1;
      for (let k=0;k<results.length;k++){ active = (active + dir + results.length) % results.length; if (!state.locs.includes(results[active].id)) break; }
      renderResults(true); $("res-"+active)?.scrollIntoView({block:"nearest"});
    } else if (e.key === "Enter"){
      e.preventDefault(); const c = results[active]; if (c && !state.locs.includes(c.id)) pickResult(c.id);
    } else if (e.key === "Escape"){ renderResults(false); }
  });
  document.addEventListener("click", e => { if (!e.target.closest(".search")) $("results").hidden = true; });

  document.addEventListener("click", e => {
    const b = e.target.closest("[data-action]"); if (!b) return;
    const id = b.dataset.id, a = b.dataset.action;
    if (a === "add"){ if (!state.locs.includes(id)) addLoc(id); }
    else if (a === "add-result") pickResult(id);
    else if (a === "add-all-favs"){
      const first = !state.locs.length;
      favorites.forEach(f => { if (!state.locs.includes(f)) state.locs.push(f); });
      if (first){ state.base = state.locs[0]; state.t = state.t || defaultTime(state.base); }
      render(); toast("Added your saved locations");
    }
    else if (a === "unfav" || a === "fav") toggleFav(id);
    else if (a === "remove") removeLoc(id);
    else if (a === "base"){ state.base = id; render(); }
    else if (a === "edit"){ state.editing = state.editing === id ? null : id; render(); }
    else if (a === "step"){ state.t += (+b.dataset.v)*6e4; render(); }
    else if (a === "now"){ state.t = roundNow(); render(); }
    else if (a === "slot"){ state.t = +b.dataset.t; render(); }
    else if (a === "fmt"){ state.h24 = b.dataset.v === "24"; render(); }
    else if (a === "share-toggle"){
      const p = $("sharePanel"); p.hidden = !p.hidden;
      $("shareToggle").setAttribute("aria-expanded", String(!p.hidden));
      if (!p.hidden) $("shareLink").value = shareLink();
    }
    else if (a === "copy-link") copyLink();
    else if (a === "open-code"){
      if (applyCode($("openCode").value)){ $("openCode").value = ""; render(); toast("Opened the shared plan"); }
      else toast("That is not a plan link. Copy the whole link and try again.");
    }
  });

  document.addEventListener("change", e => {
    const t = e.target, role = t.dataset.role; if (!role) return;
    if (role === "base"){ state.base = t.value; render(); return; }
    if (role === "exclude"){ state.excludeOff = t.checked; render(); return; }
    const id = t.dataset.id || state.base, prefix = t.dataset.id ? "ed-"+id : "base";
    if (role === "work"){
      const w = [...(state.work[id] || DEFAULT_WORK)]; w[+t.dataset.i] = +t.value;
      if (w[0] >= w[1]){ toast("The work day has to end after it starts"); render(); return; }
      state.work[id] = w; render(); return;
    }
    const dv = $(prefix+"-date").value; if (!dv) return;
    const [y,m,d] = dv.split("-").map(Number);
    state.t = zonedToUtc(y, m, d, +$(prefix+"-h").value, +$(prefix+"-m").value, CITY[id].tz);
    render();
  });
  addEventListener("hashchange", () => { if (applyCode(location.hash)) render(); });
}

function copyLink(){
  const link = shareLink(), f = $("shareLink");
  if (!link){ toast("Add a location before sharing"); return; }
  f.value = link;
  const fallback = () => { f.focus(); f.select(); toast("Press Ctrl+C or ⌘C to copy the link"); };
  try { navigator.clipboard.writeText(link).then(() => toast("Link copied"), fallback); } catch { fallback(); }
}
let toastTimer;
function toast(msg){ const t = $("toast"); t.textContent = msg; t.hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => t.hidden = true, 2200); }

/* ---------- boot ---------- */
function init(data){
  DATA = data;
  COUNTRY = data.countries;
  CITIES = data.cities.map(([id,name,cc,tz,al], idx) => ({id,name,cc,tz,al,idx,country:COUNTRY[cc].name}));
  CITY = Object.fromEntries(CITIES.map(c => [c.id,c]));
  PRIMARY = {};
  for (const c of CITIES) if (!PRIMARY[c.cc]){ PRIMARY[c.cc] = c.id; c.primary = true; }
  COUNTRY_LIST = Object.keys(PRIMARY).sort((a,b) => COUNTRY[a].name.localeCompare(COUNTRY[b].name));
  favorites = store.get("tzp:favs", []).filter(id => CITY[id]);

  const last = store.get("tzp:last", null);
  if (last){ state.h24 = last.h24 !== false; state.work = last.work || {}; state.excludeOff = last.excludeOff !== false; }
  const params = new URLSearchParams(location.search);
  if (!applyCode(location.hash)){
    if (last && Array.isArray(last.locs) && last.locs.some(id => CITY[id])){
      state.locs = last.locs.filter(id => CITY[id]);
      state.base = state.locs.includes(last.base) ? last.base : state.locs[0];
    } else {
      state.locs = ["seoul","jakarta","london"]; state.base = "seoul";
    }
    const add = params.get("add");
    if (add && CITY[add] && !state.locs.includes(add)) state.locs.push(add);
    state.t = defaultTime(state.base);
  }
  bindEvents();
  render();
  setInterval(() => { if (!document.activeElement?.closest(".editor, .meet")) renderCards(); }, 30000);
}

fetch("/data/world.json").then(r => { if (!r.ok) throw new Error(r.status); return r.json(); }).then(init).catch(() => {
  $("meet").innerHTML = `<div class="empty-state"><b>The planner could not load its data.</b><span>Check your connection and reload the page.</span></div>`;
});
})();
