# SKILL.md — browser-wallet-connector

Use the `custom.browser-wallet` connector (Chrome MV3 extension) when a
dApp only detects an injected "Browser Wallet" and no extension wallet can
be driven by the agent — e.g. Elysium quests on `elysiumeco.xyz`. The
extension injects an EIP-1193 provider (`window.ethereum`) for the
operational non-extension wallet and signs locally.

## Available connectors

- `custom.browser-wallet`
  (`~/workspace/custom-connectors/custom.browser-wallet/CONNECTOR.md`) —
  the only supported route for injected-provider detection. Read it before
  first use; the security model there is binding.

## Safety rules (non-negotiable)

1. **Testnet only.** Elysium testnet, chain 99801 (`0x185d9`). Never use
   this connector for mainnet, another chain, or real funds.
2. **Key setup is manual, one time, by the user.** The user pastes the
   private key or seed phrase on the extension's options page; only the
   private key is stored. Never ask for the seed in chat, never write it
   to any file, never print or log it, and never type it into the agent
   browser yourself — the agent cannot open extension UI anyway.
3. **Auto-approve stays OFF unless the user explicitly turns it on.**
   Default cap is 0.05 HYPE; never raise the cap without the user
   agreeing to the new number.
4. **Allowlist only.** The extension refuses signing for origins outside
   its allowlist. Never add an origin the user did not name.
5. **Low gas.** Quest transactions use `eth_estimateGas` and a gas price
   clamped to 0.1–0.2 gwei. Never push aggressive gas for farming/quests.
6. **Verify before and after.** Check the wallet address and balance
   before a quest; re-check the transaction receipt and the quest's
   completed/claimed state after. On any uncertain write, inspect current
   state before retrying — never repeat an action whose outcome is
   unknown.
7. **One approval per out-of-policy step.** Anything beyond the day's
   listed quests, above the cap, or on a non-allowlisted origin needs the
   user's explicit say-so first.

## Setup — CURRENTLY NO INSTALL ROUTE

There is NO desktop Chrome in this setup; the only browser in use is
the agent's browser, and the extension cannot be installed into it from
this VM (no profile access, `chrome://` blocked for the agent, Web
Store flow broken, extension files on this VM unreachable from that
browser's file picker). `Load unpacked` does NOT apply. Do not instruct
the user to install it in "desktop Chrome".

The steps below apply only once an install route exists:

1. `chrome://extensions` → Developer mode → **Load unpacked** →
   select `~/workspace/custom-connectors/custom.browser-wallet/extension/`.
2. Open the extension's **Options**, paste the private key or the 12-word
   seed phrase, check the derived address matches the operational wallet,
   save. (Only the private key is stored; the seed is never stored.)
3. Confirm the popup shows the wallet address, chain 99801, auto-approve
   OFF, and the allowlist.

## Common flows

Check detection (in the browser where the extension is loaded):
open `https://elysiumeco.xyz/me/` — it must show the wallet instead of
"No wallet in this browser". If it still shows that, the extension is not
loaded in that browser profile; check `chrome://extensions`.

Sign-in: on the dApp, connect "Browser Wallet" and sign the free text
signature (`personal_sign`). No transaction, no funds move.

Quest transaction: perform the quest action in the dApp (swap, bid, mint).
With auto-approve OFF, a confirmation popup shows origin, method, and
value — approve only if all three match the quest. With auto-approve ON,
only allowlisted origin + chain 99801 + value ≤ cap auto-signs.

Verify a quest: after the transaction, check the receipt on the Elysium
explorer/RPC and confirm the Quests page marks it completed, then claim
the XP the same day (before 00:00 UTC).

## Troubleshooting

- **"No wallet in this browser"** — the extension is not loaded in that
  Chrome profile, or the site is not in the allowlist. Re-check
  `chrome://extensions` (extension enabled?) and the options page.
- **Confirmation popup never appears** — auto-approve is OFF and the
  popup could not open; the request is rejected by design. Approve from a
  normal (non-headless) Chrome window, or turn auto-approve ON for
  allowlisted origins within the cap (user decision).
- **Request rejected with 4100** — origin not in the allowlist, or the
  wallet has no key configured. Add the origin (user-named only) or
  finish key setup.
- **Request rejected with 4902** — a non-99801 chain was requested. This
  connector is testnet-only; do not work around it.
- **Agent browser cannot install it, and there is no desktop Chrome
  either** — known limit. The agent's browser runs in a separate VM
  with no profile access and `chrome://` blocked, and the extension
  files on this VM are unreachable from that browser's file picker, so
  `Load unpacked` does not apply. Until an install route into the
  agent's browser exists, this connector cannot be used; use the
  remaining routes instead (user imports the seed into Rabby in the
  agent browser via takeover, or connects via a phone wallet app).
