#!/usr/bin/env python3
"""ArboTTS voice-over generator — DITUTUP untuk narasi (keputusan owner 2026-10-25).

Verdict owner (langsung, 2026-10-25 pagi, setelah mendengar re-render Ep2):
  - Tier standard: seperti robot & kurang jernih.
  - Tier Kokoro (Maya): BUKAN voice native Indonesia.
ArboTTS DILARANG untuk narasi konten apa pun. synth() di file ini MENOLAK
dengan jelas supaya tidak ada run yang diam-diam memakai voice yang ditolak
owner. Jalur voice sekarang HANYA cloud: cloud_vo.py
(Google Chirp 3 HD id-ID-Chirp3-HD-Kore / Azure id-ID-GadisNeural).

File ini dipertahankan sebagai arsip (repo, venv, model, sampel, dan catatan
ukur akustik di bawah tetap benar sebagai data — yang berubah adalah keputusan
owner tentang hasilnya). JANGAN hapus guard ini tanpa perintah eksplisit owner.

Setup lama (arsip — jangan install ulang dari nol):
  - venv CLI : ~/workspace/.arbotts-venv/bin/arbotts
  - model standard (60MB) + model Kokoro (~88MB, 24kHz) di ~/.cache/arbotts
  - repo      : ~/workspace/arboTTS — arbotts/__init__.py SUDAH diperbaiki CEO
                (import clone/torch dibuat opsional; torch TIDAK terpasang dan
                JANGAN di-install — download PyTorch diblokir proxy VM ini)
  - sampel voice storyteller:
                ~/workspace/voice-samples/sample-danu.wav  (laki-laki, kalem)
                ~/workspace/voice-samples/sample-maya.wav  (perempuan, kalem)
                ~/workspace/voice-samples/sample-bimo.wav  (laki-laki, bariton)

Catatan ukur akustik 2026-10-24 (arsip — metrik ini TIDAK mendeteksi aksen):
Kokoro maya vs standard — F0 median 182 Hz, intonasi std 28, centroid
2764 Hz, energi >8kHz 0.084 (vs 0.000 standard). Pelajaran: pitch & kejernihan
spektral bukan bukti "native" — yang menentukan adalah telinga penutur asli
(owner). Jangan ulangi kesalahan ini: jangan klaim voice "native" dari angka
akustik; yang dinilai adalah hasil akhir oleh owner.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ARBOTTS_CLI = Path.home() / "workspace" / ".arbotts-venv" / "bin" / "arbotts"
DEFAULT_VOICE = "maya"  # perempuan, storyteller (keputusan owner 2026-10-24)
DEFAULT_TIER = "kokoro"  # 24kHz — standard TIDAK BOLEH untuk narasi drama
DEFAULT_SPEED = 1.0  # kokoro; standard memakai 0.85 (lihat default_speed())
STORYTELLER_VOICES = ("danu", "maya", "bimo", "arba", "sita", "arbo", "dimas")


def default_tier(explicit=None):
    # DITUTUP 2026-10-25: owner menilai Kokoro bukan voice native Indonesia
    # dan standard seperti robot. Semua tier ArboTTS dilarang untuk narasi.
    raise ValueError(
        "ArboTTS DITUTUP untuk narasi (keputusan owner 2026-10-25: tier standard "
        "seperti robot & kurang jernih; tier Kokoro bukan voice native Indonesia). "
        "Pakai cloud_vo.py (Google Chirp 3 HD / Azure) — lihat voice-cloud-setup.md."
    )


def default_speed(tier, explicit=None):
    if explicit is not None:
        return explicit
    return 1.0 if tier == "kokoro" else 0.85


def active_voice(explicit=None):
    """Voice yang dipakai: argumen > env ARBOTTS_VOICE > default (maya)."""
    voice = explicit or os.environ.get("ARBOTTS_VOICE") or DEFAULT_VOICE
    if voice not in STORYTELLER_VOICES:
        raise ValueError(
            f"Voice '{voice}' bukan voice ArboTTS yang dikenal. "
            f"Pilih salah satu: {', '.join(STORYTELLER_VOICES)}. "
            f"Voice non-native TIDAK BOLEH dipakai untuk narasi Indonesia."
        )
    return voice


def _ffprobe_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def synth(text, out_path, voice=None, speed=None, lang="id", tier=None):
    """Sintesis satu klip narasi Indonesia -> mp3. Raise bila gagal (tanpa fallback)."""
    voice = active_voice(voice)
    tier = default_tier(tier)
    speed = default_speed(tier, speed)
    text = (text or "").strip()
    if not text:
        raise ValueError("Teks narasi kosong — tidak ada yang disintesis.")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="arbotts_vo_") as td:
        wav = Path(td) / "out.wav"
        cmd = [str(ARBOTTS_CLI), text, "-o", str(wav),
               "-l", lang, "-sp", voice, "-s", str(speed), "-t", tier]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0 or not wav.exists():
            raise RuntimeError(
                f"ArboTTS gagal (voice={voice}, rc={r.returncode}): "
                f"{(r.stderr or r.stdout or '').strip()[-500:]}"
            )
        dur = _ffprobe_duration(wav)
        if dur < 0.5:
            raise RuntimeError(f"ArboTTS menghasilkan audio terlalu pendek ({dur:.2f}s).")
        # wav -> mp3 (pipeline VO memakai .mp3)
        tmp_mp3 = Path(td) / "out.mp3"
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav),
             "-codec:a", "libmp3lame", "-q:a", "3", str(tmp_mp3)],
            check=True,
        )
        out_path.write_bytes(tmp_mp3.read_bytes())
    dur = _ffprobe_duration(out_path)
    print(f"[arbotts_vo] {out_path.name}: voice={voice} tier={tier} speed={speed} dur={dur:.2f}s")
    return out_path


def synth_segments(segments, out_dir, voice=None, speed=None, tier=None, prefix="vo"):
    """Sintesis banyak segmen. segments: [{"name","text"}] atau {"name": "text"}."""
    voice = active_voice(voice)
    tier = default_tier(tier)
    speed = default_speed(tier, speed)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if isinstance(segments, dict):
        items = list(segments.items())
    else:
        items = [(s["name"], s["text"]) for s in segments]
    made = []
    for i, (name, text) in enumerate(items, 1):
        fname = name if str(name).endswith(".mp3") else f"{name}.mp3"
        made.append(synth(text, out_dir / fname, voice=voice, speed=speed, tier=tier))
    print(f"[arbotts_vo] {len(made)} segmen selesai (voice={voice} tier={tier}) -> {out_dir}")
    return made


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="ArboTTS VO generator (voice native Indonesia).")
    ap.add_argument("--text", help="Satu kalimat/segmen narasi")
    ap.add_argument("--segments", help="File JSON segmen: [{name,text}] atau {name:text}")
    ap.add_argument("--out", help="File mp3 output (untuk --text)")
    ap.add_argument("--out-dir", help="Folder output (untuk --segments)")
    ap.add_argument("--voice", choices=list(STORYTELLER_VOICES),
                    help="Voice ArboTTS (default: env ARBOTTS_VOICE / maya)")
    ap.add_argument("--tier", default=None,
                    help="Tier model: kokoro (default, 24kHz) — standard DILARANG untuk narasi")
    ap.add_argument("--speed", type=float, default=None,
                    help="Kecepatan bicara (default: 1.0 kokoro, 0.85 standard)")
    args = ap.parse_args(argv)

    if args.text:
        if not args.out:
            ap.error("--text butuh --out")
        synth(args.text, args.out, voice=args.voice, speed=args.speed, tier=args.tier)
    elif args.segments:
        if not args.out_dir:
            ap.error("--segments butuh --out-dir")
        with open(args.segments, encoding="utf-8") as f:
            segments = json.load(f)
        synth_segments(segments, args.out_dir, voice=args.voice, speed=args.speed, tier=args.tier)
    else:
        ap.error("beri --text atau --segments")
    return 0


if __name__ == "__main__":
    sys.exit(main())
