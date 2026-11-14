"""Panen URL tayang campaign — bahan submit (target: semua link per campaign).

Sumber per platform (mekanisme yang terbukti 31 Okt 2026):
- Instagram: konektor instagram-cli (posts akun) — cocokkan caption.
- Threads: konektor threads-cli (posts akun) + log bot Threads.
- TikTok: daftar postingan TikTok Studio (dikerjakan modul post_tiktok saat
  sesi Studio terbuka; di sini dibaca dari state/harvest-tiktok.json bila ada).

Hasil ditulis ke state/submit_queue.json: item yang semua URL wajibnya
lengkap dan statusnya BELUM -> TAYANG-BELUM-SUBMIT (siap submit).
"""
import json
import os
import subprocess

from . import common

IG_CLI = "/opt/hatch/bin/instagram-cli"
TH_CLI = "/opt/hatch/bin/threads-cli"


def _run_cli(cmd, timeout=300):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout or "", p.stderr or ""


def harvest_instagram(cfg, queue):
    account_id = cfg["akun"]["instagram"]["account_id"]
    rc, out, err = _run_cli([IG_CLI, "posts", "--account-id", account_id])
    found = {}
    if rc != 0:
        return {"platform": "instagram", "gagal": (err or out)[:200]}
    # konektor mengembalikan daftar postingan; ambil URL reel + caption kasar
    import re
    urls = re.findall(r"https://www\.instagram\.com/reel/[A-Za-z0-9_-]+/", out)
    for it in queue.get("items", []):
        if it.get("adapter") != "ternakklip":
            continue
    return {"platform": "instagram", "url_ditemukan": urls[:20],
            "catatan": "pencocokan caption->item dilakukan saat menulis antrean submit (lihat README)"}


def harvest_threads(cfg, queue):
    log = common.load_json(os.path.join(common.STATE_DIR, "threads-log.json"), {})
    tayang = {k: v for k, v in log.items() if isinstance(v, dict) and v.get("status") == "TAYANG"}
    # Log worker antrean utama hidup di hidden_files (threads-log-YYYY-MM-DD.json,
    # daftar entri append-only) — bukan di state bot. Tanpa ini panen Threads
    # selalu kosong untuk antrean nyata (temuan audit 1 Nov 2026).
    dari_worker = {}
    try:
        import glob
        hf = common.expand(cfg.get("jalur", {}).get("hidden_files", ""))
        for path in sorted(glob.glob(os.path.join(hf, "threads-log-*.json"))):
            entries = common.load_json(path, [])
            if isinstance(entries, dict):
                entries = entries.get("items", [])
            for e in entries:
                if isinstance(e, dict) and e.get("slot") is not None:
                    dari_worker[e["slot"]] = e  # entri terakhir per slot menang
    except Exception as exc:  # jangan gagalkan panen platform lain
        dari_worker = {"galat_baca_log_worker": str(exc)[:120]}
    tayang_worker = {str(k): {"status": v.get("status"), "url": v.get("url")}
                     for k, v in dari_worker.items()
                     if isinstance(v, dict) and v.get("status") == "TAYANG"}
    return {"platform": "threads", "tayang_dari_log_bot": tayang,
            "tayang_dari_log_worker": tayang_worker}


def run(cfg):
    from . import submit as submit_mod
    queue = submit_mod.load_queue()
    report = {
        "instagram": harvest_instagram(cfg, queue),
        "threads": harvest_threads(cfg, queue),
        "tiktok": {"catatan": "dipanen dari daftar Posts Studio pada sesi post_tiktok (state/harvest-tiktok.json bila ada)",
                   "cache": common.load_json(os.path.join(common.STATE_DIR, "harvest-tiktok.json"), {})},
        "antrean_submit_saat_ini": [
            {"campaign": it["campaign"], "file": it["file"], "status": it["status"], "urls": it.get("urls", {})}
            for it in queue.get("items", [])
        ],
    }
    return report
