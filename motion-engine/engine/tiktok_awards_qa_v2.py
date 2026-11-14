#!/usr/bin/env python3
"""QA video reaktif TikTok Awards SEA: semua 9 VO beat terdengar utuh,
LUFS terintegrasi -16 ±1, durasi vs naskah.

Scene starts dihitung dari durasi VO + tail 30 frame (1,0 dtk) per scene
(sesuai tiktok-awards.json: tail_frames=30, no_transitions).
"""
import os
import re
import subprocess
import sys

ENG = os.path.dirname(os.path.abspath(__file__))
FINAL = os.path.join(ENG, "demos", "tiktok-awards-reaktif-v2.mp4")
VO_DIR = os.path.join(ENG, "assets", "vo-tiktok-awards")
TAIL_S = 30 / 30.0  # tail_frames / fps

vo_durs = []
for i in range(1, 10):
    p = os.path.join(VO_DIR, f"vo{i}.wav")
    d = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", p],
        capture_output=True, text=True, check=True).stdout.strip())
    vo_durs.append(d)

starts, t = [], 0.0
for d in vo_durs:
    starts.append(t)
    t += d + TAIL_S
total_expected = t

total = float(subprocess.run(
    ["ffprobe", "-v", "error", "-show_entries", "format=duration",
     "-of", "csv=p=0", FINAL],
    capture_output=True, text=True, check=True).stdout.strip())
print(f"total video: {total:.2f}s (harapan dari VO+tail: {total_expected:.2f}s, "
      f"VO total: {sum(vo_durs):.2f}s)")
ok = abs(total - total_expected) < 1.0
if not ok:
    print("  DURASI TIDAK COCOK!")

for i, (a, d) in enumerate(zip(starts, vo_durs)):
    out = subprocess.run(
        ["ffmpeg", "-hide_banner", "-ss", f"{a:.2f}", "-t", f"{d:.2f}",
         "-i", FINAL, "-map", "0:a", "-filter:a", "volumedetect",
         "-f", "null", "-"],
        capture_output=True, text=True).stderr
    m = re.search(r"mean_volume:\s*([-\d.]+)\s*dB", out)
    mv = float(m.group(1)) if m else -99
    status = "OK " if mv > -40 else "SILENT!"
    if mv <= -40:
        ok = False
    print(f"  vo{i+1} [{a:5.1f}s-{a+d:5.1f}s]: mean {mv:6.1f} dB {status}")

out = subprocess.run(
    ["ffmpeg", "-i", FINAL, "-map", "0:a", "-filter:a",
     "loudnorm=I=-16:TP=-1.0:LRA=11:print_format=json", "-f", "null", "-"],
    capture_output=True, text=True).stderr
m = re.search(r'"input_i"\s*:\s*"([^"]+)"', out)
lufs = float(m.group(1)) if m else 99
print(f"integrated LUFS: {lufs:.2f} (target -16 ±1)")
if abs(lufs + 16) > 1:
    ok = False
    print("  LUFS DI LUAR TARGET!")
print("QA:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
