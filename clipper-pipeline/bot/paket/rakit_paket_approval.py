#!/usr/bin/env python3
"""Perakit ringkasan paket approval klip — SCRIPT, sebelum sesi agen 08:00.

Fase 2 P3-10 (dokumen ~/workspace/peta-fase-2-token.md): sesi agen
`sesi-approval-posting-klip-harian` sebelumnya membaca sendiri file paket
approval (belasan KB) + memeriksa keberadaan file klip + membaca ledger
submit campaign di dalam sesi. Script ini mengerjakan perakitan mekanis
itu lebih dulu dan menulis SATU ringkasan kecil:

  goals/moderate-company-setup/hidden_files/paket-siap-<tanggal>.json/.md

berisi: paket ada/tidak, blok STATUS VERIFIKASI tercatat atau tidak,
jumlah klip, file klip yang HILANG dari disk (cek keberadaan nyata),
caption yang hashtag-nya != tepat 5, daftar klip campaign DITAHAN dari
paket, dan ringkasan ledger submit campaign (hitung status + daftar
TAYANG-BELUM-SUBMIT = alarm submit). Persetujuan owner TIDAK di-script —
agen tetap menyajikan paket + kartu dan menunggu keputusan seperti biasa.

Keluaran stdout = JSON {"changed": [...]} untuk Company Bot: changed
hanya saat ringkasan tanggal baru pertama terbentuk atau daftar file
hilang berubah. Paket belum ada -> changed [] (ketidakhadiran paket
dibaca sesi dari ringkasan, bukan event bot).
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

WIB = ZoneInfo("Asia/Jakarta")
HOME = Path.home()
HIDDEN = HOME / "workspace/goals/moderate-company-setup/hidden_files"
LEDGER = HOME / "workspace/divisi/freelancer-clipper/submit-campaign-ledger.md"
STATE = HOME / "workspace/divisi/freelancer-clipper/bot/paket/state.json"


def parse_package(path):
    text = path.read_text(errors="replace")
    out = {"status_verifikasi_tercatat": "## STATUS VERIFIKASI" in text}
    m = re.search(r"Jumlah klip terverifikasi:\s*(\d+)\s*dari\s*(\d+)", text)
    out["klaim_terverifikasi"] = [int(m.group(1)), int(m.group(2))] if m else None

    # Basis folder lolos dari baris template "File klip: `...lolos/<sumber>/<file>`"
    base = None
    m = re.search(r"File klip:\s*`([^`]+)`", text)
    if m:
        base = m.group(1).split("<")[0].rstrip("/")
        base = Path(os.path.expanduser(base))

    clips = []
    cur = None
    for line in text.splitlines():
        hm = re.match(r"^### \d+\.\s+(\S+)\s+—\s+(.*?)\s+—\s+([\d,]+)\s*dtk", line)
        if hm:
            cur = {"id": hm.group(1), "sumber": hm.group(2),
                   "durasi": hm.group(3), "file": None, "caption_ok": None}
            clips.append(cur)
            continue
        if cur is not None:
            fm = re.match(r"^- File:\s*`([^`]+)`", line)
            if fm:
                cur["file"] = fm.group(1)
            cm = re.match(r"^- Caption:\s*(.*)$", line)
            if cm:
                cur["caption_ok"] = len(re.findall(r"#\w+", cm.group(1))) == 5
    hilang, caption_rusak = [], []
    for c in clips:
        if base is not None and c["file"]:
            rel = c["file"][len("lolos/"):] if c["file"].startswith("lolos/") else c["file"]
            if not (base / rel).exists():
                hilang.append(c["id"])
        if c["caption_ok"] is False:
            caption_rusak.append(c["id"])
    out.update({"jumlah_klip": len(clips), "file_hilang": hilang,
                "caption_hashtag_bukan_5": caption_rusak})

    ditahan = []
    m = re.search(r"## Klip campaign DITAHAN.*?\n(.*?)(?:\n## |\Z)", text, re.S)
    if m:
        for line in m.group(1).splitlines():
            line = line.strip()
            if line.startswith("- "):
                ditahan.append(line[2:].strip())
    out["campaign_ditahan"] = ditahan
    return out


def parse_ledger():
    out = {"tersedia": False, "tersubmit": 0, "ditolak": 0, "belum": 0,
           "tayang_belum_submit": []}
    if not LEDGER.exists():
        return out
    out["tersedia"] = True
    for line in LEDGER.read_text(errors="replace").splitlines():
        if not line.startswith("|") or "---" in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4:
            continue
        status = cells[3]
        fname = cells[0]
        if "TAYANG-BELUM-SUBMIT" in status:
            out["tayang_belum_submit"].append(fname)
        elif status.startswith("TERSUBMIT"):
            out["tersubmit"] += 1
        elif "DITOLAK" in status:
            out["ditolak"] += 1
        elif status.startswith("BELUM"):
            out["belum"] += 1
    return out


def build(tanggal):
    paket_path = HIDDEN / f"paket-approval-{tanggal}.md"
    ringkas = {"tanggal": tanggal, "paket_ada": paket_path.exists(),
               "dibangun_wib": datetime.now(WIB).isoformat()}
    if paket_path.exists():
        ringkas.update(parse_package(paket_path))
    ringkas["ledger_submit"] = parse_ledger()
    sesi = HIDDEN / f"sesi-approval-klip-{tanggal}.md"
    ringkas["keputusan_tercatat"] = sesi.exists()
    return ringkas


def render_md(r):
    if not r["paket_ada"]:
        return (f"# Paket siap — {r['tanggal']}\n\nPAKET BELUM ADA di "
                f"hidden_files (produksi belum menulis paket tanggal ini).\n")
    lg = r["ledger_submit"]
    lines = [f"# Paket siap — {r['tanggal']} (dirakit script, bukan keputusan)",
             f"- Paket ada; STATUS VERIFIKASI tercatat: {r['status_verifikasi_tercatat']}"
             f" (klaim terverifikasi {r.get('klaim_terverifikasi')})",
             f"- Klip tercantum: {r['jumlah_klip']} · file hilang dari disk: "
             f"{r['file_hilang'] or 'tidak ada'} · caption hashtag != 5: "
             f"{r['caption_hashtag_bukan_5'] or 'tidak ada'}",
             f"- Campaign DITAHAN di paket: {len(r['campaign_ditahan'])} item",
             f"- Ledger submit: TERSUBMIT {lg['tersubmit']} · DITOLAK {lg['ditolak']} · "
             f"BELUM {lg['belum']} · TAYANG-BELUM-SUBMIT (ALARM): "
             f"{lg['tayang_belum_submit'] or 'tidak ada'}",
             f"- Keputusan sesi sudah tercatat: {r['keputusan_tercatat']}"]
    return "\n".join(lines) + "\n"


def main():
    now = datetime.now(WIB)
    dates = [str(now.date()), str(now.date() + timedelta(days=1))]
    state = {}
    if STATE.exists():
        try:
            state = json.loads(STATE.read_text())
        except Exception:
            state = {}
    changed = []
    summaries = {}
    for tanggal in dates:
        r = build(tanggal)
        summaries[tanggal] = {k: r[k] for k in
                              ("paket_ada", "jumlah_klip", "file_hilang")
                              if k in r}
        if not r["paket_ada"]:
            continue
        (HIDDEN / f"paket-siap-{tanggal}.json").write_text(json.dumps(r, indent=1))
        (HIDDEN / f"paket-siap-{tanggal}.md").write_text(render_md(r))
        key = f"built:{tanggal}"
        sig = json.dumps(r["file_hilang"])
        if state.get(key) != sig:
            changed.append(f"paket_siap:{tanggal}")
            state[key] = sig
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=1))
    print(json.dumps({"changed": changed, "ringkasan": summaries}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
