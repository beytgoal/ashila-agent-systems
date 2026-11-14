# clipper-bot — Bot Otomatis Divisi Freelancer & Clipper

Dibangun 31 Okt 2026 atas perintah owner (19:34 WIB): satu script bot untuk
seluruh rantai kerja yang sudah pernah dilakukan divisi ini, berdasarkan
pemetaan halaman per platform di `../page-map-posting.md`.

## Rantai yang diotomatisasi

| Tahap | Perintah | Mesin |
|---|---|---|
| Riset campaign/jobs | `research` | snapshot datahub (dh.py) + status platform terverifikasi; output = snapshot + diff event saja |
| Kliping | `clip --manifest <file>` | driver rantai produksi: Invidious → faster-whisper → GeminiWeb2API → cutter v3.6 → QA ffprobe |
| Jadwal IG | `schedule --platform ig --queue <json>` | Playwright → Meta Business Suite (audit Content>Scheduled dulu) |
| Jadwal TikTok | `schedule --platform tiktok --queue <json>` | Playwright → TikTok Studio (audit daftar dulu; jadwalkan DARI DRAF bila ada) |
| Posting Threads | `schedule --platform threads --queue <json>` | threads-cli berwaktu, jeda acak 15–30 mnt, plafon efektif 15/hari, stop total saat 429 |
| Panen link | `harvest` | konektor IG/Threads + log bot → antrean submit |
| Submit campaign | `submit --adapter ternakklip` | Playwright → app.ternakklip.com (Tambah Link → Submissions → Ajukan video) |
| Status | `status` | ringkasan approval, antrean submit, adapter, event terakhir |

## Cara jalan

```bash
cd ~/workspace/divisi/freelancer-clipper/bot
PY=~/workspace/scratch/cliptest2/meta-venv/bin/python
xvfb-run -a $PY clipper_bot.py status
xvfb-run -a $PY clipper_bot.py research            # dry-run (snapshot tidak ditulis)
xvfb-run -a $PY clipper_bot.py research --live     # tulis snapshot + event diff
xvfb-run -a $PY clipper_bot.py schedule --platform tiktok --queue <file-antrean.json>          # dry-run: rencana saja
xvfb-run -a $PY clipper_bot.py schedule --platform tiktok --queue <file-antrean.json> --live   # eksekusi
xvfb-run -a $PY clipper_bot.py submit --adapter ternakklip --live
```

## Aturan keras yang ditegakkan kode

- **Default dry-run.** Live butuh `--live` DAN `state/approval.json` memuat
  cakupan (`posting`/`submit`) — gerbang manusia tetap di tangan owner.
- **Audit-first + idempoten.** Poster membaca daftar platform dulu; item yang
  sudah terjadwal/tayang/diajukan dilewati. Status antrean ditulis atomik
  per item selesai, jadi run terputus aman dilanjutkan.
- **Captcha/checkpoint/bot-check = berhenti total** di jalur itu (exit 3).
  Login wall tanpa sesi profil = `LOGIN-DIPERLUKAN` (exit 2). Tidak ada paksa.
- **Plafon platform** (config.json): IG 25 terjadwal/hari; TikTok ketat
  15/hari; Threads efektif 15/hari (fakta 429 pada ±14 postingan/24 jam,
  31 Okt 2026 — jauh di bawah angka dokumen 250).
- **TikTok terjadwal tidak bisa diedit** — bot tidak pernah mencoba menggeser
  jadwal yang sudah masuk; draf Studio dipakai ulang, bukan unggah duplikat.
- Kredensial tidak pernah ditulis ke file: sesi hidup di profil persisten
  per platform (`meta-profile`, `tiktok-profile`, `ternakklip-profile` di
  scratch); proxy egress dibaca dari env saat runtime.

## Syarat live per jalur (keadaan 31 Okt 2026 malam)

- **Threads**: siap live (konektor terautentikasi) — tunduk plafon efektif.
- **IG Business Suite**: kode selesai; profil bot (`meta-profile`) perlu
  login Meta SATU KALI sebelum run live pertama (blocker yang sama dengan
  meta-suite-scheduler.py). Sampai itu statusnya LOGIN-DIPERLUKAN.
- **TikTok Studio**: kode selesai; profil bot (`tiktok-profile`) masih kosong
  — perlu login TikTok @chinatech.id SATU KALI.
- **Submit Ternak Klip**: kode selesai; profil (`ternakklip-profile`) perlu
  Login with Google (akun Heru Febrian) SATU KALI. Antrean submit saat ini:
  3 item siap (7K slot 1 & 3 lengkap 3 platform; Pulkam slot 2 TikTok),
  16 item menunggu link tayang lengkap.
- **Wefluence/Whop/TryBuzzer**: adapter browser BELUM dibangun (submit ke
  sana pernah manual/diteliti) — `submit --adapter wefluence` menjawab
  BELUM-ADAPTER dengan jujur, bukan berpura-pura.

## State

`state/`: `approval.json` (gerbang), `submit_queue.json` (antrean submit per
campaign), `threads-log.json`, `clip-jobs.json`, `research-snapshot.json`,
`events.jsonl` (hanya perubahan keadaan), `debug-*/*.png` (screenshot saat
gagal). Semua tulis JSON atomik (tmp + os.replace + verifikasi baca ulang).
