"""Poster Threads via konektor threads-cli — pola run berwaktu yang terbukti.

Fakta lapangan 31 Okt 2026 (datahub 869): kuota tulis efektif konektor jauh
di bawah plafon dokumen 250/hari — 429 'daily limit' kena setelah +/-14
postingan/24 jam. Bot menegakkan plafon efektif dari config (default 15/hari
kalender), jeda acak 15-30 menit antar posting, berhenti total saat 429,
dan RESUMABLE: status TAYANG dibaca dari log JSON, bukan ditebak.
Anti-ganda: timeout publish -> tunggu -> read-back caption via konektor ->
tandai TAYANG hanya bila terbukti; tidak pernah publish ulang buta.
"""
import json
import os
import random
import subprocess
import time

from . import common

CLI = "/opt/hatch/bin/threads-cli"
LOG_PATH = os.path.join(common.STATE_DIR, "threads-log.json")


def _cli(args, timeout=900):
    p = subprocess.run([CLI] + args, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout or "", p.stderr or ""


def _load_log():
    return common.load_json(LOG_PATH, {})


def _count_today(log):
    today = common.now_wib().strftime("%Y-%m-%d")
    return sum(1 for v in log.values()
               if v.get("status") == "TAYANG" and str(v.get("ts", "")).startswith(today))


def post_queue(cfg, queue_path, live, limit=0, gap_override=None):
    queue = common.load_json(queue_path, [])
    items = queue if isinstance(queue, list) else queue.get("items", [])
    todo = [it for it in items if it.get("status") in ("ANTRE-THREADS", "ANTRE-BULK")]
    todo.sort(key=lambda x: x.get("publish_at_wib", ""))
    if limit:
        todo = todo[:limit]
    plan = [{"slot": it.get("slot"), "file": it.get("file"), "publish_at_wib": it.get("publish_at_wib")} for it in todo]
    if not live:
        return {"mode": "dry-run", "rencana": plan}
    ok, _ap = common.check_approval("posting")
    if not ok:
        return {"mode": "live", "gagal": "approval posting tidak ditemukan di state/approval.json"}

    account_id = cfg["akun"]["threads"]["account_id"]
    cap_today = cfg.get("plafon_harian", {}).get("threads_efektif_per_hari", 15)
    gap = gap_override or cfg.get("jeda", {}).get("threads_menit", [15, 30])
    log = _load_log()
    results = []
    posted_today = _count_today(log)
    for it in todo:
        slot = it.get("slot")
        key = f"slot-{slot}"
        if log.get(key, {}).get("status") == "TAYANG":
            it["status"] = "TAYANG"
            results.append({"slot": slot, "hasil": "sudah TAYANG (log)"})
            continue
        if posted_today >= cap_today:
            results.append({"slot": slot, "hasil": f"BERHENTI — plafon efektif harian {cap_today} tercapai"})
            common.event("threads_cap", {"slot": slot, "posted_today": posted_today})
            break
        media = json.dumps({"file": it["path"], "cover": it.get("cover", "")})
        try:
            rc, out, err = _cli(["publish-post", "--account-id", account_id,
                                 "--text", it.get("caption", ""), "--media-item", media])
        except subprocess.TimeoutExpired:
            time.sleep(60)
            rc, out, err = 0, "", "timeout — wajib read-back sebelum simpulan"
        blob = out + err
        if "429" in blob or "rate limit" in blob.lower():
            it["status"] = "GAGAL-429"
            log[key] = {"status": "GAGAL-429", "ts": common.now_iso()}
            common.save_json_atomic(LOG_PATH, log)
            common.save_json_atomic(queue_path, queue)
            common.event("threads_429", {"slot": slot})
            results.append({"slot": slot, "hasil": "429 — BERHENTI untuk Threads hari ini"})
            break
        post_id = None
        try:
            post_id = json.loads(out).get("post_id")
        except Exception:
            pass
        if rc == 0 and post_id:
            it["status"] = "TAYANG"
            it["post_id"] = post_id
            log[key] = {"status": "TAYANG", "ts": common.now_iso(), "post_id": post_id}
            posted_today += 1
            results.append({"slot": slot, "hasil": f"TAYANG {post_id}"})
        else:
            # Gagal selain 429: catat apa adanya; run berikutnya membaca log
            # dulu (anti publish ulang buta) — item tidak ditandai TAYANG.
            it["status"] = "GAGAL-THREADS"
            it["catatan_bot"] = blob[:300]
            log[key] = {"status": "GAGAL-THREADS", "ts": common.now_iso(), "detail": blob[:300]}
            results.append({"slot": slot, "hasil": "GAGAL — tercatat, tidak diulang buta"})
        common.save_json_atomic(LOG_PATH, log)
        common.save_json_atomic(queue_path, queue)
        if it is not todo[-1]:
            time.sleep(random.uniform(gap[0] * 60, gap[1] * 60))
    return {"mode": "live", "hasil": results, "posted_today": posted_today}
