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
<style id="patio">__THEME__</style>
<style>
/* Project layer only. The design system is the Patio theme above; this adds
   the episode list and the tab strip, which PiHome has no equivalent for. */
.hidden{display:none !important}
.patio-page{max-width:74rem}
.rp-tabs{display:flex;gap:var(--s-1);flex-wrap:wrap}
.rp-tabs .on{background:var(--terracotta);border-color:var(--terracotta);color:#fff}
.patio-btn--sm{padding:var(--s-1) var(--s-2);font-size:var(--t-mono)}
.patio-btn--danger{color:var(--wine);border-color:var(--line)}
.patio-btn--danger:hover{background:var(--stone-2)}
.patio-panel--flush{padding:0}
.rp-copy{display:flex;gap:var(--s-2);align-items:center;flex-wrap:wrap;margin-top:var(--s-2)}
.rp-copy input{flex:1 1 18rem;min-width:12rem}
.rp-ep{padding:0;overflow:hidden}
.rp-ep__art{width:120px;aspect-ratio:16/9;object-fit:cover;background:var(--stone-2);flex:none}
.rp-ep__body{flex:1 1 18rem;min-width:0;padding:var(--s-3) var(--s-4)}
.rp-ep__title{font-size:var(--t-tile);font-weight:600;overflow-wrap:anywhere}
.rp-ep__meta{color:var(--ink-label);font-size:var(--t-label);letter-spacing:.04em;
             text-transform:uppercase;margin:var(--s-1) 0;display:flex;gap:var(--s-2);flex-wrap:wrap}
.rp-ep__sum{color:var(--ink-soft);font-size:var(--t-body);
            display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.rp-ep__sum.open{-webkit-line-clamp:unset;display:block}
.rp-ep__acts{display:flex;gap:var(--s-2);align-items:center;flex-wrap:wrap;margin-top:var(--s-3)}
.rp-ep__acts audio{height:2rem;flex:1 1 14rem;min-width:10rem}
.rp-list{display:flex;flex-direction:column;gap:var(--s-3)}
.rp-row{display:flex;gap:var(--s-2);align-items:center;flex-wrap:wrap}
.rp-grow{flex:1 1 14rem}
.rp-label{font-size:var(--t-label);text-transform:uppercase;letter-spacing:.09em;color:var(--ink-label)}
.patio-field-pick{width:auto;min-width:12rem;background:var(--stone-2);border:1px solid var(--line);border-radius:var(--r-sm);padding:var(--s-1) var(--s-2);font:inherit;color:var(--ink)}
.rp-banner{background:var(--stone-2);border-left:4px solid var(--ocre);border-radius:var(--r-sm);
  padding:var(--s-3) var(--s-4);margin-bottom:var(--s-4);font-size:var(--t-body)}
.rp-chips{display:flex;gap:var(--s-2);align-items:center;flex-wrap:wrap;margin-top:var(--s-2)}
.rp-chanrow{display:flex;gap:var(--s-2);align-items:center;margin-bottom:var(--s-2)}
.rp-chanrow input{flex:1 1 auto;min-width:0}
.rp-grid{display:grid;gap:var(--s-4)}
.rp-field{border-bottom:1px solid var(--line);padding:var(--s-3) 0}
.rp-field:last-child{border-bottom:0}
.rp-field label{display:block;font-weight:600;font-size:var(--t-body)}
.rp-field .d{color:var(--ink-soft);font-size:var(--t-body);margin:var(--s-1) 0 var(--s-2)}
.rp-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(9rem,1fr));gap:var(--s-3);margin-bottom:var(--s-4)}
.rp-ch{display:flex;gap:var(--s-4);align-items:flex-start;padding:var(--s-3);
       background:var(--stone-1);border:1px solid var(--line);border-radius:var(--r-sm);
       border-left:4px solid var(--celeste);margin-bottom:var(--s-3);flex-wrap:wrap}
.rp-ch__art{width:56px;height:56px;border-radius:var(--r-pill);object-fit:cover;background:var(--stone-2);flex:none}
.rp-ch__body{flex:1 1 14rem;min-width:0}
.rp-ch__name{font-size:var(--t-tile);font-weight:600;overflow-wrap:anywhere}
.rp-ch__count{color:var(--ink-label);font-size:var(--t-label);letter-spacing:.05em;text-transform:uppercase}
#toast{position:fixed;left:50%;transform:translateX(-50%);bottom:var(--s-5);
  background:var(--ink);color:var(--stone-0);padding:var(--s-2) var(--s-4);
  border-radius:var(--r-sm);font-size:var(--t-body);box-shadow:var(--shadow-raised);
  opacity:0;pointer-events:none;transition:opacity .2s;z-index:50}
#toast.show{opacity:1}
@media (max-width:34rem){.rp-ep__art{width:92px}}
</style></head>
<body class="patio">
<main class="patio-page">

<header class="patio-header patio-azulejo patio-cornice">
  <div class="patio-header__row">
    <h1 class="patio-header__title">RumblingPodcast</h1>
    <span class="patio-header__sub">Rumble channels as podcasts</span>
  </div>
  <nav class="rp-tabs">
    <button data-tab="feeds" class="patio-btn patio-btn--ghost on">Feeds</button>
    <button data-tab="episodes" class="patio-btn patio-btn--ghost">Episodes</button>
    <button data-tab="settings" class="patio-btn patio-btn--ghost">Settings</button>
    <button data-tab="api" class="patio-btn patio-btn--ghost">API key</button>
  </nav>
</header>

<!-- ============================== FEEDS ============================== -->
<section id="tab-feeds" aria-label="Feeds">
  <section class="patio-panel patio-cornice">
    <h2 class="patio-panel__title">Your podcast feeds</h2>
    <p class="patio-panel__hint">Copy a link and paste it into your podcast app
      (Apple Podcasts: Libraries &rarr; + &rarr; Add a Podcast by URL).</p>
    <div class="rp-row" style="margin:var(--s-3) 0">
      <button id="refresh" class="patio-btn">Check for new episodes now</button>
      <span id="refreshMsg" class="patio-panel__hint" style="margin:0"></span>
    </div>
    <div id="channels"><p class="patio-panel__hint">Loading&hellip;</p></div>
  </section>

  <section class="patio-panel patio-cornice">
    <h2 class="patio-panel__title">All channels combined</h2>
    <p class="patio-panel__hint">One feed with every channel mixed together.</p>
    <div class="rp-copy">
      <input type="text" id="allfeed" readonly aria-label="Combined feed URL">
      <button class="patio-btn patio-btn--ghost" data-copy="allfeed">Copy</button>
    </div>
    <p class="patio-panel__hint" style="margin-top:var(--s-3)">Feeds are reachable on
      your local network only.</p>
  </section>
</section>

<!-- ============================= EPISODES ============================= -->
<section id="tab-episodes" class="hidden" aria-label="Episodes">
  <div class="rp-stats" id="epStats"></div>
  <section class="patio-panel patio-cornice">
    <div class="rp-row" style="margin-bottom:var(--s-3)">
      <h2 class="patio-panel__title" style="margin:0">Episodes</h2>
      <span class="rp-grow"></span>
      <label class="patio-label" for="epFilter">Channel</label>
      <select id="epFilter" class="patio-field-pick"></select>
      <button class="patio-btn patio-btn--ghost patio-btn--sm" id="epReload">Reload</button>
    </div>
    <p class="patio-panel__hint">Everything the feeds currently publish, newest first.
      Play a summary here, open the episode on Rumble, or download the audio.</p>
    <div class="rp-list" id="epList"><p class="patio-panel__hint">Loading&hellip;</p></div>
  </section>
</section>

<!-- ============================= SETTINGS ============================= -->
<section id="tab-settings" class="hidden" aria-label="Settings">
  <div class="rp-banner" id="restartBanner" hidden>
    Changing the port or base URL takes effect after the feed server restarts.
    Use the terminal: <code>sudo rp restart</code>
  </div>
  <section class="patio-panel patio-cornice">
    <h2 class="patio-panel__title">Settings</h2>
    <p class="patio-panel__hint">Every option the config file supports. Changes save
      immediately and a timestamped backup is kept each time.</p>
    <div class="rp-row" style="margin-bottom:var(--s-4)">
      <button class="patio-btn" id="saveAll">Save changes</button>
      <button class="patio-btn patio-btn--ghost" id="reload">Discard changes</button>
      <span id="saveState" class="patio-panel__hint" style="margin:0"></span>
    </div>
    <div class="rp-grid" id="fields"><p class="patio-panel__hint">Loading&hellip;</p></div>
  </section>

  <section class="patio-panel patio-cornice">
    <h2 class="patio-panel__title">Channels</h2>
    <p class="patio-panel__hint">Add or remove the Rumble channels you follow. Each one
      becomes its own podcast feed.</p>
    <div id="chanList"></div>
    <div class="rp-row">
      <input type="text" id="chanNew" class="rp-grow"
             placeholder="URL, name or id &mdash; e.g. https://rumble.com/c/BeyondMystic">
      <button class="patio-btn" id="chanAdd">Add</button>
    </div>
    <p style="margin-top:var(--s-3)">
      <button class="patio-btn" id="chanSave">Save channels</button>
    </p>
  </section>
</section>

<!-- =============================== API =============================== -->
<section id="tab-api" class="hidden" aria-label="API key">
  <section class="patio-panel patio-cornice">
    <h2 class="patio-panel__title">OpenRouter API key</h2>
    <p class="patio-panel__hint">Used only for AI summaries, and only with free models.
      The key is never displayed after saving &mdash; it cannot be read back through
      this page or any API.</p>
    <div id="apiState"></div>
    <div class="rp-row" style="margin-top:var(--s-3)">
      <input type="password" id="apiKey" class="rp-grow" autocomplete="off"
             placeholder="sk-or-v1-&hellip;">
      <button class="patio-btn" id="apiSave">Save key</button>
      <button class="patio-btn patio-btn--ghost patio-btn--danger" id="apiClear">Remove key</button>
    </div>
    <p class="patio-panel__hint" style="margin-top:var(--s-2)">Leave empty and save to
      keep the current key unchanged.</p>
  </section>
  <section class="patio-panel patio-cornice">
    <h2 class="patio-panel__title">Also settable from the terminal</h2>
    <p class="patio-panel__hint">Run <code>sudo rp key set</code> to enter a key without
      typing it into a web page.</p>
  </section>
</section>
</main>

<footer class="patio-foot">RumblingPodcast &middot; experimental project &middot;
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
    box.innerHTML = '<p class="patio-panel__hint">No channels yet. ' +
      "Add one in the Settings tab.</p>";
    return;
  }
  box.innerHTML = "";
  DATA.channels.forEach((c) => {
    const url = feedUrl(c.slug);
    const el = document.createElement("div");
    el.className = "rp-ch";
    el.innerHTML =
      '<img class="rp-ch__art" alt="" src="' + c.art +
      '" onerror="this.style.visibility=\'hidden\'">' +
      '<div class="rp-ch__body">' +
      '<div class="rp-ch__name"></div>' +
      '<div class="rp-ch__count"></div>' +
      '<div class="rp-copy"><input type="text" readonly>' +
      '<button class="patio-btn patio-btn--ghost patio-btn--sm">Copy</button>' +
      '<button class="patio-btn patio-btn--sm" data-explore="' + c.slug +
      '">Browse episodes</button>' +
      "</div></div>";
    el.querySelector(".rp-ch__name").textContent = c.name;
    el.querySelector(".rp-ch__count").textContent =
      c.count + " episode" + (c.count === 1 ? "" : "s");
    const input = el.querySelector("input");
    input.value = url;
    input.id = "feed-" + c.slug;
    input.setAttribute("aria-label", "Feed URL for " + c.name);
    el.querySelector(".patio-btn--ghost").dataset.copy = input.id;
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
  box.innerHTML = '<p class="patio-panel__hint">Loading\u2026</p>';
  let data;
  try {
    const q = want ? "?channel=" + encodeURIComponent(want) : "";
    data = await api("/api/episodes" + q);
  } catch (e) {
    box.innerHTML = '<p class="patio-panel__hint">Could not load: ' + e.message + "</p>";
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
    ["Channels", (DATA.channels || []).length],
    ["Published", total],
  ].map(([k, n]) =>
    '<div class="patio-stat"><div class="patio-stat__value">' + n +
    '</div><div class="patio-stat__label">' + k + "</div></div>").join("");

  if (!eps.length) {
    box.innerHTML = '<p class="patio-panel__hint">No episodes published yet. Press ' +
      '"Check for new episodes now" on the Feeds tab, or wait for the ' +
      "nightly run.</p>";
    return;
  }

  box.innerHTML = eps.map((e, i) => {
    const id = "sum-" + i;
    return '<article class="rp-ch rp-ep">' +
      '<img class="rp-ep__art" alt="" src="' + e.art +
      '" onerror="this.style.visibility=\'hidden\'">' +
      '<div class="rp-ep__body">' +
      '<h3 class="rp-ep__title"></h3>' +
      '<div class="rp-ep__meta">' +
      '<span class="rp-ep__ch"></span>' +
      '<span class="rp-ep__dt"></span>' +
      '<span class="rp-ep__du"></span>' +
      '<span class="patio-chip patio-chip--live" hidden>Livestream</span>' +
      '</div>' +
      '<div class="rp-ep__sum" id="' + id + '"></div>' +
      '<div class="rp-ep__acts">' +
      '<button class="patio-btn patio-btn--ghost patio-btn--sm" data-more="' + id +
      '">Show full summary</button>' +
      '<audio class="rp-ep__audio" controls preload="none"></audio>' +
      (e.page ? '<a class="patio-btn patio-btn--ghost patio-btn--sm" target="_blank"' +
        ' rel="noopener" href="' + e.page + '">Watch on Rumble</a>' : "") +
      (e.audio ? '<a class="patio-btn patio-btn--ghost patio-btn--sm" href="' +
        e.audio + '" download>Download</a>' : "") +
      '</div></div></article>';
  }).join("");

  eps.forEach((e, i) => {
    const card = box.children[i];
    card.querySelector(".rp-ep__title").textContent = e.title || "Untitled";
    card.querySelector(".rp-ep__ch").textContent = e.channelName || e.channel;
    card.querySelector(".rp-ep__dt").textContent = fmtDate(e.date);
    if (e.live) card.querySelector(".patio-chip--live").hidden = false;
    const bits = [];
    if (e.duration) bits.push(e.duration);
    const b = fmtBytes(e.bytes);
    if (b) bits.push(b);
    card.querySelector(".rp-ep__du").textContent = bits.join(" \u00b7 ");
    const sum = card.querySelector(".rp-ep__sum");
    sum.textContent = e.description || "No summary yet.";
    // Never truncate without keeping the full text reachable.
    sum.title = sum.textContent;
    card.querySelector(".rp-ep__audio").src = e.audio || "";
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
      (spec.desc ? '<div class="d rp-field__d">' + spec.desc + "</div>" : "") +
      '<div class="rp-row"><div class="rp-grow">' + ctrl + "</div></div>";
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
    row.innerHTML = '<input type="text" class="rp-grow" value="' +
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
    ? '<p class="patio-panel__hint">A key is saved <span class="patio-chip patio-chip--warn">hidden</span>' +
      ' Summaries use free models only. Enter a new key below to replace it.</p>'
    : '<p class="patio-panel__hint">No key saved. Summaries fall back to the built-in ' +
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
  row.innerHTML = '<input type="text" class="rp-grow" value="' +
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
    $("#channels").innerHTML = '<p class="patio-panel__hint">Could not load: ' +
      e.message.replace(/</g, "&lt;") + "</p>";
  }
}
load();
</script>
</body></html>
"""
