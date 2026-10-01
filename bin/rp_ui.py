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
 :root{
   --bg:#0f1115; --card:#171a21; --card2:#1e222b; --line:#2a2f3a;
   --fg:#e8eaed; --mut:#98a0b0; --acc:#5b9cff; --ok:#3ecf8e; --warn:#ffb454;
   --err:#ff6b6b; --radius:12px;
 }
 *{box-sizing:border-box}
 body{margin:0;font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,
      "Helvetica Neue",Arial,sans-serif;background:var(--bg);color:var(--fg)}
 header{padding:1.6rem 1.25rem 1rem;border-bottom:1px solid var(--line);
        background:linear-gradient(180deg,#141821,#0f1115)}
 .wrap{max-width:60rem;margin:0 auto}
 h1{margin:0;font-size:1.35rem;letter-spacing:-.01em}
 .sub{color:var(--mut);font-size:.86rem;margin-top:.2rem}
 nav{display:flex;gap:.4rem;margin-top:1rem;flex-wrap:wrap}
 nav button{background:transparent;border:1px solid var(--line);color:var(--mut);
   padding:.4rem .8rem;border-radius:999px;cursor:pointer;font-size:.85rem}
 nav button:hover{color:var(--fg);border-color:#3a4150}
 nav button.on{background:var(--acc);border-color:var(--acc);color:#06101f;font-weight:600}
 main{max-width:60rem;margin:0 auto;padding:1.5rem 1.25rem 4rem}
 .card{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);
       padding:1.1rem;margin-bottom:1rem}
 .card h2{margin:0 0 .15rem;font-size:1.02rem}
 .card .hint{color:var(--mut);font-size:.82rem;margin:0 0 1rem}
 /* channel card */
 .ch{display:flex;gap:1rem;align-items:center;padding:.95rem;background:var(--card2);
     border:1px solid var(--line);border-radius:10px;margin-bottom:.7rem;flex-wrap:wrap}
 .ch img{width:56px;height:56px;border-radius:50%;object-fit:cover;background:#333;flex:none}
 .ch .info{flex:1 1 12rem;min-width:0}
 .ch .nm{font-weight:600;overflow-wrap:anywhere}
 .ch .ct{color:var(--mut);font-size:.8rem}
 /* copy field */
 .copyrow{display:flex;gap:.5rem;margin-top:.5rem;flex-wrap:wrap}
 input[type=text],input[type=number],input[type=password],select,textarea{
   background:#0c0e13;border:1px solid var(--line);color:var(--fg);border-radius:8px;
   padding:.55rem .7rem;font:inherit;width:100%}
 input:focus,select:focus,textarea:focus{outline:2px solid var(--acc);outline-offset:-1px}
 .copyrow input{flex:1 1 18rem;min-width:12rem;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.82rem}
 button{cursor:pointer;font:inherit;border-radius:8px;padding:.55rem .9rem;border:1px solid var(--line);
        background:var(--card2);color:var(--fg)}
 button:hover{border-color:#3a4150}
 button.secondary{background:var(--bg);color:var(--fg)}
button.secondary:hover{border-color:#3a4150}
button:disabled{opacity:.55;cursor:default}
button.primary{background:var(--acc);border-color:var(--acc);color:#06101f;font-weight:600}
 button.ok{background:var(--ok);border-color:var(--ok);color:#04150d;font-weight:600}
 button.ghost{background:transparent}
 button.sm{padding:.3rem .6rem;font-size:.8rem}
 /* settings */
 .grid{display:grid;gap:1rem}
 .f{border-bottom:1px solid var(--line);padding:.9rem 0}
 .f:last-child{border-bottom:0}
 .f label{display:block;font-weight:600;font-size:.88rem;margin-bottom:.15rem}
 .f .d{color:var(--mut);font-size:.78rem;margin-bottom:.45rem}
 .row{display:flex;gap:.6rem;align-items:center;flex-wrap:wrap}
 .row .grow{flex:1 1 14rem}
 .pill{display:inline-block;padding:.1rem .5rem;border-radius:999px;font-size:.72rem;
       background:#243040;color:var(--mut);margin-left:.4rem}
 .pill.secret{background:#3a2a12;color:var(--warn)}
 /* channels editor */
 .chrow{display:flex;gap:.5rem;margin-bottom:.5rem}
 .chrow .rm{flex:none}
 /* toast + banner */
 #toast{position:fixed;left:50%;transform:translateX(-50%);bottom:1.5rem;
   background:var(--ok);color:#04150d;padding:.6rem 1rem;border-radius:999px;
   font-weight:600;box-shadow:0 8px 30px rgba(0,0,0,.5);opacity:0;pointer-events:none;
   transition:opacity .2s,transform .2s;z-index:50}
 #toast.show{opacity:1;transform:translateX(-50%) translateY(-6px)}
 #toast.err{background:var(--err);color:#2a0606}
 .banner{background:#2a1f10;border:1px solid #4a3a1a;color:var(--warn);
         padding:.7rem .9rem;border-radius:10px;margin-bottom:1rem;font-size:.85rem}
 footer{color:var(--mut);font-size:.78rem;text-align:center;padding:2rem 1.25rem;
        border-top:1px solid var(--line)}
 a{color:var(--acc)}
 .hint-inline{color:var(--mut);font-size:.78rem;margin-top:.4rem}
 .hidden{display:none !important}
 code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.85em}
</style></head><body>
<header><div class="wrap">
  <h1>RumblingPodcast</h1>
  <div class="sub">Rumble channels as podcasts, on your own machine</div>
  <nav>
    <button data-tab="feeds" class="on">Feeds</button>
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
$$("nav button").forEach((b) => b.addEventListener("click", () => {
  $$("nav button").forEach((x) => x.classList.toggle("on", x === b));
  $$("section[id^=tab-]").forEach((s) =>
    s.classList.toggle("hidden", s.id !== "tab-" + b.dataset.tab));
}));

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
      '<div class="copyrow"><input type="text" readonly><button class="ok">Copy</button></div></div>';
    el.querySelector(".nm").textContent = c.name;
    el.querySelector(".ct").textContent = c.count + " episode" + (c.count === 1 ? "" : "s");
    const input = el.querySelector("input");
    input.value = url;
    input.id = "feed-" + c.slug;
    el.querySelector("button").dataset.copy = input.id;
    box.appendChild(el);
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
    if (want === "settings" || want === "api" || want === "feeds") {
      const btn = document.querySelector('nav button[data-tab=' + want + "]");
      if (btn) btn.click();
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
