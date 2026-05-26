# Qadam Dashboard Overhaul DX-2 Copy System Audit

Date: 2026-05-25

Stage: DX-2 - Copy And Terminology System

## Result

DX-2 is complete.

```text
dx2_copy_system_defined=True
dashboard_copy_primary_view_count=7
dashboard_copy_term_count=23
dashboard_copy_empty_state_count=8
dashboard_internal_codes_diagnostic_only=True
dashboard_phase_labels_secondary_only=True
dashboard_overview_primary_copy_bans_internal_codes=True
dashboard_safety_boundaries_explicit=True
dashboard_authority_unchanged=True
dx3_implementation_allowed=True
```

## Contract

The enforceable copy system is defined in:

```text
docs/qadam-dashboard-overhaul-dx-2-copy-system.json
```

It defines:

- user-facing replacements for internal D-codes, Q-codes, phase labels, and
  runtime jargon
- primary-copy rules for all seven DX-1 views
- Overview bans for unexplained `D0`, `D1`, `D5`, `D7`, `D9`, `Q4`, `Q5`,
  `Q5E`, `Q6`, `Q7`, and phase-first labels
- Operations-only diagnostic handling for internal codes
- secondary-only handling for phase labels
- plain empty-state language for normal no-setup, no-trade, no-position,
  no-postmortem, blocked, stale, degraded, and missing-status states
- explicit safety phrases that must remain visible

## Plain Language Policy

Primary dashboard views should lead with operating-state language:

| Internal / Technical Term | Primary Label |
| --- | --- |
| `D0` | Browser dashboard preview |
| `D1` | Public-safe status snapshot |
| `D9` | Read-only live status connection |
| `Q4` / Phase 4 | Strategy governance |
| `Q5` / Phase 5 | Paper trade orchestration |
| `Q6` / Phase 6 | Learning review loop |
| `Q7` / Phase 7 | 30-day demo-proof run |
| static snapshot | Saved status snapshot |
| secure bridge | Read-only live status connection |
| shadow toggles | Review-only strategy visibility |

Trade lifecycle copy remains explicit because those distinctions are safety
critical:

- observed signal
- qualified setup
- candidate
- draft paper order
- submitted paper order
- open position
- closed paper trade
- postmortem due

## Safety Copy

The copy system requires these phrases to stay explicit:

- read-only
- paper/demo only
- live capital disabled
- broker writes blocked
- candidate is not an order

These are not treated as jargon. They are safety boundaries.

## Verification

Added:

```text
scripts/check_dashboard_overhaul_copy_system.js
```

The checker verifies:

- DX-2 view order matches the DX-1 IA contract.
- Every view has a copy rule.
- required internal terms have plain labels and explanations.
- internal codes are not allowed in primary copy.
- phase labels are secondary diagnostics only.
- Overview primary-copy bans cover the known D/Q/phase/runtime terms.
- empty states are plain-language and avoid internal codes.
- blocked and missing empty states preserve authority boundaries.
- safety phrases remain explicit.

Commands run:

```bash
node --check scripts/check_dashboard_overhaul_copy_system.js
node scripts/check_dashboard_overhaul_copy_system.js
```

Full dashboard preflight was also rerun after adding the checker.

## Authority Review

This stage is copy and terminology governance only.

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

DX-2 exit gate passed.

DX-3 - Dashboard View Model Layer may proceed next.
