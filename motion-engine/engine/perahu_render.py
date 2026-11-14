#!/usr/bin/env python3
"""perahu_render.py — story-mode renderer for PERAHU TERAKHIR Episode 1.

Template resmi "video animasi" (perintah owner 28 Okt 2026 04:30 WIB):
gaya Ep2 Piper ini adalah template bernama "video animasi" — spesifikasi
lengkap di divisi/branding-promosi/template-video-animasi.md. Pipeline:
perahu_anim*.py (scene builders) + build_project() di sini + post + QA.

Visual style faithful to the reference reel (style only, original story):
- stick-figure bodies + big round heads with detailed expressive faces
- bold ALL-CAPS text, lime-green/white with THICK BLACK outline, center-bottom subtitles
- top-left overlay: small red label + big digital clock + episode sublabel
- dark brown/black palette, warm orange-yellow lamplight as key light

Entrance library (skill motion-video §4.3):
- rise+deblur (default for body/labels): 90px up, blur 9->0, opacity 0->1, expo-out, ~15f
- slam (hero words): scale 1.35->1 with overshoot, 2-frame impact shake, ~12f
- typewriter: character-by-character for dialog
- word stagger: ~4f apart, never simultaneous, never linear easing

Audio: VO loudnorm -15 (loudnorm BEFORE adelay), bed -34 LUFS with swell before
the final question + sidechain ducking under VO, soft thump on slam landings.
(Mix -15/-34 = konfigurasi TERKUNCI owner 2026-10-31 18:23; sebelumnya -16/-38.)
Hard cuts between scenes (no transitions, no exit fades).
"""

import json
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from motion_render import (font, text_size, expo_out, ease_out_back, clamp01,
                           add_grain, _resolve)

STORY = {
    "bg": (10, 8, 6),
    "ink": (245, 242, 235),       # warm white
    "ink_dim": (176, 163, 143),   # warm gray
    "accent": (176, 255, 72),     # lime-green hero word
    "red": (198, 44, 38),         # overlay label
    "yellow": (255, 208, 84),     # speaker label
    "font_hero": "DejaVuSans-Bold",
    "font_mono": "DejaVuSansMono-Bold",
}

FPS = 30
W, H = 1080, 1920


# ------------------------------------------------------------------ helpers
def _paste_rgba(base, ov):
    return Image.alpha_composite(base.convert("RGBA"), ov).convert("RGB")


def _audio_dur(path):
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", path],
            capture_output=True, text=True, check=True)
        return float(out.stdout.strip())
    except Exception:
        return 0.0


def _cover(img, W, H):
    s = max(W / img.width, H / img.height)
    img = img.resize((int(img.width * s) + 1, int(img.height * s) + 1),
                     Image.LANCZOS)
    x = (img.width - W) // 2
    y = (img.height - H) // 2
    return img.crop((x, y, x + W, y + H))


def _vignette(img, strength=0.32):
    W, H = img.size
    yy, xx = np.mgrid[0:H, 0:W]
    cx, cy = W / 2, H / 2
    r = np.sqrt(((xx - cx) / (W * 0.62)) ** 2 + ((yy - cy) / (H * 0.62)) ** 2)
    mask = np.clip(1 - strength * np.clip(r - 0.55, 0, 1) ** 1.6, 0, 1)
    a = np.asarray(img).astype(np.float32)
    a *= mask[:, :, None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


# ------------------------------------------------------- entrance primitives
def draw_word(img, word, cx, y_top, fnt, fill, f, start, slam=False, seed=0,
              rise_px=56, blur_max=7.0, dur=15, stroke=5):
    """One word with rise+deblur entrance; slam adds scale overshoot + 2f shake."""
    t = clamp01((f - start) / dur)
    if t <= 0:
        return img
    d = ImageDraw.Draw(img)
    tw, th = text_size(d, word, fnt)
    e = expo_out(t)
    yo = int(rise_px * (1 - e))
    blur = blur_max * (1 - e)
    alpha = int(255 * e)
    sc = 1.0
    shx = shy = 0
    if slam:
        se = ease_out_back(min(t * 1.35, 1.0))
        sc = 1.35 - 0.35 * se
        land_f = start + int(dur * 0.74)
        if f == land_f or f == land_f + 1:
            rng = np.random.default_rng(seed * 7919 + 13)
            shx = int(rng.integers(-8, 9))
            shy = int(rng.integers(-6, 7))
    pad = 48
    tmp = Image.new("RGBA", (tw + pad * 2, th + pad * 2 + 20), (0, 0, 0, 0))
    td = ImageDraw.Draw(tmp)
    td.text((pad, pad), word, font=fnt, fill=fill + (alpha,),
            stroke_width=stroke, stroke_fill=(0, 0, 0, alpha))
    if blur > 0.3:
        tmp = tmp.filter(ImageFilter.GaussianBlur(radius=blur))
    if abs(sc - 1.0) > 0.01:
        tmp = tmp.resize((max(int(tmp.width * sc), 1),
                          max(int(tmp.height * sc), 1)), Image.LANCZOS)
    if t >= 1.0:  # gentle float keeps the frame alive (anti-stiffness)
        yo += int(4 * math.sin(2 * math.pi * f / 90 + seed * 0.7))
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ov.paste(tmp, (int(cx - tmp.width / 2 + shx), int(y_top + yo + shy)), tmp)
    return _paste_rgba(img, ov)


def draw_line_stagger(img, words, cx, y_top, fnt, fill, f, start0, stagger=4,
                      accent=None, slam_seed=0, **kw):
    """Centered line, words entering ~stagger frames apart (never simultaneous).
    Layout memakai lebar slot efektif (_eff_widths): kata aksen mencadangkan
    pertumbuhan slam 1.35x + goyangan landing, jadi tinta tidak pernah
    keluar dari bentang baris yang sudah dibatasi zona aman."""
    d = ImageDraw.Draw(img)
    space_w, _ = text_size(d, " ", fnt)
    widths = [text_size(d, w, fnt)[0] for w in words]
    effs = _eff_widths(d, words, fnt, accent)
    total = sum(effs) + space_w * (len(words) - 1)
    x = cx - total / 2
    for i, w in enumerate(words):
        ww = widths[i]
        is_accent = accent is not None and w.strip(".,!?").upper() == accent
        c = fill if not is_accent else STORY["accent"]
        img = draw_word(img, w, x + effs[i] / 2, y_top, fnt, c, f,
                        start0 + i * stagger, slam=is_accent,
                        seed=slam_seed + i, **kw)
        x += effs[i] + space_w
    return img


def draw_typewriter_lines(img, lines, cx, y_top, fnt, fill, f, start, cpf=2,
                          line_h=None, stroke=5):
    """Multi-line typewriter: characters appear sequentially across lines."""
    if f < start or not lines:
        return img
    d = ImageDraw.Draw(img)
    if line_h is None:
        _, lh = text_size(d, "Ag", fnt)
        line_h = int(lh * 1.18)
    n = int((f - start) / cpf)
    total = sum(len(l) for l in lines)
    typing = n < total
    e = expo_out(clamp01((f - start) / 10))
    alpha = int(255 * e)
    yo = int(24 * (1 - e))
    y = y_top + yo
    used = 0
    for li, line in enumerate(lines):
        ln = max(min(n - used, len(line)), 0)
        used += len(line)
        shown = line[:ln]
        if not shown:
            y += line_h
            continue
        tw, th = text_size(d, shown, fnt)
        pad = 48
        tmp = Image.new("RGBA", (tw + pad * 2 + 60, th + pad * 2 + 20),
                        (0, 0, 0, 0))
        td = ImageDraw.Draw(tmp)
        td.text((pad, pad), shown, font=fnt, fill=fill + (alpha,),
                stroke_width=stroke, stroke_fill=(0, 0, 0, alpha))
        # block cursor on the actively-typing line
        if typing and ln < len(line) and (f // 8) % 2 == 0:
            cw = int(text_size(d, "M", fnt)[0] * 0.55)
            ch = int(th * 0.92)
            td.rectangle([(pad + tw + 8, pad + 4),
                          (pad + tw + 8 + cw, pad + 4 + ch)],
                         fill=fill + (alpha,))
        ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ov.paste(tmp, (int(cx - tmp.width / 2), int(y)), tmp)
        img = _paste_rgba(img, ov)
        y += line_h
    return img


def draw_typewriter(img, text, cx, y_top, fnt, fill, f, start, cpf=2,
                    stroke=5, cursor=True):
    """Character-by-character dialog entrance with block cursor while typing."""
    if f < start:
        return img
    n = int((f - start) / cpf)
    shown = text[:n]
    typing = n < len(text)
    if not shown:
        return img
    d = ImageDraw.Draw(img)
    e = expo_out(clamp01((f - start) / 10))
    alpha = int(255 * e)
    yo = int(24 * (1 - e))
    tw, th = text_size(d, shown, fnt)
    pad = 48
    tmp = Image.new("RGBA", (tw + pad * 2 + 40, th + pad * 2 + 20),
                    (0, 0, 0, 0))
    td = ImageDraw.Draw(tmp)
    td.text((pad, pad), shown, font=fnt, fill=fill + (alpha,),
            stroke_width=stroke, stroke_fill=(0, 0, 0, alpha))
    if cursor and typing and (f // 8) % 2 == 0:
        cw = int(text_size(d, "M", fnt)[0] * 0.55)
        ch = int(th * 0.92)
        td.rectangle([(pad + tw + 8, pad + 4),
                      (pad + tw + 8 + cw, pad + 4 + ch)],
                     fill=fill + (alpha,))
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ov.paste(tmp, (int(cx - tmp.width / 2), int(y_top + yo)), tmp)
    return _paste_rgba(img, ov)


# Zona aman teks (aturan owner 28 Okt 2026 ~18:38 WIB): frame 1080 lebar,
# semua teks di x=64..1016, y=64..1856. Kamera default Perahu adalah drift
# (zoom 1.05 + geser 26px selama scene) — pita pra-kamera yang aman di
# semua t: x=112..993. Lebar baris maks 840 -> bentang 120..960 pra-kamera
# (tepi akhir di frame: ~70..986, di dalam zona). Dialog 780 karena teks
# typewriter bergeser 30px ke kiri + kursor blok di ujung baris.
SAFE_L, SAFE_R = 64, 1016
HEADLINE_MAX_W = 840
BODY_MAX_W = 840
DIALOG_MAX_W = 780
_SLAM = 1.35  # skala kata aksen saat slam (draw_word)


def _eff_widths(draw, words, fnt, accent=None):
    """Lebar slot tiap kata: kata aksen mencadangkan pertumbuhan slam
    (1.35x) + goyangan landing 8px + outline 3px tiap sisi (+22px); kata
    biasa lebar apa adanya (outline 3px ditanggung margin bentang).
    Tanpa cadangan ini, kata aksen di ujung baris terpotong tepi saat slam
    (terukur: 'MEMBELI' 513px di baris 908px -> tinta x=-4)."""
    out = []
    for w in words:
        ww, _ = text_size(draw, w, fnt)
        if accent is not None and w.strip(".,!?").upper() == accent:
            out.append(ww * _SLAM + 22)
        else:
            out.append(float(ww))
    return out


def wrap_words(draw, words, fnt, max_w, accent=None):
    """Bungkus kata ke baris-baris dengan lebar slot efektif <= max_w.
    accent: kata yang di-slam (dicadangkan 1.35x) — bungkus & layout
    memakai angka yang sama supaya konsisten."""
    space_w, _ = text_size(draw, " ", fnt)
    effs = _eff_widths(draw, words, fnt, accent)
    lines, cur, curw = [], [], 0
    for w, eff in zip(words, effs):
        if cur and curw + space_w + eff > max_w:
            lines.append(cur)
            cur, curw = [], 0
        cur.append(w)
        curw += (space_w if curw else 0) + eff
    if cur:
        lines.append(cur)
    return lines

# ------------------------------------------------------------------ renderer
class PerahuRenderer:
    """Story-mode scene renderer: subtitle text, top-left overlay, slow camera."""

    def __init__(self, scene, fps=FPS, W=W, H=H):
        self.sc = scene
        self.fps, self.W, self.H = fps, W, H
        vo_path = _resolve(scene.get("vo"))
        scene["vo"] = vo_path
        self.vo_dur = _audio_dur(vo_path)
        hold = int(scene.get("hold_frames", 0))
        self.frames = int((self.vo_dur or 6.0) * fps) + 20 + 35 + hold
        bg = Image.open(_resolve(scene["bg"])).convert("RGB")
        bg = _cover(bg, W, H)
        # slight darken for subtitle legibility (keeps lamplight mood)
        bg = Image.blend(bg, Image.new("RGB", (W, H), (0, 0, 0)), 0.18)
        self.bg = bg
        self.camera = scene.get("camera", "drift")
        self.words = (scene.get("headline") or "").split()
        self.accent = (scene.get("accent_word") or "").strip().upper()
        self.body_words = (scene.get("body") or "").split()
        self.dialog = scene.get("dialog")          # quoted string or None
        self.speaker = scene.get("speaker")       # e.g. "TETANGGA"

    # -- camera: slow Ken Burns punctuation -------------------------------
    def _camera(self, img, f):
        W, H = self.W, self.H
        n = self.frames
        t = clamp01(f / max(n - 1, 1))
        if self.camera == "punch-in":
            scale = 1.07 - 0.07 * expo_out(t)
        elif self.camera == "punch-out":
            scale = 1.0 + 0.07 * expo_out(t)
        elif self.camera == "drift":
            scale = 1.05
        else:
            return img
        nw, nh = int(W * scale), int(H * scale)
        img = img.resize((nw, nh), Image.LANCZOS)
        x = (img.width - W) // 2
        y = (img.height - H) // 2
        if self.camera == "drift":
            x = int(x + 26 * t)
            y = int(y - 14 * t)
        return img.crop((x, y, x + W, y + H))

    # -- top-left overlay: red label + digital clock + episode sublabel ----
    def _overlay(self, img, f):
        st = STORY
        W = self.W
        d = ImageDraw.Draw(img)

        def rise_deblur_group(base, elems):
            # elems: (kind, y, start)
            for kind, y, start in elems:
                t = clamp01((f - start) / 14)
                if t <= 0:
                    continue
                e = expo_out(t)
                yo = int(44 * (1 - e))
                blur = 7 * (1 - e)
                alpha = int(255 * e)
                ov = Image.new("RGBA", base.size, (0, 0, 0, 0))
                od = ImageDraw.Draw(ov)
                if kind == "label":
                    lf = font(st["font_hero"], 30)
                    tw, th = text_size(od, "MALAM BANJIR", lf)
                    pad_x, pad_y = 22, 12
                    od.rounded_rectangle(
                        [(64, y + yo - pad_y),
                         (64 + tw + pad_x * 2, y + yo + th + pad_y)],
                        radius=10, fill=st["red"] + (alpha,))
                    od.text((64 + pad_x, y + yo), "MALAM BANJIR", font=lf,
                            fill=(255, 255, 255, alpha))
                elif kind == "clock":
                    cf = font(st["font_mono"], 88)
                    od.text((64, y + yo), "23:14", font=cf,
                            fill=st["ink"] + (alpha,),
                            stroke_width=4, stroke_fill=(0, 0, 0, alpha))
                elif kind == "sub":
                    sf = font(st["font_mono"], 30)
                    od.text((66, y + yo), "PERAHU TERAKHIR EPISODE 1",
                            font=sf, fill=st["ink_dim"] + (alpha,))
                if blur > 0.3:
                    ov = ov.filter(ImageFilter.GaussianBlur(radius=blur))
                base = _paste_rgba(base, ov)
            return base

        return rise_deblur_group(img, [("label", 86, 4),
                                       ("clock", 140, 9),
                                       ("sub", 248, 14)])

    # -- frame --------------------------------------------------------------
    def render_frame(self, f):
        st = STORY
        W, H = self.W, self.H
        img = self._camera(self.bg.copy(), f)
        img = _vignette(img)
        d = ImageDraw.Draw(img)

        img = self._overlay(img, f)

        hf = font(st["font_hero"], 100)
        if self.dialog:
            # speaker label (yellow) + quoted typewriter dialog (wrapped)
            df = font(st["font_hero"], 84)
            if self.speaker:
                sf = font(st["font_hero"], 44)
                t = clamp01((f - 10) / 14)
                if t > 0:
                    e = expo_out(t)
                    yo = int(40 * (1 - e))
                    alpha = int(255 * e)
                    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
                    od = ImageDraw.Draw(ov)
                    tw, _ = text_size(od, self.speaker, sf)
                    od.text((W / 2 - tw / 2, 980 + yo), self.speaker,
                            font=sf, fill=st["yellow"] + (alpha,),
                            stroke_width=4, stroke_fill=(0, 0, 0, alpha))
                    if 7 * (1 - e) > 0.3:
                        ov = ov.filter(
                            ImageFilter.GaussianBlur(radius=7 * (1 - e)))
                    img = _paste_rgba(img, ov)
            img = draw_typewriter_lines(
                img, [" ".join(l)
                      for l in wrap_words(d, self.dialog.split(), df,
                                          DIALOG_MAX_W)],
                W / 2, 1050, df, st["ink"], f, start=16, cpf=2, stroke=5)
        elif self.words:
            lines = wrap_words(d, self.words, hf, HEADLINE_MAX_W,
                               accent=self.accent or None)
            _, lh = text_size(d, "Ag", hf)
            line_h = int(lh * 1.18)
            y0 = 1150 - (len(lines) - 1) * line_h // 2
            for li, line in enumerate(lines):
                img = draw_line_stagger(
                    img, line, W / 2, y0 + li * line_h, hf, st["ink"], f,
                    start0=14, stagger=4, accent=self.accent or None,
                    slam_seed=li * 131 + 7, rise_px=48, blur_max=6.0, dur=14,
                    stroke=5)

        if self.body_words:
            bf = font(st["font_hero"], 52)
            lines = wrap_words(d, self.body_words, bf, BODY_MAX_W)
            _, lh = text_size(d, "Ag", bf)
            line_h = int(lh * 1.25)
            y0 = 1470 - (len(lines) - 1) * line_h // 2
            for li, line in enumerate(lines):
                img = draw_line_stagger(
                    img, line, W / 2, y0 + li * line_h, bf, st["ink"], f,
                    start0=36 + li * 6, stagger=4, accent=None,
                    slam_seed=li * 57 + 3, rise_px=90, blur_max=9.0, dur=15,
                    stroke=4)

        img = add_grain(img, amount=5, seed=f)
        return img


# ------------------------------------------------------------------ assembly
def build_project(scenes, bed_path, thump_path, out_mp4, tmpdir,
                  fps=FPS, W=W, H=H):
    os.makedirs(tmpdir, exist_ok=True)
    # NOTE: no tmpdir wipe — resume-safe rendering skips existing frames
    frame_idx = 0
    audio_inputs = []   # (vo_path, start_sec)
    thump_frames = []   # slam landing frames (global)
    scene_starts = []   # (start_frame, start_sec)
    t = 0.0
    for si, sc in enumerate(scenes):
        sc = dict(sc)
        r = PerahuRenderer(sc, fps, W, H)
        start_frame = frame_idx
        scene_starts.append((start_frame, t))
        for f in range(r.frames):
            fp = f"{tmpdir}/f{frame_idx:06d}.jpg"
            if not os.path.exists(fp):  # resume-safe: skip rendered frames
                r.render_frame(f).save(fp, quality=88)
            frame_idx += 1
        if sc.get("vo"):
            audio_inputs.append((sc["vo"], t))
        # thump on hero-word slam landing (scenes with accent_word)
        if sc.get("accent_word"):
            words = (sc.get("headline") or "").split()
            try:
                hero_i = [w.strip(".,!?").upper()
                          for w in words].index(sc["accent_word"].strip().upper())
            except ValueError:
                hero_i = 0
            thump_frames.append(start_frame + 14 + hero_i * 4 + 9)
        t += r.frames / fps

    total_dur = frame_idx / fps
    # NOTE: video input goes LAST — ffmpeg 8 misbinds [N:a] labels when an
    # image-sequence is input 0 together with a quoted volume expression.
    cmd = ["ffmpeg", "-y"]
    idx = 0
    vo_labels = []
    for path, start in audio_inputs:
        cmd += ["-i", path]
        ms = int(start * 1000)
        # AGENTS.md lesson: loudnorm BEFORE adelay
        vo_labels.append(
            f"[{idx}:a]loudnorm=I=-15:TP=-1.0:LRA=11,adelay={ms}|{ms}[v{idx + 1}]")
        idx += 1
    thump_labels = []
    for fr in thump_frames:
        cmd += ["-i", thump_path]
        ms = int(fr / fps * 1000)
        thump_labels.append(f"[{idx}:a]adelay={ms}|{ms},volume=0.25[th{idx}]")
        idx += 1

    # bed: trim -> -34 LUFS -> swell before final question -> duck under VO
    cmd += ["-stream_loop", "-1", "-i", bed_path]
    bidx = idx
    idx += 1
    t5 = scene_starts[4][1] if len(scene_starts) > 4 else total_dur * 0.8
    swell_inner = (f"if(lt(t,{t5:.2f}),1,"
                   f"if(lt(t,{t5 + 4:.2f}),1+0.25*(t-{t5:.2f}),"
                   f"if(lt(t,{total_dur - 3:.2f}),2,"
                   f"2*max(0,1-(t-({total_dur - 3:.2f}))/3))))")
    swell = f"if(isnan(t),1,{swell_inner})"
    bed_chain = (f"[{bidx}:a]atrim=0:{total_dur:.2f},"
                 f"loudnorm=I=-34:TP=-2:LRA=11,"
                 f"volume='{swell}'[bedn]")
    vomix_in = "".join(f"[v{i}]" for i in range(1, len(vo_labels) + 1))
    vomix = (f"{vomix_in}amix=inputs={len(vo_labels)}:normalize=0,"
             f"apad=whole_dur={total_dur:.2f},asplit=2[vomix1][vomix2]")
    duck = ("[bedn][vomix1]sidechaincompress=threshold=0.04:ratio=6:"
            "attack=400:release=1200[bed]")

    # NOTE (bugfix 2026-10-23): [vomix] was consumed twice (sidechain + final
    # amix) without asplit — ffmpeg starved the second consumer, so only the
    # first VO survived. Now split: vomix1 -> sidechain, vomix2 -> final mix.
    all_labels = (["[vomix2]"]
                  + [f"[th{i}]" for i in range(
                      len(vo_labels),
                      len(vo_labels) + len(thump_labels))]
                  + ["[bed]"])
    filter_parts = vo_labels + thump_labels + [bed_chain, vomix, duck]
    filter_parts.append(
        f"{''.join(all_labels)}amix=inputs={len(all_labels)}:"
        f"duration=longest:normalize=0,atrim=0:{total_dur:.2f},"
        f"alimiter=limit=0.9:attack=5:release=50[aout]")
    vidx = idx  # video frames go last (see note above)
    cmd += ["-framerate", str(fps), "-i", f"{tmpdir}/f%06d.jpg"]
    cmd += ["-filter_complex", ";".join(filter_parts),
            "-map", f"{vidx}:v", "-map", "[aout]",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
            "-c:a", "aac", "-shortest", out_mp4]
    print("assembling", frame_idx, "frames,", f"{total_dur:.1f}s ...")
    subprocess.run(cmd, check=True)
    print("done:", out_mp4)
    return total_dur, scene_starts
