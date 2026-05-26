# Qadam Dashboard D11K - View Model Refactor

Date: 2026-05-26

## Purpose

D11K tightens the dashboard renderer contract. The dashboard already exposed
view models, but several visible sections still rebuilt their own model slices
from the raw status snapshot. That made the data path harder to reason about
and increased the chance of duplicate or inconsistent presentation logic.

## Changes

- `buildQadamDashboardViewModels` now builds one shared model bundle per
  snapshot and records a `model_graph` with the build order and dependencies.
- Trades receives the already-built Sources/Evidence model.
- Operations receives the already-built System Connectivity and Governance
  models.
- Overview receives the already-built Sources, Trades, Reasoning, Performance,
  Operations, and System Connectivity models.
- Safety Strip receives the already-built Operations and Performance models.
- Evidence, Reasoning, Trades, Performance, and Governance renderers now accept
  the shared view-model bundle from `renderQadamDashboardStatus`.
- Legacy fallbacks remain in those renderers so focused tests and direct calls
  can still render from raw status.

## Acceptance

- One canonical dashboard view-model bundle is built for each status render.
- The model graph documents shared dependencies.
- Renderers consume `viewModels` from the canonical render path.
- The top-level schema remains compatible as `dashboard_view_models.v1`, while
  `model_contract_version` identifies the D11K shared-bundle contract.
- Public-safe and authority-boundary checks remain unchanged.
- Runtime authority, provider calls, broker writes, Telegram command behavior,
  proof-credit rules, and live-capital state are unchanged.
