# Produksi Video 3D — three.js + storyboard.json (frame-step deterministik)

Skill ini menyimpan metode produksi video animasi 3D Divisi Branding &
Promosi yang TERBUKTI selesai dua kali: **KisahVerse Ep1 "Pergi Demi Iman"**
(31 Okt 2026: 1080×1920, 76,7 dtk, LUFS −15,95) dan **Kota Impian Day 1**
(31 Okt 2026: 1080×1920, 69,33 dtk, LUFS −15,79). Metode dikunci owner
30 Okt 2026: **three.js + storyboard.json, render frame-step deterministik**.
Stills/Ken Burns dan rig 2D untuk format ini DIBATALKAN; pipeline Blender v1
(arsip `project/` di produksi-day1) digantikan jalur ini dan tidak dipakai
lagi.

Pakai skill ini untuk: episode baru KisahVerse, hari baru Kota Impian, atau
seri 3D vertikal baru dengan pola yang sama. Sumber pola (baca sebelum
memodifikasi viewer):
- `~/workspace/divisi/branding-promosi/kisahverse/produksi-ep1/` —
  `storyboard.json` (varian scene/aktor), `assets/karakter-stickman.js`
  (aset karakter persisten), `bin/record_frames.js`, `viewer/index.html`.
- `~/workspace/divisi/branding-promosi/kotaimpian/produksi-day1/` —
  `README-threejs.md` (dokumen metode asli — paling lengkap, WAJIB baca),
  `city-state.json` (state persisten), `storyboard.json` (varian
  state/shot), `bin/`, `viewer/index.html`.
- Basis viewer divisi: `~/workspace/divisi/branding-promosi/3d-agent/viewer/`
  (proyek jembatan-3d + Kantor 3D) — importmap vendor lokal, API
  deterministik. Template kosong: `storyboard-template.json` di folder
  skill ini.
- **Script pembungkus SATU perintah (31 Okt 2026):**
  `~/workspace/motion-video-projects/engine/video_pipeline_3d.py` —
  menjalankan seluruh langkah produksi di bawah sebagai tahap 0–7
  (self-check → validasi → VO → probe → rekam → rakit → finalize → QA)
  dengan laporan `qa-report.json`/`.md`. Contoh:
  `python3 video_pipeline_3d.py --project <folder produksi> --out-dir <folder hasil> [--naskah <naskah.json>] [--dry-run] [--skip-record] [--frames 0-149]`.
  Folder produksi asli tidak pernah ditulis script (bekerja di salinan
  `<out-dir>/work/`); gagal tahap mana pun berhenti terbuka
  `[TAHAP x] GAGAL` + exit 1.
  **Perbaikan P0+P1 (2026-11-01, riset datahub 1297 — uji penuh ulang
  LOLOS semua gerbang, lihat `pipeline-3d/uji/hasil-perbaikan-p0p1/`):**
  (a) tahap **2B UKUR + RETIME** sesudah VO — durasi nyata tiap segmen
  diukur (ffprobe) → `dur_measured` di voice_log → mode generate:
  voSync dibangun ulang (start kumulatif, jeda antar-segmen 0,35,
  ekor 0,40; durasi shot diskala proporsional, field `vo` shot ikut —
  kinetic reveal jadi dari durasi terukur) → `storyboard.resolved.json`
  di folder kerja; duration episode mengikuti VO. Mode pakai-ulang:
  hanya ukur, voSync dipertahankan. Atempo BUKAN mekanisme retime.
  (b) finalize: `amix duration=longest` + `apad=whole_dur` +
  `atrim=0:span` (duration=first terbukti memotong audio master ke
  durasi segmen pertama). (c) gerbang audio **QA-A1..A5** di tahap 7
  (lihat Gerbang QA). (d) voice_router muse-tts memakai **peta jeda
  v3** (koma 0,08 / titik dua & titik koma 0,15 / seru & tanya 0,20 /
  titik 0,25; pad trim 15 ms; jeda sesudah sapaan ≤3 kata maks 0,12;
  satuan klausa dipertahankan — sintesis per kalimat utuh dipalsukan
  uji: jeda internal TTS miles di koma/titik dua 0,52–0,55 dtk).
  Kelengkapan fase build 31 Okt 2026 (uji penuh Day 1 LOLOS, lihat
  `3d-agent/LAPORAN-BUILD-PIPELINE-3D.md`): tahap rekam membagi rentang
  ke `--recorders` recorder paralel (bawaan 2); total frame =
  floor(durasi × fps) menyamai semantik recorder; tahap 3 membaca
  `window.__detailing` yang AKTIF via
  `pipeline-3d/detailing-probe.js`; penjaga mekanis
  `pipeline-3d/resume-pipeline-3d.sh` mengecek status/menyelesaikan/
  me-relaunch run yang mati (mis. restart VM) tanpa agent — pakai itu
  untuk memantau run panjang, bukan rangkaian perintah manual. Panduan:
  `engine/CARA-PAKAI-PIPELINE-3D.md`.
- **Resource WebGL terpin:** `~/workspace/divisi/branding-promosi/3d-agent/webgl-resources/`
  (+ `MANIFEST.md` di dalamnya: versi three r186 terkunci, hash sha256 per
  file, tabel kecocokan detailing, tabel pemetaan teknik utama). Audit
  WebGL mesin render: `~/workspace/divisi/branding-promosi/pipeline-3d/webgl-audit.md`
  (WebGL2 tersedia; renderer ANGLE SwiftShader). Script menjalankan
  **tahap 0 SELF-CHECK WebGL** (probe headless + verifikasi hash resource)
  sebelum render — WebGL mati = berhenti terbuka, tidak render kosong.

## Perintah tetap yang mengikat skill ini

- **Format final selalu 1080×1920 (Full HD); audio mengikuti DEFAULT
  TERKUNCI owner 31 Okt 2026 18:23 WIB: VO −15 LUFS di atas bed −34 LUFS**
  (master final terukur ≈ −15, koreksi gain maks ±1). Video tidak boleh
  diam dan tidak boleh bisu; gerak dibuktikan dengan diff frame, bukan
  klaim. *Catatan riwayat: angka −16 (VO)/−38 (bed) adalah angka produksi
  lama Ep1/Day 1 — acuan lulus lamanya Ep1 −15,95 dan Day 1 −15,79 LUFS —
  dan TIDAK dipakai lagi sejak kuncian baru.*
- **Desain karakter terkunci per seri** — spek hidup di aset/state
  (KisahVerse: `assets/karakter-stickman.js`; Kota Impian: `city-state.json
  → character`, Pak Bimo v2 terkunci). Jangan ubah tanpa persetujuan owner.
- **Viewer = mesin generik.** Konten harian/episode TIDAK PERNAH di-hardcode
  di `viewer/index.html`; semua isi datang dari `storyboard.json` (+ state).
- **Hanya SATU chrome yang bisa render di VM ini:** Playwright Chrome for
  Testing 156 di
  `~/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome`
  (+ `--no-sandbox --disable-dev-shm-usage`, di bawah `xvfb-run`).
  `/opt/meta-chromium/chrome` v152 DILARANG untuk render (keluaran kosong,
  localhost diblokir LNA). Unduhan browser bawaan Remotion diblokir egress.
- **Tidak ada posting tanpa persetujuan owner.** Skill ini berhenti di
  master + versi chat + cover lulus QA, siap dinilai owner.
- Khusus KisahVerse (kunci doktrinal naskah): jumlah pemuda Ashabul Kahfi
  tidak ditegaskan (QS 18:9–26); tanpa visualisasi nabi/malaikat/Tuhan.

## Arsitektur (pola viewer divisi)

Satu halaman `viewer/index.html` memuat three.js **r186 dari vendor lokal**
(`viewer/vendor/`: three.module.js + three.core.js + addons GLTFLoader,
BufferGeometryUtils, SkeletonUtils — importmap, tanpa CDN) dan mengekspos
API deterministik yang dikendalikan perekam:

- `window.__ready === true` — scene selesai dibangun dari storyboard/state.
- `window.__duration` — durasi total dari storyboard.
- `window.__renderOnce(t)` — render tepat satu frame pada waktu `t`.
- `window.__frameDone === true` — frame selesai, aman di-screenshot.

Kamera dinyatakan sebagai `target [x,y,z]` + `az/el/dist` masing-masing
pasangan `[dari, ke]` yang di-lerp sepanjang shot (blend ±0,6 dtk
antar-shot). Overlay teks adalah **DOM di atas canvas** (bukan tekstur 3D),
jadi teks tetap tajam walau ada DOF: kicker, headline dengan penanda baris
`@@NL@@`, kata aksen berwarna, body, progress bar, dan *kinetic reveal*
kata-per-kata mengikuti waktu shot. Fungsi viewer sesuai kebutuhan seri:
builder dunia dari data (primitif/state — bukan GLB untuk seri state-ful),
rig karakter di atas topologi **MediaPipe Pose 33 landmark** (posisi
landmark → volume antar-landmark; gait anti-fase lengan/kaki, kedip siklus
deterministik), pass DOF (render ke RenderTarget + DepthTexture, shader
fullscreen circle-of-confusion, blur poisson 12-tap, ACES + sRGB di shader
yang sama), ramp senja (`sunset: [dari, ke]` per shot), dan penjadwalan
objek transparan (impian melayang dari `dreamsLib`).

Pencahayaan/gaya terkunci pola divisi: MeshStandardMaterial + primitif
smooth shading segmen tinggi, injeksi uber-shader (rim Fresnel lembut +
noise halus), ACES tone mapping, bayangan **PCFShadowMap radius 4**
(PCFSoft dihapus di r186).

## Struktur proyek baku

Per seri (persisten, dibuat sekali):

```
<seri>/
  naskah-*.json            sumber naskah episode (di luar folder produksi)
  produksi-<ep>/           SATU folder per episode/hari
    viewer/index.html      mesin generik (salinan basis, disesuaikan sekali)
    viewer/vendor/         three r186 lokal
    assets/                aset karakter persisten seri (mis. karakter-stickman.js)
    <state>.json           state persisten seri state-ful (mis. city-state.json)
    storyboard.json        konten episode ini SAJA
    vo/                    s{n}.wav, s{n}_norm.wav, bed_norm.wav, voice_log.json
    bin/                   probe, recorder, finalize, qa (salinan basis)
    frames*/               f%05d.jpg (Kota) / f_%05d.png (KisahVerse)
    qa*/                   stills probe + stills final + hasil diff
    video-silent*.mp4      rakitan frame tanpa audio
    <seri>-<ep>.mp4        MASTER final
    <seri>-<ep>-chat.mp4   versi kirim chat (≤16 MB)
    <seri>-<ep>-cover.jpg  cover dari frame terbaik
    *.log                  log probe/record/finalize per run (jangan ditimpa diam-diam: pakai sufiks baru)
```

## Skema storyboard.json (dua varian terbukti)

Anotasi lengkap ada di `storyboard-template.json`. Ringkasnya:

**Varian A — scene/aktor (KisahVerse).** Tanpa file state; dunia dibangun
dari `sets` di dalam storyboard.
- `title`, `fps` (30), `duration` (detik, total).
- `cast`: peta nama → spek kostum/warna (warna integer hex, `phase` untuk
  offset gait; flag opsional `bundle/face/lantern/torch/helmet/spear`).
- `config`: `theme` (font + warna overlay), `world` (ambient, fog, ground,
  moon, exposure), `dof` (`enabled`, `bgScale`, `mode`), `overlay`
  (`progress`, `sceneNum`).
- `sets`: peta nama set → array primitif `{k: kind, p: [x,y,z], s: [sx,sy,sz],
  r: [rx,ry,rz], c: warna}` — kind terbukti: plane, box, wallSeg, wallTorch,
  pillar, house, mountain, rock, platform, statue, throne, brazier.
- `scenes[]`: `{id, set, vo, dur, kicker, headline, accent, body,
  camera: {target, az: [a,b], el: [a,b], dist: [a,b]},
  actors: [{cast, track: [{t, p: [x,y,z], ry}], actions: [{type, from, to,
  ...}]}]}` — type aksi terbukti: walk, run, carry, raise, raiseArm, point,
  sneak (dengan `freq`, `rampIn`, `rampOut`, `side` sesuai kebutuhan).

**Varian B — state/shot (Kota Impian).** Dunia dari file state terpisah;
storyboard hanya konten harian.
- `format`, `version`, `day`, `fps`, `duration`, `cityState` (path state).
- `theme`: token warna/font overlay pastel.
- `render`: `pixelRatio` (0,75 terbukti), `fov` (40), `dof` (`enabled`,
  `maxBlur`, `focusBias`).
- `voSync.segments`: peta `s{n}` → `{start, dur}` — VO tidak di-generate
  viewer; finalize mencampur pada start yang sama dengan scene.
- `dreamsLib`: pustaka objek terjadwal (kind + pos + scale).
- `scenes[]`: `{id, vo: "s{n}", shots: [...]}`; shot: `{dur, vo (durasi VO
  shot), kicker, headline (pakai @@NL@@), accent, body, cam: {target, az,
  el, dist}, focus: "bimo" | [x,y,z], sunset: [dari, ke] (opsional),
  dreams/props (opsional), <karakter>: {pos: [x,z] | path: [[x,z],...],
  heading, rig}}` — rig terbukti: wave, waveBig, walk, pointR, pointL, talk.

**File state persisten (seri state-ful)** — skema `city-state.json`:
`{format, version, day, note, palette (token warna nama→hex), environment[]
{id, kind, pos, ...} (kind: ground-dome, hill, path, tree, cloud + anim
drift, flowers, grass-tufts — sebaran acak WAJIB pakai seed tetap),
buildings[] {id, kind, pos, rotY, ...} (kind baru = builder baru di
buildWorld() viewer), character {id, design, colors (rujuk palette),
proportions}}`.

## Langkah produksi ujung-ke-ujung

1. **Naskah & storyboard.** Tulis naskah (JSON seri), generate VO per
   segmen via `voice_router.py` (satu video = satu voice; rantai default
   divisi), lalu ukur durasi tiap segmen — durasi VO menentukan
   `voSync`/durasi scene, bukan sebaliknya. Isi `storyboard.json` dari
   template skill ini.
2. **VO final-bentuk.** Normalkan per segmen dengan loudnorm **SEBELUM
   adelay** ke `vo/s{n}_norm.wav` (−15 LUFS, kunci baru), bed ke
   `vo/bed_norm.wav` (−34 LUFS). Simpan `voice_log.json`. (Angka lama
   −16/−38 hanya untuk membaca log produksi Ep1/Day 1.)
3. **Probe dulu, selalu.** Serve folder produksi sebagai root HTTP
   (viewer varian file:// juga terbukti jalan dari disk) dan ambil stills
   di semua waktu kunci:
   `node bin/probe3.js <url viewer> <folder qa> <t1> <t2> ...`
   (KisahVerse: `bin/probe.js`). Periksa SEMUA stills sebelum rekam penuh:
   komposisi, teks, karakter, tidak ada error halaman (`__errors` kosong).
4. **Rekam frame-step.** Varian JPG (Kota):
   `node bin/record_resilient.js <url viewer> <frames3> 30 <start> <end>`
   — recorder resume-safe (skip frame utuh), retry per frame + reload
   halaman saat gagal beruntun. Boleh 2 recorder paralel pada rentang
   berbeda; kecepatan terukur di VM ini ±3–6 dtk/frame (SwiftShader).
   Varian PNG (KisahVerse):
   `NODE_PATH=~/workspace/scratch/3d-agent/node_modules xvfb-run -a -s "-screen 0 1280x2000x24" node bin/record_frames.js <url> <framesDir> <prefix> <outName.mp4> [startFrame] [endFrame]`
   (recorder ini merakit mp4 bisu sendiri; env `FPS`, `X264_CRF` default 16,
   `FRAME_W/H` default 1080×1920).
5. **Rakit video bisu** (varian JPG):
   `ffmpeg -framerate 30 -i frames3/f%05d.jpg -c:v libx264 -preset medium -crf 17 -pix_fmt yuv420p video-silent3.mp4`
6. **Finalize.** `python3 bin/finalize3.py` (sesuaikan `BASE` + `STARTS`
   dengan voSync): campur segmen VO pada start scene-nya + bed dengan
   `amix=normalize=0:duration=longest` + `apad=whole_dur=<span>` +
   `atrim=0:<span>` sesudah amix (WAJIB sejak 2026-11-01:
   `duration=first` memotong audio ke durasi input pertama — bug
   master 17,02/69,30 dtk), ukur LUFS master, koreksi gain ke −15 (maks ±1,
   acuan konfigurasi terkunci baru), turunkan
   versi chat (≤16 MB) + cover. KisahVerse: pola sama (rakit dari
   `video-3d-bisu.mp4` + audio) — master `kisahverse-ep1-pergi-demi-iman.mp4`.
   *Langkah 1–7 di atas kini dibungkus `video_pipeline_3d.py` (lihat
   bagian atas skill ini); langkah manual tetap jadi acuan bila script
   berhenti terbuka di satu tahap.*
7. **QA gate** (bagian berikut) — gagal satu angka = perbaiki & render
   ulang bagian itu, bukan ditambal di caption.

## Detailing (paket penghalusan, config storyboard — default MATI)

Perintah owner 31 Okt 2026 19:13 WIB. Semua detailing diaktifkan lewat
blok `detailing` di storyboard; tanpa blok itu tampilan = produksi lama
persis (kecuali `antialias: true` yang memang standar viewer). Resource-
nya terpin di webgl-resources (lihat MANIFEST untuk versi/hash + tabel
kecocokan lengkap + tabel pemetaan teknik utama yang tidak boleh dibuang).

```json
"detailing": {"aa": "fxaa|smaa|none", "camera": "curve", "smooth": true, "poseBlend": true}
```

- `smooth: true` — builder primitif relevan dihaluskan:
  `BufferGeometryUtils.mergeVertices()` (welding) + `computeVertexNormals()`
  + smooth shading bawaan material.
- `camera: "curve"` — jalur kamera `CatmullRomCurve3` +
  `Quaternion.slerpQuaternions`, faktor blend antar-shot memakai
  `MathUtils.damp` (di luar mode ini kamera tetap lerp lama).
- `poseBlend: true` — blend pose prosedural antar-shot (padanan fungsional
  `crossFadeTo` untuk rig non-Mixer; rig GLTF/klip memakai AnimationMixer
  asli).
- `aa` — pass anti-aliasing di present final: `fxaa` (fullscreen, jalan
  bersama DOF) atau `smaa` (EffectComposer; HANYA bila DOF mati —
  SMAA+DOF bersamaan otomatis turun ke fxaa + `console.warn`). Viewer
  mengekspos pilihan yang benar-benar aktif di `window.__detailing`
  (dibaca script untuk qa-report). **TAA tidak dijadikan pilihan default**
  (akumulasi temporal vs render satu-frame deterministik); file
  TAARenderPass/SSAARenderPass tersedia di webgl-resources sebagai slot.
- GSAP/Tween.js (terpin sebagai `external/`) hanya boleh dipakai sebagai
  fungsi easing murni pada evaluasi t frame — bukan ticker real-time.
- Terverifikasi pada proyek uji pipeline-3d: `__detailing` =
  `{aaAktif: "fxaa", camera: "curve", smooth: true, poseBlend: true}` dan
  salinan SMAA `{aaAktif: "smaa"}` (DOF mati), pageerrors kosong.

## Gerbang QA (angka, bukan kesan)

- [ ] `ffprobe` master: **1080×1920**, fps 30, durasi ≈ storyboard (±0,5 dtk).
- [ ] **LUFS master terukur ≈ −15** (target konfigurasi terkunci baru,
      koreksi gain maks ±1; loudnorm print_format=json di file final.
      Acuan historis angka lama: Ep1 −15,95, Day 1 −15,79).
- [ ] **Bukti gerak:** `python3 bin/qa_motion3.py` — diff piksel mean
      absolut antar-frame 1 dtk di SETIAP jendela scene > 0 (full-frame dan
      center crop); scene yang diff-nya ~0 = video diam = GAGAL.
- [ ] Stills final (`qa*/final/`): teks masuk zona aman **x 64..1016,
      y 64..1856**; TIDAK ada `@@NL@@` literal; dengan DOF: subjek tajam,
      latar blur, teks DOM tetap tajam; karakter identik dengan desain
      terkunci seri.
- [ ] Audio: VO terdengar di semua segmen (cek `voice_log.json` + spot-listen
      file chat), bed −34 tidak menenggelamkan VO.
- [ ] **Gerbang audio QA-A1..A5 (2026-11-01, otomatis di tahap 7 script;
      untuk finalize manual cek angka yang sama):** A1 durasi stream
      audio vs video selisih ≤ 0,30 dtk; A2 loudness irisan tiap
      jendela segmen ≥ −40 LUFS dan −15 ±6 dB; A3 dari `dur_measured`
      voice_log: tidak ada segmen berakhir melewati start segmen
      berikutnya (+0,05); A4 silencedetect −40 dB per wav segmen:
      jeda internal terpanjang ≤ 0,35, rata-rata ≤ 0,25 (angka
      dicatat); A5 voice_log WAJIB memuat `dur_measured` per segmen —
      tanpa itu QA GAGAL.
- [ ] **Gerbang P2 (2026-11-01, otomatis di tahap 7):** profil render
      tercatat di qa-report dan pixelRatio storyboard work == profil
      (master 1,0); envelope lip-sync ada untuk SEMUA segmen VO
      (`vo/lipsync.json` + `sb.lipSync`); still mulut keras-vs-jeda
      membuktikan mulut mengikuti amplitudo.
- [ ] File yang dinilai owner = MASTER di folder produksi
      (`<seri>-<ep>.mp4`), bukan file strip penonton/derivatif lain.

## Paket P2 (2026-11-01): profil resolusi, lip-sync amplitudo, tekstur prosedural

- **Profil render `--profile {master,draft}`** di `video_pipeline_3d.py`
  (default master). Tahap **2C** memaksa `render.pixelRatio` pada salinan
  storyboard work: master = 1,0 (buffer render benar-benar 1080×1920),
  draft = 0,75 (pratinjau cepat). Profil tercatat di qa-report + dua
  gerbang tahap 7: profil diterapkan (pixelRatio work == profil) dan
  envelope lip-sync lengkap. Hasil akhir untuk owner SELALU master.
- **Lip-sync amplitudo (tahap 2C):** envelope RMS VO mentah per segmen,
  hop 40 ms, normalisasi persentil-98 global, pangkat 0,75, smoothing
  rerata-geser 3 → `work/vo/lipsync.json` + injeksi `sb.lipSync` ke
  storyboard work. Viewer: `voAmp(t)` menginterpolasi envelope terhadap
  `voSync` dan menskalakan elemen mulut karakter secara deterministik
  dari waktu frame — bukan acak, bukan biner. Kedip/gerak lain tidak
  disentuh. Verifikasi: `window.__voAmp(t)` + `__bufferSize()` di debug.
- **Tekstur prosedural viewer Kota Impian:** helper canvas
  (`procTexture`/`grainTex`/`wallTex`/`pathTex`/`roofTex`) membangkitkan
  tekstur dari PALET state (bukan warna baru): tanah/bukit grain, jalan
  grain + marka emas putus-putus, dinding balai kota plester + grid
  jendela, atap sirap scallop. Warna dasar material tetap warna palet
  (map mengalikan warna) — identitas desain terkunci tidak berubah.
- **Tangkap frame di SwiftShader PR 1,0:** `page.screenshot` klasik bisa
  17–122 dtk/frame (pemanasan surface). Pola yang lolos: CDP
  `Page.captureScreenshot {fromSurface:false}` (±1 dtk, byte-identik)
  + `waitForFunction` dengan polling numerik 200–250 ms (polling rAF
  bawaan kelaparan di halaman frame-step) + timeout longgar (ready
  240 dtk). Terapkan di probe3.js + record_resilient.js proyek.
  PERHATIAN: shot debug sekali-tembak tanpa jeda presentasi bisa
  menangkap buffer kosong — beri jeda ±350–450 ms sesudah frameDone
  (pola probe3) sebelum menilai gambar.
- **Bangunan GLB nyata (kind `glb` di state):** viewer memuat via
  GLTFLoader dari `b.url`; `__ready` menunggu semua muatan. WAJIB:
  (1) pusatkan geometri ke origin grup dengan Box3 (ekspor Sketchfab
  menaruh mesh jauh dari origin root — tanpa ini model mendarat di luar
  pandangan), kaki min.y di tanah grup; (2) skala dari bbox terukur
  Blender, bukan tebakan; (3) periksa frustum kamera storyboard —
  FOV horizontal sempit (±15°) pada format vertikal, bangunan di
  |x| besar / z dekat mudah keluar frame, dan footprint model besar
  bisa menelan model lain di belakangnya; (4) error shader
  `VALIDATE_STATUS false` di konsol SwiftShader untuk material GLB
  terbukti TIDAK selalu fatal (frame tetap tergambar) — nilai dari
  still, bukan dari log konsol. Simetri: sederhanakan material ke
  albedo saja bila still membuktikan mesh hilang.
- **Port server pipeline:** `--port` default 8931 untuk SEMUA run.
  Dua run paralel WAJIB port berbeda (mis. 8933/8935/8937), kalau tidak
  run kedua diam-diam me-render halaman run pertama (server gagal bind,
  cek kesehatan lolos ke server lama) — gejalanya: still/frame tidak
  berubah walau viewer proyek sudah diubah.

## Jebakan yang sudah terbukti (jangan ulangi)

- **FS sandbox EPERM intermiten:** tulis file besar (frame/zip/mp4) kadang
  ditolak sesaat walau path benar; hasil kerja juga bisa "hilang" dari
  pandangan satu sesi exec. Verifikasi file final dari sesi exec TERPISAH
  sebelum melapor selesai; untuk sqlite pakai `journal_mode=MEMORY` +
  `synchronous=OFF`. Jangan vonis disk rusak.
- **`scenes.json` warisan viewer ≠ storyboard.** Folder produksi lama
  membawa `viewer/scenes.json` (skema edukasi basis 3d-agent: components/
  flowPath). Produksi three.js membaca `storyboard.json` di root folder
  produksi — jangan edit yang salah.
- **Label keluaran filter ffmpeg hanya boleh dikonsumsi SEKALI.** VO mix
  yang memberi makan sidechain + amix final harus di-`asplit` dulu, kalau
  tidak hanya segmen pertama yang bersuara. Selalu `amix=normalize=0`
  (default normalize=1 membagi semua input → VO jatuh ke ±−40 LUFS), dan
  dalam rantai VO, `loudnorm` SEBELUM `adelay`.
- **`amix duration=first` = audio terpotong ke input pertama** (terbukti
  31 Okt 2026: master 69,30 dtk hanya ber-audio 17,02 dtk = durasi s1,
  dan LUFS utuh tetap −14,24 sehingga gerbang lama lolos). Selalu
  `duration=longest` + `apad=whole_dur` + `atrim` pengunci span, dan
  jangan pernah menilai audio dari LUFS file utuh saja — cek durasi
  stream + bunyi per jendela (QA-A1/A2).
- **voSync warisan ≠ durasi VO regenerasi.** Meng-generate VO baru ke
  storyboard lama tanpa mengukur ulang = tumpang tindih/terpotong
  (VO baru 73,26 vs jendela 66,82 pada Day 1). Tahap 2B script
  menegakkan "durasi VO terukur menentukan timing"; bila mengerjakan
  manual, ukur dulu baru tulis voSync.
- **CCapture tidak viable headless** — perekaman selalu frame-step via API
  `__renderOnce`, bukan capture realtime.
- **DOF ala folder produksi = pass RenderTarget + DepthTexture sendiri.**
  Blur CSS pada output
  skala-rendah pernah diukur +9–11 dtk/frame di KisahVerse — mode DOF
  dicatat eksplisit di `config.dof.mode` storyboard, jangan ganti diam-diam.
  EffectComposer kini TERPIN di webgl-resources, tetapi HANYA untuk rantai
  AA detailing (FXAA/SMAA) — bukan untuk mengganti DOF kustom ini.
- **Closure import addon wajib utuh.** Satu file shader yang hilang
  (`addons/shaders/OutputShader.js`, diimpor OutputPass) pernah membuat
  modul viewer mati total: halaman termuat tapi `__ready` tidak pernah
  true dan probe timeout — gejalanya menipu seperti "viewer rusak". Bila
  probe timeout tanpa pageerror jelas, cek log server HTTP untuk 404 pada
  file vendor lebih dulu.
- **Halaman harus menunggu `__ready`** sebelum `__renderOnce` pertama;
  recorder yang screenshot terlalu dini menghasilkan frame kosong yang
  lolos hitungan file — probe stills adalah penangkapnya.
- **Dua recorder paralel hanya pada RENTANG BERBEDA** dan folder frame yang
  sama aman karena nama file per nomor frame; jangan jalankan dua proses
  finalize bersamaan.

## Checklist episode/hari lanjutan

Umum (semua seri):
1. Salin folder produksi episode sebelumnya → `produksi-<ep baru>/`
   (viewer + vendor + bin + assets ikut; kosongkan `frames*/`, `qa*/`,
   keluaran mp4 lama).
2. Tulis `storyboard.json` BARU untuk episode ini (durasi, VO, kamera,
   teks, aksi) — jangan edit storyboard episode lama.
3. Generate VO episode ini; sesuaikan durasi scene ke durasi VO terukur.
4. Probe semua waktu kunci → rekam → rakit → finalize → QA gate penuh.
5. Kirim versi chat ke owner untuk persetujuan; posting hanya atas
   persetujuan itu.

Khusus seri state-ful (Kota Impian):
1. Di salinan folder, buka file state: naikkan `day` + `updated`, tambah
   **TEPAT SATU** bangunan pemenang ke `buildings[]` (kind baru → daftarkan
   builder-nya di `buildWorld()` viewer; kind terbukti: `balai-kota`,
   `sign-kota`, `rules-board`). JANGAN bangun ulang kota dari nol dan
   jangan ubah `character`/palet terkunci.
2. `cityState` di storyboard baru tetap menunjuk file state di folder
   salinan itu — state episode sebelumnya tidak ditimpa (ia hidup di folder
   episodenya sendiri).
3. Sisanya mengikuti checklist umum.
