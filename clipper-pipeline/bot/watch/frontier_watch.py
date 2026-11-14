#!/usr/bin/env python3
"""clipper-frontier-watch — pantau frontier antrean pembersihan 104
untuk Company Bot Divisi Freelancer & Clipper. Read-only penuh,
TANPA jaringan: membaca file antrean + log worker lokal saja.

Sumber:
  - IG: goals/moderate-company-setup/hidden_files/bulk-104-ig-queue.json
    (terkonfirmasi = status TERJADWAL-META atau TERBIT*; frontier =
    slot terkecil yang belum terkonfirmasi)
  - TikTok: .../bulk-104-tiktok-queue.json (TERJADWAL-STUDIO, draf)
  - Threads: .../threads-log-2026-10-31.json (status efektif per slot
    utama 1-20 = entri terakhir per slot) + ekor
    threads-timed-2026-10-31.out + cek proses worker di /proc.
Ringkasan disimpan sebagai baseline (state/frontier_state.json);
"changed" berisi nama field yang berubah sejak baseline, "events"
rinciannya {field, from, to}. Run pertama = seed tanpa event.
Output tepat SATU baris JSON: {"changed": [...], "events": [...]}
Eksekusi/tindak lanjut BUKAN di sini — agent-on-event via hook
clipper-trigger-frontier.
"""
import glob
import json
import os
import sys

HIDDEN = os.path.expanduser(
    "~/workspace/goals/moderate-company-setup/hidden_files")
STATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state")
STATE = os.path.join(STATE_DIR, "frontier_state.json")


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def items_of(data):
    return data if isinstance(data, list) else data.get("items", [])


def ig_summary():
    items = items_of(load_json(os.path.join(HIDDEN, "bulk-104-ig-queue.json")))
    confirmed, terjadwal, terbit, antre = set(), 0, 0, 0
    for it in items:
        s = it.get("status") or ""
        if s == "TERJADWAL-META":
            terjadwal += 1
            confirmed.add(it.get("slot"))
        elif s.startswith("TERBIT"):
            terbit += 1
            confirmed.add(it.get("slot"))
        elif s.startswith("ANTRE"):
            antre += 1
    frontier = None
    for slot in range(1, 105):
        if slot not in confirmed:
            frontier = slot
            break
    return {"ig_terjadwal": terjadwal, "ig_terbit": terbit,
            "ig_antre": antre, "ig_frontier_next": frontier}


def tiktok_summary():
    items = items_of(load_json(
        os.path.join(HIDDEN, "bulk-104-tiktok-queue.json")))
    terjadwal = sum(1 for it in items
                    if (it.get("status") or "") == "TERJADWAL-STUDIO")
    draf = sum(1 for it in items
               if "DRAF" in (it.get("status") or ""))
    antre = sum(1 for it in items
                if (it.get("status") or "").startswith("ANTRE"))
    return {"tiktok_terjadwal": terjadwal, "tiktok_draf": draf,
            "tiktok_antre": antre}


def threads_summary():
    items = items_of(load_json(
        os.path.join(HIDDEN, "threads-log-2026-10-31.json")))
    eff = {}
    for it in items:
        s = it.get("slot")
        if isinstance(s, int) and 1 <= s <= 20:
            eff[s] = it.get("status")
    tayang = sum(1 for v in eff.values() if v == "TAYANG")
    worker = "tidak-aktif"
    for pid in glob.glob("/proc/[0-9]*/cmdline"):
        try:
            with open(pid, "rb") as f:
                cmd = f.read().replace(b"\0", b" ").decode("utf-8", "ignore")
        except Exception:
            continue
        if "threads-timed-2026-10-31" in cmd and "python" in cmd:
            worker = "jalan"
            break
    if worker != "jalan":
        try:
            with open(os.path.join(
                    HIDDEN, "threads-timed-2026-10-31.out"),
                    encoding="utf-8", errors="ignore") as f:
                tail = f.read()[-2000:]
            if "BERHENTI" in tail or "RATE LIMIT" in tail:
                worker = "berhenti-rate-limit"
        except Exception:
            pass
    if tayang >= 20:
        worker = "selesai"
    return {"threads_tayang": tayang, "threads_worker": worker}


def main():
    try:
        snap = {}
        snap.update(ig_summary())
        snap.update(tiktok_summary())
        snap.update(threads_summary())
    except Exception as e:
        print(json.dumps({"changed": [], "events": [], "fetch": "error",
                          "error": str(e)[:150]}))
        return 0
    base = None
    if os.path.exists(STATE):
        try:
            base = load_json(STATE)
        except Exception:
            base = None
    if base is None:
        os.makedirs(STATE_DIR, exist_ok=True)
        tmp = STATE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(snap, f, indent=1, sort_keys=True)
        os.replace(tmp, STATE)
        print(json.dumps({"changed": [], "events": [], "seeded": True,
                          "snapshot": snap}))
        return 0
    changed, events = [], []
    for k in sorted(snap):
        if snap[k] != base.get(k):
            changed.append(k)
            events.append({"field": k, "from": base.get(k), "to": snap[k]})
    if changed:
        tmp = STATE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(snap, f, indent=1, sort_keys=True)
        os.replace(tmp, STATE)
    print(json.dumps({"changed": changed, "events": events,
                      "snapshot": snap}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
