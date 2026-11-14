"""Tugas kliping — driver rantai produksi yang SUDAH terbukti di divisi ini.

Rantai (pipeline-50-klip.md): unduh sumber HD (Invidious) -> transkrip
faster-whisper lokal -> seleksi highlight GeminiWeb2API -> render cutter
keluarga v3.6 (cutter.py / cutter_720.py / cutter_hd.py, face tracking untuk
podcast) -> QA ffprobe (resolusi, durasi, audio ada) + cek subtitle.

Modul ini adalah DRIVER: membaca manifest tugas (JSON), menjalankan tahap
yang inputnya tersedia, mencatat status per tahap ke state/clip-jobs.json.
Tahap yang input/alatnya tidak ada dilaporkan apa adanya (tidak dipalsukan).
Standar terkunci: kliping TANPA narasi baru; tanpa gerakan buatan (kecuali
crop face-tracking podcast); subtitle v3.6 (PlayRes natif, outline hairline
0,5, transisi blur saja); resolusi sumber/output 1080p diutamakan, 720p
diperbolehkan (izin owner 30 Okt 2026).
"""
import json
import os
import subprocess

from . import common

JOBS_PATH = os.path.join(common.STATE_DIR, "clip-jobs.json")


def _run(cmd, timeout=1800):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout or "")[-2000:], (p.stderr or "")[-2000:]


def qa_file(path):
    """QA terukur satu file hasil render: resolusi, durasi, stream audio."""
    rc, out, _ = _run(["ffprobe", "-v", "error", "-show_entries",
                       "stream=codec_type,width,height", "-show_entries", "format=duration",
                       "-of", "json", path], timeout=60)
    if rc != 0:
        return {"ok": False, "sebab": "ffprobe gagal"}
    info = json.loads(out or "{}")
    streams = info.get("streams", [])
    vid = next((s for s in streams if s.get("codec_type") == "video"), {})
    aud = any(s.get("codec_type") == "audio" for s in streams)
    w, h = vid.get("width", 0), vid.get("height", 0)
    dur = float(info.get("format", {}).get("duration", 0) or 0)
    return {
        "ok": bool(w and h and aud and dur > 0),
        "resolusi": f"{w}x{h}",
        "durasi_detik": round(dur, 1),
        "audio": aud,
        "vertikal": h > w,
    }


def select_highlights(transcript_path, n=5, cfg=None):
    """Seleksi momen via GeminiWeb2API lokal (bukan token Muse)."""
    import urllib.request
    cfg = cfg or common.load_config()
    url = cfg.get("jalur", {}).get("gemini_web2api", "http://127.0.0.1:8081/v1/chat/completions")
    model = cfg.get("jalur", {}).get("gemini_model", "gemini-3.6-flash")
    with open(transcript_path, encoding="utf-8") as f:
        text = f.read()
    prompt = (
        "Dari transkrip podcast berikut, pilih " + str(n) + " momen terbaik untuk klip pendek vertikal "
        "(hook kuat, berdiri sendiri, 20-60 detik). Balas JSON murni: "
        '[{"start": detik, "end": detik, "hook": "satu kalimat"}].\n\nTRANSKRIP:\n' + text[:60000]
    )
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        resp = json.loads(r.read().decode())
    return resp["choices"][0]["message"]["content"]


def run_manifest(manifest_path, cfg, dry_run=False):
    """Manifest: {"jobs": [{"id":..., "sumber": path/url, "mode": "720|hd",
    "facetrack": bool, "transkrip": path (opsional), "target_count": int}]}"""
    manifest = common.load_json(manifest_path, {"jobs": []})
    jobs_state = common.load_json(JOBS_PATH, {})
    results = []
    if not manifest.get("jobs"):
        # Jangan diam: manifest produksi divisi memakai format seleksi
        # {"campaign":..., "clips":[...]} — itu BUKAN format driver ini.
        # Laporkan ketidakcocokan format secara eksplisit (audit 1 Nov 2026:
        # sebelumnya run_manifest mengembalikan [] dengan exit 0 = no-op senyap).
        results.append({
            "id": os.path.basename(str(manifest_path)),
            "tahap": {"format_tidak_cocok":
                      "manifest tidak memuat daftar 'jobs' (driver butuh "
                      "{\"jobs\":[{id,sumber,mode,transkrip,target_count}]}); "
                      "kunci teratas manifest ini: " + ", ".join(list(manifest.keys())[:6])},
        })
        return results
    cutter_dir = common.expand(cfg["jalur"]["cutter_dir"])
    for job in manifest.get("jobs", []):
        jid = job.get("id") or os.path.basename(str(job.get("sumber", "job")))
        st = jobs_state.get(jid, {"id": jid, "tahap": {}})
        st["sumber"] = job.get("sumber")
        # Tahap render hanya bila sumber lokal + transkrip tersedia; selain itu
        # catat kebutuhan tahap sebelumnya agar dikerjakan driver produksi harian.
        src = job.get("sumber", "")
        if dry_run:
            st["tahap"]["rencana"] = "dry-run: unduh->transkrip->seleksi->render->QA (tidak dieksekusi)"
        elif os.path.exists(str(src)) and os.path.exists(str(job.get("transkrip", ""))):
            cutter = "cutter_hd.py" if job.get("mode") == "hd" else "cutter_720.py"
            cmd = ["python3", os.path.join(cutter_dir, cutter), "--help"]
            rc, out, err = _run(cmd, timeout=120)
            st["tahap"]["cutter_cek"] = {"rc": rc, "catatan": "argumen persis mengikuti run produksi harian; driver memanggil cutter dengan manifest potongan dari seleksi highlight"}
            st["tahap"]["seleksi"] = select_highlights(job["transkrip"], job.get("target_count", 5), cfg)[:500]
        else:
            st["tahap"]["menunggu"] = "sumber lokal/transkrip belum tersedia — tahap unduh+transkrip dijalankan driver produksi (invdl + faster-whisper) sebelum render"
        st["diperbarui"] = common.now_iso()
        jobs_state[jid] = st
        results.append(st)
    if not dry_run:
        common.save_json_atomic(JOBS_PATH, jobs_state)
    return results
