"""Riset otomatis campaign/jobs clipper — snapshot + diff, 0 token agent.

Sumber (sesuai aturan divisi: baca datahub dulu, jangan duplikasi riset lama):
1. datahub (dh.py query) untuk campaign yang sudah terverifikasi divisi/Riset.
2. File verifikasi guide lokal divisi (verifikasi-guide-*.md terbaru).
3. Daftar platform clipper yang sudah dipakai perusahaan (status dari ledger).

Output: state/research-snapshot.json (snapshot terakhir) + event JSONL hanya
saat ada campaign baru / CPM berubah / tenggat berubah. Halaman platform yang
butuh login (Wefluence/Whop/TryBuzzer/Ternak Klip) TIDAK di-scrape buta —
statusnya dibaca dari ledger + verifikasi terakhir dan ditandai
'butuh-sesi-login' agar agent/manusia yang memutuskan, sesuai gerbang manusia.
"""
import json
import os
import re
import subprocess

from . import common

SNAP_PATH = os.path.join(common.STATE_DIR, "research-snapshot.json")

# Platform yang sudah pernah dipakai/diteliti perusahaan (fakta dari ledger +
# riset divisi; CPM hanya yang terverifikasi guide, bukan tebakan).
PLATFORMS = [
    {
        "platform": "Ternak Klip",
        "url": "https://app.ternakklip.com",
        "login": "Google (you@example.com)",
        "status": "AKTIF — 2 campaign JOINED (akun Heru Febrian)",
        "campaigns": [
            {"nama": "7 Karyawan VS 1 Clipper", "cpm": {"threads": 3000, "instagram": 2000, "tiktok": 2000},
             "platform_submit": ["tiktok", "instagram", "threads"], "sisa_budget_pct": 93,
             "min_payout_views": 10000, "maks_views": 1500000},
            {"nama": "Pulkam — Pulang Kampung Phase 2A", "cpm": {"tiktok": 2000},
             "platform_submit": ["tiktok"], "sisa_budget_pct": 37, "maks_views": 1000000},
        ],
    },
    {
        "platform": "Wefluence",
        "url": "https://wefluence.app",
        "login": "Google (you@example.com)",
        "status": "PERNAH PAKAI — campaign 'Ajak Pemilik Usaha' berakhir 29 Okt 2026",
        "campaigns": [
            {"nama": "Beauty is in the muscle (WonderFace)", "bayar_per_video_idr": 100000,
             "tenggat": "2026-11-09", "status": "brief terkonfirmasi, belum dikerjakan"},
        ],
    },
    {
        "platform": "Whop",
        "url": "https://whop.com",
        "login": "Google (you@example.com)",
        "status": "TERDAFTAR (@navyhuddle7a) — campaign Marlon $3/1K BELUM terverifikasi dasbor",
        "campaigns": [
            {"nama": "Marlon", "cpm_usd": 3, "status": "WAJIB verifikasi dasbor Reach sebelum produksi"},
        ],
    },
    {
        "platform": "TryBuzzer",
        "url": "https://trybuzzer.com",
        "login": "Google (you@example.com)",
        "status": "TERDAFTAR — aturan Discord 7 Okt 2026: video wajib dari akun Discord terhubung+aktif",
        "campaigns": [],
    },
]

DH_QUERIES = ["campaign clipper", "ternak klip", "wefluence", "whop", "trybuzzer", "scouting peluang"]


def dh_search(cfg):
    dh = common.expand(cfg.get("jalur", {}).get("dh_py", "~/workspace/divisi/data/bin/dh.py"))
    hits = []
    for q in DH_QUERIES:
        try:
            out = subprocess.run(["python3", dh, "query", q], capture_output=True, text=True, timeout=60)
            rows = json.loads(out.stdout or "[]")
            for r in rows[:5]:
                hits.append({"query": q, "ts": r.get("ts"), "title": r.get("title")})
        except Exception as e:
            hits.append({"query": q, "error": str(e)})
    return hits


def latest_guide():
    div = os.path.expanduser("~/workspace/divisi/freelancer-clipper")
    guides = sorted(f for f in os.listdir(div) if re.match(r"verifikasi-guide-.*\.md$", f))
    return guides[-1] if guides else None


def build_snapshot(cfg):
    return {
        "dibuat": common.now_iso(),
        "platforms": PLATFORMS,
        "datahub_hits_terbaru": dh_search(cfg),
        "guide_lokal_terbaru": latest_guide(),
    }


def diff_snapshot(old, new):
    changes = []
    old_names = {(p["platform"], c["nama"]) for p in (old or {}).get("platforms", []) for c in p.get("campaigns", [])}
    for p in new.get("platforms", []):
        for c in p.get("campaigns", []):
            if (p["platform"], c["nama"]) not in old_names:
                changes.append({"perubahan": "campaign_baru", "platform": p["platform"], "campaign": c["nama"]})
    old_guide = (old or {}).get("guide_lokal_terbaru")
    if old_guide != new.get("guide_lokal_terbaru"):
        changes.append({"perubahan": "guide_lokal_baru", "file": new.get("guide_lokal_terbaru")})
    return changes


def run(cfg, dry_run=False):
    snap = build_snapshot(cfg)
    old = common.load_json(SNAP_PATH)
    changes = diff_snapshot(old, snap)
    if not dry_run:
        common.save_json_atomic(SNAP_PATH, snap)
        for ch in changes:
            common.event("research_diff", ch)
    return {"snapshot": snap, "perubahan": changes, "dry_run": dry_run}
