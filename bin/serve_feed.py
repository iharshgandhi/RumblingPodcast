#!/usr/bin/env python3
"""
RumblingPodcast - https://github.com/iharshgandhi/RumblingPodcast
Copyright (C) 2026 Harsh Gandhi (harshgandhi.com) / Buho Smart Tools (buho.co.in)

Licensed under the GNU General Public License v3.0 or later.
This is an experimental project provided "AS IS", with NO WARRANTY and no
liability. It contains no copyrighted material and no circumvention code.
See DISCLAIMER.md. You are responsible for using it lawfully.
"""
#!/usr/bin/env python3
"""
RumblingPodcast feed server.

Tiny dependency-free static server for the podcast feed and its audio.
busybox httpd does not emit Content-Type for .m4a, and podcast clients refuse
episodes served as text/html, so we serve with correct MIME types instead.

Standard library only (no pip installs), serves a single directory, and
supports Range requests because podcast apps resume large downloads.

Author: Harsh Gandhi (harshgandhi.com) / Buho Smart Tools (buho.co.in)
"""
import os
import sys
import json
import glob
import socket
import argparse
import urllib.parse
import subprocess
import threading
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rp_api
import patio_theme
import rp_ui

def _rfc822_epoch(s):
    """Parse an RFC822 pubDate into an epoch, or 0 if it will not parse."""
    try:
        from email.utils import parsedate_to_datetime
        return int(parsedate_to_datetime(s).timestamp())
    except Exception:
        return 0


DESCRIPTIONS = {
    "channels": "Rumble channels you follow. Each becomes its own podcast.",
    "serve_port": "The port in your feed URL. Keep it once chosen.",
    "feed_base_url": "Leave blank to use this machine's address automatically.",
    "run_time": "Local time for the nightly run (24-hour).",
    "retention_days": "Downloaded audio older than this is deleted.",
    "max_age_days": "Only videos published within this many days are grabbed.",
    "scan_interval_hours": "How often to look for new videos.",
    "sleep_between_videos": "Pause between videos to stay gentle on the machine.",
    "loop_sleep": "Idle sleep between scan cycles.",
    "channel_meta_days": "How often to refresh each channel's name and artwork.",
    "summarize": "none = no AI; openrouter = free AI summaries; local = offline model.",
    "model_remote": "auto picks the fastest free model for you.",
    "remote_max_chars": "How much transcript is sent for summarising.",
    "remote_timeout": "Give up on a model after this many seconds.",
    "remote_max_tries": "How many free models to try before giving up.",
    "or_cache_ttl": "How long the free-model list is cached.",
    "extractive_sentences": "Sentences kept by the built-in offline summariser.",
    "model_local": "Only used when summarize = local.",
    "llm_threads": "CPU threads for the local model.",
    "llm_chunk_words": "Transcript words per chunk when summarising.",
    "use_captions": "Use Rumble's own captions instead of transcribing.",
    "whisper_model": "Only used when a video has no captions.",
    "whisper_threads": "CPU threads for transcription.",
    "download_thumbnails": "Fetch episode artwork.",
    "podcast_title": "Shown as the feed title.",
    "podcast_description": "Shown as the feed description.",
    "podcast_author": "Author name shown in the podcast app.",
    "podcast_email": "Contact address shown in the feed.",
    "podcast_language": "Two-letter language code, e.g. en.",
    "timezone": "Your local timezone, e.g. Europe/London.",
    "skip_existing": "Do not re-download videos already processed.",
}

MIME = {
    ".xml": "application/rss+xml; charset=utf-8",
    ".rss": "application/rss+xml; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".m4a": "audio/mp4",
    ".mp4": "video/mp4",
    ".mp3": "audio/mpeg",
    ".aac": "audio/aac",
    ".txt": "text/plain; charset=utf-8",
    ".json": "application/json",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".vtt": "text/vtt; charset=utf-8",
    ".srt": "application/x-subrip",
}


class FeedHandler(BaseHTTPRequestHandler):
    server_version = "RumblingPodcast"
    sys_version = ""
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        if os.environ.get("RP_HTTP_VERBOSE"):
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def resolve(self, path):
        path = path.split("?", 1)[0].split("#", 1)[0]
        path = os.path.normpath(path).lstrip("/")
        # The site root and any directory show the browsable index page, which
        # lists each channel's podcast feed. feed.xml remains available for
        # anyone who still have the old single-feed URL.
        index_page = "index.html"
        if path in ("", "."):
            path = index_page
        root = os.path.realpath(self.server.root)
        full = os.path.realpath(os.path.join(root, path))
        if not (full == root or full.startswith(root + os.sep)):
            return None
        if os.path.isdir(full):
            candidate = os.path.join(full, index_page)
            if not os.path.isfile(candidate):
                candidate = os.path.join(full, "feed.xml")
            full = candidate
            if not os.path.isfile(full):
                return None
        return full

    # ---------------- session helpers ----------------
    def cookie(self, name):
        raw = self.headers.get("Cookie") or ""
        for part in raw.split(";"):
            k, _, v = part.strip().partition("=")
            if k == name:
                return v
        return None

    def ensure_session(self):
        """Return (sid, csrf); mint a session if the caller has none."""
        sid = self.cookie("rp_sid")
        s = self.server.sessions.get(sid) if sid else None
        if not s:
            sid, csrf = self.server.sessions.create()
            self._set_cookie = ("rp_sid=%s; Path=/; HttpOnly; SameSite=Lax; "
                                "Max-Age=86400" % sid)
        else:
            csrf = s["csrf"]
        return sid, csrf

    def send_bytes(self, body, ctype, status=200):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        cookie = getattr(self, "_set_cookie", None)
        if cookie:
            self.send_header("Set-Cookie", cookie)
            self._set_cookie = None
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def send_json(self, obj, status=200):
        self.send_bytes(json.dumps(obj).encode("utf-8"),
                        "application/json", status)

    # ---------------- API ----------------
    def api_ui(self):
        """Payload for the UI. The API key is reported as a boolean only."""
        _, csrf = self.ensure_session()
        conf = rp_api.read_conf(self.server.conf)
        base = self.server.public_base()

        channels = []
        for slug in (conf.get("channels") or "").split():
            name = slug
            name_file = os.path.join(self.server.root, "channels", slug + ".name")
            if os.path.isfile(name_file):
                with open(name_file, encoding="utf-8",
                          errors="replace") as fh:
                    name = fh.read().strip() or slug
            count = 0
            feed = os.path.join(self.server.root, "feeds", slug + ".xml")
            if os.path.isfile(feed):
                with open(feed, encoding="utf-8",
                          errors="replace") as fh:
                    count = fh.read().count("<item>")
            channels.append({
                "slug": slug,
                "name": name,
                "count": count,
                "art": base + "/media/channel-%s.jpg" % slug,
            })

        safe = {k: v for k, v in conf.items()
                if k not in rp_api.SECRET_KEYS}
        schema = {}
        for key, ftype, label, secret in rp_api.FIELDS:
            if secret:
                continue
            schema[key] = {"label": label, "type": ftype,
                           "desc": DESCRIPTIONS.get(key, "")}

        return {
            "channels": channels,
            "config": safe,
            "schema": schema,
            "hasKey": bool((conf.get("openrouter_key") or "").strip()),
            "base": base,
            "port": int(conf.get("serve_port") or self.server.port),
        }

    def api_config(self):
        """Write settings. Requires the session's CSRF token."""
        sid = self.cookie("rp_sid")
        token = self.headers.get("X-CSRF-Token")
        if not self.server.sessions.valid_csrf(sid, token):
            return self.send_json(
                {"error": "invalid or missing CSRF token - reload the page"}, 403)
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if length > 65536:
                return self.send_json({"error": "request too large"}, 413)
            payload = json.loads(self.rfile.read(length) or b"{}")
            updates = payload.get("updates")
            if not isinstance(updates, dict) or not updates:
                return self.send_json({"error": "nothing to save"}, 400)
            known = {f[0] for f in rp_api.FIELDS}
            cleaned = {}
            for key, val in updates.items():
                if key not in known:
                    return self.send_json(
                        {"error": "unknown setting: %s" % key}, 400)
                try:
                    cleaned[key] = rp_api.validate(key, val)
                except rp_api.ConfigError as exc:
                    return self.send_json(
                        {"error": "%s: %s" % (key, exc)}, 400)
            rp_api.write_conf(self.server.conf, cleaned)
        except (ValueError, TypeError):
            return self.send_json({"error": "malformed request"}, 400)
        except OSError as exc:
            return self.send_json(
                {"error": "could not write config: %s" % exc}, 500)

        conf = rp_api.read_conf(self.server.conf)
        safe = {k: v for k, v in conf.items()
                if k not in rp_api.SECRET_KEYS}
        self.send_json({"ok": True, "config": safe})

    def api_episodes(self):
        """Every published episode, newest first, for the in-browser browser.

        Reads the same per-channel feeds that are served as RSS, so what a user
        sees here is exactly what a podcast app would.
        """
        slug = urllib.parse.parse_qs(
            urllib.parse.urlparse(self.path).query).get("channel", [""])[0]
        base = self.server.public_base()
        out = []
        feeddir = os.path.join(self.server.root, "feeds")
        for fn in sorted(os.listdir(feeddir) if os.path.isdir(feeddir) else []):
            if not fn.endswith(".xml"):
                continue
            ch_slug = fn[:-4]
            if slug and ch_slug != slug:
                continue
            path = os.path.join(feeddir, fn)
            try:
                tree = ET.parse(path)
            except (ET.ParseError, OSError):
                continue
            rss = tree.getroot()
            chan = rss.find("channel")
            if chan is None:
                continue
            name_el = chan.find("title")
            chan_name = (name_el.text or "").strip() if name_el is not None \
                else ch_slug
            # The feed's own <title> is the channel name; the per-channel title
            # element inside each item is the episode title.
            for item in chan.findall("item"):
                def txt(tag):
                    el = item.find(tag)
                    return (el.text or "").strip() if el is not None else ""
                dur = txt("{http://www.itunes.com/dtds/podcast-1.0.dtd}duration")
                art = item.find("{http://www.itunes.com/dtds/podcast-1.0.dtd}image")
                art_url = art.get("href") if art is not None else ""
                enc = item.find("enclosure")
                guid = txt("guid")
                vid = guid.replace("rumble-", "") if guid.startswith(
                    "rumble-") else ""
                live = "0"
                if vid:
                    meta = os.path.join(self.server.root, "meta", vid + ".meta")
                    try:
                        for line in open(meta, encoding="utf-8",
                                         errors="replace"):
                            if line.startswith("LIVE="):
                                live = line.split("=", 1)[1].strip()
                    except OSError:
                        pass
                out.append({
                    "channel": ch_slug,
                    "channelName": chan_name,
                    "title": txt("title"),
                    "description": txt("description"),
                    "date": txt("pubDate"),
                    # Sort on a real epoch. Sorting the RFC822 string itself puts
                    # "Thu, 01 Oct" under "T" and below every September entry,
                    # so newest-first silently became wrong for any month whose
                    # weekday letter sorts low.
                    "_epoch": _rfc822_epoch(txt("pubDate")),
                    "duration": dur,
                    "audio": enc.get("url") if enc is not None else "",
                    "bytes": int(enc.get("length") or 0) if enc is not None else 0,
                    "art": art_url or (base + "/media/channel-%s.jpg" % ch_slug),
                    "page": ("https://rumble.com/%s" % vid) if vid else "",
                    "transcript": (base + "/media/%s.vtt" % vid) if vid else "",
                    "live": live == "1",
                })
        out.sort(key=lambda e: e["_epoch"], reverse=True)
        for e in out:
            e.pop("_epoch", None)
        self.send_json({"episodes": out, "base": base})

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        if path == "/api/config":
            return self.api_config()
        if path == "/api/refresh":
            return self.api_refresh()
        return self.send_json({"error": "not found"}, 404)

    def api_refresh(self):
        """Kick off one scan now, instead of waiting for the nightly timer.

        A full fetch can take many minutes (audio download, transcription,
        summarising), so this starts it in the background and reports back
        immediately rather than holding the browser open.
        """
        sid = self.cookie("rp_sid")
        token = self.headers.get("X-CSRF-Token")
        if not self.server.sessions.valid_csrf(sid, token):
            return self.send_json(
                {"error": "invalid or missing CSRF token - reload the page"}, 403)

        # Never stack runs: the worker takes a lock and exits if one is live.
        if self.server.refresh_running:
            return self.send_json(
                {"error": "a scan is already running - try again shortly"}, 409)

        self.server.refresh_running = True
        worker = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "worker")
        # Derive the app root from the data dir the server was started with,
        # rather than guessing via "..": data/ is a sibling of run/ and logs/,
        # but resolving through a symlinked data dir would land in the wrong
        # place and the worker would fail silently.
        app_root = os.path.dirname(os.path.abspath(self.server.root))
        logdir = os.path.join(app_root, "logs")
        tmpdir = os.path.join(app_root, "run", "tmp")

        def run():
            try:
                os.makedirs(logdir, exist_ok=True)
                os.makedirs(tmpdir, exist_ok=True)
                env = dict(os.environ)
                env["TMPDIR"] = tmpdir
                env["RP_CONFIG"] = self.server.conf
                env["RP_ROOT"] = app_root
                out = open(os.path.join(logdir, "refresh.log"), "ab")
                try:
                    subprocess.run([worker, "--once"], stdout=out, stderr=out,
                                   env=env, timeout=6 * 3600, check=False)
                finally:
                    out.close()
            except Exception:
                pass
            finally:
                self.server.refresh_running = False

        threading.Thread(target=run, daemon=True).start()
        self.send_json({"ok": True,
                        "message": "Scan started. This can take a few "
                                   "minutes; reload in a little while."})

    def do_HEAD(self):
        self.serve(head_only=True)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/ui":
            return self.send_json(self.api_ui())
        if path == "/api/episodes":
            return self.api_episodes()
        # The web UI replaces the bare index page; index.html still works.
        if path in ("/", "/index.html", "/ui"):
            _, csrf = self.ensure_session()
            keys = json.dumps([f[0] for f in rp_api.FIELDS])
            page = (rp_ui.PAGE
                    .replace("__THEME__", patio_theme.THEME_CSS)
                    .replace("__CSRF__", csrf)
                    .replace("__DATA_KEYS__", keys))
            return self.send_bytes(page.encode("utf-8"),
                                   "text/html; charset=utf-8")
        return self.serve(head_only=False)

    def serve(self, head_only=False):
        full = self.resolve(self.path)
        if not full or not os.path.isfile(full):
            body = b"404 Not Found\n"
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if not head_only:
                self.wfile.write(body)
            return

        size = os.path.getsize(full)
        ctype = MIME.get(os.path.splitext(full)[1].lower(), "application/octet-stream")
        start, end, status = 0, size - 1, 200

        rng = self.headers.get("Range")
        if rng and rng.startswith("bytes="):
            spec = rng[6:].split(",")[0].strip()
            try:
                if spec.startswith("-"):
                    start = max(0, size - int(spec[1:]))
                else:
                    a, _, b = spec.partition("-")
                    start = int(a)
                    end = int(b) if b else size - 1
                if start >= size:
                    start, end = 0, size - 1
                else:
                    end = min(end, size - 1)
                status = 206
            except ValueError:
                start, end, status = 0, size - 1, 200

        length = max(0, end - start + 1)
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(length))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Last-Modified", self.date_time_string(os.path.getmtime(full)))
        if status == 206:
            self.send_header("Content-Range", "bytes %d-%d/%d" % (start, end, size))
        self.end_headers()
        if head_only:
            return

        try:
            with open(full, "rb") as fh:
                fh.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = fh.read(min(65536, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    address_family = socket.AF_INET
    root = "/opt/rumblingpodcast/data"
    conf = "/opt/rumblingpodcast/config/rp.conf"
    port = 8088
    sessions = None  # rp_api.Sessions, set in main()
    # Guards the manual-refresh button so two scans cannot overlap.
    refresh_running = False

    def public_base(self):
        """Base URL to hand the browser, so copied feed links actually work."""
        try:
            conf = rp_api.read_conf(self.conf)
        except OSError:
            conf = {}
        base = (conf.get("feed_base_url") or "").strip().rstrip("/")
        if base and "PI_IP" not in base and "localhost" not in base:
            return base
        host = os.environ.get("RP_PUBLIC_HOST") or local_ip() or "localhost"
        return "http://%s:%d" % (host, int(conf.get("serve_port") or self.port))


def local_ip():
    """Best-effort LAN address, without sending anything to the network."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()


def read_conf_port(conf):
    """Read serve_port from the live config so the chosen port sticks forever.

    The value is what the installer recorded; the systemd unit passes -p only
    as a fallback for a fresh install.
    """
    try:
        with open(conf, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.split("#", 1)[0].strip()
                if line.startswith("serve_port"):
                    _, _, val = line.partition("=")
                    val = val.strip().strip('"').strip("'")
                    if val.isdigit() and 1024 <= int(val) <= 65535:
                        return int(val)
    except OSError:
        pass
    return None


def main():
    ap = argparse.ArgumentParser(description="Serve the RumblingPodcast feed")
    ap.add_argument("-p", "--port", type=int, default=None,
                    help="fallback port if serve_port is unset in the config")
    ap.add_argument("-d", "--dir", default="/opt/rumblingpodcast/data")
    ap.add_argument("-c", "--conf", default="/opt/rumblingpodcast/config/rp.conf")
    args = ap.parse_args()

    port = read_conf_port(args.conf) or args.port or 8088
    root = os.path.abspath(args.dir)
    if not os.path.isdir(root):
        sys.stderr.write("not a directory: %s\n" % root)
        return 1

    Server.root = root
    Server.conf = os.path.abspath(args.conf)
    Server.port = port
    Server.sessions = rp_api.Sessions()
    httpd = Server(("", port), FeedHandler)
    sys.stderr.write("RumblingPodcast serving %s on port %d\n" % (root, port))
    sys.stderr.flush()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
