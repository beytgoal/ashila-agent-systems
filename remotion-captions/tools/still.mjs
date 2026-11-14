// still.mjs — render satu frame komposisi ClipCaptions untuk QA cepat
// sebelum render video penuh (skill Step 5: lihat frame dulu).
// Pakai: node tools/still.mjs <frame> <out.png> [captions.json] [segmen.mp4]
import {bundle} from "@remotion/bundler";
import {getCompositions, renderStill} from "@remotion/renderer";
import {execFileSync} from "child_process";
import fs from "fs";
import path from "path";

const CHROME = path.resolve("./chrome-wrapper.sh");
const [frame, out, captionsPath = "pilot/captions-ceiqu-01.json",
  input = "public/footage-ceiqu-01.mp4"] = process.argv.slice(2);

const inputAbs = path.resolve(input);
const probe = JSON.parse(
  execFileSync("ffprobe", ["-v", "error", "-show_entries", "format=duration",
    "-of", "json", inputAbs]).toString(),
);
const inputProps = {
  videoSrc: path.basename(inputAbs),
  cues: JSON.parse(fs.readFileSync(path.resolve(captionsPath), "utf8")).cues,
  durationSec: Math.floor(Number(probe.format.duration) * 100) / 100,
};

const bundled = await bundle({entryPoint: path.resolve("./src/index.ts")});
const compositions = await getCompositions(bundled, {
  browserExecutable: CHROME,
  chromiumOptions: {disableWebSecurity: true},
  inputProps,
});
const comp = compositions.find((c) => c.id === "ClipCaptions");
await renderStill({
  composition: comp,
  serveUrl: bundled,
  browserExecutable: CHROME,
  chromiumOptions: {disableWebSecurity: true},
  inputProps,
  frame: Number(frame),
  output: path.resolve(out),
});
console.log("still ok:", out);
