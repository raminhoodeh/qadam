# Qadam Dashboard Overhaul DX-4 Segmented Shell Audit

Date: 2026-05-25

Stage: DX-4 - Segmented Shell

## Result

DX-4 is complete.

```text
dx4_segmented_shell_added=True
dashboard_default_view=overview
dashboard_segmented_views_enabled=True
dashboard_primary_view_count=7
dashboard_segmented_section_count=13
dashboard_legacy_anchor_redirects=True
dashboard_mobile_tap_targets_stable=True
dashboard_authority_unchanged=True
dx5_implementation_allowed=True
```

## Implementation

The static dashboard now has a seven-view shell:

1. Overview
2. Trades
3. Sources
4. Reasoning
5. Performance
6. Operations
7. Governance

The primary switcher is defined in:

```text
landing-page-repo/dashboard/index.html
```

Existing dashboard sections are tagged with `data-dashboard-view-section` and
the browser shows only sections belonging to the active view. `/dashboard/`
starts on Overview. Non-Overview sections are hidden in the static HTML until
JavaScript activates their view.

## Section Routing

| View | Sections |
| --- | --- |
| Overview | `mission-control`, `review-sequence` |
| Trades | `trade-layer` |
| Sources | `watching` |
| Reasoning | `strategy-manifestation`, `cognition`, `worldview` |
| Performance | `money` |
| Operations | `system-map`, `forbidden`, `process-console` |
| Governance | `communications`, `governance` |

This keeps every existing panel reachable while replacing the old long-page
default with a segmented shell.

## URL Behavior

Direct view hashes are supported:

- `#overview`
- `#trades`
- `#sources`
- `#reasoning`
- `#performance`
- `#operations`
- `#governance`

Legacy section hashes are preserved as compatibility redirects into the correct
view:

- `#mission-control` -> Overview
- `#review-sequence` -> Overview
- `#trade-layer` -> Trades
- `#watching` -> Sources
- `#cognition` -> Reasoning
- `#strategy-manifestation` -> Reasoning
- `#worldview` -> Reasoning
- `#money` -> Performance
- `#system-map` -> Operations
- `#forbidden` -> Operations
- `#process-console` -> Operations
- `#communications` -> Governance
- `#governance` -> Governance

The shell stores per-view scroll positions where browser storage is available.

## Verification

Added:

```text
scripts/check_dashboard_overhaul_shell.js
```

The checker verifies:

- seven primary view links in DX-1 order
- `/dashboard/` starts on Overview
- 13 current dashboard sections are mapped into segmented views
- non-Overview sections are hidden by default
- view activation shows only the target view's sections
- legacy section hashes resolve to the correct new view
- mobile tap targets stay stable
- shell changes do not add authority

Commands run:

```bash
node --check landing-page-repo/dashboard.js
node --check scripts/check_dashboard_overhaul_shell.js
node scripts/check_dashboard_overhaul_shell.js
node scripts/check_dashboard_navigation_ux.js
node scripts/check_dashboard_renderer.js
```

Full dashboard preflight was also rerun after adding the shell checker.

## Authority Review

This stage is a presentation shell only.

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

DX-4 exit gate passed.

DX-5 - Overview First Screen may proceed next.
