# Qadam Dashboard Overhaul DX-6 Trades Audit

Date: 2026-05-25
Stage: DX-6 - Trades Workspace
Status: complete

## Result

dx6_trade_lifecycle_workspace_added=True
dashboard_trades_lifecycle_records_visible=True
dashboard_candidates_not_orders=True
dashboard_phase5_phase7_trade_partition=True
dashboard_trade_evidence_links_visible=True
dashboard_trade_filters_enabled=True
dashboard_trade_workspace_authority_unchanged=True
dx7_implementation_allowed=True

## Implementation

- Added a trades workspace at the top of the Trades view in
  `landing-page-repo/dashboard.js`.
- Consolidated observed signals, Phase 7 setup state, candidates, blocked
  ideas, staged orders, submitted paper orders, open positions, closed paper
  trades, and postmortems due into one lifecycle board.
- Added filters for all, active, blocked, open, closed, and postmortem due.
- Added a lifecycle strip so the Fund Manager can see the current count in each
  stage before reading individual cards.
- Added evidence links for source quorum, risk decision, and broker receipt
  sections.
- Added Phase 5 test lifecycle and Phase 7 proof-trade partitions so paper
  test evidence is not visually merged with demo-proof evidence.
- Preserved the existing detailed trade cards below the workspace for deeper
  review.

## Model Changes

- `trades_model.lifecycle_records` now exposes display-safe lifecycle records
  with stage, instrument, direction, source quorum, risk decision, broker
  receipt status, evidence references, filter states, proof scope, and read-only
  boundary text.
- `trades_model.lifecycle_filters` provides the filter labels and counts used by
  the workspace controls.
- `trades_model.proof_partitions` separates Phase 5 test lifecycle state from
  Phase 7 proof-trade state.
- Capital-ledger paper orders are counted as submitted lifecycle records so the
  lifecycle strip and lifecycle cards agree.

## Safety Review

- The dashboard remains read-only.
- No approval, order placement, order close, broker-write, funding, Telegram
  send, learning-write, policy-mutation, or live-capital route was added.
- Candidates stay visibly distinct from submitted paper orders.
- Phase 5 test lifecycle records explicitly do not count for Phase 7 proof.
- Phase 7 proof credit is not granted by the UI model.
- Broker receipt links are evidence references only; they do not expose a submit
  or mutate path.

## Verification

Expected checks:

```bash
node --check landing-page-repo/dashboard.js
node --check scripts/check_dashboard_overhaul_trades.js
node scripts/check_dashboard_overhaul_trades.js
node scripts/check_dashboard_trade_board.js
node scripts/check_dashboard_renderer.js
node scripts/check_dashboard_overhaul_view_models.js
node scripts/check_dashboard_overhaul_overview.js
./scripts/preflight_dashboard_deployment.sh
```

The DX-6 checker verifies:

- Trades workspace static shell exists.
- Trades CSS supports the lifecycle board, filters, proof partitions, evidence
  links, and cards.
- Renderer exports lifecycle records and filter behavior.
- Capital-ledger paper orders count as submitted lifecycle records.
- Candidate records are active but not open or closed orders.
- Phase 5 test trades cannot count for Phase 7 proof.
- Rendered HTML includes observed, candidate, blocked, submitted, closed, and
  postmortem due states.
- Evidence links route to source quorum, risk decision, and broker receipt
  sections.

## Next Stage

DX-7 - Sources Workspace may proceed next.
