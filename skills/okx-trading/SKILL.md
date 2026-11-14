# SKILL.md — okx-trading

Trade and manage an OKX exchange account via the `custom.okx` connector
(Python helper with OKX REST API v5). Use for: checking balances/positions,
placing/cancelling spot & futures orders, and reading market data on OKX.

## Available connectors

- `custom.okx` (`~/workspace/custom-connectors/custom.okx/CONNECTOR.md`) —
  the only supported route. There is no managed OKX connection.

## Key handover model (read this first)

- The API secret **cannot** be stored in Muse's managed credential flow
  (OKX uses HMAC-signed requests, which that flow declines) and must never
  be written to disk, env vars, command lines, or logs.
- The user provides key + secret + passphrase **per session**, via chat or
  another channel they explicitly choose. Offer the Secure Vault first only
  if they haven't already chosen to share it directly.
- Pass credentials to the helper **only via stdin JSON** (see connector doc).
  Use them transiently for the requested task, then drop them. Never reuse
  a key from an earlier session; ask again.

## Safety rules (non-negotiable)

1. **Demo first.** Until the user explicitly approves live trading, run every
   order through demo mode (`"demo": true` → `x-simulated-trading: 1`).
2. **One approval per live trade.** Amount, side, pair, and order type must
   be confirmed by the user (approval card) before any live `trade/order`
   call. Never batch unapproved trades.
3. **No withdrawal permission, ever.** If the user's key has withdrawal
   rights, refuse trading use and ask them to rotate to a trade-only key.
   Recommend a sub-account funded with only the allocated amount.
4. **Verify before acting.** Check balance/positions before placing orders;
   re-check order status after placing; on any uncertain write, inspect
   current state before retrying.
5. **Read-only default.** Balance, positions, tickers, and klines need no
   approval. Anything that moves funds or places/cancels orders does.
6. Keep request volume modest (ordinary app use). Stop on 429/rate-limit.

## Common flows

Balance:
`{"method":"GET","path":"/api/v5/account/balance"}` (+ credentials via stdin)

Market buy 0.001 BTC-USDT (demo):
`{"demo":true,"method":"POST","path":"/api/v5/trade/order",
  "body":{"instId":"BTC-USDT","tdMode":"cash","side":"buy",
          "ordType":"market","sz":"0.001"}}`

Cancel order:
`{"method":"POST","path":"/api/v5/trade/cancel-order",
  "body":{"instId":"BTC-USDT","ordId":"<id>"}}`

Klines (public, no key):
`{"method":"GET","path":"/api/v5/market/candles",
  "params":{"instId":"BTC-USDT","bar":"1H","limit":"24"}}`
