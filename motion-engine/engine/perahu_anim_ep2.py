#!/usr/bin/env python3
"""perahu_anim_ep2.py — PERAHU TERAKHIR Episode 2: KEPUTUSAN.

Direct continuation of Episode 1. The father must choose.

Story (~46s, 5 scenes):
  1. Keputusan — close-up: the father decides (vo1)
  2. Menjemput — boat at the roof; gran hands the grandchild down (vo2)
  3. Penuh — boat full with 4 souls; distant wood cracking (vo3)
  4. Ambruk — the neighbor's roof collapses into the flood (vo4)
  5. Tangan — a hand emerges from the debris; hook for Ep3 (vo5 + vo6)

Visual style: same as Ep1 v4 (dark + warm lamplight, lime/white text black
outline, top-left overlay). Clock advances to 23:47, sublabel EPISODE 2.
Female character (granddaughter) wears kerudung via Character(scarf=...).
"""
import json
import math
import os
import shutil
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import perahu_anim as PA
import perahu_render as PR
from perahu_render import STORY, font, text_size, add_grain
from stick_rig import (Character, Rain, Water, Boat, Lamp, House, draw_oar,
                       draw_ripple, clamp01, expo_out)

FPS = 30
W, H = 1080, 1920
CLOCK = "23:47"
EP_LABEL = "PERAHU TERAKHIR EPISODE 2"

# --- character palettes (same as Ep1 v4) ---
SKIN_BAPAK = (196, 138, 96)
SKIN_ADIK = (200, 142, 98)
SKIN_KAKEK = (188, 130, 90)


def overlay_topleft_ep2(img, f):
    """Red label + digital clock + episode sublabel (Episode 2 identity)."""
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


class Ep2Base:
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
        img = overlay_topleft_ep2(img, f)
        img = PA.subtitle_block(img, f, self.words, self.accent, self.body,
                                self.dialog, self.speaker)
        img = PA.vignette(img)
        img = add_grain(img, amount=5, seed=f)
        return img.convert("RGB")


def make_bapak(unit=780):
    return Character(unit=unit, skin=SKIN_BAPAK, shirt=(54, 66, 62),
                     pants=(44, 46, 52), hair="short",
                     hair_color=(22, 18, 16), name="bapak")


def make_adik(unit=290):
    return Character(unit=unit, skin=SKIN_ADIK, shirt=(42, 62, 108),
                     pants=(52, 52, 68), hair="tuft",
                     hair_color=(22, 18, 16), name="adik")


def make_kakek(unit=430):
    return Character(unit=unit, skin=SKIN_KAKEK, shirt=(216, 202, 172),
                     pants=(112, 72, 52), hair="bald_old", koko=True,
                     name="kakek")


def make_cucu(unit=250):
    """Granddaughter — MUST wear kerudung (scarf)."""
    return Character(unit=unit, skin=(204, 146, 100), shirt=(150, 110, 120),
                     pants=(52, 52, 68), hair="short",
                     hair_color=(22, 18, 16),
                     scarf=(139, 69, 78), name="cucu")


def draw_mother_blanket(d, cx, cy):
    """Mother lying under blanket (bow of boat). Same as Ep1."""
    mx, my = cx, cy
    bw, bh = 300, 120
    d.rounded_rectangle([(mx - bw / 2, my - bh / 2),
                         (mx + bw / 2, my + bh / 2)],
                        radius=55, fill=(96, 52, 48, 255))
    hr = 52
    hx, hy = mx - bw / 2 - 30, my - 10
    d.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=(233, 192, 152, 255))
    d.pieslice([hx - hr * 1.02, hy - hr * 1.18, hx + hr * 1.02, hy + hr * 0.42],
               start=180, end=360, fill=(70, 44, 36, 255))  # headscarf
    d.ellipse([hx - hr * 0.98, hy - hr * 1.02, hx + hr * 0.98, hy + hr * 0.72],
              fill=(233, 192, 152, 255))
    d.line([(hx - 18, hy - 8), (hx - 4, hy - 8)], fill=(24, 18, 14, 255), width=5)
    d.line([(hx + 4, hy - 8), (hx + 18, hy - 8)], fill=(24, 18, 14, 255), width=5)
    d.arc([hx - 14, hy + 2, hx + 14, hy + 26], start=20, end=160,
          fill=(24, 18, 14, 255), width=4)


class Ep2S1Decide(Ep2Base):
    """Close-up: the father looks down, then decides — jaw set."""

    def __init__(self, sc, fps=FPS):
        super().__init__(sc, fps)
        self.bg = PA.night_sky(W, H, seed=14)
        self.water = Water(y_base=1560, seed=24)
        self.man = make_bapak(780)
        self.rain = Rain(n=90, seed=34)

    def render_frame(self, f):
        t = f / self.fps
        img = self.bg.copy()
        d = ImageDraw.Draw(img)
        d.arc([140, 1500, 940, 1900], start=180, end=360,
              fill=(74, 52, 34, 255), width=60)
        m = self.man
        m.idle_breathe(t, rate=0.26, amp=1.2)
        # worried -> head down (weighing) -> determined (decided at ~4.5s)
        m.set_expr("determined" if t > 4.5 else ("sad" if t > 2.0 else "worried"))
        if t > 1.2:
            m.head_down(t - 1.2, dur=1.2, amount=26)
        if 3.0 < t < 4.4:
            m.head_turn_to(t - 3.0, dur=0.9, direction=-1.0)  # toward family
        elif t >= 4.4:
            m.head_turn_to(t - 4.4, dur=0.9, direction=1.0)   # toward roof: DECIDED
        if t > 1.2:
            m.arm_lower(t - 1.2, dur=1.6, arm="R", start_angle=40.0)
        m.pos = (540, 1010)
        m.draw(img)
        self.water.draw(img, t, W, H)
        self.rain.draw(img, t, W, H)
        return self.finish(img, f)


class Ep2S2Rescue(Ep2Base):
    """Boat at the roof; grandfather lowers the granddaughter into the boat."""

    def __init__(self, sc, fps=FPS):
        super().__init__(sc, fps)
        self.bg = PA.night_sky(W, H, seed=13)
        self.water = Water(y_base=1500, seed=23)
        self.house = House(x=640, y_base=1500, w=560, h=620)
        self.gran = make_kakek(430)
        self.kid = make_cucu(250)
        self.man = make_bapak(400)
        self.rain = Rain(n=150, seed=33)

    def render_frame(self, f):
        t = f / self.fps
        img = self.bg.copy()
        d = ImageDraw.Draw(img)
        PA.house_silhouette(d, 150, 1500, 300, 420)
        info = self.house.draw(img, t, door_open=1.0, W=W, H=H)
        # grandfather on roof apex, leaning down, arm extended toward boat
        self.gran.idle_breathe(t, rate=0.4, amp=0.6)
        self.gran.set_expr("sad")
        self.gran.pose["lean"] = -14  # lean toward boat (left)
        self.gran.pose["shoulder_L"] = -70  # left arm reaching down-left
        self.gran.pose["elbow_L"] = 18
        self.gran.pos = (info["roof_x"], info["roof_y"] - 266)
        self.gran.draw(img)
        # granddaughter: starts on roof, lowered into boat over t=2..5s
        kx0, ky0 = info["roof_x"] + 190, info["roof_y"] + 106 - 155
        kx1, ky1 = 330, 1330  # into the boat
        kt = clamp01((t - 2.0) / 3.0)
        ke = kt * kt * (3 - 2 * kt)  # smoothstep
        self.kid.set_expr("sad")
        self.kid.idle_breathe(t + 0.7, rate=0.45, amp=0.7)
        self.kid.pos = (kx0 + (kx1 - kx0) * ke, ky0 + (ky1 - ky0) * ke)
        self.kid.draw(img)
        # father's boat at left; he reaches up to receive her
        bx, by = 200, 1560
        d.ellipse([bx - 130, by - 40, bx + 130, by + 40],
                  fill=(60, 42, 28, 255))
        self.man.idle_breathe(t, rate=0.3)
        self.man.set_expr("determined")
        self.man.pose["shoulder_R"] = -120  # right arm up
        self.man.pose["elbow_R"] = 25
        self.man.head_turn_to(min(t, 1.0), dur=0.9, direction=1.0)
        self.man.pos = (bx, by - 260)
        self.man.draw(img)
        self.water.draw(img, t, W, H)
        self.rain.draw(img, t, W, H)
        return self.finish(img, f)


class Ep2S3Full(Ep2Base):
    """The boat now carries four souls; distant wood cracks."""

    def __init__(self, sc, fps=FPS):
        super().__init__(sc, fps)
        self.bg = PA.paint_s2_bg()
        self.water = Water(y_base=1050, seed=22)
        self.boat_cx, self.boat_cy = 540, 1180
        self.man = make_bapak(470)
        self.man.sit()
        self.sib = make_adik(290)
        self.sib.sit()
        self.kid = make_cucu(230)
        self.kid.sit()
        self.rain = Rain(n=120, seed=32)

    def _boat_group(self, t):
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        cx, cy = self.boat_cx, self.boat_cy
        w, h = 640, 160
        x0, x1 = cx - w / 2, cx + w / 2
        d.polygon([(x0, cy - h * 0.55), (x1, cy - h * 0.55),
                   (x1 - w * 0.10, cy + h * 0.45),
                   (x0 + w * 0.10, cy + h * 0.45)],
                  fill=(74, 52, 34, 255))
        d.arc([x0 + w * 0.10, cy + h * 0.05, x1 - w * 0.10, cy + h * 0.85],
              start=0, end=180, fill=(74, 52, 34, 255), width=int(h * 0.5))
        d.line([(x0, cy - h * 0.55), (x1, cy - h * 0.55)],
               fill=(104, 76, 48, 255), width=14, joint="curve")
        # mother under blanket (bow)
        breathe = 1 + 0.03 * math.sin(2 * math.pi * 0.28 * t)
        mx, my = cx - 190, cy - 120
        bw, bh = 280, int(110 * breathe)
        d.rounded_rectangle([(mx - bw / 2, my - bh / 2),
                             (mx + bw / 2, my + bh / 2)],
                            radius=55, fill=(96, 52, 48, 255))
        hr = 48
        hx, hy = mx - bw / 2 - 28, my - 10
        d.ellipse([hx - hr, hy - hr, hx + hr, hy + hr],
                  fill=(233, 192, 152, 255))
        d.pieslice([hx - hr * 1.02, hy - hr * 1.18, hx + hr * 1.02,
                    hy + hr * 0.42], start=180, end=360,
                   fill=(70, 44, 36, 255))
        d.ellipse([hx - hr * 0.98, hy - hr * 1.02, hx + hr * 0.98,
                   hy + hr * 0.72], fill=(233, 192, 152, 255))
        # sibling mid-boat
        self.sib.idle_breathe(t, rate=0.32)
        self.sib.set_expr("sad")
        self.sib.draw(lay, pos=(cx - 40, cy - 230), scale=1.0)
        # granddaughter (kerudung) beside sibling
        self.kid.idle_breathe(t + 0.4, rate=0.4, amp=0.8)
        self.kid.set_expr("sad")
        self.kid.draw(lay, pos=(cx + 90, cy - 210), scale=1.0)
        # father rowing hard at stern
        stroke = self.man.row(t, freq=0.75)
        self.man.set_expr("determined")
        self.man.draw(lay, pos=(cx + 230, cy - 260), scale=1.0)
        J = self.man.joints()
        piv = (cx + 230 + J["haR"][0], cy - 260 + J["haR"][1])
        oar_ang = 28 + 30 * stroke
        tip = draw_oar(lay, piv, oar_ang, length=380)
        draw_ripple(lay, tip[0], tip[1], t, seed=5, max_r=110)
        return lay

    def render_frame(self, f):
        t = f / self.fps
        img = self.bg.copy()
        self.water.draw(img, t, W, H)
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
        # distant cracking: brief white flashes on horizon at t~5s
        if 5.0 < t < 5.5:
            fl = Image.new("RGBA", img.size, (0, 0, 0, 0))
            fd = ImageDraw.Draw(fl)
            for sx in (700, 830, 950):
                jag = [(sx + int(30 * math.sin(i * 2.1)), 700 - i * 60)
                       for i in range(6)]
                fd.line(jag, fill=(220, 225, 255, 160), width=6)
            img = Image.alpha_composite(img.convert("RGBA"), fl)
        self.rain.draw(img, t, W, H)
        return self.finish(img, f)


class Ep2S4Collapse(Ep2Base):
    """The neighbor's house collapses into the flood."""

    def __init__(self, sc, fps=FPS):
        super().__init__(sc, fps)
        self.bg = PA.night_sky(W, H, seed=16)
        self.water = Water(y_base=1450, seed=26)
        self.rain = Rain(n=180, seed=36)

    def render_frame(self, f):
        t = f / self.fps
        img = self.bg.copy()
        d = ImageDraw.Draw(img)
        PA.house_silhouette(d, 150, 1450, 300, 420)
        # collapsing house: sinks + tilts after t=2s
        ct = clamp01((t - 2.0) / 2.5)
        ce = ct * ct
        hx, hy_base = 640, 1450
        sink = 420 * ce
        tilt = 24 * ce
        # house body (tilted, sinking)
        house_lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        hd = ImageDraw.Draw(house_lay)
        w, h = 560, 620
        hd.rectangle([hx - w / 2, hy_base - h, hx + w / 2, hy_base],
                     fill=(52, 40, 30, 255))
        hd.polygon([(hx - w / 2 - 30, hy_base - h), (hx + w / 2 + 30, hy_base - h),
                    (hx, hy_base - h - 130)], fill=(30, 22, 18, 255))
        # warm window flickers then dies
        if ct < 0.5:
            hd.rectangle([hx - 30, hy_base - h + 120, hx + 30, hy_base - h + 200],
                         fill=(200, 130, 60, int(120 * (1 - ct * 2))))
        rot = house_lay.rotate(tilt, resample=Image.BICUBIC, center=(hx, hy_base))
        shifted = Image.new("RGBA", img.size, (0, 0, 0, 0))
        oy = int(sink)
        if oy < H:
            shifted.alpha_composite(rot.crop((0, 0, W, H - oy)), (0, oy))
        img = Image.alpha_composite(img.convert("RGBA"), shifted)
        # splash rings as it goes down
        if 0 < ct < 1:
            for i, ph in enumerate((0.0, 0.35, 0.7)):
                draw_ripple(img, hx - 100 + i * 110, 1450, t * 1.4 + ph,
                            seed=11 + i, max_r=190)
        # floating debris planks
        for i, (px, pr) in enumerate([(420, 0.5), (700, 1.1), (880, 2.0)]):
            dt2 = clamp01((t - 2.5 - i * 0.4) / 1.5)
            if dt2 > 0:
                py = 1450 + 60 * dt2
                px2 = px + 40 * math.sin(t * 1.3 + pr)
                dd = ImageDraw.Draw(img)
                dd.rounded_rectangle([(px2 - 70, py - 12), (px2 + 70, py + 12)],
                                     radius=6, fill=(96, 70, 46, 255))
        self.water.draw(img, t, W, H)
        self.rain.draw(img, t, W, H)
        return self.finish(img, f)


class Ep2S5Hand(Ep2Base):
    """Wide shot: debris field; a hand emerges from the water."""

    def __init__(self, sc, fps=FPS):
        super().__init__(sc, fps)
        self.bg = PA.night_sky(W, H, seed=17)
        self.water = Water(y_base=1150, seed=27)
        self.man = make_bapak(300)
        self.rain = Rain(n=100, seed=37)

    def _draw_hand(self, img, t):
        """Old man's arm + hand emerging from water among debris."""
        d = ImageDraw.Draw(img)
        hx, hy = 620, 1350
        # debris planks around
        for px, py, wd in [(480, 1380, 130), (760, 1420, 150), (560, 1470, 110)]:
            d.rounded_rectangle([(px - wd / 2, py - 10), (px + wd / 2, py + 10)],
                                radius=6, fill=(80, 58, 38, 255))
        # arm rising from water, slight tremble
        trem = 4 * math.sin(t * 7.0)
        ax0, ay0 = hx, hy + 130
        ax1, ay1 = hx + 12 + trem, hy - 90
        d.line([(ax0, ay0), (ax1, ay1)], fill=(188, 130, 90, 255), width=44,
               joint="curve")
        # open hand
        hx2, hy2 = ax1, ay1
        d.ellipse([hx2 - 34, hy2 - 40, hx2 + 34, hy2 + 24],
                  fill=(188, 130, 90, 255))
        for fi, fa in enumerate((-32, -11, 11, 32)):
            fx = hx2 + fa
            d.line([(fx, hy2 - 30), (fx + fa * 0.15, hy2 - 72)],
                   fill=(188, 130, 90, 255), width=15)
        # ripple rings around the wrist
        draw_ripple(img, hx, hy + 40, t, seed=21, max_r=150)

    def render_frame(self, f):
        t = f / self.fps
        img = self.bg.copy()
        self.water.draw(img, t, W, H)
        # hand appears after 1.5s
        if t > 1.5:
            self._draw_hand(img, t - 1.5)
        # father's boat approaching from the left
        cx, cy = 250 + 120 * clamp01(t / 6.0), 1230
        bob_y = math.sin(2 * math.pi * t / 2.6) * 10
        d = ImageDraw.Draw(img)
        w = 420
        d.polygon([(cx - w / 2, cy - 60), (cx + w / 2, cy - 60),
                   (cx + w / 2 - 50, cy + 60), (cx - w / 2 + 50, cy + 60)],
                  fill=(74, 52, 34, 255))
        d.line([(cx - w / 2, cy - 60), (cx + w / 2, cy - 60)],
               fill=(104, 76, 48, 255), width=10)
        self.man.idle_breathe(t, rate=0.28)
        self.man.set_expr("panic" if t > 2.0 else "worried")
        self.man.sit()
        self.man.row(t, freq=0.9)
        self.man.pos = (cx + 60, cy - 190 + bob_y)
        self.man.draw(img)
        self.rain.draw(img, t, W, H)
        return self.finish(img, f)


BUILDERS = [Ep2S1Decide, Ep2S2Rescue, Ep2S3Full, Ep2S4Collapse, Ep2S5Hand]


def main():
    proj_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "perahu-project-ep2.json")
    with open(proj_path) as fh:
        proj = json.load(fh)
    scenes = proj["scenes"]
    for i, sc in enumerate(scenes):
        sc["anim"] = i
    bed = proj["bed"]
    thump = proj.get("thump")
    out = os.path.expanduser("~/workspace/motion-video-projects/engine/"
                             "demos/perahu-terakhir-ep2-base.mp4")
    tmpdir = os.path.expanduser("~/workspace/motion-video-projects/engine/"
                                "render-frames-ep2")
    # NOTE: no tmpdir wipe — resume-safe rendering skips existing frames
    os.makedirs(tmpdir, exist_ok=True)

    def factory(sc, fps, W_, H_):
        return BUILDERS[sc["anim"]](sc, fps)

    PR.PerahuRenderer = factory
    total_dur, scene_starts = PR.build_project(scenes, bed, thump, out,
                                               tmpdir, fps=FPS, W=W, H=H)
    with open(os.path.join(tmpdir, "manifest.json"), "w") as fh:
        json.dump({"total_dur": total_dur, "scene_starts": scene_starts}, fh)
    print("EP2 base render done:", out, f"{total_dur:.1f}s")
    for i, (sf, ss) in enumerate(scene_starts):
        print(f"  scene{i+1}: start_frame={sf} start_sec={ss:.2f}")


if __name__ == "__main__":
    main()
