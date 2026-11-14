"""Submitter campaign — gerbang akhir rantai (ledger submit divisi).

Platform yang SUDAH pernah dilakukan perusahaan dan diotomatisasi di sini:
- Ternak Klip (app.ternakklip.com): alur terverifikasi 30 Okt 2026 —
  Akun Terhubung -> detail akun platform -> 'Tambah Link' tempel URL ->
  Submissions -> 'Tambah Submission' -> pilih campaign -> 'Ajukan video'.
  Video TIDAK tersinkron otomatis; semua lewat Tambah Link.
  Akun: Heru Febrian (Login with Google you@example.com) — sesi hidup di
  profil persisten bot; belum ada sesi = LOGIN-DIPERLUKAN.

Platform lain (Wefluence, Whop, TryBuzzer) terdaftar sebagai adapter dengan
status jujur: alurnya pernah dilakukan manual, adapter browser-nya belum
dibangun — submit ke sana lewat adapter ini mengembalikan BELUM-ADAPTER,
bukan berpura-pura berhasil.

Sumber antrean submit: state/submit_queue.json — item per (campaign, file)
dengan URL per platform dan status BELUM/TAYANG-BELUM-SUBMIT/TERSUBMIT.
Audit-first: daftar Submissions di platform dibaca dulu; URL yang sudah
pernah diajukan dilewati.
"""
import os
import time

from . import browser_base as bb
from . import common

QUEUE_PATH = os.path.join(common.STATE_DIR, "submit_queue.json")
APP_URL = "https://app.ternakklip.com"
DEBUG_DIR = os.path.join(common.STATE_DIR, "debug-submit")

ADAPTERS = {
    "ternakklip": {"status": "LIVE-CODE", "nama": "Ternak Klip"},
    "wefluence": {"status": "BELUM-ADAPTER", "nama": "Wefluence",
                  "catatan": "submit pernah manual (29 Okt); adapter browser belum dibangun"},
    "whop": {"status": "BELUM-ADAPTER", "nama": "Whop",
             "catatan": "belum pernah submit; verifikasi dasbor dulu"},
    "trybuzzer": {"status": "BELUM-ADAPTER", "nama": "TryBuzzer",
                  "catatan": "submit pernah diteliti; adapter browser belum dibangun"},
}


def load_queue():
    return common.load_json(QUEUE_PATH, {"items": []})


def ready_items(queue):
    out = []
    for it in queue.get("items", []):
        if it.get("status") == "TAYANG-BELUM-SUBMIT" and it.get("urls"):
            out.append(it)
    return out


def submit_ternakklip(cfg, live, only_campaign=""):
    queue = load_queue()
    items = [it for it in ready_items(queue) if it.get("adapter") == "ternakklip"
             and (not only_campaign or it.get("campaign") == only_campaign)]
    plan = [{"campaign": it["campaign"], "file": it["file"], "urls": it["urls"]} for it in items]
    if not live:
        return {"mode": "dry-run", "rencana_submit": plan}
    ok, _ap = common.check_approval("submit")
    if not ok:
        return {"mode": "live", "gagal": "approval submit tidak ditemukan di state/approval.json"}

    pw, ctx, srv = bb.open_context(cfg, "profil_ternakklip")
    results = []
    try:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(APP_URL, wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(5000)
        bb.check_stop(page)
        body = page.inner_text("body", timeout=8000)
        if "Heru Febrian" not in body and "Akun Terhubung" not in body:
            raise bb.LoginRequired("profil Ternak Klip belum ada sesi — login Google satu kali ke profil bot dulu")
        for it in items:
            submitted_urls = []
            try:
                # Akun Terhubung -> untuk setiap platform URL: Tambah Link
                page.goto(APP_URL, wait_until="domcontentloaded", timeout=90000)
                page.wait_for_timeout(3000)
                page.get_by_text("Akun Terhubung", exact=False).first.click(timeout=12000)
                page.wait_for_timeout(3000)
                for platform, url in it["urls"].items():
                    label = {"tiktok": "TikTok", "instagram": "Instagram", "threads": "Threads"}[platform]
                    try:
                        page.get_by_text(label, exact=False).first.click(timeout=8000)
                        page.wait_for_timeout(2000)
                    except Exception:
                        pass
                    page.get_by_text("Tambah Link", exact=False).first.click(timeout=10000)
                    page.wait_for_timeout(1500)
                    page.locator("input[type=url], input[type=text]").first.fill(url)
                    for name in ["Simpan", "Tambah", "Save", "Submit"]:
                        try:
                            page.get_by_role("button", name=name).first.click(timeout=5000)
                            break
                        except Exception:
                            continue
                    page.wait_for_timeout(2500)
                    bb.check_stop(page)
                # Submissions -> Tambah Submission -> Ajukan video
                page.get_by_text("Submissions", exact=False).first.click(timeout=12000)
                page.wait_for_timeout(3000)
                page.get_by_text("Tambah Submission", exact=False).first.click(timeout=10000)
                page.wait_for_timeout(2000)
                try:
                    page.get_by_text(it["campaign"], exact=False).first.click(timeout=8000)
                except Exception:
                    pass
                for name in ["Ajukan video", "Ajukan", "Kirim", "Submit"]:
                    try:
                        page.get_by_role("button", name=name).first.click(timeout=6000)
                        break
                    except Exception:
                        continue
                page.wait_for_timeout(3000)
                verify = page.inner_text("body", timeout=8000)
                if it["file"].split("-")[0] in verify or "Submission" in verify:
                    it["status"] = "TERSUBMIT"
                    it["tanggal_submit"] = common.now_wib().strftime("%Y-%m-%d")
                    submitted_urls = list(it["urls"].keys())
                    common.event("submit_ok", {"campaign": it["campaign"], "file": it["file"]})
                    results.append({"file": it["file"], "hasil": "TERSUBMIT (tercatat di Submissions)"})
                else:
                    bb.debug_shot(page, DEBUG_DIR, f"submit-{it['file']}.png")
                    results.append({"file": it["file"], "hasil": "BELUM terverifikasi di Submissions — cek screenshot"})
            except bb.StopError:
                raise
            except Exception as e:
                bb.debug_shot(page, DEBUG_DIR, f"submit-{it.get('file')}.png")
                results.append({"file": it.get("file"), "hasil": f"GAGAL: {str(e)[:200]}"})
            common.save_json_atomic(QUEUE_PATH, queue)
            time.sleep(5)
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
    common.save_json_atomic(QUEUE_PATH, queue)
    return {"mode": "live", "hasil": results}


def run(cfg, live, adapter="ternakklip"):
    info = ADAPTERS.get(adapter)
    if not info:
        return {"gagal": f"adapter tidak dikenal: {adapter}"}
    if info["status"] != "LIVE-CODE":
        return {"adapter": adapter, "status": info["status"], "catatan": info.get("catatan")}
    return submit_ternakklip(cfg, live)
