#!/usr/bin/env python3
"""Forwarder TCP lokal untuk edge Cloudflare Tunnel (argotunnel:7844).

Kenapa perlu: semua egress VM ini wajib lewat HTTP proxy sandbox
(https_proxy). cloudflared tidak memakai proxy, dan koneksi TCP langsung
ke edge (IP sintetis 198.18.x) mati di handshake TLS (EOF) — proxy bukan
dilewati. Forwarder ini mendengarkan 127.0.0.1:7844; dns_stub.py menjawab
A record region1/region2.v2.argotunnel.com dengan 127.0.0.1, jadi
cloudflared menyambung ke sini, lalu forwarder membuka CONNECT lewat
egress proxy ke host edge asli dan meneruskan byte dua arah. TLS tetap
ujung-ke-ujung antara cloudflared dan edge Cloudflare.

Kredensial proxy dibaca dari env https_proxy saat runtime; TIDAK disimpan.
"""
import base64
import os
import socket
import threading
from urllib.parse import unquote, urlparse

LISTEN = ("127.0.0.1", 7844)
TARGETS = ["region1.v2.argotunnel.com", "region2.v2.argotunnel.com"]
TPORT = 7844


def proxy_addr():
    proxy_url = (
        os.environ.get("https_proxy")
        or os.environ.get("HTTPS_PROXY")
        or os.environ.get("http_proxy")
        or os.environ.get("HTTP_PROXY")
    )
    if not proxy_url:
        raise RuntimeError("no proxy env var set")
    u = urlparse(proxy_url)
    auth = ""
    if u.username:
        cred = f"{unquote(u.username)}:{unquote(u.password or '')}"
        auth = (
            "Proxy-Authorization: Basic "
            + base64.b64encode(cred.encode()).decode()
            + "\r\n"
        )
    return (u.hostname, u.port or 3128), auth


def open_edge():
    (phost, pport), auth = proxy_addr()
    last = None
    for host in TARGETS:
        try:
            s = socket.create_connection((phost, pport), timeout=25)
            req = (
                f"CONNECT {host}:{TPORT} HTTP/1.1\r\n"
                f"Host: {host}:{TPORT}\r\n"
                f"{auth}"
                "Proxy-Connection: keep-alive\r\n\r\n"
            )
            s.sendall(req.encode())
            buf = b""
            while b"\r\n\r\n" not in buf:
                chunk = s.recv(4096)
                if not chunk:
                    raise ConnectionError("proxy closed during CONNECT")
                buf += chunk
            head, _, rest = buf.partition(b"\r\n\r\n")
            status = head.split(b" ", 2)[1] if b" " in head else b"?"
            if status != b"200":
                raise ConnectionError(f"CONNECT {host} -> {status.decode(errors='replace')}")
            print(f"edge CONNECT ok via {host}", flush=True)
            return s, rest
        except Exception as e:
            last = e
            print(f"edge CONNECT gagal {host}: {e}", flush=True)
            continue
    raise last if last else RuntimeError("no target")


def pipe(src, dst):
    try:
        while True:
            data = src.recv(65535)
            if not data:
                break
            dst.sendall(data)
    except OSError:
        pass
    finally:
        try:
            dst.shutdown(socket.SHUT_WR)
        except OSError:
            pass


def handle_client(client):
    try:
        edge, rest = open_edge()
        if rest:
            client.sendall(rest)
        t = threading.Thread(target=pipe, args=(client, edge), daemon=True)
        t.start()
        pipe(edge, client)
    except Exception as e:
        print("client error:", e, flush=True)
    finally:
        try:
            client.close()
        except OSError:
            pass


def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(LISTEN)
    srv.listen(64)
    print(f"tcp_edge_fwd listening on {LISTEN[0]}:{LISTEN[1]} -> {TARGETS}:{TPORT} via proxy", flush=True)
    while True:
        client, _ = srv.accept()
        threading.Thread(target=handle_client, args=(client,), daemon=True).start()


if __name__ == "__main__":
    main()
