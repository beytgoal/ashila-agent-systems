---
name: brain-wallet-mediator
description: "Brain — mediator intent di atas walletd: gerbang propose → approve (exact-match) → deliver untuk eth_sendTransaction burner (termasuk intent CREATE/deploy kontrak testnet) dan intent tanda tangan pesan personal_sign/eth_signTypedData_v4 (v2), dengan policy cap per chain, allowlist tujuan, antrean intent, dan audit append-only. Terverifikasi lulus uji penuh 12 langkah + uji lanjutan (launch token, LP, swap dua arah, cabut LP, vault; 11 tx) di Sepolia 30 Okt 2026; v2 (sign + gerbang WS sign) dan v3 (semua cap dicabut, fee ikut chain, oracle Chainlink) terverifikasi 2 Nov 2026. Use when: brain.py, mediator intent walletd, propose/approve/deliver transaksi, intent personal_sign/signTypedData, gerbang transaksi burner, rekonsiliasi tx walletd."
---

# Skill: Brain — Mediator Intent di atas walletd

Brain adalah **mediator intent** di atas walletd: lapis gerbang prosedural
yang memisahkan *usulan* transaksi dari *eksekusinya*. Brain BUKAN ekstensi
browser, BUKAN injeksi provider (`window.ethereum`), dan BUKAN WalletConnect.

- File: `~/workspace/custom-connectors/custom.walletd/bin/brain.py`
- Jalankan dengan: `~/workspace/.wallet-venv/bin/python`
- `walletd.py` **TIDAK diubah** oleh lapis ini. Sejak revisi 2 Nov 2026
  22:18 WIB tidak ada cap nilai di lapis walletd juga (yang tersisa di
  sana hanya denylist alamat) — gerbang Brain adalah satu-satunya
  gerbang nominal/prosedural. Fee di semua jalur ikut gwei chain.
- Dokumen sumber: `~/workspace/custom-connectors/custom.walletd/CONNECTOR.md`
  (bagian "Brain (mediator intent)").

## State

Semua state di `~/workspace/custom-connectors/custom.walletd/state/`:

| File | Isi |
|---|---|
| `brain_policy.json` | Gerbang policy v1 (chain, method, cap, allowlist) |
| `intents.jsonl` | Antrean intent, append-only |
| `audit.jsonl` | Audit append-only — TANPA kredensial |

## Perintah

```bash
PY=~/workspace/.wallet-venv/bin/python
BIN=~/workspace/custom-connectors/custom.walletd/bin

$PY $BIN/brain.py check
$PY $BIN/brain.py propose --caller <nama> --chain <chain> \
    --method eth_sendTransaction --to <alamat|CREATE> --value <native> \
    --data <calldata> --reason "<alasan>"   # --reason WAJIB
$PY $BIN/brain.py propose --caller <nama> --chain <chain> \
    --method personal_sign --message "<teks>" --reason "<alasan>"
$PY $BIN/brain.py propose --caller <nama> --chain <chain> \
    --method eth_signTypedData_v4 --typed-data <json|@file.json> \
    --reason "<alasan>"
$PY $BIN/brain.py list
$PY $BIN/brain.py show --id <intent-id>
$PY $BIN/brain.py approve --id <intent-id> --hash <hash-intent> --by <nama>
$PY $BIN/brain.py reject  --id <intent-id> --by <nama> --note "<catatan>"
$PY $BIN/brain.py deliver --id <intent-id>
```

Aturan alur:

- `approve` bersifat **exact-match** (hash harus persis hash intent) dan
  **satu intent hanya bisa disetujui satu kali**.
- `deliver` hanya untuk intent berstatus `approved`, **satu kali, tanpa
  retry**, dan memverifikasi receipt sampai `status 0x1`.
- Sebelum kirim, `deliver` memanggil `eth_estimateGas` lewat walletd dan
  memakai estimasi itu **+ buffer 35%** sebagai gas limit. Jangan menulis
  gas manual per intent — estimasi + buffer adalah satu-satunya jalur.

## Intent CREATE (deploy kontrak)

- `propose --to CREATE` = intent **deploy kontrak**: `--data` berisi
  bytecode pembuatan kontrak, tx dikirim tanpa alamat tujuan.
- Hanya diizinkan di **chain testnet** terdaftar; di mainnet CREATE
  ditolak gerbang.
- `value` **wajib 0**.
- `intent_hash` dihitung dengan `to = "CREATE"` (string literal itu,
  bukan alamat) — approve tetap exact-match atas hash tersebut.
- Setelah deliver, `contractAddress` dari receipt dicatat di audit pada
  event `receipt_verified` — alamat itulah bukti deploy-nya.
- Kontrak hasil deploy yang terverifikasi **wajib segera didaftarkan ke
  allowlist** di `brain_policy.json` (lihat Policy) sebelum dipakai
  sebagai tujuan intent berikutnya — pendaftaran ini bagian dari
  prosedur, bukan langkah opsional.

## Policy v3 (berlaku sejak 2 Nov 2026 22:18 WIB; sign dari v2 22:14 WIB)

- Method: `eth_sendTransaction`, `personal_sign`, `eth_signTypedData_v4`.
- **SEMUA CAP NILAI DICABUT** (revisi owner 22:18 WIB, menggantikan
  rencana cap 0,005 dari 22:14/22:16: "bebaskan semuanya — ini
  decentralized, bukan perbankan"). `cap_wei` = **null** di semua chain
  `brain_policy.json` (mainnet, testnet, elysium) — tidak ada penolakan
  intent karena nilai, di Brain maupun walletd (cap walletd 0,5 native
  dan Elysium 0,05 HYPE ikut dicabut; sisa penolakan walletd hanya
  denylist alamat). Jangan pasang cap lagi tanpa perintah owner baru.
- **Fee ikut gwei chain di semua jalur walletd:** clamp gas Elysium
  0,1/0,2 gwei dicabut; pengali markup dicabut (WS/HTTP/fast_rpc
  1,8–2,5x; EIP-1559 maxFee 2,2x + priority 1,5x → baseFee + priority
  chain apa adanya). Satu-satunya penyesuaian tersisa adalah mekanik
  penerimaan chain: di Elysium, gasPrice diangkat ke TEPAT baseFee blok
  "pending" bila usulan chain di bawahnya (tanpa pengali/margin, tanpa
  cap atas) — baseFee chain di bawah itu memang tidak bisa inklusi.
- Yang TIDAK berubah: gerbang persetujuan intent (propose → approve
  exact-match → deliver/konsumsi sebelum signing) — itu alur izin
  owner, bukan cap.
- **Intent tanda tangan pesan (v2):** propose dengan `--message`
  (personal_sign) atau `--typed-data` (literal JSON atau `@file.json`).
  `intent_hash` untuk method sign = sha256 atas string kanonis
  `chain|method|sign|payload` — payload = pesan apa adanya, atau JSON
  kanonis typed data (kunci terurut, tanpa spasi; dikanonikkan sekali
  saat propose dan disimpan di record sebagai `message`/`typed_data`).
  Intent sign: value dipaksa 0, gerbang tujuan dilewati, approve tetap
  exact-match satu kali. `deliver` = walletd menandatangani lewat HTTP,
  lalu brain.py **memverifikasi recover == burner secara lokal sebelum**
  mencatat `executed` (signature disimpan di record transisi; audit
  event `signed`). Tanpa tx on-chain, tanpa receipt, nonce tidak berubah.
- Tujuan: burner sendiri
  `0xYOUR_BURNER_WALLET`, **plus kontrak terdaftar
  di allowlist**. Allowlist saat ini (Sepolia):
  - WETH9: `0xfFf9976782d46CC05630D1f6eBAb18b2324d6B14`
  - Factory Uniswap V2: `0xF62c03E08ada871A0bEb309762E260a7a6a880E6`
  - Router02 Uniswap V2: `0xeE567Fe1712Faf6149d80dA1E6934E354124CfE3`
  - Token BRNT: `0xa966BaFbE06Bc38eDda398DA4760223f5eC72Be1`
  - Pair BRNT/WETH: `0x25553714ba2d436Cef6Ca58a8787d70C6C9f1fe9`
  - BrainVault: `0x51A5D612fC8c60482F8CC7FF9EAAfD63f002F4aB`
  - Tiga alamat terakhir adalah kontrak hasil deploy lewat Brain
    sendiri (BRNT, pair-nya, BrainVault) — didaftarkan segera setelah
    deploy terverifikasi, sesuai prosedur intent CREATE di atas.
- Urutan gerbang (berurutan, berhenti di penolakan pertama):
  1. chain terdaftar → 2. method → 3. reason ada → 4. payload sign valid
  (method sign) / cap nilai → 5. allowlist tujuan (hanya
  eth_sendTransaction).
- Semua penolakan tercatat di `audit.jsonl` sebagai
  `policy_rejected` / `approval_rejected` / `deliver_rejected`.

## Bukti lulus (30 Okt 2026)

- Uji 12 langkah di Sepolia **lulus semua**.
- Tx bukti: `0x59a04a000bac3412598baea5d5a66855b48d98645405c84eb0e2fda8b2f65429`
  — transfer ke diri sendiri 0,001 ETH, receipt `0x1`, nonce 17→18.
- Transkrip uji: `state/uji-brain-2026-10-30.log`
  (di folder state di atas).

## Bukti lulus lanjutan (30 Okt 2026, 17:04–17:22 WIB)

Uji lanjutan lewat Brain di Sepolia (datahub id 703) — semua operasi
DeFi dasar dijalankan sebagai intent propose → approve → deliver:

- **Launch token BRNT** (`0xa966BaFbE06Bc38eDda398DA4760223f5eC72Be1`,
  supply 1.000.000) via intent CREATE.
- **Add LP**: 0,01 ETH + 100.000 BRNT ke pair BRNT/WETH
  (`0x25553714ba2d436Cef6Ca58a8787d70C6C9f1fe9`) → LP diterima
  31,622776.
- **Swap dua arah, persis quote**: ETH→BRNT menghasilkan +9.066,108938
  BRNT; BRNT→ETH sebesar 1.000 BRNT.
- **Cabut LP 25%**: 7,905694 LP dibakar → kembali 22.983,47 BRNT +
  0,00272 ETH; sisa LP 23,717082.
- **Vault**: deploy BrainVault
  (`0x51A5D612fC8c60482F8CC7FF9EAAfD63f002F4aB`), deposit 0,002 ETH,
  lalu withdraw penuh bersih.
- Total **11/11 tx receipt `0x1`**, nonce burner naik berurutan
  **18→29** (tanpa lompatan, tanpa dobel).
- Transkrip: `state/uji-brain-lanjutan-2026-10-30.log`.

## Bukti lulus v2 (2 Nov 2026, keputusan owner 22:14 WIB)

Transkrip lengkap: `~/workspace/superagentic-wallet/daemon/uji-brain-v2-2026-11-02.log`
(skrip WS: `daemon/uji_brain_v2.py`). Semua lulus:

- **Brain personal_sign (Sepolia):** intent `0fa422a7…`, signature
  `d743cd8d…`, recover == burner (diverifikasi brain.py + independen).
- **Brain eth_signTypedData_v4 (Sepolia):** intent `699682bf…`, signature
  `8c8dc3bd…`, recover == burner, match true.
- **Policy mainnet tanpa broadcast:** propose ethereum 0,005 LOLOS
  gerbang (intent lalu di-reject, tidak pernah di-deliver); 0,006
  `policy_rejected` (cap 5000000000000000 wei). Nol tx mainnet.
- **Gerbang WS (Elysium):** personal_sign tanpa intent DITOLAK; dengan
  intent approved signature `30c7e07d…` recover == burner; replay
  DITOLAK; eth_signTypedData_v4 signature `6ff60128…` recover == burner;
  regresi eth_sendTransaction WS lolos (tx `0xa387efc0…`).
- **Regresi Brain eth_sendTransaction (Sepolia):** self-send 0,001 ETH,
  tx `0x3e11299e…`, receipt `0x1` — alur v1 tidak berubah.
- walletd direstart berbasis PID untuk memuat kode baru (3143 → 18049
  oleh watchdog); HTTP 18924 → 501, forwarder 18888 CONNECT hidup.

## Bukti revisi v3 + oracle (2 Nov 2026, keputusan owner 22:18 + 22:21 WIB)

Transkrip: `~/workspace/superagentic-wallet/daemon/uji-brain-v2-revisi-2026-11-02.log`.
Semua lulus:

- **Cap dicabut (Brain):** propose ethereum 1 native / sepolia 10 /
  elysium 1 semua LOLOS gerbang (lalu di-reject; nol broadcast).
- **Cap dicabut (walletd):** `wd.py send` elysium 0,1 HYPE (2x cap lama)
  tidak lagi `policy denied` — sampai ke chain dan gagal dana, bukti
  policy_check bersih.
- **Sign tidak berubah & regresi lulus:** Brain personal_sign Sepolia
  signature `9c4c51aa…` recover == burner; WS Elysium 7/7 (tanpa intent
  ditolak, dengan intent recover == burner, replay ditolak, tx lolos).
- **Transaksi nyata:** Sepolia self-send tx `0xbcba8bce…` receipt `0x1`;
  Elysium self-send tx `0x0096dd8a…` receipt `0x1`.
- **Bukti gas on-chain:** effectiveGasPrice kedua tx Elysium (HTTP +
  WS) = 0,10011 gwei — persis baseFee chain yang berlaku, bukan clamp/
  lift/pengali lama.

## Oracle harga — Chainlink (2 Nov 2026, perintah owner 22:21 WIB)

- Helper: `~/workspace/custom-connectors/custom.walletd/bin/price_oracle.py`
  — `price_usd(chain)` / `gas_gwei(chain)`; CLI `price --chain X`,
  `price --all`, `gas --chain X`, `feeds`. Membaca feed AggregatorV3
  via eth_call lewat walletd (keyless); decimals dinamis; staleness dari
  `latestRoundData().updatedAt` vs heartbeat.
- Feed aktif (semua terverifikasi on-chain via `description()`):
  ethereum ETH/USD `0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419`, base
  ETH/USD `0x71041dddad3595F9CEd3DcCFBe3D1F4b0a16Bb70`, bsc BNB/USD
  `0x0567F2323251f0Aab15c8dFb1967E4e8A7D42aeE`, polygon MATIC/USD (=POL)
  `0xAB594600376Ec9fD91F8e885dADF0CE036862dE0`, sepolia ETH/USD
  `0x694AA1769357215DE4FAC081bf1f309aDC325306`.
- **Fallback jujur:** elysium, base-sepolia, bsc-testnet, amoy TIDAK
  punya feed → `available=false, price=null`. Jangan pernah mengarang
  harga untuk chain itu.
- **Alchemy: TIDAK ADA API key** di brankas/konektor (dicari 2 Nov
  2026) — belum dipakai; perlu pendaftaran akun gratis oleh owner bila
  ingin RPC cadangan. Chainlink keyless sudah mencukupi kebutuhan
  harga; data gas tetap dari eth_gasPrice chain lewat walletd.

## Pelajaran transport — rekonsiliasi sebelum intent pengganti

Respons walletd → RPC publik bisa **putus SETELAH broadcast**
(`Remote end closed connection without response`). Akibatnya catatan
Brain bisa menyimpang dari kenyataan on-chain dua arah:

- Brain mencatat `execution_failed` padahal tx-nya **sukses** on-chain
  (receipt tidak sempat terbaca), atau
- panggilan kirim tampak error padahal tx **sudah ter-broadcast**.

**ATURAN KERAS: jangan pernah propose/deliver intent pengganti sebelum
rekonsiliasi.** Urutan rekonsiliasi:

1. Cek nonce burner pada **dua pembacaan berjarak**: naik berarti tx
   sudah masuk rantai; diam berarti kemungkinan pra-broadcast.
2. Scan blok/receipt lewat RPC publik untuk menemukan tx dari nonce
   tersebut dan baca status receipt-nya.
3. Intent hanya boleh **dibuang** bila terbukti **pra-broadcast**
   (nonce diam pada dua cek). Bila nonce naik, intent dianggap
   terkirim — cocokkan receipt-nya, jangan kirim ulang.

Pengalaman run lanjutan 30 Okt: **5 dari 11 receipt tidak tercatat
oleh Brain** tapi terbukti sukses on-chain lewat rekonsiliasi;
**9 intent buangan** (pengganti yang sempat dibuat saat ragu) semuanya
terbukti pra-broadcast; hasil akhir **nol tx ganda**.

## BATAS JUJUR — baca sebelum mengandalkan Brain

1. **Mediator adalah gerbang prosedural untuk alur agen.** Sejak
   30 Okt 2026 ~18:29 WIB walletd punya **token pemanggil** di HTTP
   18924 (keputusan owner menutup temuan TINGGI uji keamanan): POST
   tanpa/salah header `X-Walletd-Token` → HTTP 401; rahasia di
   `~/.burner/walletd.token` (0600), daemon membaca ulang tiap request
   (rotasi tanpa restart, fail-closed). Bypass tanpa kredensial —
   termasuk probe C3 asli dan vektor browser/CORS — TERTUTUP (uji 9/9
   PASS, transkrip `daemon/uji-caller-token-2026-10-30.log`). Sisa
   batas yang jujur: proses lokal tepercaya yang memegang token
   (wd.py/brain.py sendiri) tetap bisa memanggil daemon langsung;
   Brain tetap gerbang prosedural yang menertibkan alur kerja agen,
   token mengautentikasi *siapa pemanggilnya*.
2. **Sejak v2 (2 Nov 2026), `personal_sign` + `eth_signTypedData_v4` EVM
   ikut masuk gerbang** (intent sign, lihat Policy v2 dan gerbang WS di
   bawah). Yang masih di luar gerbang Brain: metode baca/sign lain dan
   transfer non-EVM (Solana/Sui/Cosmos) — jalur itu tetap lewat
   `wd.py`/walletd langsung dengan policy walletd saja. Catatan jujur
   yang tidak berubah: intent sign Brain memberi *signature yang sah*,
   bukan *sesi login* di situs dApp (situs tetap memverifikasi state
   sesinya sendiri).

## Gerbang tunggal: jalur WS/ekstensi WAJIB Brain (30 Okt 2026, datahub id 709)

Perintah owner 17:47 WIB: jalur browser VM tidak lagi boleh melewati Brain.
- walletd melayani HTTP 18924 (lokal: wd.py/brain.py deliver — tidak digerbang ganda) dan WS 18923 (pintu ekstensi: ekstensi → forwarder 18888 → saw-relay 18925 → WS). Gerbang `brain_gate_ws()` di walletd.py terpasang di handler WS.
- `eth_sendTransaction` via WS wajib intent Brain approved dengan hash kanonis yang sama (`sha256 chain|method|to_lower|value_wei|data`), belum terkonsumsi. Konsumsi dicatat SEBELUM signing (fail-closed) ke `state/ws_consumed.jsonl` + audit `ws_consumed`; sesudah broadcast, audit `ws_delivered` dengan tx_hash. walletd tidak menulis intents.jsonl; brain.py meng-overlay ws_consumed.jsonl sehingga intent terkonsumsi tampil `executed` + `via:"ws"` dan tidak bisa di-deliver ulang via HTTP.
- Penolakan: JSON-RPC -32000 `brain approval required: …` + log daemon `BRAIN-GATE DENY/ALLOW`.
- `personal_sign` + `eth_signTypedData_v4` via WS: **sejak Brain v2 (2 Nov 2026) digerbang intent sign** — `brain_gate_ws_sign()` di walletd.py mewajibkan intent Brain approved yang hash kanonisnya (`chain|method|sign|payload`) cocok persis dengan payload permintaan, belum terkonsumsi; intent dikonsumsi SEBELUM signing (fail-closed, replay ditolak). Tanpa intent: tetap ditolak -32000 `brain approval required: …`. Signing WS TIDAK pernah bebas/auto-approve. Bukti uji v2: tanpa intent ditolak, dengan intent signature recover == burner, replay ditolak (transkrip `daemon/uji-brain-v2-2026-11-02.log`, skrip `daemon/uji_brain_v2.py`).
- `wallet_switchEthereumChain` TIDAK digerbang (bukan tanda tangan, tidak menggerakkan dana).
- Bukti uji (17/17 PASS, transkrip daemon/uji-brain-gate-2026-10-30.log): tanpa intent ditolak (nonce diam), dengan intent lulus sekali (tx 0xc31886…, nonce +1), replay ditolak, baca WS bebas, regresi HTTP penuh lulus (receipt_verified).
- Batas tersisa: tanda tangan non-EVM via WS belum digerbang (belum ada format intent). POST langsung ke HTTP 18924 kini wajib token pemanggil (lihat BATAS JUJUR #1) — tanpa token ditolak 401, dengan token tetap melewati Brain secara prosedural.

## Nama resmi sistem (30 Okt 2026)

Owner menamai keseluruhan sistem ini **Super Agentic BrainD Wallet** (BrainD = Brain + Daemon/walletd). Nama file brain.py dan walletd.py tidak berubah; "Super Agentic BrainD Wallet" adalah nama sistem/produknya, dipakai di diagram, laporan, dan komunikasi. Folder proyeknya memang sudah bernama superagentic-wallet sejak awal.
