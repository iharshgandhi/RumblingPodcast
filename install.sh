#!/bin/bash
# RumblingPodcast - https://github.com/iharshgandhi/RumblingPodcast
# Copyright (C) 2026 Harsh Gandhi (harshgandhi.com) / Buho Smart Tools (buho.co.in)
#
# Licensed under the GNU General Public License v3.0 or later.
# This is an experimental project provided "AS IS", with NO WARRANTY and no
# liability. It contains no copyrighted material and no circumvention code.
# See DISCLAIMER.md. You are responsible for using it lawfully.
#
#!/bin/bash
# One-click installer for RumblingPodcast.
#
#   curl -fsSL https://raw.githubusercontent.com/iharshgandhi/RumblingPodcast/main/install.sh | sudo bash
#
# Interactive by default (asks which summarizer and model), but fully
# scriptable with environment variables for unattended installs:
#
#   RP_CHANNEL=usawatchdog RP_SUMMARIZE=none ./install.sh
#   RP_CHANNEL=usawatchdog RP_SUMMARIZE=openrouter RP_OPENROUTER_KEY=sk-or-... ./install.sh
#   RP_NONINTERACTIVE=1 RP_CHANNEL=usawatchdog RP_SUMMARIZE=local \
#       RP_MODEL_LOCAL=gemma-3-270m-it-q4_k_m ./install.sh
#
# Author: Harsh Gandhi (harshgandhi.com) / Buho Smart Tools (buho.co.in)

set -uo pipefail

REPO="${RP_REPO:-https://github.com/iharshgandhi/RumblingPodcast.git}"
BRANCH="${RP_BRANCH:-main}"
RP_ROOT="${RP_ROOT:-/opt/rumblingpodcast}"
SRC_DIR="${RP_SRC_DIR:-/usr/local/share/rumblingpodcast-src}"

# Defaults, overridable by environment.
CHANNEL="${RP_CHANNEL:-usawatchdog}"
SUMMARIZE="${RP_SUMMARIZE:-}"
MODEL_LOCAL="${RP_MODEL_LOCAL:-}"
MODEL_REMOTE="${RP_MODEL_REMOTE:-openai/gpt-4o-mini}"
OR_KEY="${RP_OPENROUTER_KEY:-}"
NONINTERACTIVE="${RP_NONINTERACTIVE:-0}"

c_ok()   { printf '\033[32m==>\033[0m %s\n' "$*"; }
c_info() { printf '    %s\n' "$*"; }
c_warn() { printf '\033[33m!!\033[0m  %s\n' "$*"; }
c_err()  { printf '\033[31mxx\033[0m  %s\n' "$*" >&2; }
die()    { c_err "$*"; exit 1; }

# ---- interactive prompts ----------------------------------------------------
ask() {   # ask <var> <prompt> <default>
  local __v="$1" __p="$2" __d="$3" __a
  read -r -p "    $__p [$__d]: " __a
  [ -z "$__a" ] && __a="$__d"
  printf -v "$__v" '%s' "$__a"
}
choose() { # choose <var> <prompt> <opt1|opt2|...>
  local __v="$1" __p="$2" __opts="$3" __a n=1 o
  printf '    %s\n' "$__p"
  local IFS='|'
  for o in $__opts; do printf '      %d) %s\n' "$n" "$o"; n=$((n+1)); done
  unset IFS
  read -r -p "    choose [1]: " __a
  [ -z "$__a" ] && __a=1
  n=1
  for o in $__opts; do
    if [ "$n" = "$__a" ]; then printf -v "$__v" '%s' "$o"; return; fi
    n=$((n+1))
  done
  printf -v "$__v" '%s' "${__opts%%|*}"
}

[ "$(id -u)" -eq 0 ] || die "run with sudo:  curl -fsSL .../install.sh | sudo bash"

# ---- preflight --------------------------------------------------------------
c_ok "checking prerequisites"
RW="$(findmnt -no OPTIONS / | tr ',' '\n' | grep -E '^(rw|ro)$' | head -1)"
if [ "$RW" = "ro" ]; then
  c_err "root filesystem is READ-ONLY. Fix with: mount -o remount,rw /"
  die "cannot continue on a read-only filesystem"
fi
c_info "root filesystem is writable"

if ! command -v git >/dev/null; then
  DEBIAN_FRONTEND=noninteractive apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends git
fi

TOTAL_MB="$(awk '/MemTotal/{printf "%d", $2/1024}' /proc/meminfo)"
AVAIL_MB="$(awk '/MemAvailable/{printf "%d", $2/1024}' /proc/meminfo)"
c_info "memory: ${TOTAL_MB}MB total, ~${AVAIL_MB}MB available"

# ---- ask questions ----------------------------------------------------------
if [ "$NONINTERACTIVE" != "1" ]; then
  echo
  c_info "Rumble channel (slug, id or URL). Multiple: space-separated"
  ask CHANNEL "channel" "usawatchdog"
  echo
  c_info "Summarization:"
  c_info "  none       - lightest, no AI (recommended on <=512MB devices)"
  c_info "  local      - offline llama.cpp model (needs RAM; see note below)"
  c_info "  openrouter - best quality, needs an API key"
  choose SUMMARIZE "summarizer" "none|local|openrouter"

  if [ "$SUMMARIZE" = "local" ]; then
    # Pick a model that fits the memory we actually have available.
    if [ "${AVAIL_MB:-0}" -lt 400 ]; then
      c_warn "only ~${AVAIL_MB}MB RAM available; local models will swap to SD."
      c_warn "a 512MB Pi Zero 2 W running Pi-hole should use 'none' or 'openrouter'."
    fi
    choose MODEL_LOCAL "local model" \
      "gemma-3-270m-it-q4_k_m|smollm2-360m-instruct-q4_k_m|smollm2-135m-instruct-q4_k_m|qwen3-0.6b-q4_k_m"
  elif [ "$SUMMARIZE" = "openrouter" ]; then
    ask OR_KEY "openrouter api key" "sk-or-REPLACE_ME"
    ask MODEL_REMOTE "remote model" "openai/gpt-4o-mini"
  fi
fi
[ -z "$SUMMARIZE" ] && SUMMARIZE="none"
[ -z "$MODEL_LOCAL" ] && MODEL_LOCAL="gemma-3-270m-it-q4_k_m"

# ---- fetch source -----------------------------------------------------------
c_ok "fetching RumblingPodcast"
rm -rf "$SRC_DIR"
git clone --depth 1 --branch "$BRANCH" "$REPO" "$SRC_DIR" \
  || die "could not clone $REPO (set RP_REPO/RP_BRANCH if you use a fork)"

c_ok "installing to $RP_ROOT"
mkdir -p "$RP_ROOT"/{bin,config,data,logs,run,models}
mkdir -p "$RP_ROOT/data"/{audio,transcripts,summaries,meta,video}
cp -r "$SRC_DIR/bin" "$RP_ROOT/"
cp -r "$SRC_DIR/lib" "$RP_ROOT/"
cp -r "$SRC_DIR/systemd" "$RP_ROOT/"
chmod +x "$RP_ROOT/bin/"*
chown -R "${SUDO_USER:-root}:${SUDO_USER:-root}" "$RP_ROOT" 2>/dev/null || true

# ---- config -----------------------------------------------------------------
CONF="$RP_ROOT/config/rp.conf"
if [ -f "$CONF" ]; then
  c_info "keeping existing config at $CONF"
else
  cp "$SRC_DIR/config/rp.conf.example" "$CONF"
fi
set_conf() { sed -i "s#^[[:space:]]*$1[[:space:]]*=.*#${1} = ${2}#" "$CONF"; }
set_conf channels "$CHANNEL"
set_conf summarize "$SUMMARIZE"
set_conf model_local "$MODEL_LOCAL"
set_conf model_remote "$MODEL_REMOTE"
[ -n "$OR_KEY" ] && set_conf openrouter_key "$OR_KEY"
c_ok "configured: channel=$CHANNEL summarize=$SUMMARIZE"

# ---- dependencies -----------------------------------------------------------
c_ok "installing dependencies (ffmpeg, jq, curl)"
DEBIAN_FRONTEND=noninteractive apt-get update -qq 2>/dev/null
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  ffmpeg jq curl ca-certificates 2>/dev/null || c_warn "some packages may be missing"

# ---- yt-dlp -----------------------------------------------------------------
if [ ! -x "$RP_ROOT/bin/yt-dlp" ]; then
  c_ok "installing yt-dlp (standalone binary, no Python runtime required)"
  case "$(uname -m)" in
    aarch64) A=aarch64 ;;
    armv7l)  A=armv7l  ;;
    *)       A=""       ;;
  esac
  curl -fL --retry 3 -o "$RP_ROOT/bin/yt-dlp" \
    "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_linux${A:+_$A}" \
    || die "yt-dlp download failed"
  chmod 755 "$RP_ROOT/bin/yt-dlp"
fi

# ---- systemd ----------------------------------------------------------------
c_ok "registering systemd services"
cp "$RP_ROOT/systemd/rumblingpodcast-"*.service /etc/systemd/system/
systemctl daemon-reload
install -m 755 "$RP_ROOT/bin/rp-ctl" /usr/local/bin/rp-ctl

c_ok "starting services"
systemctl enable --now rumblingpodcast-http.service
systemctl enable --now rumblingpodcast-worker.service

PORT="$(sed -n 's/^[[:space:]]*serve_port[[:space:]]*=[[:space:]]*//p' "$CONF" | tail -1 | tr -d '[:space:]')"
PORT="${PORT:-8088}"
IP="$(hostname -I 2>/dev/null | awk '{print $1}')"

echo
c_ok "RumblingPodcast is running"
echo
printf '    Feed URL : http://%s:%s/feed.xml\n' "${IP:-<pi-ip>}" "$PORT"
printf '    Config   : %s\n' "$CONF"
printf '    Control  : sudo rp-ctl status | disable | pause | uninstall\n'
echo
c_info "In Apple Podcasts: add a podcast by URL and paste the feed URL above."
c_info "It will work on your Wi-Fi. For off-LAN access see README (Cloudflare Tunnel)."
echo
