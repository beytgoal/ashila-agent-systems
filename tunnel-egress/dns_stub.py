#!/usr/bin/env python3
"""Stub DNS lokal untuk cloudflared di VM ini.

Masalah: resolver sandbox menolak lookup SRV (error "server misbehaving")
yang dibutuhkan cloudflared untuk edge discovery
(_v2-origintunneld._tcp.argotunnel.com), dan DNS publik langsung diblokir.

Stub ini mendengarkan di 127.0.0.1:5353 (UDP+TCP):
- Query SRV untuk _v2-origintunneld._tcp.argotunnel.com dijawab statis
  dengan target resmi Cloudflare: region1/region2.v2.argotunnel.com:7844.
- Semua query lain diteruskan apa adanya ke resolver sistem
  (dari /etc/resolv.conf) dan jawabannya diteruskan kembali.

cloudflared diarahkan ke stub ini lewat TUNNEL_DNS_RESOLVER_ADDRS.
"""
import socket
import struct
import threading

LISTEN = ("127.0.0.1", 5353)
SRV_NAME = "_v2-origintunneld._tcp.argotunnel.com"
SRV_TARGETS = ["region1.v2.argotunnel.com", "region2.v2.argotunnel.com"]
SRV_PORT = 7844


def read_upstreams():
    ups = []
    try:
        with open("/etc/resolv.conf") as f:
            for line in f:
                parts = line.split()
                if len(parts) == 2 and parts[0] == "nameserver":
                    ups.append(parts[1])
    except OSError:
        pass
    return ups or ["198.19.0.1"]


UPSTREAMS = read_upstreams()


def encode_name(name):
    out = b""
    for part in name.split("."):
        out += bytes([len(part)]) + part.encode()
    return out + b"\x00"


def parse_question(data):
    # header 12 byte; lalu qname label; lalu qtype+qclass
    i = 12
    labels = []
    while True:
        ln = data[i]
        if ln == 0:
            i += 1
            break
        labels.append(data[i + 1:i + 1 + ln].decode())
        i += 1 + ln
    qtype, qclass = struct.unpack(">HH", data[i:i + 4])
    i += 4
    return ".".join(labels), qtype, qclass, i


EDGE_LOCAL = {"region1.v2.argotunnel.com", "region2.v2.argotunnel.com"}


def simple_response(query, qend, answers):
    tid = query[0:2]
    header = tid + struct.pack(">HHHHH", 0x8180, 1, len(answers), 0, 0)
    return header + query[12:qend] + b"".join(answers)


def srv_response(query, qend):
    answers = []
    for target in SRV_TARGETS:
        rdata = struct.pack(">HHH", 0, 1, SRV_PORT) + encode_name(target)
        answers.append(b"\xc0\x0c" + struct.pack(">HHIH", 33, 1, 300, len(rdata)) + rdata)
    return simple_response(query, qend, answers)


def a_response(query, qend):
    # Host edge diarahkan ke forwarder TCP lokal (tcp_edge_fwd.py, :7844)
    # karena koneksi langsung ke IP sintetis edge mati di handshake TLS;
    # forwarder meneruskannya lewat CONNECT egress proxy ke edge asli.
    rdata = socket.inet_aton("127.0.0.1")
    ans = b"\xc0\x0c" + struct.pack(">HHIH", 1, 1, 300, len(rdata)) + rdata
    return simple_response(query, qend, [ans])


def forward(query):
    # PENTING: di sandbox ini sendto() UDP pada socket tak-terhubung diblokir
    # (EPERM); pola yang lolos adalah connect() lalu send()/recv().
    last_err = None
    for up in UPSTREAMS:
        try:
            fam = socket.AF_INET6 if ":" in up else socket.AF_INET
            s = socket.socket(fam, socket.SOCK_DGRAM)
            s.settimeout(5)
            s.connect((up, 53))
            s.send(query)
            data = s.recv(65535)
            s.close()
            return data
        except OSError as e:
            last_err = e
            continue
    raise last_err if last_err else RuntimeError("no upstream")


def handle(query):
    try:
        name, qtype, _qclass, qend = parse_question(query)
    except Exception:
        return forward(query)
    lname = name.lower()
    if lname == SRV_NAME and qtype == 33:
        return srv_response(query, qend)
    if lname in EDGE_LOCAL:
        if qtype == 1:
            return a_response(query, qend)
        if qtype == 28:
            return simple_response(query, qend, [])
    return forward(query)


def udp_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(LISTEN)
    while True:
        data, addr = s.recvfrom(65535)
        try:
            resp = handle(data)
            # Balas lewat socket terhubung: sendto() dari socket server yang
            # tak-terhubung kena EPERM di sandbox ini (lihat forward()).
            r = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            r.connect(addr)
            r.send(resp)
            r.close()
        except Exception as e:
            print("udp error:", e, flush=True)


def tcp_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(LISTEN)
    s.listen(16)
    while True:
        conn, _ = s.accept()
        try:
            hdr = conn.recv(2)
            if len(hdr) < 2:
                conn.close()
                continue
            ln = struct.unpack(">H", hdr)[0]
            data = b""
            while len(data) < ln:
                chunk = conn.recv(ln - len(data))
                if not chunk:
                    break
                data += chunk
            resp = handle(data)
            conn.sendall(struct.pack(">H", len(resp)) + resp)
        except Exception as e:
            print("tcp error:", e, flush=True)
        finally:
            conn.close()


if __name__ == "__main__":
    print(f"dns_stub listening on {LISTEN[0]}:{LISTEN[1]}, upstreams={UPSTREAMS}", flush=True)
    threading.Thread(target=tcp_server, daemon=True).start()
    udp_server()
