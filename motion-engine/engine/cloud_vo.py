#!/usr/bin/env python3
"""Cloud voice-over generator — THE voice path for all Moderate video content.

Keputusan owner 2026-10-25: ArboTTS lokal GAGAL untuk narasi drama.
  - Tier standard: owner nilai seperti robot & kurang jernih.
  - Tier Kokoro (Maya): owner nilai BUKAN voice native Indonesia.
  ArboTTS dilarang untuk narasi (lihat arbotts_vo.py — synth() menolak).
  Satu-satunya jalur voice sekarang: CLOUD (voice id-ID asli, berlisensi).

Backend:
  - google (DEFAULT): Google Cloud Text-to-Speech, Chirp 3 HD.
    Voice: id-ID-Chirp3-HD-Kore (perempuan, rekomendasi riset) atau
           id-ID-Chirp3-HD-Aoede (perempuan, alternatif).
    Free tier: 1 jt karakter/bulan, lalu $30/1 jt karakter. Billing WAJIB
    aktif (overage auto-charge — pasang budget alert). Pemakaian konten ini
    sangat kecil (~750 karakter/episode ≈ 22 rb karakter/bulan) — jauh di
    bawah kuota gratis.
    Auth: API key (env GOOGLE_TTS_API_KEY). Cara buat: lihat
    voice-cloud-setup.md (langkah persis, tanpa tebak-tebak).
  - azure: Azure AI Speech, F0 tier.
    Voice: id-ID-GadisNeural (perempuan, default) / id-ID-ArdiNeural (laki-laki).
    Free tier: 500 rb karakter/bulan Neural. F0 TIDAK auto-charge — kuota
    habis = throttle HTTP 429 sampai bulan berikut (lebih aman dari Google).
    Auth: env AZURE_SPEECH_KEY + AZURE_SPEECH_REGION.

Kredensial TIDAK PERNAH ditulis ke file — hanya via environment per pemanggilan
(transient), atau via Secure Vault saat owner menyerahkannya. Jangan paste
API key ke chat; pakai alur Secure Vault.

Pemakaian:
  python3 cloud_vo.py --text "Kalimat narasi." --out vo1.mp3 [--backend azure --voice id-ID-GadisNeural]
  python3 cloud_vo.py --segments naskah.json --out-dir assets/vo-x [--backend google --voice id-ID-Chirp3-HD-Aoede]
  python3 cloud_vo.py --text "..." --out vo1.mp3 --dry-run   # cetak request tanpa mengirim (verifikasi payload)
    naskah.json: [{"name": "vo1", "text": "..."}, ...] atau {"vo1": "...", ...}
  Default: backend=google, voice=id-ID-Chirp3-HD-Kore.
"""

import json
import os
import subprocess
import sys
import urllib.request
import urllib.error
from pathlib import Path

GOOGLE_VOICES = {
    "female": ["id-ID-Chirp3-HD-Kore", "id-ID-Chirp3-HD-Aoede",
               "id-ID-Chirp3-HD-Achernar", "id-ID-Chirp3-HD-Zephyr"],
    "male": ["id-ID-Chirp3-HD-Charon", "id-ID-Chirp3-HD-Fenrir",
             "id-ID-Chirp3-HD-Achird", "id-ID-Chirp3-HD-Puck"],
}
AZURE_VOICES = {"female": ["id-ID-GadisNeural"], "male": ["id-ID-ArdiNeural"]}

DEFAULT_BACKEND = "google"
DEFAULT_VOICE = "id-ID-Chirp3-HD-Kore"  # perempuan, rekomendasi riset CEO


def _ffprobe_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def _google_request(text, voice, speaking_rate=1.0):
    return {
        "url": "https://texttospeech.googleapis.com/v1/text:synthesize",
        "body": {
            "input": {"text": text},
            "voice": {"languageCode": "id-ID", "name": voice},
            "audioConfig": {"audioEncoding": "MP3", "speakingRate": speaking_rate},
        },
    }


def _google_synth(text, voice, api_key, speaking_rate=1.0, dry_run=False):
    req = _google_request(text, voice, speaking_rate)
    if dry_run:
        print("[dry-run] POST", req["url"], "?key=***")
        print(json.dumps(req["body"], ensure_ascii=False, indent=1))
        return None
    data = json.dumps(req["body"]).encode("utf-8")
    http_req = urllib.request.Request(
        req["url"] + "?key=" + api_key, data=data,
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(http_req, timeout=60) as resp:
            payload = json.load(resp)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:500]
        raise RuntimeError(f"Google TTS gagal (HTTP {e.code}): {detail}")
    import base64
    audio = base64.b64decode(payload["audioContent"])
    if len(audio) < 1000:
        raise RuntimeError("Google TTS mengembalikan audio terlalu pendek/kosong.")
    return audio


def _azure_request(text, voice, rate=1.0):
    ssml = (
        f"<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' "
        f"xml:lang='id-ID'><voice name='{voice}'>"
        f"<prosody rate='{rate}'>{text}</prosody>"
        f"</voice></speak>"
    )
    return ssml


def _azure_synth(text, voice, key, region, rate=1.0, dry_run=False):
    ssml = _azure_request(text, voice, rate)
    region_display = region or "<AZURE_SPEECH_REGION>"
    url = f"https://{region_display}.tts.speech.microsoft.com/cognitiveservices/v1"
    if dry_run:
        print("[dry-run] POST", url)
        print("headers: Ocp-Apim-Subscription-Key=***, X-Microsoft-OutputFormat=audio-16khz-128kbitrate-mono-mp3")
        print(ssml)
        return None
    http_req = urllib.request.Request(
        url, data=ssml.encode("utf-8"), method="POST",
        headers={"Ocp-Apim-Subscription-Key": key,
                 "Content-Type": "application/ssml+xml",
                 "X-Microsoft-OutputFormat": "audio-16khz-128kbitrate-mono-mp3"})
    try:
        with urllib.request.urlopen(http_req, timeout=60) as resp:
            audio = resp.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:500]
        raise RuntimeError(f"Azure TTS gagal (HTTP {e.code}): {detail}")
    if len(audio) < 1000:
        raise RuntimeError("Azure TTS mengembalikan audio terlalu pendek/kosong.")
    return audio


def synth(text, out_path, backend=None, voice=None, rate=1.0, dry_run=False):
    """Sintesis satu klip narasi Indonesia (cloud) -> mp3. Raise bila gagal."""
    backend = backend or os.environ.get("CLOUD_VO_BACKEND") or DEFAULT_BACKEND
    if backend not in ("google", "azure"):
        raise ValueError("Backend harus 'google' atau 'azure'.")
    if backend == "google":
        voice = voice or os.environ.get("CLOUD_VO_VOICE") or DEFAULT_VOICE
        api_key = os.environ.get("GOOGLE_TTS_API_KEY")
        if not api_key and not dry_run:
            raise RuntimeError(
                "Kredensial Google TTS belum ada (env GOOGLE_TTS_API_KEY kosong). "
                "Owner harus buat API key dulu — lihat voice-cloud-setup.md. "
                "Jangan pakai ArboTTS sebagai pengganti (ditolak owner)."
            )
    else:
        voice = voice or os.environ.get("CLOUD_VO_VOICE") or "id-ID-GadisNeural"
        key = os.environ.get("AZURE_SPEECH_KEY")
        region = os.environ.get("AZURE_SPEECH_REGION")
        if (not key or not region) and not dry_run:
            raise RuntimeError(
                "Kredensial Azure belum ada (env AZURE_SPEECH_KEY / AZURE_SPEECH_REGION kosong). "
                "Owner harus buat Speech resource F0 dulu — lihat voice-cloud-setup.md. "
                "Jangan pakai ArboTTS sebagai pengganti (ditolak owner)."
            )
    text = (text or "").strip()
    if not text:
        raise ValueError("Teks narasi kosong — tidak ada yang disintesis.")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if backend == "google":
        audio = _google_synth(text, voice, api_key, speaking_rate=rate, dry_run=dry_run)
    else:
        audio = _azure_synth(text, voice, key, region, rate=rate, dry_run=dry_run)
    if dry_run:
        return None
    out_path.write_bytes(audio)
    dur = _ffprobe_duration(out_path)
    if dur < 0.5:
        raise RuntimeError(f"Cloud TTS menghasilkan audio terlalu pendek ({dur:.2f}s).")
    print(f"[cloud_vo] {out_path.name}: backend={backend} voice={voice} dur={dur:.2f}s")
    return out_path


def synth_segments(segments, out_dir, backend=None, voice=None, rate=1.0, dry_run=False):
    """Sintesis banyak segmen. segments: [{"name","text"}] atau {"name": "text"}."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if isinstance(segments, dict):
        items = list(segments.items())
    else:
        items = [(s["name"], s["text"]) for s in segments]
    made = []
    for i, (name, text) in enumerate(items, 1):
        fname = name if str(name).endswith(".mp3") else f"{name}.mp3"
        made.append(synth(text, out_dir / fname, backend=backend, voice=voice,
                          rate=rate, dry_run=dry_run))
    if not dry_run:
        print(f"[cloud_vo] {len(made)} segmen selesai (backend={backend or DEFAULT_BACKEND}) -> {out_dir}")
    return made


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Cloud VO generator (voice native Indonesia, berlisensi).")
    ap.add_argument("--text", help="Satu kalimat/segmen narasi")
    ap.add_argument("--segments", help="File JSON segmen: [{name,text}] atau {name:text}")
    ap.add_argument("--out", help="File mp3 output (untuk --text)")
    ap.add_argument("--out-dir", help="Folder output (untuk --segments)")
    ap.add_argument("--backend", choices=["google", "azure"], default=None,
                    help="Backend cloud (default: google / Chirp 3 HD)")
    ap.add_argument("--voice", default=None,
                    help="Nama voice (google: id-ID-Chirp3-HD-Kore/Aoede; azure: id-ID-GadisNeural/ArdiNeural)")
    ap.add_argument("--rate", type=float, default=1.0, help="Kecepatan bicara (default 1.0)")
    ap.add_argument("--dry-run", action="store_true", help="Cetak request tanpa mengirim")
    args = ap.parse_args(argv)

    if args.text:
        if not args.out:
            ap.error("--text butuh --out")
        synth(args.text, args.out, backend=args.backend, voice=args.voice,
              rate=args.rate, dry_run=args.dry_run)
    elif args.segments:
        if not args.out_dir:
            ap.error("--segments butuh --out-dir")
        with open(args.segments, encoding="utf-8") as f:
            segments = json.load(f)
        synth_segments(segments, args.out_dir, backend=args.backend, voice=args.voice,
                       rate=args.rate, dry_run=args.dry_run)
    else:
        ap.error("beri --text atau --segments")
    return 0


if __name__ == "__main__":
    sys.exit(main())
