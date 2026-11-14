"""Utilitas bersama clipper-bot: state JSON atomik, log event JSONL, kunci anti-bentrok.

Mengikuti arsitektur peta-otomatisasi-bot.md (Moderate, 31 Okt 2026):
skrip deterministik 0 token, state JSON, log JSONL, idempoten, satu instans.
"""
import datetime
import fcntl
import hashlib
import json
import os
import sys
import tempfile

BOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(BOT_DIR, "state")
EVENTS_PATH = os.path.join(STATE_DIR, "events.jsonl")


def now_wib():
    tz = datetime.timezone(datetime.timedelta(hours=7))
    return datetime.datetime.now(tz)


def now_iso():
    return now_wib().isoformat(timespec="seconds")


def load_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except json.JSONDecodeError:
        return default


def save_json_atomic(path, data):
    """Tulis JSON via tmp + os.replace (pola aman dari EPERM intermiten di VM ini)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    # verifikasi baca ulang
    with open(path, "r", encoding="utf-8") as f:
        json.load(f)
    return path


def event(kind, payload):
    """Tulis satu baris event JSONL. Hanya dipanggil saat keadaan berubah."""
    os.makedirs(STATE_DIR, exist_ok=True)
    row = {"ts": now_iso(), "kind": kind, **payload}
    with open(EVENTS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def load_config():
    return load_json(os.path.join(BOT_DIR, "config.json"), {})


def expand(p):
    return os.path.expanduser(p) if p else p


class SingleInstance:
    """Kunci flock di folder state bot (bukan /tmp — pelajaran VM: /tmp tak andal)."""

    def __init__(self, name):
        self.path = os.path.join(STATE_DIR, f".{name}.lock")
        self.f = None

    def __enter__(self):
        os.makedirs(STATE_DIR, exist_ok=True)
        self.f = open(self.path, "w")
        try:
            fcntl.flock(self.f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(f"[lock] instans lain untuk {self.path} sedang jalan — keluar.", flush=True)
            sys.exit(4)
        return self

    def __exit__(self, *exc):
        try:
            fcntl.flock(self.f, fcntl.LOCK_UN)
            self.f.close()
        except Exception:
            pass


def caption_key(caption):
    """Kunci idempotensi dari caption: 60 karakter pertama ternormalisasi."""
    c = " ".join((caption or "").split())
    return hashlib.sha1(c[:200].encode("utf-8")).hexdigest()[:12]


def check_approval(scope):
    """Gerbang manusia: aksi live butuh state/approval.json dengan cakupan cocok."""
    ap = load_json(os.path.join(STATE_DIR, "approval.json"), {})
    scopes = ap.get("cakupan", [])
    if scope in scopes or "*" in scopes:
        return True, ap
    return False, ap
