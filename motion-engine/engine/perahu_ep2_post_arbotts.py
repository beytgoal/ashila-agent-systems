#!/usr/bin/env python3
"""Post-process Episode 2 (ArboTTS/Danu): mix vo6 closing hook, then make chat version.

Sama persis dengan perahu_ep2_post.py, kecuali semua path mengarah ke versi
arbotts — file Ep2 lama TIDAK ditimpa sampai owner menyetujui versi baru.
"""
import json
import os
import re
import subprocess

ENG = os.path.dirname(os.path.abspath(__file__))
DEMOS = os.path.join(ENG, "demos")
VO6 = os.path.join(ENG, "assets", "vo-perahu-ep2-arbotts", "vo6.mp3")
BASE = os.path.join(DEMOS, "perahu-terakhir-ep2-arbotts-base.mp4")
FINAL = os.path.join(DEMOS, "perahu-terakhir-ep2-arbotts.mp4")
CHAT = os.path.join(DEMOS, "perahu-terakhir-ep2-arbotts-chat.mp4")

man = json.load(open(os.path.join(ENG, "render-frames-ep2-arbotts", "manifest.json")))
total = man["total_dur"]
s5_start = man["scene_starts"][4][1]
print(f"total={total:.2f}s scene5_start={s5_start:.2f}s")

# vo5 duration -> vo6 starts 0.9s after vo5 ends
vo5_dur = float(subprocess.run(
    ["ffprobe", "-v", "error", "-show_entries", "format=duration",
     "-of", "csv=p=0", os.path.join(ENG, "assets", "vo-perahu-ep2-arbotts", "vo5.mp3")],
    capture_output=True, text=True, check=True).stdout.strip())
vo6_at = s5_start + vo5_dur + 0.9
ms = int(vo6_at * 1000)
print(f"vo5_dur={vo5_dur:.2f}s -> vo6 at {vo6_at:.2f}s")

# 1) mix vo6 (loudnorm BEFORE adelay, per AGENTS.md lesson)
cmd = ["ffmpeg", "-y", "-i", BASE, "-i", VO6, "-filter_complex",
       f"[1:a]loudnorm=I=-16:TP=-1.0:LRA=11,adelay={ms}|{ms}[vo6];"
       f"[0:a][vo6]amix=inputs=2:normalize=0[aout]",
       "-map", "0:v", "-map", "[aout]", "-c:v", "copy",
       "-c:a", "aac", "-b:a", "160k", "-shortest", FINAL]
print("mixing vo6 ...")
subprocess.run(cmd, check=True)
print("final:", FINAL)

# 2) chat version: 720p, crf 28 (~11MB target)
cmd = ["ffmpeg", "-y", "-i", FINAL,
       "-vf", "scale=720:1280", "-c:v", "libx264", "-crf", "28",
       "-preset", "medium", "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-b:a", "96k", CHAT]
print("making chat version ...")
subprocess.run(cmd, check=True)
sz = os.path.getsize(CHAT) / 1e6
print(f"chat: {CHAT} ({sz:.1f}MB)")

# 3) QA: durations + LUFS
for p in (FINAL, CHAT):
    d = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", p],
        capture_output=True, text=True, check=True).stdout.strip())
    print(f"{os.path.basename(p)}: {d:.2f}s")
lufs = subprocess.run(
    ["ffmpeg", "-i", FINAL, "-map", "0:a", "-filter:a",
     "loudnorm=I=-16:TP=-1.0:LRA=11:print_format=json", "-f", "null", "-"],
    capture_output=True, text=True)
m = re.search(r'\{[^{}]*"input_i"[^{}]*\}', lufs.stderr, re.S)
if m:
    print("measured LUFS:", re.search(r'"input_i"\s*:\s*"([^"]+)"', m.group(0)).group(1))
print("DONE")
