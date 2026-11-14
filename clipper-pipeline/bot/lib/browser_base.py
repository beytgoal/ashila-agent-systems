"""Basis browser untuk poster/submitter: Playwright + Chromium lokal persisten.

Fakta lingkungan (terverifikasi divisi, lihat page-map-posting.md §0):
- Chromium mentah gagal keluar (egress wajib HTTP proxy CONNECT berauth) ->
  skrip ini membuka relay CONNECT lokal 127.0.0.1 tanpa kredensial yang
  meneruskan ke proxy egress; kredensial dibaca dari env saat runtime dan
  TIDAK PERNAH ditulis ke file/log.
- Egress melakukan intersepsi TLS -> konteks perlu ignore_https_errors=True.
- Chromium jalan headed di bawah xvfb-run (tidak ada X server di VM).
- Profil persisten per platform: sesi login hidup di profil, BUKAN di kode.
  Profil belum login = modul berhenti dengan status LOGIN-DIPERLUKAN (exit 2).
- Captcha/checkpoint/bot-check = BERHENTI TOTAL jalur itu (exit 3).
"""
import base64
import os
import socket
import threading
from urllib.parse import unquote, urlparse

STOP_MARKERS = [
    "checkpoint", "captcha", "confirm your identity", "security check",
    "verifikasi keamanan", "periksa identitas", "enter the code",
    "two-factor", "dua faktor", "unusual activity", "aktivitas tidak biasa",
    "help us confirm", "suspicious activity",
]

EXIT_OK = 0
EXIT_LOGIN = 2
EXIT_STOP = 3


class StopError(Exception):
    pass


class LoginRequired(Exception):
    pass


def _egress_parts():
    raw = (os.environ.get("https_proxy") or os.environ.get("HTTPS_PROXY")
           or os.environ.get("http_proxy") or os.environ.get("HTTP_PROXY"))
    if not raw:
        return None
    u = urlparse(raw)
    if not u.hostname:
        return None
    host = u.hostname
    try:
        host = socket.getaddrinfo(host, u.port or 3128, socket.AF_INET, socket.SOCK_STREAM)[0][4][0]
    except Exception:
        pass
    auth = None
    if u.username:
        token = base64.b64encode(f"{unquote(u.username)}:{unquote(u.password or '')}".encode()).decode()
        auth = f"Basic {token}"
    return {"host": host, "port": u.port or 3128, "auth": auth}


def _pump(src, dst):
    try:
        while True:
            data = src.recv(65536)
            if not data:
                break
            dst.sendall(data)
    except Exception:
        pass
    try:
        dst.shutdown(socket.SHUT_WR)
    except Exception:
        pass


def _relay_handle(client, egress):
    try:
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = client.recv(4096)
            if not chunk:
                client.close()
                return
            buf += chunk
        line = buf.split(b"\r\n")[0].decode("latin1")
        parts = line.split(" ")
        if len(parts) < 2 or parts[0].upper() != "CONNECT":
            client.sendall(b"HTTP/1.1 405 Method Not Allowed\r\n\r\n")
            client.close()
            return
        target = parts[1]
        up = socket.create_connection((egress["host"], egress["port"]), timeout=30)
        req = f"CONNECT {target} HTTP/1.1\r\nHost: {target}\r\n"
        if egress["auth"]:
            req += f"Proxy-Authorization: {egress['auth']}\r\n"
        req += "\r\n"
        up.sendall(req.encode())
        resp = b""
        while b"\r\n\r\n" not in resp:
            chunk = up.recv(4096)
            if not chunk:
                break
            resp += chunk
        client.sendall(resp)
        if b" 200" not in resp.split(b"\r\n")[0]:
            client.close()
            up.close()
            return
        t1 = threading.Thread(target=_pump, args=(client, up), daemon=True)
        t2 = threading.Thread(target=_pump, args=(up, client), daemon=True)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
    except Exception:
        try:
            client.close()
        except Exception:
            pass


def start_relay():
    """Mulai relay CONNECT lokal; kembalikan (server_socket, port)."""
    egress = _egress_parts()
    if not egress:
        return None, None
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(50)
    port = srv.getsockname()[1]

    def loop():
        while True:
            try:
                c, _ = srv.accept()
            except OSError:
                return
            threading.Thread(target=_relay_handle, args=(c, egress), daemon=True).start()

    threading.Thread(target=loop, daemon=True).start()
    return srv, port


def open_context(cfg, profile_key):
    """Buka konteks persisten Playwright. Profil dari config jalur[profile_key]."""
    from playwright.sync_api import sync_playwright

    jalur = cfg["jalur"]
    chrome = os.path.expanduser(jalur["chrome"])
    profile = os.path.expanduser(jalur[profile_key])
    os.makedirs(profile, exist_ok=True)
    srv, port = start_relay()
    pw = sync_playwright().start()
    args = ["--no-sandbox", "--disable-dev-shm-usage"]
    launch_kw = {
        "executable_path": chrome,
        "headless": False,
        "args": args,
        "ignore_https_errors": True,
        "viewport": {"width": 1440, "height": 900},
    }
    if port:
        launch_kw["proxy"] = {"server": f"http://127.0.0.1:{port}"}
    ctx = pw.chromium.launch_persistent_context(profile, **launch_kw)
    return pw, ctx, srv


def check_stop(page):
    """Deteksi captcha/checkpoint dari teks halaman; StopError bila kena."""
    try:
        text = (page.inner_text("body", timeout=3000) or "").lower()
    except Exception:
        return
    for m in STOP_MARKERS:
        if m in text:
            raise StopError(f"penanda berhenti terdeteksi: {m}")


def debug_shot(page, folder, name):
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, name)
    try:
        page.screenshot(path=path, full_page=False)
    except Exception:
        pass
    return path
