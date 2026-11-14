// theme.ts — satu-satunya sumber warna/font komposisi ClipCaptions.
// ATURAN TERKUNCI DIVISI (menang atas skill remotion-motion-graphics):
// - teks caption off-white #F5F3EF; kata aktif biru #0064FF;
// - tipografi warna HITAM dilarang (hitam hanya boleh sebagai bayangan
//   lembut penunjang kontras, bukan warna teks/elemen);
// - animasi caption HANYA blur + fade (tanpa translate/spring/oscillator).
export const theme = {
  colors: {
    text: "#F5F3EF", // off-white — warna teks caption
    active: "#0064FF", // biru elektrik — kata yang sedang diucapkan
    upcoming: "rgba(245, 243, 239, 0.45)", // kata belum diucapkan (redup)
    shadow: "rgba(0, 0, 0, 0.55)", // bayangan lembut demi kontras di footage terang
  },
  fonts: {
    caption: "Plus Jakarta Sans",
  },
  caption: {
    fontSize: 38, // px pada lebar 720 — kalibrasi still QA: 44px=3 baris, 40px masih menyisakan 1 kata yatim di baris ke-3; 38px pas 2 baris
    fontWeight: 600,
    activeFontWeight: 800,
    lineHeight: 1.22,
    maxWordsPerLine: 5,
    // Zona tengah vertikal: blok caption berlabuh di 50% tinggi frame,
    // aman dari UI platform (atas/bawah tertutup UI).
    anchorTopPct: 50,
    blurInFrames: 6, // durasi transisi blur->tajam + fade per kata
    fadeOutFrames: 4, // fade keluar blok sebelum cue berikutnya
  },
} as const;
