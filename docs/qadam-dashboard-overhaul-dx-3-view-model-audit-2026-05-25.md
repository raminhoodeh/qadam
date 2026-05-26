# Qadam Dashboard Overhaul DX-3 View Model Audit

Date: 2026-05-25

Stage: DX-3 - Dashboard View Model Layer

## Result

DX-3 is complete.

```text
dx3_view_model_layer_added=True
dashboard_view_model_count=7
dashboard_connectivity_node_count=27
dashboard_connectivity_edge_count=21
dashboard_system_map_shared_model=True
dashboard_missing_state_fixture_passed=True
dashboard_stale_state_fixture_passed=True
dashboard_empty_state_fixture_passed=True
dashboard_degraded_state_fixture_passed=True
dashboard_active_proof_fixture_passed=True
dashboard_dishonest_payload_probes_passed=True
dashboard_authority_unchanged=True
dx4_implementation_allowed=True
```

## Implementation

The dashboard now exposes pure presentation view-model builders in:

```text
landing-page-repo/dashboard.js
```

The exported builders are:

- `window.buildQadamDashboardViewModels`
- `window.buildQadamDashboardOverviewModel`
- `window.buildQadamDashboardTradesModel`
- `window.buildQadamDashboardSourcesModel`
- `window.buildQadamDashboardReasoningModel`
- `window.buildQadamDashboardPerformanceModel`
- `window.buildQadamDashboardSystemConnectivityModel`
- `window.buildQadamDashboardOperationsModel`
- `window.buildQadamDashboardGovernanceModel`

The current renderer still renders through the existing DOM path. DX-3 only
adds the presentation adapter that DX-4 and DX-5 can use to build the segmented
shell and Overview without re-parsing raw cockpit status in every view.

## Model Coverage

The top-level view model contains:

| Model | Purpose |
| --- | --- |
| `overview_model` | First-screen operating readout, lifecycle summary, action-needed summary, and mini-map references. |
| `trades_model` | Observed signals, qualified setups, candidates, paper lifecycle states, and postmortem due state. |
| `sources_model` | Source health, source quorum, missing credentials, and supplemental data planes. |
| `reasoning_model` | Hypotheses, evidence packets, local research, Strategy Lead context, and quant-readiness posture. |
| `performance_model` | Paper account state, drawdown, closed paper trades, demo-proof maturity, and proof-credit display gating. |
| `system_connectivity_model` | Nodes, lanes, edges, feed clusters, health states, authority boundaries, and expanded detail. |
| `operations_model` | Runtime health, live bridge state, process events, safety flags, and full connectivity model. |
| `governance_model` | Fund Manager comments, approval state, learning review state, and communications posture. |

The Overview mini-map and Operations full map both reference
`system_connectivity_model`. The full model is owned by Operations; Overview
uses the compact `overview_scope` node keys from the same model.

## Safety And Dishonest Payload Probes

The checker verifies that the view-model layer handles:

- missing status
- stale status
- empty no-trade / no-position state
- degraded source quorum
- active proof maturity
- online, degraded, blocked, pending, local-only, read-only, supplemental, and
  shadow-only system nodes
- UI-inferred readiness
- hidden live capital
- missing source quorum
- false Phase 7 proof credit

False proof credit is kept visible as backend-reported status, but it is not
converted into displayed proof credit unless the closed-proof-trade and 30-day
maturity conditions are also satisfied.

## Verification

Added:

```text
scripts/check_dashboard_overhaul_view_models.js
```

Commands run:

```bash
node --check landing-page-repo/dashboard.js
node --check scripts/check_dashboard_overhaul_view_models.js
node scripts/check_dashboard_overhaul_view_models.js
```

Full dashboard preflight was also rerun after adding the checker.

## Authority Review

This stage is a read-only projection layer.

It does not add or modify:

- trade approval authority
- candidate creation authority
- staged-order authority
- paper broker write authority
- live-capital authority
- Telegram command authority
- provider call authority
- source mutation authority
- quantum hardware submission authority
- learning-write authority

## Exit Gate

DX-3 exit gate passed.

DX-4 - Segmented Shell may proceed next.
