# Company Bot — Mesin Otomatisasi Moderate

Satu mesin bot untuk semua divisi dan pekerjaan perusahaan. Prinsipnya:

> **Bot memproses, agent mengevaluasi dan memperbaiki.**

Pekerjaan berpola tetap — polling, cek kesehatan layanan, membaca saldo, menghitung antrean, menjalankan validator, dan membandingkan ambang — dikerjakan skrip Python tanpa token Muse. Agent hanya membaca `digest.md`, mengevaluasi pengecualian, lalu memperbaiki skrip, konfigurasi, data, atau tugas yang bermasalah.

Alurnya mengikuti pipeline datahub:

```text
sumber → bot memeriksa → event hanya saat status berubah
       → dh.py index → digest.md → agent membaca, mengevaluasi, memperbaiki
```

## Status awal — 31 Oktober 2026

- Mesin: `~/workspace/bots/bot.py`
- Daemon loop: berjalan sebagai proses mandiri (PPID 1)
- Job aktif awal: 7
- Job kerangka/template: 7
- Mode awal: observasi; belum ada `action.on_fail` yang dipersenjatai
- Cron agent lama: belum dimatikan; migrasi dilakukan bertahap agar tidak ada celah pengawasan

## Perintah

Jalankan dari folder ini:

```bash
cd ~/workspace/bots

python3 bot.py list
python3 bot.py run-once
python3 bot.py run-once --job gemini-health
python3 bot.py loop
python3 bot.py start
python3 bot.py status
python3 bot.py digest
python3 bot.py stop
```

Makna perintah:

- `list` — tampilkan semua job dan status konfigurasinya.
- `run-once` — jalankan semua job aktif satu kali.
- `run-once --job ID` — jalankan satu job untuk pengujian.
- `loop` — jalankan loop di foreground.
- `start` — jalankan loop sebagai daemon double-fork.
- `status` — cek daemon dan status terakhir setiap job.
- `digest` — hasilkan/tampilkan ringkasan kecil untuk dibaca agent.
- `stop` — hentikan daemon loop.

## Struktur

```text
~/workspace/bots/
├── bot.py
├── README.md
├── jobs/
│   ├── _template.json
│   ├── infrastruktur.json
│   ├── data.json
│   ├── branding-promosi.json
│   ├── hunting-nft.json
│   └── trading.json
├── state/
│   └── <job-id>.json
├── events/
│   └── events-YYYYMMDD.jsonl
├── logs/
│   └── bot.log
├── digest.md
└── company-bot.service (opsional, contoh unit systemd user)
```

### State

`state/<job-id>.json` menyimpan status terakhir, nilai, waktu perubahan, jumlah kegagalan beruntun, serta riwayat aksi. Bot tidak perlu membaca riwayat percakapan atau log panjang untuk tahu apakah keadaan berubah.

### Event

Event hanya ditulis apabila:

1. status berubah (`ok → warn`, `warn → fail`, `fail → ok`, dan sebagainya); atau
2. status tidak-ok melewati masa pengingat/cooldown.

Event disimpan ke `events/events-YYYYMMDD.jsonl`. Transisi berarti juga di-index ke datahub melalui `dh.py index`. Kegagalan datahub tidak menjatuhkan bot.

### Digest

`digest.md` adalah satu-satunya ringkasan rutin yang perlu dibaca agent. Isinya:

- job yang sedang `warn` atau `fail`;
- sejak kapan keadaan itu terjadi;
- detail pendek;
- event terakhir;
- jumlah job ok dan yang perlu perhatian.

Agent tidak membaca seluruh log hanya untuk mengetahui keadaan normal.

## Jenis job

### `http`

Memeriksa URL dan kode status.

```json
{
  "id": "contoh-http",
  "division": "infrastruktur",
  "title": "Layanan contoh hidup",
  "type": "http",
  "url": "http://127.0.0.1:8081/v1/models",
  "expect_status": [200],
  "expect_substring": "gemini",
  "interval_s": 30,
  "timeout_s": 10,
  "cooldown_s": 1800,
  "enabled": true
}
```

`expect_substring` bersifat opsional.

### `process`

Memeriksa proses melalui `pgrep -f`.

```json
{
  "id": "contoh-proses",
  "division": "infrastruktur",
  "title": "Proses contoh hidup",
  "type": "process",
  "pattern": "proxy_fwd.py",
  "interval_s": 120,
  "enabled": true
}
```

Gunakan pola nama skrip/proses yang spesifik, bukan kata umum seperti `python`.

### `command`

Menjalankan perintah dan menilai exit code atau regex.

```json
{
  "id": "contoh-command",
  "division": "data",
  "title": "Validator contoh",
  "type": "command",
  "command": "python3 /home/user/workspace/divisi/data/bin/validasi_harian.py",
  "ok_codes": [0],
  "interval_s": 1800,
  "timeout_s": 120,
  "enabled": true
}
```

Opsional:

- `fail_if_regex` — paksa status fail jika output cocok.
- `ok_if_regex` — status ok hanya jika output cocok.

### `command_json`

Menjalankan perintah, membaca stdout sebagai JSON, mengambil angka pada path titik, lalu menerapkan ambang.

```json
{
  "id": "contoh-saldo",
  "division": "hunting-nft",
  "title": "Saldo contoh",
  "type": "command_json",
  "command": "perintah-yang-mengeluarkan-json",
  "path": "balance",
  "warn_below": 0.033,
  "interval_s": 1800,
  "enabled": true
}
```

Ambang yang didukung:

- `warn_below`
- `fail_below`
- `warn_above`
- `fail_above`

### `json`

Membaca file JSON lokal, baik mengambil satu nilai maupun menghitung item.

```json
{
  "id": "contoh-antrean",
  "division": "branding-promosi",
  "title": "Antrean contoh",
  "type": "json",
  "file": "/home/user/workspace/divisi/branding-promosi/serial/queue.json",
  "count_where": {
    "path": "episodes",
    "key": "status",
    "equals": "queued"
  },
  "warn_below": 1,
  "interval_s": 1800,
  "enabled": true
}
```

Tanpa `count_where`, gunakan `path` untuk mengambil nilai secara langsung.

## Cara divisi menambah pekerjaan

1. Pilih file pada `jobs/` sesuai slug divisi; buat file baru jika belum ada.
2. Salin contoh terdekat dari `jobs/_template.json`.
3. Ganti `id`, `division`, `title`, target, interval, dan ambang.
4. Biarkan `enabled: false` selama pengujian.
5. Uji sintaks dan satu job:

   ```bash
   python3 bot.py list
   python3 bot.py run-once --job <id>
   python3 bot.py status
   ```

6. Periksa hasil pada `state/<id>.json`, event, dan `digest.md`.
7. Setelah hasil terbukti benar, ubah menjadi `enabled: true`.
8. Daemon membaca konfigurasi pada proses start; setelah perubahan besar, restart daemon:

   ```bash
   python3 bot.py stop
   python3 bot.py start
   python3 bot.py status
   ```

ID job harus unik di seluruh perusahaan. Gunakan awalan domain bila berpotensi bentrok, misalnya `tmc-...`, `tba-...`, `hunting-...`.

## Aksi perbaikan otomatis

Job dapat diberi aksi terbatas:

```json
"action": {
  "on_fail": "perintah-restart-yang-aman",
  "after_fails": 2,
  "max_per_hour": 2,
  "cooldown_s": 600,
  "timeout_s": 120
}
```

Aksi hanya berjalan apabila:

- status bukan `ok`;
- kegagalan beruntun mencapai `after_fails`;
- cooldown sudah lewat;
- batas `max_per_hour` belum tercapai.

Jangan persenjatai aksi sebelum perintahnya terverifikasi aman dan idempotent. Untuk Gemini, supervisor lokal yang sudah ada tetap menjadi penyembuh utama; bot awalnya cukup mengamati agar tidak ada dua pengendali yang berebut memperbaiki layanan yang sama.

## Batas keamanan

Bot ini bukan pengganti keputusan agent/owner untuk:

- approval publikasi;
- login, captcha, OTP, atau pemulihan akun;
- keputusan harga trading live;
- tanda tangan atau pengiriman transaksi di luar gerbang dan cap yang sudah disetujui;
- penilaian kreatif final;
- perubahan strategi;
- error baru yang belum diketahui polanya.

Konfigurasi job dianggap tepercaya karena perintah shell berasal dari file konfigurasi perusahaan. Jangan masukkan perintah dari sumber eksternal atau teks yang belum ditinjau ke file job.

Token, kata sandi, dan kredensial tidak boleh ditulis ke file job, state, event, atau digest.

## Job aktif awal

| Job | Fungsi |
|---|---|
| `gemini-health` | GeminiWeb2API di port 8081 |
| `router9-health` | 9Router di port 20128 |
| `walletd-health` | walletd HTTP di port 18924; HTTP 501 dari root adalah tanda hidup normal |
| `forwarder-health` | proses `proxy_fwd.py` di port 18888 |
| `datahub-validasi` | `validasi_harian.py`: laporan divisi dan perubahan belum ter-index |
| `serial-queue` | jumlah episode serial berstatus `queued` |
| `elysium-balance` | saldo burner Elysium melalui `wd.py`; peringatan di bawah 0,033 tHYPE |

Hasil uji pertama dan keadaan saat dokumentasi dibuat tersedia di `digest.md`. Keadaan `warn`/`fail` pada digest adalah hasil evaluasi bot saat itu, bukan kegagalan mesin bot.

## Migrasi dari cron agent

Urutan migrasi yang aman:

1. Buat padanan job bot.
2. Jalankan berdampingan dan bandingkan hasilnya.
3. Pastikan event, state, digest, dan index datahub benar.
4. Persenjatai aksi bot hanya jika diperlukan dan terverifikasi.
5. Matikan cron agent lama untuk pekerjaan yang sama.
6. Catat migrasi ke datahub.
7. Simpan pola yang sudah terbukti sebagai skill perusahaan.

Target awal migrasi:

- `gemini-web2api-watchdog` → `gemini-health` + supervisor lokal;
- `tmc-monitor-paper` → skrip monitor divisi + job `command` TMC;
- `reset-mining-loop` → skrip mining lokal + digest/event;
- Hunting pickup dan claim-watch → skrip event-driven;
- validasi dan pembuatan ringkasan datahub → job `command` Divisi Data.

## Pemulihan setelah VM restart

Periksa:

```bash
cd ~/workspace/bots
python3 bot.py status
```

Jika daemon tidak jalan:

```bash
python3 bot.py start
python3 bot.py status
```

Contoh unit systemd user tersedia sebagai `company-bot.service`, tetapi jalur yang terverifikasi di lingkungan ini adalah daemon double-fork PPID 1 melalui `bot.py start`.
