# Listing NFT di Agent Punk Market (BSC)

Skill ini menyimpan prosedur listing NFT di Agent Punk Market yang
terverifikasi lewat listing Nakamigos 29 Okt 2026 (token #10501 + #10531,
terverifikasi on-chain dari struct listing, bukan dari UI). Disimpan sebagai
skill per aturan perusahaan 29 Okt 2026 (alur terverifikasi wajib
didokumentasikan agar bisa dipakai ulang). Pakai skill ini setiap kali
me-listing NFT di pasar ini, di koleksi apa pun — fungsi, selector, dan
cara verifikasinya sama; yang berganti hanya alamat koleksi, tokenId,
harga, dan durasi.

## Perintah tetap yang mengikat skill ini

- **Harga dan durasi mengikuti parameter owner yang berlaku saat itu.**
  Jangan hardcode angka harga sebagai konstanta abadi. Contoh
  terverifikasi di bawah ($25, 90 hari) adalah contoh, bukan konstanta.
- **Durasi dalam HARI, maks 90.** Parameter ke-4 fungsi list adalah
  durasi dalam hari (terverifikasi probe: 1/7/30/90 OK; 168/720 dan
  timestamp absolut revert "Bad duration").
- **Preview dulu, eksekusi hanya bila preview sukses.** Tiap panggilan
  (approval maupun list) di-preview via baw dulu; requireConfirmation
  TRUE = berhenti (butuh konfirmasi di Binance App — aksi owner).
- **Verifikasi listing dari struct on-chain, bukan dari UI.** Harga ada
  di word5 struct listing; word1 adalah expiry, BUKAN harga (kesalahan
  parser lama).
- **Jangan klaim listing berhasil tanpa bukti struct.** Bukti sah =
  seller, harga, dan fillable/active dari struct listing() on-chain.

## Identitas terverifikasi (contoh pembuktian)

- Pasar: Agent Punk Market `0x149b6F713a1e544ED6Dc9905Afc22F03EEf94887`
  (BSC chain 56), fee 5%.
- Wallet penjual (Binance agentic):
  `0xYOUR_AGENTIC_WALLET`.
- Koleksi pembuktian: Nakamigos
  `0x2D7097E0f28Ea0fEB0b3b44c7d0ee0227d513103`, token #10501 + #10531.
- Contoh terverifikasi 29 Okt 2026: harga $25 = 0,032942 BNB, durasi 90
  hari, expiry on-chain 1801009325 (#10501) / 1801009358 (#10531);
  approval tx
  `0x96699ef8520bf1b685371ad16b59ee10fbbad5263ffa6565bc878205bdc05ba0`;
  list tx #10531
  `0x8b8e62b6a10f386afa045edc952ed97a6b446279627c36661912c4cb469b5dae`.

## Fungsi dan selector (dari skrip terverifikasi, bukan tebakan)

- `list(address collection, uint256 tokenId, uint256 price, uint256 duration)`
  — selector `0xbb74a1c2`.
- `setApprovalForAll(address operator, bool approved)` — selector
  `0xa22cb465`.
- `isApprovedForAll(address owner, address operator)` — selector
  `0xe985e9c5` (view, mengembalikan 1 bila approved).
- `listing(address collection, uint256 tokenId)` — selector `0x8de820f6`
  (view, mengembalikan struct 7 word).
- Encoding: alamat di-pad 24 nol di depan (32 byte), uint256 di-pad 64
  hex char. Jangan salin calldata dengan tangan — susun programatis dari
  selector + encoding (lihat `list_nakamigos.py`).

## Prasyarat

- Sesi baw login aktif (bila sesi kedaluwarsa, berhenti — re-pair adalah
  aksi owner, bukan agent).
- Harga BNB saat itu (CoinGecko simple price) untuk konversi harga USD →
  wei: `price_wei = round(harga_usd * 10^18 / harga_bnb)`.
- RPC baca: `https://bsc-dataseed.binance.org` dan
  `https://bsc-dataseed1.ninicoin.io`, dengan retry (skrip listing: 6
  putaran × 2 RPC, jeda 3 detik, timeout 15 detik). Jangan pakai defibit
  untuk eth_call ini (tidak stabil: approval-gated/timeout).

## Alur langkah-demi-langkah

### Tahap 1 — Cek approval

1. `eth_call` ke kontrak NFT: `isApprovedForAll(wallet, market)`
   (selector `0xe985e9c5` + wallet + market).
2. Bila hasil berakhir `01` (approved) → lanjut ke Tahap 3.
3. Bila belum approved → Tahap 2.

Verifikasi tahap: nilai isApprovedForAll terbaca on-chain (1 = approved,
0 = belum).

### Tahap 2 — Approval (hanya bila belum approved)

1. Susun data `setApprovalForAll(market, true)` (selector `0xa22cb465` +
   market + 1).
2. Preview: `baw contract-call preview --binanceChainId 56 --from
   <wallet> --to <kontrak NFT> --value 0 --inputData <data> --json`.
   Preview harus sukses.
3. Bila preview `requireConfirmation` TRUE → BERHENTI (butuh konfirmasi
   di Binance App — aksi owner).
4. Bila preview sukses + requireConfirmation FALSE → `baw contract-call
   execute --requestId <id> --json`.
5. Tunggu ±8 detik, lalu `eth_call` isApprovedForAll lagi — harus
   berakhir `01` sebelum lanjut.

Verifikasi tahap: isApprovedForAll = 1 on-chain; tx approval tercatat
sukses.

### Tahap 3 — Listing per token

1. Hitung `price_wei` dari parameter owner yang berlaku (harga USD +
   harga BNB saat itu).
2. Tentukan durasi dalam HARI (≤ 90, sesuai parameter owner).
3. Susun data `list(koleksi, tokenId, price_wei, durasi_hari)`
   (selector `0xbb74a1c2`).
4. Preview per token (flag `--inputData`, seperti Tahap 2). Preview harus
   sukses.
5. Bila `requireConfirmation` TRUE → BERHENTI (aksi owner).
6. Bila preview sukses + requireConfirmation FALSE → execute per token.
7. Tunggu ±8 detik per token sebelum verifikasi.

Verifikasi tahap: tiap token punya tx list sukses (status sukses).

### Tahap 4 — Verifikasi dari struct listing (wajib)

1. `eth_call` ke pasar: `listing(koleksi, tokenId)` (selector `0x8de820f6`
   + koleksi + tokenId).
2. Parse 7 word (masing-masing 64 hex char): word0 seller (alamat = 40
   hex char terakhir word), word1 expiry (unix), word2 fee, word3
   koleksi, word4 tokenId, word5 price (wei), word6 active/fillable.
3. Assert: seller == wallet penjual, price == price_wei yang dipasang,
   fillable/active == 1.
4. Hanya bila ketiga assert lolos, listing dinyatakan berhasil.

Verifikasi tahap: ketiga assert lolos untuk tiap token. Bila ada yang
gagal, listing BELUM terverifikasi — jangan laporkan berhasil.

## Pitfall

- **Durasi BUKAN detik dan BUKAN timestamp.** Parameter ke-4 adalah
  hari, maks 90. Nilai 168/720 dan timestamp absolut revert "Bad
  duration". Catatan: docstring lama di kepala `list_nakamigos.py`
  sempat menyebut detik — yang benar (terverifikasi probe + kode) adalah
  hari.
- **Harga di word5, BUKAN word1.** Parser lama yang membaca harga dari
  word1 SALAH — word1 adalah expiry (unix). Selalu baca harga dari
  word5.
- **Jangan pakai RPC defibit untuk eth_call ini.** Skrip listing sengaja
  hanya memakai bsc-dataseed + ninicoin dengan retry; defibit tidak
  stabil untuk panggilan ini.
- **Jangan hardcode harga.** Harga listing mengikuti parameter owner
  yang berlaku; contoh $25 / 0,032942 BNB hanya contoh terverifikasi
  29 Okt 2026.
- **Jangan verifikasi dari UI.** UI bisa menampilkan status yang belum
  tentu cocok dengan state kontrak; struct listing() adalah sumber
  kebenaran.
- **requireConfirmation TRUE = berhenti.** Jangan bypass dengan cara
  lain; itu butuh konfirmasi owner di Binance App.
- **Tunggu sebelum verifikasi.** State on-chain butuh beberapa detik
  setelah execute (±8 detik di skrip) sebelum terbaca konsisten.

## Sumber

- `~/workspace/divisi/airdrop-nft/eksekusi/list_nakamigos.py` (alur
  approval + list + verifikasi struct; RPC retry; contoh $25/90 hari).
- `~/workspace/divisi/airdrop-nft/eksekusi/cek_harga.py` (parser struct
  listing 7 word; koreksi word5 vs word1; selector-selector
  terverifikasi).
- Bukti on-chain 29 Okt 2026: listing #10501/#10531 (seller, harga,
  fillable terverifikasi dari struct).
