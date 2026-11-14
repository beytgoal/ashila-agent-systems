#!/usr/bin/env python3
"""voice_router.py — satu pintu untuk SEMUA jalur voice (gabungan).

Perintah owner 2026-10-25 ~12:45 WIB: "kombinasikan semua itu" — semua opsi
voice yang sudah diteliti digabung dalam satu router, dengan status jujur
per backend (bisa jalan / lisensi / kualitas). Router ini TIDAK menyembunyikan
kegagalan: backend yang tidak bisa dipakai untuk tayang DITOLAK di sini,
bukan di-fallback diam-diam (pelajaran ArboTTS: fallback diam-diam = voice
aneh sampai ke telinga owner).

DEFAULT AKTIF BARU (perintah owner 2026-10-31 18:23 WIB + klarifikasi
18:47 WIB "Itu tts bawaan muse meta"): TTS bawaan Muse lewat CLI
/opt/hatch/bin/tts (Meta Shortwave API) — backend "muse-tts" di router
ini, MENGGANTIKAN Charlie/Jessica sebagai default aktif:
  - Cewek TERKUNCI: avocado_v2:MAI_01 (Aria, F, Warm), Bahasa
    Indonesia. Default bawaan CLI adalah avocado_v2:MAI_03 (Helio) —
    voice TIDAK PERNAH dibiarkan default: selalu diset eksplisit, dan
    field `voice` pada keluaran CLI diverifikasi per potongan
    (substitusi = GAGAL TERBUKA, tidak diterima diam-diam). Narasi
    digenerate per potongan pendek (klausa) dengan PETA JEDA v3
    (perbaikan 2026-11-01 atas riset datahub 1297): semua jeda
    sisipan diturunkan rapat — koma 0,08 / titik dua & titik koma
    0,15 / seru & tanya 0,20 / titik 0,25 — jeda sesudah sapaan
    pembuka <=3 kata dibatasi maks 0,12, potongan di-trim tepinya
    (pad 15 ms) lalu dirakit. (Usulan riset "sintesis per kalimat
    utuh" dipalsukan uji langsung: jeda internal TTS miles di koma/
    titik dua dalam satu panggilan terukur 0,52-0,55 dtk — satuan
    klausa dipertahankan supaya semua jeda terkendali; rincian di
    komentar MUSE_PAUSE_AFTER.) Rantai poles muse-tts tidak
    memakai atempo.
  - Cowok TERKUNCI: avocado_v2:miles (Satiny Moon, M, Deep Soothing),
    Bahasa Indonesia, TANPA pitch shift. Aturan persiapan naskah
    khusus miles: kata fonetik ditulis pakai spasi TANPA tanda
    hubung.
  - Poles voice muse-tts: -15 LUFS (target ±0,5). Mix engine render:
    voice -15 LUFS di atas backsound/bed -34 LUFS (motion_render.py +
    perahu_render.py sudah disesuaikan; amix normalize=0 tetap).
  - Rantai auto: cowok muse-tts (miles) -> qwen -> piper; cewek
    muse-tts (MAI_01) -> elevenlabs (Jessica) -> piper. Charlie/Jessica
    turun jadi FALLBACK — tetap bisa dipanggil eksplisit
    (--backend elevenlabs). Aturan multi-karakter mengikuti default
    baru: pria = miles, wanita = MAI_01; pembeda karakter sesama
    gender tetap hanya pitch dari voice default yang sama, KECUALI
    miles: owner menetapkan miles tanpa pitch shift, jadi karakter
    pria tambahan memakai miles apa adanya (pengecualian tercatat apa
    adanya dari perintah owner).

Prioritas narasi (publish) — keputusan owner 2026-10-27 ~19:14 WIB
(react ❤️ ke sampel Charlie 13-elevenlabs-charlie-ab.mp3 = verdict A/B
lawan Piper; Charlie menang):
  1. elevenlabs — ElevenLabs Charlie (IKne3meq5aSn9XLyUdCD), stock,
     male/young, deep/confident. DULU DEFAULT — sejak 2026-10-31
     18:47 turun jadi FALLBACK/eksplisit (default aktif kini
     muse-tts, lihat DEFAULT AKTIF BARU di atas). Model eleven_multilingual_v2,
     output mp3_44100_128 -> wav 44100 mono, loudnorm -16 LUFS.
     JUJUR: ini suara STOCK berbahasa Inggris yang membaca teks Indonesia
     (aksen terdengar) — BUKAN voice native. Owner mendengar sampelnya dan
     memilihnya sebagai default; telinga owner yang menentukan, bukan angka.
     Free tier 10.000 karakter/bulan, reset 26 Nov 2026 16:14 WIB;
     ~900 karakter/episode → cukup ~9-10 episode, lalu fallback Piper
     sampai reset. JANGAN top-up (pembayaran milik owner).
  1b. elevenlabs (female) — ElevenLabs Jessica (cgSgspJ2msm6clMCkdW9),
      stock, female/young, Playful Bright Warm. DULU DEFAULT CEWEK
      (keputusan owner 2026-10-28 ~04:06 WIB, react 👍 ke sampel
      18-elevenlabs-jessica-ab.mp3) — sejak 2026-10-31 18:47 jadi
      FALLBACK cewek di rantai auto (muse-tts MAI_01 -> Jessica ->
      Piper) + bisa dipanggil eksplisit. Berbagi kuota free yang sama dengan Charlie
      (10.000 karakter/bulan, reset 26 Nov 2026 16:14 WIB).
      JUJUR: sama seperti Charlie, Jessica suara STOCK berbahasa
      Inggris yang membaca teks Indonesia (aksen terdengar) — bukan
      native; owner memilihnya setelah mendengar sampelnya.
  2. piper — Piper id_ID-news_tts-medium, ONNX lokal, JALAN di VM ini.
     FALLBACK TERAKHIR kedua gender (dulu: otomatis bila ElevenLabs
     gagal 402/kuota/network; sejak 2026-10-31 18:47: ujung rantai
     auto sesudah muse-tts + qwen/Jessica).
     Fallback TERCATAT di stderr + voice_log.json di out-dir (alasan gagal
     + voice yang akhirnya dipakai) — bukan diam-diam.
     KONSISTENSI: satu episode SATU voice (owner pernah komplain
     "voice nya kok ganti ganti"). Bila ElevenLabs gagal di tengah episode,
     SELURUH episode di-render ulang dengan Piper.
  2a. qwen — Qwen3-TTS Indonesia 0.6B (alkhrzmy/qwen3-tts-0.6b-indonesian,
      Apache-2.0), speaker "indonesian_speaker", LOKAL (torch CPU, venv
      uji-vo-komunitas). FALLBACK COWOK SEBELUM PIPER — keputusan owner
      2026-10-31: sampel Qwen disetujui jadi suara lokal default cowok
      ("copy ke piper" dalam bahasa owner). Hanya untuk --voice default
      (pria): Charlie gagal/kuota habis -> episode cowok turun ke Qwen
      dulu, Piper jadi fallback terakhir. Sejak 2026-10-31 18:47
      Qwen adalah fallback muse-tts (miles) sebelum Piper. Routing
      CEWEK: muse-tts (MAI_01) -> Jessica -> Piper; --backend qwen +
      --voice female DITOLAK.
      Harga: load model ±58 dtk + generate ±155 dtk per kalimat pendek
      di CPU 2-core VM ini, RAM puncak ±4 GB — render episode selalu
      batch (satu load model per episode via qwen_runner.py).
  2b. pocket-cadangan — Pocket-TTS Indonesian (anak10thn, CC BY 4.0),
      clone penutur Common Voice ID id_20954811, LOKAL (venv
      uji-vo-komunitas; ringan: load ±4 dtk + generate ±12 dtk).
      SUARA CADANGAN karakter pendukung COWOK — keputusan owner
      2026-10-31 10:07 WIB: sampel yang semula dilabeli "Cewek B"
      (F0 prompt 192 Hz) ternyata bersuara COWOK di telinga owner;
      owner memerintahkan suara itu disimpan ke pipeline lokal dan
      ditetapkan sebagai cadangan untuk karakter orang lain/pendukung.
      HANYA dipanggil EKSPLISIT (--backend pocket-cadangan atau
      --voice male-reserve). TIDAK masuk rantai fallback otomatis
      mana pun dan TIDAK menggantikan default apa pun (cowok tetap
      Charlie -> Qwen -> Piper; cewek tetap Jessica -> Piper).
      Setelan khusus voice ini: poles tempo 0,85 + perjernih, lalu
      normalisasi -13 LUFS — PENGECUALIAN dari aturan -16 LUFS atas
      perintah owner (volumenya dinaikkan, ≈+2,6 dB; patokan lead
      terukur -13,37 LUFS). Prompt terkunci di
      uji-vo-komunitas/cewek-lain/cadangan-b/.
      Generate WAJIB per klausa + jeda tanda baca (syarat owner
      2026-10-31 10:10 WIB; implementasi di pocket_runner.py mengikuti
      gen_b_jeda.py lead): teks dipecah di . ! ? , : ;, tiap klausa
      digenerate terpisah lalu di-trim hening tepinya, jeda eksplisit
      pasca-tempo PETA v2 (revisi owner 2026-10-31 11:32 WIB): koma
      0,18 / titik dua & titik koma 0,27 / seru-tanya 0,35 / titik
      0,42 dtk (disisipkan x0,85 pre-tempo).
  2c. pocket-jawa-f / pocket-jawa-m / pocket-sunda-f / pocket-sunda-m —
      Pocket-TTS Indonesian, clone penutur dataset OpenSLR Google
      Jawa (SLR41: jvf_07335 cewek, jvm_04588 cowok) & Sunda (SLR44:
      suf_02092 cewek, sum_07842 cowok), CC BY-SA 4.0, LOKAL (venv +
      runner yang sama dengan 2b; prompt per voice dipilih lewat
      "prompt_key" di job runner, aset tetap di
      uji-vo-komunitas/jawa-sunda/refs/). EMPAT VOICE BERNAMA —
      perintah owner 2026-10-31 12:39 WIB ("Simpan semua ke piper"):
      dipanggil EKSPLISIT saja (--voice cewek-jawa / cowok-jawa /
      cewek-sunda / cowok-sunda, atau --backend pocket-jawa-f /
      pocket-jawa-m / pocket-sunda-f / pocket-sunda-m). TIDAK masuk
      rantai fallback otomatis mana pun; default TIDAK berubah.
      Setelan khusus keempatnya: poles yang sama dengan 2b (tempo
      0,85 + perjernih, generate per klausa + jeda peta v2), lalu
      normalisasi -10 LUFS, true peak <= -1,0 dB — PENGECUALIAN
      loudness khusus empat voice ini atas koreksi owner 2026-10-31
      12:39 WIB ("keraskan lagi suaranya, kurang keras"; menggantikan
      angka -13 pada brief awal pemasangan). Voice cadangan B (2b)
      TIDAK ikut berubah: tetap -13 LUFS sesuai persetujuan eksplisit
      owner sebelumnya. Lisensi CC BY-SA 4.0: bila voice ini dipakai
      tayang, WAJIB atribusi ke SLR41/SLR44 (Google) + share-alike.
  3. cloud  — Google Chirp 3 HD (utama) / Azure GadisNeural (cadangan).
             JALUR UPGRADE: hanya dipakai bila kredensial ada DAN owner
             menyetujui setelah uji A/B vs Piper. Butuh kredensial env.

DITOLAK untuk tayang (tercatat di sini supaya tidak diusulkan lagi):
  - drat / Wikidepia (Coqui, wibowo/gadis/ardi): suara paling jernih di
    antara opsi GitHub (HF>8k 0.024-0.083), TAPI lisensi model tegas
    "DO NOT USE FOR COMMERCIAL PURPOSES!" + dilatih dari output Azure TTS
    (klon voice Microsoft) + butuh torch (diblokir VM) + demo HF Space
    sudah 404/hilang. Hanya 4 sampel bawaan repo yang bisa didengar.
  - bagustris / MMS (facebook/mms-tts-ind): CC BY-NC 4.0 (non-komersial)
    + tumpul (HF>8k 0.000, 97% energi <4kHz) + butuh torch. OUT.
  - voicebox (jamiepine): TIDAK ADA bahasa Indonesia di daftar bahasanya
    (ALL_LANGUAGES di kode repo: ms/Malay, tanpa id). OUT.
  - arbotts (standard/Kokoro): DITUTUP owner 2026-10-25 (bukan native).

Penggunaan:
  python3 voice_router.py --list
  python3 voice_router.py --text "Malam itu, Bapak harus memilih." --out vo.wav
  # mode auto (bawaan) = muse-tts DULU: cowok miles, cewek MAI_01
  python3 voice_router.py --text "..." --backend muse-tts --out vo.wav
  # muse-tts = TTS bawaan Muse (CLI /opt/hatch/bin/tts): DEFAULT AKTIF
  # sejak 2026-10-31 18:47; eksplisit = muse-tts saja, gagal terbuka
  python3 voice_router.py --text "..." --backend piper --out vo.wav
  python3 voice_router.py --text "..." --backend qwen --out vo.wav
  # --backend qwen = Qwen3-TTS lokal PRIA (cowok saja; ditolak untuk --voice female)
  python3 voice_router.py --text "..." --backend pocket-cadangan --out vo.wav
  python3 voice_router.py --segments naskah.json --out-dir vo/ --voice male-reserve
  # pocket-cadangan / male-reserve = Pocket suara B, cadangan karakter
  # pendukung cowok (EKSPLISIT saja, tidak pernah otomatis, -13 LUFS)
  python3 voice_router.py --text "..." --voice cewek-jawa --out vo.wav
  python3 voice_router.py --text "..." --backend pocket-sunda-m --out vo.wav
  # voice bernama Jawa/Sunda: cewek-jawa, cowok-jawa, cewek-sunda,
  # cowok-sunda (backend pocket-jawa-f/-m, pocket-sunda-f/-m) —
  # EKSPLISIT saja, tidak pernah otomatis, -10 LUFS (owner 2026-10-31)
  python3 voice_router.py --text "..." --backend elevenlabs --out vo.wav
  python3 voice_router.py --segments naskah.json --out-dir vo/
  python3 voice_router.py --segments naskah.json --out-dir vo/ --voice female
  # --voice female = MAI_01 via muse-tts (default cewek); default =
  # miles via muse-tts (default utama); Jessica/Charlie kini fallback
  # override voice ElevenLabs (pengujian fallback): ELEVENLABS_VOICE_ID=xxx

Kredensial ElevenLabs: TIDAK PERNAH dibaca/disimpan di file ini — helper
custom.elevenlabs memakai dynamic_credentials (surrogate), kunci hanya
ditukar di memori saat request ke api.elevenlabs.io.
"""
import argparse, json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PIPER_MODEL = os.path.join(HERE, "assets", "piper", "id_ID-news_tts-medium.onnx")
PIPER_VENV = os.path.join(HERE, ".venv-piper", "bin", "python")  # dulu /tmp/tts-test-venv (hilang saat /tmp dibersihkan) — venv durable di engine/.venv-piper, di-install ulang 2026-10-25
CLOUD_VO = os.path.join(HERE, "cloud_vo.py")
# Backend lokal cowok (keputusan owner 2026-10-31): Qwen3-TTS Indonesia.
# Model + venv tinggal di folder uji divisi (BUKAN di engine) karena butuh
# torch CPU; router memanggilnya sebagai subprocess batch (qwen_runner.py,
# satu load model per episode).
QWEN_HOME = os.path.expanduser("~/workspace/divisi/branding-promosi/uji-vo-komunitas")
QWEN_VENV = os.path.join(QWEN_HOME, ".venv-uji", "bin", "python")
QWEN_RUNNER = os.path.join(QWEN_HOME, "qwen_runner.py")
QWEN_MODEL = os.path.join(QWEN_HOME, "models", "qwen3tts")
# Suara CADANGAN karakter pendukung cowok (keputusan owner 2026-10-31
# 10:07 WIB): Pocket-TTS clone penutur Common Voice ID id_20954811.
# Model + config tinggal di folder uji divisi (cewek-lain/models/pocket),
# venv sama dengan Qwen (.venv-uji, pocket-tts terpasang di sana), prompt
# tetap diamankan di cewek-lain/cadangan-b/. Router memanggilnya sebagai
# subprocess batch (pocket_runner.py). Voice ini EKSPLISIT saja — tidak
# pernah masuk rantai fallback otomatis.
POCKET_HOME = os.path.expanduser("~/workspace/divisi/branding-promosi/uji-vo-komunitas")
POCKET_VENV = os.path.join(POCKET_HOME, ".venv-uji", "bin", "python")
POCKET_RUNNER = os.path.join(POCKET_HOME, "pocket_runner.py")
POCKET_CFG = os.path.join(POCKET_HOME, "cewek-lain", "models", "pocket", "local_6l.yaml")
POCKET_PROMPT = os.path.join(POCKET_HOME, "cewek-lain", "cadangan-b", "prompt-B-commonvoice-id_20954811.mp3")
POCKET_LUFS = -13.0  # pengecualian khusus voice cadangan B — perintah owner: volumenya dinaikkan (aturan umum tetap -16)
# Empat voice BERNAMA Jawa/Sunda (perintah owner 2026-10-31 12:39 WIB:
# "Simpan semua ke piper" + koreksi loudness "keraskan lagi, kurang
# keras"): clone Pocket dari penutur OpenSLR SLR41/SLR44 (CC BY-SA
# 4.0). Prompt tetap di jawa-sunda/refs/ (md5 terverifikasi = klip
# referensi sampel v2). Target loudness KHUSUS keempat voice ini:
# -10 LUFS, true peak <= -1,0 dB (loudnorm dua pass TP -1,5 + limiter
# 0,84 pada trim gain, supaya keras tanpa pecah). Pocket-cadangan
# tetap -13 LUFS — TIDAK ikut koreksi ini.
POCKET_NAMED_LUFS = -10.0
POCKET_REFS_DIR = os.path.join(POCKET_HOME, "jawa-sunda", "refs")
POCKET_NAMED_VOICES = {
    # backend -> spesifikasi voice bernama (eksplisit saja)
    "pocket-jawa-f": {
        "voice": "cewek-jawa", "prompt_key": "cewek-jawa",
        "gender": "female", "label": "pocket-cewek-jawa",
        "speaker": "SLR41 jvf_07335 (Jawa, perempuan)",
        "prompt": os.path.join(POCKET_REFS_DIR, "ref-jawa-cewek.wav"),
    },
    "pocket-jawa-m": {
        "voice": "cowok-jawa", "prompt_key": "cowok-jawa",
        "gender": "male", "label": "pocket-cowok-jawa",
        "speaker": "SLR41 jvm_04588 (Jawa, laki-laki)",
        "prompt": os.path.join(POCKET_REFS_DIR, "ref-jawa-cowok.wav"),
    },
    "pocket-sunda-f": {
        "voice": "cewek-sunda", "prompt_key": "cewek-sunda",
        "gender": "female", "label": "pocket-cewek-sunda",
        "speaker": "SLR44 suf_02092 (Sunda, perempuan)",
        "prompt": os.path.join(POCKET_REFS_DIR, "ref-sunda-cewek.wav"),
    },
    "pocket-sunda-m": {
        "voice": "cowok-sunda", "prompt_key": "cowok-sunda",
        "gender": "male", "label": "pocket-cowok-sunda",
        "speaker": "SLR44 sum_07842 (Sunda, laki-laki)",
        "prompt": os.path.join(POCKET_REFS_DIR, "ref-sunda-cowok.wav"),
    },
}
# nama --voice -> backend padanannya
POCKET_VOICE_TO_BACKEND = {spec["voice"]: backend
                           for backend, spec in POCKET_NAMED_VOICES.items()}
# path prompt per kunci (untuk validasi _pocket_job)
POCKET_PROMPT_PATHS = {"cadangan": POCKET_PROMPT}
for _spec in POCKET_NAMED_VOICES.values():
    POCKET_PROMPT_PATHS[_spec["prompt_key"]] = _spec["prompt"]
POCKET_ALL_BACKENDS = ["pocket-cadangan"] + list(POCKET_NAMED_VOICES)
ELEVENLABS_HELPER = os.path.normpath(os.path.join(
    HERE, "..", "..", "custom-connectors", "custom.elevenlabs", "bin", "elevenlabs.py"))
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "IKne3meq5aSn9XLyUdCD")  # Charlie (default utama)
ELEVENLABS_VOICE_ID_FEMALE = os.environ.get("ELEVENLABS_VOICE_ID_FEMALE", "cgSgspJ2msm6clMCkdW9")  # Jessica (default cewek)
ELEVENLABS_VOICES = {
    "default": ("Charlie", ELEVENLABS_VOICE_ID),
    "female": ("Jessica", ELEVENLABS_VOICE_ID_FEMALE),
}
ELEVENLABS_MODEL = "eleven_multilingual_v2"
# DEFAULT AKTIF BARU (perintah owner 2026-10-31 18:23 WIB + klarifikasi
# 18:47 WIB "Itu tts bawaan muse meta"): TTS bawaan Muse lewat CLI
# /opt/hatch/bin/tts (Meta Shortwave API), katalog
# /opt/muse/assets/voice-selector/voice_source.json. Voice TERKUNCI —
# JANGAN PERNAH mengandalkan default CLI (avocado_v2:MAI_03 / Helio):
# voice selalu diset eksplisit dan field `voice` hasil CLI diverifikasi
# per potongan; substitusi = gagal terbuka.
MUSE_TTS_BIN = "/opt/hatch/bin/tts"
MUSE_TTS_VOICE_FEMALE = "avocado_v2:MAI_01"  # Aria (F, Warm) — cewek terkunci
MUSE_TTS_VOICE_MALE = "avocado_v2:miles"     # Satiny Moon (M, Deep Soothing) — cowok terkunci, TANPA pitch shift
MUSE_TTS_LANG = "id"
MUSE_TTS_LUFS = -15.0  # target poles voice muse-tts (mix engine: voice -15 di atas bed -34)
MUSE_TTS_SR = 44100
# Jeda antar-potongan muse-tts menurut tanda baca penutup potongan
# sebelumnya — PETA v3 (perbaikan P1 2026-11-01 atas riset datahub
# 1297; perintah owner menyetujui blueprint P0+P1 2026-11-01 09:02
# WIB). Menggantikan PETA v2 (koma 0,18 / titik dua & titik koma
# 0,27 / seru & tanya 0,35 / titik 0,42) yang terbukti terlalu jauh:
# jeda efektif terukur 0,34-0,45 dtk + 0,39 dtk sesudah sapaan.
# CATATAN PENYESUAIAN BERBASIS UKUR (2026-11-01): riset mengusulkan
# satuan sintesis naik ke KALIMAT utuh supaya koma/titik dua di
# dalam kalimat ditangani prosodi TTS. Uji langsung di VM ini
# MEMALSUKAN asumsi itu untuk voice miles: jeda internal TTS di
# koma dan titik dua dalam satu panggilan terukur 0,52-0,55 dtk
# (lebih jauh dari v2!), dan sapaan+kalimat dalam satu panggilan
# diregangkan jadi 24,12 dtk vs 9,43 dtk terpisah. Maka v3 final =
# satuan klausa DIPERTAHANKAN (semua jeda berada dalam kendali
# sisipan, seperti v2 yang terukur), dengan seluruh nilai peta
# diturunkan rapat + pad trim 15 ms + jeda sapaan terkap. Nilai
# NOMINAL: rantai poles muse-tts tidak memakai atempo.
MUSE_PAUSE_AFTER = {".": 0.25, "!": 0.20, "?": 0.20, ":": 0.15,
                    ";": 0.15, ",": 0.08}
# Sapaan pembuka: kalimat pertama <=3 kata (mis. "Halo, Warga!")
# tetap panggilan TTS sendiri, tetapi jeda sisipan sesudahnya
# dibatasi maks 0,12 (v2 memberinya jeda tanda seru penuh 0,35 ->
# 0,39 efektif, tepat di hook). Penggabungan sapaan+kalimat dalam
# satu panggilan DITOLAK berdasar uji 2026-11-01: TTS miles
# meregangkan jeda internal sesudah "!" sampai patologis
# (24,12 dtk gabungan vs 9,43 dtk terpisah).
MUSE_GREETING_MAX_WORDS = 3
MUSE_GREETING_MAX_PAUSE = 0.12

BACKENDS = {
    "muse-tts": {
        "status": "DEFAULT AKTIF — TTS bawaan Muse (perintah owner 2026-10-31 18:23, klarifikasi 18:47: 'tts bawaan muse meta')",
        "publish": True,
        "note": "CLI /opt/hatch/bin/tts (Meta Shortwave API), tanpa akun/kredensial. Cewek TERKUNCI avocado_v2:MAI_01 (Aria, F, Warm); cowok TERKUNCI avocado_v2:miles (Satiny Moon, M, Deep Soothing) TANPA pitch shift — aturan naskah miles: kata fonetik ditulis pakai spasi TANPA tanda hubung. Default CLI avocado_v2:MAI_03 TIDAK pernah dipakai: voice selalu eksplisit + field voice hasil diverifikasi per potongan (substitusi = gagal terbuka). Generate per potongan pendek (klausa) + jeda sisipan peta v3 (2026-11-01; koma 0,08 / titik dua & titik koma 0,15 / seru-tanya 0,20 / titik 0,25, jeda sesudah sapaan <=3 kata maks 0,12, pad trim 15 ms); poles -15 LUFS. Rantai auto: cowok muse-tts -> qwen -> piper; cewek muse-tts -> elevenlabs (Jessica) -> piper.",
    },
    "elevenlabs": {
        "status": "FALLBACK — dulu default (pilihan owner 2026-10-27, verdict A/B: react ❤️ ke Charlie); sejak 2026-10-31 18:47 turun jadi fallback cewek (Jessica) + jalur eksplisit. Default aktif kini muse-tts",
        "publish": True,
        "note": "Charlie IKne3meq5aSn9XLyUdCD, stock male/young, eleven_multilingual_v2. Cewek (--voice female): Jessica cgSgspJ2msm6clMCkdW9, stock female/young — di rantai auto kini hanya sebagai fallback sesudah muse-tts MAI_01. Free tier 10.000 karakter/bulan, reset 26 Nov 2026 16:14 WIB.",
    },
    "cloud": {
        "status": "butuh kredensial (GOOGLE_TTS_API_KEY / AZURE_SPEECH_KEY)",
        "publish": True,
        "note": "Chirp 3 HD id-ID-Chirp3-HD-Kore utama, Azure id-ID-GadisNeural cadangan.",
    },
    "piper": {
        "status": "FALLBACK TERAKHIR kedua gender — ujung rantai auto (dulu: dipakai bila ElevenLabs gagal 402/kuota/network)",
        "publish": True,
        "note": "ONNX lokal, jalan di VM tanpa torch. Dulu default (owner 2026-10-25); sejak 2026-10-27 jadi fallback Charlie. Sejak 2026-10-31 pagi: cowok fallback kedua (setelah Qwen), cewek fallback langsung Jessica. Sejak 2026-10-31 18:47: fallback TERAKHIR di kedua rantai muse-tts (cowok: miles -> qwen -> piper; cewek: MAI_01 -> Jessica -> piper).",
    },
    "qwen": {
        "status": "LOKAL COWOK — fallback muse-tts (miles) SEBELUM Piper (dulu fallback Charlie; keputusan owner 2026-10-31: sampel disetujui jadi default cowok lokal)",
        "publish": True,
        "note": "Qwen3-TTS-ID 0.6B (alkhrzmy/qwen3-tts-0.6b-indonesian, Apache-2.0), speaker indonesian_speaker, torch CPU via venv uji-vo-komunitas + qwen_runner.py (batch, satu load per episode). Load ±58 dtk + generate ±155 dtk/kalimat pendek (CPU 2-core), RAM puncak ±4 GB. PRIA SAJA — tidak pernah dipakai untuk --voice female.",
    },
    "pocket-cadangan": {
        "status": "CADANGAN KARAKTER PENDUKUNG COWOK — hanya EKSPLISIT, bukan default, bukan fallback otomatis (keputusan owner 2026-10-31)",
        "publish": True,
        "note": "Pocket-TTS-ID 6-layer (anak10thn/pocket-tts-indonesian, CC BY 4.0), clone penutur Common Voice ID id_20954811 — sampel eks-'Cewek B' yang menurut telinga owner bersuara cowok. Prompt terkunci di cewek-lain/cadangan-b/prompt-B-commonvoice-id_20954811.mp3. Setelan khusus: tempo 0,85 + perjernih, -13 LUFS (pengecualian -16 atas perintah owner). Ringan: load ±4 dtk + generate ±12 dtk/kalimat (CPU 2-core). Panggil: --backend pocket-cadangan atau --voice male-reserve.",
    },
    "pocket-jawa-f": {
        "status": "VOICE BERNAMA CEWEK JAWA — hanya EKSPLISIT (--voice cewek-jawa / --backend pocket-jawa-f), bukan default, bukan fallback (owner 2026-10-31)",
        "publish": True,
        "note": "Pocket-TTS-ID 6-layer (CC BY 4.0), clone penutur SLR41 jvf_07335 (OpenSLR Jawa, Google, CC BY-SA 4.0 — atribusi + share-alike bila tayang). Prompt tetap: jawa-sunda/refs/ref-jawa-cewek.wav. Setelan khusus: tempo 0,85 + perjernih, jeda peta v2, -10 LUFS / TP <= -1,0 (koreksi owner 2026-10-31 12:39). Ringan: load ±4 dtk + generate ±12 dtk/kalimat.",
    },
    "pocket-jawa-m": {
        "status": "VOICE BERNAMA COWOK JAWA — hanya EKSPLISIT (--voice cowok-jawa / --backend pocket-jawa-m), bukan default, bukan fallback (owner 2026-10-31)",
        "publish": True,
        "note": "Pocket-TTS-ID 6-layer (CC BY 4.0), clone penutur SLR41 jvm_04588 (OpenSLR Jawa, Google, CC BY-SA 4.0 — atribusi + share-alike bila tayang). Prompt tetap: jawa-sunda/refs/ref-jawa-cowok.wav. Setelan khusus: tempo 0,85 + perjernih, jeda peta v2, -10 LUFS / TP <= -1,0 (koreksi owner 2026-10-31 12:39). Ringan: load ±4 dtk + generate ±12 dtk/kalimat.",
    },
    "pocket-sunda-f": {
        "status": "VOICE BERNAMA CEWEK SUNDA — hanya EKSPLISIT (--voice cewek-sunda / --backend pocket-sunda-f), bukan default, bukan fallback (owner 2026-10-31)",
        "publish": True,
        "note": "Pocket-TTS-ID 6-layer (CC BY 4.0), clone penutur SLR44 suf_02092 (OpenSLR Sunda, Google, CC BY-SA 4.0 — atribusi + share-alike bila tayang). Prompt tetap: jawa-sunda/refs/ref-sunda-cewek.wav. Setelan khusus: tempo 0,85 + perjernih, jeda peta v2, -10 LUFS / TP <= -1,0 (koreksi owner 2026-10-31 12:39). Ringan: load ±4 dtk + generate ±12 dtk/kalimat.",
    },
    "pocket-sunda-m": {
        "status": "VOICE BERNAMA COWOK SUNDA — hanya EKSPLISIT (--voice cowok-sunda / --backend pocket-sunda-m), bukan default, bukan fallback (owner 2026-10-31)",
        "publish": True,
        "note": "Pocket-TTS-ID 6-layer (CC BY 4.0), clone penutur SLR44 sum_07842 (OpenSLR Sunda, Google, CC BY-SA 4.0 — atribusi + share-alike bila tayang). Prompt tetap: jawa-sunda/refs/ref-sunda-cowok.wav. Setelan khusus: tempo 0,85 + perjernih, jeda peta v2, -10 LUFS / TP <= -1,0 (koreksi owner 2026-10-31 12:39). Ringan: load ±4 dtk + generate ±12 dtk/kalimat.",
    },
    "drat": {
        "status": "DITOLAK — lisensi non-komersial + torch + demo 404",
        "publish": False,
        "note": "Suara paling jernih di GitHub, tapi 'DO NOT USE FOR COMMERCIAL PURPOSES!' + klon Azure.",
    },
    "mms": {
        "status": "DITOLAK — CC BY-NC 4.0 + tumpul + torch",
        "publish": False,
        "note": "facebook/mms-tts-ind, non-komersial, HF>8k 0.000.",
    },
    "voicebox": {
        "status": "DITOLAK — tidak ada bahasa Indonesia",
        "publish": False,
        "note": "jamiepine/voicebox: ALL_LANGUAGES di kode repo tanpa 'id' (hanya ms/Malay).",
    },
    "arbotts": {
        "status": "DITOLAK owner 2026-10-25 — bukan native",
        "publish": False,
        "note": "Standard robot/kurang jernih, Kokoro bukan native Indonesia.",
    },
}

def _ffprobe_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True)
    return float(out.stdout.strip())

def _measure_lufs(path):
    """Integrated loudness (LUFS) via ffmpeg loudnorm analysis."""
    p = subprocess.run(
        ["ffmpeg", "-i", path, "-af", "loudnorm=print_format=json",
         "-f", "null", "-"],
        capture_output=True, text=True)
    s = p.stderr
    i, j = s.find("{"), s.rfind("}")
    return float(json.loads(s[i:j + 1])["input_i"])

def _loudnorm16(path):
    """Normalisasi file VO ke -16 LUFS (aturan serial): single-pass loudnorm,
    lalu trim gain sekali bila masih >0.5 LU dari target. Return LUFS akhir."""
    tmp = path + ".ln.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", path,
         "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
         "-ar", "44100", "-ac", "1", tmp],
        check=True)
    os.replace(tmp, path)
    lufs = _measure_lufs(path)
    if abs(lufs - (-16.0)) > 0.5:
        gain = -16.0 - lufs
        tmp2 = path + ".g.wav"
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", path,
             "-af", f"volume={gain:.2f}dB", tmp2],
            check=True)
        os.replace(tmp2, path)
        lufs = _measure_lufs(path)
    return lufs

def synth_piper(text, out_path):
    if not os.path.exists(PIPER_MODEL):
        raise RuntimeError(f"Model Piper tidak ada: {PIPER_MODEL}")
    p = subprocess.run(
        [PIPER_VENV, "-m", "piper", "--model", PIPER_MODEL,
         "--output_file", out_path],
        input=text.encode(), capture_output=True)
    if p.returncode != 0 or not os.path.exists(out_path):
        raise RuntimeError(f"Piper gagal: {p.stderr.decode()[-300:]}")
    # samakan kontrak output dengan elevenlabs: VO -16 LUFS (engine juga
    # loudnorm di mix, tapi file VO-nya sendiri harus sudah -16)
    lufs = _loudnorm16(out_path)
    print(f"[piper] {os.path.basename(out_path)}: LUFS={lufs:.2f}",
          file=sys.stderr)
    return out_path

QWEN_PRE_FILTER = ("acompressor=threshold=-24dB:ratio=8:attack=2:release=200,"
                   "alimiter=limit=0.6:level=false")

def _loudnorm16_local(path):
    """Normalisasi VO Qwen lokal ke -16 LUFS. Output mentah Qwen crest
    factor-nya tinggi (puncak detik pertama TP -0,76 dB, envelope menurun
    -17 -> -27 dB): loudnorm polos mentok di ~-18,3 LUFS karena mode
    linear menahan gain demi true-peak. Pre-filter kompresor+limiter
    meratakan envelope dulu, lalu loudnorm dua pass terukur (pola
    normalize.py divisi). Terverifikasi pada wav uji divisi: hasil
    -16,48 LUFS / TP -1,50. Return LUFS akhir."""
    p = subprocess.run(
        ["ffmpeg", "-i", path, "-af",
         f"{QWEN_PRE_FILTER},loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json",
         "-f", "null", "-"],
        capture_output=True, text=True)
    s = p.stderr
    i, j = s.find("{"), s.rfind("}")
    d = json.loads(s[i:j + 1])
    af = (f"{QWEN_PRE_FILTER},loudnorm=I=-16:TP=-1.5:LRA=11:"
          f"measured_I={d['input_i']}:measured_TP={d['input_tp']}:"
          f"measured_LRA={d['input_lra']}:measured_thresh={d['input_thresh']}:"
          f"offset={d['target_offset']}:linear=true")
    tmp = path + ".ln.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", path, "-af", af,
         "-ar", "44100", "-ac", "1", tmp],
        check=True)
    os.replace(tmp, path)
    lufs = _measure_lufs(path)
    if abs(lufs - (-16.0)) > 0.5:
        # trim gain terakhir; limiter menjaga true-peak tetap aman
        gain = -16.0 - lufs
        tmp2 = path + ".g.wav"
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", path,
             "-af", f"volume={gain:.2f}dB,alimiter=limit=0.84:level=false",
             tmp2],
            check=True)
        os.replace(tmp2, path)
        lufs = _measure_lufs(path)
    return lufs

def _qwen_job(items):
    """Jalankan qwen_runner.py SEKALI (satu load model) untuk semua item.
    items: list dict {id, text, out} — out = path wav mentah tujuan."""
    for pth, label in ((QWEN_VENV, "venv uji-vo-komunitas"),
                       (QWEN_RUNNER, "qwen_runner.py"),
                       (QWEN_MODEL, "model Qwen3-TTS")):
        if not os.path.exists(pth):
            raise RuntimeError(f"{label} tidak ada: {pth}")
    out_dir = os.path.dirname(os.path.abspath(items[0]["out"]))
    os.makedirs(out_dir, exist_ok=True)
    fd, job_path = tempfile.mkstemp(suffix=".json", dir=out_dir)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(items, f)
        # load ±58 dtk + generate ±155 dtk/kalimat pendek di CPU 2-core
        timeout = 900 + 300 * len(items)
        p = subprocess.run([QWEN_VENV, QWEN_RUNNER, job_path],
                           capture_output=True, text=True, timeout=timeout)
        if p.stdout:
            print(p.stdout.strip()[-2000:], file=sys.stderr)
        if p.stderr:
            print(p.stderr.strip()[-500:], file=sys.stderr)
        if p.returncode != 0:
            raise RuntimeError(
                f"qwen_runner gagal (rc={p.returncode}): "
                f"{(p.stdout or '')[-300:]}")
    finally:
        if os.path.exists(job_path):
            os.remove(job_path)
    for it in items:
        if not os.path.exists(it["out"]):
            raise RuntimeError(f"qwen_runner tidak menghasilkan {it['out']}")

def synth_qwen(text, out_path, seg_id="text"):
    """Sintesis SATU teks dengan Qwen3-TTS lokal (pria). Untuk banyak
    segmen pakai synth_qwen_segments (satu load model per episode)."""
    raw = out_path + ".qwen-raw.wav"
    try:
        _qwen_job([{"id": seg_id, "text": text, "out": raw}])
        shutil.copyfile(raw, out_path)
    finally:
        if os.path.exists(raw):
            os.remove(raw)
    lufs = _loudnorm16_local(out_path)
    dur = _ffprobe_duration(out_path)
    if dur < 0.5:
        raise RuntimeError(f"Qwen audio terlalu pendek ({dur:.2f}s).")
    print(f"[qwen] {os.path.basename(out_path)}: voice=qwen3tts-lokal-pria "
          f"dur={dur:.2f}s LUFS={lufs:.2f}", file=sys.stderr)
    return out_path

def synth_qwen_segments(items, out_dir):
    """Render semua segmen episode dengan Qwen dalam SATU proses runner
    (satu load model per episode — bukan per segmen)."""
    jobs, raws = [], {}
    for it in items:
        raw = os.path.join(out_dir, f"{it['id']}.qwen-raw.wav")
        raws[it["id"]] = raw
        jobs.append({"id": it["id"], "text": it["text"], "out": raw})
    _qwen_job(jobs)
    for it in items:
        out_path = os.path.join(out_dir, f"{it['id']}.wav")
        try:
            shutil.copyfile(raws[it["id"]], out_path)
        finally:
            if os.path.exists(raws[it["id"]]):
                os.remove(raws[it["id"]])
        lufs = _loudnorm16_local(out_path)
        print(f"[qwen] {it['id']}.wav: LUFS={lufs:.2f}", file=sys.stderr)
    return out_dir

POCKET_POLISH_FILTER = ("atempo=0.85,highpass=f=70,afftdn=nf=-22:tn=1,"
                        "equalizer=f=2800:t=q:w=1.2:g=3,"
                        "equalizer=f=5500:t=q:w=1.2:g=2")

def _polish_pocket(path, target_lufs=POCKET_LUFS, true_peak=-1.0,
                   trim_limit=0.89, pre_filter="", trim_iters=5):
    """Poles + normalisasi KHUSUS voice Pocket (cadangan B & bernama).

    PENGECUALIAN dari aturan serial -16 LUFS. Rantai poles mengikuti
    patokan lead: tempo 0,85 (atempo, pitch terjaga), highpass 70 Hz,
    afftdn ringan, EQ presence (+3 dB @2,8 kHz, +2 dB @5,5 kHz), lalu
    loudnorm dua pass terukur ke I=target:TP=true_peak (pola
    _loudnorm16_local), ditutup trim gain iteratif (maks 3x, limiter
    trim_limit) karena loudnorm linear bisa mendarat ~1 LU di bawah
    target pada materi ini. Return LUFS akhir.

    Parameter per voice:
    - pocket-cadangan: target -13 LUFS, TP -1.0, limiter 0,89 —
      keputusan owner 2026-10-31 10:07 WIB (volume dinaikkan ≈+2,6 dB;
      patokan lead terukur -13,37 LUFS). TIDAK berubah oleh koreksi
      loudness 12:39 (koreksi itu khusus empat voice Jawa/Sunda).
    - pocket-jawa-*/pocket-sunda-*: target -10 LUFS, TP -1,5 pada
      loudnorm + limiter 0,84 pada trim — koreksi owner 2026-10-31
      12:39 WIB ("keraskan lagi suaranya, kurang keras"); TP akhir
      terukur wajib <= -1,0 dB (keras tanpa pecah/clipping). Karena
      materi Pocket padat puncak (crest raw 17,8 dB), loudnorm polos
      mentok di ≈-14,2 dan trim limiter saja asimtot di ≈-11,1;
      voice bernama memakai pre_filter penurun crest
      (POCKET_NAMED_PREFILTER: kompresor Qwen + 3x soft-clip
      compand) sebelum loudnorm + tahap penutup flat-clip terukur
      di _polish10_pocket_named."""
    tp = f"{true_peak:g}"
    chain = POCKET_POLISH_FILTER + (f",{pre_filter}" if pre_filter else "")
    p = subprocess.run(
        ["ffmpeg", "-i", path, "-af",
         f"{chain},loudnorm=I={target_lufs:g}:TP={tp}:LRA=11:print_format=json",
         "-f", "null", "-"],
        capture_output=True, text=True)
    s = p.stderr
    i, j = s.find("{"), s.rfind("}")
    d = json.loads(s[i:j + 1])
    af = (f"{chain},loudnorm=I={target_lufs:g}:TP={tp}:LRA=11:"
          f"measured_I={d['input_i']}:measured_TP={d['input_tp']}:"
          f"measured_LRA={d['input_lra']}:measured_thresh={d['input_thresh']}:"
          f"offset={d['target_offset']}:linear=true")
    tmp = path + ".ln.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", path, "-af", af,
         "-ar", "44100", "-ac", "1", tmp],
        check=True)
    os.replace(tmp, path)
    lufs = _measure_lufs(path)
    for _ in range(trim_iters):
        if abs(lufs - target_lufs) <= 0.3:
            break
        gain = target_lufs - lufs
        tmp2 = path + ".g.wav"
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", path,
             "-af", f"volume={gain:.2f}dB,alimiter=limit={trim_limit}:level=false",
             tmp2],
            check=True)
        os.replace(tmp2, path)
        lufs = _measure_lufs(path)
    return lufs

def _polish13_pocket(path):
    """Poles voice cadangan Pocket B ke -13 LUFS (parameter persis
    seperti sebelum generalisasi — jalur regresi TIDAK berubah)."""
    return _polish_pocket(path, POCKET_LUFS, true_peak=-1.0,
                          trim_limit=0.89)

# Rantai penurun crest khusus voice bernama (hasil kalibrasi offline
# pada raw Pocket cowok-jawa, crest awal 17,8 dB / LRA 2,5 — materi
# paling bandel): kompresor+limiter Qwen, lalu 3x tahap soft-clip
# compand (gain +6 dB -> kurva statis ceiling -2 dB). Sesudah rantai
# ini loudnorm dua pass mendarat ≈-13,5, trim limiter ≈-10,6, dan
# tahap penutup flat-clip terukur di _polish10_pocket_named menutup
# ke -10,26 / TP -1,65. Tanpa penurun crest, loudnorm linear mentok
# di ≈-14,2 dan trim limiter saja asimtot di ≈-11,1..-11,7.
_POCKET_FLAT_CURVE = ("compand=attacks=0:decays=0.01:"
                      "points=-90/-90|-12/-12|-2/-2|6/-2")
_POCKET_NAMED_CLIP = "volume=6.0dB," + _POCKET_FLAT_CURVE
POCKET_NAMED_PREFILTER = (QWEN_PRE_FILTER + ","
                          + ",".join([_POCKET_NAMED_CLIP] * 3))

def _polish10_pocket_named(path):
    """Poles empat voice bernama Jawa/Sunda ke -10 LUFS, TP <= -1,0
    (koreksi owner 2026-10-31 12:39 WIB). Urutan: _polish_pocket
    dengan pre-filter penurun crest + loudnorm dua pass + trim
    limiter (maks 10x), lalu tahap penutup flat-clip TERUKUR: selama
    LUFS masih di bawah target-0,3 (maks 4 tahap), terapkan gain
    kecil (0,4..1,6 dB) + kurva compand ceiling -2 yang sama —
    terverifikasi menutup -10,61 -> -10,26 dengan TP -1,65 pada
    materi cowok-jawa. Return LUFS akhir."""
    lufs = _polish_pocket(path, POCKET_NAMED_LUFS, true_peak=-1.5,
                          trim_limit=0.84, trim_iters=10,
                          pre_filter=POCKET_NAMED_PREFILTER)
    for _ in range(4):
        if lufs >= POCKET_NAMED_LUFS - 0.3:
            break
        gain = max(0.4, min(1.6, (POCKET_NAMED_LUFS - lufs) * 1.8))
        tmp = path + ".clip.wav"
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", path,
             "-af", f"volume={gain:.2f}dB,{_POCKET_FLAT_CURVE}", tmp],
            check=True)
        os.replace(tmp, path)
        lufs = _measure_lufs(path)
    return lufs

def _pocket_job(items, prompt_key=None):
    """Jalankan pocket_runner.py SEKALI (satu load model) untuk semua
    item. items: list dict {id, text, out} — out = path wav mentah.
    prompt_key (atau "prompt_key" per item) memilih prompt di runner;
    tanpa kunci -> "cadangan" (suara B, perilaku lama tidak berubah)."""
    if prompt_key is not None:
        items = [dict(it, prompt_key=prompt_key) for it in items]
    checks = [(POCKET_VENV, "venv uji-vo-komunitas"),
              (POCKET_RUNNER, "pocket_runner.py"),
              (POCKET_CFG, "config Pocket")]
    seen_keys = []
    for it in items:
        key = it.get("prompt_key", "cadangan")
        if key not in POCKET_PROMPT_PATHS:
            raise RuntimeError(f"kunci prompt Pocket tidak dikenal: {key!r}")
        if key not in seen_keys:
            seen_keys.append(key)
    for key in seen_keys:
        checks.append((POCKET_PROMPT_PATHS[key], f"prompt {key}"))
    for pth, label in checks:
        if not os.path.exists(pth):
            raise RuntimeError(f"{label} tidak ada: {pth}")
    out_dir = os.path.dirname(os.path.abspath(items[0]["out"]))
    os.makedirs(out_dir, exist_ok=True)
    fd, job_path = tempfile.mkstemp(suffix=".json", dir=out_dir)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(items, f)
        # load ±4 dtk + generate ±12 dtk/kalimat pendek di CPU 2-core.
        # Timeout diperlonggar (dari 300+120/item): pada 2026-10-31
        # sore VM mengalami load 11-13 (2-core) dan generate yang
        # normalnya ±37 dtk menembus 420 dtk -> timeout palsu.
        timeout = 900 + 300 * len(items)
        p = subprocess.run([POCKET_VENV, POCKET_RUNNER, job_path],
                           capture_output=True, text=True, timeout=timeout)
        if p.stdout:
            print(p.stdout.strip()[-2000:], file=sys.stderr)
        if p.stderr:
            print(p.stderr.strip()[-500:], file=sys.stderr)
        if p.returncode != 0:
            raise RuntimeError(
                f"pocket_runner gagal (rc={p.returncode}): "
                f"{(p.stdout or '')[-300:]}")
    finally:
        if os.path.exists(job_path):
            os.remove(job_path)
    for it in items:
        if not os.path.exists(it["out"]):
            raise RuntimeError(f"pocket_runner tidak menghasilkan {it['out']}")

def synth_pocket_cadangan(text, out_path, seg_id="text"):
    """Sintesis SATU teks dengan Pocket suara cadangan B (pendukung
    cowok). Untuk banyak segmen pakai synth_pocket_cadangan_segments."""
    raw = out_path + ".pocket-raw.wav"
    try:
        _pocket_job([{"id": seg_id, "text": text, "out": raw}])
        shutil.copyfile(raw, out_path)
    finally:
        if os.path.exists(raw):
            os.remove(raw)
    lufs = _polish13_pocket(out_path)
    dur = _ffprobe_duration(out_path)
    if dur < 0.5:
        raise RuntimeError(f"Pocket audio terlalu pendek ({dur:.2f}s).")
    print(f"[pocket-cadangan] {os.path.basename(out_path)}: "
          f"voice=pocket-B-cadangan dur={dur:.2f}s LUFS={lufs:.2f}",
          file=sys.stderr)
    return out_path

def synth_pocket_cadangan_segments(items, out_dir):
    """Render semua segmen dengan Pocket B dalam SATU proses runner
    (satu load model per episode — bukan per segmen)."""
    jobs, raws = [], {}
    for it in items:
        raw = os.path.join(out_dir, f"{it['id']}.pocket-raw.wav")
        raws[it["id"]] = raw
        jobs.append({"id": it["id"], "text": it["text"], "out": raw})
    _pocket_job(jobs)
    for it in items:
        out_path = os.path.join(out_dir, f"{it['id']}.wav")
        try:
            shutil.copyfile(raws[it["id"]], out_path)
        finally:
            if os.path.exists(raws[it["id"]]):
                os.remove(raws[it["id"]])
        lufs = _polish13_pocket(out_path)
        print(f"[pocket-cadangan] {it['id']}.wav: LUFS={lufs:.2f}",
              file=sys.stderr)
    return out_dir

def synth_pocket_named(text, out_path, backend, seg_id="text"):
    """Sintesis SATU teks dengan salah satu voice bernama Jawa/Sunda
    (backend pocket-jawa-f/-m, pocket-sunda-f/-m). Output -10 LUFS.
    Untuk banyak segmen pakai synth_pocket_named_segments."""
    spec = POCKET_NAMED_VOICES[backend]
    raw = out_path + ".pocket-raw.wav"
    try:
        _pocket_job([{"id": seg_id, "text": text, "out": raw}],
                    prompt_key=spec["prompt_key"])
        shutil.copyfile(raw, out_path)
    finally:
        if os.path.exists(raw):
            os.remove(raw)
    lufs = _polish10_pocket_named(out_path)
    dur = _ffprobe_duration(out_path)
    if dur < 0.5:
        raise RuntimeError(f"Pocket audio terlalu pendek ({dur:.2f}s).")
    print(f"[{backend}] {os.path.basename(out_path)}: "
          f"voice={spec['label']} dur={dur:.2f}s LUFS={lufs:.2f}",
          file=sys.stderr)
    return out_path

def synth_pocket_named_segments(items, out_dir, backend):
    """Render semua segmen dengan SATU voice bernama Jawa/Sunda dalam
    SATU proses runner (satu load model per episode). Output -10 LUFS."""
    spec = POCKET_NAMED_VOICES[backend]
    jobs, raws = [], {}
    for it in items:
        raw = os.path.join(out_dir, f"{it['id']}.pocket-raw.wav")
        raws[it["id"]] = raw
        jobs.append({"id": it["id"], "text": it["text"], "out": raw})
    _pocket_job(jobs, prompt_key=spec["prompt_key"])
    for it in items:
        out_path = os.path.join(out_dir, f"{it['id']}.wav")
        try:
            shutil.copyfile(raws[it["id"]], out_path)
        finally:
            if os.path.exists(raws[it["id"]]):
                os.remove(raws[it["id"]])
        lufs = _polish10_pocket_named(out_path)
        print(f"[{backend}] {it['id']}.wav: LUFS={lufs:.2f}",
              file=sys.stderr)
    return out_dir

def synth_cloud(text, out_path):
    p = subprocess.run(
        [sys.executable, CLOUD_VO, "--text", text, "--out", out_path],
        capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"cloud_vo gagal: {(p.stderr or p.stdout)[-300:]}")
    return out_path

def _elevenlabs_quota():
    """Cek kuota ElevenLabs via helper (surrogate, tanpa baca kunci).
    Return dict(used, limit, remaining, reset_unix) atau raise."""
    p = subprocess.run(
        [sys.executable, ELEVENLABS_HELPER, "user"],
        capture_output=True, text=True, timeout=60)
    if p.returncode != 0:
        raise RuntimeError(f"elevenlabs user gagal: {(p.stderr or p.stdout)[-300:]}")
    sub = json.loads(p.stdout)["subscription"]
    used = int(sub["character_count"])
    limit = int(sub["character_limit"])
    return {"used": used, "limit": limit, "remaining": limit - used,
            "reset_unix": int(sub["next_character_count_reset_unix"])}

def synth_elevenlabs(text, out_path, voice_id=None, voice_name="Charlie"):
    voice_id = voice_id or ELEVENLABS_VOICE_ID
    if not os.path.exists(ELEVENLABS_HELPER):
        raise RuntimeError(f"Helper ElevenLabs tidak ada: {ELEVENLABS_HELPER}")
    out_dir = os.path.dirname(os.path.abspath(out_path))
    fd, tmp_mp3 = tempfile.mkstemp(suffix=".mp3", dir=out_dir)
    os.close(fd)
    try:
        p = subprocess.run(
            [sys.executable, ELEVENLABS_HELPER, "tts", voice_id,
             text, tmp_mp3, "--model", ELEVENLABS_MODEL],
            capture_output=True, text=True, timeout=180)
        if p.returncode != 0 or not os.path.exists(tmp_mp3):
            raise RuntimeError(
                f"ElevenLabs gagal: {((p.stderr or '') + (p.stdout or ''))[-300:]}")
        # mp3 -> wav 44100 mono + loudnorm -16 (kontrak output router = .wav)
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", tmp_mp3, "-ar", "44100",
             "-ac", "1", out_path],
            check=True)
        lufs = _loudnorm16(out_path)
        dur = _ffprobe_duration(out_path)
        if dur < 0.5:
            raise RuntimeError(f"ElevenLabs audio terlalu pendek ({dur:.2f}s).")
        print(f"[elevenlabs] {os.path.basename(out_path)}: voice={voice_name} "
              f"dur={dur:.2f}s LUFS={lufs:.2f}", file=sys.stderr)
        return out_path
    finally:
        if os.path.exists(tmp_mp3):
            os.remove(tmp_mp3)

def _loudnorm_to(path, target_lufs, true_peak=-1.5):
    """Normalisasi VO ke target LUFS arbitrer: loudnorm dua pass
    terukur (pola _loudnorm16_local, tanpa pre-filter backend lain)
    + trim gain iteratif ber-limiter sampai |LUFS - target| <= 0,3.
    Return LUFS akhir."""
    tp = f"{true_peak:g}"
    tgt = f"{target_lufs:g}"
    p = subprocess.run(
        ["ffmpeg", "-i", path, "-af",
         f"loudnorm=I={tgt}:TP={tp}:LRA=11:print_format=json",
         "-f", "null", "-"],
        capture_output=True, text=True)
    s = p.stderr
    i, j = s.find("{"), s.rfind("}")
    d = json.loads(s[i:j + 1])
    af = (f"loudnorm=I={tgt}:TP={tp}:LRA=11:"
          f"measured_I={d['input_i']}:measured_TP={d['input_tp']}:"
          f"measured_LRA={d['input_lra']}:measured_thresh={d['input_thresh']}:"
          f"offset={d['target_offset']}:linear=true")
    tmp = path + ".ln.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", path, "-af", af,
         "-ar", "44100", "-ac", "1", tmp],
        check=True)
    os.replace(tmp, path)
    lufs = _measure_lufs(path)
    for _ in range(4):
        if abs(lufs - target_lufs) <= 0.3:
            break
        gain = target_lufs - lufs
        tmp2 = path + ".g.wav"
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", path,
             "-af", f"volume={gain:.2f}dB,alimiter=limit=0.89:level=false",
             tmp2],
            check=True)
        os.replace(tmp2, path)
        lufs = _measure_lufs(path)
    return lufs

def _muse_voice_id(voice):
    """Voice Muse terkunci per gender: 'female' -> MAI_01; selain
    itu (default/pria) -> miles."""
    return MUSE_TTS_VOICE_FEMALE if voice == "female" \
        else MUSE_TTS_VOICE_MALE

def _split_sentences(text):
    """Pecah teks menjadi [(potongan, jeda_setelahnya_detik)] — PETA
    JEDA v3 (2026-11-01, riset datahub 1297 + penyesuaian berbasis
    ukur di hari yang sama). Satuan sintesis = klausa (satu panggilan
    TTS per potongan pendek), seperti v2 — usulan riset menaikkan
    satuan ke kalimat utuh DIPALSUKAN uji langsung: jeda internal
    TTS miles di koma/titik dua dalam satu panggilan terukur
    0,52-0,55 dtk. Yang berubah dari v2 adalah PETANYA (semua nilai
    turun rapat), pad trim (15 ms), dan jeda sapaan terkap:
    - Batas: . ! ? , : ; (tanda di antara digit — desimal/ribuan —
      BUKAN batas; gugus tanda seperti "..." / "?!" dipotong sekali
      di tanda terakhir gugus).
    - Fragmen <=1 kata digabung ke potongan berikutnya, jeda =
      tanda terakhir gabungan (semantik lama dipertahankan).
    - Sapaan pembuka: potongan pertama <= MUSE_GREETING_MAX_WORDS
      kata tetap satuan sendiri; jeda sisipan sesudahnya dibatasi
      maks MUSE_GREETING_MAX_PAUSE (0,12). TIDAK digabung ke
      kalimat berikutnya — uji 2026-11-01 membuktikan panggilan
      gabungan (sapaan + kalimat) diregangkan TTS secara patologis
      (24,12 dtk vs 9,43 dtk terpisah).
    - Potongan terakhir jeda 0. Jeda dari MUSE_PAUSE_AFTER v3."""
    raw, buf = [], ""
    t = text.strip()
    n = len(t)
    for i, ch in enumerate(t):
        buf += ch
        if ch not in MUSE_PAUSE_AFTER:
            continue
        if ch in ",." and i > 0 and t[i - 1].isdigit() \
                and i + 1 < n and t[i + 1].isdigit():
            continue  # desimal/ribuan, bukan batas
        nxt = t[i + 1] if i + 1 < n else ""
        if nxt and not nxt.isspace():
            continue  # di tengah gugus tanda / kata — bukan batas
        raw.append((buf.strip(), MUSE_PAUSE_AFTER[ch]))
        buf = ""
    if buf.strip():
        raw.append((buf.strip(), 0.0))
    units = []
    j = 0
    while j < len(raw):
        txt, pause = raw[j]
        while len(txt.split()) <= 1 and j + 1 < len(raw):
            j += 1
            txt = txt + " " + raw[j][0]
            pause = raw[j][1]
        units.append((txt, pause))
        j += 1
    # Sapaan pembuka <=3 kata: jeda sisipan sesudahnya DIBATASI
    # maks MUSE_GREETING_MAX_PAUSE. Sapaan TIDAK digabung ke
    # kalimat berikutnya dalam satu panggilan — terbukti di VM ini
    # (uji 2026-11-01): "Halo, Warga! Kenalin, ..." dalam SATU
    # panggilan miles menghasilkan 24,12 dtk, sedangkan dua
    # panggilan terpisah total 9,43 dtk; TTS meregangkan jeda
    # internal sesudah "!" secara patologis. Panggilan terpisah +
    # jeda sisipan terkap = perilaku yang benar.
    if len(units) >= 2 and \
            len(units[0][0].split()) <= MUSE_GREETING_MAX_WORDS:
        units[0] = (units[0][0],
                    min(units[0][1], MUSE_GREETING_MAX_PAUSE))
    if units:
        units[-1] = (units[-1][0], 0.0)
    return units


# Nama lama dipertahankan sebagai alias supaya import eksternal yang
# telanjur memakai _split_clauses tidak patah; semantiknya kini v3.
_split_clauses = _split_sentences

def _decode_pcm(path):
    """Decode file audio apa pun ke array int16 mono pada
    MUSE_TTS_SR via ffmpeg (s16le mentah ke stdout)."""
    from array import array
    p = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-f", "s16le",
         "-acodec", "pcm_s16le", "-ac", "1", "-ar", str(MUSE_TTS_SR),
         "-"],
        capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(
            f"ffmpeg decode gagal untuk {path}: "
            f"{p.stderr.decode()[-200:]}")
    a = array("h")
    a.frombytes(p.stdout)
    if sys.byteorder == "big":
        a.byteswap()
    return a

def _trim_pcm(a, rel=0.02, pad_ms=15):
    """Trim hening tepi PCM int16: ambang relatif 2% dari puncak, pad
    15 ms per sisi (PETA v3 2026-11-01: diturunkan dari 40 ms —
    overhead hening per batas kalimat menyusut 0,08 -> 0,03 dtk;
    keluaran CLI membawa ±0,4 dtk hening di tepi tiap potongan,
    tanpa trim ini jeda tanda baca tidak akurat)."""
    if len(a) == 0:
        return a
    peak = max(max(a), -min(a))
    if peak == 0:
        return a
    thr = peak * rel
    first = next(i for i, v in enumerate(a) if abs(v) > thr)
    last = next(i for i in range(len(a) - 1, -1, -1) if abs(a[i]) > thr)
    pad = int(pad_ms * MUSE_TTS_SR / 1000)
    return a[max(0, first - pad): min(len(a), last + pad + 1)]

def _muse_speak(chunk_text, voice_id, out_mp3):
    """SATU panggilan CLI tts speak untuk SATU potongan pendek.
    Voice diset EKSPLISIT (tidak pernah default CLI MAI_03) dan field
    `voice` pada JSON hasil diverifikasi: tidak sama dengan yang
    diminta = RuntimeError (GAGAL TERBUKA — substitusi tidak diterima
    diam-diam). Teks lewat stdin (--text-stdin), bukan argv."""
    p = subprocess.run(
        [MUSE_TTS_BIN, "speak", "--output", out_mp3, "--text-stdin",
         "--voice", voice_id, "--language", MUSE_TTS_LANG,
         "--timeout-secs", "120"],
        input=chunk_text.encode(), capture_output=True, timeout=180)
    if p.returncode != 0:
        raise RuntimeError(
            f"tts speak gagal (rc={p.returncode}): "
            f"{(p.stderr or p.stdout).decode()[-300:]}")
    try:
        res = json.loads(p.stdout.decode().strip().splitlines()[-1])
    except Exception:
        raise RuntimeError(
            f"keluaran tts speak tidak bisa dibaca: "
            f"{p.stdout.decode()[-200:]}")
    if not res.get("ok"):
        raise RuntimeError(f"tts speak ok=false: {res}")
    got = res.get("voice")
    if got != voice_id:
        raise RuntimeError(
            f"voice TERSUBSTITUSI: diminta {voice_id}, hasil {got!r} "
            f"— DITOLAK (gagal terbuka)")
    if not os.path.exists(out_mp3):
        raise RuntimeError(f"tts speak tidak menghasilkan {out_mp3}")
    return got

def synth_muse(text, out_path, voice="default", seg_id="text"):
    """Sintesis SATU teks dengan TTS bawaan Muse (backend muse-tts).
    voice='female' -> MAI_01; selain itu -> miles (TANPA pitch shift;
    aturan naskah fonetik miles — spasi tanpa tanda hubung — adalah
    urusan penyiapan naskah, teks di sini dipakai apa adanya).
    Teks dipecah per potongan pendek (klausa, peta jeda v3): tiap
    potongan satu panggilan CLI, di-trim tepinya (pad 15 ms), lalu
    dirakit dengan jeda sisipan v3. Hasil akhir dipoles ke -15 LUFS
    (target ±0,5)."""
    import wave
    from array import array
    voice_id = _muse_voice_id(voice)
    clauses = _split_sentences(text)
    if not clauses:
        raise RuntimeError("teks kosong untuk muse-tts")
    tmpdir = tempfile.mkdtemp(prefix="muse-tts-")
    try:
        full = array("h")
        for n, (ctext, pause) in enumerate(clauses):
            mp3 = os.path.join(tmpdir, f"chunk{n}.mp3")
            _muse_speak(ctext, voice_id, mp3)
            full.extend(_trim_pcm(_decode_pcm(mp3)))
            if pause > 0:
                full.extend(array("h", bytes(2 * int(pause * MUSE_TTS_SR))))
        with wave.open(out_path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(MUSE_TTS_SR)
            w.writeframes(full.tobytes())
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    lufs = _loudnorm_to(out_path, MUSE_TTS_LUFS)
    dur = _ffprobe_duration(out_path)
    if dur < 0.5:
        raise RuntimeError(f"Muse TTS audio terlalu pendek ({dur:.2f}s).")
    print(f"[muse-tts] {os.path.basename(out_path)}: voice={voice_id} "
          f"potongan={len(clauses)} dur={dur:.2f}s LUFS={lufs:.2f}",
          file=sys.stderr)
    return out_path

def synth_muse_segments(items, out_dir, voice="default"):
    """Render semua segmen episode dengan muse-tts. CLI dipanggil per
    potongan pendek per segmen (tidak ada model lokal yang dimuat,
    jadi tidak ada pola batch satu-load seperti Qwen/Pocket)."""
    for it in items:
        out_path = os.path.join(out_dir, f"{it['id']}.wav")
        synth_muse(it["text"], out_path, voice, it["id"])
    return out_dir

def main():
    ap = argparse.ArgumentParser(description="Router voice gabungan (lihat docstring).")
    ap.add_argument("--list", action="store_true", help="tampilkan status semua backend")
    ap.add_argument("--text", help="teks untuk disintesis")
    ap.add_argument("--segments", help="file JSON [{id,text}]")
    ap.add_argument("--backend", default="auto",
                    choices=["auto", "muse-tts", "elevenlabs", "cloud",
                             "piper", "qwen",
                             "pocket-cadangan", "pocket-jawa-f",
                             "pocket-jawa-m", "pocket-sunda-f",
                             "pocket-sunda-m"],
                    help="auto = muse-tts (bawaan Muse: cowok miles, cewek "
                         "MAI_01) dulu — DEFAULT AKTIF sejak 2026-10-31 "
                         "18:47 — lalu qwen (lokal cowok) -> piper untuk "
                         "cowok, atau elevenlabs (Jessica) -> piper untuk "
                         "cewek. muse-tts eksplisit = rute default aktif "
                         "yang sama. elevenlabs kini fallback/eksplisit. "
                         "pocket-cadangan = Pocket suara B, cadangan karakter "
                         "pendukung cowok (eksplisit saja, tidak pernah otomatis). "
                         "pocket-jawa-f/-m, pocket-sunda-f/-m = voice bernama "
                         "Jawa/Sunda (eksplisit saja, -10 LUFS)")
    ap.add_argument("--voice", default="default",
                    choices=["default", "female", "male-reserve",
                             "cewek-jawa", "cowok-jawa", "cewek-sunda",
                             "cowok-sunda"],
                    help="default = miles via muse-tts (default utama); "
                         "female = MAI_01 via muse-tts (default cewek); "
                         "Charlie/Jessica (elevenlabs) kini fallback; "
                         "male-reserve = Pocket suara B "
                         "(cadangan karakter pendukung cowok, diarahkan ke "
                         "--backend pocket-cadangan); cewek-jawa / cowok-jawa / "
                         "cewek-sunda / cowok-sunda = voice bernama Pocket "
                         "Jawa/Sunda (diarahkan ke backend pocket-* padanannya, "
                         "eksplisit saja, -10 LUFS)")
    ap.add_argument("--out", help="file wav output (mode --text)")
    ap.add_argument("--out-dir", help="direktori output (mode --segments)")
    args = ap.parse_args()

    if args.list:
        for name, info in BACKENDS.items():
            print(f"{name:10s} {info['status']}")
            print(f"{'':10s} publish={info['publish']} — {info['note']}")
        return

    if not args.text and not args.segments:
        ap.error("butuh --text atau --segments (atau --list)")
    if args.backend in ("drat", "mms", "voicebox", "arbotts"):
        ap.error(f"backend {args.backend} DITOLAK untuk tayang (lihat --list)")
    if args.backend == "qwen" and args.voice == "female":
        ap.error("backend qwen adalah suara PRIA (speaker indonesian_speaker) — "
                 "tidak boleh untuk --voice female; routing cewek tidak berubah "
                 "(Jessica -> Piper)")
    if args.backend == "pocket-cadangan" and args.voice == "female":
        ap.error("backend pocket-cadangan adalah suara COWOK (cadangan "
                 "karakter pendukung) — tidak boleh untuk --voice female; "
                 "routing cewek tidak berubah (Jessica -> Piper)")
    # Voice bernama Jawa/Sunda: --voice <nama> selalu diarahkan ke
    # backend pocket-* padanannya; backend pocket-* yang dipilih
    # langsung dikanonkan ke nama voice-nya. Ketidakcocokan gender /
    # daerah antara --voice dan --backend DITOLAK (gagal terbuka).
    if args.voice in POCKET_VOICE_TO_BACKEND:
        _target = POCKET_VOICE_TO_BACKEND[args.voice]
        if args.backend not in ("auto", _target):
            ap.error(f"--voice {args.voice} hanya cocok dengan --backend "
                     f"{_target} (atau auto yang diarahkan ke sana), "
                     f"bukan --backend {args.backend}")
        args.backend = _target
    elif args.backend in POCKET_NAMED_VOICES:
        _spec = POCKET_NAMED_VOICES[args.backend]
        if args.voice == "male-reserve":
            ap.error("--voice male-reserve adalah Pocket suara B "
                     "(--backend pocket-cadangan), bukan voice bernama "
                     "Jawa/Sunda")
        if args.voice == "female" and _spec["gender"] == "male":
            ap.error(f"backend {args.backend} adalah suara COWOK "
                     f"({_spec['speaker']}) — tidak boleh untuk konteks "
                     f"--voice female")
        args.voice = _spec["voice"]
    if args.voice == "male-reserve":
        # --voice male-reserve adalah nama voice untuk suara cadangan B;
        # selalu diarahkan ke backend pocket-cadangan (eksplisit, tidak
        # pernah lewat rantai auto).
        if args.backend not in ("auto", "pocket-cadangan"):
            ap.error("--voice male-reserve hanya cocok dengan --backend "
                     "pocket-cadangan (atau auto yang diarahkan ke sana)")
        args.backend = "pocket-cadangan"

    if args.voice == "male-reserve":
        voice_name, voice_id = "PocketCadanganB", None
    elif args.voice in POCKET_VOICE_TO_BACKEND:
        voice_name = POCKET_NAMED_VOICES[
            POCKET_VOICE_TO_BACKEND[args.voice]]["label"]
        voice_id = None
    else:
        voice_name, voice_id = ELEVENLABS_VOICES[args.voice]

    def synth_one(text, out_path):
        if args.backend in ("auto", "muse-tts"):
            # DEFAULT AKTIF (owner 2026-10-31 18:47): muse-tts (bawaan
            # Muse) pemberhentian pertama. Cowok: miles -> Qwen lokal
            # -> Piper. Cewek: MAI_01 -> Jessica -> Piper (Qwen suara
            # pria, tidak masuk routing cewek).
            order = (["muse-tts", "qwen", "piper"] if args.voice == "default"
                     else ["muse-tts", "elevenlabs", "piper"])
        else:
            order = [args.backend]
        last_err = None
        for b in order:
            try:
                if b == "muse-tts":
                    return synth_muse(text, out_path, args.voice), b
                if b == "elevenlabs":
                    return synth_elevenlabs(text, out_path, voice_id, voice_name), b
                if b == "cloud":
                    return synth_cloud(text, out_path), b
                if b == "qwen":
                    return synth_qwen(text, out_path), b
                if b == "pocket-cadangan":
                    return synth_pocket_cadangan(text, out_path), b
                if b in POCKET_NAMED_VOICES:
                    return synth_pocket_named(text, out_path, b), b
                return synth_piper(text, out_path), b
            except Exception as e:
                last_err = e
                print(f"[{b}] gagal: {e}", file=sys.stderr)
        raise RuntimeError(f"semua backend gagal. Terakhir: {last_err}")

    if args.text:
        if not args.out:
            ap.error("--text butuh --out")
        path, used = synth_one(args.text, args.out)
        v = (voice_name if used == "elevenlabs"
             else f"muse-tts:{_muse_voice_id(args.voice)}"
             if used == "muse-tts"
             else "qwen3tts-lokal-pria" if used == "qwen"
             else "pocket-B-cadangan" if used == "pocket-cadangan"
             else POCKET_NAMED_VOICES[used]["label"]
             if used in POCKET_NAMED_VOICES
             else "piper")
        print(f"OK backend={used} voice={v} -> {path}")
        return

    # mode --segments: satu episode SATU voice (konsistensi).
    items = json.load(open(args.segments))
    os.makedirs(args.out_dir, exist_ok=True)
    total_chars = sum(len(it["text"]) for it in items)
    log = {"total_chars": total_chars, "quota": None, "segments": [],
           "fallback": None, "voice_requested": args.voice,
           "voice_name": voice_name}
    muse_auto = args.backend == "auto"
    eleven_ok = True
    if args.backend in ("qwen", "piper", "pocket-cadangan",
                        "pocket-jawa-f", "pocket-jawa-m", "pocket-sunda-f",
                        "pocket-sunda-m"):
        # Backend eksplisit diminta pemanggil: lewati ElevenLabs + preflight
        # kuota sepenuhnya (qwen = lokal cowok; piper = fallback manual;
        # pocket-cadangan = cadangan pendukung cowok; pocket-jawa-*/
        # pocket-sunda-* = voice bernama Jawa/Sunda).
        eleven_ok = False
        log["fallback"] = f"backend eksplisit: {args.backend} (tanpa ElevenLabs)"
        print(f"[backend] {log['fallback']}", file=sys.stderr)
    elif muse_auto or args.backend == "muse-tts":
        # DEFAULT AKTIF (owner 2026-10-31 18:23 + klarifikasi 18:47):
        # muse-tts (TTS bawaan Muse) adalah pemberhentian pertama —
        # ElevenLabs TIDAK dicoba di depan dan preflight kuota dilewati;
        # Jessica hanya fallback tengah untuk cewek.
        eleven_ok = False
        route = ("miles -> qwen -> piper" if args.voice == "default"
                 else "MAI_01 -> elevenlabs (Jessica) -> piper")
        log["fallback"] = (f"default aktif muse-tts ({route})" if muse_auto
                           else f"backend eksplisit muse-tts ({route})")
        print(f"[backend] {log['fallback']}", file=sys.stderr)
    else:
        try:
            quota = _elevenlabs_quota()
            log["quota"] = quota
            print(f"[quota] ElevenLabs: terpakai {quota['used']}/{quota['limit']} "
                  f"(sisa {quota['remaining']}), butuh episode ini {total_chars} karakter.",
                  file=sys.stderr)
            if quota["remaining"] < total_chars:
                eleven_ok = False
                log["fallback"] = (f"kuota tidak cukup: sisa {quota['remaining']} < "
                                   f"butuh {total_chars} — seluruh episode turun ke "
                                   f"rantai fallback "
                                   f"({'qwen lalu piper' if args.voice == 'default' else 'piper'})")
                print(f"[fallback] {log['fallback']}", file=sys.stderr)
        except Exception as e:
            print(f"[quota] cek kuota ElevenLabs gagal ({e}) — coba generate, "
                  f"fallback otomatis bila gagal.", file=sys.stderr)

    def synth_segment(it, backend):
        out_path = os.path.join(args.out_dir, f"{it['id']}.wav")
        if backend == "muse-tts":
            synth_muse(it["text"], out_path, args.voice, it["id"])
        elif backend == "elevenlabs":
            synth_elevenlabs(it["text"], out_path, voice_id, voice_name)
        elif backend == "qwen":
            synth_qwen(it["text"], out_path, it["id"])
        elif backend == "pocket-cadangan":
            synth_pocket_cadangan(it["text"], out_path, it["id"])
        elif backend in POCKET_NAMED_VOICES:
            synth_pocket_named(it["text"], out_path, backend, it["id"])
        else:
            synth_piper(it["text"], out_path)
        return out_path

    def render_episode(backend):
        """Render SELURUH episode dengan satu backend (konsistensi VO).
        Qwen/Pocket dirender batch: satu proses runner = satu load model."""
        res = {}
        if backend == "muse-tts":
            synth_muse_segments(items, args.out_dir, args.voice)
            for it in items:
                res[it["id"]] = "muse-tts"
        elif backend == "qwen":
            synth_qwen_segments(items, args.out_dir)
            for it in items:
                res[it["id"]] = "qwen"
        elif backend == "pocket-cadangan":
            synth_pocket_cadangan_segments(items, args.out_dir)
            for it in items:
                res[it["id"]] = "pocket-cadangan"
        elif backend in POCKET_NAMED_VOICES:
            synth_pocket_named_segments(items, args.out_dir, backend)
            for it in items:
                res[it["id"]] = backend
        else:
            for it in items:
                synth_segment(it, backend)
                res[it["id"]] = backend
        return res

    # Rantai episode. DEFAULT AKTIF (owner 2026-10-31 18:47): muse-tts
    # pemberhentian pertama — cowok: miles -> qwen -> piper; cewek:
    # MAI_01 -> elevenlabs (Jessica) -> piper. Rantai lama (elevenlabs
    # di depan: cowok -> qwen -> piper; cewek -> piper) hanya berlaku
    # bila ElevenLabs diminta eksplisit (--backend elevenlabs/cloud),
    # karena pada jalur itu eleven_ok yang berjalan lebih dulu.
    fallback_chain = (["qwen", "piper"] if args.voice == "default"
                      else ["piper"])
    if muse_auto or args.backend == "muse-tts":
        fallback_chain = (["muse-tts", "qwen", "piper"]
                          if args.voice == "default"
                          else ["muse-tts", "elevenlabs", "piper"])
    elif args.backend == "piper":
        fallback_chain = ["piper"]
    elif args.backend == "qwen":
        fallback_chain = ["qwen", "piper"]
    elif args.backend == "pocket-cadangan":
        # Suara cadangan diminta EKSPLISIT untuk karakter pendukung:
        # gagal = berhenti dan lapor, TIDAK diganti voice lain diam-diam,
        # dan voice ini tidak menjadi fallback bagi voice lain.
        fallback_chain = ["pocket-cadangan"]
    elif args.backend in POCKET_NAMED_VOICES:
        # Voice bernama Jawa/Sunda diminta EKSPLISIT: gagal = berhenti
        # dan lapor, TIDAK diganti voice lain diam-diam, dan voice ini
        # tidak menjadi fallback bagi voice lain.
        fallback_chain = [args.backend]

    results = {}
    if eleven_ok:
        failed = None
        for it in items:
            try:
                synth_segment(it, "elevenlabs")
                results[it["id"]] = "elevenlabs"
            except Exception as e:
                failed = (it["id"], str(e))
                break
        if failed:
            print(f"[fallback] elevenlabs gagal di segmen {failed[0]}: "
                  f"{failed[1]} — SELURUH episode di-render ulang via "
                  f"rantai fallback {' -> '.join(fallback_chain)} "
                  f"(konsistensi VO).", file=sys.stderr)
            log["fallback"] = (f"elevenlabs gagal di segmen {failed[0]}: "
                               f"{failed[1]}")
            results = {}
            eleven_ok = False
    if not eleven_ok:
        last_err = None
        for b in fallback_chain:
            try:
                results = render_episode(b)
                last_err = None
                break
            except Exception as e:
                last_err = e
                print(f"[fallback] backend {b} gagal render episode: {e} — "
                      f"turun ke backend berikutnya.", file=sys.stderr)
                log["fallback"] = ((log["fallback"] + " | ") if log["fallback"]
                                   else "") + f"{b} gagal: {e}"
                results = {}
        if last_err is not None:
            raise RuntimeError(
                f"semua backend episode gagal. Terakhir: {last_err}")
    for it in items:
        v = (voice_name if results[it['id']] == "elevenlabs"
             else f"muse-tts:{_muse_voice_id(args.voice)}"
             if results[it['id']] == "muse-tts"
             else "qwen3tts-lokal-pria" if results[it['id']] == "qwen"
             else "pocket-B-cadangan" if results[it['id']] == "pocket-cadangan"
             else POCKET_NAMED_VOICES[results[it['id']]]["label"]
             if results[it['id']] in POCKET_NAMED_VOICES
             else "piper")
        print(f"{it['id']}: backend={results[it['id']]} voice={v} -> "
              f"{os.path.join(args.out_dir, it['id'] + '.wav')}")
        log["segments"].append({"id": it["id"], "backend": results[it["id"]], "voice": v})
    with open(os.path.join(args.out_dir, "voice_log.json"), "w") as f:
        json.dump(log, f, indent=1)
    print(f"voice_log.json ditulis — fallback: {log['fallback'] or 'tidak ada'}")

if __name__ == "__main__":
    main()
