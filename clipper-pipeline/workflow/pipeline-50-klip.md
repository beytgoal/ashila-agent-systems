# Pipeline Produksi 50 Klip/Hari — Divisi Freelancer & Clipper

Dibuat: 26 Okt 2026 17:57 WIB (perintah owner: "set pipeline").
Rumus: **tools kerja berat + agent jalan paralel + Ashila review**.

## 1. Tujuan
50 klip video vertikal per hari, dibagi dua jalur:
- **Klip campaign platform** (TryBuzzer, Wefluence) — prioritas, ada tenggat + bayaran.
- **Klip niche YouTube** (psikologi) — mengisi sisa kapasitas, untuk akun sosmed.

## 2. Arsitektur

```
Sumber → Download → Transkripsi → Highlight → Potong+Render → REVIEW (Ashila) → Posting/Submit
   (agent)    (tool)      (tool)       (tool)        (tool)          (Ashila)        (agent/browser)
```

- **Model alur: BULK APPROVAL + produksi H-1 (instruksi owner 30 Okt 2026 19:30 WIB).** Konten untuk besok WAJIB diproduksi hari ini; SATU sesi approval (08:00) menyetujui seluruh paket sekaligus — klip + platform tujuan + jadwal posting — dan persetujuan paket itu menjadi otorisasi tetap bagi run posting hari tersebut (09:09). TIDAK ada kartu per postingan di luar scope paket. Posting berjalan terjadwal di bawah persetujuan paket: TikTok penjadwalan native (Studio), IG penjadwalan native (konektor `--publish-at`), Threads + FB run berwaktu detached dengan jeda. Alur lama (produksi dan approval di hari tayang yang sama) dicabut karena membuat kartu approval muncul di jam posting dan posting jadi kejar-kejaran stok lama.
- **Style posting: CROSS-POSTING (instruksi owner 30 Okt 2026 20:19 WIB).** Paket berbentuk set video (target 20 video/hari); SETIAP video dalam paket yang disetujui tayang di SEMUA sosmed pada hari yang sama — Instagram, TikTok, Threads, Facebook (1 video yang sama → 4 platform). Model distribusi kuota per platform (IG 15 / TikTok 15 / FB 20 / Threads semua) DIBATALKAN. Konsekuensi: IG menerima 20 klip/hari — batas IG 15/hari (keputusan owner 28 Okt 2026) terlampaui oleh perintah cross-posting ini; plafon API IG 50/hari tetap batas keras. URL dari setiap platform dicatat per video, dan link postingan klip campaign WAJIB di-submit ke halaman campaign-nya (Ternak Klip) di hari yang sama setelah tayang.
- **Tools**: AI-Youtube-Shorts-Generator, mode lokal (`--language id`, faster-whisper large-v3). Tanpa watermark, tanpa biaya per klip.
- **Subtitle v2 (mulai batch 4, 28 Okt 2026):** cutter v2 + word timestamps — spesifikasi di §7.
- **Agent produksi**: beberapa agent jalan paralel, masing-masing pegang 1 batch = 1 sumber video (podcast 60 mnt ≈ 5–10 klip; video 15 mnt ≈ 5 klip). Jumlah agent final ditentukan hasil uji throughput (sedang berjalan, subagent).
- **Reviewer**: Ashila. Tidak ada klip yang tayang/submit tanpa lolos review.

## 3. Tahapan

| # | Tahap | Pelaku | Alat |
|---|-------|--------|------|
| 1 | Pilih sumber (ikut urutan §5) | Ashila | riset niche + brief campaign |
| 2 | Download sumber | agent | yt-dlp (lewat tool) — **WAJIB Full HD: format video terbaik s.d. 1080p + audio terbaik (JANGAN format 18/360p)** — aturan tetap 29 Okt 2026, lihat §10 |
| 3 | Transkripsi Bahasa Indonesia | tool | faster-whisper large-v3-turbo, `language="id"` eksplisit, `--word-timestamps` (words.json untuk subtitle karaoke v2) |
| 4 | Pilih highlight (momen viral, maks 60 dtk per klip) | tool | LLM ranking dari transkrip (highlight.py menegakkan batas keras 60 dtk — perbaikan review batch 3, 28 Okt 2026). **Status 30 Okt 2026 19:02 WIB: highlight otomatis AKTIF LAGI** — GeminiWeb2API dipasang ulang atas perintah owner, membatalkan penghapusan pagi yang sama dan keputusan seleksi manual 14:18 WIB (seleksi manual hanya jadi fallback bila layanan mati). Repo Sophomoresty/gemini-web2api v1.1.0 (commit 2bb988b) di `~/workspace/gemini-web2api`, mode anonim model `gemini-3.6-flash` (tanpa cookie), config host 127.0.0.1 port 8081, TIDAK didaftarkan ke 9Router — scope hanya highlight divisi ini. Persistensi: unit systemd user `gemini-web2api.service` + cron `gemini-web2api-watchdog` tiap 5 mnt (restart detached bila mati). Uji pemasangan ulang 30 Okt 19:05–19:10 WIB: prompt kecil dijawab benar (17×23=391); highlight.py pada transkrip batch 7 Zp9jQGYIjGA menghasilkan 10/10 klip valid (durasi 36,9–57,7 dtk, 4/10 tumpang tindih pilihan manual — konvergensi wajar) |
| 5 | Potong + render vertikal 9:16 + subtitle | tool | cutter v2 (ffmpeg, crop vertikal, subtitle karaoke ASS dari words.json; spesifikasi §7) |
| 6 | **Review** | **Ashila** | checklist §4 |
| 7 | Posting (niche) / submit (campaign) | agent/browser | sesuai aturan platform |

## 4. Review gate — checklist Ashila

Setiap klip dicek sebelum tayang/submit:
1. Hook 3 detik pertama kuat (menahan penonton).
2. Subtitle akurat, sesuai ucapan (perhatikan segmen campur Inggris — wajib proofread).
3. **Kualitas HD: output 1080x1920, tidak soft/pecah (sumber wajib Full HD, bukan 360p; aturan tetap 29 Okt 2026, lihat §10).**
4. **Footage BERGERAK nyata: tolak klip dari sumber podcast audio yang visualnya kartu sampul statis (cek beda frame di beberapa titik waktu sumber; kartu sampul diam sepanjang klip = GAGAL). Pelajaran 29 Okt 2026: 13 klip dari 2 podcast audio Satu Persen (MPruv425zm4 + 0csakNsGlZE) lolos review batch 4–5 padahal seluruh visualnya kartu sampul — semua ditarik dari semua antrean platform.**
5. **Khusus klip CAMPAIGN — standar produksi penuh (perintah tetap owner 29 Okt 2026, insiden wf01/wf02): klip campaign WAJIB dibuat dengan benar, TIDAK asal bikin. Syarat minimum: footage bergerak asli (materi resmi brief atau rekaman yang layak), audio asli/VO yang layak (BUKAN klip bisu), visual BUKAN slide screenshot statis, hook + subtitle + seluruh syarat brief terpenuhi. Bila materi brief tidak memungkinkan standar ini, JANGAN diproduksi asal-asalan — laporkan bahwa klip tidak bisa dibuat dengan layak. File klip campaign WAJIB dikirim ke owner untuk DILIHAT dulu sebelum opsi posting/submit apa pun ditawarkan. (Insiden: wf01/wf02 Wefluence = slide screenshot + teks tanpa audio, tayang di IG+TikTok 29 Okt sore atas persetujuan tenggat, owner menilai sampah dan memerintahkan hapus malam yang sama.)**
3. Audio utuh, **tanpa narasi baru** (narasi sudah ada dari videonya; narasi baru hanya bila brief campaign mensyaratkan).
4. Kepatuhan brief campaign: hashtag + kode verifikasi + mention + durasi min + aturan bahan.
5. Risiko hak cipta / reused content: klip harus transformatif (hook + headline + angle + subtitle + pacing + crop), bukan re-upload mentah.
6. Visual bersih: tanpa watermark tool, tanpa teks bertumpuk.

Lolos → antrean posting/submit. Tidak lolos → balik ke agent dengan catatan perbaikan.

## 5. Urutan sumber

**Campaign (prioritas):**
1. Wefluence — "Ajak Pemilik Usaha Pasang Iklan di Wefluence" (tenggat 29 Okt, budget 27%)
2. TryBuzzer — Hair Mask Sachet (Rp 8.000/1K)
3. TryBuzzer — RONI x Raditya Dika (Threads)
4. TryBuzzer — Herborist × Ibnu Jamil & Ririn Ekawati
5. Wefluence — Campaign Stihat (tenggat 10 Nov)
6. TryBuzzer — ARAH Coffee (After Hour + Quotes Relatable)

**Prioritas fokus & gerbang submit (perintah tetap owner 30 Okt 2026 20:40 WIB):** FOKUS UTAMA divisi ini adalah **campaign clipper berbayar** — itulah sumber uangnya; konten **niche berfungsi membangun akun** (jangka panjang), bukan prioritas penyelesaian. Urutan penyusunan paket SELALU campaign dulu, niche mengisi sisa slot. **Submit adalah GERBANG PENYELESAIAN rantai** (produksi → review → approval → posting → **SUBMIT**) — bukan catatan kaki laporan: rantai klip campaign TIDAK dihitung selesai sebelum link tayangnya ter-submit ke platform campaign-nya **di hari yang sama** dan tercatat di ledger `submit-campaign-ledger.md`. Status **TAYANG-BELUM-SUBMIT = pekerjaan BELUM selesai**; run posting yang menyisakan status itu dinyatakan GAGAL dan wajib dikejar di hari yang sama. (Latar: 19 klip campaign batch 4 tertahan sejak 29 Okt tanpa tayang/submit sementara laporan berulang kali mencatat submit sebagai catatan bawah.)

**Niche (pengisi):** 5 prioritas riset `riset-niche-psikologi-youtube.md` — dr. Ryu Hasan (Otak vs Algoritma), Financial Anxiety (Ruang Tunggu), Stickman Story (Otak Suka Membuat Masalah), Morgan Housel (Sela Nalar), Dunning-Kruger (ardhianzy).

## 6. Aturan tetap

- **Konten clipper ≠ konten daily.** Konten daily (serial animasi psikologi) pakai VO baru (Piper id_ID). Konten clipper SELALU pakai narasi yang sudah ada dari videonya.
- **Campaign → ikuti brief campaign** (hook, hashtag, kode verifikasi, mention, durasi min, aturan bahan).
- **Non-campaign → tetap pakai narasi yang sudah ada dari videonya**, tanpa narasi baru (perintah owner 26 Okt 12:48 WIB, ditegaskan 17:59 WIB).
- **Bahan campaign HANYA dari aset resmi brief.** Bahan luar katalog dilarang (Ternak Klip).
- **Ternak Klip melarang AI/Opus Clip** — campaign itu jalur manual/template ffmpeg, bukan tool ini.
- Caption: 1 kalimat hook gaul + tepat 5 hashtag riset.
- Posting: 50 klip disebar 24 jam, variasikan ±15–30 mnt (jadwal kaku terbaca bot). Plafon: IG 50/hari, TikTok ~15/hari, FB 30 Reels/hari — jadi 50/hari adalah total produksi yang disebar ke semua akun, bukan 50 per akun.
- Video TikTok resmi perusahaan: **@chinatech.id** (bukan @ashilafiananda).
- **Tanpa gerakan buatan pada klip.** Segmen sumber yang gambarnya statis (ilustrasi diam video esai) dibiarkan apa adanya — tidak ditambah efek zoom/pan Ken Burns (keputusan owner 27 Okt 2026 20:01 WIB).
- **Video TIDAK BOLEH diam dan TIDAK BOLEH tanpa suara; tidak monoton (perintah tetap owner 29 Okt 2026 19:56 WIB).** Setiap video yang tayang wajib punya audio DAN visual bergerak. Sumber klip yang statis/bisu = DITOLAK di review (bukan ditambal). Konten produksi yang memang memakai gambar diam WAJIB ditampilkan CINEMATIC (gerakan sinematik yang hidup), bukan slide diam. Aturan ini memperjelas aturan gerakan buatan di atas: yang dilarang adalah menambal footage klip dengan gerakan palsu; yang diwajibkan adalah tidak ada video diam/bisu yang tayang.
- **Animasi subtitle: transisi BLUR saja (perintah tetap owner 29 Okt 2026 19:56 WIB).** DILARANG gaya oscillator mengambang (naik-turun/floating/bounce/rise) pada subtitle. Subtitle muncul dan hilang cukup dengan transisi blur, berlaku keseluruhan (cutter klip + subtitle produksi lain).
- **Podcast orang WAJIB face tracking (perintah tetap owner 30 Okt 2026 12:53 WIB).** Tidak ada video diam: crop vertikal podcast/talking-head mengikuti wajah pembicara (MediaPipe diizinkan owner) — crop tengah statis yang menghilangkan wajah = GAGAL review. Gerakan crop harus halus mengikuti subjek (bukan gerakan buatan acak).
- **Subtitle: outline hairline tipis + render resolusi NATIF (perintah tetap owner 30 Okt 2026 12:53 WIB).** Outline TIDAK boleh tebal; layer subtitle dirender pada PlayRes natif output (1080x1920 untuk HD) supaya teks tajam, tidak terlihat low-res/upscale.

## 7. Spesifikasi subtitle v2 — skill motion-video (mulai batch 4)

Perintah owner 27 Okt 2026 19:30 WIB: ke depan subtitle pakai skill
muse-motion-skills (`~/workspace/custom-skills/motion-video/`, style cinematic).
Batch 3 (produksi/2026-10-28) TETAP pakai cutter v1 — gaya baru berlaku
mulai batch 4. Laporan penerapan: `subtitle-skill-v2.md`.

- **Font (cutter v3.3, perintah owner 28 Okt 2026 19:41 WIB — "Fontnya
  terlihat murahan, ganti font premium dan style font yang berbeda tiap
  aktifnya"):** font dasar Inter Bold (v2–v3.2) DIGANTI **Plus Jakarta
  Sans Bold** — font premium gratis (OFL, Google Fonts, dirancang di
  Indonesia), geometris-humanis, jauh lebih berkarakter dari Inter yang
  netral. Kata AKTIF (karaoke) tampil dengan font BERBEDA, bukan cuma
  beda warna: **Playfair Display Bold** (serif editorial Didone, OFL,
  Google Fonts) warna biru `#0064FF` — kontras sans-vs-serif membuat
  kata aktif langsung terlihat berbeda font/style-nya. Ukuran efektif
  sama seperti v1 (FontSize 11 pada PlayRes 162x288, ~49 px di
  720x1280). Font terinstall di `~/.local/share/fonts/premium/`
  (PlusJakartaSans[wght].ttf + PlayfairDisplay[wght].ttf variable,
  Poppins-Bold/SemiBold.ttf statis untuk varian alt); sumber unduhan
  file TTF tersimpan di `cutter/fonts-v33/`. Varian alt (bukan default):
  base Poppins Bold + aktif Playfair Display Bold Italic — flag
  `--base-font / --active-font / --active-italic` di `cutter.py`.
  Detail + bukti frame: `subtitle-skill-v2.md` § v3.3.
- **Warna:** teks off-white `#F5F3EF`, outline hitam 2 (wajib demi
  keterbacaan di atas footage bergerak — aturan "outline dilarang" hanya
  untuk kinetic type serial di atas background solid, TIDAK berlaku di sini).
  **PENEGASAN OWNER 1 Nov 2026 19:52 WIB: tipografi warna HITAM DILARANG.**
  cutter_720.py + cutter_hd.py sempat menyimpang ke teks hitam gaya kalbotau
  (`TEXT=&H000000`, outline putih) — DIPERBAIKI hari yang sama: TEXT →
  `&HEFF3F5` (off-white), OUTLINE_COLOUR → `&H000000`, outline tetap 0,5
  hairline; ketiga cutter kini menghasilkan Style ASS identik. QA render
  lolos (frame: teks putih terbaca di footage gelap). Backup:
  `*.bak-20261101-prewhite`. Konsekuensi antrean: 33 klip Batch 8 yang sudah
  ter-render dengan teks hitam WAJIB di-render ulang dengan engine baru
  sebelum penjadwalan IG 4–5 Nov.
  Kata yang sedang diucapkan: aksen biru elektrik **`#0064FF`** — SAMA
  dengan sorot kata kunci gaya kalbotau serial.
- **Karaoke kata-per-kata:** satu event ASS per kata, satu baris maks
  5 kata di layar, pecah juga bila jeda antar kata > 1,2 dtk. Kata aktif
  biru, kata lain putih. Word timestamps dari
  `transcribe_chunked.py --word-timestamps` (file `words.json` per sumber;
  SRT tidak berubah). Tanpa `words.json`, cutter fallback ke event ASS
  polos dari SRT (gaya sama, tanpa karaoke).
- **Entrance — rise + deblur SEKALI PER BARIS (cutter v3.1, keputusan
  owner 28 Okt 2026 19:02 WIB):** v3 memberi entrance per kata — tiap
  pergantian kata memicu ulang entrance barisnya, jadi selama tuturan
  cepat subtitle bergoyang/lembut terus (event kata 0,12–0,26 dtk tidak
  sempat menyelesaikan entrance 600 ms; ketajaman 1189–1405 vs 1428
  saat settle, posisi ~19 px lebih rendah terus-menerus — temuan jujur
  uji v3). v3.1: HANYA event kata pertama tiap baris yang membawa
  prefix rise **34 px** + deblur **blur 10 → 0 selama 18f (600 ms
  @ 30fps)** via `\move` + `\t(\blur)`; kata berikutnya dalam baris
  yang sama hanya ganti warna karaoke. Baris masuk bersih sekali lalu
  diam sementara highlight biru berpindah kata per kata. Terverifikasi
  di klip uji: centroid Y baris C (kata cepat) 689,6 → 689,7 px konstan
  (0,1 px) sepanjang 4 pergantian kata; entrance terlihat sekali di
  awal tiap baris. Detail + bukti frame: `subtitle-skill-v2.md` § v3.1.
  Berlaku mulai batch 6 (batch 4–5 tetap v2, sudah lolos review —
  jangan disentuh).
- **Entrance di SETIAP AWAL KALIMAT (cutter v3.2, perintah owner 28 Okt
  2026 19:15 WIB):** v3.1 hanya memberi entrance di kata pertama tiap
  baris — satu baris bisa berisi dua kalimat (ganti kalimat di tengah
  baris tidak dapat entrance) dan satu kalimat bisa melintasi beberapa
  baris. v3.2: prefix entrance JUGA di kata pertama setiap kalimat,
  selain kata pertama tiap baris; satu kata yang sekaligus awal baris
  DAN awal kalimat hanya mendapat SATU prefix (OR, bukan dijumlah).
  Deteksi batas kalimat: kata sebelumnya berakhir tanda baca akhir
  kalimat (. ! ? …) pada teks kata di `words.json` (`ends_sentence()`
  di `cutter.py` — abaikan tanda kutip/kurung penutup yang menempel).
  Validasi pada data uji (0–60 dtk): 100% ujung segmen SRT cocok
  dengan tanda baca (14/14), dan tanda baca menangkap 2 akhir kalimat
  di TENGAH segmen yang tidak tertangkap batas segmen (batas segmen =
  subset ketat, tidak dipakai sebagai sinyal kedua). Terverifikasi di
  klip uji: **28 event ber-prefix (19 awal baris + 9 ganti kalimat
  tengah baris), 0 prefix ganda**; pada 4 ganti kalimat yang diperiksa
  frame-nya (`Seolah` 2,40; `Sudah` 9,64; `Ketika` 12,68; `Kamu` 23,04)
  teks lunak di +100 ms lalu tajam di +600 ms sementara posisi baris
  tidak bergerak. Catatan: singkatan bertitik ("Dr.", "Rp.") bisa
  memicu entrance palsu — tidak ada di data uji; bila muncul, tambah
  daftar pengecualian di `ends_sentence()`. Mode fallback SRT polos
  TIDAK berubah (satu event per chunk, ganti kalimat tengah chunk
  tidak bisa di-entrance terpisah). Detail + bukti frame:
  `subtitle-skill-v2.md` § v3.2. Berlaku mulai batch 6.
- **Font premium + style kata aktif berbeda (cutter v3.3, perintah owner
  28 Okt 2026 19:41 WIB):** kata non-aktif Plus Jakarta Sans Bold putih
  `#F5F3EF`; kata aktif Playfair Display Bold biru `#0064FF` (override
  `\fn` per kata di `line_events()` — tiap kata membawa override font +
  warna sendiri). Ukur ulang lebar baris (PIL, font 49 px, simulasi
  wrap libass 126 unit ≈ 560 px): garis visual terlebar 560 px → tepi
  kanan ~649 px simulasi (konservatif ~22 px — kalibrasi Inter v3.2:
  simulasi 646 px vs frame 624 px) — envelope sama dengan v3.2, jadi
  wrap 126 unit TIDAK diubah. Terverifikasi di klip uji: font premium
  ter-render benar (bukan fallback, glyph Indonesia lengkap); kata aktif
  TERLIHAT BERBEDA font/style-nya (serif vs sans) di semua frame yang
  diperiksa; tepi kanan terjauh 633 px (clear ~23 px dari kolom tombol
  kanan ~656 px), tepi kiri terdekat 87 px; pusat blok 52,0–54,6%
  (zona 50–55%); entrance per baris + per kalimat tetap bekerja
  (lunak di +100 ms, tajam di +600 ms, posisi tidak bergeser). Varian
  alt (Poppins Bold + Playfair Display Bold Italic, 15 dtk pertama)
  juga di-render sebagai pembanding — owner memilih. Detail + bukti
  frame: `subtitle-skill-v2.md` § v3.3. Berlaku mulai batch 6.
- **Outline setipis rambut (cutter v3.4, perintah owner 28 Okt 2026
  20:03 WIB — owner memilih Kandidat A + "Outlinenya terlalu tebal" /
  "Tipis saja setipis rambut"):** Outline hitam **2 → 0.5**. Dengan
  `ScaledBorderAndShadow: yes` dan PlayRes 162x288, 1 unit ASS = 4,44 px
  di 720x1280 — Outline 2 = ~8,9 px (~18% tinggi huruf 49 px, tampak
  seperti blok hitam di sekeliling huruf), Outline 0.5 = ~2,2 px garis
  rambut. Terverifikasi di klip uji: bandingkan frame yang sama t=5,00
  — v3.3 huruf dikelilingi halo hitam tebal, v3.4 hanya garis rambut
  tipis; teks tetap terbaca penuh di atas footage terang/gelap
  (t=0,80 / 5,00 / 13,00 / 35,50 diperiksa visual langsung, termasuk
  blok 3-baris di t=35,50). Nilai pecahan dirender libass dengan benar
  (tidak dibulatkan ke 0/1). Bila 0.5 suatu saat terasa hilang di
  footage ekstrem, naikkan bertahap (0.75 / 1.0) dan laporkan ke owner
  dulu — jangan langsung kembali ke 2. Detail + bukti frame:
  `subtitle-skill-v2.md` § v3.4. Berlaku mulai batch 6.
- **Animasi subtitle = TRANSISI BLUR SAJA (cutter v3.5 +
  v3.5-hd-kalbotau, perintah owner 29 Okt 2026 19:56 WIB — "DILARANG
  gaya oscillator mengambang (naik-turun/floating/bounce/rise), cukup
  transisi BLUR saja"):** bullet entrance v3.1/v3.2 di atas DIGANTI —
  komponen rise-nya dibuang. Prefix event awal baris + awal kalimat
  (karaoke) dan tiap chunk (fallback) kini hanya
  `{\blur10\t(0,600,\blur0)}`: teks muncul dengan deblur blur 10 → 0
  selama 600 ms tepat di posisi layout default dan DIAM di tempatnya.
  Tag `\move` dihapus total; tidak ada animasi posisi dalam bentuk
  apa pun. Angka blur + durasi sama persis dengan komponen deblur
  v3–v3.4; font, warna, highlight kata aktif, outline 0.5,
  posisi/margin, teks, dan timing event TIDAK berubah. Terverifikasi
  29 Okt 2026 (render lama vs baru pada klip yang sama; masker teks
  dari diff frame bersubtitle vs tanpa subtitle): centroid teks v3.4
  berayun 20,4 px (720p) / 31,2 px (1080p) selama entrance, v3.5
  konstan 0,5 px / 0,2 px sementara ketajaman naik ~2x (blur bekerja)
  dan posisi settle identik dengan v3.4. Detail + bukti:
  `subtitle-skill-v2.md` §19–20; folder uji
  `~/workspace/scratch/cliptest2/blur-only-test/`. Berlaku untuk
  semua render berikutnya (batch 6 belum masuk tahap potong saat
  perubahan ini dibuat, jadi otomatis memakai v3.5).
- **Face tracking WAJIB untuk podcast orang (cutter v3.6, perintah
  owner 30 Okt 2026 12:53 WIB):** "Gak ada video diam, ada face
  tracking jika itu podcast orang" — crop vertikal mengikuti wajah
  pembicara, menggantikan crop tengah statis. Sejak perbaikan
  31 Okt 2026 (lihat bullet khusus di bawah): tracking DEFAULT-ON
  di ketiga cutter (cutter.py, cutter_720.py, cutter_hd.py) dengan
  jangkar wajah + badan; flag `--no-facetrack` hanya untuk materi
  non-orang. Latar: batch 6 Peep Talk (podcast 2-shot wide)
  4 klip GAGAL review karena crop tengah cuma menangkap kursi
  kosong/tangan di tepi. Cara kerja: `detect_plan.py` (di folder
  cutter yang sama) mengekstrak frame sampel 2 fps, mendeteksi wajah
  dengan **MediaPipe FaceDetector** (Tasks API + model BlazeFace;
  dijalankan sebagai subprocess dengan venv
  `~/workspace/scratch/cliptest2/venv-face/` karena python3 sistem
  tidak punya mediapipe/cv2; fallback berantai OpenCV YuNet lalu
  Haar, selalu tercatat di plan), memilih wajah dominan (peringkat
  skor lalu luas + preferensi kontinuitas), lalu membangun lintasan
  pusat crop yang halus (median + smoothing eksponensial + batas
  kecepatan geser 0,30x lebar frame/dtk + histeresis kehilangan
  track 3 sampel supaya kedip deteksi tidak menyeret crop). Render
  per segmen plan (crop_x konstan per segmen) lalu concat. Yang
  bergerak adalah jendela crop mengikuti subjek — BUKAN gerakan
  buatan pada footage (aturan 27 Okt 2026 tetap berlaku). Bila plan
  gagal dibuat, cutter jatuh ke crop tengah dan mencatatnya di
  summary. Uji 30 Okt 2026 pada klip GAGAL batch 6
  `clip_6Qh3-jJ4z5w_05` (sumber 360p, render internal): versi crop
  tengah 0/5 frame berwajah (sesuai verdict review), versi
  facetrack **5/5 frame berwajah** (detektor + inspeksi visual
  strip). Bukti: `~/workspace/scratch/cliptest2/facetrack-test/`
  (strip-compare.jpg, verify-result.json, plan + log deteksi).
  Catatan lingkungan: mediapipe di VM ini butuh libEGL.so.1 +
  libGLESv2.so.2 yang tidak disediakan repo apt VM — salinan ekstrak
  .deb Ubuntu noble ada di `venv-face/egllibs/` dan detect_plan.py
  me-re-exec dirinya dengan LD_LIBRARY_PATH itu bila perlu.
- **Tracking wajah + BADAN, DEFAULT-ON di semua cutter (perbaikan
  31 Okt 2026, perintah owner 22:02 WIB — "pipelinenya tidak
  tracking wajah dan badan pembicara"):** Akar masalah batch 6/7:
  facetrack hanya flag opt-in `--facetrack` — run render massal
  720p (`run-720.sh`) hanya memberinya ke 2 dari 9 run (Peep Talk
  ft + VB1); 6 run mode-center lain jalan crop tengah, dan jalur
  pipeline niche batch 6 memakai `cutter.py` yang TIDAK punya
  facetrack sama sekali. Perbaikan: (a) `detect_plan.py` diperluas
  jangkar BADAN — sampel tanpa wajah kini diisi **MediaPipe Pose
  Landmarker** (model resmi `pose_landmarker_lite.task` di folder
  cutter; jangkar x = titik tengah bahu, fallback hidung bila bahu
  tidak meyakinkan), cadangan offline OpenCV HOG person detector.
  Badan HANYA mengisi sampel tanpa wajah — wajah tetap jangkar
  utama; mesin lintasan (histeresis hilang 3 sampel, kandidat
  persisten ≥2 sampel, smoothing median + eksponensial + batas
  geser 0,30x lebar frame/dtk) TIDAK berubah. Asal jangkar tiap
  sampel tercatat di detect-log (`anchor`: face/body/hold) dan di
  summary (`body_backend`, `samples_with_body_anchor`).
  (b) Tracking DEFAULT-ON di `cutter.py`, `cutter_720.py`,
  `cutter_hd.py` (blok facetrack kini juga ada di cutter.py);
  `--facetrack` tetap diterima (kompatibilitas run lama),
  penonaktif `--no-facetrack` hanya untuk materi non-orang;
  mode fitwidth tetap tidak memakai tracking. Subtitle v3.6
  TIDAK disentuh. Uji 31 Okt 2026 pada klip batch 6
  `clip_6Qh3-jJ4z5w_07` (Peep Talk, sumber 640x360, render
  cutter_720 TANPA flag): plan 120 sampel — 70 berwajah; 50
  sampel tanpa wajah dan ke-50-nya menemukan badan (43 sampel
  berjangkar badan); 54 segmen. Frame output tersebar
  (t=5,15,25,35,45,55): tracking **6/6 frame berisi pembicara**
  (4/6 wajah terdeteksi + 2/6 badan utuh berjangkar pose);
  baseline crop tengah klip yang sama **0/6 frame berwajah**
  (hanya meja/kursi/tangan di tengah ruangan). Bukti:
  `~/workspace/divisi/freelancer-clipper/facetrack-qa-2026-10-31/`
  (strip-compare.jpg, qa-tracking.json, qa-center.json, kedua
  render + summary). Backup pra-perbaikan:
  `*.bak-20261031-predefault` di folder cutter. Laporan lengkap:
  `laporan-perbaikan-facetrack-2026-10-31.md` (folder divisi ini).
- **Subtitle PlayRes NATIF + outline hairline sebenarnya (cutter
  v3.6, perintah owner 30 Okt 2026 12:53 WIB):** "outline jangan
  tebal dan jangan terlihat low resolusi" — s.d. v3.5 PlayRes ASS
  masih 162x288 (warisan geometri 720p) sehingga layer subtitle
  dirender pada kisi 6,67x lebih kasar dari output 1080x1920 dan
  outline 0.5 unit sebenarnya ≈ 3,3 px. v3.6: PlayRes = resolusi
  NATIF output (1080x1920 di cutter_hd; 720x1280 di cutter), semua
  geometri diskala proporsional (layout identik: FontSize 73/49,
  MarginL/R 120/80, MarginV 853/569, blur awal 67/44), dan OUTLINE
  tetap 0.5 — kini = 0,5 px hairline sebenarnya. Terverifikasi
  30 Okt 2026 (render uji 1080p yang sama, v3.5 vs v3.6): halo
  putih outline terukur median ~3 px (v3.5) -> ~1 px (v3.6) pada
  crop zoom 100% area subtitle; header ASS v3.6 terbaca
  PlayResX 1080 / PlayResY 1920. Bukti:
  `~/workspace/scratch/cliptest2/subtitle-v36-test/`
  (zoom-compare.png: atas v3.6, bawah v3.5).
- **Posisi TENGAH vertikal (cutter v3.1, koreksi owner 28 Okt 2026
  ~19:03 WIB):** subtitle TIDAK lagi di bawah-tengah — posisi bawah
  ketutup UI platform (di IG/FB Reels, ~25% bawah frame ditempati
  caption + nama akun + musik, sisi kanan ditempati kolom tombol aksi).
  Blok dipindah ke zona tengah: pusat blok **~50–55% tinggi frame**
  (tepi bawah blok 160 unit = 711 px = 55,5%; pusat 1 baris ~53%,
  2 baris ~51%, 3 baris ~50%), jelas di atas zona caption bawah
  (y > 960 px). Ini juga memenuhi aturan brief Ternak Klip "tanpa teks
  di 15% bawah". MarginV bawah 18 (v3) tidak lagi berlaku sebagai
  jangkar bawah — jangkar posisi kini MarginV 128 (tepi bawah blok) +
  Alignment 2; `MOVE_Y` diturunkan dari MarginV supaya entrance
  berakhir di posisi default. Awalnya dicoba MarginV 132 (tepi bawah
  156 unit) — blok 2 baris pusatnya 48,3%, di bawah rentang 50–55% —
  digeser ke 128 supaya blok 1 DAN 2 baris masuk rentang.
- **Margin/padding — blok subtitle tidak boleh menyentuh tepi frame
  (cutter v3.1):** MarginL/R **18** (≈80 px dari tepi kiri/kanan),
  MarginV **128** (lihat posisi tengah di atas). MarginL/R membatasi
  lebar wrap (maks 126 unit ≈ 560 px) — tepi kanan teks maks. 640 px,
  ~16 px dari kolom tombol kanan (~656 px). Alasan dipersempit dari
  v3 (11, wrap 140 unit ≈ 622 px): batas wrap v3 mengizinkan tepi kanan
  sampai 670 px — masuk zona kolom tombol; garis terpanjang v3 berakhir
  di 645 px (clearance cuma ~11 px). Terverifikasi di klip uji v3.1:
  tepi kanan terjauh 637 px (83 px dari tepi), tepi kiri terdekat
  83 px, tepi bawah settle 708–709 px, tidak ada teks menyentuh atau
  terpotong tepi di frame mana pun (termasuk baris 3-baris terpanjang
  di t=35,50).
- **Yang TIDAK dipakai dari skill ini:** transisi Whip (§5) — perintah
  tetap owner: TANPA transisi. Watermark `@nxrskyaa` (§8) — TIDAK dipakai.
  VO -16 LUFS — tidak relevan, klip tidak pakai VO.
- **Flag `--no-subs` (WAJIB untuk sumber bersubtitle bakar):** potong tanpa
  membakar subtitle sama sekali. Sumber yang wajib pakai `--no-subs`:
  **Ardhianzy, Kelas Pikir, Ruang Tunggu (intro saja)** (ketiganya sudah
  punya subtitle bakar — review 27 Okt 2026: 8 klip gagal karena subtitle
  ganda; review 28 Okt 2026: intro Ruang Tunggu ~60–90 dtk pertama juga
  bersubtitle bakar). Bila ragu,
  cek 1 frame sumber dulu: bila ada teks bakar, pakai `--no-subs`.
- **Yang tidak berubah:** crop/scale 720x1280, libx264 veryfast crf 23,
  AAC 128k, tanpa narasi baru.
- **File:** cutter v3.6 `~/workspace/scratch/cliptest2/cutter/cutter.py`;
  transkripsi `~/workspace/scratch/cliptest2/transcribe_chunked.py`
  (flag `--word-timestamps`, default MATI supaya batch 3 tidak terpengaruh).
  v3.4 = v3.3 + outline hairline 0.5 (perintah owner 28 Okt 2026 20:03 WIB,
  owner memilih Kandidat A); berlaku mulai batch 6.
  v3.5 = v3.4 dengan animasi subtitle diganti transisi blur saja
  (perintah owner 29 Okt 2026 19:56 WIB) — lihat bullet animasi di atas.
  v3.6 = v3.5 + PlayRes natif output (subtitle tajam, outline 0,5 px
  sebenarnya); face tracking podcast (MediaPipe) — perintah owner
  30 Okt 2026 12:53 WIB, lihat dua bullet di atas. Perbaikan
  31 Okt 2026: facetrack diperluas jangkar badan + DEFAULT-ON di
  ketiga cutter (sebelumnya hanya opt-in `--facetrack` di
  cutter_720/cutter_hd dan TIDAK ADA sama sekali di cutter.py).
  Versi HD: `cutter_hd.py` kini **v3.6-hd-kalbotau** (1080x1920, gaya
  kalbotau) dengan perubahan yang sama + facetrack.
  Modul deteksi: `detect_plan.py` (folder cutter yang sama) + model
  `blaze_face_short_range.tflite`; interpreter detektor:
  `~/workspace/scratch/cliptest2/venv-face/bin/python` (mediapipe +
  opencv; env `FACETRACK_PYTHON` bisa mengarahkannya ke venv lain).
  **SEMUA versi cutter lama (v1, v2, v3.1–v3.5, hd v3.4–v3.5) DIHAPUS
  atas perintah owner 30 Okt 2026 21:15 WIB** — template subtitle lama
  (outline tebal, oscillator) tidak boleh bisa dipakai lagi. Yang tersisa
  di folder cutter hanya keluarga v3.6: `cutter.py`, `cutter_720.py`,
  `cutter_hd.py`. (File terhapus masuk trash Muse, kedaluwarsa
  29 Nov 2026.)

## 8. Struktur folder

```
~/workspace/divisi/freelancer-clipper/produksi/
  YYYY-MM-DD/
    batch-<sumber>/          # kerja agent: sumber, transkrip, klip mentah
    review/                  # klip menunggu review Ashila
    lolos/                   # klip lolos review, siap posting/submit
    tayang/                  # klip sudah diposting/disubmit + buktinya
~/workspace/scratch/cliptest/  # uji tool (bukan produksi)
```

## 9. Ritme harian — model BULK APPROVAL (instruksi owner 30 Okt 2026 19:30 WIB) + style CROSS-POSTING (20:19 WIB)

Prinsip: **konten besok diproduksi hari ini; satu persetujuan paket membuka seluruh posting besoknya.** Tidak ada kartu per postingan.

- **10:09 — Produksi H-1** (cron `produksi-klip-harian`): produksi paket untuk BESOK sampai tuntas (unduh → transkrip Whisper lokal → seleksi highlight.py/GeminiWeb2API untuk niche, manual untuk campaign → potong cutter v3.6 standar 720×1280, 1080p bila sumber HD dapat → review gerbang §4 penuh). Paket siap-approval didaftarkan ke `goals/moderate-company-setup/hidden_files/paket-approval-<tanggal besok>.md` (klip + platform + caption + usulan jadwal). **Paket yang didaftarkan WAJIB sudah terverifikasi penuh di run produksi ini (perintah tetap owner 31 Okt 2026 08:13 WIB): file benar-benar ada di disk + ffprobe, lolos gerbang review §4, caption final, jadwal cross-post lengkap — dan blok "STATUS VERIFIKASI" (tanggal/jam, jumlah klip, metode cek, pengecualian) wajib tertulis di kepala file paket. Verifikasi dilakukan malam sebelumnya di sini, BUKAN di sesi approval.**
- **08:00 — Sesi approval bulk** (cron `sesi-approval-posting-klip-harian`): **kartu tampil tepat 08:00, persisten sampai diklik (perintah tetap owner 31 Okt 2026 08:13 WIB).** Tindakan PERTAMA sesi = langsung menyajikan SATU paket + kartu keputusan ke owner (semua klip siap + platform tujuan + jadwal posting; file klip campaign ditunjukkan ke owner untuk dilihat) — tanpa verifikasi panjang di dalam sesi, karena paket sudah terverifikasi penuh malam sebelumnya (statusnya terbaca dari blok STATUS VERIFIKASI di file paket; sesi hanya cek cepat keberadaan file). Kartu keputusan memakai **widget pilihan chat yang persisten** (tampil terus sampai owner mengetuknya) — BUKAN kartu konektor ber-timeout; kartu tidak boleh kedaluwarsa/hilang sebelum diklik. Satu keputusan owner (setujui semua / pilih sebagian / tolak) dicatat ke `hidden_files/sesi-approval-klip-<tanggal>.md` dan menjadi otorisasi tetap run posting hari itu. Bila tak terjawab: paket + kartu diumumkan ulang di chat divisi + sesi diluncurkan ulang di hari yang sama sampai ada keputusan (aturan tetap owner 30 Okt 17:02 WIB — kartu tidak boleh dibiarkan kedaluwarsa, tugas terjadwal wajib tuntas).
- **09:09 — Posting terjadwal CROSS-POSTING** (cron `posting-klip-harian`): eksekusi HANYA paket yang tercatat disetujui — setiap video dalam paket (target 20 video) disebarkan ke SEMUA platform pada hari yang sama: Threads via run berwaktu detached (jeda acak 15–30 mnt, di bawah scope paket), IG penjadwalan native konektor (20 video — melampaui batas lama 15/hari atas perintah cross-posting owner 30 Okt 2026 20:19 WIB), TikTok penjadwalan native Studio, FB run browser (Reel, pengecualian profil personal). URL dari SETIAP platform dicatat per video ke file progres; link postingan klip campaign di-submit ke halaman campaign-nya (Ternak Klip) di hari yang sama setelah tayang + status submit dicatat; laporan akhir: per video URL 4 platform / submit apa / sisa tertahan apa.
- **21:09 WIB**: laporan harian ke datahub (cron `divisi-laporan-harian`).

## 10. Status

- Pipeline: **SIAP (dokumen ini)**.
- Uji throughput tool lama: **SELESAI 26 Okt 18:12 WIB — verdict: 50 klip/hari TIDAK realistis di VM ini dengan tool itu** (download YouTube buntu total + render 18–40x realtime).
- Riset tools alternatif: **SELESAI 26 Okt 20:48 WIB** (`riset-tools-kliping-alternatif.md`, 10 tool diperiksa kodenya). **Tidak ada tool GitHub yang lolos kedua blocker.** Render BISA dihindari (ffmpeg-only terukur 0,62–2,5x realtime; 50 klip ≈ 25–40 mnt). **Rekomendasi: rakitan modular** (large-v3 + highlight LLM + cutter ffmpeg-only + heatmap GET). Bottleneck baru: transkripsi ~7–8 jam/6 podcast (batch latar); mitigasi: large-v3-turbo. Aturan AI clip maker: seleksi momen LLM = AI (jangan untuk campaign); heatmap/manual = bukan AI (aman untuk campaign).
- **Jalur kritis sekarang: download video ke VM — TERPECAHKAN 26 Okt 21:03 WIB.** yt-dlp JALAN dari VM dengan `--compat-options no-certifi` + `--extractor-args youtube:player_client=android` (bukti: video Dunning-Kruger 15 mnt terunduh penuh 24 MB dalam 38 detik). Kesimpulan lama "POST di-blackhole" SALAH — penyebab sebenarnya kegagalan TLS (bundle certifi tidak mengenal CA egress). Uji browser (cobalt + capture videoplayback) tidak diperlukan lagi. Berikutnya: cek format 720p untuk sumber klip lebih tajam.
- **ATURAN TETAP 29 Okt 2026 ~10:13 WIB (perintah owner "kalau ambilnya dari YouTube harusnya bisa full hd"): sumber klip WAJIB Full HD (video terbaik s.d. 1080p + audio terbaik), JANGAN format 18/360p; render target 1080x1920 CRF 18; subtitle pakai tipografi template skill kalbotau (diadaptasi untuk subtitle di atas footage, tanpa panel putih penuh).** Penyebab klip batch 4–5 terlihat tidak HD: sumber 360p dipotong vertikal (~202x360) lalu di-upscale 3,5x ke 720x1280 + CRF 23 (bitrate 300–850 kbps). Perbaikan 15 klip IG batch 4–5 sedang di-render ulang (folder hd/, file lolos/ asli tidak ditimpa); default ini berlaku untuk batch berikutnya setelah QA render ulang lolos.
- **Temuan download HD 29 Okt 2026 ~12:04 WIB (dari render ulang 15 klip, terverifikasi 9/9 sumber 1920x1080): klien yt-dlp `android` kini HANYA memberi format 18 (360p) karena eksperimen SABR-only YouTube; klien `web`/`ios`/`tv` diblokir bot-check — yang jalan untuk 1080p adalah klien `tv_embedded` (prefer avc 1080p, fallback terbaik ≤1080p).** Perintah download Full HD wajib pakai `tv_embedded`, bukan `android`. Hasil render ulang 15 klip: semua 1080x1920, bitrate 1,4–3,8 Mbps (dulu 0,23–1,15), durasi sama, subtitle kalbotau (karaoke word-by-word penuh hanya untuk klip dengan words.json; klip SRT polos highlight per event dengan teks tidak diubah; klip no-subs tidak ditambah subtitle — subtitle bakar bawaan dipertajam saja).
- **Catatan 30 Okt 2026 08:32 WIB: `tv_embedded` juga bisa kena bot-check (4 sumber batch 6 gagal total "Sign in to confirm you're not a bot"; probe `web` gagal PO token/SABR-only). Sifatnya bisa sementara — jangan paksa, hentikan setelah 2 jalur gagal, coba ulang di lain waktu; JANGAN upscale 360p→1080p.**
- **Penegasan owner 30 Okt 2026 12:51 WIB: "Jangan pernah gak full hd" — render antara non-HD (mis. potong 720p dulu, render ulang belakangan) DILARANG. Bila sumber Full HD belum tersedia, tahap render MENAHAN diri sampai sumber HD ada; hanya transkripsi (berbasis audio) yang boleh jalan lebih dulu.**
- **PELONGGARAN owner 30 Okt 2026 17:54 WIB: "Kamu bisa pakai 720p" — 720p RESMI DIPERBOLEHKAN untuk produksi klip, menggantikan gerbang Full-HD-only di atas.** Ambang render kini **output 720×1280** (cutter `cutter_720.py` v3.6-720-kalbotau); sumber 360p yang sudah ada di disk SAH dirender; 1080p tetap pilihan utama bila sumbernya bisa didapat (probe unduhan tetap 1 percobaan/sumber, bot-check tidak dipaksa). Standar subtitle v3.6 tetap berlaku penuh pada output 720p: PlayRes ASS natif output (720×1280), outline hairline 0,5 px, transisi blur saja, tanpa gerakan buatan; podcast orang: facetrack DEFAULT-ON (perbaikan 31 Okt 2026; `--no-facetrack` hanya untuk materi non-orang). Pemicu: bot-check YouTube memblokir unduhan HD seharian (probe ulang 30 Okt ~17:56 WIB: 7/7 sumber batch 6+7 tetap gagal) sehingga batch 6 (28 lolos) + batch 7 (31 terpilih) nol render. Render 720p batch 6+7 dijalankan hari yang sama ke folder `final-720/` masing-masing batch.
- **JALUR UNDUHAN HD YANG BERHASIL — INVIDIOUS (terverifikasi 30 Okt 2026 malam, datahub 773): jalur alternatif sah sesuai koreksi owner 30 Okt 17:54 WIB (gagal di satu pintu ≠ berhenti; cari pintu lain yang sah).** Resep: API instans Invidious **yt.chocolatemoo53.com** → ambil URL googlevideo bertanda tangan untuk **itag 137 (video 1080p) + itag 140 (audio)** → unduh dengan **Range-resume** (chunked, tahan putus) → **verifikasi clen + durasi** tiap aliran → **merge atomik** (tulis file sementara, rename hanya bila utuh — jangan pernah sisakan partial sebagai file final). Skrip: `~/workspace/scratch/cliptest2/.invdl-work/invdl4.py`; hasil: 7 sumber batch 6/7 Full HD 1080p di `~/workspace/scratch/cliptest2/hd-sources/`. **Jalur yang sudah GAGAL dan JANGAN diulang untuk unduhan YouTube langsung:** klien yt-dlp `tv_embedded` / `android_vr` / `web_embedded` / `mweb` / berbasis cookies — semuanya bot-check ("Sign in to confirm you're not a bot"); **Piped mati**; instans Invidious selain chocolatemoo53 nonaktif. Bukti pakai pertama: clip_Zp9jQGYIjGA_10 dirender ulang dari sumber HD ini ke `batch-7/niche/final-hd/` (1080×1920, durasi identik versi 720p, outline hairline lulus) dan menggantikan rujukan klip niche di paket 31 Okt.
- Blocker submit campaign: owner sambungkan sosmed TryBuzzer + payout (menunggu owner).
- **Subtitle v2 (skill motion-video): SELESAI 27 Okt 2026 ~19:50 WIB** — Inter Bold terinstall, aksen #0064FF, cutter v2 + word timestamps, uji render 1 klip nyata lolos verifikasi visual 5 frame (karaoke jalan, kata aktif biru). Berlaku mulai batch 4; batch 3 tetap v1. Detail: `subtitle-skill-v2.md`.
