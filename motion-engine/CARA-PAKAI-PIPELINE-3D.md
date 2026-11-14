# CARA PAKAI — video_pipeline_3d.py (pipeline video 3D satu perintah)

Satu perintah menjalankan seluruh rantai produksi video 3D three.js:
self-check WebGL → validasi storyboard → VO → probe → rekam frame-step
→ rakit → finalize → QA + laporan. Folder produksi ASLI tidak pernah
ditulis — semua kerja di salinan `<out-dir>/work/`.

## Perintah baku

```bash
cd ~/workspace/motion-video-projects/engine

# Produksi penuh (VO digenerate ulang dengan default terkunci muse-tts):
python3 video_pipeline_3d.py \
  --project <folder produksi> \
  --out-dir <folder hasil> \
  --naskah <naskah.json>

# Pakai VO yang sudah ada di folder proyek (vo/s{n}.wav + bed):
python3 video_pipeline_3d.py --project <folder produksi> --out-dir <folder hasil>

# Cek rencana saja (self-check + validasi, tanpa render):
python3 video_pipeline_3d.py --project <folder produksi> --out-dir <folder hasil> --dry-run

# Uji potongan (mis. 150 frame pertama):
python3 video_pipeline_3d.py --project <folder produksi> --out-dir <folder hasil> --frames 0-149

# Lanjutkan dari frame yang sudah terender (tahap rekam dilewati):
python3 video_pipeline_3d.py --project <folder produksi> --out-dir <folder hasil> --skip-record
```

`--project` boleh folder produksi atau langsung file `storyboard.json`.
`--naskah` = JSON segmen `[{id, text, gender?}]` (atau `{segments: [...]}`),
id harus cocok dengan segmen storyboard (`s1`, `s2`, ...).
`--recorders N` = recorder paralel tahap rekam (bawaan 2; sub-rentang
berbeda, aman — pola produksi terbukti).

## Yang dihasilkan di `<out-dir>`

- `<nama-proyek>.mp4` — MASTER final (1080×1920, target −15 LUFS)
- `<nama-proyek>-chat.mp4` — versi kirim chat (≤16 MB)
- `<nama-proyek>-cover.jpg` — cover
- `qa-report.json` + `qa-report.md` — hasil QA tertulis (selalu ada,
  juga saat gagal: tahap yang gagal tercatat)
- `probe/` stills probe · `qa-final/` stills final · `frames/` frame
  rekaman · `record-chunk*.log` log recorder

## Perilaku penting

- Gagal di tahap mana pun → berhenti dengan `[TAHAP x] GAGAL: <alasan>`
  dan exit 1. Tidak ada tahap yang dilewati diam-diam; yang tidak
  berlaku dicatat terbuka di laporan.
- Rekam terputus di tengah tidak mengulang dari nol: jalankan perintah
  yang sama lagi — recorder melewati frame yang sudah utuh.
- Tanpa blok `detailing` di storyboard, tampilan = produksi lama
  persis. Mengaktifkan detailing: tambah ke storyboard.json proyek:

```json
"detailing": {"aa": "fxaa", "camera": "curve", "smooth": true, "poseBlend": true}
```

(`aa: "smaa"` hanya bila DOF mati di config proyek; selain itu viewer
menurunkannya ke fxaa dan qa-report mencatat yang benar-benar aktif.)

- Audio terkunci: VO muse-tts (cewek MAI_01 / cowok miles) −15 LUFS
  di atas bed −34. Bila voice_log membuktikan fallback selain
  muse-tts, tahap VO GAGAL terbuka — memang disengaja.
- Proyek tanpa segmen VO (template ilustrasi bisu) didukung: tahap VO
  dilewati terbuka dan master keluar bisu, tercatat di laporan.
