"""Penjadwalan Instagram via Meta Business Suite — mengikuti page-map-posting.md §1.

Alur terbukti: business.facebook.com/latest/home -> Create reel -> unggah ->
caption persis -> Schedule ("Set date and time") -> tanggal+jam slot ->
Schedule final -> VERIFIKASI WAJIB di Content > tab Scheduled (toast saja
tidak cukup). Tujuan 'Facebook Page' [disabled] selama belum ada Page —
jangan diklik paksa; dicatat per item.

Audit-first & idempoten: sebelum menjadwalkan, daftar Scheduled dibaca;
item yang caption-nya sudah ada dilewati. Status ditulis ke file antrean
(status TERJADWAL-META) supaya run berikutnya tidak mengulang.
"""
import datetime
import os
import random
import time

from . import browser_base as bb
from . import common

SUITE_HOME = "https://business.facebook.com/latest/home"
SUITE_CONTENT = "https://business.facebook.com/latest/content"
DEBUG_DIR = os.path.join(common.STATE_DIR, "debug-ig")


def _scheduled_captions(page):
    page.goto(SUITE_CONTENT, wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(4000)
    try:
        page.get_by_text("Scheduled", exact=False).first.click(timeout=8000)
        page.wait_for_timeout(3000)
    except Exception:
        pass
    bb.check_stop(page)
    try:
        return page.inner_text("body", timeout=8000)
    except Exception:
        return ""


def _fmt_date(dt):
    return dt.strftime("%m/%d/%Y")


def _fmt_time(dt):
    return dt.strftime("%I:%M %p").lstrip("0")


def schedule_queue(cfg, queue_path, live, limit=0, only_slot=0):
    queue = common.load_json(queue_path, [])
    items = queue if isinstance(queue, list) else queue.get("items", [])
    todo = [it for it in items
            if it.get("status") == "ANTRE-IG-BROWSER"
            and (not only_slot or it.get("slot") == only_slot)]
    if limit:
        todo = todo[:limit]
    plan = [{"slot": it["slot"], "file": it.get("file"), "publish_at_wib": it.get("publish_at_wib")} for it in todo]
    if not live:
        return {"mode": "dry-run", "rencana": plan}
    ok, _ap = common.check_approval("posting")
    if not ok:
        return {"mode": "live", "gagal": "approval posting tidak ditemukan di state/approval.json"}

    pw, ctx, srv = bb.open_context(cfg, "profil_meta")
    results = []
    try:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(SUITE_HOME, wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(5000)
        if "loginpage" in page.url or "login" in page.url:
            raise bb.LoginRequired("profil Meta belum ada sesi — login satu kali ke profil bot dulu")
        bb.check_stop(page)
        scheduled_text = _scheduled_captions(page)
        gap = cfg.get("jeda", {}).get("antar_item_browser_detik", [20, 60])
        for it in todo:
            slot = it["slot"]
            cap = it.get("caption", "")
            prefix = " ".join(cap.split())[:40]
            if prefix and prefix in " ".join(scheduled_text.split()):
                it["status"] = "TERJADWAL-META"
                it["via"] = "audit-bot (sudah ada di Scheduled)"
                results.append({"slot": slot, "hasil": "sudah-terjadwal (audit)"})
                continue
            try:
                dt = datetime.datetime.fromisoformat(it["publish_at_wib"])
                page.goto(SUITE_HOME, wait_until="domcontentloaded", timeout=90000)
                page.wait_for_timeout(3000)
                page.get_by_text("Create reel", exact=False).first.click(timeout=15000)
                page.wait_for_timeout(3000)
                page.set_input_files("input[type=file]", it["path"], timeout=20000)
                page.wait_for_timeout(8000)
                # caption: editor komposer (contenteditable / textarea)
                filled = False
                for sel in ["div[contenteditable=true]", "textarea"]:
                    try:
                        page.locator(sel).first.click(timeout=5000)
                        page.keyboard.type(cap, delay=5)
                        filled = True
                        break
                    except Exception:
                        continue
                if not filled:
                    raise RuntimeError("editor caption tidak ditemukan")
                for _ in range(2):
                    try:
                        page.get_by_text("Next", exact=True).first.click(timeout=6000)
                        page.wait_for_timeout(2000)
                    except Exception:
                        break
                page.get_by_text("Schedule", exact=False).first.click(timeout=12000)
                page.wait_for_timeout(1500)
                page.locator("input[placeholder*='MM/DD/YYYY'], input[placeholder*='Date']").first.fill(_fmt_date(dt))
                page.locator("input[placeholder*='hh'], input[placeholder*='Time']").first.fill(_fmt_time(dt))
                page.wait_for_timeout(1000)
                bb.check_stop(page)
                page.get_by_role("button", name="Schedule").last.click(timeout=12000)
                page.wait_for_timeout(5000)
                verify = _scheduled_captions(page)
                if prefix in " ".join(verify.split()):
                    it["status"] = "TERJADWAL-META"
                    it["via"] = "clipper-bot Business Suite"
                    results.append({"slot": slot, "hasil": "TERJADWAL-META (terverifikasi Content>Scheduled)"})
                    scheduled_text = verify
                else:
                    it["status"] = "GAGAL-VERIFIKASI"
                    bb.debug_shot(page, DEBUG_DIR, f"slot-{slot}.png")
                    results.append({"slot": slot, "hasil": "GAGAL-VERIFIKASI — tidak muncul di Scheduled"})
            except bb.StopError:
                raise
            except Exception as e:
                it["status"] = "GAGAL-BOT"
                it["catatan_bot"] = str(e)[:300]
                bb.debug_shot(page, DEBUG_DIR, f"slot-{slot}.png")
                results.append({"slot": slot, "hasil": f"GAGAL-BOT: {str(e)[:200]}"})
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
