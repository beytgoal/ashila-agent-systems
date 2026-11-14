#!/usr/bin/env python3
"""video_pipeline_3d.py — pipeline video 3D ujung-ke-ujung Divisi
Branding & Promosi: folder produksi three.js + storyboard.json ->
self-check WebGL -> validasi storyboard -> VO (default terkunci) ->
probe stills -> rekam frame-step -> rakit -> finalize (mix terkunci)
-> master + versi chat + cover -> QA otomatis + laporan.

Dibangun 2026-10-31 atas perintah owner 19:09 WIB ("Bungkus pipeline 3D
jadi satu script juga" + "pasang juga webgl cari resourcenya").
Metode yang dibungkus = skill threejs-storyboard-production (three.js +
storyboard.json, frame-step deterministik; terbukti KisahVerse Ep1 +
Kota Impian Day 1). Pola CLI meniru video_pipeline.py (serial).

Konfigurasi audio TERKUNCI (owner 2026-10-31 18:23/18:47): VO lewat
voice_router rute auto = Muse TTS bawaan Muse (cewek
avocado_v2:MAI_01, cowok avocado_v2:miles), loudnorm segmen -15 LUFS
SEBELUM adelay, bed -34 LUFS, amix=normalize=0, final master ditargetkan
-15 LUFS +-1. (Produksi Ep1/Day 1 lama memakai -16/-38 — riwayat.)

Tahap (gagal di mana pun = berhenti "[TAHAP x] GAGAL: ..." exit 1;
tidak ada tahap yang dilewati diam-diam — yang tidak berlaku dicatat
terbuka di laporan):
  0. SELF-CHECK — chrome 156 + node + playwright-core ada; resource
     WebGL terpin (3d-agent/webgl-resources) hash-nya cocok MANIFEST;
     probe WebGL headless (pipeline-3d/webgl-probe.js): WebGL2
     tersedia + uji gambar nyata lolos. WebGL mati = berhenti.
  1. VALIDASI   — storyboard.json terbaca; varian A (scene/aktor) /
     B (state/shot) dikenali; file state ada bila dirujuk; durasi &
     scenes konsisten; segmen VO + titik mulai terkumpul.
  2. VO         — bila --naskah diberikan: generate per segmen via
     voice_router --segments (rute auto terkunci), voice_log WAJIB
     membuktikan backend muse-tts untuk semua segmen (fallback =
     gagal terbuka). Tanpa --naskah: pakai vo/*.wav proyek yang ada
     (dicatat sebagai pakai-ulang). Proyek tanpa segmen VO = tahap
     dilewati terbuka (template ilustrasi bisu).
  2B. UKUR + RETIME (perbaikan P0 2026-11-01, riset datahub 1297) —
     durasi NYATA tiap segmen VO diukur (ffprobe) dan ditulis ke
     voice_log sebagai dur_measured (syarat QA-A5). Mode generate:
     voSync DIBANGUN ULANG dari durasi terukur — start kumulatif
     dengan jeda antar-segmen 0,35 dtk, durasi shot diskala
     proporsional mengikuti segmennya (kinetic reveal viewer ikut
     dari durasi terukur), duration total = akhir segmen terakhir
     + ekor 0,40 — hasilnya storyboard.resolved.json di folder
     kerja (storyboard asli proyek tidak ditimpa). Ini menegakkan
     aturan skill: durasi VO menentukan timing scene, BUKAN
     sebaliknya. Mode pakai-ulang: voSync dipertahankan (VO = VO
     yang diukur saat storyboard dibuat), pengukuran tetap jalan
     untuk QA. Atempo TIDAK dipakai sebagai mekanisme retime.
  3. PROBE      — stills di waktu kunci tiap scene via bin/probe3.js
     proyek; pageerrors WAJIB kosong.
  4. REKAM      — bin/record_resilient.js (resume-safe) di bawah
     xvfb-run; rentang frame penuh atau --frames a-b (parsial).
     Rentang dipecah ke --recorders recorder paralel pada sub-rentang
     berbeda (bawaan 2; pola produksi Day 1 terbukti) — kecepatan
     SwiftShader +-11 dtk/frame membuat recorder tunggal tidak masuk
     akal untuk episode penuh. Tahap 3 juga membaca window.__detailing
     (detailing-probe.js) agar detailing yang AKTIF — bukan yang
     diminta — yang tercatat di qa-report.
  5. RAKIT      — ffmpeg frame JPG -> video bisu.
  6. FINALIZE   — mix terkunci -> master; versi chat (<=16 MB);
     cover. Rantai amix memakai duration=longest + apad + atrim
     pengunci span (perbaikan P0 2026-11-01: duration=first terbukti
     memotong audio master ke durasi segmen pertama — 17,02 dari
     69,30 dtk pada uji 31 Okt).
  7. QA         — 1080x1920, durasi, LUFS final, diff frame per scene
     > 0, voice_log, stills final disimpan (cek @@NL@@ literal =
     inspeksi visual/OCR bila tersedia) + GERBANG AUDIO QA-A1..A5
     (2026-11-01, riset 1297): A1 durasi stream audio ~= video
     (<=0,30 dtk); A2 loudness tiap jendela segmen >= -40 LUFS dan
     -15 +-6 dB; A3 VO tidak tumpang tindih (dari dur_measured);
     A4 jeda internal segmen maks <=0,35 dan rata-rata <=0,25
     (silencedetect, angka dicatat); A5 voice_log wajib memuat
     dur_measured per segmen. qa-report.json + .md.
  2C. PROFIL + LIP-SYNC (P2 2026-11-01) — --profile master (bawaan)
     menetapkan render.pixelRatio 1,0 pada salinan storyboard kerja
     (buffer benar-benar 1080x1920); draft = 0,75 untuk pratinjau.
     Envelope amplitudo VO (RMS per 40 ms dari berkas VO per segmen)
     disimpan vo/lipsync.json + disuntikkan ke storyboard sebagai
     lipSync; viewer menggerakkan mulut karakter mengikuti amplitudo
     secara deterministik. Gerbang P2 di tahap 7 memverifikasinya.

Teknik utama pipeline (syarat pengunci owner 2026-10-31 19:21 —
"teknik utama jangan dihilangkan") TIDAK dibuang oleh pembungkusan
ini; pemetaan lengkap teknik -> tahap/file/status jujur ada di
3d-agent/webgl-resources/MANIFEST.md ("Tabel pemetaan teknik utama")
+ skill threejs-storyboard-production. Ringkasnya: kritik visual
adversarial = tahap 3 PROBE + tahap 7 QA (render-and-fix); sinkronisasi
audio prosedural = tahap 2 VO + voSync storyboard + tahap 6 FINALIZE;
kode three.js tanpa boilerplate = viewer generik digerakkan
storyboard (konten tidak di-hardcode); sculpting prosedural + injeksi
shader kustom + interpolasi lerp/slerp + blend pose hidup di viewer;
GLTF/GLB + Blender/MCP = tahap preparasi aset DI LUAR render (slot,
bukan tahap script ini); yang belum ada implementasi dicatat apa
adanya di tabel pemetaan, bukan dikarang.

Perbaikan STRUKTUR PIPELINE (2026-11-03, perintah owner 14:10 WIB
"memetakannya seperti 3D seharusnya" — peta lengkap + penilaian per
tahap: 3d-agent/PEMETAAN-PIPELINE-3D.md):
  1B. ASET      — semua referensi GLB di state/storyboard diverifikasi
     (ada = gerbang keras; hilang = gagal terbuka). Sumber > 25 MB
     dengan varian teroptimasi (.opt.glb) di pustaka DISUBSTITUSI
     otomatis ke varian itu (tercatat); --optimize-assets menjalankan
     tools/optimize_glb.py (Blender headless) bila varian belum ada.
  2B+. PAUSE-GATE — jeda internal tiap segmen VO diukur SEBELUM
     dur_measured: jeda internal dipangkas terukur ke cap 0,24 dtk
     (gerbang QA-A4: maks <=0,35, rata-rata <=0,25) dan pelanggaran
     sisa = GAGAL di tahap 2, BUKAN sesudah rekam (cacat run penuh
     2026-11-03: QA-A4 s1+s5 ketahuan sesudah rekam 5.138 dtk).
  2D. KARAKTER  — state menyebut character.source = id di
     3d-agent/characters/registry.json; tahap ini menyelesaikan id ->
     berkas GLB (disalin ke work/assets/karakter) dan menyuntikkan
     character.glb ke state KERJA. Viewer membaca STATE.character.glb
     secara generik — tidak ada lagi path kandidat hardcoded di
     salinan viewer.
  8. FINISHING  — --finishing: Remotion (komposisi KotaFinishing3D)
     terpanggil sebagai tahap akhir dari master run yang sama ->
     <slug>-finishing.mp4.
  PORT OTOMATIS — --port bawaan None: port bebas pertama dari 8931
     dipakai; sesudah server naik, hash storyboard yang terambil
     dibandingkan dengan salinan kerja (server run lain = berhenti).
     Tabrakan port antar-run (3 run hilang, laporan P2 §6.2) ditutup.
  RUN-STATE     — <out-dir>/run-state.json diperbarui di setiap
     transisi tahap (+ progres frame saat rekam); `python3
     video_pipeline_3d.py --status <out-dir>` membacanya. Run yang
     mati (VM replacement) meninggalkan status terakhir yang benar.

Pakai:
  python3 video_pipeline_3d.py --project <folder|storyboard.json> \
      --out-dir <folder> [--naskah naskah.json] [--dry-run] \
      [--skip-record] [--frames 0-149] [--finishing] \
      [--optimize-assets] [--port N]
  python3 video_pipeline_3d.py --status <out-dir>

Folder produksi ASLI tidak pernah ditulis — semua kerja di salinan
<out-dir>/work/. Perekam yang dipakai selalu jalur JPG resilient
(API viewer sama untuk varian A/B).
"""
import argparse, hashlib, json, os, re, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROUTER = os.path.join(HERE, "voice_router.py")
HOME = os.path.expanduser("~")
CHROME = os.path.join(HOME, ".cache/ms-playwright/chromium-1248/"
                           "chrome-linux64/chrome")
NODE_MODULES = os.path.join(HOME, "workspace/scratch/3d-agent/node_modules")
WEBGL_RES = os.path.join(HOME, "workspace/divisi/branding-promosi/"
                              "3d-agent/webgl-resources")
WEBGL_PROBE_DIR = os.path.join(HOME, "workspace/divisi/branding-promosi/"
                                    "pipeline-3d")
BASIS_BIN = os.path.join(HOME, "workspace/divisi/branding-promosi/"
                              "kotaimpian/produksi-day1/bin")
TARGET_VO_LUFS = -15.0
TARGET_BED_LUFS = -34.0
TARGET_FINAL_LUFS = -15.0
FINAL_TOL = 1.0
# Tahap 2B (P0, riset 1297): jeda antar-segmen saat voSync dibangun
# ulang dari durasi VO terukur + ekor sesudah segmen terakhir.
RETIME_GAP = 0.35
RETIME_TAIL = 0.40
# Perbaikan struktur 2026-11-03: gerbang jeda internal QA-A4 ditegakkan
# di tahap audio — jeda internal segmen dipangkas ke cap ini (gerbang:
# maks <=0,35, rata-rata <=0,25; cap 0,24 memberi margin keduanya).
PAUSE_CAP = 0.24
PAUSE_MAX = 0.35
PAUSE_MEAN = 0.25
# Tahap 1B: GLB di atas ukuran ini dianggap belum teroptimasi.
ASSET_MAX_MB = 25.0
AGENT3D = os.path.join(HOME, "workspace/divisi/branding-promosi/3d-agent")
CHAR_REGISTRY = os.path.join(AGENT3D, "characters", "registry.json")
ASSET_LIBRARY = os.path.join(AGENT3D, "aset-sketchfab", "bangunan-kota")
OPTIMIZE_GLB = os.path.join(AGENT3D, "tools", "optimize_glb.py")
BLENDER_HEADLESS = os.path.join(AGENT3D, "tools", "blender",
                                "blender-headless")
REMOTION_DIR = os.path.join(HOME, "workspace/scratch/anim2d/remotion")
FINISHING_COMP = "KotaFinishing3D"
FINISHING_INPUT_NAME = "kota-glb-segmen.mp4"

# ------------------------------------------------------------ run-state
# Berkas state run (<out-dir>/run-state.json): ditulis di setiap
# transisi tahap agar status run bisa DITANYA dari luar kapan pun
# (menutup cacat peta §6: run mati karena VM replacement tidak
# meninggalkan status yang bisa dibaca).
_RUN_STATE = {"path": None, "data": None}


def _state_init(out_dir, args_dict):
    _RUN_STATE["path"] = os.path.join(out_dir, "run-state.json")
    _RUN_STATE["data"] = {
        "tool": "video_pipeline_3d.py", "run_id":
        time.strftime("%Y%m%d-%H%M%S") + f"-{os.getpid()}",
        "pid": os.getpid(), "status": "running", "stage": None,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "args": args_dict, "stages": {}, "frames": None, "error": None}
    _state_write()


def _state_write():
    if not _RUN_STATE["path"]:
        return
    _RUN_STATE["data"]["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    tmp = _RUN_STATE["path"] + ".tmp"
    try:
        json.dump(_RUN_STATE["data"], open(tmp, "w"),
                  ensure_ascii=False, indent=1, default=str)
        os.replace(tmp, _RUN_STATE["path"])
    except Exception:
        pass  # state tidak boleh membunuh run


def _state_stage(name, status, **extra):
    d = _RUN_STATE["data"]
    if d is None:
        return
    st = d["stages"].setdefault(name, {})
    if status == "running":
        st["started_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        d["stage"] = name
    else:
        st["ended_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    st["status"] = status
    st.update(extra)
    _state_write()


def _state_finish(status, **extra):
    d = _RUN_STATE["data"]
    if d is None:
        return
    d["status"] = status
    d["stage"] = None
    d.update(extra)
    _state_write()


class StageError(Exception):
    def __init__(self, stage, msg):
        super().__init__(msg)
        self.stage = stage
        self.msg = msg


def _run(cmd, stage, env=None, timeout=None, cwd=None):
    e = dict(os.environ)
    if env:
        e.update(env)
    p = subprocess.run(cmd, capture_output=True, text=True, env=e,
                       timeout=timeout, cwd=cwd)
    if p.returncode != 0:
        tail = ((p.stderr or "") + (p.stdout or ""))[-600:]
        raise StageError(stage, f"perintah gagal (rc={p.returncode}): "
                                f"{' '.join(cmd[:3])}... — {tail}")
    return p


def _lufs(path, target=None):
    af = "loudnorm=print_format=json"
    if target is not None:
        af = f"loudnorm=I={target:g}:TP=-1.5:LRA=11:print_format=json"
    p = subprocess.run(["ffmpeg", "-i", path, "-af", af, "-f", "null", "-"],
                       capture_output=True, text=True)
    s = p.stderr
    return float(json.loads(s[s.rfind("{"):s.rfind("}") + 1])["input_i"])


def _loudnorm_to(src, dst, target):
    """Dua pass loudnorm ke target LUFS (dipakai SEBELUM adelay)."""
    p = subprocess.run(["ffmpeg", "-i", src, "-af",
                        f"loudnorm=I={target:g}:TP=-1.5:LRA=11:"
                        "print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    s = p.stderr
    d = json.loads(s[s.rfind("{"):s.rfind("}") + 1])
    af = (f"loudnorm=I={target:g}:TP=-1.5:LRA=11:"
          f"measured_I={d['input_i']}:measured_TP={d['input_tp']}:"
          f"measured_LRA={d['input_lra']}:"
          f"measured_thresh={d['input_thresh']}:"
          f"offset={d['target_offset']}:linear=true")
    _run(["ffmpeg", "-y", "-v", "error", "-i", src, "-af", af,
          "-ar", "48000", dst], 6)


def _probe_file(path):
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


def _probe_av_durations(path):
    """(durasi stream video, durasi stream audio|None) via ffprobe —
    dasar QA-A1 (bug 31 Okt: audio master hanya 17,02 dari 69,30 dtk
    lolos karena tidak ada yang membandingkan dua angka ini)."""
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "stream=codec_type,duration", "-of", "json",
                        path], capture_output=True, text=True)
    vd = ad = None
    for st in json.loads(p.stdout).get("streams", []):
        if st.get("duration") is None:
            continue
        if st["codec_type"] == "video" and vd is None:
            vd = float(st["duration"])
        elif st["codec_type"] == "audio" and ad is None:
            ad = float(st["duration"])
    return vd, ad


def _slice_lufs(path, start, dur):
    """Integrated loudness (LUFS) potongan [start, start+dur) sebuah
    file — dasar QA-A2. -inf bila potongan hampa; None bila gagal
    ukur."""
    p = subprocess.run(["ffmpeg", "-hide_banner", "-ss", f"{start:.3f}",
                        "-t", f"{dur:.3f}", "-i", path, "-vn", "-af",
                        "loudnorm=print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    s = p.stderr
    try:
        return float(json.loads(
            s[s.rfind("{"):s.rfind("}") + 1])["input_i"])
    except Exception:
        return None


def _silences(path):
    """Daftar (start, durasi) hening >=0,12 dtk pada ambang -40 dB
    (silencedetect) — dasar QA-A4."""
    p = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af",
                        "silencedetect=noise=-40dB:d=0.12", "-f",
                        "null", "-"], capture_output=True, text=True)
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)",
                                           p.stderr)]
    durs = [float(x) for x in re.findall(r"silence_duration: ([\d.]+)",
                                         p.stderr)]
    return list(zip(starts, durs))


def _pause_stats(path):
    """Statistik jeda INTERNAL sebuah wav dengan definisi yang sama
    persis dengan QA-A4 tahap 7 (hening -40 dB; tepi 0,05 dtk di kedua
    ujung tidak dihitung). Mengembalikan dict {count, max, mean,
    total}."""
    sdur = _dur(path)
    internal = [d for s0, d in _silences(path)
                if s0 > 0.05 and s0 + d < sdur - 0.05]
    return {"count": len(internal),
            "max": round(max(internal), 3) if internal else 0.0,
            "mean": round(sum(internal) / len(internal), 3)
                    if internal else 0.0,
            "total": round(sum(internal), 3)}


def _cap_internal_pauses(path, cap=PAUSE_CAP):
    """Pangkas jeda internal wav ke <= cap detik (perbaikan struktur
    2026-11-03: QA-A4 ditegakkan di tahap audio, bukan sesudah rekam).

    Rentang simpan dibangun dari daftar hening yang sama dengan yang
    dinilai QA-A4; tiap jeda internal disisakan `cap` detik dari awal
    heningnya, sisanya dibuang. Tepi berkas tidak disentuh. Berkas
    ditulis ulang hanya bila ada yang dipangkas; mengembalikan total
    detik yang dibuang (0.0 bila bersih). Pemotongan pada batas hening
    (-40 dB) tidak menimbulkan klik yang terdengar pada jeda wicara.
    """
    sdur = _dur(path)
    sils = [(s0, d) for s0, d in _silences(path)
            if s0 > 0.05 and s0 + d < sdur - 0.05 and d > cap]
    if not sils:
        return 0.0
    keeps, cur = [], 0.0
    removed = 0.0
    for s0, d in sils:
        keeps.append((cur, s0 + cap))
        cur = s0 + d
        removed += d - cap
    keeps.append((cur, sdur))
    keeps = [(a, b) for a, b in keeps if b - a > 0.005]
    n = len(keeps)
    parts, labels = [], []
    if n == 1:
        fc = (f"[0:a]atrim={keeps[0][0]:.3f}:{keeps[0][1]:.3f},"
              "asetpts=PTS-STARTPTS[out]")
    else:
        fc = f"[0:a]asplit={n}" + "".join(f"[s{i}]" for i in range(n))
        for i, (a, b) in enumerate(keeps):
            fc += (f";[s{i}]atrim={a:.3f}:{b:.3f},"
                   f"asetpts=PTS-STARTPTS[k{i}]")
            labels.append(f"[k{i}]")
        fc += ";" + "".join(labels) + f"concat=n={n}:v=0:a=1[out]"
    tmp = path + ".cap.wav"
    _run(["ffmpeg", "-y", "-v", "error", "-i", path, "-filter_complex",
          fc, "-map", "[out]", tmp], 2)
    os.replace(tmp, path)
    return round(removed, 3)


def _pick_port(preferred):
    """Port server run: bila diminta eksplisit, port itu WAJIB bebas
    (sibuk = berhenti terbuka — jangan diam-diam pindah). Bila tidak
    diminta, port bebas pertama mulai dari 8931 dipakai. Menutup
    tabrakan port antar-run (laporan P2 §6.2)."""
    import socket
    def free(p):
        s = socket.socket()
        try:
            s.bind(("127.0.0.1", p))
            return True
        except OSError:
            return False
        finally:
            s.close()
    if preferred:
        if not free(preferred):
            raise StageError(0, f"port {preferred} sudah dipakai proses "
                                "lain — berhenti agar tidak merender "
                                "halaman run lain; pilih --port lain")
        return preferred
    for cand in range(8931, 8990):
        if free(cand):
            return cand
    raise StageError(0, "tidak ada port bebas di 8931-8989")


# ---------------------------------------------------------------- tahap 0
def stage0_selfcheck(report):
    info = {}
    if not os.path.exists(CHROME):
        raise StageError(0, f"Chrome for Testing 156 tidak ada: {CHROME}")
    info["chrome"] = CHROME
    if shutil.which("node") is None:
        raise StageError(0, "node tidak ada di PATH")
    if not os.path.isdir(os.path.join(NODE_MODULES, "playwright-core")):
        raise StageError(0, f"playwright-core tidak ada: {NODE_MODULES}")
    # resource WebGL terpin: file + hash cocok MANIFEST.md
    manifest = os.path.join(WEBGL_RES, "MANIFEST.md")
    if not os.path.exists(manifest):
        raise StageError(0, f"MANIFEST resource WebGL tidak ada: {manifest}")
    mtxt = open(manifest).read()
    files = ["three.module.js", "three.core.js",
             "addons/loaders/GLTFLoader.js",
             "addons/utils/BufferGeometryUtils.js",
             "addons/utils/SkeletonUtils.js",
             "addons/environments/RoomEnvironment.js"]
    hashes = {}
    for rel in files:
        p = os.path.join(WEBGL_RES, rel)
        if not os.path.exists(p):
            raise StageError(0, f"resource WebGL hilang: {p}")
        h = hashlib.sha256(open(p, "rb").read()).hexdigest()
        if h not in mtxt:
            raise StageError(0, f"hash {rel} tidak cocok MANIFEST: {h}")
        hashes[rel] = h
    info["webgl_resources"] = hashes
    # probe WebGL nyata
    probe_js = os.path.join(WEBGL_PROBE_DIR, "webgl-probe.js")
    if not os.path.exists(probe_js):
        raise StageError(0, f"skrip probe WebGL tidak ada: {probe_js}")
    p = _run(["xvfb-run", "-a", "node", probe_js], 0,
             env={"NODE_PATH": NODE_MODULES}, timeout=180)
    probe = json.loads(p.stdout[p.stdout.find("{"):])
    w2 = probe.get("webgl2", {})
    if not w2.get("available"):
        raise StageError(0, "WebGL2 TIDAK tersedia di chrome render — "
                            "render akan kosong; berhenti.")
    if not w2.get("drawOk"):
        raise StageError(0, "WebGL2 tersedia tapi uji gambar nyata GAGAL "
                            "(readPixels tidak sesuai) — berhenti.")
    info["webgl2"] = {"version": w2.get("version"),
                      "renderer": w2.get("unmaskedRenderer"),
                      "maxTextureSize": w2.get("maxTextureSize"),
                      "drawOk": True}
    report["selfcheck"] = info
    return info


# ---------------------------------------------------------------- tahap 1
def resolve_project(project_arg):
    if os.path.isdir(project_arg):
        proj = os.path.abspath(project_arg)
        sb_path = os.path.join(proj, "storyboard.json")
    else:
        sb_path = os.path.abspath(project_arg)
        proj = os.path.dirname(sb_path)
    if not os.path.exists(sb_path):
        raise StageError(1, f"storyboard.json tidak ada: {sb_path}")
    return proj, sb_path


def stage1_validate(proj, sb_path, report):
    try:
        sb = json.load(open(sb_path))
    except Exception as e:
        raise StageError(1, f"storyboard.json tidak terbaca: {e}")
    duration = float(sb.get("duration") or 0)
    if duration <= 0:
        raise StageError(1, "storyboard.duration tidak ada / <= 0")
    fps = int(sb.get("fps") or 30)
    scenes = sb.get("scenes") or []
    if not scenes:
        raise StageError(1, "storyboard.scenes kosong")
    variant = None
    segments = {}   # id -> {start, dur}
    windows = []    # (label, start, end)
    if "voSync" in sb or "cityState" in sb:
        variant = "B"
        if "cityState" in sb:
            st = sb["cityState"]
            st_path = st if os.path.isabs(st) else os.path.join(proj, st)
            if not os.path.exists(st_path):
                raise StageError(1, f"file state dirujuk tapi tidak ada: "
                                    f"{st_path}")
        t = 0.0
        for sc in scenes:
            sdur = sum(float(sh.get("dur") or 0) for sh in sc.get("shots", []))
            windows.append((f"scene {sc.get('id')}", t, t + sdur))
            t += sdur
        for sid, sv in (sb.get("voSync", {}).get("segments") or {}).items():
            segments[sid] = {"start": float(sv["start"]),
                             "dur": float(sv["dur"])}
    elif "cast" in sb or "sets" in sb:
        variant = "A"
        t = 0.0
        for sc in scenes:
            sdur = float(sc.get("dur") or 0)
            windows.append((f"scene {sc.get('id')}", t, t + sdur))
            if sc.get("vo"):
                segments[sc["vo"]] = {"start": t, "dur": sdur}
            t += sdur
    else:
        raise StageError(1, "varian storyboard tidak dikenali (bukan A "
                            "scene/aktor, bukan B state/shot)")
    total_scene = windows[-1][2] if windows else 0
    if abs(total_scene - duration) > 1.0:
        raise StageError(1, f"durasi scenes ({total_scene:.2f}) != "
                            f"storyboard.duration ({duration:.2f})")
    # validasi isi shot (perbaikan struktur 2026-11-03): camKeys kamera
    # keyframe + opsi render baru divalidasi di sini, bukan ditemukan
    # sebagai frame aneh sesudah rekam.
    for sc in scenes:
        for sh in sc.get("shots", []) + ([sc] if variant == "A" else []):
            keys = sh.get("camKeys")
            if keys is None:
                continue
            if not isinstance(keys, list) or len(keys) < 2:
                raise StageError(1, "camKeys harus daftar >= 2 kunci")
            last_t = -1.0
            for k in keys:
                t = k.get("t")
                if not isinstance(t, (int, float)) \
                        or not (0.0 <= t <= 1.0) or t <= last_t:
                    raise StageError(1, "camKeys: t harus naik ketat "
                                        "dalam [0,1]")
                last_t = t
                tgt = k.get("target")
                if not (isinstance(tgt, list) and len(tgt) == 3):
                    raise StageError(1, "camKeys: target harus [x,y,z]")
                for f in ("az", "el", "dist"):
                    if not isinstance(k.get(f), (int, float)):
                        raise StageError(1, f"camKeys: {f} harus angka")
    rnd = sb.get("render") or {}
    if rnd.get("environment") not in (None, "pmrem"):
        raise StageError(1, "render.environment tidak dikenal: "
                            f"{rnd.get('environment')} (pilihan: pmrem)")
    taps = (rnd.get("dof") or {}).get("taps")
    if taps is not None and taps not in (12, 24, 32):
        raise StageError(1, f"render.dof.taps harus 12/24/32: {taps}")
    info = {"variant": variant, "duration": duration, "fps": fps,
            "scenes": len(scenes), "segments": segments,
            "windows": windows}
    report["storyboard"] = {k: v for k, v in info.items() if k != "windows"}
    report["detailing"] = sb.get("detailing") or {"note": "storyboard "
                                                   "tanpa config "
                                                   "detailing — semua "
                                                   "penghalusan mati "
                                                   "(perilaku lama)"}
    return info


# --------------------------------------------------------------- tahap 1B
def _work_state_path(work):
    """Path file state di SALINAN kerja (varian B), atau None."""
    sbp = os.path.join(work, "storyboard.json")
    if not os.path.exists(sbp):
        return None
    sb = json.load(open(sbp))
    st = sb.get("cityState")
    if not st:
        return None
    return st if os.path.isabs(st) else os.path.join(work, st)


def _resolve_viewer_url(work, url):
    """URL aset di storyboard/state relatif terhadap viewer/ (halaman
    yang memuatnya). Kembalikan path absolut di salinan kerja."""
    p = os.path.normpath(os.path.join(work, "viewer", url))
    return p


def stage1b_assets(work, proj, optimize, report):
    """TAHAP 1B ASET (perbaikan struktur 2026-11-03, peta butir 4).

    Memindai semua referensi GLB di state kerja (buildings kind glb):
    berkas HARUS ada (hilang dicoba disalin dari folder proyek asli;
    tetap hilang = gagal terbuka sebelum render mahal). Ukuran
    dicatat; sumber > ASSET_MAX_MB dengan varian teroptimasi
    (<nama>.opt.glb di folder yang sama atau pustaka aset divisi)
    DISUBSTITUSI otomatis — state kerja ditulis ulang menunjuk varian
    itu. --optimize-assets: varian belum ada -> optimize_glb.py
    (Blender headless lokal) dijalankan menghasilkan .opt.glb di
    folder aset salinan kerja.
    """
    st_path = _work_state_path(work)
    if not st_path or not os.path.exists(st_path):
        report["assets"] = {"note": "tanpa file state — tidak ada "
                                    "referensi GLB untuk diverifikasi"}
        return
    state = json.load(open(st_path))
    entries, changed = [], False
    for b in state.get("buildings", []):
        if b.get("kind") != "glb":
            continue
        url = b.get("url")
        if not url:
            raise StageError(1, f"aset: bangunan glb {b.get('id')} "
                                "tanpa url")
        p = _resolve_viewer_url(work, url)
        if not os.path.exists(p):
            src = _resolve_viewer_url(proj, url)
            if os.path.exists(src):
                os.makedirs(os.path.dirname(p), exist_ok=True)
                shutil.copy(src, p)
            else:
                raise StageError(1, f"aset: GLB dirujuk state tapi "
                                    f"tidak ada: {url}")
        size_mb = os.path.getsize(p) / 1e6
        ent = {"id": b.get("id"), "url": url,
               "size_mb": round(size_mb, 2), "action": "as-is"}
        if size_mb > ASSET_MAX_MB:
            base = os.path.basename(p)
            opt_name = base[:-4] + ".opt.glb" if base.endswith(".glb") \
                else base + ".opt.glb"
            cands = [os.path.join(os.path.dirname(p), opt_name),
                     os.path.join(ASSET_LIBRARY, "optimized", opt_name),
                     os.path.join(ASSET_LIBRARY, opt_name)]
            opt = next((c for c in cands if os.path.exists(c)), None)
            if opt is None and optimize:
                out_opt = os.path.join(os.path.dirname(p), opt_name)
                _run([BLENDER_HEADLESS, "--background", "--python",
                      OPTIMIZE_GLB, "--", p, out_opt], 1, timeout=3600)
                if os.path.exists(out_opt):
                    opt = out_opt
                    ent["optimized_now"] = True
            if opt is not None:
                if os.path.abspath(opt) != os.path.abspath(p):
                    os.makedirs(os.path.dirname(p), exist_ok=True)
                    shutil.copy(opt, os.path.join(os.path.dirname(p),
                                                  opt_name))
                new_url = os.path.join(os.path.dirname(url),
                                       opt_name).replace(os.sep, "/")
                b["url"] = new_url
                changed = True
                ent.update({"action": "substitusi-opt",
                            "url_new": new_url,
                            "size_mb_new": round(os.path.getsize(
                                os.path.join(os.path.dirname(p),
                                             opt_name)) / 1e6, 2)})
            else:
                ent["action"] = "PERINGATAN: besar tanpa varian opt"
        entries.append(ent)
    if changed:
        json.dump(state, open(st_path, "w"), ensure_ascii=False,
                  indent=1)
    report["assets"] = {"glb": entries,
                        "max_mb_gate": ASSET_MAX_MB,
                        "optimize_flag": bool(optimize)}
    for e in entries:
        print(f"[TAHAP 1B] aset {e['id']}: {e['size_mb']} MB -> "
              f"{e['action']}", flush=True)


# --------------------------------------------------------------- tahap 2D
def stage2d_character(work, proj, report):
    """TAHAP 2D KARAKTER (perbaikan struktur 2026-11-03, peta butir 5).

    State kerja menyebut character.source = id di registry karakter
    divisi (3d-agent/characters/registry.json). Tahap ini:
    - prosedural: mencatat desain resmi yang dipakai (tanpa suntikan).
    - glb: menyalin berkas GLB registry ke work/assets/karakter/ dan
      menyuntikkan character.glb {url, clip, mouthNode, height,
      faceFill} ke state KERJA — viewer membacanya secara generik.
    State yang sudah memuat character.glb.url secara manual
    diverifikasi keberadaan berkasnya (disalin dari proyek bila ada).
    Folder proyek asli tidak pernah ditulis.
    """
    st_path = _work_state_path(work)
    if not st_path or not os.path.exists(st_path):
        report["character"] = {"note": "tanpa file state — tahap "
                                       "karakter tidak berlaku"}
        return
    state = json.load(open(st_path))
    ch = state.get("character") or {}
    info = {"id": ch.get("id"), "design": ch.get("design")}
    src_id = ch.get("source")
    if src_id:
        if not os.path.exists(CHAR_REGISTRY):
            raise StageError(2, f"registry karakter tidak ada: "
                                f"{CHAR_REGISTRY}")
        reg = json.load(open(CHAR_REGISTRY)).get("characters", {})
        ent = reg.get(src_id)
        if ent is None:
            raise StageError(2, f"character.source '{src_id}' tidak "
                                "ada di registry karakter")
        info.update({"source": src_id, "type": ent.get("type"),
                     "status": ent.get("status")})
        if ent.get("type") == "glb":
            asset = ent.get("asset")
            src = asset if os.path.isabs(asset) else os.path.join(
                AGENT3D, asset)
            if not os.path.exists(src):
                raise StageError(2, f"berkas karakter registry hilang: "
                                    f"{src}")
            dst_dir = os.path.join(work, "assets", "karakter")
            os.makedirs(dst_dir, exist_ok=True)
            dst = os.path.join(dst_dir, os.path.basename(src))
            if not os.path.exists(dst):
                shutil.copy(src, dst)
            glb = {"url": "../assets/karakter/" +
                          os.path.basename(src),
                   "clip": ent.get("clip", "talk"),
                   "mouthNode": ent.get("mouthNode", "MULUT"),
                   "height": ent.get("height", 1.68),
                   "faceFill": bool(ent.get("faceFill", False))}
            for k, v in (ch.get("glb") or {}).items():
                glb[k] = v  # state boleh menimpa bawaan registry
            ch["glb"] = glb
            state["character"] = ch
            json.dump(state, open(st_path, "w"), ensure_ascii=False,
                      indent=1)
            info["glb"] = glb
            info["size_mb"] = round(os.path.getsize(dst) / 1e6, 2)
    elif (ch.get("glb") or {}).get("url"):
        url = ch["glb"]["url"]
        p = _resolve_viewer_url(work, url)
        if not os.path.exists(p):
            src = _resolve_viewer_url(proj, url)
            if os.path.exists(src):
                os.makedirs(os.path.dirname(p), exist_ok=True)
                shutil.copy(src, p)
            else:
                raise StageError(2, f"character.glb dirujuk state tapi "
                                    f"tidak ada: {url}")
        info.update({"type": "glb", "glb": ch["glb"],
                     "note": "character.glb manual di state — "
                             "terverifikasi ada"})
    else:
        info["type"] = "procedural"
    report["character"] = info
    print(f"[TAHAP 2D] karakter: {info.get('source') or info.get('id')}"
          f" ({info.get('type')})", flush=True)


# ---------------------------------------------------------------- tahap 2
def stage2_vo(proj, out_dir, naskah_arg, sbinfo, report):
    segs = sbinfo["segments"]
    work_vo = os.path.join(out_dir, "work", "vo")
    os.makedirs(work_vo, exist_ok=True)
    if not segs:
        report["vo"] = {"mode": "tanpa-vo",
                        "note": "storyboard tanpa segmen VO — tahap "
                                "dilewati terbuka (template ilustrasi)"}
        return {"segments": {}, "bed": None, "mode": "tanpa-vo"}
    bed = None
    for cand_dir in [os.path.join(proj, "vo"), proj]:
        if os.path.isdir(cand_dir):
            for f in sorted(os.listdir(cand_dir)):
                if f.startswith("bed") and f.rsplit(".", 1)[-1] in (
                        "wav", "mp3", "m4a"):
                    bed = os.path.join(cand_dir, f)
                    break
        if bed:
            break
    if naskah_arg:
        raw = json.load(open(naskah_arg))
        items = raw["segments"] if isinstance(raw, dict) else raw
        by_gender = {}
        for it in items:
            if it["id"] in segs:
                by_gender.setdefault(it.get("gender", "male"),
                                     []).append(it)
        if not by_gender:
            raise StageError(2, "naskah tidak memuat satu pun segmen "
                                "storyboard")
        gen_dir = os.path.join(out_dir, "vo-gen")
        os.makedirs(gen_dir, exist_ok=True)
        merged_log = []
        for gender, group in by_gender.items():
            sub = os.path.join(gen_dir, gender)
            os.makedirs(sub, exist_ok=True)
            nf = os.path.join(sub, "naskah.json")
            json.dump(group, open(nf, "w"), ensure_ascii=False)
            voice = "female" if gender == "female" else "default"
            _run([sys.executable, ROUTER, "--segments", nf,
                  "--voice", voice, "--out-dir", sub], 2, timeout=1800)
            log = json.load(open(os.path.join(sub, "voice_log.json")))
            merged_log.extend(log if isinstance(log, list)
                              else log.get("segments", []))
            for it in group:
                src = os.path.join(sub, it["id"] + ".wav")
                if not os.path.exists(src):
                    raise StageError(2, f"VO segmen {it['id']} tidak "
                                        "terbentuk di router")
                shutil.copy(src, os.path.join(work_vo, it["id"] + ".wav"))
        bad = [e for e in merged_log if e.get("backend") != "muse-tts"]
        if bad:
            raise StageError(2, "voice_log membuktikan fallback (BUKAN "
                                "muse-tts) untuk: " +
                             ", ".join(str(e.get("id")) for e in bad) +
                             " — gagal terbuka sesuai kuncian")
        json.dump(merged_log, open(os.path.join(work_vo, "voice_log.json"),
                                   "w"), ensure_ascii=False, indent=1)
        report["vo"] = {"mode": "generate-muse-tts",
                        "segments": [e.get("id") for e in merged_log],
                        "bed": bed}
        return {"segments": segs, "bed": bed, "mode": "generate"}
    # tanpa naskah: pakai ulang VO proyek
    missing = [sid for sid in segs
               if not os.path.exists(os.path.join(proj, "vo", sid + ".wav"))]
    if missing:
        raise StageError(2, "tanpa --naskah dan VO proyek tidak lengkap; "
                            "segmen hilang: " + ", ".join(missing))
    for sid in segs:
        shutil.copy(os.path.join(proj, "vo", sid + ".wav"),
                    os.path.join(work_vo, sid + ".wav"))
    log_src = os.path.join(proj, "vo", "voice_log.json")
    if os.path.exists(log_src):
        shutil.copy(log_src, os.path.join(work_vo, "voice_log.json"))
    report["vo"] = {"mode": "pakai-ulang-proyek",
                    "note": "VO dari folder proyek dipakai apa adanya "
                            "(voice_log proyek dipertahankan); berikan "
                            "--naskah untuk generate ulang default "
                            "terkunci",
                    "segments": list(segs), "bed": bed}
    return {"segments": segs, "bed": bed, "mode": "reuse"}


# --------------------------------------------------------------- tahap 2B
def stage2b_retime(work, sbinfo, vo, report):
    """UKUR durasi nyata tiap segmen VO + (mode generate) RETIME.

    Pengukuran selalu jalan (semua mode ber-VO): ffprobe tiap
    work/vo/s{n}.wav -> dur_measured ditulis ke voice_log.json
    (QA-A5 membacanya dari sana; tanpa dur_measured QA gagal).

    Mode generate: voSync dibangun ulang dari durasi terukur —
    start kumulatif (GAP 0,35 antar-segmen, ekor 0,40), durasi
    scene = durasi segmennya + gap/ekor, shot di dalam scene
    diskala dengan rasio yang sama (field vo shot ikut diskala —
    kinetic reveal viewer dihitung dari angka terukur ini, P1-2
    riset), storyboard hasil ditulis ke work/storyboard.resolved.json
    dan work/storyboard.json folder KERJA diarahkan ke isinya
    (viewer membaca storyboard.json; storyboard ASLI proyek tidak
    pernah ditimpa). sbinfo + vo["segments"] diperbarui di tempat
    supaya tahap 3-7 memakai timing resolved. Mode pakai-ulang:
    voSync dipertahankan — VO-nya memang VO yang diukur saat
    storyboard dibuat; retime akan menggeser produksi lama yang
    sudah terbukti tanpa alasan.
    """
    if vo["mode"] == "tanpa-vo" or not vo["segments"]:
        report["retime"] = {"applied": False,
                            "note": "tanpa segmen VO — tidak berlaku"}
        return
    work_vo = os.path.join(work, "vo")
    # --- PAUSE-GATE (perbaikan struktur 2026-11-03, peta butir 1) ---
    # Jeda internal tiap segmen ditegakkan DI SINI, sebelum dur_measured
    # dan sebelum render: mode generate -> jeda internal dipangkas ke
    # PAUSE_CAP lalu diverifikasi; sisa pelanggaran = GAGAL tahap 2.
    # Akar: jeda prosodi internal TTS tidak bisa dipaksa router (riset
    # 1297: 0,52-0,55 dtk di koma), dan memeriksanya di tahap 7 berarti
    # membayar satu rekam penuh (run 2026-11-03: QA-A4 s1+s5 gagal
    # sesudah rekam 5.138 dtk). Mode pakai-ulang: VO tidak diubah
    # (voSync storyboard dibangun dari VO itu) — hanya diukur dan
    # dicatat; QA-A4 tahap 7 tetap hakimnya untuk mode itu.
    pause_gate = {}
    for sid in vo["segments"]:
        p = os.path.join(work_vo, sid + ".wav")
        if not os.path.exists(p):
            raise StageError(2, f"pause-gate: file VO segmen hilang: {p}")
        before = _pause_stats(p)
        ent = {"before": before, "trimmed_s": 0.0}
        if vo["mode"] == "generate":
            ent["trimmed_s"] = _cap_internal_pauses(p)
            after = _pause_stats(p)
            ent["after"] = after
            if after["max"] > PAUSE_MAX or after["mean"] > PAUSE_MEAN:
                raise StageError(
                    2, f"pause-gate: segmen {sid} masih melanggar "
                       f"QA-A4 sesudah pemangkasan (maks "
                       f"{after['max']:.3f} > {PAUSE_MAX}, rata2 "
                       f"{after['mean']:.3f} > {PAUSE_MEAN}) — berhenti "
                       "di tahap audio, bukan sesudah rekam")
        else:
            ent["action"] = "diukur-saja (mode pakai-ulang)"
        pause_gate[sid] = ent
        print(f"[TAHAP 2B] pause-gate {sid}: jeda maks "
              f"{before['max']:.3f}/rata2 {before['mean']:.3f}"
              + (f" -> dipangkas {ent['trimmed_s']:.3f} dtk, sesudah "
                 f"maks {ent['after']['max']:.3f}/rata2 "
                 f"{ent['after']['mean']:.3f}"
                 if vo["mode"] == "generate" else ""), flush=True)
    report["pause_gate"] = pause_gate
    measured = {}
    for sid in vo["segments"]:
        p = os.path.join(work_vo, sid + ".wav")
        if not os.path.exists(p):
            raise StageError(2, f"retime: file VO segmen hilang: {p}")
        measured[sid] = round(_dur(p), 3)
    vo["dur_measured"] = measured
    # tulis dur_measured ke voice_log (bentuk list / dict dipertahankan)
    log_path = os.path.join(work_vo, "voice_log.json")
    log, entries = None, []
    if os.path.exists(log_path):
        log = json.load(open(log_path))
        entries = log if isinstance(log, list) \
            else log.get("segments", [])
    by_id = {e.get("id"): e for e in entries if isinstance(e, dict)}
    for sid, d in measured.items():
        if sid in by_id:
            by_id[sid]["dur_measured"] = d
        else:
            e = {"id": sid, "backend": "tidak-tercatat",
                 "dur_measured": d}
            entries.append(e)
            by_id[sid] = e
    if isinstance(log, dict):
        log["segments"] = entries
        json.dump(log, open(log_path, "w"), ensure_ascii=False, indent=1)
    else:
        json.dump(entries, open(log_path, "w"), ensure_ascii=False,
                  indent=1)
    if vo["mode"] != "generate":
        report["retime"] = {
            "applied": False, "mode": vo["mode"],
            "dur_measured": measured,
            "note": "mode pakai-ulang: durasi diukur untuk QA-A3/A5; "
                    "voSync storyboard dipertahankan apa adanya"}
        return
    sb_path = os.path.join(work, "storyboard.json")
    sb = json.load(open(sb_path))
    scenes = sb.get("scenes") or []
    pairs = []
    for sc in scenes:
        sid = sc.get("vo")
        if sid and sid in measured:
            pairs.append((sc, sid))
    if not (len(pairs) == len(scenes) == len(measured)):
        raise StageError(
            2, f"retime: pemetaan scene<->segmen tidak 1:1 "
               f"(scene {len(scenes)}, ber-VO {len(pairs)}, segmen "
               f"terukur {len(measured)}) — tidak aman menebak "
               f"timing; perbaiki storyboard/naskah")
    order = [sid for _sc, sid in pairs]
    starts, t = {}, 0.0
    for i, sid in enumerate(order):
        starts[sid] = round(t, 3)
        t += measured[sid] + (RETIME_TAIL if i == len(order) - 1
                              else RETIME_GAP)
    new_duration = round(t, 3)
    windows, t = [], 0.0
    for i, (sc, sid) in enumerate(pairs):
        scene_new = measured[sid] + (RETIME_TAIL if i == len(pairs) - 1
                                     else RETIME_GAP)
        if sbinfo["variant"] == "B":
            shots = sc.get("shots") or []
            old = sum(float(sh.get("dur") or 0) for sh in shots)
            if old <= 0:
                raise StageError(2, f"retime: scene {sc.get('id')} "
                                    "total durasi shot <= 0")
            ratio = scene_new / old
            acc = 0.0
            for j, sh in enumerate(shots):
                if j < len(shots) - 1:
                    nd = round(float(sh.get("dur") or 0) * ratio, 3)
                else:
                    nd = round(scene_new - acc, 3)  # serap sisa bulat
                sh["dur"] = nd
                if isinstance(sh.get("vo"), (int, float)):
                    sh["vo"] = round(float(sh["vo"]) * ratio, 3)
                acc += nd
        else:  # varian A: dur scene langsung
            sc["dur"] = round(scene_new, 3)
        windows.append((f"scene {sc.get('id')}", round(t, 3),
                        round(t + scene_new, 3)))
        t += scene_new
    old_duration = sbinfo["duration"]
    sb["duration"] = new_duration
    if isinstance(sb.get("voSync"), dict):
        vs = sb["voSync"].setdefault("segments", {})
        for sid in order:
            vs[sid] = {"start": starts[sid], "dur": measured[sid]}
    resolved = os.path.join(work, "storyboard.resolved.json")
    json.dump(sb, open(resolved, "w"), ensure_ascii=False, indent=1)
    shutil.copy(resolved, sb_path)  # viewer folder kerja baca resolved
    for sid in order:
        vo["segments"][sid]["start"] = starts[sid]
        vo["segments"][sid]["dur"] = measured[sid]
    sbinfo["duration"] = new_duration
    sbinfo["windows"] = windows
    report["retime"] = {"applied": True, "gap": RETIME_GAP,
                        "tail": RETIME_TAIL, "dur_measured": measured,
                        "starts": starts,
                        "duration_old": old_duration,
                        "duration_new": new_duration,
                        "resolved": resolved}


# ------------------------------------------------------------ kerja salinan
HEAVY = ("frames", "frames3", "qa", "qa3", "project")
def make_work_copy(proj, out_dir):
    work = os.path.join(out_dir, "work")
    if os.path.exists(work):
        shutil.rmtree(work)

    def ignore(d, names):
        skip = []
        for n in names:
            full = os.path.join(d, n)
            if n in HEAVY and os.path.isdir(full):
                skip.append(n)
            elif n.endswith((".mp4", ".log")) and os.path.isfile(full):
                skip.append(n)
        return skip

    shutil.copytree(proj, work, ignore=ignore)
    # pasang resource WebGL detailing dari folder terpin: addon yang belum
    # ada di vendor proyek disalin dari webgl-resources (file proyek yang
    # sudah ada TIDAK ditimpa)
    src_addons = os.path.join(WEBGL_RES, "addons")
    dst_addons = os.path.join(work, "viewer", "vendor", "addons")
    synced = []
    if os.path.isdir(src_addons):
        for root, _dirs, names in os.walk(src_addons):
            for n in names:
                rel = os.path.relpath(os.path.join(root, n), src_addons)
                dst = os.path.join(dst_addons, rel)
                if not os.path.exists(dst):
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy(os.path.join(root, n), dst)
                    synced.append(rel)
    make_work_copy.synced = synced
    return work


def serve(work, port):
    """Server HTTP salinan kerja + VERIFIKASI IDENTITAS (perbaikan
    struktur 2026-11-03): storyboard yang terambil dari server harus
    identik byte-per-byte dengan storyboard salinan kerja — bila beda,
    yang menjawab adalah server run lain di port yang sama (tabrakan
    port laporan P2 §6.2) dan run berhenti terbuka, bukan merender
    halaman proyek lain diam-diam."""
    import hashlib as _hl
    import urllib.request
    proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--bind",
         "127.0.0.1"], cwd=work, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{port}/viewer/index.html"
    want = _hl.sha256(open(os.path.join(work, "storyboard.json"),
                           "rb").read()).hexdigest()
    got = None
    for _ in range(50):
        try:
            body = urllib.request.urlopen(
                f"http://127.0.0.1:{port}/storyboard.json",
                timeout=2).read()
            got = _hl.sha256(body).hexdigest()
            break
        except Exception:
            time.sleep(0.2)
    if got != want:
        proc.terminate()
        raise StageError(3, "identitas server tidak cocok: storyboard "
                            "dari port ini bukan salinan kerja run ini "
                            "(server run lain?) — berhenti")
    return proc, url


def bin_of(work, name):
    p = os.path.join(work, "bin", name)
    if os.path.exists(p):
        return p
    p2 = os.path.join(BASIS_BIN, name)
    if os.path.exists(p2):
        return p2
    raise StageError(3, f"bin/{name} tidak ada di proyek maupun basis")


def stage2c_profile_lipsync(work, vo, profile, report):
    """2C PROFIL RENDER + LIP-SYNC amplitudo (P2, 2026-11-01).

    Profil: paksa render.pixelRatio di SALINAN storyboard (work) —
    master = 1.0 (buffer benar-benar 1080x1920), draft = 0.75
    (pratinjau cepat). Folder proyek asli tidak pernah ditulis.

    Lip-sync: envelope RMS per 40 ms dari berkas VO mentah per segmen
    (work/vo/<sid>.wav), dinormalisasi ke persentil-98 global,
    dilicinkan rerata geser 3, disimpan sebagai data terukur
    vo/lipsync.json DAN disuntikkan ke storyboard work sebagai
    `lipSync`. Viewer membaca SB.lipSync + SB.voSync dan menggerakkan
    mulut mengikuti amplitudo pada waktu t (deterministik).
    """
    import numpy as np
    pr = 1.0 if profile == "master" else 0.75
    sb_paths = [os.path.join(work, n) for n in
                ("storyboard.resolved.json", "storyboard.json")]
    for p in sb_paths:
        if not os.path.exists(p):
            continue
        sb = json.load(open(p))
        sb.setdefault("render", {})["pixelRatio"] = pr
        json.dump(sb, open(p, "w"), ensure_ascii=False, indent=1)
    report["profile"] = {"name": profile, "pixelRatio": pr}
    print(f"[2C] profil render {profile}: pixelRatio {pr}", flush=True)
    segs = (vo or {}).get("segments") or {}
    if not segs:
        return
    hop, rate = 0.04, 8000
    hop_n = int(hop * rate)
    raw = {}
    for sid in sorted(segs):
        wav = os.path.join(work, "vo", f"{sid}.wav")
        if not os.path.exists(wav):
            continue
        pcm = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", wav, "-ac", "1", "-ar",
             str(rate), "-f", "s16le", "-"], capture_output=True).stdout
        x = np.frombuffer(pcm, dtype=np.int16).astype(np.float64) / 32768.0
        n = max(1, int(np.ceil(len(x) / hop_n)))
        rms = np.zeros(n)
        for i in range(n):
            segx = x[i * hop_n:(i + 1) * hop_n]
            if len(segx):
                rms[i] = float(np.sqrt(np.mean(segx ** 2)))
        raw[sid] = rms
    if not raw:
        return
    allv = np.concatenate(list(raw.values()))
    nz = allv[allv > 0]
    ref = float(np.percentile(nz, 98)) if len(nz) else 0.0
    env, summary = {}, {}
    for sid, rms in raw.items():
        if ref > 0:
            amp = np.clip(rms / ref, 0.0, 1.0) ** 0.75
        else:
            amp = np.zeros_like(rms)
        amp = np.convolve(np.pad(amp, (1, 1), mode="edge"),
                          np.ones(3) / 3.0, mode="valid")
        amp[amp < 0.03] = 0.0
        vals = [round(float(v), 3) for v in amp]
        env[sid] = vals
        summary[sid] = {"samples": len(vals),
                        "max": round(float(max(vals)), 3),
                        "mean": round(float(np.mean(vals)), 3)}
    json.dump({"hop": hop, "ref_rms": round(ref, 5), "segments": env},
              open(os.path.join(work, "vo", "lipsync.json"), "w"),
              ensure_ascii=False, indent=1)
    for p in sb_paths:
        if not os.path.exists(p):
            continue
        sb = json.load(open(p))
        sb["lipSync"] = {"hop": hop, "segments": env}
        json.dump(sb, open(p, "w"), ensure_ascii=False, indent=1)
    report["lipsync"] = {"hop": hop, "segments": summary}
    print(f"[2C] lip-sync: envelope {len(env)} segmen, hop {hop} dtk, "
          f"ref RMS {ref:.4f}", flush=True)


# ---------------------------------------------------------------- tahap 3
def stage3_probe(work, out_dir, sbinfo, port, report):
    probe = bin_of(work, "probe3.js")
    times = []
    for label, a, b in sbinfo["windows"]:
        for t in (a + 0.5, (a + b) / 2.0):
            if t < sbinfo["duration"] - 0.1:
                times.append(round(t, 2))
    times = sorted(set(times))
    if not times:
        raise StageError(3, "tidak ada waktu probe yang sah")
    srv, url = serve(work, port)
    try:
        p = _run(["xvfb-run", "-a", "node", probe, url,
                  os.path.join(out_dir, "probe")] +
                 [str(t) for t in times], 3,
                 env={"NODE_PATH": NODE_MODULES}, timeout=900)
        # detailing yang BENAR-BENAR aktif di viewer (window.__detailing),
        # bukan sekadar config yang diminta storyboard — viewer boleh
        # menurunkan smaa->fxaa bila DOF hidup; yang aktif yang tercatat.
        det = {"detailing": None, "note": "viewer tanpa __detailing "
                                          "(viewer produksi lama)"}
        det_js = os.path.join(WEBGL_PROBE_DIR, "detailing-probe.js")
        if os.path.exists(det_js):
            dp = _run(["xvfb-run", "-a", "node", det_js, url], 3,
                      env={"NODE_PATH": NODE_MODULES}, timeout=300)
            det = json.loads(dp.stdout[dp.stdout.find("{"):])
            if det.get("errors"):
                raise StageError(3, "detailing-probe pageerrors: "
                                    f"{det['errors']}")
    finally:
        srv.terminate()
    m = re.search(r"pageerrors:\s*(\[.*\])", p.stdout)
    errs = json.loads(m.group(1)) if m else ["<tidak terbaca>"]
    if errs:
        raise StageError(3, f"pageerrors TIDAK kosong: {errs}")
    report["probe"] = {"times": times, "pageerrors": [],
                       "stills": os.path.join(out_dir, "probe")}
    report["detailing_active"] = det.get("detailing")
    return times


# ---------------------------------------------------------------- tahap 4
def stage4_record(work, out_dir, sbinfo, frames_arg, skip_record, port,
                  report, recorders=2):
    t0_rec = time.time()
    fps = sbinfo["fps"]
    # total frame = FLOOR, menyamai semantik recorder/viewer
    # (record_resilient: total = min(END, floor(__duration*fps))).
    # round() pernah mengancam off-by-one: storyboard Day 1 = 69,32 dtk
    # -> round 2080 frame, padahal yang bisa dirender 2079 (0..2078).
    total = int(sbinfo["duration"] * fps)
    if frames_arg:
        a, b = frames_arg.split("-", 1)
        start, end = int(a), int(b)
        partial = True
    else:
        start, end, partial = 0, total - 1, False
    frames_dir = os.path.join(out_dir, "frames")
    os.makedirs(frames_dir, exist_ok=True)
    if skip_record:
        src = None
        for cand in ("frames3", "frames"):
            d = os.path.join(work, cand)
            if os.path.isdir(d) and os.listdir(d):
                src = d
                break
        if src is None:
            # salinan kerja membuang folder frame; cek proyek asli di work
            raise StageError(4, "--skip-record tapi tidak ada folder "
                                "frames di salinan kerja — jalankan tanpa "
                                "--skip-record, atau sertakan frames di "
                                "folder proyek (frames3/frames tidak disalin "
                                "ke work demi ukuran; salin manual ke "
                                "<out>/frames)")
        for f in os.listdir(src):
            shutil.copy(os.path.join(src, f), os.path.join(frames_dir, f))
    else:
        rec = bin_of(work, "record_resilient.js")
        srv, url = serve(work, port)
        try:
            # PERHATIAN semantik recorder: argumen END record_resilient.js
            # adalah CAP EKSKLUSIF (total = min(END, floor(duration*fps)),
            # render START..total-1) — rentang script ini inklusif,
            # jadi yang dikirim end+1. (Bug off-by-one tertangkap uji
            # 31 Okt 2026: --frames 0-149 menghasilkan 0..148.)
            # Rentang dipecah ke beberapa recorder PARALEL pada sub-rentang
            # BERBEDA (pola produksi Day 1 yang terbukti; recorder
            # resume-safe, nama file per nomor frame jadi aman berbagi
            # folder). Kecepatan terukur SwiftShader+detailing di VM ini
            # +-11 dtk/frame — satu recorder untuk episode penuh 2.080
            # frame = +-6,5 jam, makanya paralel adalah bawaan, bukan opsi
            # eksotik. Log per chunk: record-chunk<i>.log di out-dir.
            total_frames = end - start + 1
            n = max(1, min(int(recorders), total_frames))
            bounds, step = [], -(-total_frames // n)
            for i in range(n):
                a = start + i * step
                if a > end:
                    break
                bounds.append((a, min(end, a + step - 1)))
            env = dict(os.environ)
            env["NODE_PATH"] = NODE_MODULES
            procs = []
            for i, (a, b) in enumerate(bounds):
                lf = open(os.path.join(out_dir,
                                       f"record-chunk{i}.log"), "ab")
                procs.append((i, a, b, lf, subprocess.Popen(
                    ["xvfb-run", "-a", "node", rec, url, frames_dir,
                     str(fps), str(a), str(b + 1)],
                    stdout=lf, stderr=subprocess.STDOUT, env=env)))
            chunk_frames = max(b - a + 1 for a, b in bounds)
            deadline = time.time() + max(7200, chunk_frames * 25 + 900)
            # Loop polling (perbaikan struktur 2026-11-03): progres
            # frame ditulis ke run-state.json berkala agar run panjang
            # bisa DITANYA statusnya dari luar selagi berjalan.
            failed = []
            pending = list(procs)
            while pending:
                if time.time() > deadline:
                    for i, a, b, lf, p in pending:
                        p.kill()
                        lf.close()
                        failed.append(f"chunk{i} ({a}-{b}) rc=timeout")
                    break
                done_n = sum(1 for i2 in range(start, end + 1)
                             if os.path.exists(os.path.join(
                                 frames_dir, f"f{i2:05d}.jpg")))
                if _RUN_STATE["data"] is not None:
                    _RUN_STATE["data"]["frames"] = {
                        "done": done_n, "total": end - start + 1,
                        "range": [start, end]}
                    _state_write()
                still = []
                for i, a, b, lf, p in pending:
                    rc = p.poll()
                    if rc is None:
                        still.append((i, a, b, lf, p))
                    else:
                        lf.close()
                        if rc != 0:
                            failed.append(f"chunk{i} ({a}-{b}) rc={rc}")
                pending = still
                if pending:
                    time.sleep(15)
            if failed:
                raise StageError(4, "recorder paralel gagal: " +
                                 "; ".join(failed) + " — frame yang "
                                 "sudah jadi dipertahankan; jalankan ulang "
                                 "script untuk melanjutkan (resume-safe)")
            report["record_chunks"] = [
                {"chunk": i, "start": a, "end": b} for i, (a, b)
                in enumerate(bounds)]
        finally:
            srv.terminate()
    missing = [i for i in range(start, end + 1)
               if not os.path.exists(os.path.join(
                   frames_dir, f"f{i:05d}.jpg"))]
    if missing:
        raise StageError(4, f"{len(missing)} frame hilang dari rentang "
                            f"{start}-{end} (pertama: {missing[:5]})")
    info = {"start": start, "end": end, "count": end - start + 1,
            "partial": partial, "fps": fps,
            "elapsed_s": round(time.time() - t0_rec, 1)}
    report["record"] = info
    return info


# ---------------------------------------------------------------- tahap 5
def stage5_assemble(out_dir, rec, report):
    silent = os.path.join(out_dir, "video-silent.mp4")
    _run(["ffmpeg", "-y", "-v", "error", "-framerate", str(rec["fps"]),
          "-start_number", str(rec["start"]), "-i",
          os.path.join(out_dir, "frames", "f%05d.jpg"),
          "-frames:v", str(rec["count"]), "-c:v", "libx264",
          "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p",
          silent], 5)
    report["assemble"] = {"silent": silent, "dur": _dur(silent)}
    return silent


# ---------------------------------------------------------------- tahap 6
def stage6_finalize(out_dir, silent, vo, rec, slug, report):
    span = rec["count"] / rec["fps"]
    master = os.path.join(out_dir, slug + ".mp4")
    if vo["mode"] == "tanpa-vo":
        shutil.copy(silent, master)
        report["finalize"] = {"master": master, "audio": "tanpa VO "
                              "(master bisu — dicatat terbuka)"}
        lufs = None
    else:
        work_vo = os.path.join(out_dir, "work", "vo")
        mix_dir = os.path.join(out_dir, "mix")
        os.makedirs(mix_dir, exist_ok=True)
        inputs = ["-i", silent]
        fc, labels = [], []
        idx = 1
        for sid in sorted(vo["segments"],
                          key=lambda s: vo["segments"][s]["start"]):
            st = vo["segments"][sid]["start"]
            if st >= span:
                continue
            raw = os.path.join(work_vo, sid + ".wav")
            norm = os.path.join(mix_dir, sid + "_norm.wav")
            _loudnorm_to(raw, norm, TARGET_VO_LUFS)  # SEBELUM adelay
            inputs += ["-i", norm]
            ms = int(st * 1000)
            # atrim ke ujung jendela segmen sesudah adelay = pengaman
            # tumpang tindih (dengan retime 2B jendela memang pas;
            # ini jaring pengaman, bukan mekanisme timing)
            wend = min(span, st + float(
                vo["segments"][sid].get("dur") or span))
            fc.append(f"[{idx}:a]adelay={ms}|{ms},"
                      f"atrim=0:{wend:.3f}[v{idx}]")
            labels.append(f"[v{idx}]")
            idx += 1
        if vo.get("bed"):
            bed_norm = os.path.join(mix_dir, "bed_norm.wav")
            _loudnorm_to(vo["bed"], bed_norm, TARGET_BED_LUFS)
            inputs += ["-stream_loop", "-1", "-i", bed_norm]
            fc.append(f"[{idx}:a]atrim=0:{span:.2f}[bed]")
            labels.append("[bed]")
        # duration=longest + apad + atrim pengunci span (perbaikan P0
        # 2026-11-01, riset 1297): duration=first memotong keluaran
        # amix ke durasi input pertama (= segmen s1) — audio master
        # uji 31 Okt hanya 17,02 dari 69,30 dtk. Reproduksi
        # filtergraph riset: first -> 3,000 dtk; longest -> 12,000.
        fc.append("".join(labels) +
                  f"amix=inputs={len(labels)}:normalize=0:"
                  "duration=longest[mix]")
        fc.append(f"[mix]apad=whole_dur={span:.3f},"
                  f"atrim=0:{span:.3f}[aout]")
        _run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex",
              ";".join(fc), "-map", "0:v", "-map", "[aout]", "-c:v", "copy",
              "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
              "-t", f"{span:.2f}", master], 6)
        lufs = _lufs(master)
        for _ in range(2):
            if abs(lufs - TARGET_FINAL_LUFS) <= FINAL_TOL:
                break
            g = max(-3.0, min(3.0, TARGET_FINAL_LUFS - lufs))
            tmp = master + ".fix.mp4"
            _run(["ffmpeg", "-y", "-v", "error", "-i", master, "-af",
                  f"volume={g:.2f}dB", "-c:v", "copy", "-c:a", "aac",
                  "-b:a", "160k", tmp], 6)
            os.replace(tmp, master)
            lufs = _lufs(master)
        report["finalize"] = {"master": master, "lufs": lufs,
                              "vo_target": TARGET_VO_LUFS,
                              "bed_target": TARGET_BED_LUFS}
    # versi chat <=16 MB + cover
    chat = os.path.join(out_dir, slug + "-chat.mp4")
    _run(["ffmpeg", "-y", "-v", "error", "-i", master, "-vf",
          "scale=720:1280", "-c:v", "libx264", "-preset", "medium",
          "-b:v", "1500k", "-maxrate", "1500k", "-bufsize", "3000k",
          "-c:a", "aac", "-b:a", "96k", chat], 6)
    if os.path.getsize(chat) > 16e6:
        _run(["ffmpeg", "-y", "-v", "error", "-i", master, "-vf",
              "scale=720:1280", "-c:v", "libx264", "-preset", "medium",
              "-b:v", "1100k", "-maxrate", "1100k", "-bufsize", "2200k",
              "-c:a", "aac", "-b:a", "96k", chat], 6)
    cover = os.path.join(out_dir, slug + "-cover.jpg")
    _run(["ffmpeg", "-y", "-v", "error", "-ss",
          f"{min(3.0, span / 2):.2f}", "-i", master, "-frames:v", "1",
          "-q:v", "3", cover], 6)
    report["finalize"].update({"chat": chat,
                               "chat_mb": os.path.getsize(chat) / 1e6,
                               "cover": cover})
    return master, lufs


# ---------------------------------------------------------------- tahap 7
def stage7_qa(out_dir, master, lufs, sbinfo, rec, vo, slug, report):
    checks = []

    def check(name, passed, detail):
        # passed tri-state: True/False dinilai; None = TIDAK DIUJI
        # (alat/syarat tidak ada) — dicatat terbuka, BUKAN kegagalan.
        # (Bug tertangkap uji 31 Okt 2026: bool(None)=False membuat cek
        # OCR tanpa tesseract menggagalkan QA yang sebenarnya lulus.)
        checks.append({"name": name,
                       "pass": None if passed is None else bool(passed),
                       "detail": detail})

    w, h, dur = _probe_file(master)
    check("resolusi 1080x1920", (w, h) == (1080, 1920), f"{w}x{h}")
    span = rec["count"] / rec["fps"]
    exp = span if rec["partial"] else sbinfo["duration"]
    check("durasi ~= target (±0,5)", abs(dur - exp) <= 0.5,
          f"master {dur:.2f} vs target {exp:.2f}")
    if vo["mode"] == "tanpa-vo":
        check("LUFS final (target -15 ±1)", None,
              "tidak berlaku — proyek tanpa VO")
    else:
        check("LUFS final (target -15 ±1)",
              lufs is not None and abs(lufs + 15.0) <= FINAL_TOL,
              f"{lufs:.2f} LUFS")
    # diff gerak per scene dari frame rekaman (t vs t+1 dtk)
    try:
        import numpy as np
        from PIL import Image
        frames_dir = os.path.join(out_dir, "frames")

        def load(i):
            return np.asarray(Image.open(os.path.join(
                frames_dir, f"f{i:05d}.jpg")).convert("RGB"),
                dtype=np.int16)

        for label, a, b in sbinfo["windows"]:
            i0 = int(a * rec["fps"]) + rec["start"]
            i1 = i0 + rec["fps"]
            if i1 > rec["end"]:
                check(f"gerak {label}", None,
                      "di luar rentang rekaman parsial — tidak diuji")
                continue
            d = float(np.abs(load(i0) - load(i1)).mean())
            check(f"gerak {label}", d > 0.05, f"mean abs diff {d:.3f}")
    except ImportError as e:
        check("gerak per scene", False, f"numpy/PIL tidak ada: {e}")
    if vo["mode"] == "generate":
        log = json.load(open(os.path.join(out_dir, "work", "vo",
                                          "voice_log.json")))
        entries = log if isinstance(log, list) else log.get("segments", [])
        ok = all(e.get("backend") == "muse-tts" for e in entries)
        check("voice_log muse-tts semua segmen", ok,
              f"{len(entries)} segmen")
    elif vo["mode"] == "reuse":
        check("voice_log muse-tts semua segmen", None,
              "pakai-ulang VO proyek — log lama dipertahankan, tidak "
              "dinilai sebagai muse-tts")
    # ---- gerbang audio QA-A1..A5 (2026-11-01, riset datahub 1297) ----
    # Menutup lubang QA 31 Okt: master audio terpotong 17,02/69,30 dtk
    # lolos karena tidak ada cek durasi stream / bunyi per jendela /
    # tumpang tindih / jeda. Semua angka, semua tertulis di laporan.
    if vo["mode"] != "tanpa-vo":
        vdur_a, adur_a = _probe_av_durations(master)
        check("QA-A1 durasi stream audio ~= video (selisih <=0,30)",
              adur_a is not None and vdur_a is not None
              and abs(adur_a - vdur_a) <= 0.30,
              f"audio {adur_a} vs video {vdur_a}")
        logp = os.path.join(out_dir, "work", "vo", "voice_log.json")
        meas = {}
        if os.path.exists(logp):
            lg = json.load(open(logp))
            for e in (lg if isinstance(lg, list)
                      else lg.get("segments", [])):
                if isinstance(e, dict) and e.get("dur_measured") \
                        is not None:
                    meas[e.get("id")] = float(e["dur_measured"])
        seg_ids = list(vo["segments"])
        check("QA-A5 voice_log memuat dur_measured semua segmen",
              all(s in meas for s in seg_ids),
              f"terukur: { {s: meas.get(s) for s in seg_ids} }")
        ordered = sorted(vo["segments"].items(),
                         key=lambda kv: kv[1]["start"])
        if all(s in meas for s in seg_ids):
            viol = []
            for i, (sid, sv) in enumerate(ordered):
                end = sv["start"] + meas[sid]
                lim = (ordered[i + 1][1]["start"]
                       if i + 1 < len(ordered)
                       else sbinfo["duration"]) + 0.05
                if end > lim:
                    viol.append(f"{sid} berakhir {end:.2f} > "
                                f"batas {lim:.2f}")
            check("QA-A3 VO tidak tumpang tindih (dur_measured)",
                  not viol, "; ".join(viol) if viol else
                  "semua segmen muat di jendelanya (tol 0,05)")
        else:
            check("QA-A3 VO tidak tumpang tindih (dur_measured)",
                  False, "dur_measured tidak lengkap — lihat QA-A5")
        for sid, sv in ordered:
            wlen = meas.get(sid, sv["dur"])
            li = _slice_lufs(master, sv["start"], wlen)
            check(f"QA-A2 bunyi jendela {sid} (-15 ±6, >= -40 LUFS)",
                  li is not None and li >= -40.0
                  and abs(li + 15.0) <= 6.0,
                  f"irisan {sv['start']:.2f}.."
                  f"{sv['start'] + wlen:.2f} = {li} LUFS")
        work_vo = os.path.join(out_dir, "work", "vo")
        for sid, _sv in ordered:
            wav = os.path.join(work_vo, sid + ".wav")
            sdur = meas.get(sid) or _dur(wav)
            internal = [d for s0, d in _silences(wav)
                        if s0 > 0.05 and s0 + d < sdur - 0.05]
            longest = max(internal) if internal else 0.0
            mean = (sum(internal) / len(internal)) if internal else 0.0
            check(f"QA-A4 jeda internal {sid} "
                  "(maks <=0,35; rata2 <=0,25)",
                  longest <= 0.35 and mean <= 0.25,
                  f"maks {longest:.3f}, rata2 {mean:.3f}, "
                  f"{len(internal)} jeda, total "
                  f"{sum(internal):.2f} dtk")
    # gerbang P2: profil render + lip-sync benar-benar diterapkan
    prof = report.get("profile") or {}
    try:
        wpr = json.load(open(os.path.join(
            out_dir, "work", "storyboard.json")))["render"]["pixelRatio"]
    except Exception:
        wpr = None
    check(f"P2 profil render ({prof.get('name')}) diterapkan",
          (wpr is not None and prof.get("pixelRatio") is not None
           and abs(float(wpr) - float(prof["pixelRatio"])) < 1e-9),
          f"pixelRatio storyboard work={wpr}; profil={prof}")
    lip = report.get("lipsync") or {}
    if vo.get("segments"):
        lip_segs = lip.get("segments") or {}
        check("P2 lipSync envelope semua segmen VO",
              all(sid in lip_segs and lip_segs[sid]["samples"] > 0
                  for sid in vo["segments"]),
              f"{len(lip_segs)} segmen, hop {lip.get('hop')} dtk")
    # stills final + cek @@NL@@
    still_dir = os.path.join(out_dir, "qa-final")
    os.makedirs(still_dir, exist_ok=True)
    for name, t in (("awal", 0.3), ("tengah", dur / 2),
                    ("akhir", max(0.3, dur - 0.4))):
        _run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i",
              master, "-frames:v", "1", "-q:v", "3",
              os.path.join(still_dir, name + ".jpg")], 7)
    ocr = shutil.which("tesseract")
    if ocr:
        found = []
        for f in os.listdir(still_dir):
            p = subprocess.run([ocr, os.path.join(still_dir, f), "stdout"],
                               capture_output=True, text=True)
            if "@@" in p.stdout or "NL@@" in p.stdout:
                found.append(f)
        check("tidak ada @@NL@@ literal (OCR)", not found,
              f"stills bersih" if not found else f"di: {found}")
    else:
        check("tidak ada @@NL@@ literal (OCR)", None,
              "tesseract tidak ada — stills final disimpan di qa-final/ "
              "untuk inspeksi visual; tidak diklaim lolos OCR")
    hard = [c for c in checks if c["pass"] is False]
    report["qa"] = {"checks": checks,
                    "passed": sum(1 for c in checks if c["pass"] is True),
                    "failed": [c["name"] for c in hard]}
    # tulis laporan
    json.dump(report, open(os.path.join(out_dir, "qa-report.json"), "w"),
              ensure_ascii=False, indent=1, default=str)
    lines = [f"# QA — video_pipeline_3d ({slug})", ""]
    for c in checks:
        mark = {True: "✅", False: "❌", None: "➖"}[c["pass"]]
        lines.append(f"- {mark} **{c['name']}** — {c['detail']}")
    lines += ["", f"Profil render (P2): "
              f"{json.dumps(report.get('profile'), ensure_ascii=False)}",
              f"Lip-sync (P2): "
              f"{json.dumps(report.get('lipsync'), ensure_ascii=False)}"]
    lines += ["", f"Master: `{master}`",
              f"Mode VO: {vo['mode']} · Rekaman parsial: {rec['partial']}",
              f"Detailing config storyboard: "
              f"{json.dumps(report.get('detailing'), ensure_ascii=False)}",
              f"Detailing AKTIF di viewer (__detailing terbaca probe): "
              f"{json.dumps(report.get('detailing_active'), ensure_ascii=False)}"]
    open(os.path.join(out_dir, "qa-report.md"), "w").write(
        "\n".join(lines) + "\n")
    if hard:
        raise StageError(7, "QA gagal: " + "; ".join(c["name"]
                                                     for c in hard))
    return checks


# ---------------------------------------------------------------- tahap 8
def stage8_finishing(out_dir, master, slug, report):
    """TAHAP 8 FINISHING (perbaikan struktur 2026-11-03, peta butir 6).

    Lapisan finishing Remotion sebagai tahap pipeline yang terpanggil,
    bukan pekerjaan tangan: master run ini disalin ke public/ proyek
    Remotion dengan nama yang diharapkan komposisi (KotaFinishing3D
    membaca staticFile("kota-glb-segmen.mp4")), lalu render.mjs
    dijalankan (COMP=KotaFinishing3D, chrome wrapper lokal proyek).
    Komposisi yang ada adalah kartu judul kinetik + grade + grain +
    vignette di atas 4 detik footage (120 frame @30, playbackRate 0,5
    -> memakai 2 detik awal master) — cakupan itu dicatat apa adanya.
    Master sendiri tidak diubah; keluaran: <slug>-finishing.mp4.
    """
    if not os.path.isdir(REMOTION_DIR):
        raise StageError(8, f"proyek Remotion tidak ada: {REMOTION_DIR}")
    public_in = os.path.join(REMOTION_DIR, "public",
                             FINISHING_INPUT_NAME)
    os.makedirs(os.path.dirname(public_in), exist_ok=True)
    shutil.copy(master, public_in)
    out = os.path.join(out_dir, slug + "-finishing.mp4")
    env = {"COMP": FINISHING_COMP}
    _run(["node", "render.mjs", "video", out], 8, env=env,
         timeout=2400, cwd=REMOTION_DIR)
    report["finishing"] = {"master": out,
                            "composition": FINISHING_COMP,
                            "input_copied_to": public_in,
                            "size_mb": round(os.path.getsize(out) / 1e6,
                                             2),
                            "note": "kartu judul + grade/grain/vignette "
                                    "atas footage master (komposisi "
                                    "prototipe yang ada, 120 frame)"}
    return out


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(
        description="Pipeline video 3D (three.js + storyboard.json)")
    ap.add_argument("--project",
                    help="folder produksi atau file storyboard.json")
    ap.add_argument("--out-dir", help="folder keluaran")
    ap.add_argument("--status",
                    help="baca run-state.json (+ qa-report) folder "
                         "hasil ini dan cetak status run — tanpa "
                         "menjalankan pipeline")
    ap.add_argument("--naskah", help="JSON segmen [{id,text,gender?}] "
                                     "untuk generate VO default terkunci")
    ap.add_argument("--dry-run", action="store_true",
                    help="hanya self-check + validasi + rencana")
    ap.add_argument("--skip-record", action="store_true",
                    help="pakai frame yang sudah ada di <out-dir>/frames")
    ap.add_argument("--frames", help="rentang frame parsial, mis. 0-149")
    ap.add_argument("--profile", choices=["master", "draft"],
                    default="master",
                    help="profil resolusi render (P2): master pixelRatio "
                         "1.0 buffer penuh 1080x1920 (bawaan, hasil "
                         "akhir); draft 0.75 pratinjau cepat")
    ap.add_argument("--recorders", type=int, default=2,
                    help="jumlah recorder paralel tahap 4 (sub-rentang "
                         "berbeda, pola produksi terbukti; bawaan 2)")
    ap.add_argument("--port", type=int, default=None,
                    help="port server salinan kerja; bawaan: port "
                         "bebas pertama dari 8931 dipilih otomatis "
                         "(perbaikan 2026-11-03 — tabrakan port "
                         "antar-run ditutup; port eksplisit yang sibuk "
                         "= berhenti terbuka)")
    ap.add_argument("--finishing", action="store_true",
                    help="tahap 8: panggil Remotion (KotaFinishing3D) "
                         "sesudah QA -> <slug>-finishing.mp4")
    ap.add_argument("--optimize-assets", action="store_true",
                    help="tahap 1B: GLB besar tanpa varian .opt.glb "
                         "dioptimasi via Blender headless "
                         "(optimize_glb.py)")
    args = ap.parse_args()

    if args.status:
        sp = os.path.join(os.path.abspath(args.status),
                          "run-state.json")
        if not os.path.exists(sp):
            print(f"STATUS: tidak ada run-state.json di {args.status} "
                  "— run belum pernah dimulai (atau out-dir salah)")
            return 1
        st = json.load(open(sp))
        print(f"STATUS run {st.get('run_id')}: {st.get('status')}"
              f" · tahap: {st.get('stage')}"
              f" · mulai: {st.get('started_at')}"
              f" · diperbarui: {st.get('updated_at')}"
              f" · pid: {st.get('pid')}")
        if st.get("frames"):
            print(f"  frame: {st['frames']}")
        for name, s in (st.get("stages") or {}).items():
            print(f"  tahap {name}: {s.get('status')}"
                  f" ({s.get('started_at')} .. {s.get('ended_at')})")
        if st.get("error"):
            print(f"  error: {st['error']}")
        qp = os.path.join(os.path.abspath(args.status),
                          "qa-report.json")
        if os.path.exists(qp):
            qa = json.load(open(qp)).get("qa") or {}
            print(f"  QA: {qa.get('passed')} lulus, gagal: "
                  f"{qa.get('failed')}")
        return 0
    if not args.project or not args.out_dir:
        ap.error("--project dan --out-dir wajib (atau pakai --status)")

    out_dir = os.path.abspath(args.out_dir)
    os.makedirs(out_dir, exist_ok=True)
    _state_init(out_dir, {"project": args.project,
                          "naskah": args.naskah,
                          "profile": args.profile,
                          "recorders": args.recorders,
                          "port": args.port,
                          "frames": args.frames,
                          "finishing": bool(args.finishing),
                          "optimize_assets": bool(args.optimize_assets)})
    try:
        args.port = _pick_port(args.port)
    except StageError as e:
        print(f"[TAHAP {e.stage}] GAGAL: {e.msg}")
        _state_finish("gagal", error=f"tahap {e.stage}: {e.msg}")
        return 1
    _RUN_STATE["data"]["args"]["port"] = args.port
    _state_write()
    report = {"tool": "video_pipeline_3d.py", "project": args.project,
              "out_dir": out_dir, "server_port": args.port}
    try:
        _state_stage("0-selfcheck", "running")
        stage0_selfcheck(report)
        _state_stage("0-selfcheck", "done")
        print("[TAHAP 0] self-check WebGL + resource: OK "
              f"({report['selfcheck']['webgl2']['renderer']})")
        proj, sb_path = resolve_project(args.project)
        _state_stage("1-validasi", "running")
        sbinfo = stage1_validate(proj, sb_path, report)
        _state_stage("1-validasi", "done")
        print(f"[TAHAP 1] storyboard varian {sbinfo['variant']}: "
              f"{sbinfo['scenes']} scene, {sbinfo['duration']} dtk, "
              f"segmen VO: {list(sbinfo['segments']) or 'tidak ada'}")
        if args.dry_run:
            plan = ["# Rencana pipeline 3D (dry-run)", "",
                    f"- Proyek: {proj}",
                    f"- Varian: {sbinfo['variant']} · durasi "
                    f"{sbinfo['duration']} dtk · fps {sbinfo['fps']}",
                    "- Tahap: 0 self-check ✓ → 1 validasi ✓ → 1B aset "
                    "GLB → 2 VO "
                    f"({'generate --naskah' if args.naskah else 'pakai-ulang / tanpa'}) "
                    "→ 2B pause-gate + ukur + retime (dur_measured -> "
                    "voSync resolved) → 2D karakter (registry) → 2C "
                    "profil + lip-sync → 3 probe → 4 rekam "
                    f"({'rentang ' + args.frames if args.frames else 'penuh'}) "
                    "→ 5 rakit → 6 finalize (-15/-34) → 7 QA "
                    "(+ gerbang audio QA-A1..A5)"
                    f"{' → 8 finishing Remotion' if args.finishing else ''}",
                    "- WebGL: " + str(report["selfcheck"]["webgl2"]),
                    f"- Profil render (P2): {args.profile} "
                    "(master pixelRatio 1.0 / draft 0.75)"]
            open(os.path.join(out_dir, "rencana.md"), "w").write(
                "\n".join(plan) + "\n")
            json.dump(report, open(os.path.join(out_dir,
                                                "qa-report.json"), "w"),
                      ensure_ascii=False, indent=1, default=str)
            print("[DRY-RUN] rencana ditulis ke", out_dir)
            _state_finish("selesai-dry-run")
            return 0
        work = make_work_copy(proj, out_dir)
        _state_stage("1B-aset", "running")
        stage1b_assets(work, proj, args.optimize_assets, report)
        _state_stage("1B-aset", "done")
        print("[TAHAP 1B] aset GLB terverifikasi: OK")
        _state_stage("2-vo", "running")
        vo = stage2_vo(proj, out_dir, args.naskah, sbinfo, report)
        _state_stage("2-vo", "done")
        print(f"[TAHAP 2] VO mode {vo['mode']}: OK")
        # catatan: stage2 menulis VO langsung ke <out>/work/vo (= work/vo)
        _state_stage("2B-retime", "running")
        stage2b_retime(work, sbinfo, vo, report)
        _state_stage("2B-retime", "done")
        rt = report.get("retime", {})
        if rt.get("applied"):
            print(f"[TAHAP 2B] ukur + retime: durasi "
                  f"{rt['duration_old']} -> {rt['duration_new']} dtk "
                  f"(voSync dibangun dari dur_measured)")
        else:
            print(f"[TAHAP 2B] ukur: dur_measured tercatat "
                  f"({rt.get('note', 'retime tidak diterapkan')})")
        _state_stage("2D-karakter", "running")
        stage2d_character(work, proj, report)
        _state_stage("2D-karakter", "done")
        _state_stage("2C-profil-lipsync", "running")
        stage2c_profile_lipsync(work, vo, args.profile, report)
        _state_stage("2C-profil-lipsync", "done")
        _state_stage("3-probe", "running")
        stage3_probe(work, out_dir, sbinfo, args.port, report)
        _state_stage("3-probe", "done")
        print("[TAHAP 3] probe stills + pageerrors kosong: OK")
        _state_stage("4-rekam", "running")
        if args.skip_record:
            pre = os.path.join(out_dir, "frames")
            if not (os.path.isdir(pre) and os.listdir(pre)):
                raise StageError(4, "--skip-record: <out-dir>/frames "
                                    "kosong — tidak ada frame untuk "
                                    "dipakai")
            rec = {"start": 0, "end": -1, "fps": sbinfo["fps"],
                   "partial": bool(args.frames)}
            idxs = sorted(int(re.search(r"f(\d+)\.jpg$", f).group(1))
                          for f in os.listdir(pre) if f.endswith(".jpg"))
            rec["start"], rec["end"] = idxs[0], idxs[-1]
            if args.frames:
                a, b = args.frames.split("-", 1)
                rec["start"], rec["end"] = int(a), int(b)
            rec["count"] = rec["end"] - rec["start"] + 1
            miss = [i for i in range(rec["start"], rec["end"] + 1)
                    if not os.path.exists(os.path.join(
                        pre, f"f{i:05d}.jpg"))]
            if miss:
                raise StageError(4, f"--skip-record: {len(miss)} frame "
                                    "hilang di rentang")
            report["record"] = dict(rec, skipped=True)
        else:
            rec = stage4_record(work, out_dir, sbinfo, args.frames,
                                False, args.port, report,
                                recorders=args.recorders)
        _state_stage("4-rekam", "done")
        print(f"[TAHAP 4] rekam frame {rec['start']}-{rec['end']}: OK")
        _state_stage("5-rakit", "running")
        silent = stage5_assemble(out_dir, rec, report)
        _state_stage("5-rakit", "done")
        print("[TAHAP 5] rakit video bisu: OK")
        slug = os.path.basename(proj.rstrip("/")) or "video3d"
        _state_stage("6-finalize", "running")
        master, lufs = stage6_finalize(out_dir, silent, vo, rec, slug,
                                       report)
        _state_stage("6-finalize", "done")
        print(f"[TAHAP 6] finalize: {master} LUFS={lufs}")
        _state_stage("7-qa", "running")
        stage7_qa(out_dir, master, lufs, sbinfo, rec, vo, slug, report)
        _state_stage("7-qa", "done")
        print("[TAHAP 7] QA: semua cek keras lolos — laporan di",
              out_dir)
        if args.finishing:
            _state_stage("8-finishing", "running")
            fin = stage8_finishing(out_dir, master, slug, report)
            json.dump(report, open(os.path.join(out_dir,
                                                "qa-report.json"), "w"),
                      ensure_ascii=False, indent=1, default=str)
            _state_stage("8-finishing", "done")
            print(f"[TAHAP 8] finishing Remotion: {fin}")
        _state_finish("selesai", qa_passed=report.get("qa", {}).get(
            "passed"), master=report.get("finalize", {}).get("master"))
        return 0
    except StageError as e:
        print(f"[TAHAP {e.stage}] GAGAL: {e.msg}")
        _state_finish("gagal", error=f"tahap {e.stage}: {e.msg}")
        try:
            json.dump(report, open(os.path.join(out_dir,
                                                "qa-report.json"), "w"),
                      ensure_ascii=False, indent=1, default=str)
        except Exception:
            pass
        return 1
    except Exception as e:  # crash tak terduga pun harus terbuka, bukan diam
        import traceback
        print("[TAHAP ?] GAGAL (crash):", e)
        _state_finish("gagal", error=f"crash: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
