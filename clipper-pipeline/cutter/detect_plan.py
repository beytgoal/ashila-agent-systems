#!/usr/bin/env python3
"""Face tracking untuk crop vertikal 9:16 — sisi deteksi + lintasan.

Dipanggil oleh cutter (cutter_hd.py --facetrack / cutter.py --facetrack)
sebagai subprocess dengan interpreter venv-face (MediaPipe di dalamnya);
cutter sendiri berjalan di python3 sistem yang tidak punya mediapipe/cv2.

Alur:
  1. Ekstrak frame sampel dari segmen klip (ffmpeg, laju --fps sampel/dtk).
  2. Deteksi wajah tiap frame: MediaPipe Face Detection (blaze face,
     model full-range). Fallback berantai bila mediapipe tidak bisa
     diimpor: OpenCV DNN (model res10 SSD, diunduh sekali ke folder ini)
     lalu Haar cascade bawaan cv2. Backend yang dipakai dicatat di JSON.
  2b. Jangkar BADAN untuk sampel TANPA wajah (perintah owner 31 Okt
     2026 22:02 WIB: tracking wajah DAN badan): MediaPipe Pose
     Landmarker (model pose_landmarker_lite.task resmi MediaPipe;
     jangkar x = titik tengah bahu), fallback OpenCV HOG person
     detector. Badan hanya mengisi sampel yang wajahnya kosong —
     wajah tetap jangkar utama selama terdeteksi.
  3. Pilih wajah target per sampel: wajah terbesar, dengan preferensi
     kontinuitas (wajah dekat pusat track saat ini menang kecuali ada
     wajah lain >1,8x lebih besar pada 2 sampel berurutan = ganti
     pembicara). Tanpa wajah: tahan posisi terakhir (atau tengah).
  4. KUNCI crop per SHOT (perintah owner 4 Nov 2026: "face & body
     tracking jangan berpindah-pindah; berpindah hanya ketika
     b-roll"): shot dipisah oleh batas visual (frame-diff antar frame
     sampel — potongan keras / dissolve / ganti kamera), lalu crop_x
     dikunci SATU nilai per shot = median target shot itu. Di dalam
     satu shot crop TIDAK bergerak sama sekali; reposisi hanya
     terjadi tepat di batas shot, bersamaan dengan potongan gambar
     sumbernya sendiri. (Desain lama — lintasan halus median-3 ->
     eksponensial -> clamp kecepatan — membuat crop terus bergeser
     mengikuti gerakan kecil subjek dan ditolak owner.)
  5. Tulis crop plan JSON: [{t0, t1, crop_x}] waktu relatif klip (detik),
     crop_x dalam piksel sumber (genap, ter-clamp ke frame).

Penggunaan:
  detect_plan.py --video SRC --start 956.5 --end 1016.3 \
      --out plan.json --frames-dir frames/ --fps 2
"""
import argparse
import json
import math
import os
import subprocess
import sys
import urllib.request


def _ensure_egl_on_path():
    """VM ini tidak punya libEGL.so.1 sistem (repo apt di VM tidak
    menyediakan paket libegl1); salinan hasil ekstrak .deb Ubuntu noble
    disimpan di <venv>/egllibs. MediaPipe Tasks membutuhkannya saat
    model dimuat — bila belum terjangkau loader, re-exec proses ini
    sekali dengan LD_LIBRARY_PATH yang sudah ditambah."""
    if os.environ.get("_FACETRACK_EGL_DONE"):
        return
    try:
        import ctypes
        # WAJIB cek keduanya: di VM ini libEGL.so.1 bisa ter-resolve
        # dari jalur lain sementara libGLESv2.so.2 tidak — probe satu
        # library saja memberi rasa aman palsu dan MediaPipe tetap
        # gagal dimuat (terbukti di render uji pertama: fallback diam-
        # diam ke OpenCV).
        ctypes.CDLL("libEGL.so.1")
        ctypes.CDLL("libGLESv2.so.2")
        return  # keduanya tersedia dari sistem / env
    except OSError:
        pass
    venv_root = os.path.dirname(
        os.path.dirname(os.path.abspath(sys.executable)))
    libs = os.path.join(venv_root, "egllibs")
    if os.path.exists(os.path.join(libs, "libEGL.so.1")):
        env = dict(os.environ)
        old = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = libs + ((":" + old) if old else "")
        env["_FACETRACK_EGL_DONE"] = "1"
        os.execvpe(sys.executable, [sys.executable] + sys.argv, env)


_ensure_egl_on_path()

HERE = os.path.dirname(os.path.abspath(__file__))
MP_MODEL = os.path.join(HERE, "blaze_face_short_range.tflite")
MP_MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/"
                "face_detector/blaze_face_short_range/float16/1/"
                "blaze_face_short_range.tflite")
POSE_MODEL = os.path.join(HERE, "pose_landmarker_lite.task")
POSE_MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/"
                  "pose_landmarker/pose_landmarker_lite/float16/1/"
                  "pose_landmarker_lite.task")
YUNET_MODEL = os.path.join(HERE, "face_detection_yunet_2023mar.onnx")
YUNET_URL = ("https://github.com/opencv/opencv_zoo/raw/main/models/"
             "face_detection_yunet/face_detection_yunet_2023mar.onnx")
HAAR_MODEL = os.path.join(HERE, "haarcascade_frontalface_default.xml")
HAAR_URL = ("https://raw.githubusercontent.com/opencv/opencv/master/data/"
            "haarcascades/haarcascade_frontalface_default.xml")


def extract_frames(video, start, end, fps, frames_dir):
    os.makedirs(frames_dir, exist_ok=True)
    pattern = os.path.join(frames_dir, "f_%05d.jpg")
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-ss", f"{start:.3f}", "-to", f"{end:.3f}", "-i", video,
        "-vf", f"fps={fps}", "-q:v", "3", pattern,
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg ekstrak frame gagal: {proc.stderr[:300]}")
    files = sorted(f for f in os.listdir(frames_dir) if f.endswith(".jpg"))
    return [os.path.join(frames_dir, f) for f in files]


def _ensure_mp_model():
    if not os.path.exists(MP_MODEL):
        urllib.request.urlretrieve(MP_MODEL_URL, MP_MODEL)


def detect_mediapipe(frames):
    """MediaPipe FaceDetector (Tasks API, model BlazeFace short-range).

    mediapipe versi baru (0.10.35+/1.x) TIDAK lagi menyediakan API
    legacy mp.solutions — jalur resminya kini Tasks API dengan file
    model .tflite (diunduh sekali ke folder cutter). BlazeFace tetap
    detektor yang sama seperti yang dimaksud perintah owner
    ("pakai mediapipeline").
    """
    import cv2
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision

    _ensure_mp_model()
    options = vision.FaceDetectorOptions(
        base_options=mp_python.BaseOptions(model_asset_path=MP_MODEL),
        running_mode=vision.RunningMode.IMAGE,
        min_detection_confidence=0.33)
    faces_per_frame = []
    size = None
    with vision.FaceDetector.create_from_options(options) as det:
        for path in frames:
            img = cv2.imread(path)
            if img is None:
                faces_per_frame.append([])
                continue
            h, w = img.shape[:2]
            size = (w, h)
            # Upscale ke lebar ~1920: wajah di sumber 360p kecil
            # (~35-90 px — shot wide podcast bisa cuma ~35 px) dan
            # model short-range dirancang untuk wajah relatif besar
            # di frame; koordinat hasil diskala balik. Ambang 0,3:
            # pada 0,5 cakupan cuma 44% sampel di uji Peep Talk 360p.
            scale = max(1.0, 1920 / w)
            big = cv2.resize(img, (round(w * scale), round(h * scale)),
                             interpolation=cv2.INTER_LINEAR)
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB,
                              data=cv2.cvtColor(big, cv2.COLOR_BGR2RGB))
            res = det.detect(mp_img)
            faces = []
            for d in res.detections or []:
                bb = d.bounding_box
                faces.append({
                    "cx": (bb.origin_x + bb.width / 2) / scale,
                    "cy": (bb.origin_y + bb.height / 2) / scale,
                    "w": bb.width / scale, "h": bb.height / scale,
                    "score": float(d.categories[0].score)
                    if d.categories else 1.0,
                })
            faces_per_frame.append(faces)
    return faces_per_frame, size


def _download(url, path):
    if not os.path.exists(path):
        urllib.request.urlretrieve(url, path)


def detect_opencv_dnn(frames):
    """Fallback DNN: YuNet via cv2.FaceDetectorYN (ONNX, OpenCV Zoo).

    (Fallback lama res10 SSD Caffe tidak bisa dipakai lagi: OpenCV 5
    menghapus readNetFromCaffe.)
    """
    import cv2

    _download(YUNET_URL, YUNET_MODEL)
    faces_per_frame = []
    size = None
    det = None
    for path in frames:
        img = cv2.imread(path)
        if img is None:
            faces_per_frame.append([])
            continue
        h, w = img.shape[:2]
        size = (w, h)
        if det is None:
            det = cv2.FaceDetectorYN.create(
                YUNET_MODEL, "", (w, h), score_threshold=0.5,
                nms_threshold=0.3, top_k=50)
        det.setInputSize((w, h))
        _, found = det.detect(img)
        faces = []
        for row in found if found is not None else []:
            x, y, bw, bh = (float(v) for v in row[:4])
            faces.append({
                "cx": x + bw / 2, "cy": y + bh / 2,
                "w": bw, "h": bh, "score": float(row[-1]),
            })
        faces_per_frame.append(faces)
    return faces_per_frame, size


def detect_haar(frames):
    import cv2

    if os.path.exists(HAAR_MODEL):
        cascade_path = HAAR_MODEL
    else:
        try:
            _download(HAAR_URL, HAAR_MODEL)
            cascade_path = HAAR_MODEL
        except Exception:  # noqa: BLE001 — coba path bawaan cv2
            cascade_path = os.path.join(
                cv2.data.haarcascades,
                "haarcascade_frontalface_default.xml")
    cascade = cv2.CascadeClassifier(cascade_path)
    faces_per_frame = []
    size = None
    for path in frames:
        img = cv2.imread(path)
        if img is None:
            faces_per_frame.append([])
            continue
        h, w = img.shape[:2]
        size = (w, h)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        found = cascade.detectMultiScale(gray, 1.1, 5, minSize=(24, 24))
        faces = [{"cx": float(x + bw / 2), "cy": float(y + bh / 2),
                  "w": float(bw), "h": float(bh), "score": 1.0}
                 for (x, y, bw, bh) in found]
        faces_per_frame.append(faces)
    return faces_per_frame, size


def detect_all(frames):
    """Coba backend berurutan; kembalikan (faces_per_frame, (w,h), nama,
    errors). Error backend yang dilewati DICATAT (bukan ditelan diam-
    diam) supaya fallback selalu terlihat di plan info."""
    errors = []
    for name, fn in (("mediapipe", detect_mediapipe),
                     ("opencv-dnn", detect_opencv_dnn),
                     ("opencv-haar", detect_haar)):
        try:
            faces, size = fn(frames)
            if size is None:
                raise RuntimeError("tidak ada frame terbaca")
            return faces, size, name, errors
        except Exception as e:  # noqa: BLE001 — fallback berantai disengaja
            errors.append(f"{name}: {e}")
    raise RuntimeError("semua backend deteksi gagal — " + " | ".join(errors))


def _ensure_pose_model():
    if not os.path.exists(POSE_MODEL):
        urllib.request.urlretrieve(POSE_MODEL_URL, POSE_MODEL)


def detect_bodies_pose(frames):
    """Jangkar badan utama: MediaPipe Pose Landmarker (Tasks API).

    Jangkar x = titik tengah bahu (landmark 11/12) — pusat torso yang
    stabil untuk shot podcast duduk. Lebar semu = 3x jarak bahu
    (perkiraan lebar torso). Skor semu 0,5: badan HANYA dipakai pada
    sampel tanpa wajah (lihat choose_targets), jadi skornya tidak
    pernah bersaing langsung dengan skor wajah. Bila bahu tidak
    meyakinkan (visibility < 0,3), jangkar cadangan = hidung
    (landmark 0) dengan lebar semu 22% lebar frame.
    """
    import cv2
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision

    _ensure_pose_model()
    options = vision.PoseLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=POSE_MODEL),
        running_mode=vision.RunningMode.IMAGE,
        min_pose_detection_confidence=0.4,
        min_pose_presence_confidence=0.4)
    bodies_per_frame = []
    with vision.PoseLandmarker.create_from_options(options) as lm:
        for path in frames:
            img = cv2.imread(path)
            if img is None:
                bodies_per_frame.append([])
                continue
            h, w = img.shape[:2]
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB,
                              data=cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            res = lm.detect(mp_img)
            bodies = []
            for lms in res.pose_landmarks or []:
                if len(lms) < 25:
                    continue
                ls, rs = lms[11], lms[12]
                if min(ls.visibility, rs.visibility) >= 0.3:
                    bodies.append({
                        "cx": (ls.x + rs.x) / 2 * w,
                        "cy": (ls.y + rs.y) / 2 * h,
                        "w": max(abs(ls.x - rs.x) * w * 3.0, 0.10 * w),
                        "h": 0.45 * h, "score": 0.5, "kind": "body"})
                elif lms[0].visibility >= 0.3:
                    bodies.append({
                        "cx": lms[0].x * w, "cy": lms[0].y * h,
                        "w": 0.22 * w, "h": 0.30 * h,
                        "score": 0.5, "kind": "body"})
            bodies_per_frame.append(bodies)
    return bodies_per_frame


def detect_bodies_hog(frames):
    """Jangkar badan cadangan (offline penuh): OpenCV HOG person
    detector (SVM bawaan cv2). Lebih lemah dari Pose pada shot duduk
    terpotong, tapi memberi perkiraan x orang saat backend Pose
    tidak bisa jalan. Kotak lebih pendek dari 30% tinggi frame
    dibuang (kemungkinan besar bukan orang utuh)."""
    import cv2

    hog = cv2.HOGDescriptor()
    hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
    bodies_per_frame = []
    for path in frames:
        img = cv2.imread(path)
        if img is None:
            bodies_per_frame.append([])
            continue
        h, w = img.shape[:2]
        scale = max(1.0, 640 / w)
        big = cv2.resize(img, (round(w * scale), round(h * scale)))
        rects, _weights = hog.detectMultiScale(
            big, winStride=(8, 8), padding=(8, 8), scale=1.05)
        bodies = []
        for (x, y, bw, bh) in rects:
            if bh / scale < 0.30 * h:
                continue
            bodies.append({
                "cx": (x + bw / 2) / scale, "cy": (y + bh / 2) / scale,
                "w": bw / scale, "h": bh / scale,
                "score": 0.4, "kind": "body"})
        bodies_per_frame.append(bodies)
    return bodies_per_frame


def detect_bodies(frames):
    """Rantai jangkar badan: Pose Landmarker -> HOG. Kembalikan
    (bodies_per_frame, nama_backend, errors) — pola yang sama dengan
    detect_all supaya kegagalan backend selalu tercatat."""
    errors = []
    for name, fn in (("mediapipe-pose", detect_bodies_pose),
                     ("opencv-hog", detect_bodies_hog)):
        try:
            return fn(frames), name, errors
        except Exception as e:  # noqa: BLE001 — fallback berantai
            errors.append(f"{name}: {e}")
    return [[] for _ in frames], "none", errors


def _rank(face):
    """Urutan kualitas deteksi: skor dulu, lalu luas. (Uji Peep Talk:
    kotak palsu BlazeFace bisa lebih BESAR dari wajah asli tapi skornya
    lebih rendah — peringkat murni luas akan menyeret crop ke kotak
    palsu di tengah frame.)"""
    return (face["score"], face["w"] * face["h"])


def choose_targets(faces_per_frame, width, bodies_per_frame=None):
    """Satu pusat target per sampel (koordinat x sumber) + jangkarnya.

    Observasi per sampel: WAJAH bila ada yang terdeteksi; BADAN
    (jangkar pose/HOG) hanya bila sampel itu tanpa wajah sama
    sekali. Mesin keadaan di bawah identik untuk kedua jenis
    jangkar — karakter gerak (histeresis hilang 3 sampel, kandidat
    persisten >= 2 sampel, pergantian pembicara meyakinkan) tidak
    berubah dari versi wajah-saja.

    Aturan:
    - Akuisisi awal: observasi berperingkat tertinggi (skor, luas).
    - Selama observasi dekat pusat track (<= 18% lebar frame)
      terdeteksi, track mengikutinya. Observasi lain mengambil alih
      di sini HANYA bila skornya >0,10 lebih tinggi pada 2 sampel
      berurutan (ganti pembicara yang meyakinkan, bukan noise).
    - Bila observasi track TIDAK terdeteksi di dekat posisinya
      (kedip detektor / tertutup sesaat / shot berubah): TAHAN
      posisi — jangan langsung lompat. Track dinyatakan hilang
      setelah 3 sampel berurutan (1,5 dtk @2fps) tanpa observasi di
      dekatnya, dan kandidat pengganti harus muncul persisten
      (>= 2 sampel) sebelum track berpindah. Tanpa histeresis ini,
      deteksi yang bergantian muncul (umum di shot wide podcast:
      dua sosok terdeteksi bergantian) membuat crop menyapu
      bolak-balik melintasi ruangan dan frame sampel review
      menangkap crop di tengah sapuan tanpa wajah — terbukti pada
      uji pertama klip Peep Talk _05 (3/5 frame).
    - Tanpa deteksi sama sekali: tahan pusat terakhir; sebelum
      deteksi pertama: tengah frame.

    Kembalikan (targets, anchors): anchors[i] = "face" / "body" /
    "hold" — jangkar yang menentukan target sampel itu (untuk log).
    """
    if bodies_per_frame is None:
        bodies_per_frame = [[] for _ in faces_per_frame]
    targets = []
    anchors = []
    cur = None
    lost = 0
    cand_cx, cand_n = None, 0
    pend_cx, pend_n = None, 0
    for faces, bodies in zip(faces_per_frame, bodies_per_frame):
        obs = [dict(f, kind="face") for f in faces
               if f["w"] >= 12 and f["h"] >= 12]
        if not obs:
            obs = [dict(b, kind="body") for b in bodies]
        anchor = "hold"
        if cur is None:
            if obs:
                best = max(obs, key=_rank)
                cur = best["cx"]
                anchor = best["kind"]
            targets.append(cur)
            anchors.append(anchor)
            continue
        near = [f for f in obs if abs(f["cx"] - cur) <= 0.18 * width]
        if near:
            keep = max(near, key=_rank)
            lost = 0
            cand_cx, cand_n = None, 0
            others = [f for f in obs if f is not keep]
            best_other = max(others, key=_rank) if others else None
            if best_other is not None and \
                    best_other["score"] > keep["score"] + 0.10:
                if pend_cx is not None and \
                        abs(best_other["cx"] - pend_cx) <= 0.18 * width:
                    pend_n += 1
                else:
                    pend_cx, pend_n = best_other["cx"], 1
                if pend_n >= 2:
                    cur = best_other["cx"]
                    anchor = best_other["kind"]
                    pend_cx, pend_n = None, 0
                else:
                    cur = keep["cx"]
                    anchor = keep["kind"]
            else:
                cur = keep["cx"]
                anchor = keep["kind"]
                pend_cx, pend_n = None, 0
        else:
            lost += 1
            if obs:
                best = max(obs, key=_rank)
                if cand_cx is not None and \
                        abs(best["cx"] - cand_cx) <= 0.18 * width:
                    cand_n += 1
                else:
                    cand_cx, cand_n = best["cx"], 1
                if lost >= 3 and cand_n >= 2:
                    cur = best["cx"]
                    anchor = best["kind"]
                    lost = 0
                    cand_cx, cand_n = None, 0
            # selain itu: tahan cur (kedip deteksi / belum persisten)
        targets.append(cur)
        anchors.append(anchor)
    center = width / 2.0
    return [t if t is not None else center for t in targets], anchors


def smooth_trajectory(xs, dt, max_speed, tau=0.5):
    """Median-3 -> eksponensial (tau detik) -> clamp kecepatan (px/dtk)."""
    if len(xs) >= 3:
        med = []
        for i in range(len(xs)):
            win = sorted(xs[max(0, i - 1):i + 2])
            med.append(win[len(win) // 2])
        xs = med
    alpha = 1 - math.exp(-dt / tau)
    out = []
    prev = None
    for x in xs:
        prev = x if prev is None else prev + alpha * (x - prev)
        out.append(prev)
    clamped = []
    prev = None
    for x in out:
        if prev is not None:
            step = max_speed * dt
            x = min(max(x, prev - step), prev + step)
        clamped.append(x)
        prev = x
    return clamped


# --- Kunci crop per shot (perintah owner 4 Nov 2026) -----------------
# Crop TIDAK mengikuti gerakan subjek di dalam satu shot. Ia dikunci
# pada satu posisi per shot dan hanya berpindah tepat di batas shot
# (potongan B-roll / ganti kamera / insert pada footage sumber).
DIFF_HARD = 0.16      # frame-diff >= ini antar 2 sampel = potongan keras
DIFF_SOFT = 0.08      # ambang perubahan besar bertahap (dissolve)
DIFF_SOFT_RUN = 2     # sampel berurutan >= DIFF_SOFT = batas dissolve
ANCHOR_JUMP = 0.30    # lompatan target cx (fraksi lebar) penguat batas
MIN_SHOT_SAMPLES = 3  # shot < ini (1,5 dtk @2fps) diserap tetangganya


def frame_diffs(frames):
    """Selisih visual antar frame sampel berurutan: mean abs diff pada
    thumbnail grayscale 96x54, ternormalisasi 0..1. diffs[i] = perubahan
    dari sampel i ke i+1. None bila frame tidak terbaca — pemanggil
    jatuh ke mode aman: satu kunci untuk seluruh klip."""
    try:
        import cv2
        import numpy as np
    except Exception:  # noqa: BLE001 — fallback disengaja, tercatat di info
        return None
    thumbs = []
    for path in frames:
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return None
        thumbs.append(cv2.resize(img, (96, 54)).astype(np.float32) / 255.0)
    return [float(np.abs(thumbs[i + 1] - thumbs[i]).mean())
            for i in range(len(thumbs) - 1)]


def shot_bounds(diffs, targets, width, n):
    """Indeks sampel tempat shot baru mulai (selalu diawali 0).

    Batas shot = potongan pada footage itu sendiri: (a) diff keras
    >= DIFF_HARD; (b) diff >= DIFF_SOFT diperkuat lompatan target
    > ANCHOR_JUMP x lebar (ganti pembicara satu set — gambar berubah
    sedang tapi subjek berpindah jauh); (c) dissolve: diff >= DIFF_SOFT
    selama DIFF_SOFT_RUN sampel berurutan. Shot lebih pendek dari
    MIN_SHOT_SAMPLES diserap ke shot sebelumnya supaya kunci tidak
    melompat hanya untuk kilasan sesaat."""
    if diffs is None or n <= 1:
        return [0]
    raw = []
    run = 0
    for i, d in enumerate(diffs):
        step = i + 1  # kandidat sampel pertama shot baru
        if step >= n:
            break
        jump = abs(targets[step] - targets[i]) > ANCHOR_JUMP * width
        if d >= DIFF_HARD or (d >= DIFF_SOFT and jump):
            raw.append(step)
            run = 0
        elif d >= DIFF_SOFT:
            run += 1
            if run >= DIFF_SOFT_RUN:
                raw.append(step - DIFF_SOFT_RUN + 1)
                run = 0
        else:
            run = 0
    bounds = [0]
    for b in raw:
        if b - bounds[-1] >= MIN_SHOT_SAMPLES and b < n:
            bounds.append(b)
    return bounds


def lock_segments(targets, bounds, dt, dur, crop_w, width):
    """Satu crop_x KONSTAN per shot = median target shot itu (median
    tahan terhadap kedip deteksi), ter-clamp ke frame + kuantisasi
    4px seperti jalur lama. Shot tetangga yang kuncinya sama digabung
    menjadi satu segmen. Kembalikan (plan, shot_crops)."""
    plan = []
    shot_crops = []
    edges = list(bounds) + [len(targets)]
    for s in range(len(bounds)):
        seg = sorted(targets[edges[s]:edges[s + 1]])
        cx = seg[len(seg) // 2]
        crop_x = int(round(min(max(cx - crop_w / 2, 0), width - crop_w)))
        crop_x -= crop_x % 4
        shot_crops.append(crop_x)
        t0 = bounds[s] * dt
        t1 = min(edges[s + 1] * dt, dur)
        if t0 >= dur:
            break
        if plan and plan[-1]["crop_x"] == crop_x:
            plan[-1]["t1"] = round(t1, 3)
        else:
            plan.append({"t0": round(t0, 3), "t1": round(t1, 3),
                         "crop_x": crop_x})
    return plan, shot_crops


def build_plan(video, start, end, fps, frames_dir, max_speed_frac=0.30):
    frames = extract_frames(video, start, end, fps, frames_dir)
    if not frames:
        raise RuntimeError("tidak ada frame sampel yang terekstrak")
    faces_per_frame, (w, h), backend, backend_errors = detect_all(frames)
    # Jangkar badan hanya dihitung untuk sampel TANPA wajah (hemat
    # waktu + wajah tetap jangkar utama selama terdeteksi).
    bodies_per_frame = [[] for _ in frames]
    body_backend, body_errors = "not-needed", []
    faceless = [i for i, f in enumerate(faces_per_frame) if not f]
    if faceless:
        sub_bodies, body_backend, body_errors = detect_bodies(
            [frames[i] for i in faceless])
        for i, bodies in zip(faceless, sub_bodies):
            bodies_per_frame[i] = bodies
    crop_w = int(h * 9 / 16) // 2 * 2
    if crop_w >= w:
        raise RuntimeError(
            f"crop 9:16 ({crop_w}px) >= lebar sumber ({w}px) — "
            "facetrack tidak berlaku, pakai crop tengah")
    targets, anchors = choose_targets(faces_per_frame, w,
                                      bodies_per_frame)
    dt = 1.0 / fps
    dur = end - start
    # Kunci per shot: batas shot dari potongan visual footage; satu
    # crop_x konstan per shot. (Jalur lama smoothing + clamp kecepatan
    # diganti total — lihat catatan perintah owner 4 Nov 2026 di atas.)
    diffs = frame_diffs(frames)
    bounds = shot_bounds(diffs, targets, w, len(frames))
    plan, shot_crops = lock_segments(targets, bounds, dt, dur, crop_w, w)
    shot_of = [0] * len(frames)
    for s, b in enumerate(bounds):
        e = bounds[s + 1] if s + 1 < len(bounds) else len(frames)
        for i in range(b, min(e, len(frames))):
            shot_of[i] = s
    log = []
    for i in range(len(frames)):
        t0 = i * dt
        if t0 >= dur:
            break
        log.append({
            "t": round(t0, 2), "faces": len(faces_per_frame[i]),
            "bodies": len(bodies_per_frame[i]), "anchor": anchors[i],
            "target_cx": round(targets[i], 1),
            "diff_prev": (round(diffs[i - 1], 3)
                          if diffs is not None and i > 0 else None),
            "shot": shot_of[i],
            "crop_x": shot_crops[shot_of[i]],
        })
    info = {
        "backend": backend,
        "backend_errors": backend_errors,
        "body_backend": body_backend,
        "body_errors": body_errors,
        "src_w": w, "src_h": h, "crop_w": crop_w,
        "n_samples": len(frames),
        "n_with_face": sum(1 for f in faces_per_frame if f),
        "n_with_body": sum(1 for b in bodies_per_frame if b),
        "n_body_anchor": sum(1 for a in anchors if a == "body"),
        "segments": len(plan),
        "mode": "shot-lock",
        "n_shots": len(bounds),
        "shot_boundaries_s": [round(b * dt, 2) for b in bounds[1:]],
        "diff_source": "frames" if diffs is not None else "none-single-lock",
    }
    return plan, info, log


def main():
    ap = argparse.ArgumentParser(description="Deteksi wajah + crop plan")
    ap.add_argument("--video", required=True)
    ap.add_argument("--start", type=float, required=True)
    ap.add_argument("--end", type=float, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--frames-dir", required=True)
    ap.add_argument("--fps", type=float, default=2.0)
    ap.add_argument("--log", default=None)
    args = ap.parse_args()

    plan, info, log = build_plan(args.video, args.start, args.end,
                                 args.fps, args.frames_dir)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"plan": plan, "info": info}, f, indent=1)
    if args.log:
        with open(args.log, "w", encoding="utf-8") as f:
            json.dump(log, f, indent=1)
    print(json.dumps({"ok": True, **info}))


if __name__ == "__main__":
    sys.exit(main())
