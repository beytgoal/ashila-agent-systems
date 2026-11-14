#!/usr/bin/env python3
"""perahu_anim.py — PERAHU TERAKHIR Episode 1, v2: REAL character animation.

Replaces the v1 Ken-Burns-on-stills approach with a programmatic 2D
caricature rig (stick_rig.py), frame-by-frame at 30fps:
- big-head caricature characters, thick capsule limbs, articulated joints
- walk cycle, idle breathing, arm raise, rowing, head tilt/turn, door open
- living environment: rain particles, wave water, bobbing boat, lamp flicker

Visual style (approved, faithful to reference reel — style only):
- dark brown/black palette + warm orange lamplight
- bold ALL-CAPS text, lime/white with thick black outline, bottom-center
- top-left overlay: MALAM BANJIR / 23:14 / PERAHU TERAKHIR EPISODE 1
- typography entrances: slam / typewriter / rise+deblur (from perahu_render)

Audio: reuses v1 VO files + "Anguish" Kevin MacLeod (CC-BY) bed.
Assembly reuses perahu_render.build_project (ffmpeg bugs already fixed).
"""

import json
import math
import os
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import perahu_render as PR
from perahu_render import (STORY, font, text_size, draw_word,
                           draw_line_stagger, draw_typewriter_lines,
                           wrap_words, add_grain, HEADLINE_MAX_W,
                           BODY_MAX_W, DIALOG_MAX_W)
from stick_rig import (Character, Rain, Water, Boat, Lamp, House, draw_oar,
                       draw_ripple, clamp01, expo_out, expo_in_out,
                       ease_out_back, blit_rot)

FPS = 30
W, H = 1080, 1920

# ------------------------------------------------------------- shared pieces
_vignette_mask = None


def vignette(img, strength=0.34):
    global _vignette_mask
    if _vignette_mask is None or _vignette_mask.size != img.size:
        W_, H_ = img.size
        yy, xx = np.mgrid[0:H_, 0:W_]
        cx, cy = W_ / 2, H_ / 2
        r = np.sqrt(((xx - cx) / (W_ * 0.62)) ** 2
                    + ((yy - cy) / (H_ * 0.62)) ** 2)
        _vignette_mask = np.clip(1 - strength * np.clip(r - 0.55, 0, 1) ** 1.6,
                                 0, 1).astype(np.float32)
    a = np.asarray(img).astype(np.float32)
    a *= _vignette_mask[:, :, None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def night_sky(W, H, top=(8, 7, 6), horizon=(34, 26, 20), seed=5):
    """Painted night gradient + dim stars (cached per (W,H,seed))."""
    key = (W, H, seed, top, horizon)
    if getattr(night_sky, "_cache", {}).get("key") == key:
        return night_sky._cache["img"].copy()
    grad = np.zeros((H, W, 3), dtype=np.uint8)
    for c in range(3):
        grad[:, :, c] = np.linspace(top[c], horizon[c], H)[:, None]
    img = Image.fromarray(grad, "RGB").convert("RGBA")
    rng = np.random.default_rng(seed)
    d = ImageDraw.Draw(img)
    for _ in range(90):
        x, y = rng.uniform(0, W), rng.uniform(0, H * 0.45)
        b = int(rng.uniform(40, 110))
        d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(b, b, b, 200))
    night_sky._cache = {"key": key, "img": img}
    return img.copy()


def house_silhouette(d, x, y_base, w, h, color=(16, 12, 10, 255)):
    d.rectangle([x - w / 2, y_base - h, x + w / 2, y_base], fill=color)
    d.polygon([(x - w / 2 - 30, y_base - h), (x + w / 2 + 30, y_base - h),
               (x, y_base - h - 130)], fill=color)


def overlay_topleft(img, f):
    """Red label + digital clock + episode sublabel (our own identity)."""
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
            tw, th = text_size(od, "MALAM BANJIR", lf)
            od.rounded_rectangle([(64, y + yo - 12),
                                  (64 + tw + 44, y + yo + th + 12)],
                                 radius=10, fill=st["red"] + (alpha,))
            od.text((64 + 22, y + yo), "MALAM BANJIR", font=lf,
                    fill=(255, 255, 255, alpha))
        elif kind == "clock":
            cf = font(st["font_mono"], 88)
            od.text((64, y + yo), "23:14", font=cf,
                    fill=st["ink"] + (alpha,),
                    stroke_width=4, stroke_fill=(0, 0, 0, alpha))
        else:
            sf = font(st["font_mono"], 30)
            od.text((66, y + yo), "PERAHU TERAKHIR EPISODE 1",
                    font=sf, fill=st["ink_dim"] + (alpha,))
        if blur > 0.3:
            ov = ov.filter(ImageFilter.GaussianBlur(radius=blur))
        base = Image.alpha_composite(base.convert("RGBA"), ov).convert("RGB")
    return base


def subtitle_block(img, f, headline, accent, body, dialog=None, speaker=None):
    """v1-compatible subtitle layout: headline ~y1150, body ~y1470."""
    st = STORY
    d = ImageDraw.Draw(img)
    hf = font(st["font_hero"], 100)
    if dialog:
        df = font(st["font_hero"], 84)
        if speaker:
            sf = font(st["font_hero"], 44)
            t = clamp01((f - 10) / 14)
            if t > 0:
                e = expo_out(t)
                yo = int(40 * (1 - e))
                alpha = int(255 * e)
                ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
                od = ImageDraw.Draw(ov)
                tw, _ = text_size(od, speaker, sf)
                od.text((W / 2 - tw / 2, 980 + yo), speaker, font=sf,
                        fill=st["yellow"] + (alpha,),
                        stroke_width=4, stroke_fill=(0, 0, 0, alpha))
                if 7 * (1 - e) > 0.3:
                    ov = ov.filter(ImageFilter.GaussianBlur(radius=7 * (1 - e)))
                img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
        img = draw_typewriter_lines(
            img, [" ".join(l)
                  for l in wrap_words(d, dialog.split(), df, DIALOG_MAX_W)],
            W / 2, 1050, df, st["ink"], f, start=16, cpf=2, stroke=5)
    elif headline:
        words = headline.split()
        lines = wrap_words(d, words, hf, HEADLINE_MAX_W,
                           accent=accent or None)
        _, lh = text_size(d, "Ag", hf)
        line_h = int(lh * 1.18)
        y0 = 1150 - (len(lines) - 1) * line_h // 2
        for li, line in enumerate(lines):
            img = draw_line_stagger(
                img, line, W / 2, y0 + li * line_h, hf, st["ink"], f,
                start0=14, stagger=4, accent=accent or None,
                slam_seed=li * 131 + 7, rise_px=48, blur_max=6.0, dur=14,
                stroke=5)
    if body:
        bf = font(st["font_hero"], 52)
        words = body.split()
        lines = wrap_words(d, words, bf, BODY_MAX_W)
        _, lh = text_size(d, "Ag", bf)
        line_h = int(lh * 1.25)
        y0 = 1470 - (len(lines) - 1) * line_h // 2
        for li, line in enumerate(lines):
            img = draw_line_stagger(
                img, line, W / 2, y0 + li * line_h, bf, st["ink"], f,
                start0=36 + li * 6, stagger=4, accent=None,
                slam_seed=li * 57 + 3, rise_px=90, blur_max=9.0, dur=15,
                stroke=4)
    return img


def audio_dur(path):
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", path],
            capture_output=True, text=True, check=True)
        return float(out.stdout.strip())
    except Exception:
        return 6.0


# ============================================================ scene painters
def paint_s1_bg():
    """Flooded village at night: sky, drowned house silhouettes."""
    img = night_sky(W, H, seed=11)
    d = ImageDraw.Draw(img)
    for i, (x, w, h) in enumerate([(150, 300, 420), (520, 380, 520),
                                   (900, 260, 380)]):
        house_silhouette(d, x, 1080, w, h)
        # faint warm window in one house
        d.rectangle([x - 30, 1080 - h + 120, x + 30, 1080 - h + 200],
                    fill=(200, 130, 60, 120))
    return img


def paint_s2_bg():
    """Open flood water at night: distant rooftops, faint moon glow."""
    img = night_sky(W, H, seed=12)
    d = ImageDraw.Draw(img)
    for x, w in [(120, 260), (480, 320), (850, 240), (1030, 180)]:
        d.polygon([(x - w / 2, 760), (x + w / 2, 760), (x, 640)],
                  fill=(14, 11, 9, 255))
    # faint moon glow
    mg = Image.new("RGBA", img.size, (0, 0, 0, 0))
    dm = ImageDraw.Draw(mg)
    dm.ellipse([830 - 90, 180 - 90, 830 + 90, 180 + 90],
               fill=(210, 205, 190, 60))
    img = Image.alpha_composite(img, mg)
    return img


# ================================================================ scenes
class SceneBase:
    def __init__(self, sc, fps=FPS):
        self.sc = sc
        self.fps = fps
        vo = sc.get("vo")
        self.vo_dur = audio_dur(vo) if vo else 6.0
        hold = int(sc.get("hold_frames", 0))
        self.frames = int(self.vo_dur * fps) + 20 + 35 + hold
        self.rain = Rain(n=170, seed=7 + id(self) % 97)
        self.words = sc.get("headline") or ""
        self.accent = (sc.get("accent_word") or "").strip().upper()
        self.body = sc.get("body") or ""
        self.dialog = sc.get("dialog")
        self.speaker = sc.get("speaker")

    def finish(self, img, f):
        img = overlay_topleft(img, f)
        img = subtitle_block(img, f, self.words, self.accent, self.body,
                             self.dialog, self.speaker)
        img = vignette(img)
        img = add_grain(img, amount=5, seed=f)
        return img.convert("RGB")


class Scene1Flood(SceneBase):
    """Young man wades through the flooded village (walk cycle)."""

    def __init__(self, sc, fps=FPS):
        super().__init__(sc, fps)
        self.bg = paint_s1_bg()
        self.water = Water(y_base=1300, seed=21)
        self.lamp = Lamp(x=880, y_top=620, h=560)
        self.man = Character(unit=560, skin=(196, 138, 96), shirt=(54, 66, 62), pants=(44, 46, 52),
                             hair="short", hair_color=(22, 18, 16), name="pemuda")
        self.rain = Rain(n=200, seed=31)

    def render_frame(self, f):
        t = f / self.fps
        img = self.bg.copy()
        # lamp glow (behind character)
        lamp_pt = self.lamp.draw(img, t, W, H)
        # walking man: left -> right, knee-deep in water
        x = 180 + (880 - 180) * clamp01(t / (self.frames / self.fps))
        self.man.walk(t, stride_freq=1.6)
        self.man.set_expr("worried")
        # occasional look-around
        if 2.0 < t < 3.2:
            self.man.head_turn_to(t - 2.0, dur=0.9, direction=-1.0)
        elif 5.0 < t < 6.2:
            self.man.head_turn_to(t - 5.0, dur=0.9, direction=1.0)
        else:
            self.man.pose["head_turn"] = 0.0
        self.man.pos = (x, 950)
        self.man.draw(img)
        # footstep ripples
        J = self.man.joints()
        ox, oy = self.man.pos
        k = 1.0
        for fk, ph in (("ftL", 0.0), ("ftR", 0.5)):
            fx, fy = ox + J[fk][0] * k, oy + J[fk][1] * k
            if abs(fy - 1300) < 60:
                draw_ripple(img, fx, 1300, t + ph * 0.6, seed=9, max_r=90)
        # water over feet + rain
        self.water.draw(img, t, W, H, lamp_x=lamp_pt[0])
        self.rain.draw(img, t, W, H)
        # lightning flashes (deterministic, 2 strikes)
        for ft0 in (2.2, 5.5):
            dt_ = t - ft0
            if 0 <= dt_ < 0.22:
                a = 90 * math.exp(-dt_ * 18)
                fl = Image.new("RGBA", img.size, (200, 210, 255, int(a)))
                img = Image.alpha_composite(img.convert("RGBA"), fl).convert("RGB")
        return self.finish(img, f)


class Scene2Boat(SceneBase):
    """Rowing the boat: mother sick under blanket, little sibling aboard."""

    def __init__(self, sc, fps=FPS):
        super().__init__(sc, fps)
        self.bg = paint_s2_bg()
        self.water = Water(y_base=1050, seed=22)
        self.boat_cx, self.boat_cy = 540, 1180
        self.man = Character(unit=470, skin=(196, 138, 96), shirt=(54, 66, 62), pants=(44, 46, 52),
                             hair="short", hair_color=(22, 18, 16), name="pemuda")
        self.man.sit()
        self.sib = Character(unit=290, skin=(200, 142, 98), shirt=(42, 62, 108), pants=(52, 52, 68),
                             hair="tuft", hair_color=(22, 18, 16), name="adik")
        self.sib.sit()
        self.rain = Rain(n=120, seed=32)

    def _boat_group(self, t):
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        cx, cy = self.boat_cx, self.boat_cy
        w, h = 600, 160
        x0, x1 = cx - w / 2, cx + w / 2
        d.polygon([(x0, cy - h * 0.55), (x1, cy - h * 0.55),
                   (x1 - w * 0.10, cy + h * 0.45),
                   (x0 + w * 0.10, cy + h * 0.45)],
                  fill=(74, 52, 34, 255))
        d.arc([x0 + w * 0.10, cy + h * 0.05, x1 - w * 0.10, cy + h * 0.85],
              start=0, end=180, fill=(74, 52, 34, 255), width=int(h * 0.5))
        d.line([(x0, cy - h * 0.55), (x1, cy - h * 0.55)],
               fill=(104, 76, 48, 255), width=14, joint="curve")
        # mother lying under blanket (bow, left)
        mx, my = cx - 150, cy - 120
        bw, bh = 300, 120
        breathe = 1 + 0.03 * math.sin(2 * math.pi * 0.28 * t)
        d.rounded_rectangle(
            [(mx - bw / 2, my - bh * breathe / 2),
             (mx + bw / 2, my + bh * breathe / 2)],
            radius=55, fill=(96, 52, 48, 255))
        # mother's head on a small pillow
        hr = 52
        hx, hy = mx - bw / 2 - 30, my - 10
        d.ellipse([hx - hr, hy - hr, hx + hr, hy + hr],
                  fill=(233, 192, 152, 255))
        d.pieslice([hx - hr * 1.02, hy - hr * 1.18, hx + hr * 1.02,
                    hy + hr * 0.42], start=180, end=360,
                   fill=(70, 44, 36, 255))  # headscarf
        d.ellipse([hx - hr * 0.98, hy - hr * 1.02, hx + hr * 0.98,
                   hy + hr * 0.72], fill=(233, 192, 152, 255))
        # tired face (simple)
        d.line([(hx - 18, hy - 8), (hx - 4, hy - 8)], fill=(24, 18, 14, 255),
               width=5)
        d.line([(hx + 4, hy - 8), (hx + 18, hy - 8)], fill=(24, 18, 14, 255),
               width=5)
        d.arc([hx - 14, hy + 2, hx + 14, hy + 26], start=20, end=160,
              fill=(24, 18, 14, 255), width=4)
        # sibling sitting mid-boat
        self.sib.idle_breathe(t, rate=0.32)
        self.sib.set_expr("sad")
        self.sib.draw(lay, pos=(cx + 40, cy - 230), scale=1.0)
        # young man rowing at stern
        stroke = self.man.row(t, freq=0.55)
        self.man.set_expr("determined")
        self.man.draw(lay, pos=(cx + 200, cy - 260), scale=1.0)
        # oar from his hands
        J = self.man.joints()
        piv = (cx + 200 + J["haR"][0], cy - 260 + J["haR"][1])
        oar_ang = 28 + 30 * stroke
        tip = draw_oar(lay, piv, oar_ang, length=380)
        draw_ripple(lay, tip[0], tip[1], t, seed=5, max_r=110)
        return lay

    def render_frame(self, f):
        t = f / self.fps
        img = self.bg.copy()
        self.water.draw(img, t, W, H)
        # bob whole boat group
        bob_y = math.sin(2 * math.pi * t / 2.6) * 13
        bob_r = math.sin(2 * math.pi * t / 3.4 + 1.0) * 2.6
        lay = self._boat_group(t)
        rot = lay.rotate(bob_r, resample=Image.BICUBIC,
                         center=(self.boat_cx, self.boat_cy))
        oy = int(bob_y)
        shifted = Image.new("RGBA", img.size, (0, 0, 0, 0))
        if oy >= 0:
            shifted.alpha_composite(rot.crop((0, 0, W, H - oy)), (0, oy))
        else:
            shifted.alpha_composite(rot.crop((0, -oy, W, H)), (0, 0))
        img = Image.alpha_composite(img.convert("RGBA"), shifted)
        self.rain.draw(img, t, W, H)
        return self.finish(img, f)


class Scene3Roof(SceneBase):
    """Old neighbor on the rooftop calls for help; house door opens."""

    def __init__(self, sc, fps=FPS):
        super().__init__(sc, fps)
        self.bg = night_sky(W, H, seed=13)
        self.water = Water(y_base=1500, seed=23)
        self.house = House(x=640, y_base=1500, w=560, h=620)
        self.gran = Character(unit=430, skin=(188, 130, 90),
                              shirt=(216, 202, 172), pants=(112, 72, 52),
                              hair="bald_old", koko=True,
                              name="tetangga")
        self.kid = Character(unit=250, skin=(204, 146, 100), shirt=(192, 172, 142), pants=(52, 52, 68),
                             hair="tuft", hair_color=(22, 18, 16), name="cucu")
        self.man = Character(unit=400, skin=(196, 138, 96), shirt=(54, 66, 62), pants=(44, 46, 52),
                             hair="short", hair_color=(22, 18, 16), name="pemuda")
        self.rain = Rain(n=150, seed=33)

    def render_frame(self, f):
        t = f / self.fps
        img = self.bg.copy()
        d = ImageDraw.Draw(img)
        # distant silhouettes
        house_silhouette(d, 150, 1500, 300, 420)
        # house with door opening at t=2s
        door_t = clamp01((t - 2.0) / 1.6)
        info = self.house.draw(img, t, door_open=door_t, W=W, H=H)
        # grandmother on the roof apex: raise arm, wave, lower (2.4s loop)
        # NOTE: idle_breathe first — it touches shoulders, arm_raise after.
        self.gran.idle_breathe(t, rate=0.4, amp=0.6)
        wt = t % 2.4
        if wt < 1.5:
            self.gran.arm_raise(wt, dur=1.0, arm="R")
            if wt > 0.7:  # wave the raised hand side to side
                self.gran.pose["head_tilt"] = 8 * math.sin(wt * 9)
        else:
            self.gran.arm_lower(wt - 1.5, dur=0.9, arm="R",
                                start_angle=150.0)
        self.gran.set_expr("panic")
        # feet exactly on roof apex: torso_y = apex - (torso_h/2+thigh+shin)
        self.gran.pos = (info["roof_x"], info["roof_y"] - 266)
        self.gran.draw(img)
        # grandchild on the roof slope: surface drops 190px over 340px run
        slope_drop = 190 * 190 / 340.0
        self.kid.set_expr("sad")
        self.kid.idle_breathe(t + 0.7, rate=0.45, amp=0.7)
        self.kid.pose["shoulder_L"] = 30  # cling toward gran
        self.kid.pos = (info["roof_x"] + 190,
                        info["roof_y"] + slope_drop - 155)
        self.kid.draw(img)
        # young man's boat at left, he looks toward the house
        bx, by = 200, 1560
        d.ellipse([bx - 130, by - 40, bx + 130, by + 40],
                  fill=(60, 42, 28, 255))
        self.man.idle_breathe(t, rate=0.3)
        self.man.set_expr("worried")
        self.man.head_turn_to(min(t, 1.0), dur=0.9, direction=1.0)
        self.man.pos = (bx, by - 260)
        self.man.draw(img)
        self.water.draw(img, t, W, H)
        self.rain.draw(img, t, W, H)
        return self.finish(img, f)


class Scene4Dilemma(SceneBase):
    """Close-up: the young man looks down, then left, then right."""

    def __init__(self, sc, fps=FPS):
        super().__init__(sc, fps)
        self.bg = night_sky(W, H, seed=14)
        self.water = Water(y_base=1560, seed=24)
        self.man = Character(unit=780, skin=(196, 138, 96), shirt=(54, 66, 62), pants=(44, 46, 52),
                             hair="short", hair_color=(22, 18, 16), name="pemuda")
        self.rain = Rain(n=90, seed=34)

    def render_frame(self, f):
        t = f / self.fps
        img = self.bg.copy()
        # faint boat rim at bottom
        d = ImageDraw.Draw(img)
        d.arc([140, 1500, 940, 1900], start=180, end=360,
              fill=(74, 52, 34, 255), width=60)
        m = self.man
        m.idle_breathe(t, rate=0.26, amp=1.2)
        m.set_expr("sad" if t > 2.5 else "worried")
        # head down at 1.5s (dilemma)
        if t > 1.5:
            m.head_down(t - 1.5, dur=1.2, amount=26)
        # look left (family) at 3s, look right (roof) at 5.2s
        if 3.0 < t < 5.2:
            m.head_turn_to(t - 3.0, dur=0.9, direction=-1.0)
        elif t >= 5.2:
            m.head_turn_to(t - 5.2, dur=0.9, direction=1.0)
        # arm drops with settle
        if t > 1.2:
            m.arm_lower(t - 1.2, dur=1.6, arm="R", start_angle=40.0)
        m.pos = (540, 1010)
        m.draw(img)
        self.water.draw(img, t, W, H)
        self.rain.draw(img, t, W, H)
        return self.finish(img, f)


class Scene5Question(SceneBase):
    """Wide shot: small boat on dark water, slow drift, final question."""

    def __init__(self, sc, fps=FPS):
        super().__init__(sc, fps)
        self.bg = night_sky(W, H, seed=15)
        self.water = Water(y_base=1100, seed=25)
        self.man = Character(unit=300, skin=(196, 138, 96), shirt=(54, 66, 62), pants=(44, 46, 52),
                             hair="short", hair_color=(22, 18, 16), name="pemuda")
        self.sib = Character(unit=190, skin=(200, 142, 98), shirt=(42, 62, 108), pants=(52, 52, 68),
                             hair="tuft", hair_color=(22, 18, 16), name="adik")
        self.rain = Rain(n=100, seed=35)

    def render_frame(self, f):
        t = f / self.fps
        img = self.bg.copy()
        self.water.draw(img, t, W, H)
        cx, cy = 540, 1230
        bob_y = math.sin(2 * math.pi * t / 2.6) * 10
        d = ImageDraw.Draw(img)
        w = 420
        d.polygon([(cx - w / 2, cy - 60), (cx + w / 2, cy - 60),
                   (cx + w / 2 - 50, cy + 60), (cx - w / 2 + 50, cy + 60)],
                  fill=(74, 52, 34, 255))
        d.line([(cx - w / 2, cy - 60), (cx + w / 2, cy - 60)],
               fill=(104, 76, 48, 255), width=10)
        self.man.idle_breathe(t, rate=0.28)
        self.man.set_expr("sad")
        self.man.sit()
        self.man.pos = (cx + 60, cy - 190 + bob_y)
        self.man.draw(img)
        self.sib.idle_breathe(t + 0.5, rate=0.34)
        self.sib.set_expr("sad")
        self.sib.sit()
        self.sib.pos = (cx - 90, cy - 160 + bob_y)
        self.sib.draw(img)
        self.rain.draw(img, t, W, H)
        return self.finish(img, f)


BUILDERS = [Scene1Flood, Scene2Boat, Scene3Roof, Scene4Dilemma, Scene5Question]


# ------------------------------------------------------------- assembly
def main():
    proj_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "perahu-project.json")
    with open(proj_path) as fh:
        proj = json.load(fh)
    scenes = proj["scenes"]
    for i, sc in enumerate(scenes):
        sc["anim"] = i
    bed = proj["bed"]
    thump = proj.get("thump",
                     os.path.expanduser("~/workspace/motion-video-projects/"
                                        "serial-psikologis/public/vo/thump.mp3"))
    out = os.path.expanduser("~/workspace/motion-video-projects/engine/"
                             "demos/perahu-terakhir-v2.mp4")
    tmpdir = "/tmp/perahu_v2"
    if os.path.exists(tmpdir):
        shutil.rmtree(tmpdir)
    os.makedirs(tmpdir, exist_ok=True)

    def factory(sc, fps, W_, H_):
        return BUILDERS[sc["anim"]](sc, fps)

    PR.PerahuRenderer = factory
    total_dur, scene_starts = PR.build_project(scenes, bed, thump, out,
                                               tmpdir, fps=FPS, W=W, H=H)
    # manifest for QA
    with open("/tmp/perahu_v2/manifest.json", "w") as fh:
        json.dump({"total_dur": total_dur, "scene_starts": scene_starts,
                   "frames_per_scene": [BUILDERS[i](scenes[i], FPS).frames
                                        for i in range(5)]}, fh)
    print("V2 render done:", out, f"{total_dur:.1f}s")


if __name__ == "__main__":
    main()
