#!/bin/bash
# RumblingPodcast - https://github.com/iharshgandhi/RumblingPodcast
# Copyright (C) 2026 Harsh Gandhi (harshgandhi.com) / Buho Smart Tools (buho.co.in)
#
# Licensed under the GNU General Public License v3.0 or later.
# This is an experimental project provided "AS IS", with NO WARRANTY and no
# liability. It contains no copyrighted material and no circumvention code.
# See DISCLAIMER.md. You are responsible for using it lawfully.
#
# rp-config - safe, validated editing of rp.conf.
#
# Every helper writes the file atomically (temp + mv) and takes a timestamped
# backup, so a bad edit can never leave a truncated config behind.

RP_ROOT="${RP_ROOT:-/opt/rumblingpodcast}"
CONF="${RP_CONFIG:-$RP_ROOT/config/rp.conf}"

# ---- keys that hold secrets; never echo these in full --------------------
is_secret_key() {
  case "$1" in
    openrouter_key|whisper_model_file|whisper_model_alt_file) return 0 ;;
    *) return 1 ;;
  esac
}

mask_value() {   # mask_value <key> <value>
  local k="$1" v="$2"
  if is_secret_key "$k"; then
    local n=${#v}
    [ "$n" -le 8 ] && printf '(not set)' && return 0
    printf '%s…%s (%d chars)' "${v:0:4}" "${v: -3}" "$n"
  else
    printf '%s' "$v"
  fi
}

get_conf() {  # get_conf <key> -> value (last definition wins)
  local k="$1"
  [ -f "$CONF" ] || return 1
  sed -n "s/^[[:space:]]*$k[[:space:]]*=[[:space:]]*//p" "$CONF" | tail -1
}

_conf_backup() {
  [ -f "$CONF" ] || return 0
  cp -p "$CONF" "$CONF.bak.$(date +%Y%m%d-%H%M%S)"
}

# set_conf <key> <value>   (atomic, backs up first)
set_conf() {
  local k="$1" v="$2"
  [ -f "$CONF" ] || return 1
  _conf_backup
  local tmp; tmp="$(mktemp "${CONF}.XXXXXX")" || return 1
  # Preserve the existing comment structure: replace only the value part.
  if grep -qE "^[[:space:]]*${k}[[:space:]]*=" "$CONF"; then
    # Match on the key, keep the indentation, replace only the value.
    # (An earlier greedy regex consumed the key itself and wrote empty values.)
    awk -v k="$k" -v v="$v" '
      {
        if ($0 ~ "^[[:space:]]*" k "[[:space:]]*=") {
          indent = $0
          sub(/[^[:space:]].*$/, "", indent)
          print indent k " = " v
          next
        }
        print
      }
    ' "$CONF" > "$tmp"
  else
    cat "$CONF" > "$tmp"
    printf '%s = %s\n' "$k" "$v" >> "$tmp"
  fi
  chmod 600 "$tmp"
  mv "$tmp" "$CONF"
}

del_conf() {  # remove a key entirely
  local k="$1"
  [ -f "$CONF" ] || return 1
  _conf_backup
  local tmp; tmp="$(mktemp "${CONF}.XXXXXX")" || return 1
  grep -vE "^[[:space:]]*${k}[[:space:]]*=" "$CONF" > "$tmp"
  mv "$tmp" "$CONF"
}

# ---- channel helpers ------------------------------------------------------
# Channels are a space-separated list in one key. Accept slugs, numeric ids and
# full URLs; normalize to the bare slug so "add the same channel twice" works.
normalize_channel() {
  local c="$1"
  c="${c#"${c%%[![:space:]]*}"}"     # ltrim
  c="${c%"${c##*[![:space:]]}"}"     # rtrim
  [ -z "$c" ] && return 1

  # Query-string creator form first: .../subscriptions?creator=_cNNNNNN
  if [[ "$c" == *creator=* ]]; then
    c="${c##*creator=}"
    c="${c#_c}"; c="${c#c}"; c="${c#_}"
    printf '%s' "$c"; return 0
  fi

  # Strip scheme and host.
  c="${c#http://}"; c="${c#https://}"
  case "$c" in
    *rumble.com/*) c="${c#*rumble.com/}" ;;
    *rumble.com)   c="usawatchdog" ;;   # bare host, no path
  esac

  # Walk the path segments: /c/slug/videos -> slug, /user -> user.
  # Keep the LAST meaningful segment and drop known noise segments.
  local seg rest="$c" last=""
  while [ -n "$rest" ]; do
    seg="${rest%%/*}"
    [ "$seg" = "$rest" ] && rest="" || rest="${rest#*/}"
    case "$seg" in
      ""|videos|c|subscriptions|u|embed|browse|user|search) continue ;;
    esac
    last="$seg"
  done
  c="$last"

  # Leading channel markers on the bare form: c-732873, _c732873.
  c="${c#c-}"
  c="${c#_c}"
  c="${c#_}"

  [ -z "$c" ] && return 1
  printf '%s' "$c"
}

list_channels() {
  local raw; raw="$(get_conf channels)"
  [ -n "$raw" ] || return 0
  printf '%s\n' $raw          # intentional word-split: channels are space-separated
}

channel_present() {
  local want; want="$(normalize_channel "$1")" || return 1
  local c
  while read -r c; do
    [ "$c" = "$want" ] && return 0
  done < <(list_channels)
  return 1
}

add_channel() {  # idempotent
  local c; c="$(normalize_channel "${1:-}")" || { echo "empty channel" >&2; return 1; }
  if channel_present "$c"; then
    echo "$c"
    return 2    # already there
  fi
  local cur; cur="$(get_conf channels)"
  set_conf channels "${cur:+$cur }$c"
  echo "$c"
}

remove_channel() {
  local c; c="$(normalize_channel "${1:-}")" || return 1
  channel_present "$c" || return 2
  local out="" x
  while read -r x; do
    [ "$x" = "$c" ] && continue
    out="${out:+$out }$x"
  done < <(list_channels)
  set_conf channels "$out"
}

# ---- validation ----------------------------------------------------------
validate() {
  local errs=0 k v
  # Channels may be stored as slugs, numeric ids or full URLs. Normalize each
  # one, then check the result is a plain id.
  while read -r c; do
    [ -n "$c" ] || continue
    local n; n="$(normalize_channel "$c")"
    if [ -z "$n" ]; then
      printf '  could not read a channel from: %s\n' "$c" >&2; errs=$((errs+1))
    else
      case "$n" in
        *[!a-zA-Z0-9_-]*)
          printf '  invalid channel id: %s\n' "$n" >&2; errs=$((errs+1)) ;;
      esac
    fi
  done < <(list_channels)
  v="$(get_conf summarize)"
  case "$v" in
    none|local|openrouter|"") ;;
    *) printf '  summarize must be none|local|openrouter (found: %s)\n' "$v" >&2; errs=$((errs+1)) ;;
  esac
  v="$(get_conf serve_port)"
  case "$v" in
    ''|*[!0-9]*) printf '  serve_port must be a number (found: %s)\n' "$v" >&2; errs=$((errs+1)) ;;
    *) if [ "$v" -lt 1024 ] || [ "$v" -gt 65535 ]; then
         printf '  serve_port %s is privileged/out of range; use 1024-65535\n' "$v" >&2; errs=$((errs+1))
       fi ;;
  esac
  # Pi-hole owns these; refuse to collide with it.
  if [ "${v:-8088}" = "80" ] || [ "${v:-8088}" = "443" ]; then
    printf '  serve_port %s collides with Pi-hole; choose another\n' "$v" >&2; errs=$((errs+1))
  fi
  v="$(get_conf retention_days)"
  case "$v" in ''|*[!0-9]*) printf '  retention_days must be a number\n' >&2; errs=$((errs+1)) ;; esac
  # warn (not error) on a missing key when openrouter is selected
  if [ "$(get_conf summarize)" = "openrouter" ]; then
    v="$(get_conf openrouter_key)"
    case "$v" in
      ""|sk-or-REPLACE_ME)
        printf '  summarize=openrouter but no real key set (rp-ctl key set)\n' >&2 ;;
    esac
  fi
  return $((errs > 0))
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  case "${1:-}" in
    get)        get_conf "${2:?key required}" ;;
    set)        set_conf "${2:?key required}" "${3:?value required}"; echo "set ${2}" ;;
    unset)      del_conf "${2:?key required}"; echo "unset ${2}" ;;
    show)       for k in "${@:2}"; do printf '%-22s %s\n' "$k" "$(mask_value "$k" "$(get_conf "$k")")"; done ;;
    channels)   list_channels ;;
    normalize)  normalize_channel "${2:?channel required}" ;;
    add)        add_channel "${2:?channel required}" ;;
    remove)     remove_channel "${2:?channel required}" ;;
    validate)   validate ;;
    *) echo "usage: rp-config {get|set|unset|show|channels|normalize|add|remove|validate} [args]" >&2; exit 2 ;;
  esac
fi
