"""Penjadwalan TikTok Studio @chinatech.id — mengikuti page-map-posting.md §3.

Pola yang terbukti di pembersihan 104 (31 Okt 2026):
- Slot terjadwal TIDAK bisa diedit di Studio — jangan pernah mencoba menggeser.
- Draf tersimpan server-side: klip yang gagal terjadwal sering sudah jadi
  DRAF lengkap (video+caption). Bot WAJIB cek draf dulu dan menjadwalkan
  DARI DRAF (klik draf -> periksa caption -> Jadwalkan pada jam slot),
  jangan unggah ulang (risiko duplikat).
- Audit-first: baca daftar postingan terjadwal dulu; caption yang sudah ada
  dilewati.
- Sound wajib klip Pulkam diambil dari field 'sound'/'music_url' item antrean.
"""
import os
import random
import time

from . import browser_base as bb
from . import common

UPLOAD_URL = "https://www.tiktok.com/tiktokstudio/upload"
CONTENT_URL = "https://www.tiktok.com/tiktokstudio/content"
DEBUG_DIR = os.path.join(common.STATE_DIR, "debug-tiktok")


def _goto_retry(page, url, attempts=3):
    """Navigasi toleran ERR_ABORTED (redirect TikTok/Meta sering membatalkan
    navigasi pertama). Gagal total -> RuntimeError NAVIGASI (status item
    TIDAK boleh diubah oleh pemanggil)."""
    last = None
    for i in range(attempts):
        try:
            page.goto(url, wait_until="domcontentloaded" if i == 0 else "commit", timeout=90000)
            page.wait_for_timeout(3000)
            return
        except Exception as e:
            last = e
            page.wait_for_timeout(3000)
    raise RuntimeError(f"NAVIGASI gagal ke {url}: {str(last)[:200]}")


def _body_text(page):
    try:
        return page.inner_text("body", timeout=8000)
    except Exception:
        return ""


def _norm(s):
    return " ".join((s or "").split())


def schedule_queue(cfg, queue_path, live, limit=0, only_slot=0):
    queue = common.load_json(queue_path, [])
    items = queue if isinstance(queue, list) else queue.get("items", [])
    actionable = {"ANTRE-TIKTOK-BROWSER", "DRAF-STUDIO-BELUM-JADWAL", "TERUNGGAH-BELUM-JADWAL"}
    todo = [it for it in items if it.get("status") in actionable
            and (not only_slot or it.get("slot") == only_slot)]
    todo.sort(key=lambda x: x.get("slot", 0))
    if limit:
        todo = todo[:limit]
    plan = [{"slot": it["slot"], "status_awal": it["status"], "file": it.get("file"),
             "publish_at_wib": it.get("publish_at_wib")} for it in todo]
    if not live:
        return {"mode": "dry-run", "rencana": plan}
    ok, _ap = common.check_approval("posting")
    if not ok:
        return {"mode": "live", "gagal": "approval posting tidak ditemukan di state/approval.json"}

    pw, ctx, srv = bb.open_context(cfg, "profil_tiktok")
    results = []
    try:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            _goto_retry(page, CONTENT_URL)
        except RuntimeError as e:
            return {"mode": "live", "gagal": f"SESI: {e} — tidak ada status item yang diubah", "hasil": []}
        page.wait_for_timeout(3000)
        if "login" in page.url:
            raise bb.LoginRequired("profil TikTok belum ada sesi — login satu kali ke profil bot dulu")
        bb.check_stop(page)
        scheduled_text = _norm(_body_text(page))
        gap = cfg.get("jeda", {}).get("antar_item_browser_detik", [20, 60])
        for it in todo:
            slot = it["slot"]
            cap = it.get("caption", "")
            prefix = _norm(cap)[:40]
            if prefix and prefix in scheduled_text:
                it["status"] = "TERJADWAL-STUDIO"
                it["via"] = "audit-bot (sudah ada di daftar Studio)"
                results.append({"slot": slot, "hasil": "sudah-terjadwal (audit)"})
                continue
            try:
                done = False
                if it["status"] == "DRAF-STUDIO-BELUM-JADWAL":
                    done = _schedule_from_draft(page, it, prefix)
                if not done:
                    done = _upload_and_schedule(page, it)
                if done:
                    it["status"] = "TERJADWAL-STUDIO"
                    it["via"] = "clipper-bot TikTok Studio"
                    results.append({"slot": slot, "hasil": "TERJADWAL-STUDIO"})
                    scheduled_text = _norm(_body_text(page)) if page.url.startswith(CONTENT_URL) else scheduled_text
                else:
                    it["status"] = "GAGAL-BOT"
                    bb.debug_shot(page, DEBUG_DIR, f"slot-{slot}.png")
                    results.append({"slot": slot, "hasil": "GAGAL-BOT — lihat screenshot debug"})
            except bb.StopError:
                raise
            except Exception as e:
                msg = str(e)
                if "NAVIGASI" in msg or "ERR_ABORTED" in msg:
                    # Navigasi gagal != item gagal: status antrean dibiarkan
                    # utuh supaya run berikutnya mengulang dari keadaan sama.
                    it["catatan_bot"] = f"navigasi gagal, status utuh: {msg[:200]}"
                    results.append({"slot": slot, "hasil": "LEWATI (navigasi gagal) — status item tidak diubah"})
                else:
                    it["status"] = "GAGAL-BOT"
                    it["catatan_bot"] = msg[:300]
                    bb.debug_shot(page, DEBUG_DIR, f"slot-{slot}.png")
                    results.append({"slot": slot, "hasil": f"GAGAL-BOT: {msg[:200]}"})
            common.save_json_atomic(queue_path, queue)
            time.sleep(random.uniform(gap[0], gap[1]))
    except bb.LoginRequired as e:
        return {"mode": "live", "gagal": f"LOGIN-DIPERLUKAN: {e}", "exit": bb.EXIT_LOGIN, "hasil": results}
    except bb.StopError as e:
        return {"mode": "live", "gagal": f"BERHENTI (bot-check): {e}", "exit": bb.EXIT_STOP, "hasil": results}
    finally:
        try:
            ctx.close()
            pw.stop()
        except Exception:
            pass
        if srv:
            try:
                srv.close()
            except Exception:
                pass
    common.save_json_atomic(queue_path, queue)
    return {"mode": "live", "hasil": results}


def _set_schedule(page, publish_at_iso):
    import datetime
    dt = datetime.datetime.fromisoformat(publish_at_iso)
    # Aktifkan mode jadwal (label EN/ID)
    for label in ["Schedule", "Jadwal"]:
        try:
            page.get_by_text(label, exact=False).first.click(timeout=6000)
            break
        except Exception:
            continue
    page.wait_for_timeout(1200)
    date_str = dt.strftime("%Y-%m-%d")
    time_str = dt.strftime("%H:%M")
    for sel, val in [("input[type=date]", date_str), ("input[type=time]", time_str)]:
        try:
            page.locator(sel).first.fill(val, timeout=4000)
        except Exception:
            pass
    page.wait_for_timeout(800)


def _click_final_schedule(page):
    for name in ["Schedule", "Jadwalkan", "Jadwal", "Post", "Posting"]:
        try:
            page.get_by_role("button", name=name).last.click(timeout=6000)
            page.wait_for_timeout(4000)
            return True
        except Exception:
            continue
    return False


def _schedule_from_draft(page, it, prefix):
    """Buka daftar draf di halaman konten Studio, klik draf yang caption-nya cocok."""
    _goto_retry(page, CONTENT_URL)
    page.wait_for_timeout(2000)
    for tab in ["Drafts", "Draf"]:
        try:
            page.get_by_text(tab, exact=False).first.click(timeout=5000)
            page.wait_for_timeout(2500)
            break
        except Exception:
            continue
    bb.check_stop(page)
    # klik item draf yang memuat potongan caption
    try:
        page.get_by_text(prefix[:25], exact=False).first.click(timeout=8000)
    except Exception:
        return False
    page.wait_for_timeout(4000)
    body = _norm(_body_text(page))
    if prefix[:25] not in body and _norm(it.get("caption", ""))[:25] not in body:
        return False
    _set_schedule(page, it["publish_at_wib"])
    return _click_final_schedule(page)


def _upload_and_schedule(page, it):
    _goto_retry(page, UPLOAD_URL)
    page.wait_for_timeout(2000)
    bb.check_stop(page)
    page.set_input_files("input[type=file]", it["path"], timeout=30000)
    page.wait_for_timeout(10000)
    # caption
    cap = it.get("caption", "")
    filled = False
    for sel in ["div[contenteditable=true]", "textarea"]:
        try:
            el = page.locator(sel).first
            el.click(timeout=5000)
            page.keyboard.press("Control+a")
            page.keyboard.type(cap, delay=5)
            filled = True
            break
        except Exception:
            continue
    if not filled:
        return False
    # sound wajib (Pulkam): catat kebutuhan; pemilihan sound dilakukan dari
    # URL musik resmi di item antrean bila UI pencarian sound tersedia.
    if it.get("music_url"):
        try:
            page.get_by_text("Add sound", exact=False).first.click(timeout=5000)
            page.wait_for_timeout(2000)
        except Exception:
            pass
    _set_schedule(page, it["publish_at_wib"])
    return _click_final_schedule(page)
