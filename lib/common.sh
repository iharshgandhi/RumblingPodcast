#!/bin/bash
# RumblingPodcast - shared helpers
# Author: Harsh Gandhi (harshgandhi.com) / Buho Smart Tools (buho.co.in)

RP_ROOT="${RP_ROOT:-/opt/rumblingpodcast}"
RP_BIN="$RP_ROOT/bin"
RP_CONFIG="${RP_CONFIG:-$RP_ROOT/config/rp.conf}"
RP_DATA="${RP_DATA:-$RP_ROOT/data}"
RP_LOG="${RP_LOG:-$RP_ROOT/logs}"
RP_LOCK="$RP_ROOT/run/rp.lock"
RP_MODEL_DIR="${RP_MODEL_DIR:-$RP_ROOT/models}"

mkdir -p "$RP_DATA"/{audio,video,transcripts,summaries,meta} "$RP_LOG" "$RP_ROOT/run" "$RP_ROOT/run/tmp" 2>/dev/null || true

# Raspberry Pi OS ships /tmp as a small (often 30MB) tmpfs. The yt-dlp PyInstaller
# bundle extracts ~40MB on every run, so point TMPDIR at the app's own run dir.
# Without this, yt-dlp fails with "decompression resulted in return code -1"
# whenever /tmp is full or too small.
export TMPDIR="$RP_ROOT/run/tmp"
mkdir -p "$TMPDIR" 2>/dev/null || export TMPDIR="$RP_DATA"

# ---- config loading -------------------------------------------------------
# Format: key = value  (shell-safe, sourced once, validated on load)
cfg() {
  local key="$1" def="${2:-}"
  local v
  v="$(sed -n "s/^[[:space:]]*${key}[[:space:]]*=[[:space:]]*//p" "$RP_CONFIG" 2>/dev/null | tail -n1)"
  # strip surrounding quotes and inline comments
  v="${v%%$'\n'*}"
  v="$(printf '%s' "$v" | sed -e 's/[[:space:]]*#.*$//' -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//" -e 's/[[:space:]]*$//')"
  [ -z "$v" ] && printf '%s' "$def" || printf '%s' "$v"
}

log() {
  local level="$1"; shift
  printf '%s [%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$level" "$*" \
    | tee -a "$RP_LOG/rp.log" >/dev/null
  printf '%s [%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$level" "$*"
}

log_info() { log INFO "$@"; }
log_warn() { log WARN "$@"; }
log_error() { log ERROR "$@"; }

# Single-instance lock so two workers never fight over the SD card.
acquire_lock() {
  mkdir -p "$(dirname "$RP_LOCK")"
  if ! mkdir "$RP_LOCK" 2>/dev/null; then
    if [ -f "$RP_LOCK/pid" ]; then
      local p; p="$(cat "$RP_LOCK/pid" 2>/dev/null)"
      if [ -n "$p" ] && kill -0 "$p" 2>/dev/null; then
        log_warn "another worker already running (pid $p); exiting"
        return 1
      fi
      log_warn "clearing stale lock"
      rm -rf "$RP_LOCK"
      mkdir "$RP_LOCK" 2>/dev/null || return 1
    else
      rm -rf "$RP_LOCK"; mkdir "$RP_LOCK" 2>/dev/null || return 1
    fi
  fi
  echo $$ > "$RP_LOCK/pid"
  trap 'rm -rf "$RP_LOCK"' EXIT INT TERM
  return 0
}

# Yield to the system: pihole DNS must never be starved.
throttle() {
  local sec="${1:-$(cfg sleep_between_videos 20)}"
  [ "$sec" -le 0 ] 2>/dev/null && return 0
  sleep "$sec"
}

# ---- html/xml escaping ----------------------------------------------------
xml_escape() {
  printf '%s' "$1" | sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g' \
                          -e 's/"/\&quot;/g' -e "s/'/\&apos;/g"
}

# ---- date helpers ---------------------------------------------------------
# RSS pubDate needs RFC822. GNU date is assumed on the target (Linux/Pi) but we
# fall back to BSD date so the scripts remain testable on macOS.
rfc822_date() {
  local ts="${1:-0}"
  if [ -z "$ts" ] || [ "$ts" -eq 0 ] 2>/dev/null; then
    date '+%a, %d %b %Y %H:%M:%S %z'
    return
  fi
  TZ="$(cfg timezone UTC)" date -d "@$ts" '+%a, %d %b %Y %H:%M:%S %z' 2>/dev/null \
    || TZ="$(cfg timezone UTC)" date -r "$ts" '+%a, %d %b %Y %H:%M:%S %z' 2>/dev/null \
    || date '+%a, %d %b %Y %H:%M:%S %z'
}

epoch_from_iso() {
  # accepts 2026-09-27T00:20:28+00:00 (GNU) or 2026-09-27T00:20:28Z (jq form)
  local iso="$1"
  date -d "$iso" +%s 2>/dev/null || date -j -f '%Y-%m-%dT%H:%M:%S' "$iso" +%s 2>/dev/null || echo 0
}

# now_epoch, tolerant of both date flavours
now_epoch() { date +%s; }

# subtract_days <epoch> <days>
subtract_days() {
  local ts="$1" days="$2"
  date -d "@$(( ts - days * 86400 ))" +%s 2>/dev/null \
    || date -r "$(( ts - days * 86400 ))" +%s 2>/dev/null \
    || echo 0
}

# Escape file names for safe paths.
safe_name() {
  printf '%s' "$1" | tr -cd 'A-Za-z0-9._-' | cut -c1-80
}
