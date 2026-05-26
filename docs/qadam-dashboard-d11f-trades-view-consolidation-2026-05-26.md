# Qadam Dashboard D11F - Trades View Consolidation

Date: 2026-05-26

## Scope

D11F consolidates the Trades view so it reads as one lifecycle workspace with
three diagnostic drawers, instead of a lifecycle board followed by many flat
duplicate panels.

## Changes

- Removed the obsolete static trade-route strip from the Trades panel.
- Removed the duplicate Trade Layer panel brief from the rendered Trades view.
- Added one consolidated trade readout under the lifecycle board.
- Grouped diagnostics into three review drawers:
  - Proof and paper lifecycle.
  - Gate chain and broker readiness.
  - Signals, candidates, and paper states.
- Preserved the existing backend-derived diagnostic sections inside those
  groups so phase checks and public-safe evidence remain visible.
- Kept candidate/order and proof-credit boundaries explicit.

## Authority Boundary

D11F is presentation-only. It does not change trade lifecycle data, risk
policy, broker reconciliation, dry-run receipt behavior, proof-credit rules,
provider calls, broker routes, Telegram command behavior, live-capital state,
or execution authority.

## Acceptance

- `scripts/check_dashboard_d11f_trades_view_consolidation.js`
- Existing Trades, trade board, phase, renderer, and deployment preflight checks
  must continue to pass.
