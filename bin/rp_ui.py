#!/usr/bin/env python3
"""
RumblingPodcast - https://github.com/iharshgandhi/RumblingPodcast
Copyright (C) 2026 Harsh Gandhi (harshgandhi.com) / Buho Smart Tools (buho.co.in)

Licensed under the GNU General Public License v3.0 or later.
This is an experimental project provided "AS IS", with NO WARRANTY and no
liability. It contains no copyrighted material and no circumvention code.
See DISCLAIMER.md. You are responsible for using it lawfully.
"""
"""The web UI: feed links with a copy button, and a settings editor.

Kept as a template string so the server stays a single dependency-free file.
"""

PAGE = r"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>RumblingPodcast</title>
<style>
/* Palette and shape taken from the Pi-hole web interface, so this page sits
   next to it without looking like a different product. Colours sampled from
   Pi-hole's own default-light.css / default-dark.css and the login page. */
:root{
  --acc:#3c8dbc;          /* Pi-hole navbar blue */
  --acc-dk:#367fa9;
  --line:#bdc3c7;
  --ok:#5cb85c;
  --warn:#f0ad4e;
  --err:#d9534f;
  --bg:#ecf0f5;           /* the usual Pi-hole page background */
  --panel:#ffffff;
  --panel2:#f5f7fa;
  --fg:#333c43;
  --mut:#737c84;
  --radius:4px;           /* Pi-hole uses barely-rounded corners */
  --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
}
*{box-sizing:border-box}
.hidden{display:none !important}
body{margin:0;color:var(--fg);background:var(--bg);
     font:14px/1.55 "Source Sans Pro","Helvetica Neue",Helvetica,Arial,sans-serif}
/* ---- top bar, modelled on Pi-hole's fixed navbar ---- */
header{background:var(--acc);color:#fff;box-shadow:0 1px 2px rgba(0,0,0,.18);
       position:sticky;top:0;z-index:20}
header .bar{max-width:78rem;margin:0 auto;display:flex;align-items:center;
            gap:.9rem;padding:.6rem 1rem;flex-wrap:wrap}
header h1{margin:0;font-size:1.15rem;font-weight:600;letter-spacing:.01em}
header .sub{color:#d6e6f2;font-size:.8rem}
header .grow{flex:1}
nav{display:flex;gap:.15rem;flex-wrap:wrap}
nav button{background:transparent;border:0;color:#fff;padding:.45rem .85rem;
  border-radius:var(--radius);cursor:pointer;font:inherit;font-weight:600;
  font-size:.9rem}
nav button:hover{background:rgba(0,0,0,.12)}
nav button.on{background:var(--acc-dk);box-shadow:inset 0 -2px 0 rgba(0,0,0,.25)}
main{max-width:78rem;margin:0 auto;padding:1.25rem 1rem 4rem}
h2{margin:0 0 .3rem;font-size:1.06rem;font-weight:600}
h3{margin:0 0 .2rem;font-size:.95rem;font-weight:600}
.hint{color:var(--mut);font-size:.83rem;margin:0 0 .9rem}
/* ---- panels ---- */
.card{background:var(--panel);border:1px solid var(--line);border-top:0;
      border-radius:var(--radius);padding:1rem;margin-bottom:1rem;
      box-shadow:0 1px 1px rgba(0,0,0,.06)}
.card>h2{padding-bottom:.5rem;margin-bottom:.7rem;border-bottom:1px solid #e3e7ea}
/* ---- channel row ---- */
.ch{display:flex;gap:1rem;align-items:flex-start;padding:.9rem;
    background:var(--panel2);border:1px solid #dfe3e7;border-radius:var(--radius);
    margin-bottom:.6rem;flex-wrap:wrap}
.ch img{width:60px;height:60px;border-radius:50%;object-fit:cover;background:#dfe3e7;flex:none}
.ch .info{flex:1 1 14rem;min-width:0}
.ch .nm{font-weight:600;overflow-wrap:anywhere}
.ch .ct{color:var(--mut);font-size:.82rem}
.copyrow{display:flex;gap:.4rem;margin-top:.5rem;flex-wrap:wrap}
input[type=text],input[type=number],input[type=password],select,textarea{
  background:#fff;border:1px solid var(--line);color:var(--fg);border-radius:var(--radius);
  padding:.5rem .65rem;font:inherit;width:100%}
input:focus,select:focus,textarea:focus{
  outline:0;border-color:var(--acc);box-shadow:0 0 0 2px rgba(60,141,188,.22)}
.copyrow input{flex:1 1 18rem;min-width:12rem;font-family:var(--mono);font-size:.82rem}
button{cursor:pointer;font:inherit;border-radius:var(--radius);padding:.5rem .9rem;
  border:1px solid var(--line);background:#fff;color:var(--fg)}
button:hover{background:var(--panel2);border-color:#aab2b8}
button:disabled{opacity:.6;cursor:default}
button.primary{background:var(--acc);border-color:var(--acc);color:#fff;font-weight:600}
button.primary:hover{background:var(--acc-dk);border-color:var(--acc-dk)}
button.ok{background:var(--ok);border-color:var(--ok);color:#fff;font-weight:600}
button.danger{background:#fff;border-color:var(--err);color:var(--err)}
button.danger:hover{background:var(--err);color:#fff}
button.sm{padding:.28rem .55rem;font-size:.8rem}
a.btn{display:inline-block;text-decoration:none;padding:.28rem .55rem;font-size:.8rem;
  border-radius:var(--radius);border:1px solid var(--line);background:#fff;color:var(--fg)}
a.btn:hover{background:var(--panel2);border-color:#aab2b8;text-decoration:none}
/* ---- stats strip, like Pi-hole's dashboard tiles ---- */
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(9rem,1fr));
       gap:.6rem;margin-bottom:1rem}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);
      padding:.75rem .9rem;box-shadow:0 1px 1px rgba(0,0,0,.06)}
.stat .n{font-size:1.5rem;font-weight:600;line-height:1.1}
.stat .k{color:var(--mut);font-size:.76rem;text-transform:uppercase;letter-spacing:.04em}
/* ---- episodes ---- */
.eps{display:grid;gap:.6rem}
.ep{display:flex;gap:.9rem;padding:.85rem;background:var(--panel2);
    border:1px solid #dfe3e7;border-radius:var(--radius);flex-wrap:wrap}
.ep img{width:104px;height:58px;border-radius:3px;object-fit:cover;background:#dfe3e7;flex:none}
.ep .info{flex:1 1 16rem;min-width:0}
.ep .t{font-weight:600;overflow-wrap:anywhere}
.ep .meta{color:var(--mut);font-size:.8rem;margin:.1rem 0 .3rem}
.ep .sum{font-size:.85rem;color:#4a545b;max-height:4.6rem;overflow:hidden}
.ep .sum.open{max-height:none}
.ep .acts{display:flex;gap:.35rem;margin-top:.5rem;flex-wrap:wrap;align-items:center}
.tag{display:inline-block;padding:.05rem .4rem;border-radius:2px;font-size:.7rem;
     background:#dfe3e7;color:var(--mut);margin-left:.3rem}
.tag.live{background:#fbe3e4;color:#c0392b}
select.pick{width:auto;min-width:12rem}
.grid{display:grid;gap:1rem}
.f{border-bottom:1px solid #e9ecef;padding:.85rem 0}
.f:last-child{border-bottom:0}
.f label{display:block;font-weight:600;font-size:.88rem;margin-bottom:.15rem}
.f .d{color:var(--mut);font-size:.78rem;margin-bottom:.4rem}
.row{display:flex;gap:.5rem;align-items:center;flex-wrap:wrap}
.row .grow{flex:1 1 14rem}
.pill{display:inline-block;padding:.05rem .45rem;border-radius:2px;font-size:.72rem;
      background:#dfe3e7;color:var(--mut);margin-left:.4rem}
.pill.secret{background:#fcf3e3;color:#8a6d3b}
#toast{position:fixed;left:50%;transform:translateX(-50%);bottom:1.5rem;
  background:#333c43;color:#fff;padding:.6rem 1rem;border-radius:var(--radius);
  font-size:.86rem;box-shadow:0 3px 10px rgba(0,0,0,.25);opacity:0;
  pointer-events:none;transition:opacity .2s;z-index:50}
#toast.show{opacity:1}
a{color:var(--acc)}
footer{border-top:1px solid var(--line);color:var(--mut);font-size:.8rem;
       text-align:center;padding:1.5rem 1rem 2.5rem;margin-top:1rem}
@media (max-width:640px){
  header .bar{padding:.55rem .7rem}
  main{padding:1rem .7rem 3rem}
  .ep img{width:84px;height:48px}
}
</style></head><body>
<header><div class="bar">
  <h1>RumblingPodcast</h1>
  <span class="sub">Rumble channels as podcasts</span>
  <span class="grow"></span>
  <nav>
    <button data-tab="feeds" class="on">Feeds</button>
    <button data-tab="episodes">Episodes</button>
    <button data-tab="settings">Settings</button>
    <button data-tab="api">API key</button>
  </nav>
</div></header>

<main>
  <!-- ============================ FEEDS ============================ -->
  <section id="tab-feeds">
    <div class="card">
      <h2>Your podcast feeds</h2>
      <p class="hint">Copy a link and paste it into your podcast app
        (Apple Podcasts: Libraries → + → Add a Podcast by URL).</p>
      <div class="row" style="margin:.7rem 0">
        <button id="refresh" class="secondary">Check for new episodes now</button>
        <span id="refreshMsg" class="hint"></span>
      </div>
      <div id="channels"><p class="hint">Loading…</p></div>
    </div>
    <div class="card">
      <h2>All channels combined</h2>
      <p class="hint">One feed with every channel mixed together.</p>
      <div class="copyrow">
        <input type="text" id="allfeed" readonly>
        <button class="ok" data-copy="allfeed">Copy</button>
      </div>
      <div class="hint-inline">Feeds are reachable on your local network only.</div>
    </div>
  </section>

  <!-- =========================== EPISODES ========================== -->
  <section id="tab-episodes" class="hidden">
    <div class="stats" id="epStats"></div>
    <div class="card">
      <div class="row" style="margin-bottom:.9rem">
        <h2 style="margin:0">Episodes</h2>
        <span class="grow"></span>
        <label class="hint" for="epFilter" style="margin:0">Channel</label>
        <select id="epFilter" class="pick"></select>
        <button class="sm" id="epReload">Reload</button>
      </div>
      <p class="hint">Everything the feeds currently publish, newest first. Play a
        summary here, open the episode on Rumble, or download the audio.</p>
      <div class="eps" id="epList"><p class="hint">Loading…</p></div>
    </div>
  </section>

  <!-- =========================== SETTINGS ========================== -->
  <section id="tab-settings" class="hidden">
    <div class="banner" id="restartBanner">
      Changing the port or base URL takes effect after the feed server restarts.
      Use the terminal: <code>sudo rp restart</code>
    </div>
    <div class="card">
      <h2>Settings</h2>
      <p class="hint">Every option the config file supports. Changes save immediately
        and a timestamped backup is kept each time.</p>
      <div class="row" style="margin-bottom:1rem">
        <button class="primary" id="saveAll">Save changes</button>
        <button class="ghost" id="reload">Discard changes</button>
        <span id="saveState" class="hint-inline"></span>
      </div>
      <div class="grid" id="fields"><p class="hint">Loading…</p></div>
    </div>

    <div class="card">
      <h2>Channels</h2>
      <p class="hint">Add or remove the Rumble channels you follow. Each one becomes
        its own podcast feed.</p>
      <div id="chanList"></div>
      <div class="chrow">
        <input type="text" id="chanNew" class="grow"
               placeholder="URL, name or id — e.g. https://rumble.com/c/BeyondMystic">
        <button class="primary" id="chanAdd">Add</button>
      </div>
      <button class="primary" id="chanSave">Save channels</button>
    </div>
  </section>

  <!-- ============================= API ============================= -->
  <section id="tab-api" class="hidden">
    <div class="card">
      <h2>OpenRouter API key</h2>
      <p class="hint">Used only for AI summaries, and only with free models.
        The key is never displayed after saving — it cannot be read back through
        this page or any API.</p>
      <div id="apiState"></div>
      <div class="row" style="margin-top:.9rem">
        <input type="password" id="apiKey" class="grow" autocomplete="off"
               placeholder="sk-or-v1-…">
        <button class="primary" id="apiSave">Save key</button>
        <button class="ghost" id="apiClear">Remove key</button>
      </div>
      <div class="hint-inline">Leave empty and save to keep the current key unchanged.</div>
    </div>
    <div class="card">
      <h2>Also settable from the terminal</h2>
      <p class="hint">Run <code>sudo rp key set</code> to enter a key without typing it
        into a web page.</p>
    </div>
  </section>
</main>

<footer>RumblingPodcast · experimental project ·
  <a href="https://github.com/iharshgandhi/RumblingPodcast">source &amp; licence</a></footer>

<div id="toast" role="status" aria-live="polite"></div>

<script>
const CSRF = "__CSRF__";
const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));

function toast(msg, bad) {
  const t = $("#toast");
  t.textContent = msg;
  t.className = "show" + (bad ? " err" : "");
  clearTimeout(t._t);
  t._t = setTimeout(() => { t.className = ""; }, 2600);
}

async function api(path, opts = {}) {
  const res = await fetch(path, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": CSRF },
    ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  let data = null;
  try { data = await res.json(); } catch (e) { /* empty body */ }
  if (!res.ok) throw new Error((data && data.error) || ("HTTP " + res.status));
  return data;
}

/* ---------------------------- tabs ---------------------------- */
let EP_LOADED = false;
let pendingChannel = "";
function showTab(name) {
  $$("nav button").forEach((x) => x.classList.toggle("on", x.dataset.tab === name));
  $$("section[id^=tab-]").forEach((s) =>
    s.classList.toggle("hidden", s.id !== "tab-" + name));
  // Episodes are fetched on first visit rather than on every page load.
  if (name === "episodes" && !EP_LOADED) { EP_LOADED = true; loadEpisodes(); }
}
$$("nav button").forEach((b) =>
  b.addEventListener("click", () => showTab(b.dataset.tab)));

/* Explore: jump to the Episodes tab filtered to one channel. */
document.addEventListener("click", (ev) => {
  const b = ev.target.closest("[data-explore]");
  if (!b) return;
  pendingChannel = b.dataset.explore;
  EP_LOADED = false;
  showTab("episodes");
});

/* --------------------------- copy button ------------------------ */
async function copyFrom(inputId, btn) {
  const input = document.getElementById(inputId);
  const text = input.value;
  let ok = false;
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      ok = true;
    }
  } catch (e) { ok = false; }
  if (!ok) {
    // Works on plain http:// too, which a LAN address always is.
    input.removeAttribute("readonly");
    input.select();
    input.setSelectionRange(0, text.length);
    try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
    input.setAttribute("readonly", "readonly");
    window.getSelection().removeAllRanges();
  }
  const old = btn.textContent;
  btn.textContent = ok ? "Copied ✓" : "Press Ctrl+C";
  btn.classList.toggle("ok", ok);
  setTimeout(() => { btn.textContent = old; btn.classList.remove("ok"); }, 1600);
  toast(ok ? "Copied to clipboard" : "Select the text and copy it", !ok);
}
document.addEventListener("click", (e) => {
  const btn = e.target.closest("[data-copy]");
  if (btn) copyFrom(btn.dataset.copy, btn);
});

/* ----------------------------- feeds ---------------------------- */
let DATA = { channels: [], config: {}, hasKey: false, port: 8088, base: "" };

function feedUrl(slug) { return DATA.base + "/feeds/" + slug + ".xml"; }

function renderChannels() {
  const box = $("#channels");
  if (!DATA.channels.length) {
    box.innerHTML = '<p class="hint">No channels yet. Add one in the Settings tab.</p>';
    return;
  }
  box.innerHTML = "";
  DATA.channels.forEach((c) => {
    const url = feedUrl(c.slug);
    const el = document.createElement("div");
    el.className = "ch";
    el.innerHTML =
      '<img alt="" src="' + c.art + '" onerror="this.style.visibility=\'hidden\'">' +
      '<div class="info"><div class="nm"></div><div class="ct"></div>' +
      '<div class="copyrow"><input type="text" readonly>' +
      '<button class="ok">Copy</button>' +
      '<button class="primary" data-explore="' + c.slug + '">Browse episodes</button>' +
      '</div></div>';
    el.querySelector(".nm").textContent = c.name;
    el.querySelector(".ct").textContent = c.count + " episode" + (c.count === 1 ? "" : "s");
    const input = el.querySelector("input");
    input.value = url;
    input.id = "feed-" + c.slug;
    el.querySelector("button.ok").dataset.copy = input.id;
    box.appendChild(el);
  });
}

/* --------------------------- episodes --------------------------- */
function fmtBytes(n) {
  if (!n) return "";
  const u = ["B", "KB", "MB", "GB"];
  let i = 0, v = n;
  while (v >= 1024 && i < u.length - 1) { v /= 1024; i++; }
  return v.toFixed(i ? 1 : 0) + " " + u[i];
}

function fmtDate(s) {
  if (!s) return "";
  const d = new Date(s);
  return isNaN(d) ? s : d.toLocaleDateString(undefined,
    { year: "numeric", month: "short", day: "numeric" });
}

async function loadEpisodes() {
  const box = $("#epList");
  const pick = $("#epFilter");
  // Read the wanted channel BEFORE rebuilding the picker, otherwise a
  // deliberate choice (Browse episodes on one channel) is wiped by the
  // option list being regenerated from DATA.
  const want = pendingChannel || pick.value;
  pendingChannel = "";
  box.innerHTML = '<p class="hint">Loading\u2026</p>';
  let data;
  try {
    const q = want ? "?channel=" + encodeURIComponent(want) : "";
    data = await api("/api/episodes" + q);
  } catch (e) {
    box.innerHTML = '<p class="hint">Could not load: ' + e.message + "</p>";
    return;
  }
  const eps = data.episodes || [];

  // Channel picker, keeping the current selection.
  const chans = (DATA.channels || []).map((c) => c.slug);
  pick.innerHTML = '<option value="">All channels</option>' +
    chans.map((s) => {
      const c = (DATA.channels || []).find((x) => x.slug === s);
      return '<option value="' + s + '">' + (c ? c.name : s) + "</option>";
    }).join("");
  if (want) pick.value = want;

  // Counts across everything, not just the filtered view.
  const all = eps.length;
  const total = (DATA.channels || []).reduce((a, c) => a + c.count, 0);
  $("#epStats").innerHTML = [
    ["Episodes", all],
    ["Across channels", (DATA.channels || []).length],
    ["Feeds publish", total],
  ].map(([k, n]) =>
    '<div class="stat"><div class="n">' + n + '</div><div class="k">' +
    k + "</div></div>").join("");

  if (!eps.length) {
    box.innerHTML = '<p class="hint">No episodes published yet. Press ' +
      '"Check for new episodes now" on the Feeds tab, or wait for the ' +
      "nightly run.</p>";
    return;
  }

  box.innerHTML = eps.map((e, i) => {
    const id = "sum-" + i;
    return '<div class="ep">' +
      '<img alt="" src="' + e.art + '" onerror="this.style.visibility=\'hidden\'">' +
      '<div class="info">' +
      '<div class="t"></div>' +
      '<div class="meta"><span class="ch"></span> \u00b7 <span class="dt"></span>' +
      '<span class="tag live" hidden>livestream</span>' +
      '<span class="du"></span></div>' +
      '<div class="sum" id="' + id + '"></div>' +
      '<div class="acts">' +
      '<button class="sm" data-more="' + id + '">Show full summary</button>' +
      '<audio class="au" controls preload="none" style="flex:1 1 14rem"></audio>' +
      (e.page ? '<a class="btn sm" target="_blank" rel="noopener" href="' +
        e.page + '">Watch on Rumble</a>' : "") +
      (e.audio ? '<a class="btn sm" href="' + e.audio +
        '" download>Download audio</a>' : "") +
      '</div></div></div>';
  }).join("");

  eps.forEach((e, i) => {
    const card = box.children[i];
    card.querySelector(".t").textContent = e.title || "Untitled";
    card.querySelector(".ch").textContent = e.channelName || e.channel;
    card.querySelector(".dt").textContent = fmtDate(e.date);
    if (e.live) card.querySelector(".tag.live").hidden = false;
    const bits = [];
    if (e.duration) bits.push(e.duration);
    const b = fmtBytes(e.bytes);
    if (b) bits.push(b);
    card.querySelector(".du").textContent = bits.join(" \u00b7 ");
    card.querySelector(".sum").textContent = e.description || "No summary yet.";
    card.querySelector(".au").src = e.audio || "";
  });

  box.addEventListener("click", (ev) => {
    const btn = ev.target.closest("[data-more]");
    if (!btn) return;
    const s = document.getElementById(btn.dataset.more);
    const open = s.classList.toggle("open");
    btn.textContent = open ? "Show less" : "Show full summary";
  });
}

/* --------------------------- settings --------------------------- */
// Injected by the server: the ordered list of editable config keys.
const DATA_KEYS = __DATA_KEYS__;
const INT_FIELDS = new Set(["serve_port", "retention_days", "max_age_days",
  "scan_interval_hours", "sleep_between_videos", "loop_sleep", "channel_meta_days",
  "remote_max_chars", "remote_timeout", "remote_max_tries", "or_cache_ttl",
  "extractive_sentences", "llm_threads", "llm_chunk_words", "whisper_threads"]);
const BOOL_FIELDS = new Set(["use_captions", "download_thumbnails", "skip_existing"]);
const ENUM_FIELDS = { summarize: ["none", "local", "openrouter"] };
// Everything except the channels list, which has its own editor, and the
// secret, which is write-only.
const EDITABLE = DATA_KEYS.filter((k) => k !== "channels" && k !== "openrouter_key");

function renderFields() {
  const box = $("#fields");
  box.innerHTML = "";
  EDITABLE.forEach((f) => {
    const spec = DATA.schema[f];
    if (!spec) return;
    const wrap = document.createElement("div");
    wrap.className = "f";
    const val = DATA.config[f] === undefined ? "" : DATA.config[f];
    let ctrl;
    if (ENUM_FIELDS[f]) {
      ctrl = '<select data-key="' + f + '">' +
        ENUM_FIELDS[f].map((o) =>
          '<option value="' + o + '"' + (o === val ? " selected" : "") + ">" + o + "</option>").join("") +
        "</select>";
    } else if (BOOL_FIELDS.has(f)) {
      ctrl = '<select data-key="' + f + '"><option value="1"' + (val === "1" ? " selected" : "") +
        ">on</option><option value=\"0\"" + (val === "0" ? " selected" : "") + ">off</option></select>";
    } else {
      const t = INT_FIELDS.has(f) ? "number" : "text";
      ctrl = '<input type="' + t + '" data-key="' + f + '" value="' +
        String(val).replace(/"/g, "&quot;") + '">';
    }
    wrap.innerHTML = "<label>" + spec.label + "</label>" +
      (spec.desc ? '<div class="d">' + spec.desc + "</div>" : "") +
      '<div class="row"><div class="grow">' + ctrl + "</div></div>";
    box.appendChild(wrap);
  });
}

async function saveAll() {
  const updates = {};
  $$("#fields [data-key]").forEach((el) => { updates[el.dataset.key] = el.value; });
  $("#saveState").textContent = "Saving…";
  try {
    await api("/api/config", { method: "POST", body: { updates } });
    DATA.config = { ...DATA.config, ...updates };
    $("#saveState").textContent = "Saved ✓";
    toast("Settings saved");
    setTimeout(() => { $("#saveState").textContent = ""; }, 2500);
    await load();
  } catch (e) {
    $("#saveState").textContent = "";
    toast(e.message, true);
  }
}

function renderChannelEditor() {
  const box = $("#chanList");
  box.innerHTML = "";
  DATA.config.channels.split(" ").filter(Boolean).forEach((slug) => {
    const row = document.createElement("div");
    row.className = "chrow";
    row.innerHTML = '<input type="text" class="grow" value="' +
      slug.replace(/"/g, "&quot;") + '"><button class="ghost rm sm">Remove</button>';
    row.querySelector(".rm").addEventListener("click", () => row.remove());
    box.appendChild(row);
  });
}

async function saveChannels() {
  const slugs = Array.from(document.querySelectorAll("#chanList input"))
    .map((i) => i.value.trim()).filter(Boolean);
  if (!slugs.length) { toast("Keep at least one channel", true); return; }
  try {
    const r = await api("/api/config", { method: "POST", body: { updates: { channels: slugs.join(" ") } } });
    DATA.config.channels = r.config.channels;
    toast("Channels saved");
    await load();
  } catch (e) { toast(e.message, true); }
}

/* ------------------------------ api ----------------------------- */
function renderApi() {
  const box = $("#apiState");
  box.innerHTML = DATA.hasKey
    ? '<p class="hint">A key is saved <span class="pill secret">hidden</span>' +
      ' Summaries use free models only. Enter a new key below to replace it.</p>'
    : '<p class="hint">No key saved. Summaries fall back to the built-in ' +
      'extractive summariser.</p>';
}

$("#saveAll").addEventListener("click", saveAll);
$("#reload").addEventListener("click", () => load());

$("#epReload").addEventListener("click", () => loadEpisodes());
$("#epFilter").addEventListener("change", () => loadEpisodes());

/* Manual refresh: run one scan now instead of waiting for the nightly timer.
   The scan runs in the background, so the button disables itself and says so
   rather than appearing to hang. */
$("#refresh").addEventListener("click", async () => {
  const btn = $("#refresh"), msg = $("#refreshMsg");
  btn.disabled = true;
  msg.textContent = "Starting…";
  try {
    const r = await api("/api/refresh", { method: "POST" });
    msg.textContent = r.message || "Scan started.";
  } catch (e) {
    msg.textContent = "Could not start: " + e.message;
    btn.disabled = false;
  }
});
$("#chanAdd").addEventListener("click", () => {
  const v = $("#chanNew").value.trim();
  if (!v) return;
  const row = document.createElement("div");
  row.className = "chrow";
  row.innerHTML = '<input type="text" class="grow" value="' +
    v.replace(/"/g, "&quot;") + '"><button class="ghost rm sm">Remove</button>';
  row.querySelector(".rm").addEventListener("click", () => row.remove());
  $("#chanList").appendChild(row);
  $("#chanNew").value = "";
});
$("#chanSave").addEventListener("click", saveChannels);
$("#chanNew").addEventListener("keydown", (e) => { if (e.key === "Enter") $("#chanAdd").click(); });
$("#apiSave").addEventListener("click", async () => {
  const v = $("#apiKey").value.trim();
  if (!v) { toast("Enter a key first", true); return; }
  try {
    await api("/api/config", { method: "POST", body: { updates: { openrouter_key: v } } });
    $("#apiKey").value = "";
    toast("Key saved (it will not be shown again)");
    await load();
  } catch (e) { toast(e.message, true); }
});
$("#apiClear").addEventListener("click", async () => {
  try {
    await api("/api/config", { method: "POST", body: { updates: { openrouter_key: "" } } });
    $("#apiKey").value = "";
    toast("Key removed");
    await load();
  } catch (e) { toast(e.message, true); }
});

/* ----------------------------- boot ----------------------------- */
async function load() {
  try {
    DATA = await api("/api/ui");
    $("#allfeed").value = DATA.base + "/feed.xml";
    renderChannels();
    renderFields();
    renderChannelEditor();
    renderApi();
    // ?tab=settings / ?tab=api deep-links a tab, so a screen can be bookmarked.
    const want = new URLSearchParams(location.search).get("tab");
    if (["settings", "api", "feeds", "episodes"].includes(want)) {
      showTab(want);
    }
  } catch (e) {
    $("#channels").innerHTML = '<p class="hint">Could not load: ' +
      e.message.replace(/</g, "&lt;") + "</p>";
  }
}
load();
</script>
</body></html>
"""
