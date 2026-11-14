---
name: clipper-bot
description: Bot otomatis Divisi Freelancer & Clipper (Moderate) — riset campaign/jobs, kliping, penjadwalan posting via browser (IG Business Suite, TikTok Studio), posting Threads via konektor, panen link, dan submit campaign Ternak Klip. Audit-first, idempoten, dry-run default, gerbang approval owner.
---

# Clipper Bot — Divisi Freelancer & Clipper

Paket: `~/workspace/divisi/freelancer-clipper/bot/` (README.md di sana = acuan
operasi lengkap; peta halaman UI = `../page-map-posting.md`).

## Kapan dipakai
Setiap pekerjaan rantai clipper: riset campaign/jobs berkala, produksi klip
dari manifest, memasukkan jadwal ke scheduler native platform, memanen URL
tayang, dan submit link ke platform campaign — menggantikan sesi browser
agen manual per-post yang boros dan rapuh.

## Cara jalan
```bash
cd ~/workspace/divisi/freelancer-clipper/bot
PY=~/workspace/scratch/cliptest2/meta-venv/bin/python
xvfb-run -a $PY clipper_bot.py status
xvfb-run -a $PY clipper_bot.py research --live
xvfb-run -a $PY clipper_bot.py clip --manifest <manifest.json> --live
xvfb-run -a $PY clipper_bot.py schedule --platform ig|tiktok|threads --queue <antrean.json> [--live]
xvfb-run -a $PY clipper_bot.py harvest
xvfb-run -a $PY clipper_bot.py submit --adapter ternakklip [--live]
```

## Aturan yang ditegakkan (jangan dilonggarkan)
- Default dry-run; live butuh `--live` + `state/approval.json` (cakupan
  posting/submit dari persetujuan owner).
- Audit-first: baca daftar platform sebelum bertindak; jangan pernah
  mengulang item yang sudah terjadwal/tayang/ter-submit. Status ditulis
  atomik per item.
- Captcha/checkpoint = berhenti total jalur itu (exit 3); profil belum login
  = LOGIN-DIPERLUKAN (exit 2). Jangan paksa, jangan ganti selector membabi
  buta — perbarui `page-map-posting.md` + modul di hari yang sama.
- Plafon: IG 25 jadwal/hari; TikTok 15/hari ketat; Threads efektif 15/hari
  (fakta 429 di ±14 postingan/24 jam, 31 Okt 2026), jeda acak 15–30 menit.
- TikTok: jadwal yang sudah masuk TIDAK bisa diedit; pakai DRAF Studio yang
  ada, jangan unggah ulang. Kegagalan navigasi (ERR_ABORTED) tidak mengubah
  status item.
- Submit Ternak Klip: Tambah Link per URL lalu Submissions → Ajukan video;
  status TERSUBMIT hanya setelah nama/submission terlihat di daftar.
  Wefluence/Whop/TryBuzzer = BELUM-ADAPTER (jujur, jangan diklaim bisa).

## Syarat live yang masih terbuka (per 31 Okt 2026)
Profil persisten bot perlu login satu kali per platform: Meta
(`meta-profile`), TikTok (`tiktok-profile`), Ternak Klip Google
(`ternakklip-profile`). Threads siap live via konektor.
