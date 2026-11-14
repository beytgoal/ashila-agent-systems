#!/usr/bin/env python3
"""completeTransfer(transfer VAA) on Base Sepolia via walletd; verify wrapped SUI balance."""
import base64, json, os, time, urllib.request
from eth_hash.auto import keccak

WALLETD = "http://127.0.0.1:18924/"
RPC = "https://sepolia.base.org"
TB = "0x86F55A04690fd7815A3D802bD587e83eA888B239"
BURNER = "0xYOUR_BURNER_WALLET"
WRAPPED = "0x5fcafeb2664dc23e945faac63d1264adbf56ad9b"
CHAIN_ID = 84532

def rpc(url, method, params):
    _h = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    if url == WALLETD:  # token pemanggil walletd (2026-10-30)
        _h["X-Walletd-Token"] = open(os.path.expanduser("~/.burner/walletd.token")).read().strip()
    req = urllib.request.Request(url, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(), headers=_h)
    r = json.loads(urllib.request.urlopen(req, timeout=30).read())
    if r.get("error"): raise RuntimeError(f"{method}: {r['error']}")
    return r["result"]

def bal():
    data = "0x" + keccak(b"balanceOf(address)")[:4].hex() + "000000000000000000000000" + BURNER[2:].lower()
    return int(rpc(RPC, "eth_call", [{"to": WRAPPED, "data": data}, "latest"]), 16)

before = bal()
print("wrapped SUI balance BEFORE:", before)
vaa = base64.b64decode(open("/home/user/workspace/superagentic-wallet/sui-faucet/vaa2.txt").read().strip())
pad = (32 - len(vaa) % 32) % 32
enc = "%064x" % 32 + "%064x" % len(vaa) + (vaa + b"\x00" * pad).hex()
data = "0x" + keccak(b"completeTransfer(bytes)")[:4].hex() + enc
nonce = int(rpc(RPC, "eth_getTransactionCount", [BURNER, "pending"]), 16)
gp = int(rpc(RPC, "eth_gasPrice", []), 16)
tx = {"from": BURNER, "to": TB, "data": data, "value": 0, "gas": 600000, "chainId": CHAIN_ID, "nonce": nonce, "gasPrice": max(gp * 2, 20_000_000)}
h = rpc(WALLETD, "eth_sendTransaction", [tx])
print("completeTransfer tx:", h)
receipt = None
t0 = time.time()
while time.time() - t0 < 240:
    try: receipt = rpc(RPC, "eth_getTransactionReceipt", [h])
    except Exception: receipt = None
    if receipt: break
    time.sleep(5)
print("receipt status:", receipt["status"] if receipt else None, "gasUsed:", int(receipt["gasUsed"], 16) if receipt else None)
after = bal()
print("wrapped SUI balance AFTER:", after, "delta:", after - before)
out = {"completeTransfer_tx": h, "status": receipt["status"] if receipt else None,
       "wrapped_sui": WRAPPED, "balance_before": before, "balance_after": after,
       "eth_balance_wei": int(rpc(RPC, "eth_getBalance", [BURNER, "latest"]), 16)}
json.dump(out, open("/home/user/workspace/superagentic-wallet/sui-faucet/complete_transfer2_result.json", "w"), indent=1)
print(json.dumps(out, indent=1))
