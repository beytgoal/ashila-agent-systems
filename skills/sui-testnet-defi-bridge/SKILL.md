# Sui Testnet — Swap Cetus CLMM (PTB Manual) + Bridge Wormhole ke EVM Testnet

Skill ini menyimpan dua alur testnet Sui yang TERBUKTI BERHASIL on-chain
30 Okt 2026 (datahub infrastruktur id 664 dan 666): swap di Cetus CLMM
testnet lewat PTB yang dibangun manual di package aktif, dan bridge
Wormhole Token Bridge Sui testnet → Base Sepolia sampai redeem selesai di
sisi EVM. Pakai setelah dompet Sui testnet terdanai (skill
`sui-faucet-v3-pow`). Semua alamat package/pool di bawah adalah keadaan
30 Okt 2026 — package DEX dan bridge di testnet BISA bermigrasi lagi, jadi
resolusi ulang alamat aktif adalah langkah wajib, bukan opsional.

## Perintah tetap yang mengikat skill ini

- **Gunakan gRPC / GraphQL saja.** JSON-RPC publik Sui testnet mati di
  semua provider. Client yang terbukti: `SuiGrpcClient` dari `@mysten/sui`
  v2 ke `https://fullnode.testnet.sui.io:443`, dan GraphQL
  `https://graphql.testnet.sui.io/graphql` untuk baca saldo.
- **Simulasi dulu, selalu.** Setiap PTB wajib lolos
  `simulateTransaction` (status success + balanceChanges masuk akal)
  sebelum ditandatangani dan dieksekusi. Simulasi gagal = berhenti dan
  perbaiki komposisi, jangan broadcast.
- **Signing lewat walletd.** Tanda tangani bytes transaksi via walletd
  (`sui_signTransaction`, pola skill `walletd-interaction`). Fix digest
  Blake2b walletd sudah live dan terverifikasi (`verify_blake2b_digest:
  true`) — jangan edit ulang daemon untuk pekerjaan ini.
- **Jangan pernah percaya konfigurasi SDK DEX/bridge.** SDK Cetus
  v5.4.0 stale total (package lama + JSON-RPC mati). Package aktif selalu
  diambil dari keadaan on-chain saat itu juga (lihat resolusi package di
  bawah).
- **Standar bukti dua sisi.** Swap selesai hanya bila digest SUCCESS +
  balanceChanges cocok. Bridge selesai hanya bila sisi asal (digest Sui
  SUCCESS) DAN sisi tujuan (receipt redeem SUCCESS + saldo wrapped naik)
  sama-sama terverifikasi. Klaim dari simulasi atau dari satu sisi saja
  tidak sah.
- **Verifikasi nonce on-chain sebelum retry di sisi EVM.** Respons RPC
  daemon bisa hilang setelah broadcast (`Remote end closed`). Sebelum
  mengirim ulang transaksi EVM apa pun, baca `eth_getTransactionCount`
  (pending) dan receipt dari hash yang mungkin sudah terkirim. Retry buta
  = transaksi ganda.

## Prasyarat

- Saldo SUI testnet cukup di alamat pengirim (klaim via skill
  `sui-faucet-v3-pow`). Dana bisa berada sebagai address balance —
  `coinWithBalance` di PTB menanganinya.
- walletd hidup: `curl http://127.0.0.1:18924/` → HTTP 501 = hidup.
  Signing Sui dan `eth_sendTransaction` berjalan lewat HTTP bridge ini.
- Node dengan `@mysten/sui` v2 terpasang (folder acuan
  `~/workspace/superagentic-wallet/sui-faucet/ptb/`).
- Saldo gas EVM tujuan cukup untuk redeem (burner Base Sepolia memegang
  ETH Sepolia Base dari pekerjaan sebelumnya; cek dulu).
- Skrip rujukan yang terbukti, terarsip di `scripts/` skill ini:
  `resolve_pkg.mjs`, `cetus_swap2.mjs`, `wormhole_attest.mjs`,
  `wormhole_bridge2.mjs`, `complete_transfer2.py`.

## Bagian A — Swap Cetus CLMM testnet (PTB manual)

### Resolusi package dan pool aktif

- Abaikan package bawaan SDK Cetus (0x0c7a…/0x85e6… saat bukti berjalan —
  semuanya sudah ditinggalkan). Semua pool SUI testnet telah bermigrasi
  ke package **`0x5372d555ac734e272659136c2a0cd3227f9b92de67c80dc11250307268af2db8`**
  (keadaan 30 Okt 2026).
- Temukan pool dari daftar pool Cetus testnet (API Cetus, contoh artefak
  `cetus_pools.json`) berdasarkan pasangan coin, lalu cocokkan tipe pool
  on-chain: package pada tipe pool itulah package aktif. Pool USDT/SUI
  yang terbukti: `0xb9ea1b16ec381ca94571eed2fbe0a7f668311587aedae6282c65fa382e17b883`,
  GlobalConfig `0xc6273f844b4bc258952c4e477697aa12c918c8e08106fac6b934811298c9820a`,
  coin USDT testnet `0x14a71d857b34677a7d57e0feb303df1adb515a37780645ab763d42ce8d1a5e48::usdt::USDT`.

### Komposisi PTB (SUI → USDT, terbukti)

1. `pool::flash_swap` pada package aktif, typeArguments `[USDT, SUI]`,
   argumen: GlobalConfig, Pool, `a2b=false`, `by_amount_in=true`,
   `amount` (u64, MIST), `sqrt_price_limit` = batas maksimum
   `79226673515401279992447579055` (u128), clock `0x6`. Menghasilkan
   balance keluar A, balance keluar B, dan flash receipt.
2. Siapkan pembayaran: `0x2::balance::zero<USDT>` untuk sisi yang tidak
   dibayar, dan input SUI via `coinWithBalance({balance: amount, type: SUI})`
   lalu `0x2::coin::into_balance<SUI>`.
3. `pool::repay_flash_swap` typeArguments `[USDT, SUI]`, argumen:
   GlobalConfig, Pool, balance nol USDT, balance bayar SUI, receipt.
4. Ubah kedua balance hasil ke coin (`0x2::coin::from_balance`) dan
   `transferObjects` ke pengirim.
5. Simulasi → build → sign via walletd `sui_signTransaction` (base64
   bytes) → `executeTransaction` via gRPC → `waitForTransaction` dengan
   effects + balanceChanges.

### Bukti berjalan A (30 Okt 2026, datahub id 664)

- Digest `EQRWhdtRTcPTuV3dEWTKwPPaYU7KK7DaHjN6DXr1QcWp` SUCCESS.
  Input 1.000.000 MIST, balanceChanges: SUI −4.311.144 (input + gas),
  USDT +3.575 unit. Saldo USDT burner 0 → 3.575 terverifikasi gRPC.

## Bagian B — Bridge Wormhole Sui → EVM testnet

### Resolusi CURRENT package bridge (wajib, jebakan assert_version)

- Package ASLI token bridge dan wormhole core GAGAL dengan
  `assert_version` bila dipakai langsung. Package yang berlaku disimpan
  sebagai dynamic field **`CurrentPackage`** pada state object masing-masing.
- Baca dengan `listDynamicFields` pada state object, cari field bernama
  `CurrentPackage`, lalu `getObject` field itu dan ambil package dari
  JSON-nya (`scripts/resolve_pkg.mjs` melakukan persis ini).
- State object (tetap): token bridge
  `0x6fb10cdb7aa299e9a4308752dadecb049ff55a892de92992a1edbd7912b3d6da`,
  wormhole core
  `0x31358d198147da50db32eda2562951d53973a0c0ad5ed738e9b17d88b213d790`.
- Current package terbukti 30 Okt 2026: token bridge
  `0xad5d68fbc423bf8d6fa65b4309430fb586107220ee11444eac2146a6a8ae559e`,
  wormhole core
  `0x21473617f3565d704aa67be73ea41243e9e34a42d434c31f8182c67ba01ccf49`.
  Resolusi ulang setiap menjalankan — jangan hardcode buta.

### Chain id Wormhole — skema 1000x untuk EVM testnet (jebakan termahal)

- Chain id Wormhole BUKAN chain id EVM. Sui = **21**.
- EVM testnet memakai skema **1000x**: **Base Sepolia = 10004** (bukan
  84532, bukan 30). Selalu ambil chain id Wormhole tujuan dari registry
  resmi Wormhole sebelum menyusun PTB, jangan turunkan dari EVM chainId.
- Harga kesalahan ini sudah terbayar: percobaan 1 dengan target chain 30
  (digest Sui `C1V3h7CFBT4s8sXwc8r7LvpeDAqYeyhYC69g4mMPCLJn`, VAA seq 1433)
  revert di tujuan dengan `invalid target chain` dan 0,05 SUI testnet
  terkunci permanen di bridge. Tidak ada mekanisme refund untuk VAA yang
  sudah terbit ke chain yang salah.

### Komposisi PTB bridge (dari kode SDK resmi, terbukti)

1. `state::verified_asset<SUI>` pada CURRENT package token bridge,
   argumen: state object token bridge. Inilah kunci komposisinya.
   **`borrow_token_registry` TIDAK bisa dipakai di PTB** karena
   mengembalikan reference — jalur itu jalan buntu, jangan diulang.
2. Coin input via `coinWithBalance({balance: amount, type: SUI})`.
3. `transfer_tokens::prepare_transfer<SUI>`, argumen: verified asset,
   coin, `target_chain` (u16, chain id Wormhole tujuan), alamat tujuan
   sebagai vektor 32 byte (alamat EVM di-left-pad nol), relayer fee `0`
   (u64), `nonce` (u32). Menghasilkan ticket + dust.
4. `coin_utils::return_nonzero<SUI>` untuk dust.
5. `transfer_tokens::transfer_tokens<SUI>`, argumen: state object token
   bridge, ticket. Menghasilkan message ticket.
6. `publish_message::publish_message` pada CURRENT package wormhole
   core, argumen: state object wormhole, fee coin `0x2::coin::zero<SUI>`
   (message fee 0 di testnet), message ticket, clock `0x6`. Sequence VAA
   terbaca dari events transaksi final.
7. Simulasi → sign via walletd → eksekusi gRPC → tunggu final + events.

### Attest token (sebelum bridge pertama suatu token)

- Bridge token yang wrapped-nya belum ada di tujuan butuh attest dulu:
  `attest_token::attest_token<SUI>` pada CURRENT package token bridge,
  argumen: state object token bridge, **object CoinMetadata token**,
  nonce (u32), dilanjutkan `publish_message` seperti di atas. Ambil VAA
  attest, lalu panggil createWrapped di Token Bridge tujuan.
- Identitas token SUI untuk Wormhole = object CoinMetadata
  `0x587c29de216efd4219573e08a1f6964d4fa7cb714518c2c8a0f29abfa264327d` —
  BUKAN `0x2`. Memakai 0x2 menghasilkan attest yang salah token.
- Cek dulu apakah wrapped sudah ada di tujuan. Saat bukti berjalan,
  wrapped SUI di Base Sepolia SUDAH ada
  (`0x5fcafeb2664dc23e945faac63d1264adbf56ad9b`) sehingga createWrapped
  revert `already exists` — revert itu jinak dan berarti langkah attest
  sisi tujuan boleh dilewati.
- Bukti attest: digest `qcc49YH4AvhiAxCr42DxcqhUCf7p7SovZwmwkuSVjWd`,
  VAA seq 1434.

### Ambil VAA dan redeem di sisi EVM

- Poll WormholeScan testnet (`https://api.testnet.wormholescan.io`) untuk
  signed VAA berdasarkan emitterChain 21 (Sui), emitter address, dan
  sequence dari events transaksi bridge, sampai VAA bertanda tangan
  guardian muncul.
- Redeem: panggil `completeTransfer(bytes)` pada Token Bridge tujuan
  (Base Sepolia: `0x86F55A04690fd7815A3D802bD587e83eA888B239`) via walletd
  `eth_sendTransaction` dengan chainId EVM tujuan (Base Sepolia 84532).
  Pola persisnya di `scripts/complete_transfer2.py`: ambil nonce pending
  on-chain, gas price minimal 2x harga jaringan, tunggu receipt sampai
  240 detik, lalu bandingkan `balanceOf` wrapped token sebelum/sesudah.

### Bukti berjalan B (30 Okt 2026, datahub id 666)

- Bridge benar: digest Sui `EG1Z4sbdb6ameQ41Tfdia2BLSeUm5pdTK1jK8pHEBiM7`
  (VAA seq 1435) → `completeTransfer` Base Sepolia
  `0x3640f47046d880f13f73ac5d4ef14b2f3d12f4b24e0bd3e7b555dcc87c3c05d5`
  status sukses → saldo wrapped SUI burner EVM 0 → 50.000.000 unit
  (0,05 SUI). Dua sisi terverifikasi; blocker lama id 614/617 tertutup.

## Jebakan gabungan yang sudah terbukti

- SDK Cetus dan SDK Wormhole sama-sama menunjuk package lama; keduanya
  hanya berguna sebagai referensi komposisi fungsi (baca kode sumbernya),
  bukan sebagai sumber alamat.
- Simulasi yang lolos dengan package lama tidak menjamin eksekusi —
  `assert_version` muncul saat komposisi memakai package asli bridge.
- Alamat tujuan di PTB harus 32 byte; alamat EVM 20 byte tanpa left-pad
  membuat prepare_transfer gagal atau dana terkirim ke alamat sampah.
- Message fee wormhole di testnet adalah 0, tetapi argumen fee coin tetap
  wajib ada sebagai coin nol.
- Flaky RPC EVM daemon (`Remote end closed` dari publicnode) terjadi
  persis setelah broadcast; selalu rekonsiliasi nonce + receipt sebelum
  menyatakan gagal.

## Available connectors

- Tidak ada konektor untuk Cetus atau Wormhole. Skill ini memakai walletd lokal, gRPC/GraphQL Sui publik, dan WormholeScan langsung dari skrip.

- Use `muse.connector_search` to find other connectors and `muse.skill_search` to find related skills.

- If nothing here fits, look on the web for a maintained API or MCP server and set it up with [Custom Connectors and MCPs](/opt/muse/skills/custom-connector-setup/SKILL.md), or build a custom connector.

## Websites

- [Wormhole Connect / Docs — Contract Addresses](https://wormhole.com/docs/) untuk registry resmi chain id Wormhole dan alamat Token Bridge per jaringan. Verifikasi chain id tujuan (skema 1000x untuk EVM testnet) di sini sebelum menyusun PTB.

- [WormholeScan Testnet API](https://api.testnet.wormholescan.io/api/v1) untuk mengambil signed VAA berdasarkan emitter chain, emitter address, dan sequence.

## Alternatives for better results

- Untuk pendanaan awal dompet Sui testnet pakai skill `sui-faucet-v3-pow`. Untuk pola umum pemakaian daemon (swap/bridge/sign EVM dan non-EVM) pakai skill `walletd-interaction`.
