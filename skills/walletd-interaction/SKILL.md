# Skill: Interaksi walletd (swap, bridge, sign, relay)

Skill payung untuk SEMUA interaksi dengan walletd — daemon wallet
operasional perusahaan. Merangkum seluruh hasil uji terverifikasi
27–29 Okt 2026: baca chain, sign, kirim transaksi, swap DEX, bridge,
dan relay untuk browser. Pelajari skill ini SEBELUM memakai walletd
untuk apa pun; dua skill pendamping yang lebih spesifik:

- Swap/launch token testnet: `~/workspace/custom-skills/testnet-token-launch-lp-swap/SKILL.md`
- Bridge lewat UI Superbridge: `~/workspace/custom-skills/superbridge-testnet-ui/SKILL.md`

Dokumen sumber: `~/workspace/custom-connectors/custom.walletd/CONNECTOR.md`
(audit metode + bukti uji helper), kode daemon di
`~/workspace/superagentic-wallet/daemon/walletd.py`.

## Identitas dan arsitektur

- walletd HANYA melayani wallet burner perusahaan:
  EVM `0xYOUR_BURNER_WALLET`,
  Solana `D6HyCHrCkRQwSpj6x93oSwH5AdtKsCiAKyUJS8D835Zc`,
  Sui `0xd6e1200739c25077aa1df7ed745602e9c04df5c31546b7c954e54d81fb3bd1e5`,
  Cosmos `cosmos1p3fhzu3f44rn0q0s2t37e52zp8qwdrgpneqqr6`.
- Binance agentic wallet TIDAK lewat walletd. Wallet itu
  (`0xYOUR_AGENTIC_WALLET`) dioperasikan lewat
  `baw` CLI dan hanya bisa transaksi, tidak bisa membuka sesi dApp.
  WalletConnect dibuang atas perintah owner 3 Nov 2026; arsitektur
  wallet = Brain. (Dulu sidecar WalletConnect mengoneksikan BURNER,
  bukan Binance.)
- Jalur akses:
  - HTTP bridge `127.0.0.1:18924` — jalur utama program/kontrak.
  - WebSocket `127.0.0.1:18923` — dipakai extension bridge browser.
  - Helper CLI `~/workspace/custom-connectors/custom.walletd/bin/wd.py`
    (jalankan dengan `~/workspace/.wallet-venv/bin/python`).
    Helper tidak pernah membaca seed; semua signing di dalam daemon.
  - Forwarder proxy `127.0.0.1:18888` — khusus CONNECT untuk extension
    browser; GET polos selalu 000 dan itu normal.
  - saw-relay `127.0.0.1:18925` — relay bertoken untuk extension
    browser agen; walletd tidak pernah diekspos langsung ke luar.
- Chain yang didukung helper: `bsc`, `ethereum`, `base`, `polygon`,
  `elysium`, `sepolia`, `bsc-testnet`, `base-sepolia`, `amoy`.
- Policy daemon (ditegakkan walletd, bukan helper): auto-approve
  ≤0,5 native per tx; khusus Elysium ≤0,05 HYPE per tx dengan gas
  di-clamp 0,1–0,2 gwei. Pelanggaran ditolak sebagai `policy denied`.

## Cek kesehatan sebelum bekerja (jangan asumsi hidup)

- `curl -s http://127.0.0.1:18924/` → HTTP 501 berarti walletd hidup.
- Uji tuntas lewat helper: `wd.py accounts` harus mengembalikan
  burner dengan `burner_match: true`; `wd.py chainid --chain <chain>`
  harus sesuai chain tujuan.
- Query receipt lewat HTTP untuk Elysium WAJIB menyertakan
  `"chain": "0x185d9"`; default walletd adalah BSC `0x38`, receipt
  Elysium akan kosong tanpa parameter itu.
- Bila walletd mati (sering terjadi setelah VM restart atau restart
  massal watchdog), hidupkan manual dengan perintah yang sama seperti
  watchdog, berbasis PID:
  `cd ~/workspace/superagentic-wallet/daemon && setsid nohup ~/workspace/.wallet-venv/bin/python walletd.py >> walletd.out 2>&1 < /dev/null & disown`
- JANGAN PERNAH kill sesi exec yang menjalankan hermes-watchdog.sh —
  process.kill merobohkan seluruh process tree termasuk service yang
  baru saja di-restart watchdog.

## Operasi dasar terverifikasi

- Baca: `wd.py chains`, `accounts`, `chainid`, `balance`, `nonce`,
  `block`, `call` (eth_call read-only). Untuk respons besar seperti
  `eth_getCode`, baca lewat `curl` ke RPC publik chain — urllib dari
  VM ini sering putus di tengah respons besar dan jalur walletd juga
  bisa gagal untuk respons besar.
- Sign: `wd.py sign --message "..."` (personal_sign) dan
  `wd.py sign-typed --json <file>` (EIP-712). Keduanya terverifikasi
  recover ke alamat burner. Bug lama `eth_signTypedData_v4` sudah
  diperbaiki di daemon.
- Kirim: `wd.py send --chain <chain> --to <alamat> --value <native>`
  dengan `--data <calldata>` untuk panggilan kontrak. Alamat `to`
  WAJIB EIP-55 checksum — eth_account 0.14 menolak alamat
  all-lowercase.
- Deploy kontrak: `wd.py send` mewajibkan `--to`, jadi deploy harus
  POST `eth_sendTransaction` langsung ke HTTP bridge dengan tx TANPA
  field `to`, `data` berisi bytecode creation, gas eksplisit. POST
  langsung ini kini wajib header `X-Walletd-Token` (lihat bagian Token
  pemanggil di bawah); jalur yang lebih disukai adalah Brain
  (`brain.py propose --to CREATE`).
- Sui signing: DIPERBAIKI 30 Okt 2026. walletd menandatangani Sui lewat
  `sui_sign_intent` — Ed25519 atas digest Blake2b-256 (digest_size 32)
  dari intent message, sesuai standar Intent Signing Sui (sebelumnya
  daemon sign intent mentah sehingga signature pasti ditolak validator;
  bukti kriptografis sebelum/sesudah di
  `~/workspace/scratch/nonevm-test/sui/fix/FIX-VERIFIKASI.md`,
  `verify_blake2b_digest` kini true untuk tx maupun personal message).
  TAPI jalur RPC Sui daemon masih rusak: `SUI_RPC` hardcoded ke
  JSON-RPC mainnet publicnode yang sudah didepresiasi, jadi
  `sui_getBalance`/`sui_transfer` belum bisa dipakai sampai migrasi
  gRPC/GraphQL dikerjakan.

## Swap: verdict terverifikasi 29 Okt 2026

- **UI Uniswap DILARANG di-retry sampai masalahnya berubah.** Gateway
  `entry-gateway.backend-prod.api.uniswap.org` mengembalikan HTTP 401
  dari VM ini untuk SEMUA chain, sehingga UI selalu membaca saldo 0
  dan swap permanen gagal di "Not enough ETH". Koneksi wallet dan
  switch chain lewat extension terbukti jalan; yang mati hanya
  gateway datanya. Temuan lengkap:
  `~/workspace/scratch/swap-test/UNISWAP-UI-TESTNET-FINDINGS.md`.
- **Jalur yang terbukti berhasil: kontrak langsung via walletd.**
  Urutan wajib: ambil alamat Factory/Router02/WETH dari docs resmi
  chain tujuan (JANGAN dari ingatan), verifikasi `eth_getCode`
  non-kosong + `Router02.factory()` dan `Router02.WETH()` cocok,
  quote `getAmountsOut` sebelum swap, `amountOutMin` = 99% quote,
  deadline = now + 1200. Prosedur lengkap dan angka gas ada di skill
  `testnet-token-launch-lp-swap`.
- Bukti sukses (Sepolia, 29 Okt 2026, semua receipt status 0x1,
  diverifikasi on-chain secara independen):
  token MTST `0xe050c93bbf36b6d7fc251deeb760902fefbe2d7e`;
  pair MTST/WETH `0x56f83e297550259afac4399b98f178c5cff5ae99`;
  Factory `0xF62c03E08ada871A0bEb309762E260a7a6a880E6`;
  Router02 `0xeE567Fe1712Faf6149d80dA1E6934E354124CfE3`;
  addLiquidity 0,01 ETH + 100.000 MTST → LP 31,622776;
  swap 0,001 ETH → +9.066,1089 MTST (persis quote);
  swap 1.000 MTST → +0,00011929 ETH.
- Koreksi permanen: swap USDC TIDAK PERNAH berhasil. Yang berhasil
  28 Okt 2026 adalah wrap ETH→WETH lewat `deposit()` ke WETH9 Sepolia
  `0xfFf9976782d46CC05630D1f6eBAb18b2324d6B14` (tx `0x7dbeda12…`,
  hasil 0,003 WETH) — itu wrap, bukan swap DEX, bukan USDC.

## Bridge: verdict terverifikasi 29 Okt 2026

- Lewat UI Superbridge BERHASIL PENUH untuk deposit: 0,011 ETH
  Sepolia → Base Sepolia, Activity berstatus Complete, terverifikasi
  on-chain (Base Sepolia 0,02 → 0,031 ETH). Alur UI lengkap, solusi
  modal To, dan toggle testnet ada di skill `superbridge-testnet-ui`.
- Aturan tetap: SETIAP membuka Superbridge, cek tab Activity/Claims
  DULU sebelum aksi bridge baru. Deposit tidak butuh claim manual.
- UI DEX/bridge selalu default mainnet; testnet diaktifkan lewat
  Settings, bukan alasan meninggalkan jalur UI.
- Arah balik (withdrawal Base Sepolia → Sepolia) BELUM PERNAH diuji.
  Withdrawal OP Stack butuh sekitar 7 hari + finalize/claim manual;
  jangan menyebut bridge "bolak-balik berhasil" sebelum arah ini
  benar-benar dieksekusi dan difinalisasi.
- Fallback kontrak langsung terbukti (28 Okt 2026): deposit lewat
  L1StandardBridge `0xfd0Bf71F60660E2f608ed56e1659C450eB113120`
  sebesar 0,02 ETH, tx `0x580b6ba5…`. Catatan: `depositETH` butuh
  gas sekitar 635 ribu, bukan 200 ribu.

## Relay dan tunnel untuk browser

- Extension bridge terinstall persisten di Chromium lokal Meta pada
  profil `~/workspace/superagentic-wallet/browser-profile-meta/`
  (id ekstensi `bpjhgakeablenjpgjmhjmaakhifmmhkj`); deteksi live
  terverifikasi (chain 0x185d9, burner cocok). Di bawah Playwright,
  ekstensi hanya termuat lewat flag `--load-extension` pada profil
  sekali-pakai — profil persisten tidak memuat ekstensi di Playwright.
- Uji relay lokal (pola baku sebelum menyalahkan tunnel): tanpa token
  → 401, token salah → 401, token benar → `eth_chainId` 0x185d9,
  `eth_requestAccounts` burner, `personal_sign` panjang 130. Uji ini
  lulus dalam 0,36 detik pada 29 Okt 2026.
- localhost.run free MATI untuk relay: HTTP biasa tembus, tetapi
  upgrade WebSocket digantung edge free-nya (>25 detik tanpa respons)
  dan hostname anonim berganti sendiri tiap 10–15 menit. Runner-nya
  sudah dimatikan; jangan dihidupkan lagi untuk WebSocket.
- Jebakan TLS klien mentah ke `*.lhr.life`: wajib ALPN `http/1.1`,
  tanpa ALPN handshake stall lewat egress ini. Gejala di Node `ws`
  adalah EPROTO "wrong version number". Kegagalan tes mentah BUKAN
  bukti tunnel mati — cek dulu dengan curl. Browser tidak kena karena
  selalu mengirim ALPN.
- Jalur permanen yang DIPILIH owner 29 Okt 2026: Cloudflare named
  tunnel — **SELESAI DIBANGUN 29 Okt 2026 ~21:13 WIB**. Seluruh sisi
  Cloudflare dibuat lewat konektor MCP `custom.cloudflare` (bukan
  dashboard, bukan token via chat): zone `example.com`
  (id `73721d21d61a4f3db1b6d5723b319502`), tunnel `saw-relay`
  (id `99856627-ddb6-467b-a30a-873bf51defca`, status API `healthy`,
  2 koneksi http2), ingress `saw-relay.example.com` →
  `http://localhost:18925`, CNAME proxied ke
  `<tunnel-id>.cfargotunnel.com`, token diambil via API dan ditulis
  skrip langsung ke `.cloudflare-token` 0600 tanpa pernah ditampilkan.
  Runner: `extension-agent/tunnel/run-cloudflared.sh` (loop reconnect;
  menjalankan dns_stub.py + tcp_edge_fwd.py + cloudflared di dalam
  `unshare -Urm` dengan /etc/hosts bind-mount — WAJIB untuk egress
  sandbox ini, lihat skill `cloudflare-tunnel-egress`).
  `config.js` ekstensi sudah diregenerasi ke
  `wss://saw-relay.example.com`. SISA SATU LANGKAH OWNER: ganti
  nameserver example.com di NicNames ke
  `rosemary.ns.cloudflare.com` + `vern.ns.cloudflare.com` — zone
  masih `pending`, jadi uji WebSocket publik ujung-ke-ujung baru bisa
  lulus setelah zone `active`. Catatan zone: Cloudflare HANYA menerima
  domain root (subdomain seperti rainx.tokenized.name ditolak,
  error 1116).
- Fee Elysium sudah diperbaiki 29 Okt 2026 di walletd.py
  (`elysium_fee_with_basefee`): gasPrice diangkat ke baseFee × 1,125
  (+1 wei), tetap cap 0,2 gwei. Retest dua kali kirim 0-value
  terkonfirmasi on-chain (blok 18148745 dan 18148805). RPC Elysium
  kadang memutus koneksi tanpa respons — retry wajar untuk READ,
  bukan untuk broadcast (lihat pelajaran nonce di bawah).

## Pelajaran keras (semua terbukti, jangan diulang)

- **Jangan retry broadcast secara membabi buta.** Respons walletd
  bisa putus SETELAH tx ter-broadcast; retry buta pada deploy
  menghasilkan DUA kontrak MTST identik (yang dipakai nonce 8;
  duplikat `0x7627a0399b3fda442b8f06f13f4aa7f3d12dca5e` tidak dipakai).
  Pola aman: catat nonce sebelum kirim; bila respons ambigu, tunggu
  nonce bergerak dan rekonsiliasi dulu sebelum kirim ulang. Buat
  fase-fase idempoten: cek allowance sebelum approve, cek pair dan
  saldo LP sebelum addLiquidity, cek state sebelum swap.
- **Gas testnet jauh di atas buku teks.** Di Sepolia 29 Okt 2026:
  deploy ERC20 kecil 3.521.880 gas, approve 128.084,
  addLiquidityETH + createPair pertama 19.150.555, swap 167–346 ribu.
  Ambil `eth_estimateGas` untuk operasi berat lalu kalikan sekitar
  1,25; putusan akhir selalu receipt (status 0x0 dengan gasUsed
  persis sebesar limit = gas kurang). Estimasi node publik juga bisa
  tidak waras (transfer polos pernah diestimasi 12.000, di bawah
  intrinsic 21.000) — pakai hanya sebagai orde besaran.
- **Standar bukti tanpa pengecualian:** keberhasilan hanya boleh
  diklaim setelah verifikasi on-chain mandiri — receipt status 0x1,
  saldo sebelum/sesudah cocok, reserve pair cocok untuk swap,
  Activity Complete + saldo tujuan naik untuk bridge. Klaim dari UI
  atau laporan agen saja tidak cukup (teguran owner 29 Okt 2026:
  "jangan cuma klaim berhasil tapi kosong").
- Baca saldo beberapa detik SETELAH receipt; node publik bisa lag
  dan menampilkan saldo lama. Logs Transfer di receipt adalah bukti
  primer bila saldo belum bergerak.
- Latensi jujur: respons bridge walletd terukur cepat, tetapi satu
  read terukur sekitar 1,2 detik dan kirim via
  helper pernah 1,9 detik. Target 0,3–0,5 detik BELUM tercapai —
  jangan mengklaimnya.
- WalletConnect dibuang atas perintah owner 3 Nov 2026; arsitektur
  wallet = Brain (sidecar `wc-wallet/` dihapus, prosesnya dimatikan).

## RPC cadangan + failover otomatis (30 Okt 2026, datahub id 708)

walletd TIDAK lagi bergantung pada satu RPC publik per chain. Di walletd.py: `RPC_BACKUPS` + `RPC_ENDPOINTS` (endpoint utama dari `RPCS` selalu pertama), dan `rpc_call_chain()` menjadi satu-satunya jalur pemanggilan EVM (6 call site HTTP + FastRPC WS di fast_rpc.py dengan aturan yang sama).
- Cadangan terverifikasi (tanpa API key): BSC +3 (bnbchain dataseed, 1rpc, drpc), Ethereum +2, Base +2, Polygon +2, Sepolia +3 (tenderly gateway, zan, 1rpc), BSC testnet +2, Base Sepolia +2, Amoy +2. **Elysium tetap satu endpoint** — tidak ada RPC publik alternatif chain 99801 yang terverifikasi; 4 varian kinetiq diprobe dan gagal.
- Failover pada kegagalan transport (koneksi putus/timeout/5xx/bukan JSON) DAN penolakan rate-limit (JSON-RPC -32005 / HTTP 429 / pesan "rate limit"/"too many requests" — ditambahkan 30 Okt 2026, lihat bagian "Failover rate-limit -32005: SUDAH DIPERBAIKI"), payload identik; error semantik node lain (revert, policy, nonce) dikembalikan apa adanya. Endpoint gagal/rate-limit masuk cooldown 60 dtk; urutan coba mulai dari last-good per chain. Setiap failover tercatat di log daemon sebagai `RPC-FAILOVER chain=… method=… from=… to=…`.
- Keamanan kirim: `eth_sendRawTransaction` hanya boleh mengirim ulang raw tx yang sama persis; "already known/imported" = sukses; "nonce too low" = sukses hanya bila percobaan sebelumnya dalam panggilan yang sama gagal transport. Tidak pernah ada tx yang dibangun/ditandatangani ulang saat failover.
- Hook uji: env `WALLETD_RPC_BLACKLIST` (substring endpoint) dibaca saat start daemon untuk memaksa failover dalam pengujian; produksi berjalan TANPA env ini.
- Bukti: 15/15 baca Sepolia sukses; uji paksa (utama Sepolia diblokir) → baca + kirim Brain tetap lulus dari cadangan, receipt tercatat di audit, nonce +1 tepat; kegagalan transport acuan lama ("Remote end closed") kini muncul di log sebagai failover yang tertangani, bukan error ke pemanggil. Cadangan kode sebelum perubahan: `daemon/walletd.py.bak-20261030-rpcfailover`.
- Catatan: endpoint utama Polygon (publicnode) membalas 404 untuk eth_getBlockByNumber via klien WS — terabsorsi failover; Polygon praktis sering mulai dari cadangan.

## Brain gerbang tunggal di jalur WS (30 Okt 2026, datahub id 709)

Handler WS 18923 (jalur ekstensi/relay) kini digerbang Brain: eth_sendTransaction wajib intent approved yang cocok + belum terkonsumsi (penanda di state/ws_consumed.jsonl), personal_sign/eth_signTypedData_v4 via WS ditolak (tidak ada tipe intent-nya di Brain v1), baca tetap bebas, switch chain tidak digerbang. Detail penuh + bukti uji: skill brain-wallet-mediator, bagian "Gerbang tunggal".

## Token pemanggil HTTP walletd (30 Okt 2026, perintah owner — temuan TINGGI DITUTUP)

HTTP bridge 18924 kini **wajib token pemanggil**. Mekanisme:

- Semua POST wajib header `X-Walletd-Token` berisi rahasia dari `~/.burner/walletd.token` (izin 0600, di samping seed; 64 hex char). Perbandingan constant-time (`hmac.compare_digest`) di daemon.
- Token **dibaca ulang daemon pada setiap request** dan dibaca pemanggil pada setiap panggilan — rotasi = tulis token baru ke file itu (tetap 0600), tanpa restart apa pun.
- **Fail-closed:** file token hilang/<32 char → SEMUA POST ditolak. Penolakan = HTTP 401, error `-32001` "unauthorized: valid X-Walletd-Token header required", tercatat di log daemon sebagai `AUTH[http] DENY` (nilai token TIDAK pernah masuk log/audit — terverifikasi grep 0 kemunculan).
- GET / (health check 501), watchdog, dan jalur WS 18923 **tidak** terpengaruh. WS tetap digerbang Brain + token relay.
- Pemanggil sah yang diperbarui (cadangan `.bak-20261030-callertoken` untuk 4 file inti): `bin/wd.py`, `bin/brain.py` (keduanya kini juga membedakan HTTPError dari "tidak terjangkau" dan menampilkan error walletd apa adanya), fallback HTTP `wc-wallet/src/walletd.js` (baca file via node:fs), 4 skrip `superagentic-wallet/sui-faucet/*.py` (header hanya saat URL = walletd). Audit agen yang masuk setelah pengaktifan menemukan 13 file tambahan yang luput dari grep pertama (ekstensi `.mjs` + folder custom-skills tidak tercakup) — SEMUA sudah diperbarui + lolos `node --check`/`py_compile` di hari yang sama: skrip skill Solana (swap_orca.js, bridge_execute.mjs, bridge_redeem.mjs), skrip skill Sui (cetus_swap2.mjs, wormhole_bridge2.mjs, wormhole_attest.mjs, complete_transfer2.py), dan salinan kerja `sui-faucet/ptb/*.mjs` (6 file). Verifikasi akhir: setiap file kode yang POST ke 18924 kini memuat `X-Walletd-Token` (satu-satunya pengecualian `wc-wallet/src/index.js` hanya string log). GET probe (watchdog/brain check/wc-wallet isAlive) tetap bebas token sesuai desain. Pelajaran: grep pemanggil WAJIB mencakup ekstensi `.mjs` dan folder `custom-skills/`.
- Bukti uji 9/9 PASS (transkrip `daemon/uji-caller-token-2026-10-30.log`, skrip `daemon/uji_caller_token.py`): GET 501; tanpa token 401; token salah 401; token benar chainId/accounts benar; **probe bypass C3 asli** (POST `eth_sendTransaction` Sepolia 0,001 ETH tanpa token) → 401 dan nonce diam 34→34; regresi Brain penuh propose→approve→deliver → tx `0x2b6966ad…`, receipt `0x1`, nonce 34→35 tepat. Regresi tambahan: `wd.py` accounts/balance/nonce normal, baca WS normal, fallback HTTP wc-wallet normal.
- Makna keamanan yang jujur: yang ditutup adalah bypass **tanpa kredensial** — proses/browser apa pun yang tidak bisa membaca file 0600 itu tidak bisa lagi memanggil daemon (vektor CORS `Access-Control-Allow-Origin: *` ikut netral). Proses lokal tepercaya pemegang token (wd.py/brain.py) tetap bisa memanggil langsung; untuk alur agen, Brain tetap gerbang proseduralnya.

## Nama resmi (30 Okt 2026)

Sistem walletd + Brain secara resmi bernama **Super Agentic BrainD Wallet** (penamaan owner). Lihat skill brain-wallet-mediator untuk arsitektur mediasinya.

## Failover rate-limit -32005: SUDAH DIPERBAIKI (30 Okt 2026, perintah owner "Lanjutkan ke temuan wallet")

Celah lama (terbukti live di uji keamanan id 720): failover `rpc_call_chain` hanya berpindah pada kegagalan TRANSPORT, sehingga error JSON-RPC `-32005 Rate limit exceeded` dari endpoint utama diteruskan apa adanya ke pemanggil (probe mainnet M5; `wd.py balance --chain bsc` 18:13 WIB gagal dari publicnode padahal cadangan sehat; direproduksi lagi 30 Okt 18:41 WIB — `wd.py nonce --chain bsc` gagal -32005 tiga kali beruntun).

Fix yang terpasang (cadangan `daemon/walletd.py.bak-20261030-fixsedang` + `fast_rpc.py.bak-20261030-fixsedang`, daemon PID 27430):

- Helper `_is_rate_limit_error(err)` di walletd.py DAN fast_rpc.py: rate-limit = kode `-32005` atau `429`, atau pesan mengandung `rate limit` / `rate_limit` / `too many requests`. Penolakan rate-limit berarti node menolak SEBELUM memproses request, jadi ia kini menjadi **pemicu failover** sama seperti transport: payload IDENTIK ke endpoint berikutnya + endpoint yang kena masuk cooldown 60 dtk + tercatat `RPC-FAILOVER ... err=rate-limit: ...` di log daemon.
- HTTP 429 selalu diperlakukan sebagai rate-limit (transport-class) di `_rpc_post_once` (kedua jalur walletd.py) dan `FastRPC._post_once` — walau body-nya membawa error JSON-RPC, karena error itulah sinyal rate-limit-nya.
- Error semantik lain (revert, insufficient funds, invalid params, nonce, already known) TIDAK di-failover-kan — dikembalikan apa adanya (teruji: revert hanya 1 percobaan). Perilaku kirim tidak berubah: resend hanya raw tx yang sama persis; aturan "already known" / "nonce too low setelah failover" kini berlaku setelah failover transport ATAU rate-limit. Bila SEMUA endpoint rate-limit, error -32005 terakhir yang diteruskan ke pemanggil.
- Berlaku di kedua jalur: `rpc_call_chain` (HTTP 18924) dan `FastRPC.call` (WS 18923).

Bukti uji 26/26 PASS (transkrip `daemon/uji-fix-sedang-2026-10-30.log`, skrip `daemon/uji_fix_sedang.py`): organik — `wd.py nonce --chain bsc` yang pra-fix selalu -32005 kini sukses (nonce 0) dan log daemon menangkap failover 429 organik dari publicnode BSC (`11:45:21 ... chain=0x38 ... err=HTTP 429 rate limit exceeded`); deterministik — stub HTTP lokal: primer -32005 → hasil dari cadangan + baris log `err=rate-limit:`, varian HTTP 429 → failover, varian revert → tanpa failover; regresi Brain penuh lulus (tx `0x62ddb680…`, nonce Sepolia 35→36 tepat).

## Chain asing DITOLAK, tidak lagi dipetakan ke BSC (30 Okt 2026, temuan SEDANG id 720 — DIPERBAIKI)

Celah lama: request HTTP dengan chain `0xdead`/`bogus123` dijawab sebagai BSC `0x38` termasuk saldo BSC, karena fallback `RPCS.get(chain_hex, RPCS[DEFAULT_CHAIN])` di ±4 tempat.

Fix yang terpasang (file/cadangan yang sama dengan fix rate-limit di atas):

- Helper `resolve_chain_hint(raw)` di walletd.py menjadi satu-satunya resolusi chain per-request di kedua handler (HTTP + WS, termasuk chainId di dalam tx `eth_sendTransaction` dan `dex_swap`): nilai eksplisit yang tidak menormalisasi ke chain di `RPCS` → **ditolak `4902: chain not supported by this wallet: <nilai>`**. Resolusi dipindah ke DALAM blok try handler supaya penolakan terkirim sebagai error JSON-RPC (bukan memutus koneksi).
- Guard keras di lapis bawah: `rpc_call_chain()`, `fast_client()`, dan `rpc_endpoints_filtered()` kini melempar 4902 untuk chain di luar RPCS — tidak ada lagi fallback diam-diam di mana pun (grep akhir: nol `RPCS.get(..., DEFAULT)` tersisa). `wallet_switchEthereumChain`/`wallet_addEthereumChain` memang sudah menolak 4902 dan tidak diubah.
- **Keputusan chain kosong (dengan bukti audit pemanggil): default DIPERTAHANKAN hanya untuk chain yang TIDAK diberikan (absen/None/string kosong).** Pemanggil sah yang mengandalkan itu: wd.py + brain.py (`call_walletd` hanya menyisipkan `chain` bila truthy — accounts/personal_sign/sign-typed/sol/sui/cosmos dikirim tanpa chain), wc-wallet `walletd.js` (`if (chainHex) body.chain = chainHex`), background.js ekstensi meneruskan `msg.chain` yang bisa undefined, dan provider ekstensi lama yang tidak mengirim hint. Nilai eksplisit dari semua pemanggil sah selalu hex valid anggota RPCS (peta CHAINS wd/brain; elysium `0x185d9`).

Bukti uji (transkrip yang sama, bagian A): HTTP `eth_chainId`/`eth_getBalance` chain `0xdead` + `bogus123` → 4902; tx dengan chainId 57005 (0xdead) → 4902 dan nonce Sepolia diam; WS chain `0xdead` → 4902; nonce/saldo BSC diam 0/0 sebelum-sesudah; WS read tanpa chain tetap normal (default utuh).
