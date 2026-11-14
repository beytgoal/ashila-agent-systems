#!/usr/bin/env python3
"""
motion_render.py — Python motion-graphics engine (v1.1)
Adaptation of the motion-video skill for environments where Remotion/Chrome
cannot run. Implements the skill's core playbook with PIL + numpy + ffmpeg:

- VO-first timing (scene durations from measured narration)
- Kinetic typography: staggered word entrances, expo-out easing, slam accents,
  scramble/decode entrance variant
- v3 word_highlight: kata headline & body disorot (amber + membesar) mengikuti
  durasi VO, kata per kata — teks tidak pernah diam (scene flag word_highlight,
  atau project flag yang dipropagasi main())
- Kicker labels (mono, tracked-out)
- Style palettes (lila default; see STYLES)
- Vector shapes: bars, ring, arrow, pulse rings, count-up numbers
- Illustration PNG layers with entrances
- Panel chrome behind headline; auto-layout keeps headline clear of lower shapes
- Fuzzy asset resolution (a near-miss path still finds the file)
- Whip-style transitions with SFX glue
- Bed music mixed under loudness-normalized VO

Usage:
  python3 motion_render.py project.json -o out.mp4

project.json format:
{
  "style": "cinematic",
  "fps": 30, "width": 1080, "height": 1920,
  "bed": "path/to/bed.mp3",            # optional
  "sfx": {"whoosh": "...", "impact": "..."},  # optional
  "scenes": [
    {
      "bg": "path/to/bg.png",           # background image (AI-generated ok)
      "vo": "path/to/narration.mp3",    # voiceover for this scene
      "kicker": "001 — MASALAH",
      "headline": "Kata kunci SLAM",     # hero line
      "headline_entrance": "words",       # words | scramble
      "panel": true,                     # chrome panel behind headline
      "body": "Baris satu@@NL@@Baris dua",  # supporting text, staggered
      "accent_words": ["SLAM"],          # words rendered in accent color
      "illustrations": [{"file": "...", "x": 0.5, "y": 0.3, "size": 420,
                         "entrance": "rise|slam|fade|slide-left|slide-right",
                         "start": 10}],
      "shapes": [{"type": "bars|ring|arrow|pulse|countup", ...}],
      "camera": "punch-in"               # punch-in | punch-out | drift | static
    }
  ]
}
countup shape fields: target, prefix, suffix, decimals, font_size, label,
                      color, dur, start, x, y
"""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ---------------------------------------------------------------- styles
STYLES = {
    # style serial "cinematic" (dipulihkan 29 Okt 2026, perintah owner:
    # serial harus berbentuk cinematic) — definisi dipulihkan dari salinan
    # tes scratch/hedonic-tes/motion_render_tes.py; definisi engine sempat
    # dihapus 29 Okt 05:30 WIB. Look serial harian: latar gelap, tinta
    # putih, aksen amber, tipografi skill motion-video.
    "cinematic": {
        "bg": (12, 12, 16),
        "surface": (24, 24, 32),
        "ink": (240, 238, 232),
        "ink_dim": (140, 138, 130),
        "accent": (255, 180, 60),      # warm amber hero
        "danger": (235, 80, 70),
        "grid": (40, 40, 52),
        # skill motion-video (27 Okt 2026, perintah owner: ganti tipografi
        # + motion pakai skill ini) — Inter + JetBrains Mono gantikan DejaVu
        # (dinilai kuno).
        "font_hero": "Inter-Bold",
        "font_body": "Inter-Regular",
        "font_mono": "JetBrainsMono-Regular",
        "font_mono_bold": "JetBrainsMono-Bold",
        "hero_size": 120,        # skill §3.3: hero word >=120px @1080p (dulu 84)
        "body_size": 48,         # dulu 44
        "skill_v2": True,        # gating: tipografi + motion skill baru
        "line_height": 1.18,     # skill Kinetic: 1.18 (dulu 1.25)
        "word_rise": 34,         # skill Kinetic: rise 34px (dulu 60)
        "word_dur": 18,          # skill Kinetic: 18f (dulu 16)
        "word_deblur": True,     # skill Kinetic: blur 10->0 saat masuk
    },
    # referensi @beyondstudioid (2026-10-25): krem + biru elektrik, dipakai
    # pertama untuk video reaktif TikTok Awards SEA (26 Okt 2026)
    "beyond": {
        "bg": (244, 240, 232),         # krem / off-white
        "surface": (255, 255, 255),
        "ink": (16, 22, 48),           # biru gelap (teks di krem)
        "ink_dim": (95, 100, 120),
        "accent": (0, 100, 255),       # biru elektrik (SATU kata kunci)
        "danger": (235, 80, 70),
        "grid": (222, 217, 207),
        "font_hero": "DejaVuSans-Bold",
        "font_body": "DejaVuSans",
        "font_mono": "DejaVuSansMono",
        "darken_bg": False,
    },
    # gaya @kalbotau (26 Okt 2026, perintah owner: ganti tipografi LAMA yang
    # dinilai terlalu kuno) — sans modern tebal, kata kunci sorot biru.
    # 3 Nov 2026 (perintah owner): DIBALIK jadi teks PUTIH di atas latar
    # gelap — tidak ada teks hitam lagi di template mana pun.
    "kalbotau": {
        "bg": (24, 24, 27),             # arang gelap hangat (dulu putih hangat)
        "surface": (40, 40, 45),
        "ink": (245, 243, 239),         # off-white #F5F3EF (teks utama)
        "ink_dim": (170, 170, 175),
        "accent": (0, 100, 255),       # biru (sorot kata kunci, seperti kalbotau)
        "danger": (235, 80, 70),
        "grid": (54, 54, 60),
        "font_hero": "NotoSans-ExtraBold",
        "font_body": "NotoSans-Bold",
        "font_mono": "DejaVuSansMono",
        "darken_bg": False,
        "hl_box": True,                # sorot kata = KOTAK BIRU + teks putih
        "kicker_ink": "ink",           # label bab ikut ink (putih)
        # v2 penyamaan kalbotau (26 Okt 2026): HANYA style ini — "edukasi" beku
        "hero_size": 92,        # headline lebih besar (default engine 84)
        "body_size": 48,        # body lebih besar (default engine 44)
        "body_dy": 60,          # body turun 60px — isi zona bawah (default H-560)
        "headline_dy": 120,     # headline turun 120px — rapat ke body (default H/2-40)
        "hook_size": 100,       # kartu hook: pertanyaan besar
        "hl_solid": True,       # kotak sorot langsung solid (default: ramp pucat)
    },
    # gaya serial baru "lila" (29 Okt 2026, perintah owner: template baru
    # untuk serial harian pasca-hapus cinematic) — editorial serif di atas
    # lila lembut. BEDA dari kalbotau (sans tebal + kotak biru) dan beyond
    # (sans + biru elektrik): headline serif, sorot kata = blend ke ungu
    # (bukan kotak), label bab plum. Bukan kebangkitan style yang dihapus.
    "lila": {
        "bg": (233, 229, 246),         # lila lembut
        "surface": (255, 255, 255),
        "ink": (46, 28, 72),           # plum gelap (teks utama)
        "ink_dim": (115, 102, 135),    # mauve abu (teks sekunder)
        "accent": (124, 58, 237),      # ungu (sorot kata kunci, blend)
        "danger": (214, 84, 66),       # terakota (angka kontras)
        "grid": (208, 200, 228),
        "font_hero": "DejaVuSerif-Bold",
        "font_body": "DejaVuSerif",
        "font_mono": "DejaVuSansMono",
        "darken_bg": False,
        "kicker_ink": "ink",           # label bab plum (bukan abu-abu)
        "hero_size": 88,        # headline (default engine 84)
        "body_size": 46,        # body (default engine 44)
    },
}

# ---------------------------------------------------------------- easing
def expo_out(t):  # skill §4: expo-out entrances
    return 1 - pow(2, -10 * t) if t < 1 else 1

def ease_out_back(t, s=1.70158):  # slam overshoot
    t -= 1
    return 1 + (s + 1) * t ** 3 + s * t ** 2

def ease_in(t):
    return t * t

def spring_p(f, fps=30, stiffness=160, damping=18):
    """Remotion spring (mass=1, skill Punch): p 0->1 dengan overshoot kecil.
    omega=sqrt(k), zeta=c/(2*sqrt(k)), omega_d=omega*sqrt(1-zeta^2)."""
    t = max(f, 0) / fps
    w = math.sqrt(stiffness)
    z = damping / (2 * w)
    wd = w * math.sqrt(max(1 - z * z, 1e-6))
    return 1 - math.exp(-z * w * t) * (
        math.cos(wd * t) + (z / math.sqrt(max(1 - z * z, 1e-6))) * math.sin(wd * t))

def clamp01(t):
    return max(0.0, min(1.0, t))


def _blend(c1, c2, t):
    """v3: interpolasi warna c1 -> c2 (dipakai word_highlight)."""
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))

# ---------------------------------------------------------------- fonts
_font_cache = {}
def font(name, size):
    key = (name, size)
    if key not in _font_cache:
        for ext in (".ttf", ".otf"):
            for d in ("/usr/share/fonts/truetype/dejavu",
                      "/usr/share/fonts/truetype/noto",
                      "/home/user/workspace/motion-video-projects/serial-psikologis/public/fonts"):
                p = os.path.join(d, name + ext)
                if os.path.exists(p):
                    _font_cache[key] = ImageFont.truetype(p, size)
                    break
            if key in _font_cache:
                break
        else:
            _font_cache[key] = ImageFont.load_default()
    return _font_cache[key]

def text_size(draw, s, f):
    b = draw.textbbox((0, 0), s, font=f)
    return b[2] - b[0], b[3] - b[1]

def draw_tracked(draw, xy, s, f, fill, tracking=6):
    """Mono tracked-out text (kickers)."""
    x, y = xy
    for ch in s:
        draw.text((x, y), ch, font=f, fill=fill)
        w, _ = text_size(draw, ch, f)
        x += w + tracking
    return x

def _tracked_w(draw, s, f, tracking):
    """Lebar visual teks tracked-out (ujung huruf terakhir, tanpa trailing)."""
    if not s:
        return 0
    return (sum(text_size(draw, ch, f)[0] + tracking for ch in s)
            - tracking)

def _fit_tracked(draw, s, f, tracking, x0, xmax):
    """Potong string dari kanan sampai teks tracked-out muat di x0..xmax."""
    while s and x0 + _tracked_w(draw, s, f, tracking) > xmax:
        s = s[:-1]
    return s

def draw_text_center(draw, cx, y, s, f, fill, stroke=0, stroke_fill=(0, 0, 0)):
    w, h = text_size(draw, s, f)
    draw.text((cx - w / 2, y), s, font=f, fill=fill,
              stroke_width=stroke, stroke_fill=stroke_fill)
    return h


def _resolve(path):
    """v1.1: resolve an asset path; if the exact path is missing, fuzzy-match
    by filename tokens inside the known asset directories."""
    if not path:
        return None
    if os.path.exists(path):
        return path
    import re
    stem = os.path.splitext(os.path.basename(path))[0].lower()
    toks = [t for t in re.split(r"[-_. ]+", stem) if t]
    if not toks:
        return None
    search_dirs = [
        "/home/user/workspace/motion-video-projects/engine/assets",
        "/home/user/workspace/goals/serial-animasi-analogi-psikologis-10-topik/hidden_files",
        os.path.dirname(path) or ".",
    ]
    best, best_extra = None, None
    for dname in search_dirs:
        if not os.path.isdir(dname):
            continue
        try:
            files = os.listdir(dname)
        except OSError:
            continue
        for fn in files:
            ftoks = [t for t in re.split(r"[-_. ]+",
                                         os.path.splitext(fn)[0].lower()) if t]
            if all(t in ftoks for t in toks):
                extra = len(ftoks) - len(toks)
                if best is None or extra < best_extra:
                    best, best_extra = os.path.join(dname, fn), extra
    if best:
        print(f"  [resolve] {path} -> {best}")
    return best


SCRAMBLE_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#%&?/<>"

# ---------------------------------------------------------------- zona aman
# Aturan owner 28 Okt 2026 ~18:38 WIB: semua teks harus punya padding dan
# margin di dalam frame — tidak ada teks menyentuh/melewati tepi. Zona aman
# frame 1080 lebar: x=64..1016 (margin 64px tiap sisi), y=64..1856.
# Diterapkan ke semua blok teks: kicker, headline, body, highlight box,
# panel, hook. Kamera punch-in/out sudah settle (~1.0) saat teks tampil.
SAFE_L, SAFE_R = 64, 1016
SAFE_W = SAFE_R - SAFE_L            # 952
HEADLINE_MAX_W = 900                # lebar ter-scale maks baris headline
                                    # (930 lama: kotak aksen +12px/sisi
                                    #  -> 63..1017, bocor 1px dari zona)
HEADLINE_MAX_W_OLD_CAM = 840        # kamera lama (non-skill_v2) settle
                                    # lambat (zoom 1.09x di awal scene) —
                                    # baris dibatasi 840px supaya kotak
                                    # aksen tetap di zona aman selama
                                    # transien f=14..48 (terukur f=30:
                                    # cap 900 -> kotak aksen x~53)
BODY_MAX_W = 880                    # lebar maks baris body (ter-wrap)
# ---------------------------------------------------------------- grain
def add_grain(img, amount=6, seed=0):
    rng = np.random.default_rng(seed)
    a = np.asarray(img).astype(np.int16)
    n = rng.integers(-amount, amount + 1, a.shape[:2])
    a[:, :, :3] = np.clip(a[:, :, :3] + n[:, :, None], 0, 255)
    return Image.fromarray(a.astype(np.uint8))

# ---------------------------------------------------------------- scene renderer
class SceneRenderer:
    def __init__(self, scene, style, fps, W, H, sfx=None):
        self.sc = scene
        self.st = style
        self.fps = fps
        self.W, self.H = W, H
        self.sfx = sfx or {}
        # VO duration -> scene frames (voDelay 20f + tail 35f)
        vo_path = _resolve(scene.get("vo"))
        scene["vo"] = vo_path
        self.vo_dur = self._audio_dur(vo_path)
        # tail_frames: jeda tahan setelah VO habis (default 55f = 20+35 lama).
        # Proyek reaktif bisa memendekkan (mis. 30f) supaya pacing lebih rapat.
        self.frames = int((self.vo_dur or 6.0) * fps) + scene.get("tail_frames", 55)
        # Ken Burns ilustrasi (BRD-005, 29 Okt 2026): flag per scene,
        # diisi dari project-level "illustration_motion" di main().
        # Default False = perilaku lama byte-identik (statis + bob).
        self.illustration_motion = bool(scene.get("illustration_motion", False))
        # background: video > image > generated grid
        self.bg_video = None
        bg_video_path = _resolve(scene.get("bg_video"))
        if bg_video_path:
            # extract frames from video, loop/trim to scene duration
            self.bg_video = self._load_bg_video(bg_video_path)
        bg_path = _resolve(scene.get("bg"))
        if bg_path:
            try:
                bg = Image.open(bg_path).convert("RGB")
                bg = self._cover(bg, W, H)
            except Exception as ex:
                print(f"  [warn] bg load failed {bg_path}: {ex}")
                bg = None
        else:
            if scene.get("bg"):
                print(f"  [warn] bg not found: {scene.get('bg')}")
            bg = None
        if bg is None:
            bg = Image.new("RGB", (W, H), style["bg"])
            self._draw_grid(bg)
        # darken for text legibility (cinematic stage)
        if style.get("darken_bg", True):
            overlay = Image.new("RGB", (W, H), (0, 0, 0))
            bg = Image.blend(bg, overlay, 0.35)
        self.bg = bg
        # parse text
        self.words = (scene.get("headline") or "").split()
        self.accent_words = set(w.strip().strip(".,!?").upper() for w in scene.get("accent_words", []))
        # zona aman: bungkus baris body ke BODY_MAX_W (baris panjang
        # sebelumnya dirender tanpa batas — terukur baris body ep14 2183px
        # -> x -551..1632 tanpa wrap)
        self.body_lines = self._wrap_body(
            (scene.get("body") or "").split("@@NL@@"))
        self.kicker = scene.get("kicker", "")
        self.hook = scene.get("hook")          # v2 kalbotau: {"text","accent","frames"}
        self.character = scene.get("character")  # v2 kalbotau: {"file","x","y","size"}
        # v3 word_highlight: durasi VO dalam frame (VO mulai frame 0 scene;
        # tail_frames di luar VO tidak ikut jendela sorot)
        self.vo_frames = int((self.vo_dur or 6.0) * fps)
        self.word_highlight = bool(scene.get("word_highlight"))
        # layout (computed lazily per frame is fine at 30fps)
        self.camera = scene.get("camera", "punch-in")
        self.flip = bool(scene.get("flip", False))  # skill Punch: arah rotasi bergantian per scene
        # insert/cutaway mode: stock video full-frame, minimal overlay
        self.is_insert = scene.get("insert", False)

    def _load_bg_video(self, path):
        """Extract video frames to disk, load on-demand to save RAM. Returns temp dir + count."""
        import tempfile, glob
        # extract at scene fps, scale to cover 1080x1920
        tmpd = tempfile.mkdtemp(prefix="bgvid-")
        W, H = self.W, self.H
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error", "-i", path,
            "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={self.fps}",
            f"{tmpd}/bg%04d.jpg"
        ], check=True)
        frames = sorted(glob.glob(f"{tmpd}/bg*.jpg"))
        print(f"  [bgvideo] {path}: {len(frames)} frames @ {self.fps}fps (on-demand)")
        # return dir and file list instead of loading all into RAM
        return {"dir": tmpd, "files": frames}

    def _bg_frame(self, f):
        """Get background for frame f: video frame (looped, loaded on-demand) or static image."""
        if self.bg_video:
            files = self.bg_video["files"]
            fp = files[f % len(files)]
            return Image.open(fp).convert("RGB")
        return self.bg.copy()

    def _hl(self, f, idx, n, start):
        """v3: VO-synced word highlight. Kata ke-idx dari n kata disorot
        selama jendelanya di dalam durasi VO (frame start..vo_frames).
        Return 0..1 dengan ramp masuk/keluar ~5 frame (tanpa popping)."""
        if n <= 0:
            return 0.0
        span = max(self.vo_frames - start, 1)
        w0 = start + idx * span / n
        w1 = start + (idx + 1) * span / n
        return clamp01((f - w0) / 5) * clamp01((w1 - f) / 5)

    def _audio_dur(self, path):
        if not path or not os.path.exists(path):
            return None
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                            "format=duration", "-of", "csv=p=0", path],
                           capture_output=True, text=True)
        try:
            return float(r.stdout.strip())
        except ValueError:
            return None

    def _wrap_body(self, lines):
        """Bungkus tiap baris body ke BODY_MAX_W (zona aman x=64..1016).
        Baris pendek (konten serial selama ini) tidak berubah."""
        bf = font(self.st["font_body"], self.st.get("body_size", 44))
        probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        space_w, _ = text_size(probe, " ", bf)
        out = []
        for line in lines:
            words = line.split()
            if not words:
                out.append(line)
                continue
            cur, curw = [], 0
            for w in words:
                ww, _ = text_size(probe, w, bf)
                if cur and curw + space_w + ww > BODY_MAX_W:
                    out.append(" ".join(cur))
                    cur, curw = [], 0
                cur.append(w)
                curw += (space_w if curw else 0) + ww
            if cur:
                out.append(" ".join(cur))
        return out

    def _cover(self, img, W, H):
        iw, ih = img.size
        s = max(W / iw, H / ih)
        img = img.resize((int(iw * s) + 1, int(ih * s) + 1), Image.LANCZOS)
        x = (img.width - W) // 2
        y = (img.height - H) // 2
        return img.crop((x, y, x + W, y + H))

    def _draw_grid(self, img):
        d = ImageDraw.Draw(img)
        st = self.st
        for x in range(0, self.W, 90):
            d.line([(x, 0), (x, self.H)], fill=st["grid"], width=1)
        for y in range(0, self.H, 90):
            d.line([(0, y), (self.W, y)], fill=st["grid"], width=1)

    def _draw_illustration(self, img, ill, f):
        """v2: place a PNG illustration with entrance animation.
        ill: {file, x (0-1 center), y (0-1 center), size (px height),
              entrance: rise|slam|fade|slide-left|slide-right,
              start (frame), }
        """
        path = _resolve(ill.get("file"))
        if not path:
            return img
        W, H = self.W, self.H
        st = self.st
        start = ill.get("start", 20)
        t = clamp01((f - start) / 20)
        if t <= 0:
            return img
        pic = Image.open(path).convert("RGBA")
        # fit to target height
        th = ill.get("size", 500)
        s = th / pic.height
        pic = pic.resize((int(pic.width * s), int(pic.height * s)),
                         Image.LANCZOS)
        cx, cy = int(ill.get("x", 0.5) * W), int(ill.get("y", 0.38) * H)
        entrance = ill.get("entrance", "rise")
        e = expo_out(t)
        dx, dy, sc, alpha = 0, 0, 1.0, int(255 * min(t * 1.8, 1))
        if entrance == "rise":
            dy = int(120 * (1 - e))
        elif entrance == "slam":
            e2 = ease_out_back(min(t * 1.5, 1.0))
            sc = 1.35 - 0.35 * e2
            dy = int(-40 * (1 - e2))
        elif entrance == "slide-left":
            dx = int(-300 * (1 - e))
        elif entrance == "slide-right":
            dx = int(300 * (1 - e))
        # fade handled by alpha
        if abs(sc - 1.0) > 0.01:
            pic = pic.resize((max(int(pic.width * sc), 1),
                              max(int(pic.height * sc), 1)),
                             Image.LANCZOS)
        if alpha < 255:
            a = pic.split()[3].point(lambda v: v * alpha // 255)
            pic.putalpha(a)
        # Ken Burns (BRD-005): hanya bila flag proyek aktif DAN ilustrasi
        # ini tidak di-opt-out (motion != "none"). Menggantikan bob, bukan
        # ditambah — hindari gerak ganda. Zoom 1.00 -> motion_zoom (atau
        # sebaliknya bila motion_dir == "out"), pan smoothstep, crop
        # di-clamp ke dalam gambar yang di-zoom sehingga ilustrasi tidak
        # pernah keluar dari ukurannya sendiri. Tipografi digambar
        # sesudahnya di render_frame, jadi tidak tertutup gerak ini.
        _motion_active = False
        if t >= 1 and getattr(self, "illustration_motion", False):
            if ill.get("motion", "kenburns") != "none":
                _motion_active = True
                _dur = max(self.frames - start, 1)
                _p = clamp01((f - start) / _dur)
                _e = _p * _p * (3 - 2 * _p)  # smoothstep
                _zoom_end = float(ill.get("motion_zoom", 1.13))
                _dir = ill.get("motion_dir", "in")
                if _dir == "out":
                    _z = _zoom_end + (1.0 - _zoom_end) * _e
                else:
                    _z = 1.0 + (_zoom_end - 1.0) * _e
                _pan = ill.get("motion_pan", (-28, -18))
                _px, _py = int(_pan[0] * _e), int(_pan[1] * _e)
                _zw, _zh = max(int(pic.width * _z), 1), max(int(pic.height * _z), 1)
                _zoomed = pic.resize((_zw, _zh), Image.LANCZOS)
                _cx = min(max((_zw - pic.width) // 2 + _px, 0), max(_zw - pic.width, 0))
                _cy = min(max((_zh - pic.height) // 2 + _py, 0), max(_zh - pic.height, 0))
                pic = _zoomed.crop((_cx, _cy, _cx + pic.width, _cy + pic.height))
        # subtle float after entrance (ambient life per skill §4.2)
        # — nonaktif untuk ilustrasi yang sedang Ken Burns.
        if t >= 1 and not _motion_active:
            dy += int(12 * math.sin((f - start) * 0.06))
        img.paste(pic, (cx - pic.width // 2 + dx, cy - pic.height // 2 + dy),
                  pic)
        return img

    def _draw_shape(self, img, shp, f):
        """v2: vector shapes with animated entrances.
        shp: {type: bars|ring|arrow|line, ...}
        """
        st, W, H = self.st, self.W, self.H
        start = shp.get("start", 24)
        t = clamp01((f - start) / 22)
        if t <= 0:
            return img
        e = expo_out(t)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        alpha = int(255 * min(t * 1.8, 1))
        typ = shp.get("type")
        cx, cy = int(shp.get("x", 0.5) * W), int(shp.get("y", 0.62) * H)
        col = shp.get("color", "accent")
        fill = st[col] + (alpha,)
        if typ == "bars":
            # animated bar chart: bars grow with stagger
            vals = shp.get("values", [0.3, 0.5, 0.7, 0.9])
            bw, gap, maxh = shp.get("bw", 90), shp.get("gap", 30), shp.get("maxh", 320)
            total_w = len(vals) * bw + (len(vals) - 1) * gap
            x0 = cx - total_w / 2
            for i, v in enumerate(vals):
                bt = clamp01((f - start - i * 6) / 18)
                if bt <= 0:
                    continue
                bh = int(maxh * v * expo_out(bt))
                x = x0 + i * (bw + gap)
                d.rounded_rectangle([(x, cy - bh), (x + bw, cy)],
                                    radius=14, fill=fill)
        elif typ == "ring":
            # progress ring: arc sweeps
            r = shp.get("r", 130)
            pct = shp.get("pct", 0.75) * e
            d.arc([(cx - r, cy - r), (cx + r, cy + r)],
                  start=-90, end=-90 + 360 * pct, fill=fill, width=22)
            d.ellipse([(cx - r, cy - r), (cx + r, cy + r)],
                      outline=st["grid"] + (alpha,), width=6)
        elif typ == "arrow":
            # arrow grows left->right
            length = int(shp.get("length", 420) * e)
            wdt = shp.get("width", 18)
            x0 = cx - shp.get("length", 420) / 2
            d.line([(x0, cy), (x0 + length, cy)], fill=fill, width=wdt)
            if length > 40:  # arrowhead
                ah = 46
                d.polygon([(x0 + length, cy - ah), (x0 + length, cy + ah),
                           (x0 + length + ah, cy)], fill=fill)
        elif typ == "pulse":
            # expanding rings (ambient accent)
            for i in range(3):
                pt = ((f * 0.02 + i / 3) % 1.0)
                pr = int(60 + pt * 220)
                pa = int(alpha * (1 - pt) * 0.5)
                d.ellipse([(cx - pr, cy - pr), (cx + pr, cy + pr)],
                          outline=st["accent"] + (pa,), width=5)
        elif typ == "countup":
            # v1.1: big number counts 0 -> target with expo easing
            target = float(shp.get("target", 100))
            dur = shp.get("dur", 70)
            t2 = clamp01((f - start) / dur)
            val = target * expo_out(t2)
            dec = shp.get("decimals", 0)
            num = f"{val:,.{dec}f}".replace(",", ".")  # id-ID thousands sep
            txt = f"{shp.get('prefix', '')}{num}{shp.get('suffix', '')}"
            nf = font(st["font_hero"], shp.get("font_size", 130))
            nw, nh = text_size(d, txt, nf)
            d.text((cx - nw / 2, cy - nh / 2), txt, font=nf,
                   fill=st[shp.get("color", "accent")] + (alpha,),
                   stroke_width=0)  # v3.1 outline dihapus (owner 26 Okt 2026)
            label = shp.get("label")
            if label:
                lf = font(st["font_body"], 40)
                lw2, _ = text_size(d, label, lf)
                d.text((cx - lw2 / 2, cy + nh / 2 + 52), label, font=lf,
                       fill=st["ink_dim"] + (alpha,))
        img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
        return img

    def _draw_headline_scramble(self, img, d, hf, lines, y0, line_h, f,
                                space_w):
        """v1.1: decode/scramble entrance — characters flicker through random
        glyphs, then lock in left-to-right, word by word."""
        st = self.st
        for li, line in enumerate(lines):
            widths = [text_size(d, w, hf)[0] for w in line]
            lw = sum(widths) + space_w * (len(line) - 1)
            x = (self.W - lw) / 2
            y = y0 + li * line_h
            for wi, w in enumerate(line):
                is_accent = w.strip(".,!?").upper() in self.accent_words
                base = 14 + (li * 10 + wi) * 3
                cx = x
                for ci, ch in enumerate(w):
                    cw, _ = text_size(d, ch, hf)
                    lock = base + ci * 2
                    if f < lock - 10:
                        cx += cw
                        continue
                    if f < lock:
                        # deterministic flicker per char + frame pair
                        r = (ci * 31 + wi * 17 + li * 7 + (f // 2) * 13)
                        show = SCRAMBLE_CHARS[r % len(SCRAMBLE_CHARS)]
                        col = st["ink_dim"]
                        yo = 0
                    else:
                        show = ch
                        col = st["accent"] if is_accent else st["ink"]
                        e = expo_out(clamp01((f - lock) / 10))
                        yo = int(24 * (1 - e))
                    alpha = int(255 * clamp01((f - (lock - 10)) / 10))
                    if ch != " " and alpha > 0:
                        tmp = Image.new("RGBA", (int(cw) + 24,
                                                int(line_h * 1.7)),
                                        (0, 0, 0, 0))
                        td = ImageDraw.Draw(tmp)
                        td.text((12, int(line_h * 0.55)), show, font=hf,
                                fill=col + (alpha,),
                                stroke_width=0)  # v3.1 outline dihapus (owner 26 Okt 2026)
                        img.paste(tmp, (int(cx - 12),
                                        int(y + yo - line_h * 0.55)), tmp)
                    cx += cw
                x += widths[wi] + space_w
        return img

    def _camera_transform(self, frame_img, f):
        """Camera punch per skill §3.2: small punch on every cut, alternate."""
        W, H = self.W, self.H
        n = self.frames
        t = clamp01(f / max(n - 1, 1))
        if self.camera == "static":
            return frame_img
        if self.st.get("skill_v2"):
            # skill Punch: spring 1.09->1 + rotate +-1.1deg (arah bergantian)
            # + deblur 9->0 selama 16f pertama. Full-frame rise TIDAK dipakai:
            # menggeser frame akan membuka celah di tepi (PIL compositing).
            p = spring_p(f, self.fps)
            if self.camera == "punch-in":
                scale = 1.09 - 0.09 * p
                angle = (1.1 if self.flip else -1.1) * (1 - p)
            elif self.camera == "punch-out":
                scale = 1.0 + 0.09 * p
                angle = (-1.1 if self.flip else 1.1) * (1 - p)
            else:  # drift: lateral glide (skill: slow move antar detail)
                scale = 1.06
                angle = 0
            if f < 16:
                frame_img = frame_img.filter(
                    ImageFilter.GaussianBlur(radius=9 * (1 - f / 16)))
        elif self.camera == "punch-in":
            scale = 1.09 - 0.09 * expo_out(t)
            angle = 0.6 * (1 - expo_out(t))
        elif self.camera == "punch-out":
            scale = 1.0 + 0.09 * expo_out(t)
            angle = -0.6 * (1 - expo_out(t))
        elif self.camera == "drift":
            scale = 1.06
            angle = 0
        else:
            return frame_img
        # scale + slight rotate around center
        nw, nh = int(W * scale), int(H * scale)
        img = frame_img.resize((nw, nh), Image.LANCZOS)
        if angle:
            img = img.rotate(angle, resample=Image.BICUBIC, expand=False)
        x = (img.width - W) // 2
        y = (img.height - H) // 2
        if self.camera == "drift":
            x = int(x + 30 * t)
        return img.crop((x, y, x + W, y + H))

    def render_frame(self, f):
        st, W, H, fps = self.st, self.W, self.H, self.fps
        img = self._bg_frame(f)
        # insert mode: darken video slightly for text legibility, skip illustrations/shapes
        if self.is_insert:
            overlay = Image.new("RGB", (W, H), (0, 0, 0))
            img = Image.blend(img, overlay, 0.25)
        d = ImageDraw.Draw(img)
        n = self.frames
        # --- v2 kalbotau: hook card — kartu pertanyaan besar di awal scene
        hook = self.hook
        hook_frames = int(hook.get("frames", 60)) if hook else 0
        hook_active = bool(hook) and f < hook_frames

        # --- v2: illustration layers (PNG, style-matched) with entrances
        # (skipped in insert mode — the stock video is the hero)
        if not self.is_insert and not hook_active:
            for ill in self.sc.get("illustrations", []):
                img = self._draw_illustration(img, ill, f)

            # --- v2: vector shapes (bars, rings, arrows)
            for shp in self.sc.get("shapes", []):
                img = self._draw_shape(img, shp, f)
        # --- v2 kalbotau: karakter pemandu (persisten, semua scene)
        if self.character and not self.is_insert:
            img = self._draw_illustration(
                img, dict(self.character, entrance="fade", start=10,
                          motion="none"), f)
        d = ImageDraw.Draw(img)

        # --- kamera HANYA untuk latar/ilustrasi (perintah owner 29 Okt 2026:
        # subtitle harus di zona aman) — transformasi kamera dipindah ke
        # sini, SEBELUM teks digambar, supaya teks (kicker, headline, body,
        # hook, panel) selalu menempel di zona aman 64..1016 dan tidak ikut
        # terdorong kamera (terbukti probe: punch-out/drift mendorong teks
        # ke x~8..46 / ~1035..1059). Sebelumnya kamera di akhir render_frame.
        img = self._camera_transform(img, f)
        d = ImageDraw.Draw(img)

        # --- kicker (mono, tracked, top) — enters first
        if self.kicker:
            kf = font(st["font_mono"], 34)
            if st.get("skill_v2") and " — " in self.kicker:
                # skill Kicker: index (accent, bold) + hairline 0->120px
                # (f 4..26) + label tracked-out — satu baris, tanpa rise.
                kfb = font(st.get("font_mono_bold", st["font_mono"]), 34)
                idx_s, label_s = self.kicker.split(" — ", 1)
                kt = clamp01(f / 16)
                alpha = int(255 * kt)
                if alpha > 0:
                    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                    od = ImageDraw.Draw(ov)
                    x0, ky = 80, 150
                    iw, _ = text_size(od, idx_s, kfb)
                    od.text((x0, ky), idx_s, font=kfb,
                            fill=st["accent"] + (alpha,))
                    lx = x0 + iw + 18
                    # zona aman: label dipotong dari kanan bila melewati
                    # x=1016 (terukur: "003 — EKSPERIMEN SELAI IYENGAR"
                    # -> x=1027 tanpa potong)
                    label_s = _fit_tracked(od, label_s, kf, 10,
                                           lx + 120 + 18, SAFE_R)
                    lw_anim = int(120 * clamp01((f - 4) / 22))
                    if lw_anim > 0:
                        od.line([(lx, ky + 17), (lx + lw_anim, ky + 17)],
                                fill=st["ink_dim"] + (int(alpha * 0.7),),
                                width=2)
                    draw_tracked(od, (lx + lw_anim + 18, ky), label_s, kf,
                                 st["ink_dim"] + (alpha,), tracking=10)
                    img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
                    d = ImageDraw.Draw(img)
            else:
                kt = clamp01((f - 4) / 18)
                ky = int(150 - 40 * (1 - expo_out(kt)))
                alpha = int(255 * kt)
                if alpha > 0:
                    # draw on overlay for fade
                    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                    od = ImageDraw.Draw(ov)
                    # zona aman: kicker mulai x=110 (bukan 80) — kamera
                    # lama settle lambat (zoom 1.09x di awal scene) dan
                    # menggeser kicker ke x~47 di f=30 bila mulai dari 80
                    # (terukur: BOCOR 315px kiri + 12px kanan di f=30)
                    kicker_fit = _fit_tracked(od, self.kicker, kf, 8,
                                              110, SAFE_R)
                    draw_tracked(od, (110, ky), kicker_fit, kf,
                                 st[st.get("kicker_ink", "ink_dim")] + (alpha,),
                                 tracking=8)
                    # hairline rule
                    od.line([(110, ky + 52), (W - 110, ky + 52)],
                            fill=st["grid"] + (alpha,), width=2)
                    img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
                    d = ImageDraw.Draw(img)

        # --- headline layout: wrap, measure, auto-avoid lower content
        hf = font(st["font_hero"], st.get("hero_size", 84))
        words = [] if hook_active else self.words
        lines, line_h, total_h, y0 = [], 0, 0, 0
        if words:
            # measure total width for centering (two-line wrap if needed)
            # supports @@NL@@ as forced line break
            lines, cur, curw = [], [], 0
            for w in words:
                if "@@NL@@" in w:
                    # split on the marker: finish current line, start new
                    parts = w.split("@@NL@@")
                    for pi, part in enumerate(parts):
                        if pi > 0:
                            if cur:
                                lines.append(cur)
                            cur, curw = [], 0
                        if part:
                            ww, _ = text_size(d, part + " ", hf)
                            cur.append(part)
                            curw += ww
                    continue
                ww, _ = text_size(d, w + " ", hf)
                if curw + ww > W - 160 and cur:
                    lines.append(cur)
                    cur, curw = [], 0
                cur.append(w)
                curw += ww
            if cur:
                lines.append(cur)
            _, lh = text_size(d, "Ag", hf)
            line_h = int(lh * st.get("line_height", 1.25))
            total_h = line_h * len(lines)
            y0 = H // 2 - total_h // 2 - 40 + st.get("headline_dy", 0)
            # v1.1 auto-layout: keep the headline block clear of lower-half
            # shapes/illustrations (fixes headline colliding with bar charts)
            lower_tops = []
            for shp in self.sc.get("shapes", []):
                typ = shp.get("type")
                if typ == "pulse":
                    continue
                cy2 = shp.get("y", 0.62) * H
                if cy2 < 0.5 * H:
                    continue
                if typ == "bars":
                    lower_tops.append(cy2 - shp.get("maxh", 320))
                elif typ == "ring":
                    lower_tops.append(cy2 - shp.get("r", 130))
                elif typ == "countup":
                    lower_tops.append(cy2 - shp.get("font_size", 130))
                elif typ == "arrow":
                    lower_tops.append(cy2 - 80)
            for ill in self.sc.get("illustrations", []):
                cy2 = ill.get("y", 0.38) * H
                if cy2 >= 0.5 * H:
                    lower_tops.append(cy2 - ill.get("size", 500) / 2)
            if lower_tops:
                limit = min(lower_tops)
                if y0 + total_h + 70 > limit:
                    y0 = max(300, int(limit - total_h - 70))
            # v1.1 panel chrome behind the headline block
            if self.sc.get("panel"):
                pad = 48
                pt = clamp01(f / 20)
                pa = int(225 * pt)
                if pa > 0:
                    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                    od = ImageDraw.Draw(ov)
                    # zona aman: panel dijepit ke x=64..1016 (dulu 32..1048)
                    px0, px1 = max(SAFE_L, 80 - pad), min(SAFE_R, W - 80 + pad)
                    od.rounded_rectangle(
                        [(px0, y0 - pad), (px1, y0 + total_h + pad)],
                        radius=40, fill=st["surface"] + (pa,))
                    od.line([(px0 + 40, y0 - pad),
                             (px1 - 40, y0 - pad)],
                            fill=st["accent"] + (pa,), width=6)
                    tl = 34  # corner ticks (jangkar masuk 3px: garis
                    # width=5 berpusat di koordinat -> tepi luar 2px;
                    # tanpa inset, tick di px0/px1 bocor ke 62..1018)
                    for cx3, cy3, sx, sy in [
                            (px0 + 3, y0 - pad + 3, 1, 1),
                            (px1 - 3, y0 - pad + 3, -1, 1),
                            (px0 + 3, y0 + total_h + pad - 3, 1, -1),
                            (px1 - 3, y0 + total_h + pad - 3, -1, -1)]:
                        od.line([(cx3, cy3), (cx3 + sx * tl, cy3)],
                                fill=st["accent"] + (pa,), width=5)
                        od.line([(cx3, cy3), (cx3, cy3 + sy * tl)],
                                fill=st["accent"] + (pa,), width=5)
                    img = Image.alpha_composite(img.convert("RGBA"),
                                                ov).convert("RGB")
                    d = ImageDraw.Draw(img)

        # --- headline: kinetic entrances (words | scramble)
        space_w, _ = text_size(d, " ", hf)
        if words and self.sc.get("headline_entrance") == "scramble":
            img = self._draw_headline_scramble(img, d, hf, lines, y0,
                                               line_h, f, space_w)
            d = ImageDraw.Draw(img)
        elif words:
            for li, line in enumerate(lines):
                widths = [text_size(d, w, hf)[0] for w in line]
                # v2.1 (28 Okt 2026, port dari video tes #13): centering
                # dua-pass — skala kata (slam aksen 1.3x, pulse highlight
                # 1.14x) menggeser kata berikut ke kanan (x += ww*sc), jadi
                # baris lebar terpotong tepi frame saat kata disorot
                # (terukur di hedonic v1: "LOTRE" E & "PROSES" S terpotong,
                # x=1079; S1/S2 juga menyentuh tepi). Pass 1 hitung kinetika
                # tiap kata, cap lebar total ter-scale, lalu pusatkan dari
                # lebar itu — teks tidak pernah keluar frame; font/gerak sama.
                kin = []
                for wi, w in enumerate(line):
                    # skill Kinetic: stagger ~4f per kata, indeks FLAT
                    # (dulu li*10+wi: baris 2 telat 40f/1,3 dtk)
                    gi = (sum(len(l) for l in lines[:li]) + wi
                          if st.get("skill_v2") else li * 10 + wi)
                    start = 14 + gi * 4  # stagger ~4f per skill §4.2
                    t = clamp01((f - start) / st.get("word_dur", 16))
                    is_accent = w.strip(".,!?").upper() in self.accent_words
                    sc, e, yo, hl = 1.0, 0.0, 0, 0.0
                    if t > 0:
                        if is_accent:
                            # slam: scale 1.3 -> 1 with overshoot
                            e = ease_out_back(min(t * 1.4, 1.0))
                            sc = 1.3 - 0.3 * e
                            yo = int(-30 * (1 - e))
                        else:
                            e = expo_out(t)
                            # skill Kinetic: rise 34px (dulu 60)
                            yo = int(st.get("word_rise", 60) * (1 - e))
                        # v3: continuous kinetic life after entrance — the
                        # headline never sits fully static: gentle float on all
                        # words + subtle pulse on accent words
                        if t >= 1.0:
                            yo += int(6 * math.sin(2 * math.pi * f / 90))
                            if is_accent:
                                sc *= 1.0 + 0.02 * math.sin(2 * math.pi * f / 75)
                        # v3 word_highlight: kata yang sedang diucapkan VO
                        # membesar + disorot mengikuti VO (flat index semua kata headline)
                        if self.word_highlight:
                            hi = sum(len(l) for l in lines[:li]) + wi
                            n_hl = sum(len(l) for l in lines)
                            hl = self._hl(f, hi, n_hl, 14)
                        if hl > 0:
                            sc *= 1.0 + 0.14 * hl
                            yo -= int(12 * hl)
                    kin.append((t, e, sc, yo, hl, is_accent))
                lw = sum(widths[i] * kin[i][2] for i in range(len(line))) \
                    + space_w * (len(line) - 1)
                # cap lebar ter-scale (dua-pass v2): 900px kamera skill_v2
                # (spring settle ~30f), 840px kamera lama (transien zoom)
                cap_w = (HEADLINE_MAX_W if st.get("skill_v2")
                         else HEADLINE_MAX_W_OLD_CAM)
                if lw > cap_w:  # kotak aksen (+12px/sisi, slam s.d. 1.3x)
                    # membawa tepi visual ke ~74..1006, di dalam zona aman
                    cap_k = cap_w / lw
                    kin = [(t, e, sc * cap_k, yo, hl, acc)
                           for (t, e, sc, yo, hl, acc) in kin]
                    lw = float(cap_w)
                x = (W - lw) / 2
                y = y0 + li * line_h
                for wi, w in enumerate(line):
                    ww = widths[wi]
                    t, e, sc, yo, hl, is_accent = kin[wi]
                    if t <= 0:
                        x += ww * sc + space_w
                        continue
                    # kalbotau (hl_box): sorot = KOTAK BIRU + teks putih,
                    # bukan teks berubah warna (cinematic: blend ke amber)
                    hl_box = bool(st.get("hl_box"))
                    box_a = 0
                    if hl_box:
                        if is_accent:
                            box_a = int(255 * min(t * 2, 1))
                        elif hl > 0:
                            # v2 kalbotau (hl_solid): kotak langsung solid,
                            # bukan ramp pucat — referensi: kotak biru solid
                            box_a = (255 if hl > 0.3 else int(255 * hl / 0.3)
                                     if st.get("hl_solid") else int(255 * hl))
                            # v2 kalbotau (hl_solid): kata tanpa huruf/angka
                            # (mis. "+") tidak dikotak — sama seperti aturan body
                            if st.get("hl_solid") and not any(c.isalnum() for c in w):
                                box_a = 0
                    if hl_box and box_a > 0:
                        fill = (255, 255, 255)
                    elif is_accent:
                        fill = st["accent"]
                    elif hl > 0:
                        fill = _blend(st["ink"], st["accent"], hl)
                    else:
                        fill = st["ink"]
                    # render word to temp canvas for scaling + alpha
                    tmp = Image.new("RGBA", (int(ww * 1.6) + 24, lh + 90),
                                    (0, 0, 0, 0))
                    td = ImageDraw.Draw(tmp)
                    if hl_box and box_a > 0:
                        # kotak mengikuti bbox tinta kata itu sendiri (bukan
                        # tebakan tinggi font) — kalau tidak, kotak memotong huruf
                        bb = td.textbbox((12, 45), w, font=hf)
                        td.rounded_rectangle([(bb[0] - 12, bb[1] - 10),
                                              (bb[2] + 12, bb[3] + 10)],
                                             radius=16, fill=st["accent"] + (box_a,))
                    td.text((12, 45), w, font=hf,
                            fill=fill + (int(255 * min(t * 2, 1)),),
                            stroke_width=0)  # v3.1 outline dihapus (owner 26 Okt 2026)
                    if st.get("word_deblur") and t < 1:
                        # skill Kinetic: blur 10->0 saat kata masuk
                        tmp = tmp.filter(ImageFilter.GaussianBlur(
                            radius=10 * (1 - min(e, 1.0))))
                    if abs(sc - 1.0) > 0.01:
                        tmp = tmp.resize((max(int(tmp.width * sc), 1),
                                          max(int(tmp.height * sc), 1)),
                                         Image.LANCZOS)
                    # v1.1 fix: align the word's *visual* left edge to x and
                    # advance by visual width (old code used the padded canvas
                    # width, which stretched word spacing ~60% too wide)
                    img.paste(tmp, (int(x - 12 * sc), int(y + yo - 45)), tmp)
                    x += ww * sc + space_w
            d = ImageDraw.Draw(img)

        # --- body lines: staggered rise+fade, dimmer
        bf = font(st["font_body"], st.get("body_size", 44))
        if self.word_highlight and not hook_active:
            # v3: body kata-per-kata, disorot mengikuti VO (flat index
            # semua kata body; jendela mulai frame 30 = entrance baris 1)
            body_words = [w for ln in self.body_lines for w in ln.split()]
            n_b = len(body_words)
            bi_flat = 0
            for bi, line in enumerate(self.body_lines):
                if not line.strip():
                    continue
                words_b = line.split()
                widths_b = [text_size(d, w, bf)[0] for w in words_b]
                space_b, _ = text_size(d, " ", bf)
                lw_b = sum(widths_b) + space_b * (len(words_b) - 1)
                x_b = (W - lw_b) / 2
                y_b = H - 560 + st.get("body_dy", 0) + bi * 70
                start_b = 30 + bi * 10
                t_b = clamp01((f - start_b) / 18)
                if t_b <= 0:
                    bi_flat += len(words_b)
                    continue
                e_b = expo_out(t_b)
                yo_b = int(40 * (1 - e_b))
                if t_b >= 1.0:
                    yo_b += int(6 * math.sin(2 * math.pi * f / 90))
                alpha_b = int(255 * min(t_b * 1.6, 1))
                for wj, w in enumerate(words_b):
                    ww_b = widths_b[wj]
                    hl_b = self._hl(f, bi_flat, n_b, 30)
                    bi_flat += 1
                    # kalbotau (hl_box): sorot = KOTAK BIRU + teks putih;
                    # kata yang hanya tanda baca (mis. "—") TIDAK dikotak —
                    # kotaknya jadi pil kecil berisi garis, terlihat seperti bug
                    if st.get("hl_box"):
                        if any(c.isalnum() for c in w):
                            # v2 kalbotau (hl_solid): kotak langsung solid
                            box_b = (255 if hl_b > 0.3 else int(255 * hl_b / 0.3)
                                     if st.get("hl_solid") else int(255 * hl_b))
                        else:
                            box_b = 0
                        fill_b = (255, 255, 255) if box_b > 0 else st["ink"]
                    else:
                        box_b = 0
                        fill_b = _blend(st["ink_dim"], st["accent"], hl_b)
                    sc_b = 1.0 + 0.10 * hl_b
                    tmp_b = Image.new("RGBA", (int(ww_b * 1.6) + 24, 150),
                                      (0, 0, 0, 0))
                    td_b = ImageDraw.Draw(tmp_b)
                    if box_b > 0:
                        bb_b = td_b.textbbox((12, 45), w, font=bf)
                        td_b.rounded_rectangle([(bb_b[0] - 10, bb_b[1] - 8),
                                                (bb_b[2] + 10, bb_b[3] + 8)],
                                               radius=12, fill=st["accent"] + (box_b,))
                    td_b.text((12, 45), w, font=bf, fill=fill_b + (alpha_b,),
                              stroke_width=0)  # v3.1 outline dihapus (owner 26 Okt 2026)
                    if abs(sc_b - 1.0) > 0.01:
                        tmp_b = tmp_b.resize(
                            (max(int(tmp_b.width * sc_b), 1),
                             max(int(tmp_b.height * sc_b), 1)), Image.LANCZOS)
                    img.paste(tmp_b, (int(x_b - 12 * sc_b),
                                      int(y_b + yo_b - 45)), tmp_b)
                    # v2 kalbotau (hl_solid): kata yang dikotak dapat ruang
                    # ekstra — kotak (padding 10px/sisi) menabrak kata berikut
                    x_b += ww_b * sc_b + space_b + (12 if box_b > 0 and st.get("hl_solid") else 0)
            d = ImageDraw.Draw(img)
        elif not hook_active:
            for bi, line in enumerate(self.body_lines):
                if not line.strip():
                    continue
                start = 30 + bi * 10
                t = clamp01((f - start) / 18)
                if t <= 0:
                    continue
                e = expo_out(t)
                yo = int(40 * (1 - e))
                # v3: body breathes with the headline (same float phase)
                if t >= 1.0:
                    yo += int(6 * math.sin(2 * math.pi * f / 90))
                alpha = int(255 * min(t * 1.6, 1))
                ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                od = ImageDraw.Draw(ov)
                draw_text_center(od, W / 2, H - 560 + st.get("body_dy", 0) + bi * 70 + yo, line, bf,
                                 st["ink_dim"] + (alpha,), stroke=0)
                img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")

        # --- hook card (kalbotau v2): pertanyaan besar, kata kunci dikotak
        if hook_active:
            hlines = hook["text"].split("@@NL@@")
            hacc = set(w.strip().strip(".,!?").upper()
                       for w in hook.get("accent", []))
            hf2 = font(st["font_hero"], st.get("hook_size", 100))
            _, lh2 = text_size(d, "Ag", hf2)
            lh2 = int(lh2 * 1.25)
            y2 = H // 2 - (lh2 * len(hlines)) // 2 - 60
            gi2 = 0
            for li2, hline in enumerate(hlines):
                hwords = hline.split()
                widths2 = [text_size(d, w, hf2)[0] for w in hwords]
                sp2, _ = text_size(d, " ", hf2)
                lw2 = sum(widths2) + sp2 * (len(hwords) - 1)
                cap_w2 = (HEADLINE_MAX_W if st.get("skill_v2")
                          else HEADLINE_MAX_W_OLD_CAM)
                if lw2 > cap_w2:  # zona aman: sempitkan font
                    # supaya baris hook (+ kotak aksen) muat x=64..1016
                    hf2 = font(st["font_hero"], max(
                        24, int(st.get("hook_size", 100)
                                * cap_w2 / lw2)))
                    widths2 = [text_size(d, w, hf2)[0] for w in hwords]
                    sp2, _ = text_size(d, " ", hf2)
                    lw2 = sum(widths2) + sp2 * (len(hwords) - 1)
                x2 = (W - lw2) / 2
                y = y2 + li2 * lh2
                for wi2, w2 in enumerate(hwords):
                    ww2 = widths2[wi2]
                    start2 = 10 + gi2 * 5
                    gi2 += 1
                    t2 = clamp01((f - start2) / 16)
                    if t2 <= 0:
                        x2 += ww2 + sp2
                        continue
                    is_acc2 = w2.strip(".,!?").upper() in hacc
                    if is_acc2:
                        e2 = ease_out_back(min(t2 * 1.4, 1.0))
                        sc2 = 1.3 - 0.3 * e2
                        yo2 = int(-30 * (1 - e2))
                    else:
                        e2 = expo_out(t2)
                        sc2 = 1.0
                        yo2 = int(60 * (1 - e2))
                    box2 = int(255 * min(t2 * 2, 1)) if is_acc2 else 0
                    fill2 = (255, 255, 255) if box2 > 0 else st["ink"]
                    tmp2 = Image.new("RGBA", (int(ww2 * 1.6) + 24, lh2 + 90),
                                     (0, 0, 0, 0))
                    td2 = ImageDraw.Draw(tmp2)
                    if box2 > 0:
                        bb2 = td2.textbbox((12, 45), w2, font=hf2)
                        td2.rounded_rectangle(
                            [(bb2[0] - 12, bb2[1] - 10),
                             (bb2[2] + 12, bb2[3] + 10)],
                            radius=18, fill=st["accent"] + (box2,))
                    td2.text((12, 45), w2, font=hf2,
                             fill=fill2 + (int(255 * min(t2 * 2, 1)),),
                             stroke_width=0)
                    if abs(sc2 - 1.0) > 0.01:
                        tmp2 = tmp2.resize(
                            (max(int(tmp2.width * sc2), 1),
                             max(int(tmp2.height * sc2), 1)), Image.LANCZOS)
                    img.paste(tmp2, (int(x2 - 12 * sc2), int(y + yo2 - 45)), tmp2)
                    x2 += ww2 * sc2 + sp2
            d = ImageDraw.Draw(img)

        # --- exit choreography (last 12f): lift + fade, faster than entrance
        # no_exit_fade (proyek reaktif): hard cut, tanpa fade keluar
        exit_f = 0 if self.sc.get("no_exit_fade") else 12
        if exit_f and f >= n - exit_f:
            et = (f - (n - exit_f)) / exit_f
            img = img.filter(ImageFilter.GaussianBlur(radius=et * 5))
            ov = Image.new("RGBA", (W, H), (0, 0, 0, int(200 * et)))
            img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")

        img = add_grain(img, amount=5, seed=f)  # film grain per skill
        return img


def whip_transition(style, W, H, fps, direction=1):
    """20-frame whip overlay: accent band sweeps vertically, white flash on cut."""
    frames = []
    accent = style["accent"]
    for f in range(20):
        t = f / 19
        img = Image.new("RGB", (W, H), (0, 0, 0))
        d = ImageDraw.Draw(img)
        # band position: sweeps top->bottom, cut lands mid-sweep (frame 10)
        band_y = int(t * (H + 400) - 200)
        d.rectangle([(0, band_y - 90), (W, band_y + 90)], fill=accent)
        if 9 <= f <= 11:  # white flash exactly on cut
            img = Image.new("RGB", (W, H), (255, 255, 255))
        frames.append(img)
    return frames


def main():
    if len(sys.argv) < 4 or sys.argv[2] != "-o":
        print(__doc__)
        sys.exit(1)
    with open(sys.argv[1]) as fh:
        proj = json.load(fh)
    out = sys.argv[3]
    style = STYLES.get(proj.get("style", "cinematic"), STYLES["cinematic"])
    fps = proj.get("fps", 30)
    W, H = proj.get("width", 1080), proj.get("height", 1920)

    import tempfile
    # tmpdir bisa di-override per proyek (default render-frames). Proyek
    # reaktif memakai tmpdir sendiri supaya tidak bentrok dengan serial #11
    # (run 17:09 WIB) yang memakai tmpdir default.
    tmpdir = proj.get("tmpdir") or os.path.join(os.path.expanduser("~"), "workspace",
                          "motion-video-projects", "engine", "render-frames")
    os.makedirs(tmpdir, exist_ok=True)
    # clear previous frames
    for fn in os.listdir(tmpdir):
        try:
            os.remove(os.path.join(tmpdir, fn))
        except OSError:
            pass
    ext = "jpg"  # JPEG: /tmp is only 512MB, PNG frames don't fit
    frame_idx = 0
    audio_inputs = []   # (path, start_sec)
    sfx_events = []     # (frame, path)
    t = 0.0

    # v1.1: resolve sfx + bed through the fuzzy asset resolver
    sfx = {k: _resolve(v) for k, v in proj.get("sfx", {}).items()}
    bed_path = _resolve(proj.get("bed"))

    cameras = ["punch-in", "punch-out", "punch-in", "drift", "punch-out"]
    for si, sc in enumerate(proj["scenes"]):
        sc = dict(sc)
        sc.setdefault("camera", cameras[si % len(cameras)])
        sc["flip"] = bool(si % 2)  # skill Punch: arah rotasi bergantian per scene
        sc.setdefault("kicker", f"{si + 1:03d} — BEAT")
        # opsi per proyek -> tiap scene (backward-compatible, default lama)
        if proj.get("no_exit_fade"):
            sc["no_exit_fade"] = True
        if proj.get("word_highlight"):
            sc["word_highlight"] = True
        if proj.get("character"):
            sc["character"] = proj["character"]
        if proj.get("tail_frames") is not None:
            sc.setdefault("tail_frames", proj["tail_frames"])
        # Ken Burns (BRD-005): project-level flag -> tiap scene.
        # Default False; diubah ke True HANYA atas persetujuan owner
        # setelah QA satu episode penuh.
        if proj.get("illustration_motion"):
            sc.setdefault("illustration_motion", True)
        # override style per scene (mis. beyond-dark untuk hook & penutup)
        scene_style = style
        if sc.get("style"):
            scene_style = dict(style)
            scene_style.update(STYLES.get(sc["style"], {}))
        r = SceneRenderer(sc, scene_style, fps, W, H)
        start_frame = frame_idx
        for f in range(r.frames):
            img = r.render_frame(f)
            img.save(f"{tmpdir}/f{frame_idx:06d}.jpg", quality=88)
            frame_idx += 1
        if sc.get("vo"):
            audio_inputs.append((sc["vo"], t))
        # SFX: whoosh on cut, impact on headline land (~frame 18)
        # (skipped entirely when project sets no_transitions)
        no_trans = bool(proj.get("no_transitions"))
        if not no_trans:
            if sfx.get("whoosh"):
                sfx_events.append((start_frame, sfx["whoosh"]))
            if sfx.get("impact"):
                sfx_events.append((start_frame + 18, sfx["impact"]))
        t += r.frames / fps
        # whip transition between scenes (except after last)
        # no_transitions -> hard cut, no extra frames, no SFX
        if si < len(proj["scenes"]) - 1 and not no_trans:
            for wf in whip_transition(style, W, H, fps):
                wf.save(f"{tmpdir}/f{frame_idx:06d}.jpg", quality=88)
                frame_idx += 1
            t += 20 / fps
            if sfx.get("whoosh"):
                sfx_events.append((frame_idx - 10, sfx["whoosh"]))

    total_dur = frame_idx / fps
    # --- assemble with ffmpeg
    cmd = ["ffmpeg", "-y", "-framerate", str(fps), "-i",
           f"{tmpdir}/f%06d.jpg"]
    # audio inputs: VO clips at offsets + sfx events + bed
    amix_inputs = []
    idx = 1
    vo_labels = []
    for path, start in audio_inputs:
        cmd += ["-i", path]
        # delay to start offset
        ms = int(start * 1000)
        # Mix TERKUNCI (owner 2026-10-31 18:23): VO -15 LUFS (loudnorm
        # SEBELUM adelay — pelajaran AGENTS.md), bed -34 LUFS di bawah.
        vo_labels.append(f"[{idx}:a]loudnorm=I=-15:TP=-1.0:LRA=11,adelay={ms}|{ms}[v{idx}]")
        idx += 1
    sfx_labels = []
    for fr, path in sfx_events:
        cmd += ["-i", path]
        ms = int(fr / fps * 1000)
        sfx_labels.append(f"[{idx}:a]adelay={ms}|{ms},volume=0.3[s{idx}]")
        idx += 1
    bed_label = ""
    if bed_path and os.path.exists(bed_path):
        cmd += ["-stream_loop", "-1", "-i", bed_path]
        bed_label = (f"[{idx}:a]atrim=0:{total_dur:.2f},volume=0.12,"
                     f"loudnorm=I=-34:TP=-2:LRA=11[bed]")
        idx += 1
    # mix
    all_labels = [f"[v{i}]" for i in range(1, len(vo_labels) + 1)]
    all_labels += [f"[s{i}]" for i in range(len(vo_labels) + 1,
                                            len(vo_labels) + len(sfx_labels) + 1)]
    filter_parts = vo_labels + sfx_labels
    if bed_label:
        filter_parts.append(bed_label)
        all_labels.append("[bed]")
    filter_parts.append(
        f"{''.join(all_labels)}amix=inputs={len(all_labels)}:duration=longest:"
        f"normalize=0,"
        f"atrim=0:{total_dur:.2f}[aout]")
    cmd += ["-filter_complex", ";".join(filter_parts),
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
            "-c:a", "aac", "-shortest", out]
    print("assembling", frame_idx, "frames ...")
    subprocess.run(cmd, check=True)
    print("done:", out)


if __name__ == "__main__":
    main()
