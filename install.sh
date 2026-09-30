#!/bin/bash
# RumblingPodcast - https://github.com/iharshgandhi/RumblingPodcast
# Copyright (C) 2026 Harsh Gandhi (harshgandhi.com) / Buho Smart Tools (buho.co.in)
#
# Licensed under the GNU General Public License v3.0 or later.
# This is an experimental project provided "AS IS", with NO WARRANTY and no
# liability. It contains no copyrighted material and no circumvention code.
# See DISCLAIMER.md. You are responsible for using it lawfully.
#
# ---------------------------------------------------------------------------
# ONE-CLICK INSTALLER
#
#   curl -fsSL https://raw.githubusercontent.com/iharshgandhi/RumblingPodcast/main/install.sh | sudo bash
#
# It asks a handful of plain-English questions, installs everything, arms a
# systemd timer (so you never touch cron), and prints the feed URL to paste
# into your podcast app. Safe to re-run; your existing settings are kept.
#
# Unattended:
#   RP_CHANNEL=usawatchdog RP_SUMMARIZE=none RP_NONINTERACTIVE=1 ./install.sh
# ---------------------------------------------------------------------------
set -uo pipefail

REPO="${RP_REPO:-https://github.com/iharshgandhi/RumblingPodcast.git}"
BRANCH="${RP_BRANCH:-main}"
RP_ROOT="${RP_ROOT:-/opt/rumblingpodcast}"
SRC_DIR="${RP_SRC_DIR:-/usr/local/share/rumblingpodcast-src}"
NONINTERACTIVE="${RP_NONINTERACTIVE:-0}"

if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  B=$'\033[1m'; G=$'\033[32m'; Y=$'\033[33m'; R=$'\033[31m'; C=$'\033[36m'; N=$'\033[0m'
else
  B=""; G=""; Y=""; R=""; C=""; N=""
fi
c_ok()   { printf '%s==>%s %s\n' "$G" "$N" "$*"; }
c_info() { printf '    %s\n' "$*"; }
c_warn() { printf '%s!! %s%s\n'  "$Y" "$*" "$N"; }
c_err()  { printf '%sxx %s%s\n'  "$R" "$*" "$N" >&2; }
c_head() { printf '\n%s%s%s\n' "$B" "$*" "$N"; }
die()    { c_err "$*"; exit 1; }

ask() {        # ask <varname> <prompt> <default>
  local __v="$1" __p="$2" __d="$3" __a
  if [ "$NONINTERACTIVE" = 1 ]; then
    printf -v "$__v" '%s' "${!__v:-$__d}"; return 0
  fi
  read -r -p "    $__p${__d:+ [$__d]}: " __a || true
  [ -z "$__a" ] && __a="$__d"
  printf -v "$__v" '%s' "$__a"
  return 0
}
ask_secret() { # hidden input, typed twice
  local __v="$1" __p="$2" __a __b
  [ "$NONINTERACTIVE" = 1 ] && return 0
  printf '    %s (input hidden): ' "$__p"; read -rs __a || true; echo
  printf '    type it again: '; read -rs __b || true; echo
  if [ "$__a" != "$__b" ]; then c_err "they did not match"; return 1; fi
  if [ -z "$__a" ]; then c_warn "left empty — set it later with: rp key set"; return 1; fi
  printf -v "$__v" '%s' "$__a"
  return 0
}
choose() {     # choose <varname> <prompt> "a|b|c"
  local __v="$1" __p="$2" __opts="$3" __a n=1 o
  if [ "$NONINTERACTIVE" = 1 ]; then
    printf -v "$__v" '%s' "${!__v:-${__opts%%|*}}"; return 0
  fi
  printf '    %s\n' "$__p"
  local IFS='|'
  for o in $__opts; do printf '      %d) %s\n' "$n" "$o"; n=$((n+1)); done
  unset IFS
  read -r -p "    choose [1]: " __a || true
  [ -z "$__a" ] && __a=1
  n=1
  for o in $__opts; do
    if [ "$n" = "$__a" ]; then printf -v "$__v" '%s' "$o"; return 0; fi
    n=$((n+1))
  done
  printf -v "$__v" '%s' "${__opts%%|*}"
}

[ "$(id -u)" -eq 0 ] || die "needs root. Run:
    curl -fsSL https://raw.githubusercontent.com/iharshgandhi/RumblingPodcast/main/install.sh | sudo bash"

# ---------------------------------------------------------------- preflight
c_ok "checking your system"
RW="$(findmnt -no OPTIONS / 2>/dev/null | tr ',' '\n' | grep -E '^(rw|ro)$' | head -1)"
[ "$RW" = "ro" ] && die "your root filesystem is READ-ONLY. Fix with: sudo mount -o remount,rw /"
c_info "root filesystem is writable"

ARCH="$(uname -m)"
case "$ARCH" in
  aarch64|armv7l|armv6l) c_info "architecture: $ARCH (Raspberry Pi)" ;;
  x86_64)                c_info "architecture: x86_64" ;;
  *) c_warn "unusual architecture: $ARCH — this may not work" ;;
esac

TOTAL_MB="$(awk '/MemTotal/{printf "%d", $2/1024}' /proc/meminfo 2>/dev/null || echo 0)"
AVAIL_MB="$(awk '/MemAvailable/{printf "%d", $2/1024}' /proc/meminfo 2>/dev/null || echo 0)"
c_info "memory: ${TOTAL_MB}MB total, about ${AVAIL_MB}MB free"

# Our port must never collide with an existing listener (pi-hole uses 80/443/53).
PORTS_IN_USE="$(ss -tuln 2>/dev/null | awk '{print $5}' | sed 's/.*://' | sort -u)"
pick_port() {
  local p
  for p in 8088 8090 8080 9090 8099; do
    echo "$PORTS_IN_USE" | grep -qx "$p" || { printf '%s' "$p"; return 0; }
  done
  printf '8088'
}
SERVE_PORT="$(pick_port)"

if command -v pihole >/dev/null; then
  c_ok "pi-hole detected — it will not be touched"
  c_info "pi-hole keeps 53/80/443; this app will use ${SERVE_PORT}"
fi

# ---------------------------------------------------------------- questions
CHANNEL="${RP_CHANNEL:-}"
SUMMARIZE="${RP_SUMMARIZE:-}"
OR_KEY="${RP_OPENROUTER_KEY:-}"
LOCAL_MODEL="${RP_MODEL_LOCAL:-}"
RETENTION="${RP_RETENTION_DAYS:-30}"
MAXAGE="${RP_MAX_AGE_DAYS:-7}"
RUN_TIME="${RP_RUN_TIME:-02:00}"

c_head "Let's set you up (about 2 minutes)"
c_info "Press Enter to accept the value shown in [brackets]."

c_info ""
c_info "1) Which Rumble channels should the podcast follow?"
c_info "   Paste anything you have. Several at once: separate with spaces."
ask CHANNEL "channels" "https://rumble.com/c/usawatchdog"

c_info ""
c_info "2) Summaries — a short written recap of each episode."
choose SUMMARIZE "how should summaries be made?" \
  "free AI via OpenRouter (needs a free API key, recommended)|no AI - fastest and lightest|local AI model (needs 300MB+ free RAM)"
case "$SUMMARIZE" in
  "free AI via OpenRouter"*) SUMMARIZE="openrouter" ;;
  "no AI - fastest and lightest") SUMMARIZE="none" ;;
  "local AI model"*) SUMMARIZE="local" ;;
esac

if [ "$SUMMARIZE" = "openrouter" ]; then
  c_info ""
  c_info "   Get a free key at https://openrouter.ai/keys (sign in, Create Key)."
  c_info "   Only free models are ever selected, so this should cost nothing."
  if ask_secret OR_KEY "OpenRouter API key"; then
    case "$OR_KEY" in
      sk-or-v1-*) c_ok "key looks right" ;;
      *) c_warn "does not start with sk-or-v1- — saving anyway" ;;
    esac
  fi
fi

if [ "$SUMMARIZE" = "local" ]; then
  if [ "$AVAIL_MB" -lt 400 ] 2>/dev/null; then
    c_warn "only ~${AVAIL_MB}MB RAM free — local AI will thrash and may swap."
    c_warn "on a small Pi running pi-hole, free AI or 'no AI' is much better."
    if [ "$NONINTERACTIVE" != 1 ]; then
      read -r -p "    switch to free AI instead? [Y/n]: " sw || true
      case "${sw:-y}" in n|N) ;; *) SUMMARIZE="openrouter" ;; esac
    fi
  fi
  [ "$SUMMARIZE" = "local" ] && choose LOCAL_MODEL "local model" \
    "gemma-3-270m-it-q4_k_m|smollm2-360m-instruct-q4_k_m|qwen3-0.6b-q4_k_m"
fi

c_info ""
c_info "3) When should it look for new videos?"
c_info "   A systemd timer handles this — you never touch cron."
ask RUN_TIME "time of day, 24-hour, your local time" "$RUN_TIME"

ask RETENTION "delete downloaded audio older than this many days" "$RETENTION"
ask MAXAGE    "only consider videos published within this many days" "$MAXAGE"

# ---------------------------------------------------------------- install
c_ok "installing packages"
export DEBIAN_FRONTEND=noninteractive
if ! command -v git >/dev/null; then
  apt-get update -qq 2>/dev/null && apt-get install -y --no-install-recommends git ca-certificates curl 2>/dev/null
fi
MISSING=""
for t in ffmpeg jq curl; do command -v "$t" >/dev/null || MISSING="$MISSING $t"; done
if [ -n "$MISSING" ]; then
  apt-get update -qq 2>/dev/null
  # shellcheck disable=SC2086
  apt-get install -y --no-install-recommends $MISSING 2>/dev/null \
    || c_warn "could not install:$MISSING"
fi
for t in ffmpeg jq curl; do
  command -v "$t" >/dev/null && c_ok "$t ready" || c_err "$t MISSING"
done
# python3 is used only by the feed web server (standard library only).
command -v python3 >/dev/null || {
  apt-get install -y --no-install-recommends python3 2>/dev/null \
    && c_ok "python3 ready (feed server only)" \
    || c_warn "python3 missing — the feed server will not start"
}

c_ok "downloading RumblingPodcast"
rm -rf "$SRC_DIR"
git clone --depth 1 --branch "$BRANCH" "$REPO" "$SRC_DIR" 2>/dev/null \
  || die "could not download from $REPO
    If you already cloned this yourself, run: sudo ./install.sh"

APP_USER="${SUDO_USER:-${RP_USER:-root}}"
[ "$APP_USER" = "root" ] && c_warn "installing as root; set RP_USER=<your-user> to run as a normal user"

c_ok "installing to $RP_ROOT"
mkdir -p "$RP_ROOT"/{bin,config,data,logs,run}
mkdir -p "$RP_ROOT/data"/{audio,transcripts,summaries,meta,feed,video}
mkdir -p "$RP_ROOT/run/tmp"
cp -r "$SRC_DIR/bin" "$SRC_DIR/lib" "$SRC_DIR/systemd" "$RP_ROOT/" 2>/dev/null
cp "$SRC_DIR/VERSION" "$RP_ROOT/" 2>/dev/null
chmod +x "$RP_ROOT/bin/"* 2>/dev/null

c_ok "installing yt-dlp (standalone binary — no Python needed for downloads)"
if [ ! -x "$RP_ROOT/bin/yt-dlp" ]; then
  case "$ARCH" in
    aarch64) A="_aarch64" ;;
    armv7l)  A="_armv7l" ;;
    *)       A="" ;;
  esac
  curl -fL --retry 3 --connect-timeout 20 -o "$RP_ROOT/bin/yt-dlp" \
    "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_linux${A}" \
    || die "could not download yt-dlp"
  chmod 755 "$RP_ROOT/bin/yt-dlp"
fi
c_info "yt-dlp $("$RP_ROOT/bin/yt-dlp" --version 2>/dev/null | head -1)"

# ---- config -------------------------------------------------------------
CONF="$RP_ROOT/config/rp.conf"
if [ -f "$CONF" ]; then
  c_ok "keeping your existing settings"
else
  cp "$SRC_DIR/config/rp.conf.example" "$CONF"
fi
# shellcheck source=/dev/null
. "$RP_ROOT/lib/rp-config.sh"
set_conf channels "$CHANNEL"
set_conf summarize "$SUMMARIZE"
set_conf retention_days "$RETENTION"
set_conf max_age_days "$MAXAGE"
set_conf serve_port "$SERVE_PORT"
set_conf run_time "$RUN_TIME"
[ -n "$LOCAL_MODEL" ] && set_conf model_local "$LOCAL_MODEL"
if [ -n "$OR_KEY" ]; then set_conf openrouter_key "$OR_KEY"; fi
chmod 600 "$CONF"

validate || c_warn "settings have warnings (see above); 'rp test' will show them"
c_ok "channels: $(get_conf channels)"
[ "$SUMMARIZE" = openrouter ] && c_info "summaries: free OpenRouter models only"

# ---- systemd ------------------------------------------------------------
c_ok "setting up the schedule (systemd timer — you never touch cron)"
sed "s/__RP_USER__/$APP_USER/g" \
  "$RP_ROOT/systemd/rumblingpodcast-worker.service" \
  > /etc/systemd/system/rumblingpodcast-worker.service
cp "$RP_ROOT/systemd/rumblingpodcast-http.service" /etc/systemd/system/

cat > /etc/systemd/system/rumblingpodcast-daily.service <<UNIT
[Unit]
Description=RumblingPodcast nightly run (discover, download, transcribe, summarize, publish)
Documentation=https://github.com/iharshgandhi/RumblingPodcast
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$RP_ROOT
Environment=TMPDIR=$RP_ROOT/run/tmp
ExecStart=$RP_ROOT/bin/worker --once
UNIT

# Rewritten on every install so a changed run_time takes effect.
cat > /etc/systemd/system/rumblingpodcast-daily.timer <<UNIT
[Unit]
Description=Run RumblingPodcast nightly at ${RUN_TIME}
Documentation=https://github.com/iharshgandhi/RumblingPodcast

[Timer]
OnCalendar=*-*-* ${RUN_TIME}:00
Persistent=true
RandomizedDelaySec=300

[Install]
WantedBy=timers.target
UNIT

install -m 755 "$RP_ROOT/bin/rp"     /usr/local/bin/rp
install -m 755 "$RP_ROOT/bin/rp-ctl" /usr/local/bin/rp-ctl
chown -R "$APP_USER:$APP_USER" "$RP_ROOT" 2>/dev/null || true

systemctl daemon-reload
systemctl enable --now rumblingpodcast-daily.timer 2>/dev/null \
  && c_ok "nightly timer armed for ${RUN_TIME}" || c_warn "could not arm the timer"
systemctl enable --now rumblingpodcast-http.service 2>/dev/null \
  && c_ok "feed server running on port ${SERVE_PORT}" || c_warn "feed server did not start"

NEXT="$(systemctl list-timers rumblingpodcast-daily.timer --no-pager 2>/dev/null | awk 'NR==2{print $1" "$2" "$3}')"
IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
HOST="$(hostname 2>/dev/null || echo localhost)"

c_head "All done."
printf '    %sAdd this URL to your podcast app:%s\n\n' "$B" "$N"
printf '        http://%s:%s/feed.xml\n\n' "${IP:-$HOST}" "$SERVE_PORT"
c_info "Apple Podcasts:  Libraries -> + -> 'Add a Podcast by URL', paste the link above."
c_warn "that link only works while you are on your home network."
c_info "For listening anywhere, see 'Off-LAN listening' in the README."

c_head "Everyday commands"
cat <<EOF
    sudo rp                 interactive menu
    sudo rp status          what is set up and running
    sudo rp add <channel>   subscribe to another channel
    sudo rp channels        list what you follow
    sudo rp key set         add or change your OpenRouter key
    sudo rp run             process new videos right now
    sudo rp test            check everything is healthy
    sudo rp pause           stop it completely
    sudo rp uninstall       remove it
EOF
c_head "Next scheduled run"
c_info "${NEXT:-see: systemctl list-timers | grep rumbling}"
echo
c_info "Logs:  sudo journalctl -u rumblingpodcast-daily -n 40"
c_info "Docs:  https://github.com/iharshgandhi/RumblingPodcast"
echo
