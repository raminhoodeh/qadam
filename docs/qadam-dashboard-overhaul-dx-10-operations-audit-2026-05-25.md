# Qadam Dashboard Overhaul DX-10 Operations Audit

Date: 2026-05-25

Stage: DX-10 - Operations Workspace

## Result

DX-10 is complete. The dashboard now has a dedicated Operations workspace for
expert diagnostics, while Overview remains the simpler first-read experience.

## Implemented Scope

- Moved the full system connectivity view into a purpose-built Operations
  workspace.
- Kept the System Operating Map backed by the shared
  `system_connectivity_model`.
- Added first-class operating-role nodes for the Fund Manager, live data feed
  clusters, Python COO, local LLM Research Analyst, frontier LLM Strategy Lead,
  quantum/classical Head of Quant, Signal/Risk Gates, Paper Lifecycle, and
  Learning Loop.
- Added expandable diagnostics for every system-map node: purpose, inputs,
  outputs, current status, latest heartbeat, dependencies, degraded reasons,
  Event Log references, authority boundary, and related dashboard links.
- Added expandable feed clusters for the five intelligence pipelines and
  provenance rows for canonical replay, Yahoo Finance, and Preference MCP.
- Added edge-state rendering for active, shadow/context-only, degraded, locked,
  and blocked handoffs.
- Added read-only runtime diagnostics for bridge/snapshot state,
  exporter/cache/signature state, module health, phase/certification state, and
  kill-switch ledger state.
- Added a compact "what is broken?" summary and persistent safety rail.

## Safety Boundary

Operations is diagnostics only. It cannot expose shell access, run commands,
approve trades, stage orders, write brokers, mutate kill switches, grant proof
credit, or enable live capital.

The rendered workspace must not expose local paths, secret names, API keys, raw
payloads, request bodies, broker identifiers, or private payloads.

## Verification

New checker:

```bash
node scripts/check_dashboard_overhaul_operations.js
```

Expected summary:

```text
dashboard_overhaul_operations=ok
dashboard_operations_authority_unchanged=True
```

Preflight now includes the DX-10 checker:

```bash
./scripts/preflight_dashboard_deployment.sh
```

## Handoff

DX-11 - Governance And Communications Workspace may proceed next.
