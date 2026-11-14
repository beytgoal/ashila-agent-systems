#!/usr/bin/env python3
"""Bangun caption JSON untuk komposisi ClipCaptions (Remotion) dari rentang
segmen sumber.

Format output:
{
  "sourceStart": 1.0,            // detik awal segmen di video sumber
  "cues": [
    {"start": 0.0, "end": 2.1,   // relatif terhadap awal segmen (detik)
     "words": [{"text": "Sudah", "start": 0.0, "end": 0.88}, ...]}
  ]
}

Sumber kata (urutan prioritas):
1. words.json hasil transcribe_chunked.py --word-timestamps
   (list datar {"start","end","word"}) — timing kata ASLI, dipakai bila ada.
2. SRT — cue dipecah per kata dengan durasi MERATA di dalam cue
   (keterbatasan: bukan timing ucap asli; hanya fallback).

Pengelompokan kata -> cue mengikuti disiplin cutter divisi:
- kata baru memutus cue bila jeda antar kata > GAP_SPLIT (default 0.7 dtk),
- maksimal MAX_WORDS kata per cue (default 10 = 2 baris x 5 kata),
- maksimal MAX_CUE_S durasi per cue (default 4.5 dtk).

Pakai:
  python3 tools/build-captions.py --words words.json --start 1 --end 57 \
      --out pilot/captions-ceiqu-01.json
  python3 tools/build-captions.py --srt part_01.srt --start 0 --end 56 \
      --out captions.json
"""
import argparse
import json
import re
import sys

GAP_SPLIT = 0.7
# Maks 8 kata/cue: pada fontSize 44/720px, 9-10 kata berlirik panjang bisa
# membungkus jadi 3 baris visual (cacat QA still pilot) — 8 kata aman 2 baris.
MAX_WORDS = 8
MAX_CUE_S = 4.5


def load_words_json(path):
    data = json.load(open(path))
    if isinstance(data, dict):
        data = data.get("words") or data.get("segments") or []
    out = []
    for w in data:
        if "word" in w:  # format datar faster-whisper
            out.append({"text": w["word"].strip(),
                        "start": float(w["start"]), "end": float(w["end"])})
        else:  # format segmen berisi words[]
            for sw in w.get("words", []):
                out.append({"text": sw["word"].strip(),
                            "start": float(sw["start"]),
                            "end": float(sw["end"])})
    return [w for w in out if w["text"]]


TS = re.compile(r"(\d+):(\d+):(\d+)[,.](\d+)")


def parse_ts(s):
    m = TS.search(s)
    h, mi, se, ms = (int(m.group(i)) for i in range(1, 5))
    return h * 3600 + mi * 60 + se + ms / 1000.0


def load_srt(path):
    words = []
    blocks = re.split(r"\n\s*\n", open(path, encoding="utf-8").read().strip())
    for b in blocks:
        lines = [l for l in b.splitlines() if l.strip()]
        tl = next((l for l in lines if "-->" in l), None)
        if not tl:
            continue
        a, z = tl.split("-->")
        start, end = parse_ts(a), parse_ts(z)
        text = " ".join(l for l in lines
                        if "-->" not in l and not l.strip().isdigit())
        toks = text.split()
        if not toks:
            continue
        step = (end - start) / len(toks)  # pecah merata (fallback SRT)
        for i, t in enumerate(toks):
            words.append({"text": t, "start": start + i * step,
                          "end": start + (i + 1) * step})
    return words


def group(words):
    cues, cur = [], []
    for w in words:
        if cur:
            gap = w["start"] - cur[-1]["end"]
            span = w["end"] - cur[0]["start"]
            if gap > GAP_SPLIT or len(cur) >= MAX_WORDS or span > MAX_CUE_S:
                cues.append(cur)
                cur = []
        cur.append(w)
    if cur:
        cues.append(cur)
    return [{"start": c[0]["start"], "end": c[-1]["end"], "words": c}
            for c in cues]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--words", help="words.json (timing kata asli)")
    ap.add_argument("--srt", help="file .srt (fallback, kata dipecah merata)")
    ap.add_argument("--start", type=float, required=True,
                    help="awal segmen di sumber (detik)")
    ap.add_argument("--end", type=float, required=True,
                    help="akhir segmen di sumber (detik)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    if args.words:
        raw, mode = load_words_json(args.words), "words.json (timing asli)"
    elif args.srt:
        raw, mode = load_srt(args.srt), "srt (kata dipecah merata)"
    else:
        sys.exit("butuh --words atau --srt")

    seg = []
    for w in raw:
        if w["end"] <= args.start or w["start"] >= args.end:
            continue
        seg.append({"text": w["text"],
                    "start": round(max(w["start"], args.start) - args.start, 3),
                    "end": round(min(w["end"], args.end) - args.start, 3)})
    cues = group(seg)
    doc = {"sourceStart": args.start, "mode": mode, "cues": cues}
    json.dump(doc, open(args.out, "w"), ensure_ascii=False, indent=1)
    print(f"{args.out}: {len(cues)} cue, {len(seg)} kata, mode={mode}")


if __name__ == "__main__":
    main()
