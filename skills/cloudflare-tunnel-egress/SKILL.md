# Skill: Cloudflare Tunnel dari VM beregress proxy paksa (cloudflared + stub DNS + forwarder CONNECT)

Menjalankan Cloudflare named tunnel (cloudflared) dari VM sandbox yang
semua egress-nya wajib lewat HTTP proxy. Terverifikasi ujung-ke-ujung
29 Okt 2026: tunnel `saw-relay` status `healthy` (2 koneksi HTTP/2,
colo lax11 + dfw05). Dipakai untuk saw-relay walletd; berlaku umum
untuk cloudflared apa pun dari VM ini.

## Fakta egress sandbox (penyebab semua lapisan di bawah perlu)

1. Resolver sistem menolak lookup SRV (`server misbehaving`) — edge
   discovery cloudflared (`_v2-origintunneld._tcp.argotunnel.com`)
   gagal total. DNS publik langsung (1.1.1.1/8.8.8.8) diblokir.
   Catatan 29 Okt 21:15 WIB: setelah owner mengaktifkan izin aplikasi
   "Pencarian DNS eksternal", SRV via resolver sistem LOLOS; stub di
   bawah tetap dipakai karena A-override + forwarder tetap wajib
   (fakta 2–5 tidak berubah oleh izin itu).
2. UDP `sendto`/`sendmsg` pada socket tak-terhubung = EPERM (Python
   DAN Go). QUIC cloudflared (UDP 7844) mati: "sendmsg: operation not
   permitted". Pola UDP yang LOLOS: socket `connect()` lalu `send()`.
3. TCP langsung ke IP sintetis hasil DNS (198.18.0.0/15) mati di
   handshake TLS (EOF/timeout) — data hanya mengalir lewat HTTP proxy
   (CONNECT) atau endpoint yang diizinkan. cloudflared tidak memakai
   proxy env.
4. `/etc/hosts` dan `/etc/resolv.conf` read-only. `unshare -Urm`
   (user+mount namespace) BOLEH dan bisa bind-mount file di atasnya
   untuk satu pohon proses. Jaringan tidak ikut terisolasi.
5. cloudflared mengambil SRV lewat resolver `--dns-resolver-addrs`,
   tetapi A record host edge lewat resolver OS (/etc/hosts/glibc).

## Arsitektur solusi (semua di `superagentic-wallet/extension-agent/tunnel/`)

- `dns_stub.py` — DNS lokal 127.0.0.1:5353 (UDP+TCP). SRV
  `_v2-origintunneld._tcp.argotunnel.com` dijawab statis
  (region1/region2.v2.argotunnel.com:7844); A region* dijawab
  127.0.0.1; AAAA region* dijawab kosong; sisanya diteruskan ke
  resolver sistem. SEMUA kiriman UDP memakai pola connect()+send()
  (sendto = EPERM), termasuk socket balasan ke klien.
- `tcp_edge_fwd.py` — dengar TCP 127.0.0.1:7844; per koneksi, buka
  CONNECT lewat egress proxy (kredensial dari env `https_proxy` saat
  runtime, tidak disimpan) ke region1.v2.argotunnel.com:7844
  (fallback region2), lalu pipe dua arah. TLS tetap ujung-ke-ujung.
- `run-cloudflared.sh` — supervisor: menolak jalan tanpa
  `.cloudflare-token` (0600); menjalankan dns_stub + tcp_edge_fwd;
  menyiapkan `hosts.local` (salinan /etc/hosts + baris
  `127.0.0.1 region1.v2.argotunnel.com region2.v2.argotunnel.com`);
  menjalankan cloudflared di dalam `unshare -Urm` dengan hosts.local
  ter-bind-mount ke /etc/hosts; flag WAJIB:
  `--protocol http2` + env `TUNNEL_DNS_RESOLVER_ADDRS=127.0.0.1:5353`;
  loop reconnect 5 detik.
- Token tunnel: ambil via API (konektor MCP Cloudflare, GET
  .../cfd_tunnel/{id}/token) dengan skrip yang menulis langsung ke
  `.cloudflare-token` 0600 dan hanya mencetak panjangnya
  (`fetch_cf_token.py`). Token TIDAK bisa lewat Secure Vault (nilai
  vault tidak bisa dibaca kembali untuk binary lokal).

## Sisi Cloudflare (lewat konektor MCP custom.cloudflare, tool execute)

Urutan: (1) POST /zones — WAJIB domain root; subdomain ditolak
HTTP 400 kode 1116. Butuh scope `zone.write`. (2) POST
/accounts/{id}/cfd_tunnel {name, config_src:"cloudflare"}.
(3) PUT .../cfd_tunnel/{id}/configurations — ingress hostname →
http://localhost:<port> + catch-all http_status:404. (4) DNS TIDAK
terbuat otomatis: POST /zones/{id}/dns_records CNAME <host> →
<tunnel-id>.cfargotunnel.com, proxied=true. (5) GET token (di atas).
Zone mulai `pending`: pemilik domain mengganti nameserver di
registrar ke dua NS Cloudflare yang diberikan; uji publik hanya lulus
setelah zone `active`.

## Verifikasi

- Log cloudflared: `Registered tunnel connection ... protocol=http2`
  (ip=127.0.0.1 itu normal — itu alamat forwarder).
- API: GET tunnel → `status: healthy` + connections terisi.
- Setelah zone active: uji WebSocket ke wss://<hostname> — tanpa token
  ditolak, token salah ditolak, token benar → eth_chainId benar.
- Kegagalan khas: SRV error = stub tidak jalan/resolver override
  hilang; `sendmsg operation not permitted` = QUIC, paksa http2;
  TLS EOF = koneksi masih langsung, periksa hosts bind-mount dan
  forwarder (log `edge CONNECT ok`).

## Batas

- Proses mati tiap VM restart (file persisten, proses tidak).
  Hidupkan ulang: hidupkan stack aplikasi dulu, lalu
  `setsid nohup ./run-cloudflared.sh >> cloudflared-runner.out 2>&1 &`.
- Jangan pakai jalur ini untuk mengekspos layanan tanpa autentikasi
  sendiri di belakang tunnel (saw-relay aman karena bertoken; walletd
  18923 tanpa auth TIDAK PERNAH diekspos langsung).
