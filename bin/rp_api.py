#!/usr/bin/env python3
"""
RumblingPodcast - https://github.com/iharshgandhi/RumblingPodcast
Copyright (C) 2026 Harsh Gandhi (harshgandhi.com) / Buho Smart Tools (buho.co.in)

Licensed under the GNU General Public License v3.0 or later.
This is an experimental project provided "AS IS", with NO WARRANTY and no
liability. It contains no copyrighted material and no circumvention code.
See DISCLAIMER.md. You are responsible for using it lawfully.
"""
"""Web UI API for RumblingPodcast: read and edit rp.conf over HTTP.

Security model
--------------
The service is reachable from the whole local network, so anything that changes
settings is gated:

  * every /api/* request needs the session cookie issued by the UI, and
  * mutating requests additionally need a CSRF token bound to that session;
  * the OpenRouter key is write-only. It can be set or cleared through this API
    but is never included in any response, not even masked.

Config edits are validated against a schema, written atomically, and a
timestamped backup is kept on every change.
"""

import json
import os
import re
import secrets
import shutil
import threading
import time

# ---------------------------------------------------------------------------
# Schema: every key the config file supports, with type and validation rules.
# 'secret' keys are never returned by the API.
# ---------------------------------------------------------------------------
FIELDS = [
    # key,                 type,   label,                       secret
    ("channels",           "list",  "Channels to follow",        False),
    ("serve_port",         "int",   "Feed port",                 False),
    ("feed_base_url",      "text",  "Feed base URL",             False),
    ("run_time",           "time",  "Nightly run time",          False),
    ("retention_days",     "int",   "Delete audio after (days)", False),
    ("max_age_days",       "int",   "Only videos newer than (days)", False),
    ("scan_interval_hours", "int",  "Scan interval (hours)",     False),
    ("sleep_between_videos", "int", "Pause between videos (seconds)", False),
    ("loop_sleep",         "int",   "Idle loop sleep (seconds)", False),
    ("channel_meta_days",  "int",   "Refresh channel info (days)", False),
    ("summarize",          "enum",  "Summarizer",                False),
    ("openrouter_key",     "text",  "OpenRouter API key",        True),
    ("model_remote",       "text",  "Remote model",              False),
    ("remote_max_chars",   "int",   "Max transcript chars",      False),
    ("remote_timeout",     "int",   "Request timeout (s)",       False),
    ("remote_max_tries",   "int",   "Max model attempts",        False),
    ("or_cache_ttl",       "int",   "Model list cache (s)",      False),
    ("extractive_sentences", "int", "Extractive summary sentences", False),
    ("model_local",        "text",  "Local model",               False),
    ("llm_threads",        "int",   "LLM threads",               False),
    ("llm_chunk_words",    "int",   "LLM chunk size (words)",    False),
    ("use_captions",       "bool",  "Use Rumble captions",       False),
    ("whisper_model",      "text",  "Whisper model",             False),
    ("whisper_model_file", "text",  "Whisper model file",        False),
    ("whisper_model_alt_file", "text", "Whisper alt model file", False),
    ("whisper_threads",    "int",   "Whisper threads",           False),
    ("download_thumbnails", "bool", "Download thumbnails",       False),
    ("podcast_title",      "text",  "Podcast title",             False),
    ("podcast_description", "text", "Podcast description",       False),
    ("podcast_author",     "text",  "Author",                    False),
    ("podcast_email",      "text",  "Contact email",             False),
    ("podcast_language",   "text",  "Language",                  False),
    ("timezone",           "text",  "Timezone",                  False),
    ("skip_existing",      "bool",  "Skip already downloaded",   False),
]

ENUMS = {
    "summarize": ["none", "local", "openrouter"],
}

LABELS = {k: lbl for k, _t, lbl, _s in FIELDS}
SECRET_KEYS = {k for k, _t, _l, s in FIELDS if s}

# Keys that must never be reassigned to something invalid.
RESERVED = {"openrouter_key"}  # write-only, handled specially


class ConfigError(Exception):
    pass


# ---------------------------------------------------------------------------
# Reading / writing rp.conf
# ---------------------------------------------------------------------------
# A config file can contain "key =" with nothing after it. Treating that as an
# empty string is worse than useless: it shows as a blank box in the web UI and,
# for a numeric field, would read as 0. Substitute the documented default.
BLANK_MEANS_DEFAULT = {
    "remote_max_tries": "5",
    "or_cache_ttl": "21600",
    "extractive_sentences": "7",
}


def parse_conf(text):
    """Return an ordered {key: value} of the last definition of each key."""
    out = {}
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip() if not raw.strip().startswith("#") else ""
        if not line or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        # A key with no value means "unset", not "the empty string". Substituting
        # the default here stops a blank box reaching the settings UI.
        if not val and key in BLANK_MEANS_DEFAULT:
            val = BLANK_MEANS_DEFAULT[key]
        out[key] = val
    return out


def read_conf(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return parse_conf(fh.read())


def validate(key, value):
    if isinstance(value, str) and not value.strip():
        value = BLANK_MEANS_DEFAULT.get(key, value)
    """Validate one value. Raises ConfigError with a human-readable message."""
    ftype = dict((k, t) for k, t, _l, _s in FIELDS).get(key, "text")

    if value is None:
        return ""
    value = str(value)

    if key == "channels":
        parts = [p for p in value.split() if p]
        if not parts:
            raise ConfigError("at least one channel is required")
        return " ".join(normalize_channel(p) for p in parts)

    if key == "serve_port":
        if not value.isdigit() or not (1024 <= int(value) <= 65535):
            raise ConfigError("port must be a number between 1024 and 65535")
        if value in ("53", "80", "443"):
            raise ConfigError("port %s is reserved for Pi-hole" % value)
        return value

    if key in ENUMS:
        if value not in ENUMS[key]:
            raise ConfigError("must be one of: %s" % ", ".join(ENUMS[key]))
        return value

    if ftype == "int":
        if value != "" and not value.lstrip("-").isdigit():
            raise ConfigError("must be a whole number")
        if int(value or 0) < 0:
            raise ConfigError("must not be negative")
        return value

    if ftype == "bool":
        if value in ("1", "true", "yes", "on"):
            return "1"
        if value in ("0", "false", "no", "off"):
            return "0"
        raise ConfigError("must be on/off (1/0)")

    if key == "run_time":
        m = re.match(r"^([01]?\d|2[0-3]):([0-5]\d)$", value)
        if not m:
            raise ConfigError("use 24-hour HH:MM, for example 02:00")
        return "%02d:%s" % (int(m.group(1)), m.group(2))

    if key == "openrouter_key":
        if value == "":
            return ""
        if not value.startswith("sk-or-v1-"):
            raise ConfigError("an OpenRouter key starts with sk-or-v1-")
        return value

    if len(value) > 2000:
        raise ConfigError("value is too long")

    return value


def normalize_channel(raw):
    """Accept a slug, numeric id or any Rumble URL; store the bare id."""
    c = raw.strip()
    if "creator=" in c:
        c = c.rsplit("creator=", 1)[1]
        c = c[2:] if c.startswith("_c") else (c[1:] if c.startswith("c") else c.lstrip("_"))
        return c
    c = re.sub(r"^https?://", "", c)
    c = re.sub(r"^[^/]*rumble\.com/", "", c)
    parts = [p for p in c.split("/") if p]
    noise = {"c", "videos", "user", "u", "subscriptions", "embed", "browse", "search"}
    slug = ""
    for p in parts:
        if p.lower() in noise:
            continue
        slug = p
        break
    if slug.startswith("c-"):
        slug = slug[2:]
    elif slug.startswith("_c"):
        slug = slug[2:]
    return slug or c


def write_conf(path, updates):
    """Atomically apply {key: value}; backs up first. Preserves comments."""
    backup = "%s.bak.%s" % (path, time.strftime("%Y%m%d-%H%M%S"))
    shutil.copy2(path, backup)
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()

    remaining = dict(updates)
    out = []
    for line in lines:
        stripped = line.strip()
        key = None
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
        if key in remaining:
            val = remaining.pop(key)
            if val == "":
                # Keep the key present but empty so the intent stays visible.
                out.append("%s = %s" % (key, val))
            else:
                indent = line[: len(line) - len(line.lstrip())]
                out.append("%s%s = %s" % (indent, key, val))
            continue
        out.append(line)
    # Append anything new (a key that was not in the file before).
    for key, val in remaining.items():
        out.append("%s = %s" % (key, val))

    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)
    return backup


# ---------------------------------------------------------------------------
# Sessions: cookie + CSRF token. In-memory only, so a restart invalidates them.
# ---------------------------------------------------------------------------
class Sessions:
    def __init__(self, ttl=86400):
        self.ttl = ttl
        self.lock = threading.Lock()
        self.data = {}

    def create(self):
        sid = secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(24)
        with self.lock:
            self.data[sid] = {"csrf": csrf, "seen": time.time()}
            self._gc()
        return sid, csrf

    def _gc(self):
        now = time.time()
        for k in [k for k, v in self.data.items() if now - v["seen"] > self.ttl]:
            del self.data[k]

    def get(self, sid):
        if not sid:
            return None
        with self.lock:
            self._gc()
            s = self.data.get(sid)
            if s:
                s["seen"] = time.time()
            return s

    def valid_csrf(self, sid, token):
        s = self.get(sid)
        return bool(s) and secrets.compare_digest(s["csrf"], token or "")
