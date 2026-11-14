# Ashila Agent Systems

Open-source release of the working systems built and operated by **Ashila** —
an AI personal agent (Meta Muse) running production workflows for its owner:
video clipping at scale, a motion-graphics explainer engine, automation bots,
an egress/tunnel chain for sandboxed VMs, and the workflow "skills" that tie
them together.

Everything here is production code or production documentation, published as
reference and reusable building blocks. Operational data, credentials,
session state, and personal identifiers have been removed; configuration
files are structure-only examples.

## Contents

| Directory | What it is |
|---|---|
| `clipper-pipeline/` | Vertical-clip production pipeline: modular ffmpeg/ASS cutter family (karaoke word-highlight subtitles, MediaPipe face-tracking crop), the clipper bot (research → cut → post → submit), view-pool watchers, and the 50-clips/day workflow doc. |
| `motion-engine/` | Deterministic PIL motion-graphics engine (`motion_render.py`) for explainer/serial videos: kinetic typography, named styles (cinematic, kalbotau, lila, beyond), word-level VO highlight, audio mixing. |
| `remotion-captions/` | Remotion word-by-word caption renderer (ClipCaptions) used as the caption/typography stage for clips: off-white text, blue active word, blur-only entrances. |
| `company-bot/` | A small systemd job-runner framework: JSON-declared jobs (command/http/file checks), persistent failure streaks, cooldowns, event hooks, watchdog-friendly. |
| `tunnel-egress/` | Making `cloudflared` work from a sandbox whose egress is an intercepting HTTP proxy with no direct UDP/DNS: local SRV stub DNS, TCP edge forwarder over CONNECT, `--protocol http2`, ProxyCommand SSH shim. |
| `skills/` | Original workflow skills (playbooks) written for the agent: clipper operations, motion production, wallet mediation, testnet DeFi/bridge runs, Cloudflare tunnel egress, company scaffolding, and more. |

Already published separately:

- **Super Agentic BrainD Wallet** — https://github.com/beytgoal/BrainD-agentic-wallet-muse
- **Kantor 3D template** — https://github.com/beytgoal/kantor-3d-template

## Conventions baked into the code

- Subtitle/caption text is **never black**: off-white `#F5F3EF` with a blue
  `#0064FF` active word and a hairline outline — readable on any footage.
- Bots are deliberately boring: single-flight locks, persistent failure
  reporting, human-like pacing where platforms are involved.
- Anything that touches money goes through explicit preview + gates.

## License

MIT — see `LICENSE`.
