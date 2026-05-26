# Qadam Dashboard Overhaul DX-0 Baseline Audit

Date: 2026-05-25

Stage: DX-0 - Baseline Audit And Freeze

## 1. Result

DX-0 captured the current local and deployed dashboard baseline before any
dashboard overhaul implementation.

```text
dashboard_overhaul_baseline_captured=True
dashboard_implementation_change_made=False
dashboard_authority_change_made=False
dashboard_existing_dashboard_checks_pass=False
dx0_exit_gate_passed=False
dx0_blocker=dashboard_money_panel_preflight_maturity_text_mismatch
```

The stage is useful and complete as a baseline capture, but the formal DX-0
exit gate is blocked because the broader dashboard deployment preflight exposed
an existing money-panel assertion mismatch. No dashboard HTML, CSS, JS, auth, or
runtime implementation file was changed for this stage.

## 2. Current Local Dashboard Shape

Local dashboard files:

| File | Current Size |
| --- | ---: |
| `landing-page-repo/dashboard/index.html` | 947 lines |
| `landing-page-repo/dashboard.js` | 3997 lines |
| `landing-page-repo/auth.css` | 2852 lines |

Current local dashboard structure:

| Metric | Value |
| --- | ---: |
| Top nav links | 10 |
| `data-cockpit-section` sections/articles | 13 |
| Info buttons | 14 |
| Panel cards | 9 |
| Static metric tiles | 26 |
| Native `<details>` disclosures | 1 |

Current local nav order:

1. Mission
2. Map
3. Sources
4. Cognition
5. Strategy
6. Trades
7. Money
8. Safety
9. Runtime
10. Governance

Current local DOM/data-section order:

1. Mission Control
2. Strategy
3. System Map
4. Review Sequence
5. Sources
6. Cognition
7. Safety
8. Communications
9. Trade Layer
10. Money
11. Process Console
12. Private Edge
13. Governance

Baseline UX finding: the local nav order and DOM order already disagree.
Communications and Private Edge exist in the DOM but are not first-level nav
items. Strategy appears earlier in the DOM than its operating relevance for a
new user.

## 3. Current Deployed Dashboard Shape

Live `https://qadam.trade/dashboard/` was fetched during DX-0.

Current deployed cache keys:

- CSS: `/auth.css?v=20260521-nav-ux`
- Dashboard JS: `/dashboard.js?v=20260521-nav-ux`
- Auth JS: `/auth.js?v=20260517-d9-release`

Current deployed nav order:

1. Mission
2. Map
3. Sources
4. Cognition
5. Trades
6. Money
7. Safety
8. Runtime
9. Governance

Current deployed DOM/data-section order:

1. Mission Control
2. System Map
3. Review Sequence
4. Sources
5. Cognition
6. Safety
7. Communications
8. Trade Layer
9. Money
10. Process Console
11. Private Edge
12. Governance

Baseline deployment finding: the deployed dashboard is behind the local working
tree. The local shell includes Strategy in the nav/DOM; the deployed shell does
not. Any overhaul implementation must treat live/local parity as a deployment
verification requirement, not an assumption.

## 4. Status Source Baseline

`landing-page-repo/dashboard.js` currently reads status from two sources in
order:

| Source | URL | Auth |
| --- | --- | --- |
| `live_bridge` | `/api/cockpit-status` | Supabase bearer token required |
| `static_snapshot` | `/status/cockpit-status.json` | no auth header |

The dashboard fetcher uses `cache: "no-store"` and only reads status JSON. It
does not call broker, paper-submit, prediction-market, Telegram-command, or
hardware-submission endpoints.

Current local public-safe status snapshot:

| Field | Value |
| --- | --- |
| `schema_version` | `1` |
| `generated_at` | `2026-05-25T22:29:38.141467+00:00` |
| `mode` | `paper` |
| top-level key count | `49` |
| module count | `29` |
| watched source count | `36` |
| pipeline count | `5` |
| forbidden action count | `9` |
| process event count | `8` |
| live capital | `False` |
| D1 read-only | `True` |
| D1 public-safe | `True` |
| D1 browser authority | `read_only` |
| Mission headline | `13/36 sources online; 5 hypotheses; 1 candidates; 0 open positions; live capital disabled.` |

Current deployed public-safe status snapshot:

| Field | Value |
| --- | --- |
| `schema_version` | `1` |
| `generated_at` | `2026-05-21T22:39:36.613419+00:00` |
| `mode` | `paper` |
| top-level key count | `29` |
| module count | `28` |
| watched source count | `36` |
| forbidden action count | `9` |
| process event count | `8` |
| live capital | `False` |
| Mission headline | `13/36 sources online; 5 hypotheses; 1 candidates; 0 open positions; live capital disabled.` |

Baseline data finding: the live status snapshot is older and materially smaller
than the local status snapshot. The overhaul certification stage must verify
that deployed `/dashboard/` and deployed `/status/cockpit-status.json` are both
updated together.

## 5. Auth And Authority Baseline

Supabase/allowlist gating remains active in the deployed auth script:

- `wireDashboard()` calls `qadamAuth.auth.getSession()`.
- Unauthenticated users are redirected to `/login/`.
- Non-allowlisted users are signed out and redirected to login with
  `error=not-allowlisted`.
- The dashboard remains hidden until the session and allowlist checks pass.
- Dashboard status rendering receives the Supabase session so the read-only
  bridge can send a bearer token when available.

Browser write paths found in the static site:

| Path | Purpose | Authority Risk |
| --- | --- | --- |
| Fund Manager comment insert/update | Supabase comments/forum only | governance notes only |
| Dashboard status fetch | read-only cockpit status | no mutation |
| Login/signup/signout | Supabase auth | no trading authority |

No dashboard browser route was found that can place, modify, close, resize,
cancel, approve, reject, fund, or submit broker/paper/prediction-market trades.

## 6. Verification Commands

Passing checks:

```text
node --check landing-page-repo/dashboard.js
node scripts/check_dashboard_renderer.js
node scripts/check_dashboard_navigation_ux.js
node scripts/check_dashboard_mission_control.js
node scripts/check_dashboard_phase7_demo_proof.js
node scripts/check_dashboard_live_bridge.js
node scripts/check_protected_user_guide.js
node scripts/check_dashboard_information_hierarchy.js
node scripts/check_dashboard_page_architecture.js
node scripts/check_dashboard_visual_system.js
node scripts/check_dashboard_section_explainers.js
.venv/bin/python scripts/check_cockpit_status.py
```

The broader deployment preflight was also run:

```text
./scripts/preflight_dashboard_deployment.sh
```

It passed the early dashboard acceptance, readiness, renderer, bridge, watching,
cognition, and trade-board checks, then failed in the money-panel check:

```text
[data-capital] did not include expected text: 0 of 100 closed proof trades
```

The direct failing command is:

```text
node scripts/check_dashboard_money_panel.js
```

The current local status has:

```text
capital.closed_trade_count=1
capital.maturity_closed_trade_count=1
capital.maturity_closed_trade_target=100
```

The failing assertion still expects:

```text
0 of 100 closed proof trades
```

Baseline blocker interpretation: the current Money panel/check is mixing a
generic paper closed-trade maturity count with proof-trade language. That is
dangerous for the overhaul because Phase 5 test lifecycle evidence must not be
mistaken for Phase 7 proof credit. This should be resolved before or during the
view-model/copy stages, not hidden by relaxing the check.

## 7. Baseline UX Problems To Carry Into DX-1

DX-1 should treat these as hard inputs:

- The live and local dashboards are not at parity.
- The guide, nav, local DOM, and deployed DOM do not share one mental model.
- Communications and Private Edge are not discoverable enough in first-level
  navigation.
- Runtime/build-phase material appears too close to the first-time-user path.
- Money/proof-trade copy needs a stricter distinction between paper lifecycle
  records, Phase 5 test trades, Phase 7 proof trades, and the 100-trade maturity
  benchmark.
- The future Overview mini-map and Operations full map must be derived from one
  shared connectivity model rather than duplicated static UI.

## 8. DX-0 Exit Decision

DX-0 produced the intended freeze/baseline record and made no dashboard
implementation changes.

Formal exit gate:

```text
dashboard_overhaul_baseline_captured=True
dashboard_existing_dashboard_checks_pass=False
dashboard_preflight_passed=False
dashboard_money_panel_proof_trade_mismatch=True
dashboard_authority_unchanged=True
dx1_implementation_allowed=False
```

Recommended next step: run a narrow DX-0 unblock before DX-1 that separates
paper closed-trade count from Phase 7 proof-trade count in the dashboard money
contract/copy/checks, while preserving the read-only status contract and the
rule that Phase 5 test trades do not count as Phase 7 proof.
