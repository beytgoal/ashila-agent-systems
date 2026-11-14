# Clipper Pipeline

Production pipeline that turns long-form YouTube videos into vertical clips
for Instagram / Threads / TikTok, at a cadence of ~50 clips/day.

## Pieces

- `cutter/` — the cutter family (v3.6): cuts 9:16 vertical clips with
  karaoke word-by-word ASS subtitles (off-white text, blue active word,
  hairline outline, native PlayRes so subtitles stay sharp) and optional
  MediaPipe face-tracking crops for talking-head sources.
  - `cutter.py` — 1080×1920 facetrack cutter
  - `cutter_720.py` — 720×1280 cutter
  - `cutter_hd.py` — 1080×1920 cutter
  - `detect_plan.py` — face-track plan detector
- `bot/` — the clipper bot: highlight research, cutting via the cutter
  family, platform posting helpers, campaign submission, approval-package
  builder, and read-only watchers (`watch/`) that track posting frontiers
  and campaign view pools through platform connectors.
  `config.example.json` shows the config structure (values are placeholders).
- `workflow/` — the written workflow: the 50-clips/day production pipeline
  document and example batch chain scripts (download → transcribe → select
  → render → review).

## Notes

- Clips never get new narration: transformation is editing (hook, headline,
  angle, subtitles, pacing, vertical crop).
- Sources that already carry burned-in captions are rendered `--no-subs`
  so captions never stack.
