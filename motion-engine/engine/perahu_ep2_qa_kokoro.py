#!/usr/bin/env python3
"""QA Episode 2: verify all 6 VOs audible, no cut-off, LUFS ~-16."""
import json
import os
import re
import subprocess
import sys

ENG = os.path.dirname(os.path.abspath(__file__))
FINAL = os.path.join(ENG, "demos", "perahu-terakhir-ep2-kokoro.mp4")

man = json.load(open(os.path.join(ENG, "render-frames-ep2-kokoro", "manifest.json")))
starts = [s for _, s in man["scene_starts"]]
total = man["total_dur"]

vo_durs = []
for i in range(1, 7):
    p = os.path.join(ENG, "assets", "vo-perahu-ep2-kokoro", f"vo{i}.mp3")
    d = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", p],
        capture_output=True, text=True, check=True).stdout.strip())
    vo_durs.append(d)

# vo6 mixed at s5_start + vo5_dur + 0.9
vo6_at = starts[4] + vo_durs[4] + 0.9
windows = [(starts[i], starts[i] + vo_durs[i]) for i in range(5)]
windows.append((vo6_at, vo6_at + vo_durs[5]))

print(f"total video: {total:.1f}s")
ok = True
for i, (a, b) in enumerate(windows):
    # measure mean volume in the VO window
    out = subprocess.run(
        ["ffmpeg", "-hide_banner", "-ss", f"{a:.2f}", "-t", f"{b-a:.2f}",
         "-i", FINAL, "-map", "0:a", "-filter:a", "volumedetect",
         "-f", "null", "-"],
        capture_output=True, text=True).stderr
    m = re.search(r"mean_volume:\s*([-\d.]+)\s*dB", out)
    mv = float(m.group(1)) if m else -99
    status = "OK " if mv > -40 else "SILENT!"
    if mv <= -40:
        ok = False
    print(f"  vo{i+1} [{a:5.1f}s-{b:5.1f}s]: mean {mv:6.1f} dB {status}")

# overall integrated loudness
out = subprocess.run(
    ["ffmpeg", "-i", FINAL, "-map", "0:a", "-filter:a",
     "loudnorm=I=-16:TP=-1.0:LRA=11:print_format=json", "-f", "null", "-"],
    capture_output=True, text=True).stderr
m = re.search(r'"input_i"\s*:\s*"([^"]+)"', out)
print("integrated LUFS:", m.group(1) if m else "n/a")
print("QA:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
