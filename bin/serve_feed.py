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
import socket
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

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
        if path in ("", "."):
            path = "feed.xml"
        root = os.path.realpath(self.server.root)
        full = os.path.realpath(os.path.join(root, path))
        if not (full == root or full.startswith(root + os.sep)):
            return None
        if os.path.isdir(full):
            full = os.path.join(full, "feed.xml")
            if not os.path.isfile(full):
                return None
        return full

    def do_HEAD(self):
        self.serve(head_only=True)

    def do_GET(self):
        self.serve(head_only=False)

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


def main():
    ap = argparse.ArgumentParser(description="Serve the RumblingPodcast feed")
    ap.add_argument("-p", "--port", type=int, default=8088)
    ap.add_argument("-d", "--dir", default="/opt/rumblingpodcast/data")
    args = ap.parse_args()

    root = os.path.abspath(args.dir)
    if not os.path.isdir(root):
        sys.stderr.write("not a directory: %s\n" % root)
        return 1

    Server.root = root
    httpd = Server(("", args.port), FeedHandler)
    sys.stderr.write("RumblingPodcast serving %s on port %d\n" % (root, args.port))
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
