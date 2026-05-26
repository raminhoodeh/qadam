# Qadam Dashboard D11E - Rebuild Overview

Date: 2026-05-26

## Scope

D11E rebuilds the default Overview view so it acts as a short Fund Manager
brief instead of a collection of repeated cards.

## Changes

- Replaced the old Overview status-card grid with one compact proof/status
  strip.
- Replaced the separate hero plus metric-card grid with one command surface:
  the current readout on the left and the review queue on the right.
- Kept only four Overview readouts: source health, trade path, proof run, and
  needs-review.
- Kept the compact system map, but grouped it under one system-summary section.
- Removed duplicated mode, capital, and live-capital copy from Overview because
  those now belong to the D11D single safety strip.
- Preserved the four navigation handoffs: Trades, Evidence, Reasoning, and
  Operations.

## Authority Boundary

D11E is presentation-only. It changes the dashboard's read-only public view and
view model. It does not change provider calls, broker routes, Telegram command
handling, proof-credit rules, live-capital state, or execution authority.

## Acceptance

- `scripts/check_dashboard_d11e_rebuild_overview.js`
- Existing dashboard renderer, Overview, hierarchy, responsive, and acceptance
  checks must continue to pass.
