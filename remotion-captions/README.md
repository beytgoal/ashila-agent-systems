# remotion-clip — Renderer Klip Remotion (ClipCaptions)

Mesin tipografi/subtitle BARU untuk pipeline clipping Divisi Freelancer &
Clipper, dibangun di atas skill `remotion-motion-graphics`. Menggantikan
langkah burn-in subtitle ASS pada cutter ffmpeg. Alur pipeline:

1. **ffmpeg tetap menyiapkan segmen** — potong + crop/facetrack dari video
   sumber menjadi segmen 720x1280 TANPA subtitle bakar (cutter `cutter_*.py`
   dengan `--no-subs`, atau potongan ffmpeg setara).
2. **tools/build-captions.py** membentuk caption JSON dari `words.json`
   hasil transkripsi (timing kata asli) — fallback SRT (kata dipecah merata).
3. **render-clip.mjs** merender segmen + caption menjadi mp4 final
   (karaoke kata-per-kata tersinkron waktu ucap).

## Aturan terkunci divisi (menang atas skill)

- Teks caption off-white `#F5F3EF`; kata aktif biru `#0064FF` + bobot 800.
  Tipografi warna hitam DILARANG.
- Animasi caption HANYA blur + fade. Dilarang translate/rise, bounce,
  spring, floating/oscillator pada elemen caption.
- Footage TANPA perlakuan: tanpa Ken Burns, grade, grain, transisi,
  watermark, atau gerakan buatan. Caption berlabuh di zona tengah
  vertikal (50% tinggi frame), maks 2 baris x 5 kata.
- Font: Plus Jakarta Sans (variable) via @font-face dari `public/fonts/`.

## Pakai

```bash
# 1) caption JSON dari words.json transkripsi
python3 tools/build-captions.py --words <words.json> --start <dtk> \
    --end <dtk> --out captions.json
#    atau fallback: --srt <part.srt>

# 2) render (segmen di luar public/ disalin otomatis ke public/)
node render-clip.mjs --input <segmen.mp4> --captions captions.json \
    --out <hasil.mp4> [--width 720] [--height 1280] [--fps 30]

# QA cepat sebelum render penuh (skill Step 5):
node tools/still.mjs <frame> out/frames/cek.png [captions.json] [segmen.mp4]
```

Render memakai `chrome-wrapper.sh` (Playwright Chrome for Testing 156).
JANGAN pakai `/opt/meta-chromium` (tidak bisa render di VM ini) dan JANGAN
`npx remotion browser ensure` (unduhan diblokir egress). `node_modules`
adalah symlink ke proyek pilot `~/workspace/scratch/anim2d/remotion`
(Remotion 4.0.539) agar tidak install ulang.

## Pilot

- Sumber: batch-9 `ceIQuc2419k.mp4`, klip_01 rentang 1.0–57.0 dtk.
- Footage: `public/footage-ceiqu-01.mp4` (crop tengah 608x1080 -> 720x1280,
  audio AAC utuh dari sumber).
- Caption: `pilot/captions-ceiqu-01.json` (14 cue, 118 kata, timing kata
  ASLI dari words.json transkripsi — bukan pecahan merata SRT).
- Hasil: `out/pilot-ceIQu-01.mp4`; frame verifikasi di `out/frames/`.
- Ulangi: `npm run pilot`

### Hasil verifikasi pilot (1 Nov 2026)

- ffprobe: h264 720x1280 @30fps, **1680 frame**, durasi 56,0 dtk persis,
  audio AAC ada dan berbunyi (volumedetect mean −24,2 dB, max −7,4 dB —
  level sama dengan sumber, tidak bisu).
- 5 frame hasil render (3/14/25/38/50 dtk) + 3 still pra-render diperiksa
  visual: karaoke sinkron (kata aktif biru #0064FF di semua titik sampel),
  blok maks 2 baris, tanpa overflow, tanpa teks hitam, posisi zona tengah
  konsisten. Teks kapital besar yang kadang tampak di frame adalah
  tipografi BAKAR milik video sumber sendiri, bukan lapisan kita.
- Kalibrasi dari QA still: fontSize 44px -> 38px dan maks 8 kata/cue
  (di `tools/build-captions.py`) agar cue kata-panjang tidak pecah 3 baris.
- Waktu render pilot: **750 dtk** (56 dtk video, concurrency 1). Percobaan
  concurrency 2 mati di tengah pada VM bersama ini — render produksi
  pakai concurrency 1 dan jalankan detached (`setsid nohup ... &`),
  pantau lewat log; sesi exec di VM ini punya tampilan FS yang bisa
  berbeda antar-sesi, jadi verifikasi file hasil dari sesi yang sama
  dengan yang meluncurkan render.
- /tmp adalah tmpfs 512MB: bundle webpack Remotion (~42MB/bundle) bisa
  memenuhinya — bersihkan `/tmp/remotion-webpack-bundle-*` sebelum
  render bila menumpuk.
