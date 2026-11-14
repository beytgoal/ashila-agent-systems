#!/usr/bin/env python3
"""video_pipeline.py — pipeline video ujung-ke-ujung Divisi Branding
& Promosi: SATU file proyek JSON -> VO (default Muse TTS) -> render
serial -> QA otomatis -> video final + laporan QA.

Dibangun 2026-10-31 menyusul perintah owner 18:23/18:47 WIB (default
VO terkunci = TTS bawaan Muse) + perintah lanjutan 18:50 WIB
"Lanjutkan bikin script pipeline video nya."

Alur (gagal di tahap mana pun = berhenti dengan pesan tahap + alasan;
tidak ada tahap yang dilewati diam-diam):
  1. VALIDASI  — proyek JSON: segmen unik, teks tidak kosong, gender
                 per segmen sah (male/female), bed ada bila disebut.
  2. PERSIAPAN — salinan teks TTS (naskah asli TIDAK diubah):
                 - cowok (miles): salinan fonetik — tanda hubung "-"
                   diganti spasi (aturan naskah miles dari owner);
                 - cewek (MAI_01): teks apa adanya + catatan pecahan
                   potongan pendek (pemecahan klausa dilakukan
                   voice_router per potongan, peta jeda v2).
                 Hasil persiapan ditulis ke <out-dir>/naskah-tts.json.
  3. VO        — voice_router.py --segments per kelompok gender
                 (rute auto = DEFAULT BARU muse-tts; backend lama
                 TIDAK dipilih). voice_log.json per kelompok disimpan
                 dan digabung ke <out-dir>/voice_log.json.
  4. RENDER    — motion_render.py dengan proyek engine yang dibangkit-
                 kan dari proyek ini; mix terkunci voice -15 LUFS /
                 bed -34 LUFS hidup di engine (bukan di sini).
  5. QA        — ffprobe 1080x1920 (atau ukuran proyek), durasi video
                 >= total durasi VO - toleransi, LUFS final terukur,
                 jendela VO per scene, rantai bed terukur ~= -34,
                 voice_log membuktikan backend muse-tts + voice
                 terkunci per gender, tidak ada segmen VO hilang.
                 Laporan: <out-dir>/qa-report.json + qa-report.md.

Pakai:
  python3 video_pipeline.py --project proyek.json --out-dir hasil/
  python3 video_pipeline.py --project proyek.json --out-dir hasil/ --dry-run
  python3 video_pipeline.py --project proyek.json --out-dir hasil/ --skip-render

Format proyek JSON:
{
  "title": "slug-judul",
  "gender": "male",                  # gender bawaan proyek (male/female)
  "bed": "path/bed.mp3",             # opsional tapi disarankan (mix terkunci)
  "style": "cinematic",              # style engine (bawaan cinematic)
  "fps": 30, "width": 1080, "height": 1920,
  "segments": [
    {"id": "s1", "text": "Teks narasi...",
     "gender": "female",             # opsional, menimpa gender proyek
     "kicker": "001 — PEMBUKA",      # opsional (scene engine)
     "headline": "KATA KUNCI",       # opsional
     "body": "Baris satu@@NL@@Baris dua"}   # opsional
  ]
}
"""
import argparse, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROUTER = os.path.join(HERE, "voice_router.py")
RENDER = os.path.join(HERE, "motion_render.py")
sys.path.insert(0, HERE)
import voice_router as vr  # noqa: E402 — reuse pemecah klausa + konstanta

LOCKED_VOICE = {"male": vr.MUSE_TTS_VOICE_MALE,
                "female": vr.MUSE_TTS_VOICE_FEMALE}
ROUTER_VOICE = {"male": "default", "female": "female"}
TARGET_VO_LUFS = -15.0
TARGET_BED_LUFS = -34.0


class StageError(Exception):
    def __init__(self, stage, msg):
        super().__init__(msg)
        self.stage = stage
        self.msg = msg


def _run(cmd, stage, **kw):
    p = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if p.returncode != 0:
        tail = ((p.stderr or "") + (p.stdout or ""))[-500:]
        raise StageError(stage, f"perintah gagal (rc={p.returncode}): "
                                f"{' '.join(cmd[:3])}... — {tail}")
    return p


def _lufs(path):
    p = subprocess.run(["ffmpeg", "-i", path, "-af",
                        "loudnorm=print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    s = p.stderr
    i, j = s.find("{"), s.rfind("}")
    return float(json.loads(s[i:j + 1])["input_i"])


def _lufs_window(path, start, dur):
    p = subprocess.run(["ffmpeg", "-ss", f"{start:.2f}", "-t", f"{dur:.2f}",
                        "-i", path, "-af", "loudnorm=print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True)
    s = p.stderr
    i, j = s.find("{"), s.rfind("}")
    return float(json.loads(s[i:j + 1])["input_i"])


def _probe(path):
    p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=width,height",
                        "-show_entries", "format=duration",
                        "-of", "json", path], capture_output=True, text=True)
    d = json.loads(p.stdout)
    st = d["streams"][0]
    return int(st["width"]), int(st["height"]), float(d["format"]["duration"])


def _dur(path):
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    return float(p.stdout.strip())


# ---------------------------------------------------------------- tahap 1
def validate(proj, proj_path):
    errs = []
    if not isinstance(proj, dict):
        raise StageError("validasi", "proyek harus objek JSON")
    title = proj.get("title")
    if not title or not isinstance(title, str):
        errs.append("field 'title' wajib (string)")
    g = proj.get("gender", "male")
    if g not in ("male", "female"):
        errs.append(f"gender proyek tidak sah: {g!r} (male/female)")
    segs = proj.get("segments")
    if not segs or not isinstance(segs, list):
        errs.append("field 'segments' wajib (list, minimal 1)")
        segs = []
    seen = set()
    for n, s in enumerate(segs):
        sid = s.get("id")
        if not sid or not isinstance(sid, str):
            errs.append(f"segmen #{n}: 'id' wajib")
            continue
        if sid in seen:
            errs.append(f"id segmen duplikat: {sid}")
        seen.add(sid)
        if any(c in sid for c in "/\\ \t"):
            errs.append(f"id segmen mengandung karakter terlarang: {sid!r}")
        if not s.get("text") or not str(s["text"]).strip():
            errs.append(f"segmen {sid}: 'text' kosong")
        sg = s.get("gender", g)
        if sg not in ("male", "female"):
            errs.append(f"segmen {sid}: gender tidak sah {sg!r}")
    bed = proj.get("bed")
    if bed and not os.path.exists(bed):
        errs.append(f"bed tidak ditemukan: {bed}")
    if errs:
        raise StageError("validasi", "; ".join(errs))
    return title


# ---------------------------------------------------------------- tahap 2
def prepare(proj):
    """Bangun daftar segmen TTS: {id, text_asli, text_tts, gender,
    potongan}. Naskah asli tidak disentuh — text_tts adalah SALINAN."""
    gdef = proj.get("gender", "male")
    out = []
    for s in proj["segments"]:
        gender = s.get("gender", gdef)
        text = str(s["text"])
        if gender == "male":
            # aturan fonetik miles (owner): spasi TANPA tanda hubung
            tts = " ".join(text.replace("-", " ").split())
            note = "fonetik miles: tanda hubung -> spasi (salinan)"
        else:
            tts = text
            note = "MAI_01: teks asli; dipecah per potongan oleh router"
        clauses = [c for c, _p in vr._split_clauses(tts)]
        out.append({"id": s["id"], "gender": gender, "text_asli": text,
                    "text_tts": tts, "persiapan": note,
                    "potongan": clauses,
                    "scene": {k: s[k] for k in ("kicker", "headline", "body")
                              if k in s}})
    return out


# ---------------------------------------------------------------- tahap 3
def synth_vo(prepared, out_dir):
    """Panggil voice_router --segments per kelompok gender (rute auto
    = default muse-tts). Gabung voice_log ke <out-dir>/voice_log.json.
    Return dict id -> path wav."""
    vo_dir = os.path.join(out_dir, "vo")
    os.makedirs(vo_dir, exist_ok=True)
    groups = {}
    for s in prepared:
        groups.setdefault(s["gender"], []).append(s)
    merged = {"segments": [], "groups": {}}
    wavs = {}
    for gender, segs in groups.items():
        gdir = os.path.join(vo_dir, f"grup-{gender}")
        os.makedirs(gdir, exist_ok=True)
        segfile = os.path.join(gdir, "naskah-grup.json")
        with open(segfile, "w") as f:
            json.dump([{"id": s["id"], "text": s["text_tts"]} for s in segs],
                      f, ensure_ascii=False, indent=1)
        _run([sys.executable, ROUTER, "--segments", segfile,
              "--out-dir", gdir, "--voice", ROUTER_VOICE[gender]],
             "vo")
        logp = os.path.join(gdir, "voice_log.json")
        if not os.path.exists(logp):
            raise StageError("vo", f"voice_log.json tidak dibuat router "
                                   f"untuk grup {gender}")
        glog = json.load(open(logp))
        merged["groups"][gender] = {"fallback": glog.get("fallback"),
                                    "voice_requested":
                                        glog.get("voice_requested")}
        for entry in glog.get("segments", []):
            merged["segments"].append({**entry, "gender": gender})
        for s in segs:
            src = os.path.join(gdir, f"{s['id']}.wav")
            if not os.path.exists(src):
                raise StageError("vo", f"segmen VO hilang sesudah router: "
                                       f"{s['id']}")
            dst = os.path.join(vo_dir, f"{s['id']}.wav")
            if os.path.abspath(src) != os.path.abspath(dst):
                import shutil
                shutil.copyfile(src, dst)
            wavs[s["id"]] = dst
    with open(os.path.join(out_dir, "voice_log.json"), "w") as f:
        json.dump(merged, f, indent=1, ensure_ascii=False)
    return wavs


# ---------------------------------------------------------------- tahap 4
def render(proj, prepared, wavs, out_dir):
    scenes = []
    for s in prepared:
        sc = {"vo": wavs[s["id"]]}
        sc.update(s["scene"])
        scenes.append(sc)
    eng = {"style": proj.get("style", "cinematic"),
           "fps": proj.get("fps", 30),
           "width": proj.get("width", 1080),
           "height": proj.get("height", 1920),
           "no_transitions": True,
           "tmpdir": os.path.join(out_dir, "frames-render"),
           "scenes": scenes}
    if proj.get("bed"):
        eng["bed"] = proj["bed"]
    eng_path = os.path.join(out_dir, "proyek-engine.json")
    with open(eng_path, "w") as f:
        json.dump(eng, f, indent=1, ensure_ascii=False)
    video = os.path.join(out_dir, f"{proj['title']}.mp4")
    _run([sys.executable, RENDER, eng_path, "-o", video], "render",
         timeout=3600)
    if not os.path.exists(video):
        raise StageError("render", f"video final tidak dibuat: {video}")
    return video


# ---------------------------------------------------------------- tahap 5
def qa(proj, prepared, wavs, out_dir, video, merged_log):
    checks = []
    ok = True

    def check(name, passed, detail):
        nonlocal ok
        checks.append({"cek": name, "lulus": bool(passed),
                       "detail": detail})
        ok = ok and bool(passed)

    # voice_log: backend muse-tts + voice terkunci per segmen
    by_id = {e["id"]: e for e in merged_log.get("segments", [])}
    for s in prepared:
        e = by_id.get(s["id"])
        want = f"muse-tts:{LOCKED_VOICE[s['gender']]}"
        check(f"voice_log {s['id']}",
              e is not None and e.get("backend") == "muse-tts"
              and e.get("voice") == want,
              f"backend={e.get('backend') if e else None} "
              f"voice={e.get('voice') if e else None} (target {want})")
    # tidak ada segmen VO hilang + LUFS per segmen
    vo_durs = {}
    for s in prepared:
        p = wavs[s["id"]]
        exists = os.path.exists(p)
        d = _dur(p) if exists else 0.0
        vo_durs[s["id"]] = d
        l = _lufs(p) if exists else float("nan")
        check(f"VO {s['id']} ada + -15 LUFS",
              exists and d >= 0.5 and abs(l - TARGET_VO_LUFS) <= 0.5,
              f"ada={exists} dur={d:.2f}s LUFS={l:.2f}")
    total_vo = sum(vo_durs.values())
    if video:
        w, h, vdur = _probe(video)
        check("resolusi video",
              (w, h) == (proj.get("width", 1080), proj.get("height", 1920)),
              f"{w}x{h}")
        check("durasi video >= total VO - 1,0 dtk",
              vdur >= total_vo - 1.0,
              f"video={vdur:.2f}s total_VO={total_vo:.2f}s")
        final_lufs = _lufs(video)
        check("LUFS final (target -15 +-1,5)",
              abs(final_lufs - TARGET_VO_LUFS) <= 1.5,
              f"{final_lufs:.2f} LUFS")
        # jendela VO per scene (scene mengikuti urutan + durasi VO)
        t = 0.0
        for s in prepared:
            d = vo_durs[s["id"]]
            wl = _lufs_window(video, t + 0.3, max(0.5, d - 0.6))
            check(f"jendela VO scene {s['id']} (-15 +-1)",
                  abs(wl - TARGET_VO_LUFS) <= 1.0, f"{wl:.2f} LUFS")
            t += d
        # rantai bed engine direplikasi persis (atrim+volume+loudnorm -34)
        bed = proj.get("bed")
        if bed:
            tmp = os.path.join(out_dir, "qa-bed-chain.wav")
            _run(["ffmpeg", "-y", "-v", "error", "-stream_loop", "-1",
                  "-i", bed, "-af",
                  f"atrim=0:{vdur:.2f},volume=0.12,"
                  f"loudnorm=I={TARGET_BED_LUFS:g}:TP=-2:LRA=11",
                  tmp], "qa")
            bl = _lufs(tmp)
            check("rantai bed (-34 +-1,5)",
                  abs(bl - TARGET_BED_LUFS) <= 1.5, f"{bl:.2f} LUFS")
        else:
            check("rantai bed (-34 +-1,5)", False,
                  "proyek tanpa bed — mix terkunci tidak terverifikasi")
    report = {"proyek": proj["title"], "lulus": ok,
              "video": video, "cek": checks}
    with open(os.path.join(out_dir, "qa-report.json"), "w") as f:
        json.dump(report, f, indent=1, ensure_ascii=False)
    lines = [f"# Laporan QA — {proj['title']}", "",
             f"Status: **{'LULUS' if ok else 'GAGAL'}**",
             f"Video: `{video}`", "", "| Cek | Hasil | Detail |",
             "|---|---|---|"]
    for c in checks:
        lines.append(f"| {c['cek']} | {'LULUS' if c['lulus'] else 'GAGAL'} "
                     f"| {c['detail']} |")
    with open(os.path.join(out_dir, "qa-report.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    if not ok:
        bad = "; ".join(c["cek"] for c in checks if not c["lulus"])
        raise StageError("qa", f"cek gagal: {bad} "
                               f"(detail: qa-report.md)")
    return report


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(
        description="Pipeline video divisi: proyek JSON -> VO muse-tts "
                    "-> render serial -> QA (lihat docstring).")
    ap.add_argument("--project", required=True, help="file proyek JSON")
    ap.add_argument("--out-dir", required=True, help="folder keluaran")
    ap.add_argument("--dry-run", action="store_true",
                    help="hanya validasi + persiapan + rencana perintah")
    ap.add_argument("--skip-render", action="store_true",
                    help="berhenti sesudah VO (tanpa render/QA video)")
    args = ap.parse_args()

    try:
        if not os.path.exists(args.project):
            raise StageError("validasi",
                             f"file proyek tidak ada: {args.project}")
        proj = json.load(open(args.project))
        title = validate(proj, args.project)
        print(f"[1/5 validasi] OK — proyek '{title}', "
              f"{len(proj['segments'])} segmen")
        prepared = prepare(proj)
        for s in prepared:
            print(f"[2/5 persiapan] {s['id']} ({s['gender']}): "
                  f"{len(s['potongan'])} potongan — {s['persiapan']}")
        if args.dry_run:
            print("[dry-run] rencana perintah:")
            genders = sorted({s['gender'] for s in prepared})
            for g in genders:
                print(f"  python3 {ROUTER} --segments "
                      f"<out>/vo/grup-{g}/naskah-grup.json "
                      f"--out-dir <out>/vo/grup-{g} "
                      f"--voice {ROUTER_VOICE[g]}   # auto = muse-tts")
            print(f"  python3 {RENDER} <out>/proyek-engine.json "
                  f"-o <out>/{title}.mp4")
            print("  QA: ffprobe + LUFS + voice_log (lihat docstring)")
            os.makedirs(args.out_dir, exist_ok=True)
            with open(os.path.join(args.out_dir, "naskah-tts.json"),
                      "w") as f:
                json.dump(prepared, f, indent=1, ensure_ascii=False)
            print(f"[dry-run] naskah-tts.json ditulis ke {args.out_dir} "
                  f"(tanpa eksekusi TTS/render)")
            return
        os.makedirs(args.out_dir, exist_ok=True)
        with open(os.path.join(args.out_dir, "naskah-tts.json"), "w") as f:
            json.dump(prepared, f, indent=1, ensure_ascii=False)
        wavs = synth_vo(prepared, args.out_dir)
        print(f"[3/5 vo] OK — {len(wavs)} segmen via voice_router "
              f"(default muse-tts)")
        merged_log = json.load(open(os.path.join(args.out_dir,
                                                 "voice_log.json")))
        if args.skip_render:
            print("[4/5 render] dilewati (--skip-render); "
                  "[5/5 qa] hanya voice_log diperiksa di laporan parsial")
            rep = {"proyek": title, "lulus": None,
                   "catatan": "skip-render: QA video tidak dijalankan",
                   "voice_log": merged_log}
            with open(os.path.join(args.out_dir, "qa-report.json"),
                      "w") as f:
                json.dump(rep, f, indent=1, ensure_ascii=False)
            return
        video = render(proj, prepared, wavs, args.out_dir)
        print(f"[4/5 render] OK — {video}")
        qa(proj, prepared, wavs, args.out_dir, video, merged_log)
        print(f"[5/5 qa] LULUS — laporan: "
              f"{os.path.join(args.out_dir, 'qa-report.md')}")
        print(f"SELESAI: {video}")
    except StageError as e:
        print(f"[TAHAP {e.stage}] GAGAL: {e.msg}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[TAHAP tak-terduga] GAGAL: {type(e).__name__}: {e}",
              file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
