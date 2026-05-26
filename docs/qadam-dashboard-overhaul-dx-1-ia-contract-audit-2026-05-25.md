# Qadam Dashboard Overhaul DX-1 IA Contract Audit

Date: 2026-05-25

Stage: DX-1 - Information Architecture Contract

## Result

DX-1 is complete.

```text
dx1_ia_contract_defined=True
dashboard_primary_view_count=7
dashboard_current_section_count=13
dashboard_all_sections_mapped=True
dashboard_orphan_panel_count=0
dashboard_system_map_compact_destination=overview
dashboard_system_map_expanded_destination=operations
dashboard_first_time_tour_rewritable=True
dashboard_authority_unchanged=True
dx2_implementation_allowed=True
```

## Contract

The enforceable IA contract is now defined in:

```text
docs/qadam-dashboard-overhaul-dx-1-ia-contract.json
```

The contract defines seven primary views:

| Order | View | Entry Question |
| --- | --- | --- |
| 1 | Overview | What should I know first? |
| 2 | Trades | What happened to setups, candidates, orders, positions, exits, and postmortems? |
| 3 | Sources | Are Qadam's inputs fresh, trustworthy, and sufficient? |
| 4 | Reasoning | Why does Qadam care, and what is still missing? |
| 5 | Performance | Is the paper/demo-proof account proving anything? |
| 6 | Operations | Is the runtime, bridge, exporter, system map, and safety plumbing healthy? |
| 7 | Governance | What comments, approvals, reviews, and communications need attention? |

The first static dashboard release should use hash-state tabs within
`/dashboard/`, with `#overview` as the default view. Legacy section anchors
remain mapped so old deep links can redirect into the relevant segmented view
instead of failing silently.

## Existing Section Mapping

Every current `data-cockpit-section` in `landing-page-repo/dashboard/index.html`
has a destination:

| Current Section | Destination View | Visibility |
| --- | --- | --- |
| Mission Control | Overview | Primary |
| Strategy | Reasoning | Secondary |
| System Map | Operations | Secondary |
| Review Sequence | Overview | Demoted |
| Sources | Sources | Primary |
| Cognition | Reasoning | Primary |
| Safety | Operations | Primary |
| Communications | Governance | Secondary |
| Trade Layer | Trades | Primary |
| Money | Performance | Primary |
| Process Console | Operations | Demoted |
| Private Edge | Reasoning | Secondary |
| Governance | Governance | Primary |

## System Map Placement

The system map has two defined homes:

| Placement | View | Scope | Model |
| --- | --- | --- | --- |
| Overview mini-map | Overview | Compact | `system_connectivity_model` |
| Operations full map | Operations | Expanded | `system_connectivity_model` |

This preserves the requested connectivity concept while avoiding the current
problem where a first-time user must read the full operating graph before they
understand what is happening.

## Demoted Panels

These panels are no longer first-level dashboard concepts in the new IA:

- `strategy-manifestation`
- `system-map`
- `review-sequence`
- `communications`
- `process-console`
- `worldview`

They remain available in the segmented destination views. No panel is removed
or orphaned.

## Verification

Added:

```text
scripts/check_dashboard_overhaul_ia_contract.js
```

The checker verifies:

- The seven primary views exist in the required order.
- `/dashboard/` uses the first-release hash-tab contract.
- Every existing dashboard cockpit section has one destination.
- No IA mapping points at a missing current section.
- Required high-risk mappings are fixed: Trades, Sources, Reasoning,
  Performance, Operations, Governance.
- The system map has both compact and expanded destinations.
- Legacy anchor compatibility covers all current dashboard sections.
- The first-time tour can be rewritten against the seven-view IA.
- The IA is explicitly read-only and does not alter authority.

Commands run:

```bash
node --check scripts/check_dashboard_overhaul_ia_contract.js
node scripts/check_dashboard_overhaul_ia_contract.js
```

Full dashboard preflight was also rerun after adding the checker.

## Authority Review

This stage is presentation planning only.

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

## Exit Gate

DX-1 exit gate passed.

DX-2 - Copy And Terminology System may proceed next.
