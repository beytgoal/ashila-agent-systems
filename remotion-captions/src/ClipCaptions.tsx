import React, {useEffect, useMemo, useState} from "react";
import {
  AbsoluteFill,
  OffthreadVideo,
  continueRender,
  delayRender,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import {theme} from "./theme";

export type CaptionWord = {text: string; start: number; end: number};
export type CaptionCue = {start: number; end: number; words: CaptionWord[]};
export type ClipCaptionsProps = {
  // nama file segmen di public/ (footage TANPA subtitle bakar)
  videoSrc: string;
  cues: CaptionCue[];
  durationSec: number;
};

// Muat Plus Jakarta Sans (variable font) dari public/fonts sebelum render
// frame pertama — tanpa ini frame awal bisa jatuh ke font bawaan.
const useCaptionFont = () => {
  const [handle] = useState(() => delayRender("load Plus Jakarta Sans"));
  useEffect(() => {
    const face = new FontFace(
      theme.fonts.caption,
      `url(${staticFile("fonts/PlusJakartaSans-VF.ttf")})`,
      {weight: "200 800"},
    );
    face
      .load()
      .then(() => {
        document.fonts.add(face);
        continueRender(handle);
      })
      .catch(() => continueRender(handle));
  }, [handle]);
};

// Satu kata caption. Animasi HANYA blur + fade (aturan owner):
// - belum diucapkan: redup, sedikit blur
// - sedang diucapkan: biru #0064FF, bobot 800, blur->tajam dalam blurInFrames
// - sudah diucapkan: off-white penuh
// TANPA transform/translate/spring sama sekali.
const Word: React.FC<{word: CaptionWord}> = ({word}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;
  const {blurInFrames} = theme.caption;

  // Progres menajam 0->1 selama blurInFrames sejak kata mulai diucapkan.
  const sharp = interpolate(
    frame,
    [Math.round(word.start * fps), Math.round(word.start * fps) + blurInFrames],
    [0, 1],
    {extrapolateLeft: "clamp", extrapolateRight: "clamp"},
  );
  const isActive = t >= word.start && t < word.end;
  const isDone = t >= word.end;

  const color = isActive
    ? theme.colors.active
    : isDone
      ? theme.colors.text
      : theme.colors.upcoming;
  const fontWeight = isActive
    ? theme.caption.activeFontWeight
    : theme.caption.fontWeight;
  // Mendatang: blur tipis konstan. Aktif: blur menghilang seiring sharp.
  // Selesai: tajam penuh.
  const blurPx = isDone ? 0 : isActive ? (1 - sharp) * 4 : 1.2;

  return (
    <span
      style={{
        color,
        fontWeight,
        filter: blurPx > 0.05 ? `blur(${blurPx.toFixed(2)}px)` : undefined,
        textShadow: `0 2px 10px ${theme.colors.shadow}, 0 0 2px ${theme.colors.shadow}`,
      }}
    >
      {word.text}
    </span>
  );
};

// Blok caption: maksimal 2 baris, 5 kata per baris (disiplin cutter divisi).
// Blok masuk dengan fade (dan kata-katanya blur->tajam), keluar dengan fade
// singkat sebelum cue berikutnya mulai.
const CaptionBlock: React.FC<{cue: CaptionCue; nextStart: number | null}> = ({
  cue,
  nextStart,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;
  if (t < cue.start - 0.05 || t > cue.end + 0.15) return null;

  const fadeIn = interpolate(
    frame,
    [Math.round(cue.start * fps), Math.round(cue.start * fps) + 4],
    [0, 1],
    {extrapolateLeft: "clamp", extrapolateRight: "clamp"},
  );
  const outStart = nextStart !== null ? Math.min(cue.end, nextStart) : cue.end;
  const fadeOut = interpolate(
    frame,
    [
      Math.round(outStart * fps) - theme.caption.fadeOutFrames,
      Math.round(outStart * fps),
    ],
    [1, 0],
    {extrapolateLeft: "clamp", extrapolateRight: "clamp"},
  );

  // Satu kontainer flex-wrap: kata mengalir alami dan membungkus ke baris
  // berikutnya (maks ~2 baris untuk cue <= 10 kata pada fontSize ini).
  // JANGAN membagi per-div baris: div + wrap ganda membuat blok pecah
  // menjadi 3+ baris visual (cacat QA pilot pertama).
  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        top: `${theme.caption.anchorTopPct}%`,
        transform: "translateY(-50%)",
        display: "flex",
        flexWrap: "wrap",
        justifyContent: "center",
        alignItems: "baseline",
        columnGap: 11,
        rowGap: 2,
        padding: "0 28px",
        opacity: Math.min(fadeIn, fadeOut),
        fontFamily: theme.fonts.caption,
        fontSize: theme.caption.fontSize,
        lineHeight: theme.caption.lineHeight,
        textAlign: "center",
      }}
    >
      {cue.words.map((w, wi) => (
        <Word key={wi} word={w} />
      ))}
    </div>
  );
};

export const ClipCaptions: React.FC<ClipCaptionsProps> = ({videoSrc, cues}) => {
  useCaptionFont();
  const sorted = useMemo(
    () => [...cues].sort((a, b) => a.start - b.start),
    [cues],
  );
  return (
    <AbsoluteFill style={{backgroundColor: "#000"}}>
      {/* Layer aset: footage apa adanya — TANPA Ken Burns, grade, grain,
          transisi, atau gerakan buatan (aturan divisi). */}
      <OffthreadVideo
        src={staticFile(videoSrc)}
        style={{width: "100%", height: "100%", objectFit: "cover"}}
      />
      {/* Layer caption karaoke kata-per-kata di zona tengah vertikal. */}
      {sorted.map((cue, i) => (
        <CaptionBlock
          key={i}
          cue={cue}
          nextStart={i + 1 < sorted.length ? sorted[i + 1].start : null}
        />
      ))}
    </AbsoluteFill>
  );
};
