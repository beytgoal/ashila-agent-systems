#!/usr/bin/env python3
"""Post-process video reaktif TikTok Awards SEA: buat versi chat 720p.

Base sudah berisi semua 9 VO + bed (di-mix motion_render.py). Tidak ada
VO tambahan yang perlu di-mix. File serial / Perahu TIDAK disentuh.
"""
import os
import subprocess

ENG = os.path.dirname(os.path.abspath(__file__))
DEMOS = os.path.join(ENG, "demos")
FINAL = os.path.join(DEMOS, "tiktok-awards-reaktif-v2.mp4")
CHAT = os.path.join(DEMOS, "tiktok-awards-reaktif-v2-chat.mp4")

assert os.path.exists(FINAL), f"base belum ada: {FINAL}"

cmd = ["ffmpeg", "-y", "-i", FINAL,
       "-vf", "scale=720:1280", "-c:v", "libx264", "-crf", "28",
       "-preset", "medium", "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-b:a", "96k", CHAT]
print("making chat version ...")
subprocess.run(cmd, check=True)
sz = os.path.getsize(CHAT) / 1e6
print(f"chat: {CHAT} ({sz:.1f}MB)")

for p in (FINAL, CHAT):
    d = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", p],
        capture_output=True, text=True, check=True).stdout.strip())
    print(f"{os.path.basename(p)}: {d:.2f}s")
print("DONE")
