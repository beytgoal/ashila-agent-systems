#!/usr/bin/env python3
"""kisahverse_anim_ep1.py — KisahVerse Ep1 "Pergi Demi Iman" (arc Ashabul Kahfi).

Pipeline template "video animasi" (perahu_render/stick_rig pola): animasi
karakter rig frame-by-frame asli (bukan stills/Ken Burns) — perintah owner
30 Okt 2026 18:38 WIB. Karakter: stickman BIRU gaya foto profil v2
@kisahverse.id (kepala bulat biru, mata titik, senyum sederhana), berkostum
era kisah: tunik pasir + ikat pinggang tali + jubah cokelat. Palet teal
malam. Tipografi mengikuti konvensi template (DejaVuSans-Bold, outline
hitam, headline stagger + kata aksen slam, zona aman x=64..1016).

VO: assets/vo-kisahverse-ep1/s1..s5.wav (voice_router auto -> Piper,
kuota ElevenLabs 748 < 1007). Mix: loudnorm VO -16 SEBELUM adelay,
bed -38 + swell + sidechain duck, amix normalize=0, asplit (pola
perahu_render.build_project). Hard cut, tanpa transisi.
"""
import json
import math
import os
import subprocess
import sys
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from motion_render import font, text_size, expo_out, ease_out_back, clamp01, add_grain, _resolve
import perahu_render as pr
from perahu_render import draw_line_stagger, wrap_words, _vignette, _paste_rgba, _eff_widths

FPS = 30
W, H = 1080, 1920
ENGINE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.expanduser("~/workspace/divisi/branding-promosi/kisahverse/produksi-ep1")
TMPDIR = os.path.join(ENGINE, "render-frames-kisahverse-ep1")
BED = os.path.join(ENGINE, "assets/music/Anguish-KevinMacLeod.mp3")
THUMP = os.path.expanduser("~/workspace/motion-video-projects/serial-psikologis/public/vo/thump.mp3")
VO_DIR = os.path.join(ENGINE, "assets/vo-kisahverse-ep1")

# KisahVerse palette (teal malam, aksen emas lentera)
pr.STORY["accent"] = (255, 176, 66)
INK = (245, 242, 235)
INK_DIM = (176, 196, 200)
AMBER = (255, 190, 80)
BLUE = (64, 148, 202)
BLUE_DARK = (46, 116, 168)
TUNIC = (199, 171, 121)
TUNIC_DARK = (172, 144, 98)
BELT = (122, 84, 44)
CLOAK = (109, 77, 45)
ROYAL = (96, 48, 104)
ROYAL_DARK = (72, 34, 82)
GOLD = (232, 178, 60)


def clamp(x, a, b):
    return max(a, min(b, x))


# ------------------------------------------------------------ glow sprite
_GLOW_CACHE = {}


def glow_sprite(color, r, power=2.2):
    key = (color, r, power)
    if key in _GLOW_CACHE:
        return _GLOW_CACHE[key]
    yy, xx = np.mgrid[0:2 * r, 0:2 * r]
    dist = np.sqrt((xx - r) ** 2 + (yy - r) ** 2) / r
    a = np.clip(1 - dist, 0, 1) ** power
    sp = np.zeros((2 * r, 2 * r, 4), dtype=np.uint8)
    sp[..., 0], sp[..., 1], sp[..., 2] = color
    sp[..., 3] = (a * 255).astype(np.uint8)
    img = Image.fromarray(sp, "RGBA")
    _GLOW_CACHE[key] = img
    return img


def paste_glow(base, color, cx, cy, r, alpha=0.8, power=2.2):
    sp = glow_sprite(color, r, power)
    if alpha < 0.99:
        a = sp.split()[3].point(lambda v: int(v * alpha))
        sp = sp.copy()
        sp.putalpha(a)
    base.alpha_composite(sp, (int(cx - r), int(cy - r)))


def flick(t, ph=0.0):
    return 0.86 + 0.10 * math.sin(t * 11.0 + ph) + 0.04 * math.sin(t * 43.0 + ph * 1.7)


def draw_flame(base, cx, cy, s, t, ph=0.0):
    """Small animated flame: stacked ellipses with flicker scale + glow."""
    fl = flick(t, ph)
    paste_glow(base, (255, 150, 50), cx, cy, int(2.4 * s * fl), alpha=0.35 * fl)
    d = ImageDraw.Draw(base)
    # lidah api bentuk tetesan (bukan elips bulat): lebar ramping, ujung
    # runcing bergoyang — s = tinggi api nominal
    for k, (wr, hr, col) in enumerate([(0.20, 1.00, (232, 106, 30)),
                                       (0.13, 0.70, (248, 160, 52)),
                                       (0.065, 0.44, (255, 214, 120))]):
        w2 = wr * s * (1 + 0.08 * math.sin(t * 13 + ph + k))
        h2 = hr * s * fl
        sway = 0.06 * s * math.sin(t * 7 + ph + k * 0.8)
        base_y = cy + 0.16 * s
        d.polygon([(cx - w2, base_y), (cx - w2 * 0.45, cy - h2 * 0.25),
                   (cx + sway, cy - h2), (cx + w2 * 0.45, cy - h2 * 0.25),
                   (cx + w2, base_y), (cx, base_y + 0.07 * s)],
                  fill=col + (255,))


# ==================================================================== rig
class KVRig:
    """Stickman biru gaya profil v2: kepala bulat biru + mata titik +
    senyum, tungkai kapsul tipis biru, tunik era + ikat tali + jubah.
    Pose = fungsi deterministik t. Angle deg: 0 = ke bawah, + ke +x."""

    def __init__(self, unit=560, royal=False, back=False, dark=False,
                 mouth="smile", tunic=TUNIC, cloak=CLOAK):
        self.u = float(unit)
        self.royal = royal
        self.back = back
        self.mouth = mouth
        self.body = (38, 66, 92) if dark else BLUE
        self.body_d = (26, 48, 70) if dark else BLUE_DARK
        self.tunic = ROYAL if royal else tunic
        self.tunic_d = ROYAL_DARK if royal else TUNIC_DARK
        self.cloak_c = (58, 30, 66) if royal else cloak
        self.pose = {"shL": 8, "shR": -8, "elL": 10, "elR": 10,
                     "hipL": 3, "hipR": -3, "kneeL": 5, "kneeR": 5,
                     "lean": 0.0, "bob": 0.0, "head_up": 0.0}
        self.lantern = False
        self.bundle = False
        self.spear = False
        self.helmet = False

    def _dir(self, deg):
        a = math.radians(deg)
        return (math.sin(a), math.cos(a))

    def joints(self):
        u = self.u
        p = self.pose
        bob = p["bob"]
        neck = (0.0, -0.735 * u + bob)
        shL = (-0.105 * u, -0.705 * u + bob)
        shR = (0.105 * u, -0.705 * u + bob)
        hipL = (-0.058 * u, -0.315 * u + bob)
        hipR = (0.058 * u, -0.315 * u + bob)
        d = self._dir
        elL = (shL[0] + d(p["shL"])[0] * 0.155 * u, shL[1] + d(p["shL"])[1] * 0.155 * u)
        elR = (shR[0] + d(p["shR"])[0] * 0.155 * u, shR[1] + d(p["shR"])[1] * 0.155 * u)
        haL = (elL[0] + d(p["shL"] + p["elL"])[0] * 0.145 * u,
               elL[1] + d(p["shL"] + p["elL"])[1] * 0.145 * u)
        haR = (elR[0] + d(p["shR"] + p["elR"])[0] * 0.145 * u,
               elR[1] + d(p["shR"] + p["elR"])[1] * 0.145 * u)
        knL = (hipL[0] + d(p["hipL"])[0] * 0.165 * u, hipL[1] + d(p["hipL"])[1] * 0.165 * u)
        knR = (hipR[0] + d(p["hipR"])[0] * 0.165 * u, hipR[1] + d(p["hipR"])[1] * 0.165 * u)
        ftL = (knL[0] + d(p["hipL"] + p["kneeL"])[0] * 0.155 * u,
               knL[1] + d(p["hipL"] + p["kneeL"])[1] * 0.155 * u)
        ftR = (knR[0] + d(p["hipR"] + p["kneeR"])[0] * 0.155 * u,
               knR[1] + d(p["hipR"] + p["kneeR"])[1] * 0.155 * u)
        head = (0.0, -0.735 * u + bob - 0.135 * u + p["head_up"])
        return {"neck": neck, "shL": shL, "shR": shR, "elL": elL, "elR": elR,
                "haL": haL, "haR": haR, "hipL": hipL, "hipR": hipR,
                "knL": knL, "knR": knR, "ftL": ftL, "ftR": ftR, "head": head}

    # -- animation verbs --------------------------------------------------
    def idle(self, t, amp=1.0):
        s = math.sin(2 * math.pi * 0.26 * t)
        self.pose["bob"] = -abs(s) * self.u * 0.006 * amp
        self.pose["shL"] = 8 + s * 2.2 * amp
        self.pose["shR"] = -8 - s * 2.2 * amp
        self.pose["lean"] = s * 1.2

    def walk(self, t, freq=1.6, swing=30.0, arm_swing=24.0, phase=0.0):
        p = 2 * math.pi * freq * t + phase
        self.pose["hipL"] = swing * math.sin(p)
        self.pose["hipR"] = swing * math.sin(p + math.pi)
        self.pose["kneeL"] = 6 + 40 * max(0.0, math.sin(p - 2.1))
        self.pose["kneeR"] = 6 + 40 * max(0.0, math.sin(p + math.pi - 2.1))
        self.pose["shL"] = -arm_swing * math.sin(p) + 5
        self.pose["shR"] = -arm_swing * math.sin(p + math.pi) + 5
        self.pose["elL"] = 12 + 9 * math.sin(p)
        self.pose["elR"] = 12 + 9 * math.sin(p + math.pi)
        self.pose["bob"] = -abs(math.sin(p)) * self.u * 0.020
        self.pose["lean"] = 5.0

    def run(self, t, phase=0.0):
        self.walk(t, freq=2.3, swing=44.0, arm_swing=38.0, phase=phase)
        self.pose["lean"] = 11.0
        self.pose["elL"] = 55
        self.pose["elR"] = 55

    # -- drawing ------------------------------------------------------------
    def _capsule(self, d, p1, p2, w, color):
        d.line([p1, p2], fill=color, width=max(int(w), 3), joint="curve")
        r = w / 2.0
        for p in (p1, p2):
            d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=color)

    def draw(self, base, pos, flip=False):
        """pos = titik tanah (ground) karakter di frame utama."""
        u = self.u
        J = self.joints()
        lw = 0.030 * u            # tungkai tipis gaya stickman
        aw = 0.028 * u
        # layer lokal: x -0.62u..0.62u, y -1.12u..0.06u
        lw_px, lh_px = int(1.30 * u), int(1.22 * u)
        ox, oy = 0.65 * u, 1.14 * u   # origin (ground) di dalam layer
        layer = Image.new("RGBA", (lw_px, lh_px), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        P = {k: (v[0] + ox, v[1] + oy) for k, v in J.items()}

        def S(pt):
            return pt

        # jubah belakang (sisi kiri tubuh)
        cloak_poly = [S((P["shL"][0] - 0.03 * u, P["shL"][1])),
                      S((P["neck"][0] - 0.02 * u, P["neck"][1] + 0.01 * u)),
                      S((P["hipL"][0] - 0.16 * u, -0.06 * u + oy)),
                      S((P["hipL"][0] - 0.02 * u, -0.30 * u + oy))]
        d.polygon(cloak_poly, fill=self.cloak_c + (255,))
        # tungkai belakang + lengan belakang
        self._capsule(d, P["hipL"], P["knL"], lw, self.body_d)
        self._capsule(d, P["knL"], P["ftL"], lw * 0.92, self.body_d)
        self._capsule(d, P["shL"], P["elL"], aw, self.body_d)
        self._capsule(d, P["elL"], P["haL"], aw * 0.9, self.body_d)
        # tunik: A-line ramping dari bahu ke hem di atas lutut (gaya profil
        # v2) + bahu membulat; BUKAN kotak lebar — figur harus terpisah.
        top_y = P["shL"][1] - 0.012 * u
        hem_y = -0.190 * u + oy + self.pose["bob"]
        robe = [S((ox - 0.118 * u, top_y)),
                S((ox + 0.118 * u, top_y)),
                S((ox + 0.178 * u, hem_y)),
                S((ox - 0.178 * u, hem_y))]
        robe_col = self.cloak_c if self.back else self.tunic
        d.polygon(robe, fill=robe_col + (255,))
        d.ellipse([ox - 0.118 * u, top_y - 0.045 * u, ox + 0.118 * u,
                   top_y + 0.055 * u], fill=robe_col + (255,))
        # shading sisi kanan tunik
        if not self.back:
            d.polygon([robe[1], robe[2],
                       (robe[2][0] - 0.045 * u, robe[2][1]),
                       (robe[1][0] - 0.020 * u, robe[1][1] + 0.04 * u)],
                      fill=self.tunic_d + (110,))
            # jubah cokelat tersampir di bahu kiri, menjuntai diagonal
            d.polygon([(ox - 0.118 * u, top_y + 0.01 * u),
                       (ox - 0.052 * u, top_y - 0.005 * u),
                       (ox - 0.108 * u, hem_y - 0.01 * u),
                       (ox - 0.172 * u, hem_y + 0.015 * u)],
                      fill=self.cloak_c + (255,))
            # ikat pinggang tali + simpul + dua ujung menjuntai
            by = -0.475 * u + oy + self.pose["bob"]
            d.line([(ox - 0.148 * u, by), (ox + 0.148 * u, by)],
                   fill=BELT + (255,), width=max(int(0.020 * u), 4))
            kx = ox + 0.038 * u
            d.ellipse([kx - 0.016 * u, by - 0.016 * u, kx + 0.016 * u, by + 0.016 * u],
                      fill=BELT + (255,))
            d.line([(kx - 0.008 * u, by + 0.01 * u), (kx - 0.02 * u, by + 0.085 * u)],
                   fill=BELT + (255,), width=max(int(0.011 * u), 3))
            d.line([(kx + 0.010 * u, by + 0.01 * u), (kx + 0.026 * u, by + 0.075 * u)],
                   fill=BELT + (255,), width=max(int(0.011 * u), 3))
        # tungkai depan (di bawah hem)
        self._capsule(d, P["hipR"], P["knR"], lw, self.body)
        self._capsule(d, P["knR"], P["ftR"], lw * 0.92, self.body)
        # kaki: elips kecil gaya profil
        for fk in ("ftL", "ftR"):
            fx, fy = P[fk]
            d.ellipse([fx - 0.026 * u, fy - 0.012 * u, fx + 0.034 * u, fy + 0.010 * u],
                      fill=self.body + (255,))
        # lengan depan
        self._capsule(d, P["shR"], P["elR"], aw, self.body)
        self._capsule(d, P["elR"], P["haR"], aw * 0.9, self.body)
        # tangan: cakram biru
        hr = aw * 0.62
        for hk in ("haL", "haR"):
            hx, hy = P[hk]
            d.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=self.body + (255,))
        # kepala
        hc = P["head"]
        r = 0.135 * u
        d.ellipse([hc[0] - r, hc[1] - r, hc[0] + r, hc[1] + r], fill=self.body + (255,))
        # shading bulan sabit kanan-bawah (lembut, gaya 3D-look)
        sh = Image.new("RGBA", layer.size, (0, 0, 0, 0))
        ds = ImageDraw.Draw(sh)
        ds.ellipse([hc[0] - r, hc[1] - r, hc[0] + r, hc[1] + r], fill=(10, 40, 70, 60))
        ds.ellipse([hc[0] - r * 1.18, hc[1] - r * 1.34, hc[0] + r * 0.80, hc[1] + r * 0.66],
                   fill=(0, 0, 0, 0))
        layer.alpha_composite(sh)
        d = ImageDraw.Draw(layer)
        if self.helmet:
            # helm penjaga: band baja gelap di atas kepala + tepian
            d.pieslice([hc[0] - r * 1.02, hc[1] - r * 1.06,
                        hc[0] + r * 1.02, hc[1] + r * 0.30],
                       start=180, end=360, fill=(52, 58, 66, 255))
            d.rectangle([hc[0] - r * 1.06, hc[1] - r * 0.16,
                         hc[0] + r * 1.06, hc[1] - r * 0.02],
                        fill=(40, 45, 52, 255))
        if self.royal:
            # mahkota emas di atas kepala
            cw = r * 1.15
            cy0 = hc[1] - r * 1.02
            d.polygon([(hc[0] - cw, cy0), (hc[0] - cw, cy0 - r * 0.34),
                       (hc[0] - cw * 0.5, cy0 - r * 0.10),
                       (hc[0], cy0 - r * 0.44), (hc[0] + cw * 0.5, cy0 - r * 0.10),
                       (hc[0] + cw, cy0 - r * 0.34), (hc[0] + cw, cy0)],
                      fill=GOLD + (255,))
            d.rectangle([hc[0] - cw, cy0 - r * 0.06, hc[0] + cw, cy0 + r * 0.05],
                        fill=(198, 148, 44, 255))
        if not self.back:
            # wajah minimal profil v2: mata titik + mulut sederhana
            dk = (16, 26, 34, 255)
            for s in (-1, 1):
                ex = hc[0] + s * r * 0.36
                ey = hc[1] - r * 0.06
                d.ellipse([ex - r * 0.085, ey - r * 0.085, ex + r * 0.085, ey + r * 0.085],
                          fill=dk)
            mw = r * 0.34
            my = hc[1] + r * 0.30
            if self.mouth == "smile":
                d.arc([hc[0] - mw, my - r * 0.20, hc[0] + mw, my + r * 0.22],
                      start=15, end=165, fill=dk, width=max(int(r * 0.07), 3))
            elif self.mouth == "flat":
                d.line([(hc[0] - mw * 0.8, my + r * 0.06), (hc[0] + mw * 0.8, my + r * 0.06)],
                       fill=dk, width=max(int(r * 0.07), 3))
            elif self.mouth == "o":
                d.ellipse([hc[0] - r * 0.10, my - r * 0.02, hc[0] + r * 0.10, my + r * 0.20],
                          fill=dk)
        # tombak (penjaga/pengejar)
        if self.spear:
            hx, hy = P["haR"]
            top = (hx + 0.10 * u, hy - 1.04 * u)
            d.line([(hx, hy + 0.10 * u), top], fill=(90, 70, 48, 255),
                   width=max(int(0.019 * u), 3))
            d.polygon([(top[0] - 0.020 * u, top[1] + 0.07 * u),
                       (top[0] + 0.020 * u, top[1] + 0.07 * u),
                       (top[0], top[1] - 0.05 * u)], fill=(168, 178, 188, 255))
        # bungkusan bekal di punggung (s4)
        if self.bundle:
            bx, by2 = P["shL"][0] - 0.16 * u, P["shL"][1] - 0.10 * u
            d.line([P["haL"], (bx, by2)], fill=(90, 70, 48, 255),
                   width=max(int(0.012 * u), 3))
            d.ellipse([bx - 0.075 * u, by2 - 0.075 * u, bx + 0.075 * u, by2 + 0.075 * u],
                      fill=(150, 120, 88, 255))
            d.ellipse([bx - 0.030 * u, by2 - 0.030 * u, bx + 0.030 * u, by2 + 0.030 * u],
                      fill=(128, 100, 72, 255))
        if flip:
            layer = layer.transpose(Image.FLIP_LEFT_RIGHT)
            lx = pos[0] - (lw_px - ox) if False else pos[0] - (lw_px - (lw_px - ox))
            # posisi tempel: origin layer di (pos - ox) — setelah flip, origin
            # berada di lw_px-ox dari kiri layer
            px = int(pos[0] - (lw_px - ox))
        else:
            px = int(pos[0] - ox)
        py = int(pos[1] - oy)
        base.alpha_composite(layer, (px, py))
        # posisi tangan kanan di koordinat frame (untuk lentera)
        hx, hy = P["haR"]
        if flip:
            hx = lw_px - hx
        return (px + hx, py + hy)


# ------------------------------------------------------------ environments
def sky(top=(6, 30, 43), bot=(9, 44, 58)):
    key = ("sky", top, bot)
    if key in _GLOW_CACHE:
        return _GLOW_CACHE[key].copy()
    g = np.zeros((H, 1, 3), dtype=np.uint8)
    for c in range(3):
        g[:, 0, c] = np.linspace(top[c], bot[c], H)
    img = Image.fromarray(np.repeat(g, W, axis=1), "RGB").convert("RGBA")
    _GLOW_CACHE[key] = img
    return img.copy()


def draw_stars(base, t, seed=5, n=90, ymax=900):
    rng = np.random.default_rng(seed)
    xs = rng.uniform(0, W, n)
    ys = rng.uniform(0, ymax, n)
    rs = rng.uniform(1.0, 2.6, n)
    ph = rng.uniform(0, 6.28, n)
    ov = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for i in range(n):
        a = int(90 + 80 * (0.5 + 0.5 * math.sin(t * 1.7 + ph[i])))
        d.ellipse([xs[i] - rs[i], ys[i] - rs[i], xs[i] + rs[i], ys[i] + rs[i]],
                  fill=(220, 235, 240, a))
    base.alpha_composite(ov)


def draw_moon(base, cx=880, cy=215, r=58):
    paste_glow(base, (200, 220, 230), cx, cy, r * 3, alpha=0.20)
    d = ImageDraw.Draw(base)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(226, 233, 226, 255))
    d.ellipse([cx - r * 0.45, cy - r * 0.3, cx - r * 0.1, cy + r * 0.05],
              fill=(206, 216, 208, 255))
    d.ellipse([cx + r * 0.25, cy + r * 0.3, cx + r * 0.5, cy + r * 0.55],
              fill=(206, 216, 208, 255))


def ground_band(base, y=1330, col=(6, 24, 33)):
    d = ImageDraw.Draw(base)
    d.rectangle([0, y, W, H], fill=col + (255,))
    d.line([(0, y), (W, y)], fill=(30, 80, 96, 255), width=3)
    rng = np.random.default_rng(11)
    for _ in range(260):
        x = rng.uniform(0, W)
        yy = rng.uniform(y + 12, H - 6)
        d.point((x, yy), fill=(16, 44, 56, 255))


def draw_dust(base, t, seed=9, n=26, col=(205, 190, 155)):
    rng = np.random.default_rng(seed)
    x0 = rng.uniform(0, W, n)
    y0 = rng.uniform(1050, 1420, n)
    vx = rng.uniform(14, 44, n)
    ph = rng.uniform(0, 6.28, n)
    ov = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for i in range(n):
        x = (x0[i] + vx[i] * t) % (W + 40) - 20
        y = y0[i] + 12 * math.sin(t * 0.9 + ph[i])
        d.ellipse([x - 3, y - 2, x + 3, y + 2], fill=col + (70,))
    base.alpha_composite(ov)


def draw_lantern(base, hx, hy, t, s=1.0):
    """Lentera emas tergantung di tangan: cahaya berdenyut + badan lampu."""
    fl = flick(t, 2.0)
    cx, cy = hx, hy + 62 * s
    paste_glow(base, (255, 176, 80), cx, cy, int(210 * s * fl), alpha=0.5 * fl)
    paste_glow(base, (255, 205, 110), cx, cy, int(95 * s), alpha=0.55)
    d = ImageDraw.Draw(base)
    d.line([(hx, hy), (cx, cy - 34 * s)], fill=(150, 116, 52, 255),
           width=max(int(5 * s), 2))
    d.rounded_rectangle([cx - 21 * s, cy - 34 * s, cx + 21 * s, cy + 30 * s],
                        radius=int(8 * s), fill=(146, 104, 40, 255))
    d.rounded_rectangle([cx - 14 * s, cy - 24 * s, cx + 14 * s, cy + 20 * s],
                        radius=int(6 * s), fill=(255, 196, 96, 255))
    d.ellipse([cx - 6 * s, cy - 12 * s, cx + 6 * s, cy + 10 * s],
              fill=(255, 236, 180, 255))
    d.rectangle([cx - 10 * s, cy - 42 * s, cx + 10 * s, cy - 34 * s],
                fill=(120, 86, 32, 255))


def draw_torch(base, x, y, t, ph=0.0, s=1.0):
    d = ImageDraw.Draw(base)
    d.line([(x, y), (x, y + 120 * s)], fill=(52, 38, 26, 255), width=max(int(9 * s), 3))
    d.polygon([(x - 13 * s, y), (x + 13 * s, y), (x + 8 * s, y + 22 * s),
               (x - 8 * s, y + 22 * s)], fill=(70, 52, 34, 255))
    draw_flame(base, x, y - 16 * s, 58 * s, t, ph)


_BG_CACHE = {}


def bg_city_idols():
    if "city" in _BG_CACHE:
        return _BG_CACHE["city"].copy()
    img = sky()
    d = ImageDraw.Draw(img)
    sil = (15, 56, 70, 255)
    sil2 = (18, 66, 84, 255)
    # skyline rumah kuno bertingkat
    rng = np.random.default_rng(4)
    x = -20
    while x < W + 20:
        bw = rng.uniform(120, 210)
        bh = rng.uniform(180, 330)
        d.rectangle([x, 1330 - bh, x + bw, 1330], fill=sil2)
        if rng.random() < 0.5:
            d.polygon([(x + bw * 0.2, 1330 - bh), (x + bw * 0.8, 1330 - bh),
                       (x + bw * 0.5, 1330 - bh - 52)], fill=sil2)
        # jendela hangat kecil
        for _ in range(3):
            wx = x + rng.uniform(14, bw - 30)
            wy = 1330 - bh + rng.uniform(30, bh - 60)
            d.rectangle([wx, wy, wx + 10, wy + 14], fill=(255, 176, 92, 165))
        x += bw + rng.uniform(6, 26)
    # kuil + panggung berhala (kiri-tengah)
    d.rectangle([70, 1030, 520, 1086], fill=sil)
    d.rectangle([100, 974, 490, 1030], fill=sil)
    d.rectangle([135, 918, 455, 974], fill=sil)
    for sx, ss in [(205, 1.0), (330, 1.18), (445, 0.92)]:
        # patung batu: alas + badan + kepala
        d.rectangle([sx - 30 * ss, 872, sx + 30 * ss, 918], fill=(70, 84, 94, 255))
        d.rounded_rectangle([sx - 24 * ss, 872 - 92 * ss, sx + 24 * ss, 872],
                            radius=int(16 * ss), fill=(84, 100, 112, 255))
        d.ellipse([sx - 20 * ss, 872 - 148 * ss, sx + 20 * ss, 872 - 108 * ss],
                  fill=(84, 100, 112, 255))
        d.rectangle([sx - 40 * ss, 872 - 78 * ss, sx - 26 * ss, 872 - 20 * ss],
                    fill=(74, 90, 102, 255))
        d.rectangle([sx + 26 * ss, 872 - 78 * ss, sx + 40 * ss, 872 - 20 * ss],
                    fill=(74, 90, 102, 255))
    ground_band(img, 1330)
    _BG_CACHE["city"] = img
    return img.copy()


def bg_palace():
    if "palace" in _BG_CACHE:
        return _BG_CACHE["palace"].copy()
    img = sky(top=(10, 26, 34), bot=(26, 44, 48))
    d = ImageDraw.Draw(img)
    # dinding belakang + kolom
    d.rectangle([0, 300, W, 1330], fill=(16, 34, 40, 255))
    for cx in (90, 330, 750, 990):
        d.rectangle([cx - 46, 300, cx + 46, 1330], fill=(22, 48, 56, 255))
        d.rectangle([cx - 62, 282, cx + 62, 318], fill=(28, 58, 66, 255))
        d.rectangle([cx - 62, 1296, cx + 62, 1330], fill=(28, 58, 66, 255))
    # karpet tengah
    d.polygon([(300, 1330), (780, 1330), (700, 1060), (380, 1060)],
              fill=(52, 30, 44, 255))
    # panggung singgasana (kanan)
    d.rectangle([700, 1224, 1050, 1330], fill=(30, 56, 64, 255))
    d.rectangle([724, 1118, 1026, 1224], fill=(36, 64, 72, 255))
    d.rectangle([748, 1012, 1002, 1118], fill=(42, 72, 80, 255))
    # singgasana: sandaran tinggi di atas panggung
    d.rounded_rectangle([806, 560, 950, 1012], radius=26, fill=(64, 36, 74, 255))
    d.rounded_rectangle([824, 584, 932, 900], radius=20, fill=(84, 48, 94, 255))
    d.ellipse([856, 520, 900, 564], fill=GOLD + (255,))
    ground_band(img, 1330, col=(8, 22, 28))
    _BG_CACHE["palace"] = img
    return img.copy()


def bg_gate():
    if "gate" in _BG_CACHE:
        return _BG_CACHE["gate"].copy()
    img = sky()
    d = ImageDraw.Draw(img)
    sil = (17, 60, 76, 255)
    # tembok kota + gerbang lengkung (kiri)
    d.rectangle([-20, 760, 430, 1330], fill=sil)
    d.rectangle([-20, 724, 430, 776], fill=(21, 70, 88, 255))
    for bx in range(0, 430, 58):
        d.rectangle([bx, 700, bx + 40, 726], fill=(21, 70, 88, 255))
    # lubang gerbang (langit malam terlihat)
    d.pieslice([120, 880, 330, 1150], start=180, end=360, fill=(7, 34, 48, 255))
    d.rectangle([120, 1015, 330, 1330], fill=(7, 34, 48, 255))
    d.rectangle([96, 1330 - 470, 120, 1330], fill=sil)
    d.rectangle([330, 1330 - 470, 354, 1330], fill=sil)
    # rumah-rumah di luar tembok (kanan jauh)
    for hx, hw, hh in [(700, 170, 150), (880, 210, 190), (1010, 150, 120)]:
        d.rectangle([hx, 1330 - hh, hx + hw, 1330], fill=(18, 64, 80, 255))
        d.polygon([(hx - 12, 1330 - hh), (hx + hw + 12, 1330 - hh),
                   (hx + hw / 2, 1330 - hh - 44)], fill=(18, 64, 80, 255))
        d.rectangle([hx + hw * 0.4, 1330 - hh + 42, hx + hw * 0.4 + 16,
                     1330 - hh + 66], fill=(255, 176, 92, 190))
    # pegunungan jauh
    d.polygon([(430, 1330), (700, 1090), (880, 1330)], fill=(8, 32, 44, 255))
    d.polygon([(760, 1330), (990, 1150), (1100, 1330)], fill=(8, 32, 44, 255))
    ground_band(img, 1330)
    _BG_CACHE["gate"] = img
    return img.copy()


def bg_mountain():
    if "mount" in _BG_CACHE:
        return _BG_CACHE["mount"].copy()
    img = sky(top=(6, 28, 42), bot=(11, 52, 68))
    d = ImageDraw.Draw(img)
    # gunung gelap besar (kanan)
    d.polygon([(430, 1330), (790, 700), (1120, 1330)], fill=(7, 26, 37, 255))
    d.polygon([(790, 700), (880, 840), (820, 880), (760, 800)], fill=(16, 46, 58, 255))
    # bukit kiri jauh
    d.polygon([(-40, 1330), (240, 1090), (480, 1330)], fill=(9, 36, 48, 255))
    ground_band(img, 1330, col=(5, 20, 29))
    _BG_CACHE["mount"] = img
    return img.copy()


# ------------------------------------------------------------ scene builders
GROUND = 1330


def _lerp(a, b, k):
    return a + (b - a) * k


def scene1(t, dur):
    img = bg_city_idols()
    draw_stars(img, t, seed=5, n=70, ymax=700)
    # api sesaji di depan berhala + obor dinding
    for bx, ph in [(150, 0.0), (470, 1.3)]:
        d = ImageDraw.Draw(img)
        d.polygon([(bx - 26, 1086), (bx + 26, 1086), (bx + 14, 1058), (bx - 14, 1058)],
                  fill=(60, 46, 32, 255))
        draw_flame(img, bx, 1040, 80, t, ph)
    draw_torch(img, 655, 962, t, 0.7)
    draw_torch(img, 958, 902, t, 2.1)
    # pencerita: masuk berjalan, berhenti, mengangkat lentera
    st = KVRig(unit=580, mouth="smile")
    walk_dur = 3.2
    if t < walk_dur:
        k = expo_out(clamp01(t / walk_dur))
        x = _lerp(1210, 735, k)
        st.walk(t, freq=1.7)
        raise_k = 0.0
    else:
        x = 735
        raise_k = expo_out(clamp01((t - walk_dur) / 1.3))
        st.idle(t)
        # kaki diam (idle) — walk pose diluruhkan oleh idle di atas;
        # lengan kanan naik memegang lentera
        st.pose["shR"] = _lerp(st.pose["shR"], 146, raise_k)
        st.pose["elR"] = _lerp(st.pose["elR"], 10, raise_k)
        st.pose["shL"] = _lerp(st.pose["shL"], 14, raise_k)
    hand = st.draw(img, (x, GROUND))
    draw_lantern(img, hand[0], hand[1], t, s=1.0)
    draw_dust(img, t)
    return img


def _youths_row(img, t, xs, arms_up_from=None, mouth="flat", step_back=0.0):
    """Barisan pemuda: jumlah figur dibuat tumpang-tindih samar (bukan
    klaim jumlah pasti — catatan doktrinal 1)."""
    units = [452, 428, 466, 438, 416]
    grounds = [GROUND, GROUND + 16, GROUND + 2, GROUND + 20, GROUND + 30]
    for i, x0 in enumerate(xs):
        y = KVRig(unit=units[i % len(units)], mouth=mouth)
        y.idle(t + i * 0.37)
        if arms_up_from is not None:
            k = ease_out_back(clamp01((t - arms_up_from - i * 0.22) / 1.1))
            k = clamp(k, 0.0, 1.0)
            y.pose["shL"] = _lerp(y.pose["shL"], -112, k)
            y.pose["shR"] = _lerp(y.pose["shR"], 112, k)
            y.pose["elL"] = _lerp(y.pose["elL"], -8, k)
            y.pose["elR"] = _lerp(y.pose["elR"], 8, k)
            y.pose["head_up"] = -5 * k
        y.draw(img, (x0 - step_back, grounds[i % len(grounds)]))


def _king(img, t, point_from=None):
    kg = KVRig(unit=472, royal=True, mouth="flat")
    kg.idle(t, amp=0.6)
    if point_from is not None:
        k = expo_out(clamp01((t - point_from) / 0.8))
        kg.pose["shR"] = _lerp(kg.pose["shR"], 97, k)
        kg.pose["elR"] = _lerp(kg.pose["elR"], 2, k)
    kg.draw(img, (878, 1012), flip=True)
    return kg


def _braziers(img, t):
    for bx, ph in [(150, 0.4), (648, 1.9)]:
        d = ImageDraw.Draw(img)
        d.polygon([(bx - 24, 1330), (bx + 24, 1330), (bx + 12, 1290), (bx - 12, 1290)],
                  fill=(56, 42, 30, 255))
        d.line([(bx, 1290), (bx, 1330)], fill=(56, 42, 30, 255), width=8)
        draw_flame(img, bx, 1272, 74, t, ph)


def scene2(t, dur):
    img = bg_palace()
    _braziers(img, t)
    _king(img, t)
    _youths_row(img, t, [148, 270, 392, 510, 618], arms_up_from=0.5)
    return img


def scene3(t, dur):
    img = bg_palace()
    _braziers(img, t)
    _king(img, t, point_from=0.9)
    back = 26 * expo_out(clamp01((t - 3.4) / 0.8))
    _youths_row(img, t, [272, 382, 488, 590, 672], mouth="flat", step_back=back)
    # penjaga bertombak merangsek dari dua sisi — digambar DI DEPAN barisan,
    # dibedakan helm baja + tunik lebih gelap
    guards = [(36, 138, False), (120, 216, False), (788, 756, True), (862, 824, True)]
    for i, (gx0, gx1, flip) in enumerate(guards):
        g = KVRig(unit=458, mouth="flat", tunic=(92, 78, 62), cloak=(44, 38, 32))
        g.spear = True
        g.helmet = True
        mv = clamp01((t - 1.2 - i * 0.15) / 2.4)
        gx = _lerp(gx0, gx1, expo_out(mv))
        if mv < 1.0:
            g.walk(t, freq=1.8, phase=i * 1.3)
        else:
            g.idle(t + i)
            g.pose["shR"] = 24
        g.draw(img, (gx, GROUND + 6), flip=flip)
    return img


def scene4(t, dur):
    img = bg_gate()
    draw_stars(img, t, seed=8, n=80, ymax=760)
    draw_moon(img)
    draw_torch(img, 104, 838, t, 0.5)
    draw_torch(img, 352, 838, t, 1.6)
    trav = 470 * (0.5 - 0.5 * math.cos(math.pi * clamp01(t / dur)))
    units = [458, 434, 470, 442, 420]
    for i in range(5):
        y = KVRig(unit=units[i], mouth="flat")
        if i in (1, 3):
            y.bundle = True
        y.walk(t, freq=1.7, phase=i * 1.7)
        x = 84 + i * 118 + trav
        y.draw(img, (x, GROUND + (i % 3) * 10))
    draw_dust(img, t, seed=13)
    return img


def scene5(t, dur):
    img = bg_mountain()
    draw_stars(img, t, seed=3, n=85, ymax=720)
    # pengejar di kejauhan: siluet gelap berlari + obor, makin mendekat
    for i, (px0, px1, ph) in enumerate([(-90, 196, 0.0), (-170, 118, 1.1), (-40, 268, 2.2)]):
        k = clamp01(t / dur)
        px = _lerp(px0, px1, k)
        sc = _lerp(0.56, 0.68, k)
        p = KVRig(unit=560 * sc, dark=True, mouth="flat",
                  tunic=(30, 48, 62), cloak=(24, 40, 54))
        p.run(t, phase=ph)
        p.draw(img, (px, GROUND))
        if i in (0, 2):
            draw_torch(img, px + 66 * sc + 18, GROUND - 400 * sc, t, ph, s=sc)
    # para pemuda dari belakang, bergegas ke gunung gelap
    units = [446, 420, 452, 428]
    gnds = [GROUND, GROUND + 24, GROUND + 6, GROUND + 28]
    for i, x0 in enumerate([540, 680, 812, 936]):
        y = KVRig(unit=units[i], back=True, mouth="flat")
        y.walk(t, freq=2.0, swing=36, arm_swing=20, phase=i * 1.9)
        x = x0 + 44 * clamp01(t / dur)
        y.draw(img, (x, gnds[i]))
        # debu di kaki
        d = ImageDraw.Draw(img)
        for k2 in range(2):
            ph2 = (t * 1.4 + i * 0.7 + k2 * 0.5) % 1.0
            r = 12 + ph2 * 30
            d.ellipse([x - 30 - ph2 * 36 - r, GROUND - 8 - r * 0.3,
                       x - 30 - ph2 * 36 + r, GROUND - 8 + r * 0.3],
                      fill=(180, 168, 140, int(52 * (1 - ph2))))
    draw_dust(img, t, seed=21)
    return img


BUILDERS = [scene1, scene2, scene3, scene4, scene5]

SCENES = [
    {"kicker": "001 — PEMBUKA KISAHVERSE", "headline": "KOTA PENUH@@NL@@BERHALA",
     "body": "RAJA ZALIM · SEMUA HARUS TUNDUK", "accent": "BERHALA",
     "camera": "punch-in", "vo": "s1.wav", "hold": 0},
    {"kicker": "002 — PEMUDA BERIMAN", "headline": "TAUHID DI@@NL@@HADAPAN RAJA",
     "body": "KAMI TIDAK MENYEMBAH SELAIN DIA", "accent": "TAUHID",
     "camera": "drift", "vo": "s2.wav", "hold": 0},
    {"kicker": "003 — MENOLAK ITU BAHAYA", "headline": "MENOLAK =@@NL@@BAHAYA",
     "body": "DIPAKSA KEMBALI · ATAU DIHUKUM", "accent": "BAHAYA",
     "camera": "punch-in", "vo": "s3.wav", "hold": 0},
    {"kicker": "004 — PILIHAN YANG BERAT", "headline": "MALAM ITU@@NL@@MEREKA PERGI",
     "body": "MENINGGALKAN RUMAH · DEMI IMAN", "accent": "PERGI",
     "camera": "drift", "vo": "s4.wav", "hold": 0},
    {"kicker": "005 — PENGEJAR MENDEKAT", "headline": "LANGKAH PENGEJAR@@NL@@MENDEKAT",
     "body": "GUNUNG GELAP DI DEPAN MEREKA", "accent": "PENGEJAR",
     "camera": "punch-out", "vo": "s5.wav", "hold": 75},
]


# ------------------------------------------------------------ text + camera
def _camera(img, kind, t01):
    if kind == "punch-in":
        scale = 1.07 - 0.07 * expo_out(t01)
    elif kind == "punch-out":
        scale = 1.0 + 0.07 * expo_out(t01)
    elif kind == "drift":
        scale = 1.05
    else:
        return img
    nw, nh = int(W * scale), int(H * scale)
    im2 = img.resize((nw, nh), Image.LANCZOS)
    x = (im2.width - W) // 2
    y = (im2.height - H) // 2
    if kind == "drift":
        x = int(x + 26 * t01)
        y = int(y - 14 * t01)
    return im2.crop((x, y, x + W, y + H))


def _headline_font(lines_words, accent):
    dummy = Image.new("RGB", (10, 10))
    d = ImageDraw.Draw(dummy)
    for size in (100, 92, 84, 76, 68):
        hf = font("DejaVuSans-Bold", size)
        space_w, _ = text_size(d, " ", hf)
        ok = True
        for words in lines_words:
            effs = _eff_widths(d, words, hf, accent or None)
            if sum(effs) + space_w * (len(words) - 1) > 840:
                ok = False
                break
        if ok:
            return hf
    return font("DejaVuSans-Bold", 68)


def render_scene_frame(si, f, nframes):
    sc = SCENES[si]
    t = f / FPS
    dur = nframes / FPS
    img = BUILDERS[si](t, dur)
    img = _camera(img, sc["camera"], clamp01(f / max(nframes - 1, 1)))
    img = img.convert("RGB")
    img = _vignette(img, 0.30)
    # kicker (atas, tengah) — masuk rise+deblur
    kf = font("DejaVuSansMono-Bold", 36)
    img = pr.draw_word(img, sc["kicker"], W / 2, 92, kf, AMBER, f, 6,
                       rise_px=30, blur_max=6.0, dur=14, stroke=3)
    # headline: hormati @@NL@@ sebagai patahan baris
    lines_words = [ln.split() for ln in sc["headline"].split("@@NL@@")]
    hf = _headline_font(lines_words, sc["accent"])
    d = ImageDraw.Draw(img)
    _, lh = text_size(d, "Ag", hf)
    line_h = int(lh * 1.18)
    y0 = 1150 - (len(lines_words) - 1) * line_h // 2
    for li, words in enumerate(lines_words):
        img = draw_line_stagger(img, words, W / 2, y0 + li * line_h, hf, INK, f,
                                start0=14 + li * 2, stagger=4,
                                accent=sc["accent"] or None,
                                slam_seed=li * 131 + 7, rise_px=48,
                                blur_max=6.0, dur=14, stroke=5)
    # body
    bf = font("DejaVuSans-Bold", 52)
    blines = wrap_words(d, sc["body"].split(), bf, 840)
    _, lh2 = text_size(d, "Ag", bf)
    line_h2 = int(lh2 * 1.25)
    y02 = 1470 - (len(blines) - 1) * line_h2 // 2
    for li, line in enumerate(blines):
        img = draw_line_stagger(img, line, W / 2, y02 + li * line_h2, bf, INK, f,
                                start0=36 + li * 6, stagger=4, accent=None,
                                slam_seed=li * 57 + 3, rise_px=90,
                                blur_max=9.0, dur=15, stroke=4)
    img = add_grain(img, amount=5, seed=f)
    return img


def _vo_dur(path):
    """Durasi VO robust: ffprobe dulu; bila gagal/0 (subprocess bisa gagal
    saat VM sibuk), fallback baca header WAV via modul wave (tanpa
    subprocess). Mengembalikan 0 hanya bila file benar-benar tak terbaca."""
    d = pr._audio_dur(path)
    if d and d > 0:
        return d
    try:
        import wave
        with wave.open(path, "rb") as w:
            return w.getnframes() / float(w.getframerate())
    except Exception:
        return 0.0


def scene_frame_count(si):
    vo = os.path.join(VO_DIR, SCENES[si]["vo"])
    d = _vo_dur(vo)
    if d <= 0:
        raise RuntimeError(f"durasi VO tak terbaca: {vo}")
    return int(d * FPS) + 55 + SCENES[si]["hold"]


# ------------------------------------------------------------ assembly
def assemble(out_mp4):
    os.makedirs(TMPDIR, exist_ok=True)
    os.makedirs(OUTDIR, exist_ok=True)
    frame_idx = 0
    audio_inputs = []
    thump_frames = []
    scene_starts = []
    t = 0.0
    for si, sc in enumerate(SCENES):
        n = scene_frame_count(si)
        scene_starts.append((frame_idx, t))
        if sc.get("vo"):
            audio_inputs.append((os.path.join(VO_DIR, sc["vo"]), t))
        words = sc["headline"].replace("@@NL@@", " ").split()
        try:
            hero_i = [w.strip(".,!?").upper() for w in words].index(sc["accent"])
        except ValueError:
            hero_i = 0
        thump_frames.append(frame_idx + 14 + hero_i * 4 + 9)
        for f in range(n):
            fp = f"{TMPDIR}/f{frame_idx:06d}.jpg"
            if not os.path.exists(fp):
                img = render_scene_frame(si, f, n)
                # lapisan FS sandbox kadang menolak write() proses exec
                # secara terputus-putus (EPERM) — tunggu sampai jendela
                # blokir lewat (maks ~15 menit per frame)
                for attempt in range(90):
                    try:
                        img.save(fp, quality=88)
                        break
                    except PermissionError:
                        if attempt == 89:
                            raise
                        time.sleep(10)
            frame_idx += 1
            if frame_idx % 300 == 0:
                print(f"  frames: {frame_idx}", flush=True)
        t += n / FPS
    total_dur = frame_idx / FPS
    cmd = ["ffmpeg", "-y"]
    idx = 0
    vo_labels = []
    for path, start in audio_inputs:
        cmd += ["-i", path]
        ms = int(start * 1000)
        vo_labels.append(f"[{idx}:a]loudnorm=I=-16:TP=-1.0:LRA=11,adelay={ms}|{ms}[v{idx + 1}]")
        idx += 1
    thump_labels = []
    for fr in thump_frames:
        cmd += ["-i", THUMP]
        ms = int(fr / FPS * 1000)
        thump_labels.append(f"[{idx}:a]adelay={ms}|{ms},volume=0.25[th{idx}]")
        idx += 1
    cmd += ["-stream_loop", "-1", "-i", BED]
    bidx = idx
    idx += 1
    t5 = scene_starts[4][1]
    swell_inner = (f"if(lt(t,{t5:.2f}),1,"
                   f"if(lt(t,{t5 + 4:.2f}),1+0.25*(t-{t5:.2f}),"
                   f"if(lt(t,{total_dur - 3:.2f}),2,"
                   f"2*max(0,1-(t-({total_dur - 3:.2f}))/3))))")
    swell = f"if(isnan(t),1,{swell_inner})"
    bed_chain = (f"[{bidx}:a]atrim=0:{total_dur:.2f},loudnorm=I=-38:TP=-2:LRA=11,"
                 f"volume='{swell}'[bedn]")
    vomix_in = "".join(f"[v{i}]" for i in range(1, len(vo_labels) + 1))
    vomix = (f"{vomix_in}amix=inputs={len(vo_labels)}:normalize=0,"
             f"apad=whole_dur={total_dur:.2f},asplit=2[vomix1][vomix2]")
    duck = ("[bedn][vomix1]sidechaincompress=threshold=0.04:ratio=6:"
            "attack=400:release=1200[bed]")
    all_labels = (["[vomix2]"]
                  + [f"[th{i}]" for i in range(len(vo_labels), len(vo_labels) + len(thump_labels))]
                  + ["[bed]"])
    parts = vo_labels + thump_labels + [bed_chain, vomix, duck]
    parts.append(f"{''.join(all_labels)}amix=inputs={len(all_labels)}:"
                 f"duration=longest:normalize=0,atrim=0:{total_dur:.2f},"
                 f"alimiter=limit=0.9:attack=5:release=50[aout]")
    vidx = idx
    cmd += ["-framerate", str(FPS), "-i", f"{TMPDIR}/f%06d.jpg"]
    cmd += ["-filter_complex", ";".join(parts), "-map", f"{vidx}:v", "-map", "[aout]",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
            "-preset", "veryfast",
            "-c:a", "aac", "-shortest", out_mp4]
    print("assembling", frame_idx, "frames,", f"{total_dur:.1f}s ...", flush=True)
    subprocess.run(cmd, check=True)
    print("done:", out_mp4)
    return total_dur, scene_starts


def probe():
    pdir = os.path.join(OUTDIR, "probe")
    os.makedirs(pdir, exist_ok=True)
    for si in range(5):
        n = scene_frame_count(si)
        for f in (8, n // 2, n - 8):
            img = render_scene_frame(si, f, n)
            img.save(os.path.join(pdir, f"s{si + 1}_f{f:04d}.jpg"), quality=88)
            print("probe", si + 1, f, "of", n, flush=True)


if __name__ == "__main__":
    if "--probe" in sys.argv:
        probe()
    else:
        out = os.path.join(OUTDIR, "kisahverse-ep1-pergi-demi-iman.mp4")
        dur, starts = assemble(out)
        print(json.dumps({"out": out, "duration": dur,
                          "scene_starts": starts}, indent=1))
