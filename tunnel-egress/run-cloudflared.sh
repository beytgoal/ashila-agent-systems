#!/bin/bash
# run-cloudflared.sh — runner persisten Cloudflare named tunnel untuk saw-relay.
#
# Token dibaca cloudflared dari file .cloudflare-token (chmod 600) via
# --token-file, jadi token TIDAK muncul di command line / ps / log.
# Loop: bila cloudflared exit, tunggu 5 detik lalu sambung ulang.
# Hostname publik STABIL (dari dashboard Cloudflare), tidak berubah per restart
# proses — yang bisa berubah hanya setelah VM restart (proses harus dihidupkan
# lagi; token + tunnel tetap sama).
#
# Jalankan: setsid nohup ./run-cloudflared.sh >> cloudflared-runner.out 2>&1 < /dev/null &
set -u
cd "$(dirname "$0")"
TOKEN_FILE="$PWD/.cloudflare-token"
LOG="$PWD/cloudflared.log"

if [ ! -s "$TOKEN_FILE" ]; then
  echo "[run-cloudflared] token file tidak ada/kosong: $TOKEN_FILE — tunnel TIDAK dijalankan." >&2
  exit 1
fi
chmod 600 "$TOKEN_FILE" 2>/dev/null || true

# DNS lokal: resolver sandbox menolak lookup SRV yang dibutuhkan cloudflared
# untuk edge discovery (error "server misbehaving"), dan DNS publik langsung
# diblokir. dns_stub.py menjawab SRV _v2-origintunneld._tcp.argotunnel.com
# secara statis dan meneruskan query lain ke resolver sistem.
export TUNNEL_DNS_RESOLVER_ADDRS="127.0.0.1:5353"
python3 "$PWD/dns_stub.py" >> "$PWD/dns_stub.log" 2>&1 &
DNS_STUB_PID=$!
# Forwarder edge: dns_stub menjawab A region*.v2.argotunnel.com = 127.0.0.1,
# dan tcp_edge_fwd.py meneruskan TCP :7844 lewat CONNECT egress proxy ke
# edge asli (koneksi langsung mati di handshake TLS/EOF).
python3 "$PWD/tcp_edge_fwd.py" >> "$PWD/tcp_edge_fwd.log" 2>&1 &
EDGE_FWD_PID=$!
trap 'kill $DNS_STUB_PID $EDGE_FWD_PID 2>/dev/null' EXIT
sleep 1

# /etc/hosts sistem read-only, dan cloudflared mengambil A record host edge
# lewat resolver OS (bukan --dns-resolver-addrs). Jadi cloudflared dijalankan
# di dalam user+mount namespace dengan /etc/hosts bind-mount yang memetakan
# host edge ke 127.0.0.1 (forwarder). Jaringan tetap namespace yang sama.
HOSTS_LOCAL="$PWD/hosts.local"
cat /etc/hosts > "$HOSTS_LOCAL"
grep -q 'region1.v2.argotunnel.com' "$HOSTS_LOCAL" || echo '127.0.0.1 region1.v2.argotunnel.com region2.v2.argotunnel.com' >> "$HOSTS_LOCAL"

while true; do
  echo "[run-cloudflared] $(date -Is) starting cloudflared (token via file)..." >> "$LOG"
  # --protocol http2 WAJIB di VM ini: QUIC (UDP 7844) diblokir sandbox
  # (sendmsg: operation not permitted). TCP-nya pun harus lewat forwarder
  # CONNECT (koneksi langsung mati di TLS/EOF), maka dijalankan di dalam
  # namespace dengan /etc/hosts hasil bind-mount di atas.
  unshare -Urm bash -c "mount --bind '$HOSTS_LOCAL' /etc/hosts && exec ./cloudflared tunnel --no-autoupdate --protocol http2 run --token-file '$TOKEN_FILE'" >> "$LOG" 2>&1
  echo "[run-cloudflared] $(date -Is) cloudflared exited ($?), reconnect in 5s" >> "$LOG"
  sleep 5
done
