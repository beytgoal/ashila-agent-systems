#!/usr/bin/env python3
"""perahu_anim_paradoks.py — PARADOKS PILIHAN, tes gaya VIDEO-ANIMASI (#4 dari 10).

Turunan perahu_anim_ep2.py (template video-animasi). Cerita orisinal dari
riset ep14 (studi selai Iyengar & Lepper 2000, maximizer vs satisficer),
bukan Perahu Terakhir — hanya GAYA visualnya yang dipakai: animasi 2D
gelap malam + hujan, karikatur chunky (stick_rig.py), palet gelap, teks
ALL-CAPS outline hitam tebal, overlay jam kiri atas, hard cut, musik
dramatis no-copyright. VO Charlie dipakai ulang (vo1..vo6.wav).

Story (~80 dtk, 5 scene + closing hook vo6):
  1. Scroll — pemuda di sofa malam hari, TV penuh pilihan, tak nonton apa-apa (vo1)
  2. Selai — lapak selai malam hari, 24 rasa vs 6 rasa (vo2)
  3. 3% — dua meja: 24 selai + 3 koin vs 6 selai + 10 koin (vo3)
  4. Lumpuh — close-up, tiga gelembung pikiran: ?, 23, ! (vo4)
  5. Maximizer vs Satisficer — kiri panik di antara selai, kanan tenang
     dengan satu selai; hold 280f untuk hook penutup vo6 (vo5 + vo6)

Overlay: label MALAM / jam 23:47 / sublabel PARADOKS PILIHAN.
Perempuan WAJIB berkerudung (scarf) — penjual selai & satisficer.
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import perahu_anim as PA
import perahu_render as PR
from perahu_render import STORY, font, text_size, add_grain
from stick_rig import (Character, Rain, Water, Lamp, draw_ripple,
                       clamp01, expo_out)

FPS = 30
W, H = 1080, 1920
CLOCK = "23:47"
EP_LABEL = "PARADOKS PILIHAN"

SKIN_MAN = (196, 138, 96)
SKIN_WOMAN = (204, 146, 100)

# warna selai (deterministik per indeks)
JAM_COLORS = [(178, 34, 34), (220, 120, 40), (110, 60, 140),
              (230, 170, 80), (60, 60, 140), (140, 180, 60),
              (200, 60, 90), (90, 140, 110)]


def draw_jar(d, cx, y_bottom, w, h, color):
    """Satu stoples selai: badan + tutup + label."""
    x0, x1 = cx - w / 2, cx + w / 2
    y0 = y_bottom - h
    d.rounded_rectangle([(x0, y0 + h * 0.22), (x1, y_bottom)],
                        radius=int(w * 0.18), fill=color + (255,))
    d.rounded_rectangle([(x0 + w * 0.08, y0),
                         (x1 - w * 0.08, y0 + h * 0.26)],
                        radius=int(w * 0.08), fill=(210, 190, 150, 255))
    lw = w * 0.72
    d.rounded_rectangle([(cx - lw / 2, y0 + h * 0.48),
                         (cx + lw / 2, y0 + h * 0.78)],
                        radius=4, fill=(245, 240, 225, 255))


def overlay_topleft_paradoks(img, f):
    """Red label + digital clock + episode sublabel (identitas tes ini)."""
    st = STORY
    base = img
    for kind, y, start in (("label", 86, 4), ("clock", 140, 9), ("sub", 248, 14)):
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
            tw, th = text_size(od, "MALAM", lf)
            od.rounded_rectangle([(64, y + yo - 12),
                                  (64 + tw + 44, y + yo + th + 12)],
                                 radius=10, fill=st["red"] + (alpha,))
            od.text((64 + 22, y + yo), "MALAM", font=lf,
                    fill=(255, 255, 255, alpha))
        elif kind == "clock":
            cf = font(st["font_mono"], 88)
            od.text((64, y + yo), CLOCK, font=cf,
                    fill=st["ink"] + (alpha,),
                    stroke_width=4, stroke_fill=(0, 0, 0, alpha))
        else:
            sf = font(st["font_mono"], 30)
            od.text((66, y + yo), EP_LABEL,
                    font=sf, fill=st["ink_dim"] + (alpha,))
        if blur > 0.3:
            ov = ov.filter(ImageFilter.GaussianBlur(radius=blur))
        base = Image.alpha_composite(base.convert("RGBA"), ov).convert("RGB")
    return base


class ParadoksBase:
    def __init__(self, sc, fps=FPS):
        self.sc = sc
        self.fps = fps
        vo = sc.get("vo")
        self.vo_dur = PA.audio_dur(vo) if vo else 6.0
        hold = int(sc.get("hold_frames", 0))
        self.frames = int(self.vo_dur * fps) + 20 + 35 + hold
        self.rain = Rain(n=170, seed=7 + id(self) % 97)
        self.words = sc.get("headline") or ""
        self.accent = (sc.get("accent_word") or "").strip().upper()
        self.body = sc.get("body") or ""
        self.dialog = sc.get("dialog")
        self.speaker = sc.get("speaker")

    def finish(self, img, f):
        img = overlay_topleft_paradoks(img, f)
        img = PA.subtitle_block(img, f, self.words, self.accent, self.body,
                                self.dialog, self.speaker)
        img = PA.vignette(img)
        img = add_grain(img, amount=5, seed=f)
        return img.convert("RGB")


def make_man(unit=520):
    return Character(unit=unit, skin=SKIN_MAN, shirt=(54, 66, 62),
                     pants=(44, 46, 52), hair="short",
                     hair_color=(22, 18, 16), name="pemuda")


def make_woman(unit=420):
    """Penjual selai / satisficer — WAJIB berkerudung (scarf)."""
    return Character(unit=unit, skin=SKIN_WOMAN, shirt=(96, 70, 110),
                     pants=(52, 52, 68), hair="short",
                     hair_color=(22, 18, 16),
                     scarf=(139, 69, 78), name="perempuan")


class PdxS1Scroll(ParadoksBase):
    """Malam hari di ruang tamu: pemuda di sofa, TV penuh pilihan."""

    def __init__(self, sc, fps=FPS):
        super().__init__(sc, fps)
        self.bg = PA.night_sky(W, H, seed=18)
        self.lamp = Lamp(x=170, y_top=420, h=420)
        self.man = make_man(520)
        self.man.sit()
        self.rain = Rain(n=70, seed=41)

    def _draw_tv(self, img, t):
        d = ImageDraw.Draw(img)
        # TV frame + glow
        d.rounded_rectangle([(230, 400), (850, 800)], radius=18,
                            fill=(12, 10, 9, 255), outline=(60, 52, 44, 255),
                            width=6)
        # thumbnail grid 4x3, brightness pulses as he "scrolls"
        cols, rows = 4, 3
        tw, th, gap = 128, 88, 12
        x0, y0 = 252, 424
        thumbs = [(178, 34, 34), (42, 62, 108), (140, 180, 60),
                  (220, 120, 40), (110, 60, 140), (200, 60, 90),
                  (90, 140, 110), (230, 170, 80), (60, 60, 140),
                  (178, 34, 34), (42, 62, 108), (140, 180, 60)]
        for i, col in enumerate(thumbs):
            r, c = divmod(i, cols)
            b = 0.55 + 0.45 * math.sin(2 * math.pi * t / 3.0 + i * 0.9)
            fill = tuple(int(v * (0.45 + 0.55 * b)) for v in col)
            d.rounded_rectangle(
                [(x0 + c * (tw + gap), y0 + r * (th + gap)),
                 (x0 + c * (tw + gap) + tw, y0 + r * (th + gap) + th)],
                radius=8, fill=fill + (255,))
        # remote on the couch arm
        d.rounded_rectangle([(880, 1180), (930, 1300)], radius=10,
                            fill=(40, 36, 32, 255))

    def _draw_couch(self, img):
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([(150, 1000), (930, 1160)], radius=30,
                            fill=(70, 50, 40, 255))
        d.rounded_rectangle([(150, 1140), (930, 1340)], radius=30,
                            fill=(88, 62, 48, 255))
        d.rounded_rectangle([(150, 1060), (210, 1340)], radius=20,
                            fill=(80, 56, 44, 255))
        d.rounded_rectangle([(870, 1060), (930, 1340)], radius=20,
                            fill=(80, 56, 44, 255))

    def render_frame(self, f):
        t = f / self.fps
        img = self.bg.copy()
        d = ImageDraw.Draw(img)
        # window with night + rain glow (left wall)
        d.rectangle([70, 420, 200, 780], fill=(16, 20, 34, 255))
        d.rectangle([70, 420, 200, 780], outline=(60, 52, 44, 255), width=6)
        d.line([(135, 420), (135, 780)], fill=(60, 52, 44, 255), width=5)
        d.line([(70, 600), (200, 600)], fill=(60, 52, 44, 255), width=5)
        mg = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(mg).ellipse([110, 470, 170, 530],
                                   fill=(210, 205, 190, 70))
        img = Image.alpha_composite(img.convert("RGBA"), mg)
        self.lamp.draw(img, t, W, H)
        self._draw_tv(img, t)
        self._draw_couch(img)
        # man on the couch, scrolling his phone
        m = self.man
        m.idle_breathe(t, rate=0.26, amp=1.0)
        m.set_expr("tired" if t > 5.0 else "worried")
        if t > 1.5:
            m.head_down(t - 1.5, dur=1.2, amount=18)
        m.pose["shoulder_R"] = -38  # right arm up toward phone
        m.pose["elbow_R"] = 55
        m.pos = (480, 1010)
        m.draw(img)
        # phone glow in his hand, bobbing with the scroll
        bob = 6 * math.sin(2 * math.pi * t / 1.8)
        ph = Image.new("RGBA", img.size, (0, 0, 0, 0))
        pd = ImageDraw.Draw(ph)
        px, py = 640, 1060 + bob
        pd.rounded_rectangle([(px - 26, py - 44), (px + 26, py + 44)],
                             radius=10, fill=(120, 170, 230, 230))
        pd.rounded_rectangle([(px - 18, py - 34), (px + 18, py + 34)],
                             radius=6, fill=(200, 225, 255, 255))
        img = Image.alpha_composite(img.convert("RGBA"), ph)
        self.rain.draw(img, t, W, H)
        return self.finish(img, f)


class PdxS2Selai(ParadoksBase):
    """Lapak selai malam hari: 24 rasa vs 6 rasa, penjual berkerudung."""

    def __init__(self, sc, fps=FPS):
        super().__init__(sc, fps)
        self.bg = PA.night_sky(W, H, seed=19)
        self.lamp = Lamp(x=540, y_top=300, h=380)
        self.woman = make_woman(420)
        self.rain = Rain(n=120, seed=42)

    def _draw_stall(self, img, t):
        d = ImageDraw.Draw(img)
        # string lights
        for i in range(13):
            x = 70 + i * 78
            y = 330 + 26 * math.sin(math.pi * i / 12)
            fl = 0.75 + 0.25 * math.sin(2 * math.pi * t / 1.3 + i)
            r = 7
            d.ellipse([x - r, y - r, x + r, y + r],
                      fill=(int(255 * fl), int(208 * fl), int(84 * fl), 255))
        # table
        d.rectangle([(110, 1180), (970, 1420)], fill=(74, 52, 34, 255))
        d.rectangle([(110, 1180), (970, 1210)], fill=(104, 76, 48, 255))
        d.rectangle([(160, 1420), (200, 1560)], fill=(60, 42, 28, 255))
        d.rectangle([(880, 1420), (920, 1560)], fill=(60, 42, 28, 255))
        # left group: 24 jars, 8 cols x 3 rows
        for r in range(3):
            for c in range(8):
                cx = 165 + c * 52
                yb = 1180 - r * 92
                draw_jar(d, cx, yb, 46, 80,
                         JAM_COLORS[(r * 8 + c) % len(JAM_COLORS)])
        # right group: 6 jars, 3 cols x 2 rows (bigger, spaced)
        for r in range(2):
            for c in range(3):
                cx = 700 + c * 110
                yb = 1180 - r * 140
                draw_jar(d, cx, yb, 92, 124,
                         JAM_COLORS[(r * 3 + c + 3) % len(JAM_COLORS)])

    def render_frame(self, f):
        t = f / self.fps
        img = self.bg.copy()
        d = ImageDraw.Draw(img)
        PA.house_silhouette(d, 150, 1080, 300, 420)
        PA.house_silhouette(d, 930, 1080, 260, 380)
        self.lamp.draw(img, t, W, H)
        # shopkeeper BEHIND the table: draw her first, jars/table occlude
        # her lower body (depth), then the stall in front.
        w = self.woman
        w.idle_breathe(t, rate=0.32, amp=0.8)
        wt = t % 2.4
        if wt < 1.5:
            w.arm_raise(wt, dur=1.0, arm="R")
        else:
            w.arm_lower(wt - 1.5, dur=0.9, arm="R", start_angle=150.0)
        w.set_expr("neutral")
        w.pos = (540, 900)
        w.draw(img)
        self._draw_stall(img, t)
        self.rain.draw(img, t, W, H)
        return self.finish(img, f)


class PdxS3TigaPersen(ParadoksBase):
    """Dua kelompok selai di satu meja: 24 rasa + 3 koin vs 6 rasa + 10 koin."""

    def __init__(self, sc, fps=FPS):
        super().__init__(sc, fps)
        self.bg = PA.night_sky(W, H, seed=20)
        self.lamp = Lamp(x=540, y_top=280, h=360)
        self.rain = Rain(n=110, seed=43)

    def _draw_coins(self, d, xs, y, n):
        for i, x in enumerate(xs[:n]):
            d.ellipse([x - 16, y - 16, x + 16, y + 16],
                      fill=(255, 208, 84, 255),
                      outline=(160, 110, 20, 255), width=3)
            d.ellipse([x - 8, y - 8, x + 8, y + 8],
                      outline=(160, 110, 20, 255), width=2)

    def render_frame(self, f):
        t = f / self.fps
        img = self.bg.copy()
        d = ImageDraw.Draw(img)
        PA.house_silhouette(d, 150, 1080, 300, 420)
        PA.house_silhouette(d, 930, 1080, 260, 380)
        self.lamp.draw(img, t, W, H)
        # long table
        d.rectangle([(90, 1120), (990, 1340)], fill=(74, 52, 34, 255))
        d.rectangle([(90, 1120), (990, 1150)], fill=(104, 76, 48, 255))
        # left: 24 jars, 6 cols x 4 rows
        for r in range(4):
            for c in range(6):
                cx = 155 + c * 62
                yb = 1120 - r * 84
                draw_jar(d, cx, yb, 52, 74,
                         JAM_COLORS[(r * 6 + c) % len(JAM_COLORS)])
        # right: 6 jars, 3 cols x 2 rows
        for r in range(2):
            for c in range(3):
                cx = 660 + c * 120
                yb = 1120 - r * 150
                draw_jar(d, cx, yb, 100, 134,
                         JAM_COLORS[(r * 3 + c + 5) % len(JAM_COLORS)])
        # coins: 3 on the left, 10 on the right
        self._draw_coins(d, [200, 260, 320], 1240, 3)
        self._draw_coins(d, [640, 700, 760, 820, 880,
                             640, 700, 760, 820, 880], 1240, 5)
        self._draw_coins(d, [670, 730, 790, 850, 910], 1285, 5)
        # a hand reaches in from top-right toward the 6-jar group,
        # fingers pointing DOWN to grip a jar from above
        reach = clamp01((t - 1.0) / 2.0)
        re_ = reach * reach * (3 - 2 * reach)
        hx, hy = 1000 - 220 * re_, 480 + 340 * re_
        d.line([(1020, 420), (hx, hy - 10)], fill=SKIN_MAN + (255,), width=42,
               joint="curve")
        d.ellipse([hx - 30, hy - 34, hx + 30, hy + 22],
                  fill=SKIN_MAN + (255,))
        for fi, fa in enumerate((-26, -9, 9, 26)):
            d.line([(hx + fa, hy + 12), (hx + fa * 1.15, hy + 54)],
                   fill=SKIN_MAN + (255,), width=13)
        draw_ripple(img, 780, 1120, t, seed=15, max_r=60)
        self.rain.draw(img, t, W, H)
        return self.finish(img, f)


class PdxS4Lumpuh(ParadoksBase):
    """Close-up: pemuda menunduk, tiga gelembung pikiran muncul bertahap."""

    def __init__(self, sc, fps=FPS):
        super().__init__(sc, fps)
        self.bg = PA.night_sky(W, H, seed=21)
        self.water = Water(y_base=1560, seed=24)
        self.man = make_man(780)
        self.rain = Rain(n=90, seed=44)

    def _bubble(self, img, f, cx, cy, r, text, start):
        t = clamp01((f - start) / 12)
        if t <= 0:
            return img
        e = expo_out(t)
        rr = max(int(r * e), 1)
        ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        alpha = int(255 * e)
        od.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                   fill=(245, 242, 235, alpha),
                   outline=(20, 16, 12, alpha), width=5)
        bf = font(STORY["font_hero"], int(r * 0.95))
        tw, th = text_size(od, text, bf)
        od.text((cx - tw / 2, cy - th / 2), text, font=bf,
                fill=(30, 25, 20, alpha))
        # trailing dots toward the head — kept just outside the bubble so
        # they never land on the face (head centre ~ (540, 830), r ~117)
        hx, hy = 540.0, 830.0
        dx, dy = hx - cx, hy - cy
        ln = math.hypot(dx, dy) or 1.0
        ux, uy = dx / ln, dy / ln
        for dist, dr in ((r + 30, 12), (r + 55, 8)):
            px, py = cx + ux * dist, cy + uy * dist
            od.ellipse([px - dr, py - dr, px + dr, py + dr],
                       fill=(245, 242, 235, alpha))
        return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")

    def render_frame(self, f):
        t = f / self.fps
        img = self.bg.copy()
        d = ImageDraw.Draw(img)
        d.arc([140, 1500, 940, 1900], start=180, end=360,
              fill=(74, 52, 34, 255), width=60)
        m = self.man
        m.idle_breathe(t, rate=0.26, amp=1.2)
        m.set_expr("sad" if t > 3.0 else "worried")
        if t > 1.5:
            m.head_down(t - 1.5, dur=1.2, amount=26)
        if 3.0 < t < 5.0:
            m.head_turn_to(t - 3.0, dur=0.9, direction=-1.0)
        elif t >= 5.0:
            m.head_turn_to(t - 5.0, dur=0.9, direction=1.0)
        if t > 1.2:
            m.arm_lower(t - 1.2, dur=1.6, arm="R", start_angle=40.0)
        m.pos = (540, 1010)
        m.draw(img)
        self.water.draw(img, t, W, H)
        self.rain.draw(img, t, W, H)
        # thought bubbles appear one by one (right column, clear of the head)
        img = self._bubble(img, f, 860, 440, 72, "?", 60)
        img = self._bubble(img, f, 890, 620, 62, "23", 120)
        img = self._bubble(img, f, 850, 780, 56, "!", 180)
        return self.finish(img, f)


class PdxS5DuaTipe(ParadoksBase):
    """Kiri: maximizer panik di antara selai. Kanan: satisficer tenang."""

    def __init__(self, sc, fps=FPS):
        super().__init__(sc, fps)
        self.bg = PA.night_sky(W, H, seed=22)
        self.lamp = Lamp(x=850, y_top=320, h=400)
        self.maxer = make_man(420)
        self.sat = make_woman(420)
        self.sat.sit()
        self.rain = Rain(n=60, seed=45)
        # scattered jars on the maximizer's side (fixed layout)
        self.scatter = []
        rng = np.random.default_rng(11)
        for i in range(10):
            self.scatter.append((int(rng.uniform(90, 480)),
                                 int(rng.uniform(1240, 1420)),
                                 int(rng.uniform(44, 66)),
                                 JAM_COLORS[i % len(JAM_COLORS)]))

    def render_frame(self, f):
        t = f / self.fps
        img = self.bg.copy()
        d = ImageDraw.Draw(img)
        # divider between the two halves
        d.rectangle([(537, 320), (543, 1150)], fill=(60, 50, 40, 255))
        self.lamp.draw(img, t, W, H)
        # --- maximizer side (left): pacing among scattered jars
        for cx, yb, w, col in self.scatter:
            draw_jar(d, cx, yb, w, int(w * 1.5), col)
        mx = 280 + 90 * math.sin(2 * math.pi * t / 3.0)
        self.maxer.walk(t, stride_freq=1.8)
        self.maxer.set_expr("panic")
        self.maxer.pose["shoulder_R"] = -120
        self.maxer.pose["elbow_R"] = 25
        self.maxer.pose["shoulder_L"] = -110
        self.maxer.pose["elbow_L"] = 20
        self.maxer.pos = (mx, 1000)
        self.maxer.draw(img)
        # --- satisficer side (right): calm, one jar in her lap
        w = self.sat
        w.idle_breathe(t, rate=0.24, amp=0.7)
        w.set_expr("neutral")
        w.pos = (800, 1010)
        w.draw(img)
        draw_jar(d, 800, 1180, 92, 128, (178, 34, 34))
        # warm glow on the calm side (blurred: soft wash, no hard edge)
        glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gd.ellipse([640, 700, 1040, 1300], fill=(255, 190, 90, 26))
        glow = glow.filter(ImageFilter.GaussianBlur(radius=60))
        img = Image.alpha_composite(img.convert("RGBA"), glow)
        self.rain.draw(img, t, W, H)
        return self.finish(img, f)


BUILDERS = [PdxS1Scroll, PdxS2Selai, PdxS3TigaPersen, PdxS4Lumpuh,
            PdxS5DuaTipe]


def main():
    ENG = os.path.dirname(os.path.abspath(__file__))
    proj = json.load(open(os.path.join(ENG, "perahu-project-paradoks.json")))
    scenes = proj["scenes"]
    for i, sc in enumerate(scenes):
        sc["anim"] = i
    bed = proj["bed"]
    thump = proj.get("thump")
    out = os.path.join(ENG, "demos", "paradoks-pilihan-video-animasi-base.mp4")
    tmpdir = os.path.join(ENG, "render-frames-paradoks")
    # FRESH tmpdir — durasi VO baru; memakai tmpdir lama akan memakai ulang
    # frame lama di posisi yang salah (pola perahu_anim_ep2_piper.py).
    os.makedirs(tmpdir, exist_ok=True)

    def factory(sc, fps, W_, H_):
        return BUILDERS[sc["anim"]](sc, fps)

    PR.PerahuRenderer = factory
    total_dur, scene_starts = PR.build_project(scenes, bed, thump, out,
                                               tmpdir, fps=FPS, W=W, H=H)
    with open(os.path.join(tmpdir, "manifest.json"), "w") as fh:
        json.dump({"total_dur": total_dur, "scene_starts": scene_starts}, fh)
    print("PARADOKS base render done:", out, f"{total_dur:.1f}s")
    for i, (sf, ss) in enumerate(scene_starts):
        print(f"  scene{i+1}: start_frame={sf} start_sec={ss:.2f}")


if __name__ == "__main__":
    main()
