---
name: sketchfab-assets
description: Cari, periksa lisensi, dan unduh model 3D dari Sketchfab lewat MCP server lokal (gregkop/sketchfab-mcp-server, ISC) untuk mengisi slot katalog aset pihak ketiga pipeline 3D divisi. Membutuhkan API token Sketchfab milik akun yang dipakai (Secure Vault). Gerbang lisensi per model WAJIB sebelum unduh/pakai.
---

# Sketchfab Assets (MCP lokal)

## Instalasi (sudah terpasang & teruji 2026-11-01)

- Repo: `~/workspace/divisi/branding-promosi/3d-agent/tools/sketchfab-mcp-server/` (gregkop/sketchfab-mcp-server, lisensi ISC, TypeScript/Node).
- Sudah `npm install` + `npm run build` → `build/index.js`; smoke test MCP lolos: server memperkenalkan diri sebagai `3d-model-mcp-server` dan mengekspos tool di bawah.

## Tool yang tersedia

| Tool | Fungsi | Parameter kunci |
| :--- | :--- | :--- |
| `sketchfab-search` | Cari model | `query`, `tags`, `categories`, `downloadable=true`, `limit` (1–24) |
| `sketchfab-model-details` | Detail + lisensi satu model | `modelId` |
| `sketchfab-download` | Unduh model | `modelId`, `format` (gltf/glb/usdz/source), `outputPath` |

Jalankan sebagai MCP stdio: `node build/index.js --api-key <TOKEN>` atau env `SKETCHFAB_API_KEY`.

## Status kredensial (per 2026-11-01 23:15 WIB)

- Token API Sketchfab akun owner (username cpktemon) SUDAH tersimpan di brankas sebagai koneksi `custom.sketchfab`, dan helper konektor ada di `~/workspace/custom-connectors/custom.sketchfab/bin/sketchfab.py` (dokumentasi: CONNECTOR.md di folder yang sama).
- TETAPI panggilan verifikasi `GET /v3/me` membalas 401: Sketchfab membaca token pribadi dengan skema `Authorization: Token <key>` (terbukti dari kode sumber server MCP lokal, index.ts baris 80), sedangkan koneksi brankas terdaftar dengan skema Bearer — dan tidak ada pilihan penempatan brankas yang bisa menambahkan awalan "Token". Jadi jalur API lewat konektor TERBLOKIR skema; jangan minta owner memasukkan ulang token yang sama.
- Server MCP lokal tetap jalur yang benar secara skema (mengirim `Token ...`), tetapi ia membaca kunci dari environment prosesnya sendiri dan nilai brankas tidak bisa dibaca balik ke sana. Aktivasi jalur ini butuh keputusan owner tersendiri.
- Jalur yang berfungsi HARI INI untuk cari/unduh model: sesi Sketchfab yang sudah masuk di browser (akun cpktemon), lewat situs web, tanpa token API.
- Akun Sketchfab BARU tidak bisa dibuat langsung lagi — pendaftaran hanya lewat Epic Games (terverifikasi 2026-11-01).
- JANGAN pernah minta token lewat chat dan jangan tulis token ke file/repo.

## Gerbang lisensi (TIDAK bisa ditawar)

1. Selalu panggil `sketchfab-model-details` dulu dan baca lisensi modelnya. Model Sketchfab berlisensi per model: CC0/CC-BY (sering wajib atribusi), CC-BY-NC (NON-komersial — DILARANG untuk konten monetisasi/brand), lisensi editorial (DILARANG komersial), atau berbayar.
2. Hanya unduh model yang lisensinya mengizinkan pemakaian yang direncanakan; untuk tayangan brand/monetisasi: CC0, CC-BY (dengan atribusi), atau lisensi berbayar yang sudah dibeli akun.
3. Setiap unduhan WAJIB dicatat di file lisensi di samping aset: nama model, URL Sketchfab, pembuat, jenis lisensi, teks atribusi yang diwajibkan, tanggal unduh. Pola sama seperti arsip lisensi CC0 Quaternius/KayKit di `3d-agent/uji-aset-glb/`.
4. Jangan distribusikan ulang file sumber model; yang tayang adalah render/video hasil produksi.
5. Unduh hanya model yang memang bisa diunduh akun (gratis downloadable atau sudah dibeli); server tidak membuka konten berbayar orang lain.

## Alur pakai

`search (downloadable=true)` → `model-details` (cek lisensi) → catat lisensi → `download` format `glb` → optimasi lewat skill `blender-web-pipeline` bila perlu → uji di viewer divisi sebelum masuk pipeline produksi.
