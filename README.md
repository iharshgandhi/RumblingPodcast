# RumblingPodcast

Turn any [Rumble](https://rumble.com) channel into a podcast feed you can
subscribe to in Apple Podcasts, Overcast, Castro, or any other podcast app.

It runs unattended on a **Raspberry Pi Zero 2 W** — a machine small enough to
share with Pi-hole — and downloads **audio only** (never video), transcribes,
summarizes, and publishes an RSS feed.

**Author: Harsh Gandhi ([harshgandhi.com](https://harshgandhi.com)) ·
[Buho Smart Tools](https://buho.co.in))**

---

## Why this is light

Rumble publishes **auto-generated English captions for every video**. This
project uses them by default, so transcription is essentially free and the CPU
never has to chew through a two-hour audio file. `whisper.cpp` is installed and
used automatically *only* when captions are missing.

No Python runtime is required for downloads: `yt-dlp` is used as a standalone
binary. The rest is bash, `curl`, `jq` and `ffmpeg`.

---

## One-click install

```bash
curl -fsSL https://raw.githubusercontent.com/iharshgandhi/RumblingPodcast/main/install.sh | sudo bash
```

You'll be asked two questions: which channel, and how to summarize. Fully
unattended:

```bash
RP_NONINTERACTIVE=1 RP_CHANNEL=usawatchdog RP_SUMMARIZE=none \
  curl -fsSL https://raw.githubusercontent.com/iharshgandhi/RumblingPodcast/main/install.sh | sudo bash
```

Supported variables: `RP_CHANNEL`, `RP_SUMMARIZE` (`none|local|openrouter`),
`RP_MODEL_LOCAL`, `RP_MODEL_REMOTE`, `RP_OPENROUTER_KEY`, `RP_NONINTERACTIVE`,
`RP_REPO`, `RP_BRANCH`.

---

## Control

| Command | Effect |
|---|---|
| `sudo rp-ctl status` | units, config, episode counts, recent log |
| `sudo rp-ctl disable` | stop processing; the feed keeps serving |
| `sudo rp-ctl pause` | stop everything (zero CPU, no network) |
| `sudo rp-ctl resume` | start again |
| `sudo rp-ctl run-once` | process what's pending right now, then exit |
| `sudo rp-ctl retention` | run the 30-day cleanup now |
| `sudo rp-ctl uninstall` | remove units + app, **keep** data and transcripts |
| `sudo rp-ctl uninstall --purge` | delete absolutely everything |

It never touches Pi-hole's ports (80/443/53) or services.

---

## Subscribe

Feed URL: `http://<pi-ip>:8088/feed.xml`

In Apple Podcasts: **⋯ → Add a Podcast by URL**, paste it. Works on Wi-Fi.

For listening off-LAN, put a [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)
in front and set `feed_base_url` in `config/rp.conf` — no code changes needed.

---

## Configuration

`/opt/rumblingpodcast/config/rp.conf` — plain `key = value`, no quotes needed.

| Key | Default | Notes |
|---|---|---|
| `channels` | `usawatchdog` | slug, numeric id or URL; space-separated for several |
| `max_age_days` | `7` | only videos newer than this |
| `use_captions` | `1` | `0` forces whisper.cpp transcription |
| `summarize` | `none` | `none`, `local`, or `openrouter` |
| `model_local` | `gemma-3-270m-it-q4_k_m` | see table below |
| `model_remote` | `openai/gpt-4o-mini` | any OpenRouter model id |
| `serve_port` | `8088` | deliberately not 80/443 |
| `feed_base_url` | `http://<pi-ip>:8088` | change for a tunnel/domain |
| `retention_days` | `30` | audio + summaries deleted past this; transcripts kept |
| `scan_interval_hours` | `6` | how often channels are polled |
| `sleep_between_videos` | `20` | politeness pause between videos |

### Summarization modes

- **`none`** — no AI. Lightest, always safe. Episodes still carry the full
  transcript in their description.
- **`local`** — offline `llama.cpp` + GGUF model. No API cost, no data leaves
  the device.
- **`openrouter`** — best quality, needs a key.

#### Local model sizes

`rp-summarize --list-models` prints this table on the machine.

| Model | ~Size | Fits 512MB Pi Zero 2 W with Pi-hole? |
|---|---|---|
| `smollm2-135m-instruct-q4_k_m` | 105 MB | yes, but quality is poor |
| `gemma-3-270m-it-q4_k_m` | 253 MB | **yes — recommended** |
| `smollm2-360m-instruct-q4_k_m` | 270 MB | yes, tight |
| `smollm2-360m-instruct-q2_k` | 219 MB | yes |
| `qwen3-0.6b-q4_k_m` | 397 MB | no — needs swap |
| `qwen2.5-0.5b-instruct-q4_k_m` | 491 MB | no — needs swap |

> **On a Pi Zero 2 W:** only ~165 MB is free with Pi-hole running, so `local`
> summarization will push into swap and is *not* recommended. Use `none` or
> `openrouter`. On a Pi 4/5 or any 2GB+ board, `local` with
> `gemma-3-270m-it-q4_k_m` is a good default.

---

## Storage

Audio is ~85 MB/hour at Rumble's 191 kbps. With `retention_days = 30` and a
channel posting daily, budget roughly **2 GB** of SD card. Transcripts are kept
forever.

---

## How it works

1. `discover` fetches the channel page and reads an embedded JSON island —
   `yt-dlp`'s Rumble channel extractor is unreliable (it returns a single entry),
   and Rumble publishes no RSS, so the page is parsed directly with `jq`.
2. Videos already processed (tracked in `data/meta/*.meta`) are skipped.
3. Captions are pulled as VTT and converted to plain text. If absent, the
   audio-only stream is downloaded and transcribed with `whisper.cpp`.
4. An audio-only `.m4a` (`audio-192p`) is fetched for the episode enclosure.
   Only if a video has no audio-only stream is a low-res video downloaded and
   **immediately deleted** after extraction.
5. The summary is generated per the configured mode.
6. `feed.xml` is regenerated after every episode, so the feed updates
   immediately.
7. A retention sweep deletes audio and summaries past `retention_days` and
   rebuilds the feed.

## Be a good neighbour

The worker runs with `Nice=19` and `IOSchedulingClass=idle` and pauses between
videos, so Pi-hole's DNS resolution always wins the CPU.

---

## Troubleshooting

```bash
sudo rp-ctl status            # everything at a glance
tail -f /opt/rumblingpodcast/logs/rp.log
sudo journalctl -u rumblingpodcast-worker -f
```

**`decompression resulted in return code -1`** — Raspberry Pi OS ships `/tmp` as
a small tmpfs (often 30 MB). `yt-dlp` self-extracts ~40 MB per run. The app
redirects `TMPDIR` to `/opt/rumblingpodcast/run/tmp`; if you hit this, check
that directory is writable.

**No episodes appear** — the worker only picks up videos newer than
`max_age_days` that have no `.meta` file yet. `sudo rp-ctl run-once` forces a
pass.

## License

MIT — see [LICENSE](LICENSE).
