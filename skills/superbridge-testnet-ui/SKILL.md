# Superbridge UI — Testnet Flow & Claim Check

Skill ini menyimpan alur kerja UI Superbridge yang terverifikasi lewat retest
29 Okt 2026 (probe1–30, atas perintah owner "simpan flow ini"). Pakai skill
ini setiap kali bekerja lewat UI Superbridge: cek claim tertunda, pilih
chain testnet, verifikasi rute bridge, atau EKSEKUSI deposit — di chain
apa pun. Langkah, verifikasi, dan cek claim-nya sama untuk semua chain;
yang berganti hanya nama chain pada ikon filter. Deposit Sepolia →
Base Sepolia 0,011 ETH TEREKSEKUSI penuh 29 Okt 2026 (probe28–30) di bawah
perintah kampanye owner 29 Okt 2026 10:43 WIB ("uji semua tanpa berhenti").

## Perintah tetap yang mengikat skill ini

- **Cek claim dulu sebelum aksi bridge baru.** Buka tab Activity/Claims
  sebelum melakukan apa pun: tombol Claim/Finalize = withdrawal yang sudah
  lewat 7 hari dan siap difinalisasi; deposit tidak butuh claim manual.
  Transaksi berstatus Complete = tidak ada claim tertunda.
- **UI default mainnet.** Superbridge (dan UI DEX/bridge lain seperti
  Uniswap) selalu default mainnet — testnet diaktifkan lewat pengaturan,
  bukan alasan meninggalkan jalur UI.
- **View-only sampai ada perintah eksekusi.** Memilih chain/token dan
  membuka Activity tidak menggerakkan dana. Eksekusi bridge, claim, atau
  transaksi apa pun butuh perintah/konfirmasi owner dulu. Mainnet = dana
  riil, tiap tx butuh konfirmasi owner; testnet bebas dicoba tapi tetap
  tanpa eksekusi tanpa perintah. Pengecualian tercatat: kampanye uji
  testnet 29 Okt 2026 berjalan atas perintah eksplisit owner ("uji semua
  tanpa berhenti, kalau sudah berhasil baru berhenti") — deposit 0,011
  ETH dieksekusi dalam rangka itu, bukan atas inisiatif sendiri.
- **Jangan klaim berhasil tanpa bukti.** Bukti yang sah = screenshot form
  dan screenshot Activity yang SUDAH DIBACA sebelum melapor. Teks DOM saja
  bukan bukti final (pelajaran dari teguran owner 29 Okt 2026: laporan
  berbasis teks DOM dinilai "klaim berhasil tapi kosong").

## Prasyarat infra (cek dulu, jangan asumsi hidup)

- walletd: `curl http://127.0.0.1:18924/` → HTTP 501 = hidup.
- Forwarder: `curl -x http://127.0.0.1:18888 https://example.com` →
  CONNECT 200 = hidup. Catatan: GET polos ke forwarder selalu 000, itu
  normal (forwarder hanya CONNECT).
- Bila mati (mis. sehabis VM restart): hidupkan manual dengan perintah
  watchdog yang sama, berbasis PID (jangan `pkill -f` dengan pola yang
  cocok dengan perintah sendiri):
  - forwarder: `cd ~/workspace/superagentic-wallet/bin && setsid nohup python3 proxy_fwd.py >> proxy_fwd.out 2>&1 < /dev/null & disown`
  - walletd: `cd ~/workspace/superagentic-wallet/daemon && setsid nohup /home/user/workspace/.wallet-venv/bin/python walletd.py >> walletd.out 2>&1 < /dev/null & disown`
- Jangan pernah kill sesi backgrounded yang menjalankan hermes-watchdog.sh
  (process.kill merobohkan seluruh process tree termasuk service yang baru
  di-restart).

## Lingkungan eksekusi

- Playwright Chromium di bawah `xvfb-run`, Python dari venv wallet
  (`~/workspace/.wallet-venv`, playwright terinstal di sana).
- Proxy forwarder `http://127.0.0.1:18888` + bypass `localhost;127.0.0.1`
  (walletd diakses via localhost, jangan lewat proxy).
- Extension bridge: `~/workspace/superagentic-wallet/extension`, dimuat
  dengan flag `--load-extension` + `--disable-extensions-except` pada
  profil SEKALI-PAKAI (mis. `/tmp/chrome-superbridge-test`).
- **Profil persisten TIDAK memuat extension di bawah Playwright**
  (`window.ethereum` = false pada `browser-profile-meta`) — extension
  hanya jalan lewat flag `--load-extension`. Jadi run Playwright selalu
  profil sekali-pakai + flag; konsekuensi: setting testnet harus
  diaktifkan ulang tiap run.
- **Simpan skrip di `~/workspace/scratch/superbridge-test/`, BUKAN /tmp.**
  /tmp terhapus tiap VM restart (skrip `/tmp/pwtest/` hilang pada
  restart 29 Okt 2026). Contoh kerja: `probe19.py` (template tangkap
  bukti: form + Activity).

## Alur langkah-demi-langkah

1. **Buka Superbridge.** `https://superbridge.app`, tunggu render,
   tolak banner cookie (klik `Reject` — tunggu banner muncul dulu,
   klik di awal bisa balapan dengan render).
2. **Connect wallet.** Klik `Connect wallet` → klik `SuperAgentic Wallet`
   (teks PERSIS). Badge `Installed` adalah node teks terpisah — jangan
   cari teks gabungan `SuperAgentic Wallet Installed` (tidak akan ketemu).
   Verifikasi: `eth_requestAccounts` mengembalikan burner
   `0xYOUR_BURNER_WALLET` (tampil `0x65…b4E2`).
3. **Buka Settings.** Klik tombol ikon kanan atas (urutan DOM button
   ke-1). **BUKAN menu hamburger** — menu navigasi hanya berisi
   Superbridge/Rollies/API/Advertise/Stats/Support/Terms/Privacy, tidak
   ada Settings. Panel Settings berisi Theme, Currency (USD), Language
   (English), **Enable testnets**, Cookies & Analytics.
4. **Aktifkan testnet.** Klik elemen `role="switch"` pada baris Enable
   testnets. **Klik teks baris TIDAK mengubah apa-apa** (terbukti:
   `testnets` tetap false). Verifikasi lewat localStorage:
   `sb-widget-settings.state.preferences.testnets === true`. Tanda
   visual: form reset ke `Select a token` + badge `Testnet` di kartu.
5. **Pilih chain (From/To).** Klik `Select a token` → di modal, klik
   ikon filter chain di baris bawah: `img[alt="<NamaChain>-network-icon"]`
   (klik tombol pembungkusnya; contoh: `Sepolia-network-icon`,
   `Base Sepolia-network-icon`). Lalu **TUNGGU token chain itu ke-load**:
   poll s/d 90 detik sampai indikator `Loading tokens...` hilang DAN
   baris token muncul (mainnet ~25 detik, testnet ~50 detik).
   Kemudian klik baris token dengan teks persis (mis. `Ethereum`).
   Verifikasi: form menampilkan token + nama chain (mis. `ETH Sepolia`).
6. **Pilih To lewat network picker (SOLUSI anomali To, probe22–28).**
   Modal To terbuka dalam tampilan ALL-CHAINS (baris `ETH 11 Networks`,
   `USDC 10 Networks`, `WETH 2 Networks`, `XAN 3 Networks`, ikon globe
   aktif di baris chain bawah) — ini BUKAN kegagalan. Klik ikon chain
   tujuan dengan **klik Playwright** (scroll-into-view + click; klik JS
   `.click()` TIDAK menggerakkan filter — terbukti probe21). Klik itu
   membuka **Ethereum network picker**: header `← Ethereum | Search`,
   baris `ETH / <chain> / saldo` (Sepolia 0,227, Base Sepolia 0,02, …).
   Klik baris tujuan dengan logika **deepest-match** (wadah list juga
   mengandung teks chain + saldo, jadi saring kandidat yang tidak punya
   keturunan kandidat, lalu klik `closest('button')`/baris itu) —
   contoh: baris `Base Sepolia 0.02` menutup modal dan mengisi To.
   **Pasangan lengkap HANYA ditentukan form + URL, bukan return klik:**
   form menampilkan To = `ETH Base Sepolia` DAN URL mengandung
   `toChainKey=base-sepolia` (ETH = zero address). Klaim `PAIR COMPLETE`
   dari return klik saja PERNAH SALAH (probe21) — selalu cek form + URL.
7. **Cek Activity (wajib, sebelum aksi bridge baru).** Klik tab Activity.
   Satu transaksi Complete = tidak ada claim tertunda. Tombol
   Claim/Finalize yang muncul = aksi transaksi — jangan diklik tanpa
   konfirmasi owner. **Tutup panel Settings dulu sebelum klik Activity**
   (tekan Escape; bila masih terbuka, klik tombol X) — klik Activity
   menembus panel Settings yang terbuka TIDAK membuka daftar Activity
   (probe29 gagal karena ini, probe30 berhasil setelah Escape).
8. **Isi amount.** Kolom amount BUKAN `<input>` — melainkan **TEXTAREA**
   placeholder `0` (probe24). `document.body.innerText` TIDAK memuat
   nilai textarea — verifikasi amount lewat seksi quote/Review, bukan
   teks body saja. Pola yang jalan: klik textarea (fokus) + `fill`,
   lalu `Control+a` + ketik angka (ketikan mendarat karena fokus
   bertahan) sampai quote tampil (mis. `Native bridge / 54 secs /
   0.011 ETH / $25.34 / No extra fees`).
9. **Review → Start (TIDAK ada tombol aksi di halaman form).**
   Terbukti lewat screenshot full-page + inventaris DOM (probe27):
   halaman form TIDAK punya tombol Review/Deposit/Bridge apa pun —
   jangan buang waktu memindai `<button>`. Klik **baris header kartu
   rute** (elemen terkecil yang mengandung `Native bridge` DAN
   `54 secs`) → modal review `Via Native bridge` (0,011 ETH Sepolia →
   0,011 ETH Base Sepolia, `About 54 secs`, `Network fees $0.03 /
   0.000011 ETH`) → klik tombol **`Start`** (teks persis; inilah CTA
   yang selama ini dicari — pemindai kata review/deposit/bridge
   melewatkannya karena teksnya `Start`). Setelah Start, modal
   beralih `Waiting for transaction` lalu menampilkan hash tx +
   `Started at …` + `You can safely close this…`.
10. **Konfirmasi wallet (auto-sign, bukan popup).** Extension wallet
    meneruskan permintaan ke walletd, dan walletd **auto-approve**
    transaksi native ≤0,5 (policy) — TIDAK ada popup konfirmasi yang
    muncul (pemindai popup probe28 tidak menemukan halaman apa pun).
    Jangan menunggu popup yang tidak datang; verifikasi lewat hash di
    modal + Activity + `wd.py` (saldo/nonce). Bila popup MUNCUL,
    guard tetap berlaku: konfirmasi HANYA bila teksnya mengandung
    amount dan nama chain yang diharapkan (mis. `0.011` + `sepolia`).
11. **Tangkap bukti.** Screenshot form (From/To terisi + badge Testnet),
    screenshot modal review/Start, dan screenshot Activity. **BACA
    semua screenshot sebelum melapor.** Bila screenshot menunjukkan
    keadaan lain (mis. modal masih terbuka), laporkan keadaan itu apa
    adanya, jangan klaim keadaan yang tidak terlihat di foto.

## Generalisasi ke chain lain

Ganti hanya nama chain pada alt ikon. Chain testnet yang terlihat di
modal Superbridge (29 Okt 2026): Sepolia, Base Sepolia, Arbitrum
Sepolia, OP Sepolia, Soneium Minato Testnet, Superseed Sepolia, Celo
Sepolia Testnet, Linea Sepolia Testnet, Unichain Sepolia, World Chain
Sepolia, Ink Sepolia, Solana Devnet, BNB Smart Chain Testnet, Robinhood
Chain Testnet, Arc Testnet. Alur connect → Settings → switch testnet →
ikon chain → tunggu load → pilih token → cek Activity berlaku identik
untuk semuanya. Saldo yang tampil di form (mis. 0,227 ETH untuk Sepolia)
adalah saldo wallet pada chain yang dipilih — cocokkan dengan saldo
yang diketahui sebagai pemeriksaan kewarasan.

## Gotcha teknis (jangan diulangi)

- **Teks terpisah di node berbeda.** `get_by_text` gabungan gagal untuk
  `SuperAgentic Wallet Installed` dan `ETH Ethereum` — pakai teks satu
  node, `button:has-text(...)`, atau klik JS fallback.
- **Klik Playwright bisa flaky** pada span-di-dalam-button (timeout saat
  `performing click action`) — pola klik: locator click dulu, gagal →
  fallback JS (klik button yang innerText-nya persis, atau span lalu
  tombol terdekatnya).
- **Daftar token lambat, bukan gagal.** Jangan simpulkan gagal sebelum
  poll 90 detik. Di mode testnet, list pernah baru ke-load setelah
  ~50 detik.
- **Modal menutupi form.** Selama modal selector terbuka, tombol form di
  belakangnya tidak bisa diklik — pastikan token terpilih (modal
  tertutup) sebelum klik `Select a token` sisi berikutnya.
- **Anomali To (29 Okt 2026, TERSELESAIKAN probe22–28).** Modal To
  yang menampilkan baris XAN multi-chain tanpa `Ethereum` adalah
  tampilan ALL-CHAINS yang normal, bukan kegagalan — JANGAN menunggu
  `Ethereum` muncul di tampilan itu. Solusi: klik Playwright pada ikon
  chain tujuan → network picker → klik baris tujuan (deepest-match).
  Detail di langkah 6.
- **Klik ikon chain WAJIB scoped ke dialog token modal.** Modal detail
  Activity memakai alt ikon chain yang SAMA (`Sepolia-network-icon`,
  `Base Sepolia-network-icon`) — klik ikon di level dokumen bisa
  mengenai badge detail Activity, bukan filter modal (akar kegagalan
  probe20). Selalu batasi pencarian ikon ke `[role="dialog"]` modal
  token yang sedang terbuka.
- **Jangan reload / jangan klik "back to Bridge" setelah cek Activity.**
  Form dan Activity hidup berdampingan di satu halaman — dari Activity
  langsung ke selector From. Reload membuat klik selector berikutnya
  gagal (probe20).
- **Cek sukses klik: `locator` atau akhiran `:True`.** Return JS
  `js-norm:False` mengandung huruf besar `False` — cek substring
  `false` (huruf kecil) mengira gagal sebagai sukses (bug probe21).
  Sukses = return persis `locator` atau berakhir `:True`.
- **Tutup panel Settings sebelum klik Activity** (lihat langkah 7).
- **Rantai wallet default BUKAN Sepolia.** Extension wallet per profil
  segar default di BSC mainnet (`chainId 0x38`); `wallet_switchEthereumChain`
  ke testnet (mis. `0xaa36a7` Sepolia) terverifikasi auto-approve
  (2x, Uniswap probe3–4). Navigasi/reload MERESET rantai ke `0x38` +
  memutus koneksi — jangan navigasi setelah switch; verifikasi ulang
  `chainId` tepat sebelum aksi apa pun.

## Bukti keberhasilan yang sah (contoh 29 Okt 2026)

### Retest awal (probe18–19, view-only)

- Form: `ETH Sepolia` terisi, badge `Testnet`, saldo 0,227 ETH
  (`scratch/superbridge-test/superbridge19-form.png`).
- Activity: `0.02 ETH Sepolia → Base Sepolia, Complete, 23 hrs ago`,
  tanpa claim tertunda
  (`scratch/superbridge-test/superbridge19-activity.png`).

### Deposit penuh TEREKSEKUSI (probe28–30, kampanye uji testnet)

- Form + amount: `ETH Sepolia → ETH Base Sepolia`, `0.011` ($25,39),
  `Native bridge / 54 secs / No extra fees`
  (`scratch/superbridge-test/superbridge28-post.png` — modal review
  pasca-Start; `superbridge26-form-full.png` — form terisi penuh).
- Modal pasca-Start: `Via Native bridge`, `0.011 ETH Sepolia →
  0.011 ETH Base Sepolia`, `About 54 secs`, hash `0x2f13...be35`,
  `Started at 4:23 AM, Oct 29, 2026` (= 11:23 WIB).
- Hash penuh (dari `walletd.log`, baris `11:23:25 TX … in 415ms
  (policy: within policy)`):
  `0x2f13a6f70955e1446347456763eaa06baa03465ed0a627d63797e850b047be35`.
- Receipt on-chain (Sepolia, via RPC publik):
  `status 0x1`, blok 12017085, dari `0x650E...b4E2` ke kontrak bridge
  `0xfd0bf71f60660e2f608ed56e1659c450eb113120`, gas 637815.
  Saldo Sepolia 0,227 → 0,21599043 (delta persis 0,011 + gas
  0,00000957), nonce 6 → 7.
- Sisi tujuan: saldo Base Sepolia 0,02 → **0,031** (+0,011 persis).
- Activity akhir (probe30, dibaca dari screenshot):
  `0.011 ETH Sepolia $25.39, 30 mins ago → 0.011 ETH Base Sepolia
  $25.39, Complete` — tanpa claim tertunda
  (`scratch/superbridge-test/superbridge30-activity.png`).
- Alur To → amount → review → Start terreproduksi 6x (probe23–28);
  deposit dieksekusi 1x (probe28) dan terverifikasi di kedua sisi.
