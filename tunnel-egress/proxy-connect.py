#!/usr/bin/env python3
# proxy-connect.py — ssh ProxyCommand shim: CONNECT through the sandbox
# egress proxy (read from the https_proxy env var at runtime; no credential
# is stored in this file) to <host> <port>, then pipe stdin/stdout.
# Usage: ssh -o "ProxyCommand=python3 proxy-connect.py %h %p" ...
import base64
import os
import socket
import sys
import threading
from urllib.parse import unquote, urlparse


def main() -> int:
    if len(sys.argv) != 3:
        sys.stderr.write("usage: proxy-connect.py <host> <port>\n")
        return 2
    host, port = sys.argv[1], int(sys.argv[2])
    proxy_url = (
        os.environ.get("https_proxy")
        or os.environ.get("HTTPS_PROXY")
        or os.environ.get("http_proxy")
        or os.environ.get("HTTP_PROXY")
    )
    if not proxy_url:
        sys.stderr.write("no proxy env var set\n")
        return 1
    u = urlparse(proxy_url)
    phost, pport = u.hostname, u.port or 3128
    sock = socket.create_connection((phost, pport), timeout=25)
    auth = ""
    if u.username:
        cred = f"{unquote(u.username)}:{unquote(u.password or '')}"
        auth = (
            "Proxy-Authorization: Basic "
            + base64.b64encode(cred.encode()).decode()
            + "\r\n"
        )
    req = (
        f"CONNECT {host}:{port} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        f"{auth}"
        "Proxy-Connection: keep-alive\r\n\r\n"
    )
    sock.sendall(req.encode())
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = sock.recv(4096)
        if not chunk:
            sys.stderr.write("proxy closed during CONNECT\n")
            return 1
        buf += chunk
    status = buf.split(b"\r\n", 1)[0].decode(errors="replace")
    if " 200" not in status:
        sys.stderr.write(f"CONNECT failed: {status}\n")
        return 1
    leftover = buf.split(b"\r\n\r\n", 1)[1]
    if leftover:
        os.write(1, leftover)

    def stdin_to_sock() -> None:
        try:
            while True:
                data = os.read(0, 65536)
                if not data:
                    break
                sock.sendall(data)
        except OSError:
            pass
        try:
            sock.shutdown(socket.SHUT_WR)
        except OSError:
            pass

    t = threading.Thread(target=stdin_to_sock, daemon=True)
    t.start()
    try:
        while True:
            data = sock.recv(65536)
            if not data:
                break
            os.write(1, data)
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
