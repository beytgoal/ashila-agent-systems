# Skill: Testnet Token Launch + LP + Swap Dua Arah (kontrak langsung via walletd)

Prosedur TERVERIFIKASI end-to-end di Sepolia, 29 Okt 2026: deploy ERC20
sendiri → verifikasi Uniswap V2 resmi → approve → addLiquidityETH →
swapExactETHForTokens → swapExactTokensForETH, semua receipt status 0x1.
Jalur UI Uniswap TIDAK dipakai (gateway RPC Uniswap = HTTP 401 dari VM;
lihat `~/workspace/scratch/swap-test/UNISWAP-UI-TESTNET-FINDINGS.md`).

Hasil referensi (contoh sukses):
- Token MTST `0xe050c93bbf36b6d7fc251deeb760902fefbe2d7e`
  (deploy tx `0x681f013c9b09fb9747f0033d6a00ea863f37f3fc4c71ca361a5003b4225d2994`)
- Pair MTST/WETH `0x56f83e297550259afac4399b98f178c5cff5ae99`
- Driver + artefak: `~/workspace/scratch/swap-test/launch/`
  (`MTST.sol`, `compile.js`, `driver.py`, `state.json`)

## Arsitektur jalur

- **Transaksi**: selalu lewat walletd HTTP `127.0.0.1:18924` (signing +
  broadcast oleh daemon; kebijakan ≤0,5 native/tx). `wd.py` hanyalah
  wrapper CLI atas bridge HTTP yang sama.
- **Contract creation**: `wd.py send` mewajibkan `--to` → TIDAK bisa
  deploy. Deploy = POST `eth_sendTransaction` ke walletd dengan tx
  TANPA field `to`, `data` = bytecode creation, gas eksplisit.
  **Sejak 30 Okt 2026 POST langsung ini WAJIB header `X-Walletd-Token`
  dari `~/.burner/walletd.token`** (token pemanggil walletd) — tanpa
  header itu daemon menolak 401. Pola yang lebih disukai kini: deploy
  lewat Brain (`brain.py propose --to CREATE`), yang sudah membawa
  token + gerbang intent sekaligus.
- **Pembacaan chain**: lewat `curl` ke RPC publik chain. urllib python
  dari VM ini sering terputus (`RemoteDisconnected`/`IncompleteRead`)
  pada respons besar; curl stabil. walletd juga meneruskan read, tapi
  respons besar (getCode) sering gagal di jalurnya.

## Alamat Uniswap V2 Sepolia (dari docs resmi Uniswap, deployment-addresses)

- Factory: `0xF62c03E08ada871A0bEb309762E260a7a6a880E6` (getCode 13.859 byte)
- Router02: `0xeE567Fe1712Faf6149d80dA1E6934E354124CfE3` (getCode 17.944 byte)
- WETH: `0xfFf9976782d46CC05630D1f6eBAb18b2324d6B14` (getCode 3.124 byte)

WAJIB verifikasi silang sebelum pakai (pelajaran datahub id 419):
`eth_getCode` non-kosong untuk ketiganya + `Router02.factory()` ==
alamat Factory + `Router02.WETH()` == alamat WETH. Ketiganya lolos
29 Okt 2026. Untuk chain lain: ambil alamat dari docs resmi dulu,
lalu verifikasi yang sama — JANGAN pakai alamat dari memori.

## Langkah

1. **Kompilasi**: ERC20 minimal (name/symbol/decimals/totalSupply/
   balanceOf/allowance/transfer/approve/transferFrom; supply dicetak ke
   deployer di constructor). `npm i solc@0.8.26`, compile via solc-js
   (optimizer 200). Simpan `{abi, bytecode}` JSON.
2. **Deploy** via walletd (tanpa `to`). Verifikasi: receipt status 0x1,
   `contractAddress`, getCode > 0, `name()/symbol()/decimals()/
   totalSupply()/balanceOf(deployer)` sesuai parameter.
3. **Approve** Router02 untuk token (≥ jumlah LP + swap uji).
   Verifikasi `allowance(burner, router)` on-chain.
4. **Likuiditas**: `addLiquidityETH(token, amountToken, 0, 0, burner,
   deadline=now+1200)` + `value` ETH. Verifikasi: `factory.getPair(
   token, WETH)` ≠ 0x0, LP balance burner > 0, `getReserves()` terbaca.
5. **Swap A (ETH→token)**: quote `getAmountsOut` dulu; `amountOutMin` =
   99% quote; `swapExactETHForTokens(min, [WETH, token], burner,
   deadline)` + value. Verifikasi saldo token naik ≥ min, status 0x1.
6. **Swap B (token→ETH)**: `swapExactTokensForETH(amount, min,
   [token, WETH], burner, deadline)`. Verifikasi saldo token turun
   persis amount dan ETH naik ≈ quote − gas. CATATAN: baca saldo
   beberapa detik SETELAH receipt — node publik bisa lag dan membaca
   saldo lama (kejadian nyata 29 Okt: saldo terbaca "tidak berubah"
   padahal swap sukses; logs Transfer di receipt adalah bukti primer).

## Pelajaran keras (semua terbukti 29 Okt 2026)

- **eth_account 0.14 menolak alamat `to` all-lowercase** —
  `Transaction had invalid fields: {'to': ...}`. Semua alamat tujuan
  WAJIB EIP-55 checksum (`eth_utils.to_checksum_address`) sebelum
  dikirim ke walletd. Alamat dari receipt/`contractAddress` bisa
  lowercase — checksum-kan selalu.
- **Gas di Sepolia saat ini jauh di atas buku teks** (fork repricing;
  gasPrice sendiri ~150 wei jadi biaya tetap debu):
  deploy ERC20 kecil (runtime 1.705 byte) = 3.521.880 gas;
  approve = 128.084; addLiquidityETH + createPair pertama =
  19.150.555 (estimateGas 19.313.806); swap di pair yang ada =
  167k–346k. Aturan praktis: ambil `eth_estimateGas` untuk operasi
  berat (deploy/LP), kalikan ~1,25; untuk approve/swap pakai limit
  longgar (600k / 1,5 jt). Gejala kurang gas: status 0x0 dengan
  gasUsed ≈ limit persis.
- **`eth_estimateGas` node publik TIDAK selalu waras** (transfer ETH
  polos pernah diestimasi 12.000 < intrinsic 21.000) — pakai hanya
  sebagai orde besaran untuk operasi berat, putusan akhir selalu
  receipt.
- **JANGAN retry broadcast secara membabi buta.** Respons walletd bisa
  putus SETELAH tx ter-broadcast ("Remote end closed…") — retry buta
  pada deploy menghasilkan DUA kontrak identik (nonce 8 & 9). Pola
  aman di `driver.py::send()`: catat nonce sebelum kirim; bila respons
  ambigu, tunggu nonce bergerak lalu cari tx hash-nya via binary
  search `eth_getTransactionCount` per blok + isi blok itu. Fase-fase
  juga idempoten: approve cek allowance dulu, LP cek pair+LP dulu,
  swap cek state.
- **walletd bisa mati di tengah jalan** (watchdog VM me-restart massal
  tiap beberapa menit). Cek `curl -s http://127.0.0.1:18924/` = 501
  berarti hidup. Bila mati dan tidak pulih sendiri, hidupkan manual:
  `cd ~/workspace/superagentic-wallet/daemon && setsid nohup
  ~/workspace/.wallet-venv/bin/python walletd.py >> walletd.out 2>&1
  < /dev/null &` — JANGAN kill sesi exec yang menjalankan watchdog.
- Deadline selalu `now + 1200` dihitung saat kirim; batas nilai
  mengikuti kebijakan walletd (≤0,5 native/tx).
