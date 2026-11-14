#!/usr/bin/env python3
"""Cutter modular v3.5 — potong klip vertikal 9:16 + subtitle karaoke gaya skill.

STYLE_SKILL: muse-motion-skills (~/workspace/custom-skills/motion-video/),
    style cinematic — grotesk hero Inter Bold, kata masuk stagger ~4f,
    maks 5 kata di layar sekaligus, satu kata hero per layar, warna aksen
    untuk kata yang sedang diucapkan.
    Perintah owner 27 Okt 2026 19:30 WIB: ke depan subtitle pakai skill ini.
    Koreksi owner 28 Okt 2026: entrance blur (deblur) skill WAJIB masuk —
    v2 baru font + karaoke, entrance-nya belum ada. v3 menambah entrance
    rise + deblur per kata (lihat blok transisi blur di bawah; rise DIHAPUS di v3.5).
    Aturan tetap owner yang DIPATUHI di sini:
    - TANPA transisi (skill §5 Whip diabaikan — cutter tidak pakai transisi).
    - TANPA watermark @nxrskyaa (skill §8 diabaikan).
    - VO tetap -16 LUFS: tidak relevan — klip tidak pakai VO sama sekali.
    - Outline hitam DIPAKAI untuk subtitle (aturan "outline dilarang" hanya
      untuk kinetic type serial di atas background solid; subtitle klip di
      atas footage bergerak WAJIB outline demi keterbacaan — gaya v1 ini
      sudah lolos review 35/50).
    - Warna aksen = biru elektrik #0064FF, SAMA dengan sorot kata kunci
      gaya kalbotau serial (motion_render.py, accent (0,100,255)).
    - TANPA gerakan buatan pada FOOTAGE (owner 27 Okt 2026) — rise/deblur
      v3 hanya pada TEKS subtitle, footage tidak disentuh sama sekali.

    - v3.6 (perintah owner 30 Okt 2026 12:53 WIB): DUA perubahan.
      (1) FACE TRACKING untuk podcast orang (flag --facetrack):
      "Gak ada video diam, ada face tracking jika itu podcast
      orang" — crop vertikal mengikuti wajah pembicara (MediaPipe
      FaceDetector lewat detect_plan.py; lintasan halus berkecepatan
      terbatas), menggantikan crop tengah statis yang menghilangkan
      wajah (batch 6 Peep Talk 4 klip gagal). Tanpa flag, perilaku
      v3.5 persis. Detail di blok Face tracking di bawah.
      (2) Subtitle PlayRes NATIF 1080x1920: s.d. v3.5 PlayRes masih
      162x288 sehingga layer subtitle dirender 6,67x lebih kasar
      dari output (terlihat low-res) dan outline 0.5 unit sebenarnya
      ~3,3 px. v3.6 PlayRes = resolusi output; geometri diskala
      x20/3 (layout identik), OUTLINE tetap 0.5 = 0,5 px hairline
      sebenarnya. Detail di blok PlayRes NATIF di bawah.

SATU perintah ffmpeg per klip:
    trim (-ss/-to) + center crop (lebar = ih*9/16, dibulatkan genap)
    + scale 720x1280 + burn subtitle dari ASS + libx264 veryfast crf 23 + AAC.

Subtitle karaoke (mode utama, butuh --words words.json dari
transcribe_chunked.py --word-timestamps):
    - File ASS, satu event per kata: event berisi SATU baris (maks 5 kata),
      kata yang sedang diucapkan diwarnai aksen biru, kata lain putih.
      Event kata ke-i berlaku [mulai kata-i, mulai kata-(i+1)) — event
      BERDAMPINGAN, tidak tumpang tindih, karena libass menumpuk event yang
      aktif bersamaan secara vertikal (bukan menimpa). Dalam satu saat hanya
    - v3: tiap event membawa entrance skill — rise 34px (5 unit ASS) +
      deblur blur 10->0 selama 18f (600 ms), via \move + \t(\blur).
      Posisi akhir entrance = layout default (tidak bergeser).
    - v3.1 (keputusan owner 28 Okt 2026 19:02 WIB): entrance HANYA di
      event kata PERTAMA tiap baris (prefix bila i == 0 di line_events);
      kata berikutnya dalam baris yang sama hanya ganti warna karaoke.
      Alasan: v3 per kata memicu ulang entrance tiap pergantian kata —
      pada kata cepat (event 0,12-0,26 dtk) baris jatuh 22 px + blur
      kembali terus-menerus, subtitle bergoyang/lembut. Per baris, baris
      masuk bersih sekali lalu diam sementara highlight biru berpindah.
      Mode fallback (plain_line_events) sudah sekali per chunk, tidak
      berubah.
    - v3.1 juga PINDAHKAN posisi subtitle ke TENGAH vertikal (koreksi
      owner 28 Okt 2026 ~19:03 WIB): posisi bawah-tengah ketutup UI
      platform (caption bawah ~25% frame + kolom tombol kanan di IG/FB
      Reels). MarginV 128 -> tepi bawah blok di 55,5% tinggi frame,
      pusat blok ~51-53%; MarginL/R 18 (~80 px) supaya tepi kanan teks
      maks. 640 px, tidak masuk kolom tombol kanan (~656 px). Detail
      di komentar MARGIN_* di bawah.
    - v3.2 (perintah owner 28 Okt 2026 19:15 WIB): entrance JUGA di
      kata pertama SETIAP KALIMAT, bukan hanya kata pertama tiap baris.
      Satu baris bisa berisi dua kalimat (ganti kalimat di tengah baris
      tidak dapat entrance di v3.1) dan satu kalimat bisa melintasi
      beberapa baris. Deteksi batas kalimat: kata SEBELUMNYA berakhir
      tanda baca akhir kalimat (. ! ? …) pada teks kata di words.json
      — lihat ends_sentence() di bawah. Validasi 28 Okt 2026 pada
      data uji (0-60 dtk): 100% ujung segmen SRT cocok dengan tanda
      baca di words.json (14/14), dan tanda baca menangkap 2 akhir
      kalimat di TENGAH segmen yang tidak tertangkap batas segmen —
      jadi batas segmen SRT adalah subset ketat dari sinyal tanda
      baca dan tidak dipakai (tidak menambah apa-apa). Satu kata yang
      sekaligus awal baris DAN awal kalimat hanya mendapat SATU prefix
      (prefix = i == 0 OR awal kalimat, bukan dijumlah).
    - v3.3 (perintah owner 28 Okt 2026 19:41 WIB): "Fontnya terlihat
      murahan, ganti font premium dan style font yang berbeda tiap
      aktifnya." Font dasar Inter DIGANTI Plus Jakarta Sans Bold
      (premium, modern, dirancang di Indonesia — geometris-humanis,
      jauh lebih berkarakter dari Inter yang netral). Kata AKTIF
      (karaoke) tampil dengan font BERBEDA, bukan cuma beda warna:
      Playfair Display Bold (serif editorial Didone) warna biru
      #0064FF, sementara kata non-aktif Plus Jakarta Sans Bold putih.
      Kontras sans-vs-serif membuat kata aktif langsung terlihat
      berbeda font/style-nya. Ukur ulang lebar baris (PIL, font
      ukuran 49 px): garis visual terlebar 560 px -> tepi kanan
      ~649 px simulasi (konservatif ~22 px; kalibrasi Inter v3.2:
      simulasi 646 px vs frame 624 px) — sama dengan envelope v3.2,
      jadi wrap 126 unit TIDAK diubah. Flag --base-font /
      --active-font / --active-italic untuk varian (alt: Poppins
      Bold + Playfair Display Bold Italic).
    - v3.4 (perintah owner 28 Okt 2026 20:03 WIB): owner memilih
      Kandidat A (Plus Jakarta Sans dasar + Playfair Display Bold aktif,
      upright — BUKAN kandidat B Poppins/italic) dan "Outlinenya terlalu
      tebal" / "Tipis saja setipis rambut". Outline hitam 2 -> 0.5
      (hairline): dengan ScaledBorderAndShadow: yes, 1 unit ASS =
      4,44 px di 720x1280, jadi Outline 2 = ~8,9 px (~18% tinggi huruf
      49 px) sedangkan 0.5 = ~2,2 px. Lihat konstanta OUTLINE di bawah;
      terverifikasi ter-render sebagai garis rambut di uji v3.4
      (bukan dibulatkan ke 0/1 oleh libass).
    - v3.5 (perintah owner 29 Okt 2026 19:56 WIB): animasi subtitle
      KESELURUHAN diganti — gaya oscillator mengambang (naik-turun/
      floating/bounce/rise) DILARANG. Entrance \move (rise 34px)
      DIHAPUS TOTAL dari v3-v3.4; yang tersisa HANYA transisi BLUR:
      teks muncul dengan deblur blur 10->0 selama 600 ms tepat di
      posisi layout default, diam di tempatnya — tanpa \move, tanpa
      \pos animasi, tanpa pop/bounce. Titik pemakaian prefix sama
      seperti v3.2 (awal baris + awal kalimat / chunk fallback);
      isi prefix kini BLUR_PREFIX saja. Lihat blok transisi blur di
      bawah (BLUR_MS / BLUR_START / BLUR_PREFIX).
      satu event aktif, jadi baris tampil sekali dengan kata aktif biru.
    - CATATAN: tag \\k standar TIDAK dipakai — uji 27 Okt 2026 membuktikan
      libass build ini mewarnai kata yang SUDAH terucap tetap aksen
      (kumulatif), bertentangan dengan spesifikasi "kata lain putih".
      Event per-kata memberi hasil yang diminta, terverifikasi per frame.
    - Baris: maks 5 kata, pecah juga bila jeda antar kata > 1,2 dtk.

Mode fallback (tanpa --words): segmen SRT diubah jadi event ASS polos
(baris maks 5 kata, durasi dibagi rata per kata) dengan gaya yang sama.

Flag --no-subs: potong TANPA membakar subtitle sama sekali — WAJIB untuk
sumber yang sudah punya subtitle bakar sendiri (Ardhianzy, Kelas Pikir,
Ruang Tunggu — intro ~60-90 dtk pertama saja), karena review 27 Okt 2026:
8 klip gagal akibat subtitle ganda; review 28 Okt 2026: 1 klip Ruang Tunggu
gagal karena subtitle bakar intro + subtitle cutter menumpuk.

Tanpa narasi baru: audio asli dipertahankan, subtitle hanya menampilkan
ucapan yang sudah ada di video.

Penggunaan:
    python3 cutter.py --video SRC.mp4 --srt SRC.srt --words words.json \\
        --clips "0-59,59-101,101-145" --outdir out/
    python3 cutter.py --video SRC.mp4 --srt SRC.srt \\
        --clips clips.json --outdir out/        # tanpa karaoke (fallback)
    python3 cutter.py --video SRC.mp4 --srt SRC.srt --no-subs \\
        --clips "0-59" --outdir out/             # sumber bersubtitle bakar

Keluar: out/<name>.mp4 per klip + ringkasan JSON (waktu, x-realtime, verifikasi).
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

OUT_W, OUT_H = 1080, 1920
PRESET, CRF, AUDIO_BITRATE = "medium", "18", "128k"
VERSION = "v3.6-hd-kalbotau"

# --- Margin eksplisit (perintah owner 28 Okt 2026, instruksi tambahan) ---
# Layout subtitle HARUS pakai padding/margin dari frame — blok subtitle
# tidak boleh menyentuh tepi frame. Nilai (unit ASS, PlayRes 162x288;
# 1 unit = 720/162 = 4,44 px horizontal, 1280/288 = 4,44 px vertikal):
#   MarginL/R = 18  -> ~80 px dari tepi kiri/kanan (v3: 11 -> ~48 px;
#                        dipersempit di v3.1 — lihat alasan di bawah)
#   MarginV   = 128 -> tepi BAWAH blok di 288-128 = 160 unit
#                        = 55,5% tinggi frame. Blok 1 baris (~13 unit
#                        incl. outline) pusatnya ~153 unit = 53%;
#                        blok 2 baris pusatnya ~147 unit = 51%.
#                        Jadi pusat blok SELALU di zona 50-55% tinggi
#                        frame (perintah owner 28 Okt 2026 ~19:03 WIB).
#                        (Awalnya 132 -> tepi bawah 156 unit; ukur
#                        frame 28 Okt 2026: blok 2 baris pusatnya
#                        48,3% — di bawah rentang 50-55% — jadi
#                        MarginV digeser 132 -> 128 supaya blok 1 DAN
#                        2 baris sama-sama masuk 50-55%.)
# POSISI TENGAH (koreksi owner 28 Okt 2026 ~19:03 WIB): subtitle TIDAK
# lagi di bawah-tengah — posisi bawah ketutup UI platform (di IG/FB
# Reels, ~25% bawah frame ditempati caption + nama akun + musik, dan
# sisi kanan ditempati kolom tombol aksi like/comment/share). Blok
# dipindah ke zona tengah vertikal (pusat ~50-55%), jelas di atas zona
# caption bawah (y > 960 px = 216 unit; blok berakhir di 156 unit =
# 693 px) dan tidak menyentuh kolom tombol kanan. MarginV bawah 18
# (v3) TIDAK lagi berlaku sebagai jangkar bawah — jangkar posisi kini
# MarginV 132 (tepi bawah blok) + Alignment 2. MOVE_Y diturunkan dari
# MarginV (PLAY_RES_Y - MARGIN_V = 156), jadi entrance \move berakhir
# di posisi yang sama dengan layout default — tanpa lompatan.
# (v3.5: \move DIHAPUS total — posisi subtitle kini MURNI layout
# default Alignment 2 + margin ini, tanpa override posisi apa pun.)
# MarginL/R 18 (bukan 11): batas wrap v3 (140 unit) mengizinkan tepi
# kanan teks sampai 670 px — MASUK ke zona kolom tombol kanan IG/FB
# (mulai ~656 px); garis terpanjang terukur v3 berakhir di 645 px
# (clearance cuma ~11 px). Kondisi owner terpenuhi ("bila baris
# terpanjang berisiko mencapai kolom tombol kanan, persempit lebar
# maksimum baris") -> wrap kini 126 unit = ~560 px, tepi kanan teks
# maks. 640 px (~16 px dari kolom tombol). Margin simetris supaya
# blok tetap terpusat (tengah wrap = tengah frame).
# --- PlayRes NATIF (v3.6, perintah owner 30 Okt 2026 12:53 WIB) ---
# s.d. v3.5 PlayRes masih 162x288 (warisan geometri 720p) sehingga
# layer subtitle dirender pada kisi koordinat 6,67x lebih kasar dari
# output 1080x1920 — teks terlihat low-res dan outline 0.5 unit
# sebenarnya = ~3,3 px. v3.6: PlayRes = NATIF output (1080x1920,
# 1 unit ASS = 1 px). Semua geometri diskala x20/3 dari nilai 162x288
# supaya layout TIDAK berubah: MarginL/R 18 -> 120, MarginV 128 ->
# 853, FontSize 11 -> 73, blur awal 10 -> 67. OUTLINE tetap 0.5 —
# pada PlayRes natif itu = 0,5 px, garis rambut sebenarnya (perintah
# owner: outline JANGAN tebal). Posisi blok tetap zona tengah
# 50-55%: tepi bawah blok di 1920-853 = 1067 px = 55,6% tinggi frame.
PLAY_RES_X, PLAY_RES_Y = 1080, 1920
MARGIN_L, MARGIN_R, MARGIN_V = 120, 120, 853

# --- Transisi subtitle: BLUR SAJA (v3.5, perintah owner 29 Okt 2026
# 19:56 WIB) ---
# Riwayat singkat: v3-v3.4 memakai entrance gaya skill Kinetic berupa
# rise 34px (tag \move naik 5 unit PlayRes) + deblur blur 10->0 selama
# 600 ms, diterapkan di kata pertama tiap baris + kata pertama tiap
# kalimat (mode karaoke) dan tiap chunk (mode fallback). Perintah
# owner 29 Okt 2026 19:56 WIB: animasi subtitle KESELURUHAN diperbaiki
# — DILARANG gaya oscillator mengambang (naik-turun / floating /
# bounce / rise), cukup transisi BLUR saja.
# Maka v3.5: tag \move DIHAPUS TOTAL. Tidak ada lagi animasi posisi
# pada subtitle dalam bentuk apa pun (tanpa \move, tanpa \pos yang
# dianimasikan, tanpa pop/bounce/skala). Teks dirender diam di posisi
# layout default (Alignment 2 + MarginL/R/V) sejak frame pertama;
# satu-satunya transisi adalah deblur: blur 10 -> 0 selama 600 ms
# (\blur10 + \t(0,600,\blur0)). Angka blur dan durasi SAMA persis
# dengan komponen deblur v3-v3.4, supaya perubahan perilaku murni
# 'rise hilang', bukan tuning ulang. Titik pemakaian prefix tidak
# berubah dari v3.2. Verifikasi 29 Okt 2026 (folder blur-only-test):
# render lama vs baru pada klip yang sama — versi lama bergeser
# vertikal selama entrance, versi baru diam (centroid teks konstan)
# sementara ketajaman naik blur->tajam.
BLUR_MS = 600            # durasi deblur 18f @ 30fps — sama dengan v3-v3.4
BLUR_START = 67          # v3.6: 10 unit @PlayRes288 -> 67 px @PlayRes1920 (proporsi sama)
BLUR_PREFIX = "{\\blur%d\\t(0,%d,\\blur0)}" % (BLUR_START, BLUR_MS)

# --- Gaya subtitle v3.3 (font premium, perintah owner 28 Okt 2026 19:41 WIB) ---
# PlayRes 162x288 = skala yang sama dengan v1 (FontSize 11 -> ~49 px efektif
# di 720x1280). Geometri ini sudah lolos review 35/50 pada v1.
# FONT DASAR (v3.3): "Plus Jakarta Sans" — font premium gratis (OFL,
# Google Fonts, dirancang tim desain Tokopedia di Indonesia), Bold via
# style Bold=1 (file variable [wght] di-install; fontconfig mengembalikan
# instance Bold dengan benar, terverifikasi fc-match). Menggantikan Inter
# (v2-v3.2) yang dinilai owner "terlihat murahan".
# FONT AKTIF (v3.3): "Playfair Display" Bold — serif editorial Didone
# (OFL, Google Fonts), warna biru #0064FF. Kata aktif dibedakan dengan
# KELUARGA FONT yang berbeda (serif vs sans), bukan cuma warna — terlihat
# jelas di frame. Varian alt: base "Poppins" Bold + aktif Playfair
# Display Bold Italic (flag --base-font/--active-font/--active-italic).
FONT_NAME = "Noto Sans"
ACTIVE_FONT_NAME = "Noto Sans ExtraBold"
ACTIVE_FONT_ITALIC = False
FONT_SIZE = 73
# OUTLINE (v3.4, perintah owner 28 Okt 2026 20:03 WIB): "Outlinenya
# terlalu tebal" / "Tipis saja setipis rambut" — Outline hitam v3.3 = 2
# TERLALU TEBAL. Dengan ScaledBorderAndShadow: yes dan PlayRes 162x288,
# 1 unit ASS = 1280/288 = 4,44 px pada render 720x1280, jadi Outline 2
# = ~8,9 px — hampir seperlima tinggi huruf (~49 px). v3.4: Outline 0.5
# = ~2,2 px, garis rambut. Nilai pecahan didukung libass (fixed-point);
# terverifikasi ter-render di uji v3.4 (bukan dibulatkan ke 0/1) — lihat
# subtitle-skill-v2.md §17-18. Bila suatu saat outline 0.5 terasa hilang
# di footage sangat terang/gelap, NAIKKAN BERTAHAP (0.75 / 1.0), jangan
# langsung kembali ke 2 — dan laporkan ke owner dulu.
OUTLINE = 0.5
# ASS memakai &HBBGGRR. Teks off-white #F5F3EF, aksen biru #0064FF.
# PERINTAH OWNER 1 Nov 2026: tipografi warna HITAM DILARANG — teks selalu
# putih (off-white) dengan outline HITAM hairline 0,5 supaya terbaca di
# footage terang maupun gelap (skema sama dengan cutter.py). Jangan
# kembalikan teks hitam gaya kalbotau.
TEXT = "&HEFF3F5"          # off-white #F5F3EF — teks putih, BUKAN hitam
ACCENT = "&HFF6400"       # biru #0064FF (0,100,255), sama dengan v3.4
OUTLINE_COLOUR = "&H000000"  # outline hitam hairline: kontras untuk teks putih
MAX_WORDS_PER_LINE = 5
GAP_SPLIT_S = 1.2  # jeda antar kata > ini -> baris baru

def build_ass_header():
    """Header ASS — dibangun dari FONT_NAME global (bisa diubah via flag
    --base-font sebelum render; lihat main())."""
    return """[Script Info]
ScriptType: v4.00+
PlayResX: {playx}
PlayResY: {playy}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: ClipSub,{font},{size},{text},{accent},{outlinec},&H00000000,1,0,0,0,100,100,0,0,1,{outline},0,2,{ml},{mr},{mv},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""".format(playx=PLAY_RES_X, playy=PLAY_RES_Y, font=FONT_NAME,
           size=FONT_SIZE, text=TEXT, accent=ACCENT, outlinec=OUTLINE_COLOUR,
           outline=OUTLINE, ml=MARGIN_L, mr=MARGIN_R, mv=MARGIN_V)


ASS_HEADER = build_ass_header()

SRT_RE = re.compile(
    r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*"
    r"(\d+):(\d+):(\d+)[,.](\d+)\s*\n(.*?)(?=\n\s*\n|\Z)",
    re.DOTALL,
)


def ts_to_s(h, m, s, ms):
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def ass_ts(sec):
    """Detik -> H:MM:SS.cc (format waktu ASS)."""
    sec = max(sec, 0.0)
    cs = int(round((sec - int(sec)) * 100))
    if cs == 100:
        sec = int(sec) + 1
        cs = 0
    sec = int(sec)
    return f"{sec // 3600}:{sec // 60 % 60:02d}:{sec % 60:02d}.{cs:02d}"


def parse_srt(path):
    """Kembalikan list (start, end, teks)."""
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    segs = []
    for m in SRT_RE.finditer(raw):
        start = ts_to_s(*m.group(1, 2, 3, 4))
        end = ts_to_s(*m.group(5, 6, 7, 8))
        text = " ".join(m.group(9).strip().splitlines()).strip()
        if text:
            segs.append((start, end, text))
    return segs


def load_words(path):
    """words.json dari transcribe_chunked.py --word-timestamps.

    Kembalikan list (start, end, kata) terurut waktu.
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    words = [(float(w["start"]), float(w["end"]), str(w["word"]))
             for w in data]
    words.sort(key=lambda x: x[0])
    return words


def escape_ass(text):
    return (text.replace("\\", "\\\\")
                .replace("{", "\\{").replace("}", "\\}"))


def group_lines(words):
    """Kata -> baris-baris (maks 5 kata; pecah bila jeda > 1,2 dtk)."""
    lines = []
    cur = []
    for w in words:
        if cur and (len(cur) >= MAX_WORDS_PER_LINE
                    or w[0] - cur[-1][1] > GAP_SPLIT_S):
            lines.append(cur)
            cur = []
        cur.append(w)
    if cur:
        lines.append(cur)
    return lines


def ends_sentence(word):
    """Kata mengakhiri kalimat? Tanda baca akhir (. ! ? …) di ujung teks
    kata di words.json — abaikan tanda kutip/kurung penutup yang menempel
    di belakangnya (mis. 'benar."' tetap akhir kalimat).

    Dipakai v3.2 untuk memberi entrance ke kata pertama SETIAP KALIMAT.
    Validasi 28 Okt 2026 (data uji 0-60 dtk): sinyal ini cocok 100%
    dengan ujung segmen SRT (14/14) DAN menangkap akhir kalimat di
    tengah segmen yang tidak tertangkap batas segmen — batas segmen
    adalah subset ketat, jadi tidak dipakai sebagai sinyal kedua.
    Keterbatasan yang diketahui: singkatan bertitik ("Dr.", "Rp.") bisa
    memicu entrance palsu; tidak ada di data uji, dan Whisper jarang
    menempelkan titik pada singkatan di words.json. Bila muncul, perbaiki
    dengan daftar pengecualian singkatan di sini.
    """
    w = word.rstrip('"\u201d\u2019)]')
    return bool(w) and w[-1] in ".!?…"


def line_events(line):
    """Satu baris kata -> event per kata (karaoke: hanya kata aktif biru).

    Event kata ke-i: [mulai kata-i, mulai kata-(i+1)) — event BERDAMPINGAN,
    tidak tumpang tindih. Ini penting: libass MENUMPUK event yang aktif
    bersamaan secara vertikal (bukan menimpa), jadi event yang overlap
    menghasilkan 2-4 salinan baris yang sama di layar (terbukti di uji
    render pertama: 4 salinan "Pernah nggak kamu menunggu sebuah").
    Dengan event berdampingan, dalam satu saat hanya SATU event yang aktif:
    baris tampil sekali, kata yang sedang diucapkan biru, kata lain putih.
    Kata terakhir event-nya berakhir di akhir baris.
    """
    events = []
    line_end = line[-1][1]
    texts = [escape_ass(w[2]) for w in line]
    n = len(line)
    for i, (ws, we, _w) in enumerate(line):
        if i + 1 < n and line[i + 1][0] > ws:
            end = line[i + 1][0]
        elif i + 1 >= n:
            end = line_end
        else:
            # Kata berdurasi nol / start sama dengan kata berikut (artefak
            # Whisper word timestamps): JANGAN pakai line_end — itu membuat
            # event sepanjang sisa baris dan menumpuk dengan event kata
            # berikutnya sehingga subtitle tampil ganda (terbukti batch 4
            # C1 c02/c03/c06, 28 Okt 2026). Pakai akhir kata sendiri
            # (+ epsilon 40 ms agar event tidak nol); tumpang tindih
            # dengan event berikut tinggal ~1 frame.
            end = max(we, ws + 0.04)
        parts = []
        for j, t in enumerate(texts):
            if j == i:
                # v3.3: kata AKTIF memakai font BERBEDA (serif Playfair
                # Display Bold) + warna aksen biru — bukan cuma beda warna.
                # \i1 bila varian italic aktif (flag --active-italic).
                tag = ("\\fn%s\\i1" % ACTIVE_FONT_NAME if ACTIVE_FONT_ITALIC
                       else "\\fn%s" % ACTIVE_FONT_NAME)
                parts.append("{%s\\c%s&}%s" % (tag, ACCENT, t))
            else:
                # v3.3: kata non-aktif font dasar premium + putih. Setiap
                # kata membawa override \fn + \c sendiri supaya state
                # tidak bocor antar kata (override ASS berlaku sampai
                # diubah; tiap event mulai fresh dari style).
                parts.append("{\\fn%s\\c%s&}%s" % (FONT_NAME, TEXT, t))
        # v3.2 (perintah owner 28 Okt 2026 19:15 WIB): entrance rise +
        # deblur di event kata PERTAMA tiap baris (i == 0) DAN di kata
        # pertama SETIAP KALIMAT — yaitu kata yang kata SEBELUMNYA
        # mengakhiri kalimat (ends_sentence). Satu kata yang sekaligus
        # awal baris DAN awal kalimat hanya mendapat SATU prefix (OR,
        # bukan dijumlah). Kata lain dalam baris yang sama TIDAK
        # membawa prefix — hanya ganti warna karaoke.
        # Alasan: v3.1 hanya memberi entrance di awal baris; sebuah
        # baris bisa berisi dua kalimat, dan ganti kalimat di tengah
        # baris tidak mendapat entrance. Per baris + per kalimat,
        # setiap pergantian kalimat masuk bersih dengan blur 600 ms
        # sementara barisnya sendiri tidak bergerak.
        # v3.5: prefix kini BLUR_PREFIX — deblur saja, TANPA \move/rise
        # (perintah owner 29 Okt 2026 19:56 WIB; oscillator dilarang).
        prefix = (BLUR_PREFIX
                  if i == 0 or (i > 0 and ends_sentence(line[i - 1][2]))
                  else "")
        events.append((ws, end, prefix + " ".join(parts)))
    return events


def plain_line_events(start, end, text):
    """Fallback tanpa word timestamps: segmen SRT -> baris maks 5 kata,
    durasi segmen dibagi rata per kata (bukan karaoke, gaya sama)."""
    words = text.split()
    if not words:
        return []
    n = len(words)
    dur = max(end - start, 0.1)
    per = dur / n
    events = []
    for i in range(0, n, MAX_WORDS_PER_LINE):
        chunk = words[i:i + MAX_WORDS_PER_LINE]
        s = start + i * per
        e = start + min(i + len(chunk), n) * per
        # v3.1: entrance sekali per chunk (= sekali per baris, konsisten
        # dengan aturan per-baris mode karaoke) — tiap chunk satu event,
        # jadi prefix di sini memang hanya sekali per baris.
        # v3.2: aturan "entrance di awal kalimat" TIDAK diterapkan di
        # mode fallback — satu event chunk tidak punya kata-per-kata,
        # jadi ganti kalimat di tengah chunk tidak bisa di-entrance
        # terpisah. Mode fallback hanya dipakai bila tidak ada
        # --words; pipeline produksi selalu memakai --word-timestamps.
        # v3.5: prefix di sini juga BLUR_PREFIX (blur saja, tanpa \move).
        events.append((s, e, BLUR_PREFIX + escape_ass(" ".join(chunk))))
    return events


def write_ass(events, path):
    with open(path, "w", encoding="utf-8") as f:
        f.write(ASS_HEADER)
        for s, e, text in events:
            f.write(f"Dialogue: 0,{ass_ts(s)},{ass_ts(e)},ClipSub,,0,0,0,,"
                    f"{text}\n")


def build_ass_for_clip(segs, words, start, end):
    """Event ASS untuk satu klip (waktu digeser ke 0).

    Kembalikan (events, n_words, mode): mode 'karaoke' bila words dipakai,
    'plain' bila fallback SRT, 'none' bila tidak ada subtitle di rentang.
    """
    if words is not None:
        clipped = [(max(s, start) - start, min(e, end) - start, w)
                   for s, e, w in words if e > start and s < end]
        if not clipped:
            return [], 0, "none"
        events = []
        for line in group_lines(clipped):
            events.extend(line_events(line))
        return events, len(clipped), "karaoke"
    clipped = [(max(s, start) - start, min(e, end) - start, t)
               for s, e, t in segs if e > start and s < end]
    if not clipped:
        return [], 0, "none"
    events = []
    for s, e, t in clipped:
        events.extend(plain_line_events(s, e, t))
    return events, 0, "plain"


def escape_sub_path(path):
    # Pola heatmap-clipper: absolut, backslash -> /, titik-dua di-escape
    # (':' memisahkan opsi filter, jadi ':' di nama file harus di-escape).
    return os.path.abspath(path).replace("\\", "/").replace(":", "\\:")


CROP_MODE = "center"

def build_vf(ass_path):
    # center: crop tengah vertikal (lebar = ih*9/16 genap, tinggi = ih),
    #   lalu scale ke OUT_W x OUT_H — SAMA dengan v3.4.
    # fitwidth: scale lebar penuh + pad vertikal hitam (klip fix batch 5,
    #   supaya subtitle bakar sumber tidak terpotong tepi; geometri 720p
    #   lama 720x405@437 -> di 1080p menjadi 1080x608@656).
    if CROP_MODE == "fitwidth":
        vf = f"scale={OUT_W}:-2,pad={OUT_W}:{OUT_H}:(ow-iw)/2:(oh-ih)/2:black"
    else:
        w = "trunc(ih*9/16/2)*2"
        vf = f"crop={w}:trunc(ih/2)*2:(iw-{w})/2:0,scale={OUT_W}:{OUT_H}"
    if ass_path:
        vf += f",subtitles='{escape_sub_path(ass_path)}'"
    # Klip asli 30fps (format 18) — kunci 30fps supaya render HD tidak jadi
    # 60fps (sumber 1080p ada yang 60fps) dan waktu encode tetap wajar.
    return vf + ",fps=30"


# --- Face tracking (v3.6, perintah owner 30 Okt 2026 12:53 WIB) ---
# "Gak ada video diam, ada face tracking jika itu podcast orang."
# Podcast orang WAJIB --facetrack: crop vertikal MENGIKUTI wajah
# pembicara, bukan crop tengah statis (batch 6 Peep Talk: 4 klip
# GAGAL review karena crop tengah cuma menangkap kursi kosong).
# Deteksi + lintasan dibangun detect_plan.py (MediaPipe FaceDetector;
# fallback OpenCV YuNet/Haar) yang dijalankan sebagai subprocess
# dengan interpreter venv-face — python3 sistem tidak punya
# mediapipe/cv2. Lintasan: sampel 2 fps, wajah dominan (skor lalu
# luas) + preferensi kontinuitas, smoothing median + eksponensial +
# batas kecepatan geser 0,30x lebar frame/dtk, plus histeresis
# kehilangan track 3 sampel (deteksi yang berkedip tidak menyeret
# crop). Yang bergerak adalah
# JENDELA CROP mengikuti subjeknya — bukan gerakan buatan pada
# footage (aturan owner 27 Okt 2026 tetap dipatuhi).
# Render: klip dipecah per segmen plan (crop_x konstan per segmen),
# satu ffmpeg per segmen, lalu concat demuxer -c copy. Bila plan
# gagal dibuat (venv tidak ada, detektor gagal, crop 9:16 tidak
# berlaku) -> JATUH ke crop tengah biasa dan dicatat di ringkasan.
# PERBAIKAN 31 Okt 2026 22:02 WIB (perintah owner): tracking kini
# DEFAULT-ON di SEMUA entry point cutter. Akar masalah batch 6/7:
# flag ini opt-in dan render massal (run-720.sh) hanya memberinya
# ke 2 dari 9 run, jadi mayoritas klip podcast tetap crop tengah
# statis. Matikan per run dengan --no-facetrack (materi non-orang).
# detect_plan.py juga diperluas jangkar BADAN (MediaPipe Pose
# Landmarker; fallback OpenCV HOG) untuk sampel tanpa wajah.
FACETRACK = True
_FT_FALLBACK_ERR = None
FACE_PYTHON = os.environ.get(
    "FACETRACK_PYTHON",
    os.path.expanduser("~/workspace/scratch/cliptest2/venv-face/bin/python"))
DETECT_PLAN = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "detect_plan.py")


def get_crop_plan(video, start, end, workdir):
    """Jalankan detect_plan.py; kembalikan (plan, info). Raise bila gagal."""
    os.makedirs(workdir, exist_ok=True)
    plan_path = os.path.join(workdir, "plan.json")
    frames_dir = os.path.join(workdir, "frames")
    cmd = [FACE_PYTHON, DETECT_PLAN, "--video", video,
           "--start", str(start), "--end", str(end),
           "--out", plan_path, "--frames-dir", frames_dir,
           "--log", os.path.join(workdir, "detect-log.json")]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError("detect_plan gagal: "
                           + (proc.stderr or proc.stdout)[-300:])
    with open(plan_path, encoding="utf-8") as f:
        data = json.load(f)
    shutil.rmtree(frames_dir, ignore_errors=True)
    return data["plan"], data["info"]


def facetrack_vf(ass_path, crop_w, crop_h, crop_x):
    vf = f"crop={crop_w}:{crop_h}:{crop_x}:0,scale={OUT_W}:{OUT_H}"
    if ass_path:
        vf += f",subtitles='{escape_sub_path(ass_path)}'"
    return vf + ",fps=30"


def cut_one_facetrack(video, segs, words, start, end, out_path, no_subs,
                      plan, plan_info):
    """Render per segmen crop plan lalu concat. Semantik pengembalian
    sama dengan cut_one: (elapsed, dur, rc, stderr, info)."""
    dur = end - start
    info = {"subtitle_mode": "none", "subtitle_words": 0, "subtitle_events": 0,
            "facetrack": {"backend": plan_info.get("backend"),
                          "body_backend": plan_info.get("body_backend"),
                          "segments": len(plan),
                          "samples_with_face": plan_info.get("n_with_face"),
                          "samples_with_body_anchor":
                              plan_info.get("n_body_anchor"),
                          "samples": plan_info.get("n_samples")}}
    crop_w = plan_info["crop_w"]
    crop_h = int(plan_info["src_h"]) // 2 * 2
    tmp_dir = out_path + ".ft_parts"
    os.makedirs(tmp_dir, exist_ok=True)
    parts = []
    t0 = time.perf_counter()
    for i, segp in enumerate(plan):
        s_abs, e_abs = start + segp["t0"], start + segp["t1"]
        part = os.path.join(tmp_dir, f"part_{i:03d}.mp4")
        tmp_ass = None
        if no_subs:
            vf = facetrack_vf(None, crop_w, crop_h, segp["crop_x"])
            info["subtitle_mode"] = "no-subs"
        else:
            events, n_words, mode = build_ass_for_clip(segs, words,
                                                       s_abs, e_abs)
            info["subtitle_words"] += n_words
            info["subtitle_events"] += len(events)
            if mode != "none":
                info["subtitle_mode"] = mode
            if events:
                tmp_ass = part + ".ass"
                write_ass(events, tmp_ass)
                vf = facetrack_vf(tmp_ass, crop_w, crop_h, segp["crop_x"])
            else:
                vf = facetrack_vf(None, crop_w, crop_h, segp["crop_x"])
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-ss", str(s_abs), "-to", str(e_abs), "-i", video,
            "-vf", vf,
            "-c:v", "libx264", "-preset", PRESET, "-crf", CRF,
            "-c:a", "aac", "-b:a", AUDIO_BITRATE,
            part,
        ]
        proc = None
        for _attempt in range(2):  # 1x ulangi: abort ffmpeg sesaat
            proc = subprocess.run(cmd, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True)
            if proc.returncode == 0:
                break
        if tmp_ass and os.path.exists(tmp_ass):
            os.remove(tmp_ass)
        if proc.returncode != 0:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return (time.perf_counter() - t0, dur, proc.returncode,
                    proc.stderr.strip(), info)
        parts.append(part)
    list_path = os.path.join(tmp_dir, "list.txt")
    with open(list_path, "w", encoding="utf-8") as f:
        for p in parts:
            f.write(f"file '{p}'\n")
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", list_path,
        "-c", "copy", out_path,
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True)
    elapsed = time.perf_counter() - t0
    shutil.rmtree(tmp_dir, ignore_errors=True)
    return elapsed, dur, proc.returncode, proc.stderr.strip(), info


def cut_one(video, segs, words, start, end, out_path, no_subs):
    """Satu klip, satu perintah ffmpeg. Kembalikan (detik, rc, stderr, info)."""
    global _FT_FALLBACK_ERR
    if FACETRACK and CROP_MODE == "center":
        try:
            plan, plan_info = get_crop_plan(
                video, start, end, out_path + ".facetrack")
            return cut_one_facetrack(video, segs, words, start, end,
                                     out_path, no_subs, plan, plan_info)
        except Exception as e:  # noqa: BLE001 — jatuh ke crop tengah
            _FT_FALLBACK_ERR = str(e)
            print(f"  [facetrack] GAGAL ({e}) — jatuh ke crop tengah")
    dur = end - start
    info = {"subtitle_mode": "none", "subtitle_words": 0, "subtitle_events": 0}
    if _FT_FALLBACK_ERR is not None:
        info["facetrack"] = {"fallback_center": _FT_FALLBACK_ERR}
        _FT_FALLBACK_ERR = None
    if no_subs:
        vf = build_vf(None)
        tmp_ass = None
        info["subtitle_mode"] = "no-subs"
    else:
        events, n_words, mode = build_ass_for_clip(segs, words, start, end)
        info["subtitle_mode"] = mode
        info["subtitle_words"] = n_words
        info["subtitle_events"] = len(events)
        if events:
            tmp_ass = out_path + ".clip.ass"
            write_ass(events, tmp_ass)
            vf = build_vf(tmp_ass)
        else:
            tmp_ass = None
            vf = build_vf(None)
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-ss", str(start), "-to", str(end), "-i", video,
        "-vf", vf,
        "-c:v", "libx264", "-preset", PRESET, "-crf", CRF,
        "-c:a", "aac", "-b:a", AUDIO_BITRATE,
        out_path,
    ]
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    elapsed = time.perf_counter() - t0
    if tmp_ass and os.path.exists(tmp_ass):
        os.remove(tmp_ass)
    return elapsed, dur, proc.returncode, proc.stderr.strip(), info


def probe(path):
    cmd = [
        "ffprobe", "-v", "error", "-show_entries",
        "stream=codec_type,codec_name,width,height",
        "-show_entries", "format=duration,size",
        "-of", "json", path,
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        return {"error": proc.stderr.strip()}
    return json.loads(proc.stdout)


def verify(path):
    """720x1280 + H.264 + audio AAC + durasi. Kembalikan dict hasil."""
    info = probe(path)
    if "error" in info:
        return {"ok": False, "error": info["error"]}
    v = [s for s in info["streams"] if s["codec_type"] == "video"]
    a = [s for s in info["streams"] if s["codec_type"] == "audio"]
    ok = bool(v and a)
    checks = {
        "ok": ok,
        "width": v[0].get("width") if v else None,
        "height": v[0].get("height") if v else None,
        "vcodec": v[0].get("codec_name") if v else None,
        "acodec": a[0].get("codec_name") if a else None,
        "duration_s": round(float(info["format"]["duration"]), 2),
        "size_mb": round(int(info["format"]["size"]) / 1e6, 1),
    }
    checks["ok"] = (
        checks["width"] == OUT_W and checks["height"] == OUT_H
        and checks["vcodec"] == "h264" and checks["acodec"] == "aac"
    )
    return checks


def parse_clips(spec):
    if spec.strip().startswith("[") or spec.endswith(".json"):
        data = json.load(open(spec)) if spec.endswith(".json") else json.loads(spec)
        clips = []
        for i, item in enumerate(data):
            clips.append({
                "name": item.get("name", f"clip_{i + 1:02d}"),
                "start": float(item["start"]),
                "end": float(item["end"]),
            })
        return clips
    clips = []
    for i, part in enumerate(spec.split(",")):
        s, e = part.strip().split("-")
        clips.append({"name": f"clip_{i + 1:02d}", "start": float(s), "end": float(e)})
    return clips


def main():
    global FONT_NAME, ACTIVE_FONT_NAME, ACTIVE_FONT_ITALIC, ASS_HEADER, CROP_MODE, FACETRACK
    ap = argparse.ArgumentParser(description="Cutter modular v2 (subtitle skill)")
    ap.add_argument("--video", required=True)
    ap.add_argument("--srt", required=True)
    ap.add_argument("--words", default=None,
                    help="words.json dari transcribe_chunked.py --word-timestamps "
                         "(mode karaoke); bila tidak ada, fallback SRT polos")
    ap.add_argument("--clips", required=True,
                    help='"0-59,59-101" atau file JSON [{name,start,end}]')
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--no-subs", action="store_true",
                    help="potong tanpa subtitle sama sekali (sumber yang sudah "
                         "punya subtitle bakar: Ardhianzy, Kelas Pikir)")
    ap.add_argument("--base-font", default=FONT_NAME,
                    help="font kata non-aktif (default: Plus Jakarta Sans)")
    ap.add_argument("--active-font", default=ACTIVE_FONT_NAME,
                    help="font kata aktif karaoke (default: Playfair Display)")
    ap.add_argument("--active-italic", action="store_true",
                    help="kata aktif italic (varian alt v3.3)")
    ap.add_argument("--crop-mode", default="center", choices=["center", "fitwidth"],
                    help="center: crop tengah vertikal (default v3.4); "
                         "fitwidth: scale lebar penuh + pad (klip fix batch 5)")
    ap.add_argument("--facetrack", dest="facetrack",
                    action="store_true", default=True,
                    help="crop vertikal mengikuti wajah+badan "
                         "pembicara (MediaPipe via detect_plan.py) — "
                         "DEFAULT AKTIF untuk podcast orang (perintah "
                         "owner 30 + 31 Okt 2026); hanya berlaku "
                         "dengan --crop-mode center")
    ap.add_argument("--no-facetrack", dest="facetrack",
                    action="store_false",
                    help="matikan face tracking (crop tengah statis) "
                         "— untuk materi non talking-head")
    args = ap.parse_args()

    FONT_NAME = args.base_font
    ACTIVE_FONT_NAME = args.active_font
    ACTIVE_FONT_ITALIC = args.active_italic
    CROP_MODE = args.crop_mode
    FACETRACK = args.facetrack
    if FACETRACK and CROP_MODE != "center":
        print(f"[cutter-{VERSION}] facetrack diabaikan: "
              f"crop-mode {CROP_MODE} bukan center")
        FACETRACK = False
    if FACETRACK:
        print(f"[cutter-{VERSION}] FACETRACK aktif (default; python "
              f"detektor: {FACE_PYTHON})")
    else:
        print(f"[cutter-{VERSION}] FACETRACK nonaktif "
              f"(--no-facetrack) — crop tengah statis")
    ASS_HEADER = build_ass_header()
    print(f"[cutter-{VERSION}] font dasar: {FONT_NAME} | font aktif: "
          f"{ACTIVE_FONT_NAME}{' italic' if ACTIVE_FONT_ITALIC else ''}")

    os.makedirs(args.outdir, exist_ok=True)
    segs = parse_srt(args.srt)
    print(f"[cutter-{VERSION}] SRT: {len(segs)} segmen dari {args.srt}")
    words = None
    if args.words:
        words = load_words(args.words)
        print(f"[cutter-{VERSION}] words: {len(words)} kata dari {args.words} "
              f"(mode karaoke)")
    elif not args.no_subs:
        print(f"[cutter-{VERSION}] tanpa --words: mode fallback SRT polos")
    if args.no_subs:
        print(f"[cutter-{VERSION}] --no-subs: subtitle TIDAK dibakar")
    clips = parse_clips(args.clips)
    print(f"[cutter-{VERSION}] {len(clips)} klip dari {args.video}")

    summary = []
    for c in clips:
        out = os.path.join(args.outdir, f"{c['name']}.mp4")
        print(f"[cutter-{VERSION}] {c['name']}: {c['start']:.0f}-{c['end']:.0f} dtk "
              f"(dur {c['end'] - c['start']:.0f} dtk) ...", flush=True)
        elapsed, dur, rc, err, info = cut_one(
            args.video, segs, words, c["start"], c["end"], out, args.no_subs)
        if rc != 0:
            print(f"  GAGAL rc={rc}: {err[:300]}")
            summary.append({"name": c["name"], "ok": False, "error": err[:300]})
            continue
        v = verify(out)
        x = dur / elapsed if elapsed > 0 else 0
        print(f"  selesai {elapsed:.1f} dtk ({x:.2f}x realtime), "
              f"subtitle {info['subtitle_mode']} "
              f"({info['subtitle_words']} kata, {info['subtitle_events']} event), "
              f"{v['width']}x{v['height']} {v['vcodec']}/{v['acodec']}, "
              f"{v['size_mb']} MB, verifikasi={'OK' if v['ok'] else 'GAGAL'}")
        summary.append({
            "name": c["name"], "ok": v["ok"], "path": os.path.abspath(out),
            "start": c["start"], "end": c["end"], "duration_s": dur,
            "render_s": round(elapsed, 1), "x_realtime": round(x, 2),
            "cutter_version": VERSION, **info,
            **{k: v[k] for k in ("width", "height", "vcodec", "acodec", "size_mb")},
        })

    summ_path = os.path.join(args.outdir, "summary.json")
    with open(summ_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    n_ok = sum(1 for s in summary if s.get("ok"))
    print(f"[cutter-{VERSION}] {n_ok}/{len(summary)} klip OK — ringkasan: {summ_path}")
    return 0 if n_ok == len(summary) else 1


if __name__ == "__main__":
    sys.exit(main())
