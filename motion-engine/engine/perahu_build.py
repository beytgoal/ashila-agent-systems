#!/usr/bin/env python3
"""Driver: build PERAHU TERAKHIR Episode 1 from perahu-project.json."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from perahu_render import build_project

proj = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "perahu-project.json")))
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "demos", "perahu-terakhir-v1.mp4")
tmpdir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "render-frames-perahu")
total_dur, scene_starts = build_project(
    proj["scenes"], proj["bed"], proj["thump"], out, tmpdir)
print(f"total={total_dur:.1f}s scenes={len(scene_starts)}")
for i, (sf, ss) in enumerate(scene_starts):
    print(f"  scene{i+1}: start_frame={sf} start_sec={ss:.2f}")
