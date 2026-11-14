# Universal 3D Procedural Production Agent

Agen produksi animasi 3D generik & prosedural: dari perintah "buatkan video 3D
tentang X" menjadi video ilustrasi 3D 9:16 siap storyboard — lewat 3 tahap
otomatis: (1) Blender Python/BPY memodelkan objek dari primitif, (2) Three.js +
GLSL uber-shader merendernya, (3) perekaman kanvas deterministik ke mp4.

> **Jalur terverifikasi di VM ini (2026-10-27):** Blender 4.5.0 resmi (download
> dari blender.org BERHASIL, bukan fallback) + Three.js r186 vendored lokal +
> **frame-stepping Playwright → ffmpeg** (PRIMARY). CCapture real-time TIDAK
> stabil di headless SwiftShader (terlalu lambat untuk 60fps real-time) —
> frame-stepping adalah jalur perekaman yang terverifikasi. Fallback
> pure-Python .glb builder TIDAK dibutuhkan di VM ini (Blender jalan) dan
> TIDAK diimplementasikan — jangan klaim sebaliknya.

## Kapan pakai skill ini

- Owner minta video ilustrasi 3D tentang objek/sistem apa pun (AC, jembatan,
  mesin, diagram 3D, arsitektur, konstruksi).
- Hasilnya video ilustrasi TANPA VO (VO ditambahkan divisi nanti) untuk disusun
  jadi storyboard konten (format kalbotau "BIKIN …" / template "edukasi").

## Template "ilustrasi" (disetujui owner 2026-10-27 ~08:49 WIB)

Template resmi video ilustrasi 3D untuk storyboard konten (format kalbotau
"BIKIN …"). **Bila permintaan menyebut "pakai template ilustrasi", pakai
bagian ini — jangan rancang ulang dari nol.**

Definisi lengkap (parameter persis dari video AC): `templates/specs/template-ilustrasi.json` v1.0. Video acuan: `divisi/branding-promosi/3d-agent/ac-cycle-3d.mp4` (42 dtk, 1080×1920, 7 scene, tanpa VO).

**Alur (rantai BIKIN, 7 scene × 6 detik):**

| Scene | Peran | Kicker | Contoh (AC) |
|---|---|---|---|
| 1 | Versi 1 — masalah / percobaan awal yang GAGAL | `BIKIN {X} — VERSI 1` | ES BATU + KIPAS |
| 2–6 | Komponen 1–5, satu komponen per scene, urutan sebab-akibat | `KOMPONEN {n} — {NAMA}` | KOMPRESOR MEMADATKAN GAS |
| 7 | 2 shot: komponen terakhir (3,5 dtk) + twist/penutup (2,5 dtk) | `PENUTUP` (shot 2) | AC MEMINDAHKAN PANAS |

Body scene 1 selalu diakhiri kata `GAGAL`; body shot penutup selalu memuat
twist + kalimat `Selamat, kamu udah bikin {X}!`.

**Gaya label (overlay viewer.html, gaya template "edukasi" — JANGAN diubah
tanpa perintah owner):** bg #faf8f4; font Noto Sans (headline ExtraBold);
kicker 34px abu-abu #6a6a6e + titik biru ● #0064ff, top 64px left 64px;
headline 88px hitam #141416, keyword dalam kotak biru #0064ff teks putih,
≤ ~20 karakter/baris; caption bawah 40px, bottom 150px; penanda `SCENE n/7`
30px abu-abu; progress bar #0064ff di atas #e3dfd8, bottom 110px.

**Format:** 1080×1920 9:16, 30 fps, 42 dtk (7×6), tanpa VO, tanpa musik.
**Visual:** AmbientLight 0.85 + DirectionalLight 2.4 (shadow 2048,
PCFShadowMap); uber-shader Fresnel rim 0x9fd0ff (0.35 / 0.85 aktif) + noise
3D ±3.5%; scale-in komponen 1.2 dtk + naik 0.25m, komponen lain di-dim
opacity 0.35; kamera per-shot az/el/dist lerp 0.6 dtk, FOV 40°.
**Palet material:** lihat `template-ilustrasi.json` (Utama putih, Sekunder
gelap, Tembaga, Panas oranye emissive 0.6, Dingin biru emissive 1.2, Es,
Dinding abu-abu, Lantai, Layar). Aturan kontras: dinding abu-abu vs unit
putih.

**Cara pakai untuk topik baru:** riset dulu → pecah jadi rantai BIKIN →
salin `template-ilustrasi.json` jadi `templates/specs/<topik>.json` (isi
`components` + `materials`, format seperti `ac_cycle.json`) → tulis
`templates/scenes-<topik>.json` (format seperti `scenes-ac.json`) → builder
Blender → probe tiap scene → record → storyboard → QA gate.

**Contoh pemetaan (DRAF, belum dirender):** "Kok jembatan bisa kuat?" —
bambu patah → gelagar → pilar → kabel → siar muai → rangka pengaku →
penutup "KAMU BIKIN JEMBATAN!" — lengkap di `template-ilustrasi.json`
(`contoh_pemetaan`). Fakta struktur wajib diverifikasi dari riset sebelum
produksi.

**Model 3D boleh dari dua jalur** (lihat "Input gambar → mesh (image-to-3D)"
di bawah): primitif prosedural BPY (Tahap 1) ATAU mesh hasil image-to-3D.
Gaya visual dan aliran scene tetap template ini.

## Lingkungan (terverifikasi 2026-10-27)

| Komponen | Status |
|---|---|
| Blender 4.5.0 Linux x64 | **Jalur kanonis: `~/workspace/blender/blender`** (symlink → `~/workspace/scratch/3d-agent/blender-4.5.0-linux-x64/`; tarball 376MB di sampingnya) — headless OK (`blender -b --factory-startup -noaudio`); BPY terverifikasi (`BPY_OK (4,5,0)`, `MATHUTILS_OK`, 27 Okt 2026) |
| Node v24.22.1, npm 10.9.4 | OK |
| three.js 0.186.1 | npm OK; **wajib vendor-kan** `three.module.js` + `three.core.js` (r186: module.js re-export dari core.js) + `addons/loaders/GLTFLoader.js` + `addons/utils/{BufferGeometryUtils,SkeletonUtils}.js` |
| playwright-core 1.49.1 | OK; Chromium `~/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome` (bukan `chrome-linux/chrome`!) |
| CCapture.js 1.1.0 | npm OK, ter-vendor; real-time capture TIDAK stabil headless (lihat di bawah) |
| ffmpeg 8.1.2 | OK |
| WebGL | WebGL 2.0 via SwiftShader (`--enable-unsafe-swiftshader --use-angle=swiftshader --no-sandbox`) |
| TripoSR (image-to-3D, opsional) | **TERUJI 27 Okt 2026** — venv `~/workspace/scratch/image-to-3d/venv` (torch 2.14.1+cpu, trimesh 4.0.5); bobot 1,56 GB di HF cache; inferensi CPU ~60 dtk, RAM puncak ~2,8 GB; ekspor **OBJ** (GLB langsung gagal — bug `.ptp()` NumPy 2); konverter `bin/obj_to_glb.py` |
| /tmp | 512MB tmpfs — JANGAN taruh node_modules/venv/frame di /tmp; pakai `~/workspace/scratch/` dan direktori proyek |
| VM restart | Sering terjadi (~22:25, ~03:53 WIB 26–27 Okt) — **semua script harus resume-safe** (frame-stepping skip frame yang sudah ada) |

## TAHAP 1 — Pemodelan (Blender Python / BPY)

Template: `templates/blender_build.py`. Spesifikasi: `templates/specs/<objek>.json`.

```bash
~/workspace/blender/blender -b --factory-startup -noaudio \
  --python templates/blender_build.py -- templates/specs/ac_cycle.json
# output: <project>/assets/<objek>.glb
# (jalur kanonis ~/workspace/blender/blender = symlink ke
#  ~/workspace/scratch/3d-agent/blender-4.5.0-linux-x64/blender)
```

### Format spec JSON

```json
{
  "name": "ac_cycle",
  "output": "/home/user/workspace/divisi/branding-promosi/3d-agent/assets/ac_cycle.glb",
  "materials": {
    "Material_Utama":   { "color": [0.95,0.95,0.96,1], "metallic": 0.05, "roughness": 0.5 },
    "Material_Tembaga": { "color": [0.72,0.35,0.16,1], "metallic": 0.9,  "roughness": 0.3 },
    "Material_Panas":   { "color": [0.85,0.22,0.0,1],  "metallic": 0.0,  "roughness": 0.6,
                          "emissive": [0.9,0.2,0.0,1], "emission_strength": 0.6 }
  },
  "components": [
    { "name": "Kompresor", "parts": [
      { "name": "BadanKompresor", "type": "cylinder", "loc": [1.0,0.35,-0.5],
        "rot": [0,0,0], "radius": 0.32, "depth": 0.75, "material": "Material_Sekunder" },
      { "name": "KumparanTembaga", "type": "torus", "loc": [1.0,0.85,-0.5],
        "rot": [0,0,0], "major_radius": 0.3, "minor_radius": 0.05, "material": "Material_Tembaga" }
    ]}
  ]
}
```

- **Koordinat Blender (Z-up):** `loc: [x, y, z]`, z = tinggi. Primitif:
  `box` (size [x,y,z]), `cylinder` (radius, depth, rot agar sumbu tegak/miring),
  `sphere` (radius), `torus` (major_radius, minor_radius), `cone` (radius1,
  radius2, depth — kerucut terbalik untuk uap/panas), `pipe` (path titik-titik →
  rangkaian cylinder + sphere sambungan).
- **Builder otomatis:** UV unwrap (Smart UV Project) tiap mesh, material
  dinamis per tipe (`Material_Utama/Sekunder/Tembaga/Cairan/Panas/Dingin/Es/
  Dinding/Lantai/Layar` — tambah sesuai objek), tiap komponen jadi grup
  (empty) bernama, ekspor **satu** `.glb` (glTF 2.0).
- **Aturan warna (pelajaran AC):** objek putih vs dinding harus KONTRAS —
  dinding [0.72,0.72,0.77] (abu-abu), unit putih [0.95]. Warna panas:
  oranye dalam [0.85,0.22,0] + emissive 0.6 — emissive >1.0 + matahari kuat
  = overexposure (kuning pucat) di bawah ACES tone mapping.
- **Validasi .glb:** magic `glTF`, jumlah mesh & material, semua nama komponen
  ada. (`python3 -c` baca header + JSON chunk.)

### Merancang objek baru (prosedur agen)

1. Pecah objek jadi komponen (maks ~8, tiap komponen 1–8 part primitif).
2. Tentukan skala kasar dalam meter (ruangan ~4×3m; komponen 0.3–1.5m).
3. Tulis spec JSON → jalankan builder → cek `.glb` (ukuran, mesh, material).
4. Bila ada part yang "tenggelam" (mis. vent strip di dalam body) — periksa
   urutan z/depth: part depan harus punya z lebih kecil (ke arah kamera) dari
   face body.

### Jalur alternatif Tahap 1 — image-to-3D (TERUJI 2026-10-27, opsional)

Bila bentuk terlalu rumit untuk primitif, generate mesh dari SATU foto
referensi benda asli (TripoSR, MIT) lalu konversi ke `.glb`. **Bukan
pengganti primitif** — hasilnya storyboard-grade (lihat batasan di bawah),
tapi bentuknya identik dengan benda aslinya dari depan.

Setup (sudah terpasang 27 Okt 2026 — jangan install ulang tanpa alasan):
`~/workspace/scratch/image-to-3d/` — venv `venv/` (Python 3.12, torch
2.14.1+cpu, trimesh 4.0.5, rembg, xatlas, moderngl), repo `triposr/`
(VAST-AI-Research/TripoSR), bobot `~/.cache/huggingface/hub/models--stabilityai--TripoSR`
(`model.ckpt` **1,56 GB** — bukan 588 MB seperti perkiraan awal), rembg
`~/.u2net/u2net.onnx` (176 MB).

```bash
cd ~/workspace/scratch/image-to-3d
# 1) Foto -> mesh OBJ (detached: VM sering restart; model load ~2 mnt,
#    inferensi ~60 dtk; RAM puncak ~2,8 GB — jalan saat VM sepi)
setsid nohup env OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 TORCH_NUM_THREADS=2 \
  ./venv/bin/python -u triposr/run.py <foto.jpg> --device cpu \
  --chunk-size 4096 --mc-resolution 128 --model-save-format obj \
  --output-dir ./output > /tmp/triposr-run.log 2>&1 < /dev/null & disown
# output: output/0/mesh.obj (+ input.png = foto setelah hapus background)

# 2) OBJ -> .glb (Blender; perbaiki orientasi + warna + bungkus grup)
~/workspace/blender/blender -b --factory-startup -noaudio \
  --python <skill>/bin/obj_to_glb.py -- output/0/mesh.obj <project>/assets/<objek>.glb <NamaKomponen>
# output: .glb dengan group bernama <NamaKomponen> berisi mesh

# 3) Render scene tes seperti biasa (Tahap 2+3): viewer + record_frames.
#    Front (kipas menghadap kamera) dicari dulu via probe 4 sisi
#    (az 0/90/180/270) — TripoSR tidak menjamin arah depan.
```

Aturan & jebakan (semua terverifikasi 27 Okt 2026, jangan ulangi):
- **Wajib `--model-save-format obj`** — ekspor GLB langsung GAGAL:
  `AttributeError: ndarray has no attribute 'ptp'` (trimesh 4.0.5 vs NumPy 2.0).
  JANGAN downgrade numpy ke 1.x — torch 2.14 butuh NumPy 2 (`np.long` hilang di 1.x).
  Jangan tambal `ndarray.ptp` (tipe immutable). Rute OBJ → Blender aman.
- **Build `torchmcubes`**: butuh `pybind11` + `scikit-build-core` + `ninja`
  terinstall dulu + flag `--no-build-isolation`:
  `./venv/bin/pip install --no-build-isolation git+https://github.com/tatsy/torchmcubes.git`
- **Orientasi**: OBJ TripoSR itu Z-up; importer Blender mengira Y-up dan
  menambah rotasi -90° X → mesh terbaring (kipas berdampingan horizontal).
  `obj_to_glb.py` membuang rotasi importer itu (`rotation_euler = (0,0,0)`)
  — JANGAN `transform_apply` rotasi (diam-diam tidak jalan headless, dan
  +90° adalah arah yang salah). Verifikasi dari GLB: sumbu panjang harus di
  komponen Y POSITION (glTF Y-up = atas).
- **Warna**: vertex color TripoSR gelap (mean lum ~0,35, unit aslinya krem
  terang) — converter mengangkat ×1,6 (clamp 1,0). Tetap gelap di kipas
  (grille memang gelap) — terima sebagai batasan, jangan klaim identik.
- **Wajib grup bernama**: mesh image-to-3D HARUS dibungkus empty group
  bernama komponen — logika pivot viewer MENGHAPUS mesh telanjang
  (`grp.children` kosong → `grp.parent.remove(grp)`).
- **Kualitas (uji unit outdoor AC Mitsubishi, 27 Okt 2026)**: dari depan
  TERKENALI (dua kipas bundar tersusun vertikal seperti foto); permukaan
  bergelombang/low-poly (mc 128); belakang/samping gumpalan kasar; proporsi
  terjepit (lebar 0,36 vs tinggi 0,92 — unit asli ~0,8 : 0,9); tanpa tekstur,
  hanya vertex color. Video tes 6 dtk:
  `divisi/branding-promosi/3d-agent/image-to-3d-test/image-to-3d-test.mp4`
  (1080x1920, 30 fps, 180 frame).
- **Yang DITOLAK lokal (butuh GPU)**: TRELLIS.2 (24 GB VRAM), Hunyuan3D-2.1
  (29 GB full pipeline), Stable Fast 3D (bobot HF gated — butuh approval),
  LGM / Zero123++ (GPU). Opsi API berbayar (tidak dibeli, tidak diminta
  kunci): lihat laporan `divisi/branding-promosi/3d-agent/image-to-3d.md`.
- **Tripo API V3 (DICOBA 27 Okt 2026 — TERBLOKIR saldo API 0)**: akun Free
  (200 kredit Studio) ternyata saldonya **tidak masuk ke API**
  (`GET /v3/account/balance` → balance 0.00, frozen 0.00); semua submit
  ditolak `code 2010 insufficient credit`, bahkan geometri saja. Uji
  perbandingan vs TripoSR BELUM terjawab — butuh top-up pay-as-you-go
  (~$0,20–0,60/model uji). Alur V3 yang terverifikasi: `POST /v3/files`
  (multipart) → file_token; `POST /v3/generation/image-to-model` JSON
  dengan `file: {"file_token": ...}` (OBJEK, bukan string!) + `model`
  WAJIB (`v3.1-20260211` dst.); `image_url` TIDAK diterima; poll
  `GET /v3/tasks/{id}`; `output.model_url` kedaluwarsa 5 menit. Python
  urllib ke openapi.tripo3d.ai DIPUTUS — pakai curl. Output free Tripo =
  non-komersial + model publik (uji saja, JANGAN dipakai di konten).
  Detail: laporan `divisi/branding-promosi/3d-agent/image-to-3d-tripo-test.md`.

## TAHAP 2 — Engine visual (Three.js + GLSL)

Template: `templates/viewer.html` (+ `templates/scenes-<objek>.json`).
Instance kerja: salin ke `<project>/viewer/` + vendor ke `viewer/vendor/`.

```bash
cp templates/viewer.html <project>/viewer/index.html
cp templates/scenes-ac.json <project>/viewer/scenes.json
cp <project>/assets/<objek>.glb <project>/viewer/assets/
cp node_modules/three/build/{three.module.js,three.core.js} <project>/viewer/vendor/
cp node_modules/three/examples/jsm/loaders/GLTFLoader.js <project>/viewer/vendor/addons/loaders/
cp node_modules/three/examples/jsm/utils/{BufferGeometryUtils,SkeletonUtils}.js <project>/viewer/vendor/addons/utils/
cp node_modules/ccapture.js/build/CCapture.all.min.js <project>/viewer/vendor/
```

### Yang ada di viewer.html

- **Importmap lokal** (tanpa CDN): `three` → `./vendor/three.module.js`,
  `three/addons/` → `./vendor/addons/`.
- **Pencahayaan:** AmbientLight 0.85 + DirectionalLight 2.4 (shadow map 2048,
  `PCFShadowMap` — `PCFSoftShadowMap` DIHAPUS di r186) + fill light.
- **Uber-shader** (`onBeforeCompile` pada MeshStandardMaterial — shadow &
  lighting tetap jalan): Fresnel rim glow (`pow(1-dot(V,N),3)`, rim 0x9fd0ff,
  0.35 / 0.85 saat komponen aktif) + noise nilai 3D (`vnoise(vWPos*7)`,
  ±3.5% diffuse). Uniform `uTime`, `uActive`.
- **Animasi tahapan:** tiap komponen dibungkus pivot di tengah bbox-nya —
  scale-in 1.2 detik + naik 0.25m saat scene-nya mulai; komponen lain
  di-dim (opacity 0.35, nonaktif). Kipas/bilah berputar
  (`rotation.z += t*6`); kerucut uap/panas berdenyut; partikel refrigeran
  (64 THREE.Points) mengalir sepanjang kurva CatmullRom lewat waypoint pipa
  (biru = dingin, oranye = panas).
- **Kamera sinematik:** per-shot azimuth/elevasi/jarak + lerp halus 0.6 detik
  antar shot; kamera selalu di sisi −Z (depan) — perhatikan: glTF mengubah
  Blender Z-up ke Y-up `(x,y,z)→(x,z,−y)`, jadi dinding Blender y=0 ada di
  three z≈+1.6 (belakang). **Kamera dari depan melihat +Z; kiri-kanan
  terbalik dibanding top view Blender.**
- **Overlay label gaya template "edukasi":** Noto Sans ExtraBold, teks hitam,
  kata kunci dalam kotak biru, kicker abu-abu + titik biru, caption bawah,
  nomor scene, progress bar. Headline ≤ ~20 karakter per baris — headline
  panjang terpotong di tepi (pelajaran scene 2: "REFRIGERAN: CAIR JADI GAS"
  → "CAIR JADI GAS").
- **API deterministik:** `window.__ready`, `window.__duration`,
  `window.__renderOnce(t)` (render satu frame pada detik t, lalu
  `window.__frameDone = true`), `window.__cam`, `window.__scene`,
  `window.__THREE` (debug).

### Format scenes JSON

```json
{ "fps": 30, "components": ["EsKipas","Refrigeran","Kompresor","Kondensor",
  "PipaKapiler","Evaporator","Termostat"],
  "scenes": [
    { "id": 1, "start": 0, "dur": 6, "focus": "EsKipas",
      "kicker": "KOMPONEN 0 — ES BATU",
      "headline": "ES BATU JADI AC", "keyword": "ES BATU",
      "body": "Satu kalimat penjelasan.",
      "target": [-2.55, 0.45, -0.9],
      "az": [205, 165], "el": [12, 8], "dist": [4.6, 4.2] }
  ] }
```

- `az/el/dist` = [awal, akhir] per scene (lerp). FOV 40° vertikal, aspek 9:16 →
  **horizontal FOV hanya ~23°** — objek selebar 1.5m butuh dist ≥ 3.5–4.5m
  agar muat. Selalu probe tiap scene (lihat QA).
- Scene dengan beberapa shot: `"shots": [ {…shot 1…}, {…shot 2…} ]` dengan
  `dur` per shot; scene `dur` = jumlah dur shot.

## TAHAP 3 — Perekaman

### PRIMARY (terverifikasi): frame-stepping Playwright → ffmpeg

`bin/record_frames.js` (juga disalin ke tiap proyek):

```bash
# server statis dulu (dari direktori viewer)
cd <project>/viewer && (setsid nohup python3 -m http.server 8901 >/tmp/http-8901.log 2>&1 &)
# rekam (detached; resume-safe — frame yang sudah ada di-skip)
cd <project> && setsid nohup env NODE_PATH=~/workspace/scratch/3d-agent/node_modules \
  node bin/record_frames.js http://127.0.0.1:8901/index.html <project>/frames 30 \
  > /tmp/record.log 2>&1 &
# hasil: <project>/ac-cycle-3d.mp4 (libx264, CRF 18, yuv420p, faststart)
```

- Kecepatan terukur: ~1 detik/frame @1080×1920 SwiftShader → 42 detik video
  (1260 frame) ≈ 21 menit. Jalankan detached; bila VM restart, jalankan ulang
  perintah yang sama — frame yang sudah ada di-skip.
- **Jangan** jalankan dua Chromium SwiftShader bersamaan (saling melambatkan).

### CCapture (TIDAK terverifikasi — dokumentasikan bila dicoba)

`viewer.html` mendukung `?capture=1` (CCapture webm 60fps, auto-download saat
selesai). Di headless SwiftShader, render real-time jauh di bawah 60fps
(~1–10 fps), sehingga CCapture merekam dengan frame drop / durasi salah.
**Jangan pakai CCapture sebagai jalur utama di VM ini.** Bila suatu saat
GPU tersedia, uji ulang dan catat hasilnya di `produksi.md`.

## QA gate (wajib sebelum lapor selesai)

1. `.glb` dibuat + dimuat Three.js tanpa error (`window.__ready === true`,
   tanpa `pageerror` kecuali favicon 404).
2. **Probe tiap scene** (`bin/probe_scenes.js` — satu frame tengah tiap
   scene, lihat gambarnya): semua komponen fokus terlihat utuh (tidak
   terpotong tepi / tidak tertutup objek lain / tidak hilang), label terbaca,
   headline tidak terpotong.
3. Video final: `ffprobe` — durasi & resolusi sesuai (42 dtk, 1080×1920),
   bisa diputar; cek 3–5 frame acak dari `frames/`.
4. Fakta konten cocok dengan riset acuan (untuk AC:
   `divisi/branding-promosi/riset-kalbotau-ac.md` — panas dipindahkan bukan
   dibuat; kondensor buang panas ke luar; evaporator serap panas di dalam;
   kapiler turunkan tekanan; termostat on/off kompresor).
5. Laporkan jujur jalur mana yang terverifikasi (Blender vs fallback,
   CCapture vs frame-stepping) + apa yang belum jalan.

## Aturan

- JANGAN sentuh serial / Perahu Terakhir / TikTok Awards / template
  "edukasi" / engine 2D (boleh baca saja). Jangan posting apa pun.
- Video ilustrasi TANPA VO. Format 9:16 1080×1920, ~30–60 detik.
- Setiap selesai kerja: tulis `produksi.md` di direktori proyek + index ke
  datahub (`dh.py index --division branding-promosi --type laporan`).
- Bila VM restart di tengah render: lanjutkan dari frame terakhir
  (resume-safe), jangan render ulang dari nol.

## PERLUASAN GAME — arena 3D playable dari scene-spec (terverifikasi 2026-10-30, keputusan owner: perluasan skill ini, BUKAN skill baru)

Implementasi kerja: `~/workspace/divisi/research/game-3d-tool/fase1/`
(`CONTRACT.md` + `CONTRACT-FASE2.md` = kontrak mengikat; riset dasar datahub
id 762; hasil fase 1 id 769, fase 2 id 774). Arsitektur hibrida: yang menulis
geometri adalah generator deterministik dari **scene-spec JSON** — model/VLM
kelak hanya mengisi spec, tidak pernah menulis kode bebas (compile rate kode
bebas terukur 5%, Proc3D; >75% gagal, BlenderGym).

**Rantai:** scene-spec → validator → generator bpy (Blender 4.5 headless) →
validasi geometri → `arena.glb` (visual + mesh `COL_<id>`) + `manifest.json`
→ viewer Three.js r186 + Rapier (playable) → mode kritik untuk loop visual.

```bash
cd ~/workspace/divisi/research/game-3d-tool/fase1
python3 spec/validate_spec.py spec/arena-maze.json
~/workspace/blender/blender -b --factory-startup -noaudio \
  --python generator/build_arena.py -- --spec spec/arena-maze.json --out output/
# sajikan folder fase1/ secara statis, buka viewer/index.html
```

- **Scene-spec** (`spec/scene-spec.schema.json`, draft 2020-12): `floor`,
  `spawn`, `goal`, `objects[]` shape `box`/`cylinder` (kondisional: box wajib
  `size[3]`, cylinder wajib `radius`+`height`), koordinat Blender Z-up,
  `position` = titik tengah. Validator stdlib `spec/validate_spec.py`:
  skema, id unik, batas lantai (toleransi tepi 0,5 m), spawn/goal bebas AABB.
- **Validasi generator (gerbang, build GAGAL bila tak lulus):** overlap
  antar-objek solid via `mathutils.bvhtree` harus KOSONG; clearance
  spawn/goal > 0,6 m; uji jalan grid 2D + BFS spawn→goal `reachable: true`.
  Validasi ini terbukti menangkap kesalahan geometri nyata (sudut dinding
  menembus 0,6 m) pada spec contoh pertama.
- **Manifest** = sumber kebenaran viewer, koordinat Three.js/glTF:
  three = (x, z_blender, −y_blender); `colliders` cuboid (cylinder didekati
  radius). Viewer menyembunyikan mesh `COL_*`; collider dari manifest.
- **Viewer** (`viewer/game.js`): Rapier `@dimforge/rapier3d-compat` v0.21.0
  (WASM inline; kinematic character controller, kapsul) + fallback resolver
  AABB otomatis; WASD + mouse look pointer lock + lompat. Hook uji:
  `window.__game {ready, getPlayerPos(), teleport(x,z), state}`; mode kritik
  `?critique=1` → `preserveDrawingBuffer` + `window.__critique.setView()`
  (orbit/top/spawn-pov/goal-pov). rAF headless VM ini di-throttle nyaris
  mati → viewer punya penggerak cadangan setInterval (jangan hapus).
- **Profil sculpt (generator, fase 2):** bevel semua mesh VISUAL
  (min(0,08 m; 35% dimensi terkecil), segments 3, limit angle 30°),
  cylinder 48 vertices + shade smooth; `COL_*` tetap primitif murni (fisika
  persis). Terukur pada arena contoh: .glb 79,6→232,4 KiB, segitiga
  1.196→5.980 (tepat 5,00× — pad datar penyumbang besar; terima, total tetap
  ringan), build 3,7→8,5 dtk, validasi tetap lulus penuh.
- **Paket shader clay (viewer, fase 2):** ACES tone mapping exposure 1,1,
  PCFSoft shadows (directional 1024), HemisphereLight + fog tipis;
  `MeshStandardMaterial` glTF diperkaya `onBeforeCompile` (roh uber-shader
  Tahap 2 diadaptasi): noise posisi dunia → variasi warna ±3%, modulasi
  roughness, bump mikro, Fresnel rim 0xa8c8e8. TANPA post-processing
  composer (SSAO/DOF) — SwiftShader tidak kuat; DOF sungguhan belum fase ini.
- **Batas terukur:** screenshot Playwright sudut POV flaky dalam run
  gabungan (stall kompositor SwiftShader; timeout 120 dtk) — pola yang
  berhasil: viewport kecil (480×360) + percobaan tersendiri. Screenshot
  orbit/top deterministik dan stabil.
- **Belum dibangun:** loop kritik VLM (screenshot → daftar defect JSON →
  revisi parameter spec, maks 3 iterasi) dan input gambar → scene-spec.
  Blender MCP BUKAN bagian arsitektur (add-on populer tidak bisa headless;
  MCP resmi Blender Lab butuh Blender 5.1+).
