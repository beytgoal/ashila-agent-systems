# Adaptasi Lokal — Indonesia (Ashila)

Skill ini aslinya memakai **Remotion** (React + TypeScript + headless Chrome)
untuk render. Di VM ini Remotion **tidak bisa jalan**:

1. Download Chrome Headless Shell diblokir (server tidak merespons).
2. Chromium sistem (`/opt/meta-chromium/chrome`, v152) memblokir
   `http://localhost:3000` dengan `ERR_BLOCKED_BY_LOCAL_NETWORK_ACCESS_CHECKS`
   — flag `--disable-features=LocalNetworkAccessChecks` tidak mempan di
   versi ini, dan `--dump-dom` tidak menghasilkan output sama sekali.

## Solusi: Python motion engine

`../../motion-video-projects/engine/motion_render.py` mengimplementasikan
playbook skill ini (SKILL.md §1–§7) dengan **PIL + numpy + ffmpeg**:

| Prinsip skill | Implementasi Python |
|---|---|
| VO-first timing | Durasi scene dari `ffprobe` file narasi |
| Kinetic typography | Kata masuk staggered ~4f, easing expo-out |
| Slam accents | Scale 1.3→1 dengan overshoot (ease-out-back) |
| Kicker labels | Mono tracked-out + hairline rule |
| Camera punch | Scale 1.09→1 + rotasi ringan, arah bergantian |
| Whip transitions | 20-frame accent band + white flash on cut |
| SFX glue | whoosh/impact/riser dari `scripts/sfx.py` |
| Bed under VO | loudnorm VO −19 LUFS, bed −38 LUFS |
| Film grain | Seeded noise per frame |
| Style palettes | `cinematic`, `chalk-lecture`, `bauhaus` |

Hybrid yang disarankan: background dari gambar AI (pipeline yang sudah ada)
+ teks/elemen motion graphics dari engine ini.

## Diketahui (untuk iterasi)

- [x] ~~Background `.webp` kadang tidak ter-load (fallback ke grid) — cek path & format~~
      → v1.1: `_resolve()` fuzzy-match nama file di direktori aset; path v1 yang
      typo (`universe25-scene1-paradise-07a29268.webp`) kini ketemu otomatis.
- [x] ~~Spacing kata accent (slam scale) belum presisi~~
      → v1.1: advance kata kini = lebar visual kata (ww × scale) + spasi;
      spacing "KATA BISA" kembali normal (terverifikasi frame QA).
- [x] ~~Headline bisa nabrak shape di bawahnya~~ (temuan user di test v2)
      → v1.1: auto-layout menggeser blok headline ke atas bila bertabrakan
      dengan shape/ilustrasi di paruh bawah (terverifikasi: "ANGKA JADI HIDUP"
      vs bar chart).
- [x] ~~Belum ada: scramble text, count-up numbers, panel chrome~~
      → v1.1: ketiganya diimplementasikan (`headline_entrance: "scramble"`,
      shape `countup` dengan label + format ribuan id-ID, `panel: true` dengan
      corner ticks + hairline aksen).
- [ ] Render ~1.5 detik/frame di 1080x1920 (lambat; optimasi: cache static layers)

## Riwayat pengembangan

- 2026-10-27: skill-v2 (perintah owner ~19:04 WIB, install `nxrskyaa/muse-motion-skills`): tipografi + motion skill diterapkan ke default engine (style `cinematic`): Inter Bold/Regular + JetBrains Mono, hero 120px, kata masuk rise 34px + deblur 18f, stagger flat 4f/kata, kicker `001 — LABEL` + hairline animasi, punch spring ±1,1° bergantian + deblur 16f. Semua digating `skill_v2` (hanya cinematic); `edukasi` frozen & `beyond` banned tidak berubah. TIDAK diterapkan: whip transitions + white flash + SFX glue (owner: tanpa transisi), watermark @nxrskyaa, VO −19 LUFS (tetap −16), rotasi style per video. Terverifikasi: render scene uji 1 scene, frame f30/f89 identik antara salinan uji & engine asli (md5 cocok); laporan `divisi/branding-promosi/skill-motion-install.md`.
- 2026-10-18: v1.1 — perbaikan 3 bug (spacing kata, tabrakan headline/shape,
  bg tidak ke-load via fuzzy resolve) + 3 fitur baru (scramble entrance,
  count-up numbers, panel chrome). Semua terverifikasi via frame QA;
  demo `engine/demos/motion-test-v3.mp4` (4 scene).
- 2026-10-18: v1 — engine dasar + test render 5 detik berhasil.
  Adaptasi `scripts/vo.sh` (+`--language`, env `VOICE_LANG`).
