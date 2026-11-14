#!/bin/bash
# Wrapper: adds flags needed for Remotion rendering on this VM
# - no-sandbox (running as root)
# - Local Network Access bypass (Remotion serves bundle on localhost)
# - disable-dev-shm-usage (small /dev/shm in sandbox)
# NOTE: Remotion's own headless-shell download is BLOCKED on this VM
# (egress), so rendering MUST use a local Chromium.
# /opt/meta-chromium/chrome (v152) does NOT render here (blank output,
# localhost blocked) — use Playwright's Chrome for Testing 156 instead
# (verified 2026-10-28: renders localhost fine).
exec /home/user/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome \
  --no-sandbox \
  --disable-dev-shm-usage \
  --disable-features=LocalNetworkAccessChecks,BlockInsecurePrivateNetworkRequests,PrivateNetworkAccessSendPreflights \
  "$@"
