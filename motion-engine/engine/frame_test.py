#!/usr/bin/env python3
"""Render selected frames from project scenes for visual QA (no ffmpeg)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from motion_render import SceneRenderer, STYLES

# usage: frame_test.py project.json outdir "si:frame,si:frame,..."
proj = json.load(open(sys.argv[1]))
outdir = sys.argv[2]
os.makedirs(outdir, exist_ok=True)
style = STYLES.get(proj.get("style", "cinematic"))
fps = proj.get("fps", 30)
W, H = proj.get("width", 1080), proj.get("height", 1920)

for spec in sys.argv[3].split(","):
    si, fr = spec.split(":")
    si, fr = int(si), int(fr)
    sc = dict(proj["scenes"][si])
    sc.setdefault("camera", "static")
    r = SceneRenderer(sc, style, fps, W, H)
    img = r.render_frame(fr)
    p = f"{outdir}/s{si}-f{fr:04d}.jpg"
    img.save(p, quality=90)
    print("saved", p, f"(scene frames={r.frames})")
