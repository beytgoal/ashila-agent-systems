# Tunnel Egress

Getting a Cloudflare Tunnel (and plain SSH) out of a sandbox VM whose only
egress is an intercepting HTTP proxy — no direct UDP, no direct DNS, TCP
only via CONNECT.

The working chain, proven in production:

1. `dns_stub.py` — local stub DNS that answers the tunnel's SRV lookups
   with static records and forwards the rest over connected UDP.
2. `tcp_edge_fwd.py` — local TCP forwarder that opens HTTP CONNECT
   tunnels through the proxy to the tunnel edge IPs (the resolver hands
   out synthetic IPs that refuse direct TLS).
3. `cloudflared --protocol http2` — QUIC/UDP is dead in this environment;
   HTTP/2 over the forwarder works. A custom `/etc/hosts` is bind-mounted
   into the process tree (`unshare -Urm`) so cloudflared resolves edge
   hostnames to the local forwarder.
4. `proxy-connect.py` — a ProxyCommand shim that speaks HTTP CONNECT so
   plain `ssh` can leave through the proxy.
5. `run-cloudflared.sh` — the runner that assembles the chain.
6. `test-wss-via-proxy.js` — WebSocket reachability tester (Node; raw
   Python WS testers give false negatives through this proxy).

Full write-up: `../skills/cloudflare-tunnel-egress/SKILL.md`.
