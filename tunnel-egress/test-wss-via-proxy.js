// test-wss-via-proxy.js — Verify the public tunnel end-to-end from this VM.
// Same checks as test-tunnel.js (no token -> rejected, wrong token ->
// rejected, right token -> eth_chainId / eth_requestAccounts /
// personal_sign, NO value transfer), but the wss connection goes through
// the sandbox egress proxy with an explicit agent (the plain 'ws' client
// does not use the proxy env on its own, which produced a misleading
// TLS "wrong version number" error).
//   node test-wss-via-proxy.js <host-tunnel>   (no scheme)
// The relay token is read from saw-relay/.env and never printed; the proxy
// URL is read from the https_proxy env var and never printed.
'use strict';
const fs = require('fs');
const path = require('path');
const { WebSocket } = require(path.join(__dirname, '..', 'saw-relay', 'node_modules', 'ws'));
const { HttpsProxyAgent } = require(path.join(
  __dirname, '..', '..', 'wc-wallet', 'node_modules', 'https-proxy-agent'
));

const HOST = process.argv[2];
if (!HOST || HOST.includes('://')) {
  console.error('usage: node test-wss-via-proxy.js <host-tunnel>');
  process.exit(2);
}
const proxyUrl = process.env.https_proxy || process.env.HTTPS_PROXY;
if (!proxyUrl) { console.error('no proxy env var'); process.exit(2); }
const agent = new HttpsProxyAgent(proxyUrl);

const env = {};
for (const line of fs.readFileSync(path.join(__dirname, '..', 'saw-relay', '.env'), 'utf8').split('\n')) {
  const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.+?)\s*$/);
  if (m) env[m[1]] = m[2];
}
const TOKEN = env.SAW_RELAY_TOKEN;
const BASE = `wss://${HOST}/`;

function rpc(ws, method, params, chain) {
  return new Promise((resolve, reject) => {
    const id = Math.floor(Math.random() * 1e6);
    const to = setTimeout(() => reject(new Error('timeout ' + method)), 20000);
    const h = (raw) => {
      let msg; try { msg = JSON.parse(raw.toString()); } catch { return; }
      if (msg.id !== id) return;
      clearTimeout(to); ws.off('message', h);
      if (msg.error) reject(new Error(method + ' -> ' + JSON.stringify(msg.error)));
      else resolve(msg.result);
    };
    ws.on('message', h);
    ws.send(JSON.stringify({ id, method, params: params || [], chain }));
  });
}

function attempt(url, label) {
  return new Promise((resolve) => {
    const ws = new WebSocket(url, { agent });
    let done = false;
    const finish = (r) => { if (!done) { done = true; if (!r.open) { try { ws.terminate(); } catch {} } resolve(r); } };
    ws.on('open', () => finish({ label, open: true, ws }));
    ws.on('error', (e) => finish({ label, open: false, error: 'ws-error: ' + e.message }));
    ws.on('close', (code) => finish({ label, open: false, error: 'closed code=' + code }));
    setTimeout(() => finish({ label, open: false, error: 'connect timeout' }), 20000);
  });
}

(async () => {
  console.log('== Tunnel test VIA PROXY: ' + BASE + ' ==');
  const noTok = await attempt(BASE, 'tanpa-token');
  console.log('1. tanpa token   :', noTok.open ? 'LOLOS (BAHAYA!)' : 'DITOLAK (' + noTok.error + ')');
  const badTok = await attempt(BASE + '?token=salah-semua-0000', 'token-salah');
  console.log('2. token salah   :', badTok.open ? 'LOLOS (BAHAYA!)' : 'DITOLAK (' + badTok.error + ')');
  const ok = await attempt(BASE + '?token=' + TOKEN, 'token-benar');
  if (!ok.open) { console.log('3. token benar   : GAGAL KONEK (' + ok.error + ')'); process.exit(1); }
  const ws = ok.ws;
  try {
    const chain = await rpc(ws, 'eth_chainId', [], '0x185d9');
    console.log('3a. eth_chainId (hint 0x185d9) :', chain, chain === '0x185d9' ? '(Elysium OK)' : '(UNEXPECTED)');
    const accts = await rpc(ws, 'eth_requestAccounts', []);
    console.log('3b. eth_requestAccounts        :', JSON.stringify(accts));
    const sig = await rpc(ws, 'personal_sign', ['Tunnel workaround test - no value', accts[0]]);
    console.log('3c. personal_sign              : 0x' + String(sig).slice(0, 20) + '... (len ' + String(sig).length + ')');
    console.log('== SEMUA UJI VIA TUNNEL PUBLIK LULUS ==');
  } catch (e) {
    console.log('3. RPC GAGAL:', e.message);
    process.exit(1);
  } finally { try { ws.close(); } catch {} }
  process.exit(0);
})();
