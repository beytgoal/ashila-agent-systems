#!/usr/bin/env python3
"""stick_rig.py — reusable 2D CARICATURE character rig (PIL, frame-by-frame).

Caricature style (per user correction 2026-10-23 12:00 WIB):
- BIG round head with detailed expressive face (eyes, brows, mouth)
- ROUNDED FILLED torso (berisi), NOT thin stick lines
- THICK cartoon arms & legs drawn as capsules (limb = thick rounded segment
  + joint discs), articulated at shoulder/elbow/hip/knee
- Cartoon proportions: big head + filled body, lucu-dramatis

All motion is a deterministic function of time t (seconds). No randomness
except seeded particle systems. Angles in degrees; 0 deg = pointing DOWN,
positive = toward +x (character's left on screen).

Animation principles (skill motion-video §4):
- expo easing (never linear), anticipation before big moves,
  overshoot + settle, staggered entrances.
"""

import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter


# ------------------------------------------------------------ easing helpers
def clamp01(x):
    return max(0.0, min(1.0, x))


def expo_out(t):
    t = clamp01(t)
    return 1.0 if t >= 1.0 else 1.0 - pow(2.0, -10.0 * t)


def expo_in_out(t):
    t = clamp01(t)
    if t <= 0.0:
        return 0.0
    if t >= 1.0:
        return 1.0
    if t < 0.5:
        return pow(2.0, 20.0 * t - 10.0) / 2.0
    return (2.0 - pow(2.0, -20.0 * t + 10.0)) / 2.0


def ease_out_back(t, s=1.70158):
    t = clamp01(t)
    return 1.0 + (s + 1.0) * pow(t - 1.0, 3.0) + s * pow(t - 1.0, 2.0)


def smooth(t):
    """smoothstep — for gentle idle loops."""
    t = clamp01(t)
    return t * t * (3.0 - 2.0 * t)


def anticipation_rise(t, a_dur=0.18, dip=0.12):
    """Dip DOWN first (anticipation), then rise with expo-out + overshoot.

    Returns 0..~1.06 (overshoots past 1, caller should settle).
    t: 0..1 normalized over the whole move.
    """
    t = clamp01(t)
    if t < a_dur:
        return -dip * math.sin(math.pi * t / a_dur)
    u = (t - a_dur) / (1.0 - a_dur)
    return ease_out_back(u)


def blit_rot(dst_rgba, src_rgba, center, angle_deg):
    """Paste src (RGBA) onto dst (RGBA) rotated about its own center."""
    rot = src_rgba.rotate(angle_deg, expand=True, resample=Image.BICUBIC)
    x = int(center[0] - rot.width / 2)
    y = int(center[1] - rot.height / 2)
    dst_rgba.alpha_composite(rot, (x, y))


# ================================================================= Character
class Character:
    """Caricature rig: big head + filled rounded torso + thick capsule limbs."""

    def __init__(self, unit=520,
                 skin=(198, 140, 98), shirt=(44, 96, 88), pants=(40, 42, 56),
                 hair="short", hair_color=(22, 18, 16),
                 scarf=None, koko=False, name=""):
        self.unit = float(unit)
        u = self.unit
        # --- caricature proportions
        self.head_r = 0.150 * u
        self.torso_w = 0.300 * u
        self.torso_h = 0.400 * u
        self.upper = 0.200 * u
        self.fore = 0.185 * u
        self.thigh = 0.215 * u
        self.shin = 0.205 * u
        self.arm_w = 0.088 * u      # thick cartoon limbs
        self.leg_w = 0.098 * u
        self.skin = skin
        self.shirt = shirt
        self.pants = pants
        self.hair = hair
        self.hair_color = hair_color
        self.scarf = scarf          # color tuple or None
        self.koko = koko          # True: draw koko-shirt collar + buttons
        self.name = name
        # --- pose state (degrees). 0 = limb pointing down.
        self.pose = {
            "shoulder_L": 8, "shoulder_R": -8,
            "elbow_L": 12, "elbow_R": 12,
            "hip_L": 4, "hip_R": -4,
            "knee_L": 6, "knee_R": 6,
            "head_tilt": 0.0,      # deg, + = tilt toward +x
            "head_nod": 0.0,       # deg, + = nod down
            "head_turn": 0.0,      # -1..1 face shift
            "lean": 0.0,           # torso lean deg (+ = toward +x)
            "bob": 0.0,            # vertical px offset
        }
        self.expr = "neutral"      # neutral|sad|worried|panic|determined|tired
        self.pos = (540.0, 960.0)  # torso center in px
        self.look = (0.0, 0.0)     # pupil offset (-1..1)

    # ------------------------------------------------------------- FK solver
    def _dir(self, deg):
        a = math.radians(deg)
        return (math.sin(a), math.cos(a))

    def _rot(self, pt, deg):
        a = math.radians(deg)
        c, s = math.cos(a), math.sin(a)
        return (pt[0] * c - pt[1] * s, pt[0] * s + pt[1] * c)

    def joints(self):
        """Return dict of joint pixel positions in character-local space."""
        p = self.pose
        u = self.unit
        lean = p["lean"]
        cx, cy = 0.0, p["bob"]  # local origin = torso center
        neck = (cx + self._rot((0, -self.torso_h / 2), lean)[0],
                cy + self._rot((0, -self.torso_h / 2), lean)[1])
        sh_off = self._rot((-self.torso_w * 0.34, -self.torso_h / 2 + 0.05 * u), lean)
        sh_off_r = self._rot((self.torso_w * 0.34, -self.torso_h / 2 + 0.05 * u), lean)
        shL = (cx + sh_off[0], cy + sh_off[1])
        shR = (cx + sh_off_r[0], cy + sh_off_r[1])
        la = p["shoulder_L"] + lean * 0.4
        ra = p["shoulder_R"] + lean * 0.4
        d = self._dir
        elL = (shL[0] + d(la)[0] * self.upper, shL[1] + d(la)[1] * self.upper)
        elR = (shR[0] + d(ra)[0] * self.upper, shR[1] + d(ra)[1] * self.upper)
        haL = (elL[0] + d(la + p["elbow_L"])[0] * self.fore,
               elL[1] + d(la + p["elbow_L"])[1] * self.fore)
        haR = (elR[0] + d(ra + p["elbow_R"])[0] * self.fore,
               elR[1] + d(ra + p["elbow_R"])[1] * self.fore)
        hip_off = self._rot((-0.105 * u, self.torso_h / 2 - 0.015 * u), lean)
        hip_off_r = self._rot((0.105 * u, self.torso_h / 2 - 0.015 * u), lean)
        hipL = (cx + hip_off[0], cy + hip_off[1])
        hipR = (cx + hip_off_r[0], cy + hip_off_r[1])
        knL = (hipL[0] + d(p["hip_L"])[0] * self.thigh,
               hipL[1] + d(p["hip_L"])[1] * self.thigh)
        knR = (hipR[0] + d(p["hip_R"])[0] * self.thigh,
               hipR[1] + d(p["hip_R"])[1] * self.thigh)
        ftL = (knL[0] + d(p["hip_L"] + p["knee_L"])[0] * self.shin,
               knL[1] + d(p["hip_L"] + p["knee_L"])[1] * self.shin)
        ftR = (knR[0] + d(p["hip_R"] + p["knee_R"])[0] * self.shin,
               knR[1] + d(p["hip_R"] + p["knee_R"])[1] * self.shin)
        # head center: above neck, with tilt/nod/turn
        hx = neck[0] + math.sin(math.radians(p["head_tilt"])) * self.head_r * 0.9 \
            + p["head_turn"] * self.head_r * 0.28
        hy = neck[1] - math.cos(math.radians(p["head_tilt"])) * self.head_r * 1.02 \
            + p["head_nod"] * 0.35
        return {"neck": neck, "shL": shL, "shR": shR, "elL": elL, "elR": elR,
                "haL": haL, "haR": haR, "hipL": hipL, "hipR": hipR,
                "knL": knL, "knR": knR, "ftL": ftL, "ftR": ftR,
                "head": (hx, hy), "origin": (cx, cy)}

    # ------------------------------------------------------------- drawing
    def _capsule(self, draw, p1, p2, w, color):
        """Thick cartoon limb segment with round caps + joint discs."""
        p1 = (float(p1[0]), float(p1[1]))
        p2 = (float(p2[0]), float(p2[1]))
        wi = max(int(w), 3)
        draw.line([p1, p2], fill=color, width=wi, joint="curve")
        r = w / 2.0
        for p in (p1, p2):
            draw.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=color)

    def _draw_head(self, layer, hc):
        """Big round head + hair/scarf + expressive face. layer is RGBA."""
        r = self.head_r
        d = ImageDraw.Draw(layer)
        # long back-hair mass (drawn BEHIND the head ball)
        if self.hair == "long":
            d.ellipse([hc[0] - r * 1.18, hc[1] - r * 1.22,
                       hc[0] + r * 1.18, hc[1] + r * 2.05],
                      fill=self.hair_color + (255,))
        # head ball
        d.ellipse([hc[0] - r, hc[1] - r, hc[0] + r, hc[1] + r],
                  fill=self.skin + (255,))
        # subtle shading: darker crescent bottom-right
        sh = Image.new("RGBA", layer.size, (0, 0, 0, 0))
        ds = ImageDraw.Draw(sh)
        ds.ellipse([hc[0] - r, hc[1] - r, hc[0] + r, hc[1] + r],
                   fill=(120, 70, 50, 70))
        ds.ellipse([hc[0] - r * 1.15, hc[1] - r * 1.30,
                    hc[0] + r * 0.85, hc[1] + r * 0.70],
                   fill=(0, 0, 0, 0))
        # hair / scarf
        if self.scarf:
            d.ellipse([hc[0] - r * 1.12, hc[1] - r * 1.28,
                       hc[0] + r * 1.12, hc[1] + r * 0.55],
                      fill=self.scarf + (255,))
            d.ellipse([hc[0] - r * 0.98, hc[1] - r * 1.02,
                       hc[0] + r * 0.98, hc[1] + r * 0.72],
                      fill=self.skin + (255,))  # face opening
            # scarf tail
            d.polygon([(hc[0] + r * 0.7, hc[1] + r * 0.4),
                       (hc[0] + r * 1.25, hc[1] + r * 1.5),
                       (hc[0] + r * 0.35, hc[1] + r * 1.1)],
                      fill=self.scarf + (255,))
        elif self.hair == "short":
            d.pieslice([hc[0] - r * 1.02, hc[1] - r * 1.18,
                        hc[0] + r * 1.02, hc[1] + r * 0.42],
                       start=180, end=360, fill=self.hair_color + (255,))
            # natural hairline: small side triangles
            for s in (-1, 1):
                d.polygon([(hc[0] + s * r * 1.00, hc[1] - r * 0.35),
                           (hc[0] + s * r * 0.82, hc[1] - r * 0.30),
                           (hc[0] + s * r * 0.95, hc[1] + r * 0.05)],
                          fill=self.hair_color + (255,))
        elif self.hair == "long":
            # top cap + side falls framing the face
            d.pieslice([hc[0] - r * 1.04, hc[1] - r * 1.20,
                        hc[0] + r * 1.04, hc[1] + r * 0.44],
                       start=180, end=360, fill=self.hair_color + (255,))
            for s in (-1, 1):
                d.ellipse([hc[0] + s * r * 0.86 - r * 0.22,
                           hc[1] - r * 0.55,
                           hc[0] + s * r * 0.86 + r * 0.22,
                           hc[1] + r * 1.55],
                          fill=self.hair_color + (255,))
        elif self.hair == "tuft":
            d.pieslice([hc[0] - r * 1.02, hc[1] - r * 1.18,
                        hc[0] + r * 1.02, hc[1] + r * 0.42],
                       start=180, end=360, fill=self.hair_color + (255,))
            for sx in (-0.45, 0.0, 0.45):
                d.polygon([(hc[0] + sx * r - r * 0.10, hc[1] - r * 0.95),
                           (hc[0] + sx * r + r * 0.10, hc[1] - r * 0.95),
                           (hc[0] + sx * r, hc[1] - r * 1.45)],
                          fill=self.hair_color + (255,))
        elif self.hair == "bald_old":
            # few side wisps for the old neighbor
            d.arc([hc[0] - r * 1.0, hc[1] - r * 1.0,
                   hc[0] + r * 1.0, hc[1] + r * 1.0],
                  start=200, end=250, fill=(200, 200, 200, 255), width=6)
        self._draw_face(d, hc, r)

    def _draw_face(self, d, hc, r):
        ex, ey = hc
        turn = self.pose["head_turn"]
        lx, ly = self.look
        e = self.expr
        dark = (24, 18, 14, 255)
        white = (245, 242, 235, 255)
        # --- eyes
        eye_dx, eye_dy = r * 0.36 + turn * r * 0.10, -r * 0.08
        eye_w, eye_h = r * 0.30, r * 0.34
        pupil_r = r * 0.10
        for s in (-1, 1):
            cx = ex + s * eye_dx + lx * r * 0.06
            cy = ey + eye_dy + ly * r * 0.05
            if e == "panic":
                d.ellipse([cx - eye_w * 0.62, cy - eye_h * 0.62,
                           cx + eye_w * 0.62, cy + eye_h * 0.62], fill=white)
                d.ellipse([cx - pupil_r * 0.7, cy - pupil_r * 0.7,
                           cx + pupil_r * 0.7, cy + pupil_r * 0.7], fill=dark)
            elif e == "tired":
                # half-lidded: dark line + small pupil
                d.line([(cx - eye_w / 2, cy), (cx + eye_w / 2, cy)],
                       fill=dark, width=max(int(r * 0.07), 3))
                d.ellipse([cx - pupil_r * 0.6, cy - pupil_r * 0.2,
                           cx + pupil_r * 0.6, cy + pupil_r * 1.0], fill=dark)
            else:
                d.ellipse([cx - eye_w / 2, cy - eye_h / 2,
                           cx + eye_w / 2, cy + eye_h / 2], fill=white)
                d.ellipse([cx - pupil_r + lx * r * 0.05,
                           cy - pupil_r + ly * r * 0.05,
                           cx + pupil_r + lx * r * 0.05,
                           cy + pupil_r + ly * r * 0.05], fill=dark)
        # --- eye highlights (avatar catchlight)
        hl_r = max(int(r * 0.035), 2)
        for s in (-1, 1):
            cx = ex + s * eye_dx + lx * r * 0.06
            cy = ey + eye_dy + ly * r * 0.05
            if e not in ("tired",):
                px = cx + lx * r * 0.05 - pupil_r * 0.35
                py = cy + ly * r * 0.05 - pupil_r * 0.35
                d.ellipse([px - hl_r, py - hl_r, px + hl_r, py + hl_r],
                          fill=(255, 255, 255, 230))
        # --- nose (small shadow line)
        nx = ex + turn * r * 0.06
        d.line([(nx, ey + r * 0.10), (nx - r * 0.03, ey + r * 0.30)],
               fill=(140, 85, 55, 180), width=max(int(r * 0.045), 2))
        # --- cheek blush / warmth
        for s in (-1, 1):
            d.ellipse([ex + s * r * 0.62 - r * 0.16, ey + r * 0.22,
                       ex + s * r * 0.62 + r * 0.16, ey + r * 0.48],
                      fill=(190, 90, 70, 55))
        # --- brows (thick, expression-driven)
        bw, bh = r * 0.42, r * 0.09
        by = ey - r * 0.52
        for s in (-1, 1):
            cx = ex + s * (eye_dx + r * 0.02)
            if e == "sad":
                # inner ends up: \ /
                x0, y0 = cx - s * bw / 2, by - r * 0.10
                x1, y1 = cx + s * bw / 2, by + r * 0.10
            elif e == "worried":
                x0, y0 = cx - s * bw / 2, by - r * 0.06
                x1, y1 = cx + s * bw / 2, by + r * 0.12
            elif e == "panic":
                x0, y0 = cx - s * bw / 2, by - r * 0.22
                x1, y1 = cx + s * bw / 2, by - r * 0.18
            elif e == "determined":
                # inner ends down: / \
                x0, y0 = cx - s * bw / 2, by + r * 0.08
                x1, y1 = cx + s * bw / 2, by - r * 0.10
            else:
                x0, y0 = cx - bw / 2, by
                x1, y1 = cx + bw / 2, by
            d.line([(x0, y0), (x1, y1)], fill=(30, 22, 18, 255),
                   width=max(int(bh), 4), joint="curve")
        # --- mouth
        mx, my = ex + turn * r * 0.08, ey + r * 0.52
        mw = r * 0.44
        if e == "sad":
            d.arc([mx - mw / 2, my - r * 0.30, mx + mw / 2, my + r * 0.22],
                  start=200, end=340, fill=dark, width=max(int(r * 0.07), 3))
        elif e == "worried":
            d.line([(mx - mw / 2, my + r * 0.04), (mx + mw / 2, my - r * 0.02)],
                   fill=dark, width=max(int(r * 0.07), 3), joint="curve")
        elif e == "panic":
            d.ellipse([mx - mw * 0.28, my - r * 0.20,
                       mx + mw * 0.28, my + r * 0.20], fill=(58, 20, 16, 255))
        elif e == "determined":
            d.line([(mx - mw / 2, my), (mx + mw / 2, my)],
                   fill=dark, width=max(int(r * 0.08), 4))
        elif e == "tired":
            d.arc([mx - mw / 2, my - r * 0.18, mx + mw / 2, my + r * 0.30],
                  start=20, end=160, fill=dark, width=max(int(r * 0.06), 3))
        else:
            d.line([(mx - mw * 0.32, my), (mx + mw * 0.32, my)],
                   fill=dark, width=max(int(r * 0.06), 3), joint="curve")

    def draw(self, base_rgba, pos=None, scale=1.0):
        """Draw full character onto base_rgba (RGBA). pos = torso center px."""
        if pos is None:
            pos = self.pos
        u = self.unit * scale
        k = u / self.unit  # scale factor for joint offsets
        J = self.joints()
        ox, oy = pos
        P = {kk: (ox + vv[0] * k, oy + vv[1] * k) for kk, vv in J.items()}
        layer = Image.new("RGBA", base_rgba.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        aw, lw = self.arm_w * k, self.leg_w * k
        # back limbs (L)
        self._capsule(d, P["hipL"], P["knL"], lw, self.pants)
        self._capsule(d, P["knL"], P["ftL"], lw * 0.92, self.pants)
        self._capsule(d, P["shL"], P["elL"], aw, self.shirt)
        self._capsule(d, P["elL"], P["haL"], aw * 0.9, self.shirt)
        # torso: rounded filled blob (caricature berisi) on rotated temp layer
        tw, th = self.torso_w * k, self.torso_h * k
        pad = int(u * 0.12) + 8
        tmp = Image.new("RGBA", (int(tw + pad * 2), int(th + pad * 2)),
                        (0, 0, 0, 0))
        dt = ImageDraw.Draw(tmp)
        dt.rounded_rectangle([(pad, pad), (pad + tw, pad + th)],
                             radius=int(tw * 0.42), fill=self.shirt + (255,))
        # belly roundness: extra lower ellipse
        dt.ellipse([(pad + tw * 0.08, pad + th * 0.42),
                    (pad + tw * 0.92, pad + th * 1.02)],
                   fill=self.shirt + (255,))
        # collar shadow
        dt.ellipse([(pad + tw * 0.30, pad - th * 0.06),
                    (pad + tw * 0.70, pad + th * 0.16)],
                   fill=(0, 0, 0, 60))
        if self.koko:
            # koko shirt: mandarin collar band + button placket
            sh = self.shirt
            dark_c = (max(sh[0] - 38, 0), max(sh[1] - 34, 0), max(sh[2] - 30, 0))
            cx0 = pad + tw * 0.5
            dt.rounded_rectangle([(cx0 - tw * 0.16, pad + th * 0.015),
                                 (cx0 + tw * 0.16, pad + th * 0.085)],
                                radius=int(tw * 0.04), fill=dark_c + (255,))
            # V opening below collar
            dt.polygon([(cx0 - tw * 0.10, pad + th * 0.085),
                        (cx0 + tw * 0.10, pad + th * 0.085),
                        (cx0, pad + th * 0.20)], fill=dark_c + (255,))
            # buttons
            for by in (0.30, 0.44):
                dt.ellipse([(cx0 - tw * 0.022, pad + th * by),
                            (cx0 + tw * 0.022, pad + th * by + tw * 0.044)],
                           fill=(235, 225, 205, 255))
        blit_rot(layer, tmp, (ox, oy), -self.pose["lean"])
        # head
        hl = Image.new("RGBA", base_rgba.size, (0, 0, 0, 0))
        self._draw_head(hl, P["head"])
        hrot = hl.rotate(self.pose["head_tilt"] + self.pose["head_nod"] * 0.4,
                         resample=Image.BICUBIC, center=P["head"])
        layer.alpha_composite(hrot)
        # front limbs (R)
        d = ImageDraw.Draw(layer)
        self._capsule(d, P["hipR"], P["knR"], lw, self.pants)
        self._capsule(d, P["knR"], P["ftR"], lw * 0.92, self.pants)
        # feet: rounded shoes
        fr = lw * 0.62
        for fk in ("ftL", "ftR"):
            fx, fy = P[fk]
            d.rounded_rectangle([(fx - fr * 1.15, fy - fr * 0.55),
                                (fx + fr * 1.15, fy + fr * 0.55)],
                               radius=int(fr * 0.5), fill=(26, 20, 16, 255))
        self._capsule(d, P["shR"], P["elR"], aw, self.shirt)
        self._capsule(d, P["elR"], P["haR"], aw * 0.9, self.shirt)
        # hands: skin discs
        hr = aw * 0.58
        for hk in ("haL", "haR"):
            hx, hy = P[hk]
            d.ellipse([hx - hr, hy - hr, hx + hr, hy + hr],
                      fill=self.skin + (255,))
        base_rgba.alpha_composite(layer)

    # ------------------------------------------------------- animation verbs
    def walk(self, t, stride_freq=1.6, swing=32.0, arm_swing=26.0):
        """Walk cycle: legs sine, arms counter-swing, torso bob."""
        p = 2 * math.pi * stride_freq * t
        self.pose["hip_L"] = swing * math.sin(p)
        self.pose["hip_R"] = swing * math.sin(p + math.pi)
        self.pose["knee_L"] = 8 + 42 * max(0.0, math.sin(p - 2.1))
        self.pose["knee_R"] = 8 + 42 * max(0.0, math.sin(p + math.pi - 2.1))
        self.pose["shoulder_L"] = -arm_swing * math.sin(p) + 6
        self.pose["shoulder_R"] = -arm_swing * math.sin(p + math.pi) + 6
        self.pose["elbow_L"] = 14 + 10 * math.sin(p)
        self.pose["elbow_R"] = 14 + 10 * math.sin(p + math.pi)
        self.pose["bob"] = -abs(math.sin(p)) * self.unit * 0.022
        self.pose["lean"] = 5.0

    def idle_breathe(self, t, rate=0.28, amp=1.0):
        """Subtle breathing: bob + lean sway. Keeps every frame alive."""
        s = math.sin(2 * math.pi * rate * t)
        s2 = math.sin(2 * math.pi * rate * t + 1.3)
        self.pose["bob"] = -abs(s) * self.unit * 0.008 * amp
        self.pose["lean"] = s2 * 1.6 * amp
        self.pose["shoulder_L"] = 8 + s * 2.0 * amp
        self.pose["shoulder_R"] = -8 - s * 2.0 * amp

    def arm_raise(self, t, dur=1.1, arm="R", delay=0.0):
        """Raise one arm high (calling for help): anticipation dip, expo
        rise, overshoot settle. t seconds since cue start."""
        tt = clamp01((t - delay) / dur)
        key = "shoulder_" + arm
        rest = -8 if arm == "R" else 8
        # shoulder angle: 0 = down. Raised high = ~150 deg toward up.
        target = 150.0 if arm == "R" else -150.0
        m = anticipation_rise(tt)
        # clamp the dip so it never goes weird
        self.pose[key] = rest + (target - rest) * max(m, -0.15)
        ek = "elbow_" + arm
        self.pose[ek] = 12 * (1 - tt) + 6

    def arm_lower(self, t, dur=1.4, arm="R", delay=0.0, start_angle=150.0):
        """Lower arm back down with settle."""
        tt = clamp01((t - delay) / dur)
        key = "shoulder_" + arm
        rest = -8 if arm == "R" else 8
        e = expo_in_out(tt)
        self.pose[key] = start_angle + (rest - start_angle) * e

    def row(self, t, freq=0.55, sweep=30.0):
        """Rowing: shoulders sweep, elbows pump, torso rocks slightly."""
        p = 2 * math.pi * freq * t
        s = math.sin(p)
        self.pose["shoulder_L"] = 42 + sweep * s
        self.pose["shoulder_R"] = 42 + sweep * s
        self.pose["elbow_L"] = 26 - 16 * s
        self.pose["elbow_R"] = 26 - 16 * s
        self.pose["lean"] = 8 + 7 * s
        self.pose["bob"] = -abs(math.cos(p)) * self.unit * 0.012
        return s  # stroke phase for oar + ripples

    def head_down(self, t, dur=1.2, delay=0.0, amount=26.0):
        """Dilemma: head tilts/nods down with expo-out."""
        tt = clamp01((t - delay) / dur)
        self.pose["head_nod"] = amount * expo_out(tt)
        self.pose["head_tilt"] = 6 * expo_out(tt)

    def head_turn_to(self, t, dur=0.9, delay=0.0, direction=1.0):
        """Turn face toward a side (-1 left, +1 right)."""
        tt = clamp01((t - delay) / dur)
        self.pose["head_turn"] = direction * expo_in_out(tt)
        self.look = (direction * 0.8 * expo_in_out(tt), 0.1)

    def sit(self):
        """Seated preset: thighs forward, shins down."""
        self.pose.update({"hip_L": -78, "hip_R": -78, "knee_L": 82,
                          "knee_R": 82, "shoulder_L": 10, "shoulder_R": -10,
                          "elbow_L": 18, "elbow_R": 18, "lean": -4})

    def set_expr(self, expr):
        self.expr = expr


# ==================================================================== Rain
class Rain:
    """Deterministic rain streaks."""

    def __init__(self, n=170, seed=7, slant=-0.18, speed=(950, 1500),
                 length=(34, 70), color=(150, 170, 200, 110)):
        rng = np.random.default_rng(seed)
        self.n = n
        self.x0 = rng.uniform(0, 1, n)
        self.spd = rng.uniform(speed[0], speed[1], n)
        self.ln = rng.uniform(length[0], length[1], n)
        self.ph = rng.uniform(0, 1, n)
        self.slant = slant
        self.color = color

    def draw(self, base_rgba, t, W, H, x0=0, x1=None):
        if x1 is None:
            x1 = W
        ov = Image.new("RGBA", base_rgba.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        span = x1 - x0
        for i in range(self.n):
            y = (self.ph[i] * (H + 240) + self.spd[i] * t) % (H + 240) - 120
            x = x0 + ((self.x0[i] * span + self.slant * y) % span)
            l = self.ln[i]
            d.line([(x, y), (x + self.slant * l, y + l)],
                   fill=self.color, width=3)
        base_rgba.alpha_composite(ov)


# ==================================================================== Water
class Water:
    """Animated flood-water surface with waves, foam and lamp reflection."""

    def __init__(self, y_base, seed=21,
                 color_top=(36, 34, 30), color_deep=(12, 11, 10),
                 foam=(200, 190, 170, 130)):
        self.y_base = y_base
        self.foam = foam
        self.color_top = color_top
        self.color_deep = color_deep
        rng = np.random.default_rng(seed)
        self.foam_x = rng.uniform(0, 1, 26)
        self.foam_spd = rng.uniform(20, 60, 26)

    def surface(self, x, t):
        return (self.y_base
                + 14 * math.sin(0.008 * x + 1.7 * t)
                + 9 * math.sin(0.017 * x - 2.6 * t + 1.2)
                + 5 * math.sin(0.031 * x + 3.4 * t + 4.0))

    def draw(self, base_rgba, t, W, H, lamp_x=None):
        # vertical gradient body (cached — built once per geometry)
        top = int(self.y_base) - 40
        key = (top, H, W, self.color_top, self.color_deep)
        if getattr(self, "_grad_key", None) != key:
            gh = H - top
            grad = np.zeros((gh, 1, 3), dtype=np.uint8)
            for c in range(3):
                grad[:, 0, c] = np.linspace(self.color_top[c],
                                           self.color_deep[c], gh)
            self._grad_img = Image.fromarray(np.repeat(grad, W, axis=1), "RGB")
            self._grad_key = key
            self._grad_top = top
        gimg = self._grad_img
        # wave surface mask
        mask = Image.new("L", (W, H), 0)
        dm = ImageDraw.Draw(mask)
        xs = list(range(0, W + 1, 12))
        pts = [(x, self.surface(x, t)) for x in xs]
        dm.polygon([(0, H)] + pts + [(W, H)], fill=255)
        top = self._grad_top
        base_rgba.paste(gimg, (0, top), mask.crop((0, top, W, H)))
        ov = Image.new("RGBA", base_rgba.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        # surface highlight
        for i in range(len(pts) - 1):
            d.line([pts[i], pts[i + 1]], fill=(120, 110, 95, 160), width=4)
        # drifting foam dashes
        for i in range(len(self.foam_x)):
            fx = (self.foam_x[i] * W + self.foam_spd[i] * t) % W
            fy = self.surface(fx, t) + 8 + 6 * math.sin(t * 2 + i)
            fl = 26 + 20 * math.sin(i * 3.7)
            d.line([(fx - fl / 2, fy), (fx + fl / 2, fy)],
                   fill=self.foam, width=3)
        # lamp reflection streak
        if lamp_x is not None:
            for k in range(7):
                yy = self.surface(lamp_x, t) + 26 + k * 34
                wob = 10 * math.sin(t * 2.2 + k * 1.1)
                ww = 60 - k * 6
                al = max(120 - k * 16, 20)
                d.line([(lamp_x - ww / 2 + wob, yy),
                        (lamp_x + ww / 2 + wob, yy)],
                       fill=(255, 170, 80, al), width=9)
        base_rgba.alpha_composite(ov)


# ===================================================================== Boat
class Boat:
    """Wooden boat hull; call draw() inside a boat-local layer, then blit
    the layer with bob transform via draw_on(base, ...)."""

    def __init__(self, w=560, h=150, wood=(74, 52, 34), rim=(104, 76, 48)):
        self.w = w
        self.h = h
        self.wood = wood
        self.rim = rim

    def draw_on(self, base_rgba, t, cx, cy, W, H, bob_amp=1.0):
        """Draw bobbing boat centered at (cx, cy) [cy = waterline]."""
        bob_y = math.sin(2 * math.pi * t / 2.6) * 13 * bob_amp
        bob_r = math.sin(2 * math.pi * t / 3.4 + 1.0) * 2.6 * bob_amp
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        w, h = self.w, self.h
        x0, x1 = cx - w / 2, cx + w / 2
        # hull: trapezoid with curved bottom
        d.polygon([(x0, cy - h * 0.55), (x1, cy - h * 0.55),
                   (x1 - w * 0.10, cy + h * 0.45),
                   (x0 + w * 0.10, cy + h * 0.45)],
                  fill=self.wood + (255,))
        d.arc([x0 + w * 0.10, cy + h * 0.05, x1 - w * 0.10, cy + h * 0.85],
              start=0, end=180, fill=self.wood + (255,), width=int(h * 0.5))
        # rim
        d.line([(x0, cy - h * 0.55), (x1, cy - h * 0.55)],
               fill=self.rim + (255,), width=14, joint="curve")
        # plank lines
        for k in (0.15, 0.35):
            yy = cy - h * 0.55 + h * k
            inset = w * 0.10 * k / 0.55
            d.line([(x0 + inset, yy), (x1 - inset, yy)],
                   fill=(0, 0, 0, 90), width=4)
        # bench
        d.line([(x0 + w * 0.18, cy - h * 0.28),
                (x1 - w * 0.18, cy - h * 0.28)],
               fill=self.rim + (255,), width=12)
        rot = lay.rotate(bob_r, resample=Image.BICUBIC, center=(cx, cy))
        base_rgba.alpha_composite(rot, (0, int(bob_y)))
        return bob_y, bob_r


# ===================================================================== Lamp
class Lamp:
    """Street lamp with flickering warm glow (deterministic)."""

    def __init__(self, x, y_top, h=560, glow_r=340,
                 glow=(255, 166, 66)):
        self.x = x
        self.y_top = y_top
        self.h = h
        self.glow_r = glow_r
        self.glow = glow
        # precomputed radial glow sprite
        r = glow_r
        yy, xx = np.mgrid[0:2 * r, 0:2 * r]
        dist = np.sqrt((xx - r) ** 2 + (yy - r) ** 2) / r
        a = np.clip(1 - dist, 0, 1) ** 2.2
        sprite = np.zeros((2 * r, 2 * r, 4), dtype=np.uint8)
        sprite[..., 0] = glow[0]
        sprite[..., 1] = glow[1]
        sprite[..., 2] = glow[2]
        sprite[..., 3] = (a * 255).astype(np.uint8)
        self.sprite = Image.fromarray(sprite, "RGBA")

    def flicker(self, t):
        return 0.86 + 0.10 * math.sin(t * 11.0) + 0.04 * math.sin(t * 43.0 + 1.7)

    def draw(self, base_rgba, t, W, H):
        d = ImageDraw.Draw(base_rgba)
        bx, by = self.x, self.y_top + self.h
        # pole
        d.line([(self.x, self.y_top), (self.x, by)], fill=(24, 20, 16, 255),
               width=22, joint="curve")
        d.line([(self.x, self.y_top), (self.x + 90, self.y_top + 26)],
               fill=(24, 20, 16, 255), width=18, joint="curve")
        lx, ly = self.x + 96, self.y_top + 40
        # lamp head
        d.ellipse([lx - 34, ly - 20, lx + 34, ly + 20], fill=(30, 24, 18, 255))
        d.ellipse([lx - 20, ly - 12, lx + 20, ly + 12],
                  fill=(255, 200, 110, 255))
        # glow
        fl = self.flicker(t)
        gs = self.sprite.copy()
        alpha = gs.split()[3].point(lambda v: int(v * fl * 0.85))
        gs.putalpha(alpha)
        base_rgba.alpha_composite(gs, (int(lx - self.glow_r),
                                      int(ly - self.glow_r)))
        return (lx, ly)


# ==================================================================== House
class House:
    """Simple house with openable door + rooftop perch spot."""

    def __init__(self, x, y_base, w=560, h=620, wall=(52, 40, 30),
                 roof=(30, 22, 18)):
        self.x, self.y_base, self.w, self.h = x, y_base, w, h
        self.wall, self.roof = wall, roof

    def draw(self, base_rgba, t, door_open=0.0, W=1080, H=1920):
        """door_open: 0 closed .. 1 fully open."""
        d = ImageDraw.Draw(base_rgba)
        x0 = self.x - self.w / 2
        y0 = self.y_base - self.h
        # wall
        d.rectangle([x0, y0, x0 + self.w, self.y_base], fill=self.wall + (255,))
        # roof (sloped)
        d.polygon([(x0 - 60, y0), (x0 + self.w + 60, y0),
                   (x0 + self.w / 2, y0 - 190)], fill=self.roof + (255,))
        # window with warm light
        wx, wy = x0 + self.w * 0.62, y0 + 150
        d.rectangle([wx - 55, wy - 70, wx + 55, wy + 70],
                    fill=(255, 178, 90, 235))
        d.line([(wx - 55, wy), (wx + 55, wy)], fill=(30, 22, 16, 255), width=8)
        d.line([(wx, wy - 70), (wx, wy + 70)], fill=(30, 22, 16, 255), width=8)
        # doorway
        dx, dw, dh = x0 + self.w * 0.16, 150, 300
        dy = self.y_base - dh
        d.rectangle([dx, dy, dx + dw, self.y_base], fill=(8, 6, 5, 255))
        # light wedge spilling out, grows with door angle
        if door_open > 0.01:
            e = expo_out(door_open)
            wl = 260 * e
            ov = Image.new("RGBA", base_rgba.size, (0, 0, 0, 0))
            od = ImageDraw.Draw(ov)
            od.polygon([(dx, dy + dh * 0.3), (dx + dw, dy + dh * 0.3),
                        (dx + dw + wl, self.y_base + 60),
                        (dx - wl * 0.4, self.y_base + 60)],
                       fill=(255, 170, 80, int(110 * e)))
            base_rgba.alpha_composite(ov)
        # door panel rotating open (hinge at left)
        ang = -72 * expo_out(door_open)
        dw2 = dw - 14
        door = Image.new("RGBA", (int(dw2) + 20, dh + 20), (0, 0, 0, 0))
        dd = ImageDraw.Draw(door)
        dd.rectangle([(10, 10), (10 + dw2, 10 + dh)], fill=(66, 46, 30, 255))
        dd.rectangle([(10, 10), (10 + dw2, 10 + dh)], outline=(24, 16, 10, 255),
                     width=6)
        blit_rot(base_rgba, door, (dx + 7, dy + dh / 2), ang)
        return {"roof_y": y0 - 190, "roof_x": x0 + self.w / 2,
                "door": (dx, dy, dw, dh)}


# ==================================================================== Oar
def draw_oar(base_rgba, pivot, angle_deg, length=430, wood=(96, 70, 44)):
    """Oar rotating about pivot (oarlock). angle 0 = pointing down."""
    a = math.radians(angle_deg)
    tip = (pivot[0] + math.sin(a) * length, pivot[1] + math.cos(a) * length)
    d = ImageDraw.Draw(base_rgba)
    w = 20
    d.line([pivot, tip], fill=wood + (255,), width=w, joint="curve")
    # blade
    bx, by = tip
    px, py = math.cos(a), -math.sin(a)
    bw = 46
    d.polygon([(bx - px * bw / 2, by - py * bw / 2),
               (bx + px * bw / 2, by + py * bw / 2),
               (bx + px * bw / 2 - math.sin(a) * 90,
                by + py * bw / 2 - math.cos(a) * 90),
               (bx - px * bw / 2 - math.sin(a) * 90,
                by - py * bw / 2 - math.cos(a) * 90)],
              fill=wood + (255,))
    return tip


def draw_ripple(base_rgba, cx, cy, t, seed=3, max_r=120,
                color=(190, 180, 160, 120)):
    """Expanding ripple rings at oar tip (deterministic)."""
    ov = Image.new("RGBA", base_rgba.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for k in range(3):
        ph = ((t * 0.7 + seed * 0.37 + k / 3.0) % 1.0)
        r = 12 + ph * max_r
        al = int(color[3] * (1 - ph))
        d.ellipse([cx - r, cy - r * 0.32, cx + r, cy + r * 0.32],
                  outline=color[:3] + (al,), width=3)
    base_rgba.alpha_composite(ov)
