# Motion Engine

A deterministic, frame-stepped motion-graphics engine in Python (PIL +
ffmpeg) for explainer and serial videos. Every frame is a pure function of
time, so previews are identical to final renders.

- `engine/motion_render.py` — the renderer: scenes from a JSON storyboard,
  kinetic word-by-word typography synced to voice-over word timings,
  named styles (`cinematic`, `kalbotau`, `lila`, `beyond`), highlight
  boxes, count-ups, camera punch/spring moves, VO + SFX + music mixing
  (voice −16 LUFS target over a quiet bed).
- `engine/` also holds the VO helpers (`cloud_vo.py`, `arbotts_vo.py`)
  and small utilities used around the renderer.
- `CARA-PAKAI-PIPELINE-3D.md` — how the companion 3D pipeline is operated.
- `examples/` — an example project JSON (`kalbotau-ac.json`).

Text is never black: styles use light ink on dark or designed backgrounds;
the `kalbotau` style pairs off-white text with a blue highlight box on a
dark charcoal background.
