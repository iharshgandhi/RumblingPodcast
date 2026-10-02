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

# Port validity, and whether something is already listening on it.
port_in_use() { echo "$PORTS_IN_USE" | grep -qx "$1"; }
port_is_pi_hole() {
  case "$1" in
    53|80|443) return 0 ;;
    *)          return 1 ;;
  esac
}
port_valid() {
  case "$1" in
    ''|*[!0-9]*) return 1 ;;
  esac
  [ "$1" -ge 1024 ] && [ "$1" -le 65535 ]
}

# A port already recorded in an existing install always wins, so re-running the
# installer never silently moves a feed people have already subscribed to.
if [ -f "$RP_ROOT/config/rp.conf" ]; then
  EXISTING_PORT="$(sed -n 's/^[[:space:]]*serve_port[[:space:]]*=[[:space:]]*//p' \
                    "$RP_ROOT/config/rp.conf" 2>/dev/null | tail -1 | tr -d '[:space:]')"
  if port_valid "$EXISTING_PORT"; then
    SERVE_PORT="$EXISTING_PORT"
  fi
fi

if ! port_valid "$SERVE_PORT"; then
  for p in 8088 8090 8080 9090 8099; do
    port_valid "$p" || continue
    port_in_use "$p" && continue
    SERVE_PORT="$p"; break
  done
  port_valid "$SERVE_PORT" || SERVE_PORT=8088
fi

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
SERVE_PORT="${RP_SERVE_PORT:-}"

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
c_info "3) Which port should the podcast feed be served on?"
c_info "   This is the number in the feed URL. It is saved permanently, so"
c_info "   re-running this installer later will not change it."
if port_valid "$EXISTING_PORT"; then
  c_ok "you already chose port ${EXISTING_PORT} - keeping it"
  SERVE_PORT="$EXISTING_PORT"
fi
while :; do
  ask SERVE_PORT "port (1024-65535, never 53/80/443 which pi-hole uses)" "$SERVE_PORT"
  if ! port_valid "$SERVE_PORT"; then
    c_err "'${SERVE_PORT}' is not a usable port (use a number 1024-65535)"
    continue
  fi
  if port_is_pi_hole "$SERVE_PORT"; then
    c_err "port ${SERVE_PORT} belongs to pi-hole - choose another"
    continue
  fi
  # Already served by us is fine; anything else already listening is not.
  if port_in_use "$SERVE_PORT" && ! ss -tuln 2>/dev/null \
       | grep -q "rumblingpodcast"; then
    c_warn "something is already listening on port ${SERVE_PORT}"
    if [ "$NONINTERACTIVE" != 1 ]; then
      read -r -p "    use it anyway? [y/N]: " ok || true
      case "${ok:-n}" in y|Y) ;; *) continue ;; esac
    else
      continue
    fi
  fi
  break
done
c_ok "port ${SERVE_PORT} will be saved permanently"

c_info ""
c_info "4) When should it look for new videos?"
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
# whisper.cpp transcribes videos that have no Rumble captions. Most Rumble
# videos do have them, but a channel that streams live often does not, and
# without this those episodes silently get no transcript at all. It is optional:
# if it cannot be installed, say so plainly rather than leaving a broken
# fallback that looks like a success.
if ! command -v whisper-cli >/dev/null 2>&1; then
  if apt-get install -y --no-install-recommends whisper-cpp >/dev/null 2>&1 \
     && command -v whisper-cli >/dev/null 2>&1; then
    c_ok "whisper-cli ready (fallback transcription)"
  else
    c_warn "whisper-cli unavailable - videos without Rumble captions will have no transcript"
    c_warn "  install it later with: sudo apt-get install whisper-cpp"
  fi
fi

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

# yt-dlp ships as a standalone binary rather than a distro package: the Debian
# copy is far older, and the PyInstaller build needs no Python on the target.
# That also means apt knows nothing about it, so refresh it here rather than
# skipping: a stale yt-dlp breaks extractors quietly, and this is the natural
# moment to pick up a fix. rp-update verifies the new binary before it replaces
# a working one, and is safe to run while other tools share the file.
c_ok "installing yt-dlp (standalone binary — no Python needed for downloads)"
if [ -x "$RP_ROOT/bin/rp-update" ]; then
  "$RP_ROOT/bin/rp-update" yt-dlp 2>&1 | sed 's/^/  /' \
    || c_warn "yt-dlp refresh failed; keeping the version already installed"
else
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

# ---- config -------------------------------------------------------------
CONF="$RP_ROOT/config/rp.conf"
if [ -f "$CONF" ]; then
  # Never clobber live settings: rp.conf holds the API key and channel list.
  c_ok "keeping your existing settings"
  cp -p "$CONF" "$CONF.bak.$(date +%Y%m%d-%H%M%S)"
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
# Both units need the run-as user substituted in.
sed "s/__RP_USER__/$APP_USER/g" \
  "$RP_ROOT/systemd/rumblingpodcast-worker.service" \
  > /etc/systemd/system/rumblingpodcast-worker.service
sed "s/__RP_USER__/$APP_USER/g" \
  "$RP_ROOT/systemd/rumblingpodcast-http.service" \
  > /etc/systemd/system/rumblingpodcast-http.service
# The web UI edits rp.conf, so that one file must be writable by the service.
chown "$APP_USER:$APP_USER" "$CONF" 2>/dev/null || true
chmod 600 "$CONF"

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

install -m 755 "$RP_ROOT/bin/rp"        /usr/local/bin/rp
install -m 755 "$RP_ROOT/bin/rp-ctl"    /usr/local/bin/rp-ctl
install -m 755 "$RP_ROOT/bin/rp-update" /usr/local/bin/rp-update 2>/dev/null || true
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
