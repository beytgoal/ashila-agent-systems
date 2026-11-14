#!/usr/bin/env python3
"""Re-render Ep2 BASE with ArboTTS Kokoro VO (Maya).

Sama persis dengan perahu_anim_ep2.main(), kecuali:
  - project : perahu-project-ep2-kokoro.json (VO -> assets/vo-perahu-ep2-kokoro/)
  - out     : demos/perahu-terakhir-ep2-kokoro-base.mp4 (file lama TIDAK ditimpa)
  - tmpdir  : render-frames-ep2-kokoro (FRESH — wajib, karena durasi VO baru
              mengubah jumlah frame tiap scene; memakai tmpdir lama akan
              memakai ulang frame lama di posisi yang salah)
Visual: kode animasi sama — isi visual identik dengan yang disetujui owner,
timing scene mengikuti durasi VO baru.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import perahu_anim_ep2 as A2
import perahu_render as PR

ENG = os.path.dirname(os.path.abspath(__file__))

proj = json.load(open(os.path.join(ENG, "perahu-project-ep2-kokoro.json")))
scenes = proj["scenes"]
for i, sc in enumerate(scenes):
    sc["anim"] = i
bed = proj["bed"]
thump = proj.get("thump")
out = os.path.join(ENG, "demos", "perahu-terakhir-ep2-kokoro-base.mp4")
tmpdir = os.path.join(ENG, "render-frames-ep2-kokoro")
os.makedirs(tmpdir, exist_ok=True)


def factory(sc, fps, W_, H_):
    return A2.BUILDERS[sc["anim"]](sc, fps)


PR.PerahuRenderer = factory
total_dur, scene_starts = PR.build_project(scenes, bed, thump, out,
                                           tmpdir, fps=A2.FPS, W=A2.W, H=A2.H)
with open(os.path.join(tmpdir, "manifest.json"), "w") as fh:
    json.dump({"total_dur": total_dur, "scene_starts": scene_starts}, fh)
print("EP2 kokoro base render done:", out, f"{total_dur:.1f}s")
for i, (sf, ss) in enumerate(scene_starts):
    print(f"  scene{i + 1}: start_frame={sf} start_sec={ss:.2f}")
