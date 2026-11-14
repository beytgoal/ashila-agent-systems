// render-clip.mjs — renderer klip Remotion (komposisi ClipCaptions).
// Memakai chrome-wrapper.sh (Playwright Chrome for Testing 156) karena
// headless shell bawaan Remotion tidak bisa diunduh di VM ini dan
// /opt/meta-chromium tidak bisa render. JANGAN ganti ke `remotion browser
// ensure`.
//
// Pakai:
//   node render-clip.mjs --input <segmen.mp4> --captions <captions.json> \
//       --out <hasil.mp4> [--width 720] [--height 1280] [--fps 30]
//
// - segmen: video TANPA subtitle bakar (hasil potongan ffmpeg/facetrack).
//   File di luar public/ disalin dulu ke public/ (staticFile).
// - captions.json: {"cues":[{"start","end","words":[{"text","start","end"}]}]}
//   waktu dalam detik, relatif ke awal segmen (lihat tools/build-captions.py).
import {bundle} from "@remotion/bundler";
import {getCompositions, renderMedia} from "@remotion/renderer";
import {execFileSync} from "child_process";
import fs from "fs";
import path from "path";

const CHROME = path.resolve("./chrome-wrapper.sh");
const ENTRY = path.resolve("./src/index.ts");
const PUBLIC = path.resolve("./public");

function arg(name, def) {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 ? process.argv[i + 1] : def;
}

const input = arg("input");
const captionsPath = arg("captions");
const out = arg("out");
const width = Number(arg("width", "720"));
const height = Number(arg("height", "1280"));
const fps = Number(arg("fps", "30"));
// Default 1: render panjang pada VM bersama (RAM ~8GB) rawan OOM pada
// concurrency 2 (render pilot pertama mati di tengah tanpa output).
const concurrency = Number(arg("concurrency", "1"));
if (!input || !captionsPath || !out) {
  console.error("wajib: --input <segmen.mp4> --captions <captions.json> --out <hasil.mp4>");
  process.exit(2);
}

// Salin segmen ke public/ bila belum di sana (OffthreadVideo memakai staticFile).
const inputAbs = path.resolve(input);
let videoSrc = path.basename(inputAbs);
if (path.dirname(inputAbs) !== PUBLIC) {
  fs.copyFileSync(inputAbs, path.join(PUBLIC, videoSrc));
}

// Durasi segmen dari ffprobe (audio+video mengikuti footage).
const probe = JSON.parse(
  execFileSync("ffprobe", [
    "-v", "error", "-show_entries", "format=duration",
    "-of", "json", inputAbs,
  ]).toString(),
);
const durationSec = Math.floor(Number(probe.format.duration) * 100) / 100;

const captionsDoc = JSON.parse(fs.readFileSync(path.resolve(captionsPath), "utf8"));
const cues = captionsDoc.cues || [];
if (!cues.length) console.error("PERINGATAN: captions.json tidak punya cue");

const inputProps = {videoSrc, cues, durationSec};

const bundled = await bundle({entryPoint: ENTRY});
const compositions = await getCompositions(bundled, {
  browserExecutable: CHROME,
  chromiumOptions: {disableWebSecurity: true},
  inputProps,
});
const comp = compositions.find((c) => c.id === "ClipCaptions");
if (!comp) throw new Error('Komposisi "ClipCaptions" tidak ditemukan');

const t0 = Date.now();
await renderMedia({
  composition: {...comp, width, height, fps},
  serveUrl: bundled,
  browserExecutable: CHROME,
  chromiumOptions: {disableWebSecurity: true},
  inputProps,
  outputLocation: path.resolve(out),
  codec: "h264",
  crf: 17,
  audioCodec: "aac",
  concurrency,
  onProgress: ({progress}) =>
    process.stdout.write(`\r${Math.round(progress * 100)}%`),
});
console.log(
  `\nrender ok: ${out} (${comp.durationInFrames} frame, ${durationSec}s, ` +
    `${((Date.now() - t0) / 1000).toFixed(1)} dtk render)`,
);
