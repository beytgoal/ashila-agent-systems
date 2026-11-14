#!/usr/bin/env python3
"""clipper-bot — bot otomatis Divisi Freelancer & Clipper (Moderate).

Perintah owner 31 Okt 2026 19:34 WIB: satu script bot untuk seluruh rantai
yang sudah pernah dilakukan divisi ini:
  research  — riset otomatis campaign/jobs (snapshot datahub + platform, diff saja)
  clip      — tugas kliping (unduh->transkrip->seleksi->render cutter v3.6->QA)
  schedule  — posting terjadwal via browser (IG Business Suite, TikTok Studio)
              + Threads via konektor berwaktu (plafon efektif, anti-429)
  harvest   — panen URL tayang campaign dari konektor/log
  submit    — submit link ke platform campaign (Ternak Klip live-code;
              Wefluence/Whop/TryBuzzer adapter menyusul, status jujur)
  status    — ringkasan state bot (antrean, submit, event terakhir)

Prinsip (peta-otomatisasi-bot.md + koreksi arsitektur owner 31 Okt 19:36):
pemrosesan data (query datahub, antrean, state) murni skrip tanpa agent di
tengah; agent hanya membaca HASIL OLAHAN di ujung, mengevaluasi, memperbaiki.

Keamanan: default DRY-RUN. Aksi live butuh --live DAN approval pada
state/approval.json. Captcha/checkpoint = berhenti total jalur itu (exit 3).
Profil belum login = LOGIN-DIPERLUKAN (exit 2). Idempoten + audit-first di
semua poster: yang sudah terjadwal/tayang/submit tidak pernah diulang.

Jalan dengan python venv Playwright:
  xvfb-run -a ~/workspace/scratch/cliptest2/meta-venv/bin/python clipper_bot.py <perintah> [opsi]
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib import common  # noqa: E402


def _print(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=1))


def main():
    ap = argparse.ArgumentParser(prog="clipper_bot", description="Bot otomatis Divisi Freelancer & Clipper")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("research")
    p.add_argument("--live", action="store_true", help="tulis snapshot + event (default: dry-run)")

    p = sub.add_parser("clip")
    p.add_argument("--manifest", required=True)
    p.add_argument("--live", action="store_true")

    p = sub.add_parser("schedule")
    p.add_argument("--platform", choices=["ig", "tiktok", "threads"], required=True)
    p.add_argument("--queue", required=True, help="file antrean JSON platform")
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--only-slot", type=int, default=0)
    p.add_argument("--live", action="store_true")

    p = sub.add_parser("harvest")

    p = sub.add_parser("submit")
    p.add_argument("--adapter", default="ternakklip")
    p.add_argument("--live", action="store_true")

    p = sub.add_parser("status")

    args = ap.parse_args()
    cfg = common.load_config()

    with common.SingleInstance(f"clipper-bot-{args.cmd}"):
        if args.cmd == "research":
            from lib import research
            _print(research.run(cfg, dry_run=not args.live))
        elif args.cmd == "clip":
            from lib import clip
            _print(clip.run_manifest(args.manifest, cfg, dry_run=not args.live))
        elif args.cmd == "schedule":
            if args.platform == "ig":
                from lib import post_ig
                res = post_ig.schedule_queue(cfg, args.queue, args.live, args.limit, args.only_slot)
            elif args.platform == "tiktok":
                from lib import post_tiktok
                res = post_tiktok.schedule_queue(cfg, args.queue, args.live, args.limit, args.only_slot)
            else:
                from lib import post_threads
                res = post_threads.post_queue(cfg, args.queue, args.live, args.limit)
            _print(res)
            sys.exit(res.get("exit", 0))
        elif args.cmd == "harvest":
            from lib import harvest
            _print(harvest.run(cfg))
        elif args.cmd == "submit":
            from lib import submit
            res = submit.run(cfg, args.live, args.adapter)
            _print(res)
            sys.exit(res.get("exit", 0))
        elif args.cmd == "status":
            from lib import submit as submit_mod
            sq = submit_mod.load_queue()
            events = []
            if os.path.exists(common.EVENTS_PATH):
                with open(common.EVENTS_PATH, encoding="utf-8") as f:
                    events = [json.loads(x) for x in f.readlines()[-10:] if x.strip()]
            _print({
                "approval": common.load_json(os.path.join(common.STATE_DIR, "approval.json"), {}),
                "submit_queue": [
                    {"campaign": it["campaign"], "file": it["file"], "status": it["status"]}
                    for it in sq.get("items", [])
                ],
                "adapters": submit_mod.ADAPTERS,
                "event_terakhir": events,
            })


if __name__ == "__main__":
    main()
