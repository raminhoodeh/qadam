# Qadam Dashboard Overhaul Master Implementation Plan

Date: 2026-05-25

This document defines the master implementation plan for overhauling
`/dashboard/` from a long cockpit page into a segmented, intuitive operating
surface for first-release founding Fund Managers.

The goal is not to remove Qadam's complexity. The goal is to stop forcing a new
user to understand the implementation graph before they can answer the basic
operating questions:

- Is Qadam running?
- Is it in paper/demo-proof mode?
- Is live capital disabled?
- What is Qadam watching?
- Did it find a qualified setup?
- Is there a paper trade, open position, closed trade, or postmortem due?
- What needs human review?
- What is broken, stale, degraded, or blocked?

The dashboard remains read-only. This overhaul must not create approval,
broker-write, Telegram-command, live-capital, prediction-market-write, hardware
submission, or hidden local-runtime authority.

## 1. Entry Findings

The current dashboard has useful data but weak information architecture.

Problems to solve:

- The user guide, navigation, and DOM order disagree about the first-time tour.
- Important panels such as Communications and Private Edge can exist without
  first-level navigation.
- The page is too long and card-heavy for a first-time read.
- Implementation labels such as `D9`, `D0`, `Q4`, `Phase 4`, static snapshot,
  secure bridge, and shadow toggles appear before the user knows what matters.
- Runtime, governance, strategy certification, source diagnostics, and trade
  state compete for attention in one scroll.
- Hover tooltips carry too much onboarding work and are weak on mobile.
- The dashboard serves several personas at once: Fund Manager, operator,
  auditor, and builder.
- The first viewport does not provide a plain-language answer to "what is
  happening now?"

## 2. Product Principle

The new dashboard should be organized by user question, not by module.

The default view should answer:

```text
What is Qadam doing right now, and does anything need review?
```

Detail views should answer:

| View | User Question | Primary User |
| --- | --- | --- |
| Overview | What is happening now? | Founding Fund Manager |
| Trades | What happened to setups, candidates, orders, positions, exits, and postmortems? | Fund Manager / operator |
| Sources | Are Qadam's inputs fresh, trustworthy, and sufficient? | Fund Manager / operator |
| Reasoning | Why does Qadam care, and what is still missing? | Fund Manager |
| Performance | Is the paper/demo-proof account proving anything? | Fund Manager |
| Operations | Is the runtime, bridge, exporter, system map, and safety plumbing healthy? | Operator / auditor |
| Governance | What comments, approvals, reviews, and communications need attention? | Fund Manager |

## 3. Non-Negotiable UX Rules

- `/dashboard/` opens to `Overview`, not to the full system map.
- The first viewport must show mode, live-capital status, demo-proof state,
  trade state, source state, safety state, and action needed.
- No default view should require reading more than one to two viewport heights.
- Advanced runtime and build-phase data must move behind Operations.
- The system connectivity diagram must appear in two places: a compact mini-map
  in Overview and a full expandable map in Operations.
- Internal phase labels may exist in diagnostics, but not as primary user copy.
- Tooltips may clarify, but must not carry essential onboarding content.
- Mobile users must be able to switch sections without scrolling through the
  entire page.
- Empty states must explain what is absent and why that is normal.
- Every trade state must preserve the distinction between observation,
  hypothesis, candidate, staged paper order, submitted paper order, open
  position, closed trade, and postmortem.
- The UI must never infer readiness from presentation. Readiness comes from the
  backend status contract and runtime artifacts only.

## 4. Proposed Information Architecture

### 4.1 Default Overview

The Overview is the new first screen and should be short. After D11E it is a
Fund Manager brief, not a card wall.

Required readouts:

| Readout | Plain-Language Question | Data Source |
| --- | --- | --- |
| Source health | Are enough sources online and fresh? | `watching`, source registry |
| Trade path | Are there setups, candidates, submitted paper orders, positions, exits, or postmortems? | `trade_layer`, Phase 7 lifecycle |
| Proof run | What day/week of the 30-day proof run is this, and how many proof trades are closed? | Phase 7 cockpit visibility |
| Needs review | What should a Fund Manager review next? | Derived read-only summary from status fields |

Mode, live-capital, broker-path, LLM-path, and proof-credit authority are owned
by the D11D single safety strip and should not be repeated as Overview cards.

The Overview should include one compact timeline:

```text
Source event -> qualified setup -> candidate -> paper order -> position -> exit -> postmortem
```

The Overview should also include a compact system mini-map:

```text
Live feeds -> COO -> Research Analyst -> Strategy Lead -> Head of Quant
             -> Signal/Risk Gates -> Paper Lifecycle -> Learning Loop
```

The Fund Manager should appear above the flow as overseer/reviewer, not as an
execution node. The safety boundary should appear once in the D11D single
safety strip; Overview can reference it but must not render a duplicate rail.

Only completed or active states should be visually emphasized.

### 4.2 Trades

Trades becomes the main lifecycle workspace.

Segments:

- Observed signals.
- Qualified setups.
- Hypotheses and candidates.
- Blocked candidates.
- Staged paper orders.
- Submitted paper orders and broker receipts.
- Open positions.
- Closed trades.
- Postmortems due and complete.

The old Trade Layer, Money snippets, Signal Integrity, Risk Agent, paper-order
state, and Phase 7 proof lifecycle should converge here.

### 4.3 Sources

Sources becomes the data reliability workspace.

Segments:

- Source group health.
- Credential state.
- Heartbeat freshness.
- Trust score / degradation reason.
- Source quorum for current setups.
- Yahoo Finance and PREF/Preference roles where present.
- Source provenance for active trade ideas.

This view should answer whether a setup is backed by real evidence, supplemental
confirmation, stale data, or weak context.

### 4.4 Reasoning

Reasoning becomes the human-readable explanation layer.

Segments:

- Current hypotheses.
- Evidence packets.
- Missing corroboration.
- Worldview/private-prior context.
- Strategy Lead review.
- Quantum/classical annotation when present.
- Why a setup did or did not advance.

The old Cognition and Private Edge sections belong here.

### 4.5 Performance

Performance becomes the paper/demo-proof account view.

Segments:

- GBP 1000 paper account state.
- Realized/unrealized P&L.
- Drawdown and halt state.
- Weekly proof cadence.
- 30-day proof progress.
- Closed proof trades.
- 100-trade maturity marker.
- Learning/postmortem summary.

The old Money panel belongs here, but with Phase 7 proof context added.

### 4.6 Operations

Operations becomes the advanced technical and audit view.

Segments:

- Full expandable System Operating Map.
- Module health.
- Runtime/process console.
- Secure bridge/static snapshot state.
- Exporter state.
- Deployment/cache key.
- Phase/certification diagnostics.
- Kill-switch ledger details.

This preserves power-user detail without making it the first experience.

### 4.7 Interactive System Map Visualization

The dashboard should use one shared system map concept in two levels of detail.

Overview mini-map:

- Shows the full Qadam flow in a compact, readable strip.
- Uses one node each for Live Data Feeds, COO, Research Analyst, Strategy Lead,
  Head of Quant, Signal/Risk Gates, Paper Lifecycle, Learning Loop, and Fund
  Manager oversight.
- Shows health only: online, degraded, blocked, pending, local-only, or
  read-only.
- Uses the D11D single safety strip for paper-only, live-capital,
  read-only, UI-to-broker, and LLM-to-broker authority state instead of
  rendering a second rail under the map.
- Links to the full Operations map.

Operations full map:

- Shows the same nodes with expandable detail panels.
- Shows data-feed clusters instead of every individual feed by default:
  conflict/geopolitics, physical world/energy/shipping/weather, macro/rates,
  markets/broker/prediction markets, and narrative/filings/social/news.
- Lets each feed cluster expand into the underlying source rows and provenance
  state.
- Lets each system node expand into what it does, inputs, outputs, status,
  latest heartbeat, dependencies, degraded reasons, Event Log references,
  authority boundary, and related dashboard links.
- Shows the Fund Manager as supervisor with review, challenge, comment, and
  kill-switch/governance links, not as a manual trade-execution node.
- Shows the safety boundary as a persistent rail across the full map.

Required nodes:

| Node | Plain Role | Default Status Detail |
| --- | --- | --- |
| Fund Manager | Oversees, reviews, challenges, comments, and governs. | Allowlist/session state, latest review/action needed. |
| Live Data Feeds | Supplies observable inputs across intelligence pipelines. | Online/degraded/missing counts and source freshness. |
| Python Script / COO | Routes work, schedules checks, supervises modules, exports status. | Heartbeat, exporter status, Event Log health. |
| Local LLM / Research Analyst | Triage, compression, and local-first reasoning. | Model availability, latest queue, shadow-only boundary. |
| Frontier LLM / Strategy Lead | Builds deeper strategy packets and challenges hypotheses. | Provider readiness, review mode, challenge count. |
| Quantum Computer / Head of Quant | Weekly quantum/classical oracle and bounded annotation. | Backend mode, fallback/hardware state, latest recommendation. |
| Signal + Risk Gates | Blocks stale, weak, oversize, or unauthorized ideas. | Signal Integrity, Risk Agent, kill-switch, drawdown state. |
| Paper Lifecycle | Stages/submits/monitors paper-only orders when gates allow. | Candidate/order/position/closed/postmortem counts. |
| Learning Loop | Converts closed trades and postmortems into reviewed learning. | Postmortem due/resolved count, approval/deferral state. |

Required edge semantics:

- Solid edge: active backend-derived data flow.
- Dashed edge: shadow/context-only influence.
- Faded edge: degraded or missing dependency.
- Locked edge: explicit authority boundary.
- Red blocked edge: fail-closed path.

Health encoding:

- Green: online/fresh/healthy.
- Amber: degraded/stale/partial.
- Red: blocked/failed/unsafe.
- Gray: pending/unavailable.
- Blue: read-only, supplemental, shadow, or context-only.

The map should never imply execution authority. It visualizes system
connectivity and health only.

### 4.8 Governance

Governance becomes the review and comment surface.

Segments:

- Fund Manager comments.
- Approval/certification records.
- Weekly review packs.
- Live-promotion review workflow.
- Telegram outbound/dry-run communications.
- Open action items.

Comments should become contextual. A user should be able to comment on a trade,
source, hypothesis, postmortem, or operations issue without memorizing internal
reference keys.

## 5. Data And Contract Strategy

The overhaul should reuse the existing sanitized status contract first.

Implementation rule:

```text
status contract -> normalized dashboard view model -> segmented UI
```

Do not let view components parse raw status deeply. Create small view-model
builders that translate Qadam's internal status into user-facing sections.

Required view models:

| View Model | Purpose |
| --- | --- |
| `overview_model` | One-pass current state and action-needed summary. |
| `trade_lifecycle_model` | Normalized trade ladder from observed signal to postmortem. |
| `source_reliability_model` | Source health, quorum, provenance, and degradation. |
| `reasoning_model` | Hypotheses, evidence, priors, missing corroboration. |
| `performance_model` | Paper account, demo-proof progress, P&L, drawdown, maturity. |
| `system_connectivity_model` | Nodes, edges, feed clusters, health, authority boundaries, and expandable details for the mini-map and full Operations map. |
| `operations_model` | Module, bridge, exporter, runtime, and certification state. |
| `governance_model` | Comments, approvals, review packs, and communications. |

The view models may initially live in `landing-page-repo/dashboard.js` for the
static site, but should be written as pure functions so they can later move into
the Next cockpit without changing behavior.

## 6. Implementation Stages

### DX-0 - Baseline Audit And Freeze

Objective: freeze the current dashboard behavior before redesign.

Work:

- Capture the current local and deployed dashboard structure.
- Record section order, nav order, status source behavior, cache keys, and
  current public-safe status fields.
- Confirm Supabase allowlist gating still protects `/dashboard/`.
- Confirm no browser route can create execution authority.
- Add a short audit document describing the current UX problems and the target
  segmentation.

Acceptance:

- `dashboard_overhaul_baseline_captured=True`.
- Existing dashboard checks still pass.
- No implementation change is made in this stage.

Expected files:

- `docs/qadam-dashboard-overhaul-dx-0-baseline-audit-YYYY-MM-DD.md`

Status after DX-0:

- DX-0 baseline capture was completed in
  `docs/qadam-dashboard-overhaul-dx-0-baseline-audit-2026-05-25.md`.
- Local dashboard structure, deployed dashboard structure, status source order,
  cache keys, auth/allowlist behavior, and public-safe status shape were
  captured.
- The initial baseline found a money/proof-trade mismatch and blocked DX-1.
- The DX-0 unblock is complete in
  `docs/qadam-dashboard-overhaul-dx-0-unblock-audit-2026-05-25.md`.
- The unblock separates paper closed-trade count from Phase 7 proof-trade count
  in the Money panel and check, and normalizes notify-only system-map authority
  copy.
- Full dashboard preflight now passes.
- DX-0 now reports `dashboard_overhaul_baseline_captured=True`,
  `dashboard_existing_dashboard_checks_pass=True`,
  `dashboard_preflight_passed=True`, and `dx1_implementation_allowed=True`.
- The current explicit next step is DX-1 - Information Architecture Contract.

### DX-1 - Information Architecture Contract

Objective: replace the long-page mental model with a stable segmented IA.

Work:

- Define the seven primary views: Overview, Trades, Sources, Reasoning,
  Performance, Operations, Governance.
- Define view order, labels, short descriptions, and entry questions.
- Decide URL behavior for the static dashboard:
  - first release: hash or query-state tabs within `/dashboard/`
  - later release: static route directories or Next routes when needed
- Map every existing section to a new destination.
- Identify panels to demote from first-level visibility.
- Define the two system map placements: Overview mini-map and Operations full
  expandable map.
- Map existing System Operating Map content into the full Operations map while
  preserving a simplified Overview mini-map.

Acceptance:

- Every current dashboard section has a destination.
- No important panel is orphaned.
- The system map has a defined compact and expanded destination.
- The guide's first-time tour can be rewritten against the new IA.

Expected files:

- `docs/qadam-dashboard-overhaul-dx-1-ia-contract-audit-YYYY-MM-DD.md`

Status update, 2026-05-25:

- DX-1 is complete.
- The IA contract is captured in
  `docs/qadam-dashboard-overhaul-dx-1-ia-contract.json`.
- The audit record is captured in
  `docs/qadam-dashboard-overhaul-dx-1-ia-contract-audit-2026-05-25.md`.
- `scripts/check_dashboard_overhaul_ia_contract.js` verifies the seven primary
  views, current-section mapping coverage, legacy-anchor compatibility, compact
  and expanded system-map destinations, and read-only authority boundary.
- Full dashboard preflight includes the IA contract check.
- DX-2 - Copy And Terminology System may proceed next.

### DX-2 - Copy And Terminology System

Objective: make the dashboard readable by someone who has never heard of Qadam.

Work:

- Define user-facing labels for internal terms.
- Create a copy map from technical labels to plain labels.
- Keep internal codes visible only in Operations diagnostics.
- Replace phase-first language with operating-state language.
- Define empty-state language for normal no-trade, blocked, stale, and degraded
  conditions.

Acceptance:

- Overview contains no unexplained `D0`, `D9`, `Q4`, `Q5`, `Q6`, or `Q7`
  labels.
- Phase labels are allowed only as secondary diagnostics.
- Safety boundaries remain explicit.

Expected files:

- `docs/qadam-dashboard-overhaul-dx-2-copy-system-audit-YYYY-MM-DD.md`

Status update, 2026-05-25:

- DX-2 is complete.
- The copy system contract is captured in
  `docs/qadam-dashboard-overhaul-dx-2-copy-system.json`.
- The audit record is captured in
  `docs/qadam-dashboard-overhaul-dx-2-copy-system-audit-2026-05-25.md`.
- `scripts/check_dashboard_overhaul_copy_system.js` verifies the copy contract,
  primary view rules, Overview primary-copy bans, Operations-only internal-code
  diagnostics, secondary-only phase labels, plain empty states, and explicit
  safety phrases.
- Full dashboard preflight includes the copy-system check.
- DX-3 - Dashboard View Model Layer may proceed next.

### DX-3 - Dashboard View Model Layer

Objective: create a presentation adapter between the raw status contract and the
new segmented UI.

Work:

- Add pure view-model builders for Overview, Trades, Sources, Reasoning,
  Performance, system connectivity, Operations, and Governance.
- Add the `system_connectivity_model` for nodes, edges, feed clusters, health
  states, authority boundaries, and expanded details.
- Preserve all public-safe filtering.
- Preserve all authority flags as read-only status.
- Add fixture coverage for missing, stale, empty, degraded, and active proof
  states.
- Add fixture coverage for online, degraded, blocked, pending, local-only,
  read-only, supplemental, and shadow-only map nodes.
- Add dishonest-payload probes for UI-inferred readiness, hidden live capital,
  missing source quorum, and false proof credit.

Acceptance:

- View models render useful summaries from the current status snapshot.
- The same connectivity model can drive both Overview mini-map and Operations
  full map without duplicating status logic.
- Missing data creates honest empty states.
- No view model grants authority or changes status state.

Expected files:

- `landing-page-repo/dashboard.js`
- `scripts/check_dashboard_overhaul_view_models.js`
- `docs/qadam-dashboard-overhaul-dx-3-view-model-audit-YYYY-MM-DD.md`

Status update, 2026-05-25:

- DX-3 is complete.
- Pure view-model builders are exposed from `landing-page-repo/dashboard.js`
  for Overview, Trades, Sources, Reasoning, Performance, system connectivity,
  Operations, and Governance.
- The audit record is captured in
  `docs/qadam-dashboard-overhaul-dx-3-view-model-audit-2026-05-25.md`.
- `scripts/check_dashboard_overhaul_view_models.js` verifies useful model
  summaries, shared connectivity model scope, public-safe output, honest empty
  states, stale/degraded/active-proof fixtures, system-node health states, and
  dishonest-payload probes for UI-inferred readiness, hidden live capital,
  missing source quorum, and false proof credit.
- Full dashboard preflight includes the view-model check.
- DX-4 - Segmented Shell may proceed next.

### DX-4 - Segmented Shell

Objective: replace the long visible page with a segmented app shell.

Work:

- Add a primary view switcher for Overview, Trades, Sources, Reasoning,
  Performance, Operations, and Governance.
- Render only the active segment by default.
- Keep direct deep links to each segment.
- Preserve keyboard navigation and scroll restoration.
- Keep old section anchors as compatibility redirects where practical.
- Avoid nested card walls; use full-width bands and compact panels.

Acceptance:

- `/dashboard/` starts on Overview.
- A user can switch views without scrolling through the full dashboard.
- Existing deep links do not break silently.
- Mobile users can switch views with stable tap targets.

Expected files:

- `landing-page-repo/dashboard/index.html`
- `landing-page-repo/dashboard.js`
- `landing-page-repo/auth.css`
- `scripts/check_dashboard_overhaul_shell.js`
- `docs/qadam-dashboard-overhaul-dx-4-segmented-shell-audit-YYYY-MM-DD.md`

Status update, 2026-05-25:

- DX-4 is complete.
- `/dashboard/` now has a seven-view segmented shell with Overview as the
  default view.
- Existing sections are assigned to Overview, Trades, Sources, Reasoning,
  Performance, Operations, and Governance through `data-dashboard-view-section`.
- Direct hashes such as `#trades`, `#sources`, and `#operations` activate the
  corresponding view.
- Legacy section hashes such as `#money`, `#system-map`, and `#trade-layer`
  activate the correct new view instead of breaking silently.
- The audit record is captured in
  `docs/qadam-dashboard-overhaul-dx-4-segmented-shell-audit-2026-05-25.md`.
- `scripts/check_dashboard_overhaul_shell.js` verifies default Overview,
  segmented visibility, legacy-anchor routing, mobile tap-target stability, and
  unchanged authority.
- Full dashboard preflight includes the segmented-shell check.
- DX-5 - Overview First Screen may proceed next.

### DX-5 - Overview First Screen

Objective: make the default dashboard immediately understandable.

Work:

- Build the Overview from the `overview_model`.
- Show mode, live-capital disabled state, demo-proof day/week, setup count,
  trade lifecycle state, source health, safety state, and action-needed summary.
- Add a compact lifecycle strip.
- Add the compact system mini-map from `system_connectivity_model`.
- Show Fund Manager oversight above the mini-map, not inside the execution
  chain.
- Show the safety boundary rail under the mini-map.
- Add plain next-review links into Trades, Sources, Reasoning, Performance,
  Operations, or Governance.
- Keep the Overview to one to two viewport heights on desktop and mobile.

Acceptance:

- A new user can answer "what is happening now?" within 30 seconds.
- The first screen does not require opening tooltips.
- Paper/demo mode and live-capital disabled state are impossible to miss.
- The mini-map shows system connectivity and health without overwhelming the
  first screen.

Expected files:

- `landing-page-repo/dashboard/index.html`
- `landing-page-repo/dashboard.js`
- `landing-page-repo/auth.css`
- `scripts/check_dashboard_overhaul_overview.js`
- `docs/qadam-dashboard-overhaul-dx-5-overview-audit-YYYY-MM-DD.md`

Status update, 2026-05-25:

- DX-5 is complete.
- The default Overview now renders a compact first-screen operating readout
  from `overview_model` and the shared `system_connectivity_model`.
- The first screen shows paper/demo mode, live-capital disabled state, the
  30-day demo-proof window, current proof week, 3-per-week proof-trade target,
  eligible setup count, trade lifecycle state, source health, safety state, and
  action-needed summary.
- Fund Manager oversight is shown above the mini-map as supervision, not as an
  automated execution-chain node.
- The safety boundary rail remains below the mini-map and states that the
  Overview cannot approve, place, modify, close, or fund trades.
- Plain next-review links route into Trades, Sources, Reasoning, Performance,
  Operations, and Governance.
- The audit record is captured in
  `docs/qadam-dashboard-overhaul-dx-5-overview-audit-2026-05-25.md`.
- `scripts/check_dashboard_overhaul_overview.js` verifies the Overview DOM,
  renderer, model fields, lifecycle strip, mini-map, copy bans, review links,
  and unchanged authority.
- Full dashboard preflight includes the Overview first-screen check.
- DX-6 - Trades Workspace may proceed next.

### DX-6 - Trades Workspace

Objective: make the trade lifecycle the main operational workspace.

Work:

- Move observed signals, qualified setups, candidates, blocked candidates,
  staged orders, submitted orders, open positions, closed trades, and
  postmortems into one lifecycle view.
- Show which stage is active for each setup/trade.
- Add filters for active, blocked, open, closed, and postmortem due.
- Surface source quorum, risk decision, and broker receipt links where present.
- Keep Phase 5 test trades visually separate from Phase 7 proof trades.

Acceptance:

- A Fund Manager can identify whether Qadam has merely observed something,
  formed a candidate, staged an order, submitted a paper order, opened a
  position, closed a trade, or owes a postmortem.
- No candidate is visually treated as an order.
- Phase 7 proof credit cannot be inferred from UI alone.

Expected files:

- `landing-page-repo/dashboard.js`
- `landing-page-repo/auth.css`
- `scripts/check_dashboard_overhaul_trades.js`
- `docs/qadam-dashboard-overhaul-dx-6-trades-audit-YYYY-MM-DD.md`

Status update, 2026-05-25:

- DX-6 is complete.
- The Trades view now opens with a lifecycle workspace covering observed
  signals, setup state, candidates, blocked ideas, staged orders, submitted
  paper orders, open positions, closed paper trades, and postmortems due.
- The lifecycle workspace includes all, active, blocked, open, closed, and
  postmortem-due filters.
- Source quorum, risk decision, and broker receipt evidence links are visible
  from lifecycle records.
- Phase 5 test lifecycle state and Phase 7 proof-trade state are visually
  separated and explicitly do not imply proof credit.
- Capital-ledger paper orders now count as submitted lifecycle records so counts
  and rendered cards agree.
- The audit record is captured in
  `docs/qadam-dashboard-overhaul-dx-6-trades-audit-2026-05-25.md`.
- `scripts/check_dashboard_overhaul_trades.js` verifies the Trades workspace
  DOM contract, model records, filters, evidence links, Phase 5/Phase 7
  partition, candidate-is-not-order boundary, and unchanged authority.
- Full dashboard preflight includes the Trades workspace check.
- DX-7 - Sources Workspace may proceed next.

### DX-7 - Sources Workspace

Objective: make source health and provenance clear enough to trust or challenge.

Work:

- Group sources by pipeline and reliability state.
- Show online, degraded, missing credential, stale heartbeat, pending adapter,
  and supplemental-only status.
- Surface Yahoo Finance and PREF/Preference as capability-aware supplemental
  inputs where present.
- Add source-to-setup links for active qualified setups and candidates.
- Keep source provenance public-safe.

Acceptance:

- A user can see whether Qadam has enough corroboration for current ideas.
- Supplemental sources are not mistaken for sole proof.
- Stale or degraded sources are visible without reading runtime logs.

Expected files:

- `landing-page-repo/dashboard.js`
- `landing-page-repo/auth.css`
- `scripts/check_dashboard_overhaul_sources.js`
- `docs/qadam-dashboard-overhaul-dx-7-sources-audit-YYYY-MM-DD.md`

Status update, 2026-05-25:

- DX-7 is complete.
- The Sources view now opens with a source health and provenance workspace
  before the detailed watched-source registry.
- `sources_model` now exposes pipeline health records, six reliability states,
  supplemental capability records, source quorum, and source-to-setup links.
- Online, degraded, missing credential, stale heartbeat, pending adapter, and
  supplemental-only states are visible without reading runtime logs.
- Yahoo Finance and Preference/PREF MCP are displayed as capability-aware
  supplemental inputs, explicitly not source quorum or sole proof.
- Observed signals, active candidates, and the Phase 7 setup pool are linked
  back to source evidence while remaining review-only.
- The audit record is captured in
  `docs/qadam-dashboard-overhaul-dx-7-sources-audit-2026-05-25.md`.
- `scripts/check_dashboard_overhaul_sources.js` verifies the Sources workspace
  DOM contract, model records, reliability states, supplemental boundaries,
  source-to-setup links, public-safe rendering, and unchanged authority.
- Full dashboard preflight includes the Sources workspace check.
- DX-8 - Reasoning Workspace may proceed next.

### DX-8 - Reasoning Workspace

Objective: explain why Qadam cares without confusing priors, hypotheses, and
evidence.

Work:

- Merge Cognition and Private Edge into Reasoning.
- Separate worldview prior, hypothesis, evidence packet, missing
  corroboration, Strategy Lead review, and quant/quantum annotation.
- Show why an idea advanced, stalled, or was blocked.
- Keep private-worldview claims labelled as priors, not evidence.

Acceptance:

- A user can distinguish worldview context from factual evidence.
- A hypothesis cannot be mistaken for a candidate or order.
- Missing corroboration is visible as a normal blocker.

Expected files:

- `landing-page-repo/dashboard.js`
- `landing-page-repo/auth.css`
- `scripts/check_dashboard_overhaul_reasoning.js`
- `docs/qadam-dashboard-overhaul-dx-8-reasoning-audit-YYYY-MM-DD.md`

Status update, 2026-05-25:

- DX-8 is complete.
- The Reasoning view now opens with a workspace that separates worldview
  priors, factual evidence, hypotheses, missing corroboration, Strategy Lead
  review, and Head of Quant annotation.
- `reasoning_model` now exposes six reasoning lanes, a prior-only worldview
  record, a hypothesis queue, public-safe evidence packets, missing
  corroboration blockers, a four-step review chain, and quant annotation state.
- Private Edge is now labelled as a compact prior index merged into Reasoning,
  not a separate proof layer.
- Hypotheses show why they advanced, stalled, or were blocked while remaining
  explicitly not candidates, paper orders, broker writes, or live-capital
  authority.
- Missing corroboration is visible as a normal hold condition before trade
  state.
- The audit record is captured in
  `docs/qadam-dashboard-overhaul-dx-8-reasoning-audit-2026-05-25.md`.
- `scripts/check_dashboard_overhaul_reasoning.js` verifies the Reasoning
  workspace DOM contract, model records, prior/evidence separation,
  hypothesis-not-candidate boundary, missing corroboration blockers, review
  chain, quant annotation, public-safe rendering, and unchanged authority.
- Full dashboard preflight includes the Reasoning workspace check.
- DX-9 - Performance Workspace may proceed next.

### DX-9 - Performance Workspace

Objective: make demo-proof progress and paper performance legible.

Work:

- Move Money into Performance.
- Add Phase 7 day count, proof-week cadence, qualified setups, proof trades,
  closed proof trades, postmortems, drawdown, and maturity state.
- Separate operational completion from statistical maturity.
- Show the 100-trade maturity benchmark without implying it is required for the
  30-day proof run to finish.

Acceptance:

- A user can see whether the 30-day demo proof is progressing cleanly.
- Drawdown and halt state are obvious.
- No forced-trade pressure is introduced by the UI.

Expected files:

- `landing-page-repo/dashboard.js`
- `landing-page-repo/auth.css`
- `scripts/check_dashboard_overhaul_performance.js`
- `docs/qadam-dashboard-overhaul-dx-9-performance-audit-YYYY-MM-DD.md`

Status update, 2026-05-25:

- DX-9 is complete.
- The Performance view now opens with a workspace for 30-day demo-proof
  progress, paper account state, drawdown/halt state, proof cadence, setup
  funnel, proof lifecycle, postmortems, source records, and maturity state.
- `performance_model` now exposes paper account state, demo-proof cadence,
  proof lifecycle counts, risk/drawdown state, operational-vs-maturity
  separation, backend source records, and safety counters.
- Money has been absorbed into Performance while the detailed paper mirror
  remains below the workspace for continuity.
- The 100-trade maturity benchmark is visible without implying it is required
  for the 30-day operating run to complete.
- Phase 5 trades remain explicitly excluded from Phase 7 proof credit, and the
  UI cannot infer proof credit or readiness from display state.
- The audit record is captured in
  `docs/qadam-dashboard-overhaul-dx-9-performance-audit-2026-05-25.md`.
- `scripts/check_dashboard_overhaul_performance.js` verifies the Performance
  workspace DOM contract, model records, 30-day/3-per-week proof rules,
  operational-vs-maturity separation, drawdown/halt state, backend source
  records, public-safe rendering, forced-trade protections, and unchanged
  authority.
- Full dashboard preflight includes the Performance workspace check.
- DX-10 - Operations Workspace may proceed next.

### DX-10 - Operations Workspace

Objective: preserve diagnostics without making them the default experience.

Work:

- Move System Map, runtime/process console, bridge/static snapshot state,
  exporter status, module health, cache keys, and certification diagnostics into
  Operations.
- Build the full expandable System Operating Map from `system_connectivity_model`.
- Render the Fund Manager, live data feed clusters, COO, Research Analyst,
  Strategy Lead, Head of Quant, Signal/Risk Gates, Paper Lifecycle, and Learning
  Loop as first-class nodes.
- Add expandable node sections for purpose, inputs, outputs, current status,
  latest heartbeat, dependencies, degraded reasons, Event Log references,
  authority boundary, and related dashboard links.
- Add expandable feed clusters for the five intelligence pipelines and source
  provenance.
- Encode edges as active, shadow/context-only, degraded, locked, or blocked.
- Keep the persistent safety rail visible across the full map.
- Keep advanced phase labels and raw operational terms here.
- Add a compact "what is broken?" summary.
- Preserve read-only runtime boundaries.

Acceptance:

- Operators still have the technical detail they need.
- First-time users are not forced through runtime diagnostics.
- The full map explains system connectivity and health better than the old
  card-grid System Map.
- Expanded nodes reveal diagnostics without lengthening the default Overview.
- No runtime panel exposes shell access, local paths, secrets, or broker write
  routes.

Expected files:

- `landing-page-repo/dashboard.js`
- `landing-page-repo/auth.css`
- `scripts/check_dashboard_overhaul_operations.js`
- `docs/qadam-dashboard-overhaul-dx-10-operations-audit-YYYY-MM-DD.md`

Status update, 2026-05-25:

- DX-10 is complete.
- The Operations view now opens with a dedicated read-only diagnostics
  workspace rather than only the legacy System Map card grid.
- `operations_model` now exposes the shared `system_connectivity_model`,
  first-class operating-role spine, compact "what is broken?" summary,
  bridge/static snapshot state, exporter/cache state, module health,
  phase/certification diagnostics, kill-switch ledger state, and runtime safety
  boundaries.
- The full Operations map renders expandable node diagnostics for purpose,
  inputs, outputs, current status, latest heartbeat, dependencies, degraded
  reasons, Event Log references, authority boundary, and related dashboard
  links.
- The Operations view now renders five intelligence-pipeline feed clusters plus
  canonical replay, Yahoo Finance, and Preference MCP provenance summaries.
- Edge states are encoded as `active`, `shadow/context-only`, `degraded`,
  `locked`, or `blocked`, with a visible legend.
- The Operations view references the D11D single safety strip for paper-only,
  live-capital, read-only, UI-to-broker, and LLM-to-broker authority state.
- Advanced phase labels and raw operational terms remain in Operations, not the
  Overview first screen.
- The audit record is captured in
  `docs/qadam-dashboard-overhaul-dx-10-operations-audit-2026-05-25.md`.
- `scripts/check_dashboard_overhaul_operations.js` verifies static shell copy,
  CSS contract, operations/connectivity model shape, role spine, feed clusters,
  edge states, runtime diagnostics, rendered map content, public-safe rendering,
  and unchanged authority.
- Full dashboard preflight includes the Operations workspace check.
- DX-11 - Governance And Communications Workspace may proceed next.

### DX-11 - Governance And Communications Workspace

Objective: make comments, approvals, reviews, and Telegram state useful without
burying them at the bottom of a long page.

Work:

- Move Fund Manager comments, approval records, weekly review packs,
  live-promotion review status, and Telegram outbound state into Governance.
- Add contextual comment entry points from Trades, Sources, Reasoning,
  Performance, and Operations.
- Replace raw reference-key entry with assisted selectors where possible.
- Keep Telegram outbound-only and comments governance-only.

Acceptance:

- A user can add a useful governance comment without knowing internal IDs.
- Communications are visible but cannot become commands.
- Approvals and review state remain audit-only unless a backend gate says
  otherwise.

Expected files:

- `landing-page-repo/dashboard.js`
- `landing-page-repo/auth.css`
- `scripts/check_dashboard_overhaul_governance.js`
- `docs/qadam-dashboard-overhaul-dx-11-governance-audit-YYYY-MM-DD.md`

Status update, 2026-05-25:

- DX-11 is complete.
- The Governance view now opens with a combined workspace for Fund Manager
  comments, approval/certification records, weekly review pack state,
  live-promotion review workflow state, Telegram outbound state, and open
  action items.
- `governance_model` now exposes contextual comment targets, approval/review
  records, weekly proof-review state, live-promotion review state, Telegram
  command/live-send boundaries, and open governance actions.
- Comment entry is now assisted by contextual target buttons from Trades,
  Sources, Reasoning, Performance, Operations, and Governance plus a target
  selector, so users do not need to memorize internal reference keys.
- Telegram remains outbound/dry-run and cannot become a command path.
- Approval and certification state remains audit-only unless backend gates say
  otherwise; the dashboard does not grant trade, broker, learning-write,
  Telegram-command, live-promotion, or live-capital authority.
- The audit record is captured in
  `docs/qadam-dashboard-overhaul-dx-11-governance-audit-2026-05-25.md`.
- `scripts/check_dashboard_overhaul_governance.js` verifies the static shell,
  CSS contract, governance model shape, contextual comment targets,
  approval/review records, weekly/live-promotion state, Telegram outbound
  boundary, assisted selector contract, public-safe rendering, and unchanged
  authority.
- Full dashboard preflight includes the Governance workspace check.
- DX-12 - Responsive Layout And Accessibility may proceed next.

### DX-12 - Responsive Layout And Accessibility

Objective: make the segmented dashboard usable on desktop and mobile.

Work:

- Replace wide three-column card grids with responsive layouts per view.
- Make the Overview mini-map usable on mobile without horizontal confusion.
- Make the Operations full map pan/scroll or stack predictably on narrow
  screens.
- Use stable dimensions for status chips, lifecycle steps, and controls.
- Ensure long labels wrap safely.
- Validate keyboard focus order.
- Avoid tooltip-only explanations.
- Confirm high-contrast states for online, degraded, blocked, pending, and
  action-needed states.

Acceptance:

- Mobile users can understand Overview and switch to any view quickly.
- The mini-map and full map remain readable on mobile and desktop.
- Text does not overlap or overflow.
- Active view, focused control, and selected filters are clear.

Expected files:

- `landing-page-repo/auth.css`
- `scripts/check_dashboard_overhaul_responsive.js`
- `docs/qadam-dashboard-overhaul-dx-12-responsive-audit-YYYY-MM-DD.md`

Status update, 2026-05-25:

- DX-12 is complete.
- The dashboard now exposes a first keyboard target skip link into the segmented
  dashboard workspace.
- Focus-visible states are explicit for links, buttons, summaries, form fields,
  and dashboard controls.
- Navigation, lifecycle strips, and horizontal workflow rails now use snap-aware
  scrolling and stable minimum tap targets.
- The operating-mode rail stacks into one column on narrow phones and clips
  accidental horizontal overflow at the dashboard shell boundary.
- Mode-rail pill styling is scoped to direct children and the density toggle uses
  equal-width columns on narrow phones, so nested status text cannot create
  accidental pill layouts.
- The dashboard CSS cache key now points at the DX-12 responsive stylesheet.
- Overview mini-map nodes now show ordered step markers and collapse to a single
  readable column on narrow phones.
- Operations map cards stop using absolute footers on narrow screens, preventing
  authority-boundary copy from overlapping diagnostic facts.
- Status chips, node statuses, trade filters, governance target buttons, and
  repeated card grids wrap long labels safely.
- Online, degraded, pending, and blocked states have stronger visual contrast
  without changing any backend authority.
- The audit record is captured in
  `docs/qadam-dashboard-overhaul-dx-12-responsive-audit-2026-05-25.md`.
- `scripts/check_dashboard_overhaul_responsive.js` verifies the skip link,
  keyboard focus contract, responsive CSS breakpoints, mini-map rendering,
  lifecycle/filter state, public-safe output, and unchanged authority.
- Full dashboard preflight includes the responsive/accessibility check.
- DX-13 - User Guide Alignment may proceed next.

### DX-13 - User Guide Alignment

Objective: make the guide match the rebuilt dashboard.

Work:

- Rewrite the First 10-Minute Tour around Overview, Trades, Sources,
  Reasoning, Performance, Operations, and Governance.
- Explain that Overview contains the quick health mini-map and Operations
  contains the full expandable system map.
- Add a "What to check daily" section for Phase 7 demo-proof operation.
- Add a "When to go to Operations" section for technical diagnostics.
- Add a plain-language glossary for old implementation terms.
- Ensure guide and dashboard navigation agree.

Acceptance:

- A user following the guide lands on the same sections the dashboard exposes.
- The guide teaches the two-level system map without making the mini-map feel
  like the full diagnostics surface.
- The guide no longer asks users to hunt for panels that are missing from nav.
- The guide clearly explains that blocked/no-trade states can be healthy.

Expected files:

- `docs/qadam-user-guide.md`
- `landing-page-repo/guide/index.html`
- `scripts/check_protected_user_guide.js`
- `docs/qadam-dashboard-overhaul-dx-13-guide-alignment-audit-YYYY-MM-DD.md`

### DX-14 - Verification, Deployment, And Certification

Objective: prove the overhaul is shipped and safe.

Work:

- Add a single dashboard overhaul certification checker.
- Run all dashboard renderer, mission-control, Phase 7 cockpit, protected guide,
  and deployment preflight checks.
- Verify the Overview mini-map and Operations full map render from the same
  backend-derived connectivity model.
- Verify the live deployed `/dashboard/` HTML, JS cache key, CSS cache key, and
  protected guide link.
- Capture desktop and mobile screenshots if browser tooling is available.
- Certify that the dashboard remains read-only and status-derived.

Acceptance:

- `dashboard_overhaul_certified=True`.
- `dashboard_default_view=overview`.
- `dashboard_segmented_views_enabled=True`.
- `dashboard_system_mini_map_enabled=True`.
- `dashboard_operations_full_map_enabled=True`.
- `dashboard_system_map_shared_model=True`.
- `dashboard_first_view_readability_passed=True`.
- `dashboard_authority_unchanged=True`.
- `dashboard_guide_alignment_passed=True`.
- Live deployment serves the new segmented dashboard.

Expected files:

- `scripts/check_dashboard_overhaul_certification.js`
- `docs/qadam-dashboard-overhaul-dx-14-certification-audit-YYYY-MM-DD.md`

## 7. D11 Simplification Pass

D11 is the second-pass simplification layer after the segmented dashboard
exists. Its purpose is to reduce the number of primary views, remove duplicate
status language, and collapse implementation-heavy sections into a smaller
operating dashboard without weakening auditability.

### D11A - Information Diet Audit

Status: complete on 2026-05-26.

Control artifacts:

- `docs/qadam-dashboard-d11a-information-diet-audit-2026-05-26.md`
- `scripts/check_dashboard_d11a_information_diet_audit.js`

Outcome:

- Every current static dashboard section has a D11 fate.
- Every major dynamic renderer/model has a D11 fate.
- Duplicate concepts have a single future owner.
- `Executive / Terminal` is explicitly marked for deletion.
- No runtime authority, provider call, broker write, or live-capital behavior
  changes in D11A.

Next stage:

- D11B - New Navigation Contract.

### D11B - New Navigation Contract

Status: complete on 2026-05-26.

Control artifacts:

- `docs/qadam-dashboard-d11b-new-navigation-contract-2026-05-26.md`
- `scripts/check_dashboard_d11b_new_navigation_contract.js`

Outcome:

- The primary dashboard nav now has five views: Overview, Trades, Evidence,
  Reasoning, and Operations.
- `Sources` is renamed to `Evidence`.
- `Performance` is merged into Trades at the navigation level.
- `Governance` and Communications are merged into Operations at the navigation
  level.
- Legacy hashes such as `#sources`, `#performance`, `#money`, `#governance`,
  `#communications`, `#system-map`, `#process-console`, and `#forbidden`
  resolve into the new owner view while preserving target scrolling.
- The obsolete `Executive / Terminal` density switcher was removed from HTML,
  CSS, renderer state, and exported browser hooks.
- No runtime authority, provider call, broker write, Telegram command, or
  live-capital behavior changes in D11B.

Next stage:

- D11C - Canonical Status Language.

### D11C - Canonical Status Language

Status: complete on 2026-05-26.

Control artifacts:

- `docs/qadam-dashboard-d11c-canonical-status-language-2026-05-26.md`
- `scripts/check_dashboard_d11c_canonical_status_language.js`

Outcome:

- The dashboard now has a canonical display vocabulary for Current,
  Read-only, Paper only, Live capital off, Dry run, Waiting for evidence,
  Missing setup, Degraded, Local only, Non-executable, Safety stop, and Fault.
- Generic status pills no longer need to expose raw `Blocked`, `Pending`, or
  `Online` language when a clearer canonical label exists.
- Exact raw status-token badges are normalized where safe, while
  domain-specific lifecycle labels such as `Blocked idea` remain intact.
- Existing backend status values, CSS tone classes, readiness gates, provider
  calls, broker routes, Telegram posture, and live-capital state are unchanged.

Next stage:

- D11D - Single Safety Strip.

### D11D - Single Safety Strip

Status: complete on 2026-05-26.

Control artifacts:

- `docs/qadam-dashboard-d11d-single-safety-strip-2026-05-26.md`
- `scripts/check_dashboard_d11d_single_safety_strip.js`

Outcome:

- The dashboard now has one canonical dashboard-wide authority strip under the
  view switcher.
- The strip owns paper-only, read-only, live-capital-off, UI-to-broker,
  LLM-to-broker, and proof-credit-inference copy.
- Overview now references the single safety strip instead of repeating
  broker-write and live-capital copy as a second rail.
- Operations no longer renders a separate safety rail; it points to the single
  strip and then shows diagnostic evidence.
- Runtime authority, provider calls, broker writes, Telegram command behavior,
  proof-credit rules, and live-capital state are unchanged.

Next stage:

- D11E - Rebuild Overview.

### D11E - Rebuild Overview

Status: complete on 2026-05-26.

Control artifacts:

- `docs/qadam-dashboard-d11e-rebuild-overview-2026-05-26.md`
- `scripts/check_dashboard_d11e_rebuild_overview.js`

Outcome:

- The Overview now opens as a short Fund Manager brief rather than a repeated
  status-card wall.
- Mode, live-capital, broker path, LLM path, and proof-credit authority copy
  remain in the D11D single safety strip, not in Overview.
- The Overview is now four readouts only: source health, trade path, proof run,
  and needs-review.
- The proof window and trade lifecycle are grouped into one compact proof/status
  strip plus one lifecycle strip.
- The compact system map remains in Overview, but is grouped as one system
  summary instead of several disconnected panels.
- The four next-review handoffs remain Trades, Evidence, Reasoning, and
  Operations.
- Runtime authority, provider calls, broker writes, Telegram command behavior,
  proof-credit rules, and live-capital state are unchanged.

Next stage:

- D11F - Trades View Consolidation.

### D11F - Trades View Consolidation

Status: complete on 2026-05-26.

Control artifacts:

- `docs/qadam-dashboard-d11f-trades-view-consolidation-2026-05-26.md`
- `scripts/check_dashboard_d11f_trades_view_consolidation.js`

Outcome:

- The Trades view now has one primary lifecycle board and one consolidated
  trade readout before diagnostics.
- The duplicate static trade-route strip and duplicate Trade Layer panel brief
  are removed.
- Detailed trade diagnostics are grouped into three review drawers: proof and
  paper lifecycle, gate chain and broker readiness, and signals/candidates/
  paper states.
- Existing backend-derived phase diagnostics remain visible inside the grouped
  review drawers.
- Candidate/order and proof-credit boundaries remain explicit.
- Runtime authority, provider calls, broker writes, Telegram command behavior,
  proof-credit rules, and live-capital state are unchanged.

Next stage:

- D11G - Evidence View Consolidation.

### D11G - Evidence View Consolidation

Status: complete on 2026-05-26.

Control artifacts:

- `docs/qadam-dashboard-d11g-evidence-view-consolidation-2026-05-26.md`
- `scripts/check_dashboard_d11g_evidence_view_consolidation.js`

Outcome:

- The Evidence view now presents one consolidated source/evidence readout
  instead of a repeated Watching panel brief plus separate source summary strip.
- Source-to-setup links, source reliability, supplemental context, and factual
  evidence packets are grouped into four review drawers.
- The detailed source ledger remains available as an advanced diagnostic drawer
  instead of dominating the first screen.
- Yahoo Finance and Preference/PREF remain labelled as supplemental context,
  not source quorum or proof.
- Factual evidence packets stay separate from private priors and do not imply
  trade, broker, proof-credit, or live-capital authority.
- Runtime authority, provider calls, broker writes, Telegram command behavior,
  proof-credit rules, and live-capital state are unchanged.

Next stage:

- D11H - Reasoning View Consolidation.

### D11H - Reasoning View Consolidation

Status: complete on 2026-05-26.

Control artifacts:

- `docs/qadam-dashboard-d11h-reasoning-view-consolidation-2026-05-26.md`
- `scripts/check_dashboard_d11h_reasoning_view_consolidation.js`

Outcome:

- The Reasoning view now starts with one consolidated reasoning readout instead
  of a repeated Cognition panel brief.
- Private priors, factual evidence, hypotheses/blockers, and the review chain
  are grouped into clear review drawers.
- Legacy cognition diagnostics remain available in one advanced diagnostics
  drawer instead of occupying the main first screen.
- The UI keeps priors, factual evidence, hypotheses, Strategy Lead review,
  Signal Integrity, and Head of Quant annotation semantically separate.
- Model output, quantum/classical annotation, hypotheses, and evidence packets
  remain explicitly non-executable and cannot create orders or proof credit.
- Runtime authority, provider calls, broker writes, Telegram command behavior,
  proof-credit rules, and live-capital state are unchanged.

Next stage:

- D11I - Operations View.

### D11I - Operations View

Status: complete on 2026-05-26.

Control artifacts:

- `docs/qadam-dashboard-d11i-operations-view-2026-05-26.md`
- `scripts/check_dashboard_d11i_operations_view.js`

Outcome:

- The Operations view now starts with one consolidated operations readout
  instead of separate visible runtime, hard-block, process-console,
  communications, and governance cards.
- Operations detail is grouped into four review drawers: runtime/bridge/safety,
  operating team/data plumbing, full system map/event trail, and
  governance/communications audit.
- The full expandable System Operating Map remains the central Operations
  artifact, with node diagnostics, edge states, and closed-loop Event Log
  semantics.
- Legacy operations panels remain available for compatibility and renderer
  coverage, but they are hidden from the visible Operations tab to reduce
  duplicate information.
- Legacy hashes for communications, process console, hard blocks, and
  governance now land on the consolidated Operations readout.
- Runtime authority, provider calls, broker writes, Telegram command behavior,
  proof-credit rules, and live-capital state are unchanged.

Next stage:

- D11J - Tooltip Simplification.

### D11J - Tooltip Simplification

Status: complete on 2026-05-26.

Control artifacts:

- `docs/qadam-dashboard-d11j-tooltip-simplification-2026-05-26.md`
- `scripts/check_dashboard_d11j_tooltip_simplification.js`

Outcome:

- Dashboard hover help now uses a compact `Shows / Watch / Limits` contract
  instead of the longer `Use it to / Watch for / Boundary` onboarding pattern.
- Every dashboard section tooltip has `data-tooltip-contract="compact"` so the
  shorter contract is enforceable.
- Tooltip copy is constrained to one short summary and three short rows, reducing
  repeated safety paragraphs and keeping the dashboard itself responsible for
  primary explanation.
- The single safety strip renderer uses the same compact tooltip structure as
  the static shell.
- Tooltip styling is narrower and tighter so hover help behaves like quick
  operator assistance, not another card layer.
- Runtime authority, provider calls, broker writes, Telegram command behavior,
  proof-credit rules, and live-capital state are unchanged.

Next stage:

- D11K - View Model Refactor.

### D11K - View Model Refactor

Status: complete on 2026-05-26.

Control artifacts:

- `docs/qadam-dashboard-d11k-view-model-refactor-2026-05-26.md`
- `scripts/check_dashboard_d11k_view_model_refactor.js`

Outcome:

- The dashboard now builds one shared view-model bundle per status snapshot
  instead of letting visible sections independently rebuild equivalent model
  slices.
- `buildQadamDashboardViewModels` declares a model graph with build order and
  shared dependencies for Overview, Trades, Operations, and the safety strip.
- Trades receives the shared Evidence/Sources model, Operations receives the
  shared System Connectivity and Governance models, and Overview receives the
  already-built Sources, Trades, Reasoning, Performance, Operations, and System
  Connectivity models.
- Evidence, Reasoning, Trades, Performance, and Governance renderers now accept
  the shared bundle from `renderQadamDashboardStatus`, while keeping fallback
  builders for isolated tests and legacy calls.
- The top-level schema remains `dashboard_view_models.v1` for compatibility,
  with `model_contract_version` marking the D11K shared-bundle contract.
- Runtime authority, provider calls, broker writes, Telegram command behavior,
  proof-credit rules, and live-capital state are unchanged.

Next stage:

- D11L - Visual Simplification.

### D11L - Visual Simplification

Status: complete on 2026-05-26.

Control artifacts:

- `docs/qadam-dashboard-d11l-visual-simplification-2026-05-26.md`
- `scripts/check_dashboard_d11l_visual_simplification.js`

Outcome:

- The dashboard visual layer now treats primary views as scrollable operating
  sections separated by quiet dividers instead of nested floating cards.
- The cockpit view switcher and single safety strip no longer stack as sticky
  glass layers, reducing visual compression while preserving the same status
  and authority copy.
- High-saturation glow is reduced to status borders and compact accents; large
  panel shadows and decorative gradients are removed from the visible dashboard
  surfaces.
- Metrics, review groups, paper-account cards, performance panels, and system
  map containers share one quieter surface vocabulary.
- The cache key was bumped so the simplified stylesheet is fetched by the
  deployed dashboard.
- Runtime authority, provider calls, broker writes, Telegram command behavior,
  proof-credit rules, and live-capital state are unchanged.

Next stage:

- D11M - Regression And Acceptance Tests.

### D11M - Regression And Acceptance Tests

Status: complete on 2026-05-26.

Control artifacts:

- `docs/qadam-dashboard-d11m-regression-and-acceptance-tests-2026-05-26.md`
- `scripts/check_dashboard_d11m_regression_acceptance.js`

Outcome:

- Added a cross-view regression checker for the D11A-D11L simplified dashboard
  shell.
- The checker verifies the canonical five-view navigation contract, the single
  global safety strip, D11 consolidated view content, cache-key continuity, and
  public-safe rendering boundaries.
- The dashboard preflight now runs the D11M checker, and the dashboard
  acceptance gate treats it as a required dependency.
- Performance remains consolidated inside Trades for now; a deeper performance
  cleanup has moved to D11O.
- Runtime authority, provider calls, broker writes, Telegram command behavior,
  proof-credit rules, and live-capital state are unchanged.

Next stage:

- D11N - Documentation And Guide Alignment.

### D11N - Documentation And Guide Alignment

Status: complete on 2026-05-26.

Control artifacts:

- `docs/qadam-dashboard-d11n-documentation-guide-alignment-2026-05-26.md`
- `scripts/check_dashboard_d11n_documentation_guide_alignment.js`

Outcome:

- The protected User Guide now teaches the simplified five-view dashboard:
  Overview, Trades, Evidence, Reasoning, and Operations.
- The first tour and daily operating routine now start from Overview, read the
  single safety strip first, and route deeper work through the same nav labels
  the dashboard exposes.
- Old panel names such as Mission Control, Watching, Cognition, Trade Layer,
  Money, Forbidden, Process Console, Comments, and Communications are retained
  only as implementation-term mappings.
- The guide explains the two-level system map: Overview has the compact
  mini-map, while Operations has the full expandable system map and diagnostics.
- The protected guide checker and dashboard preflight now enforce the guide
  alignment contract.
- Runtime authority, provider calls, broker writes, Telegram command behavior,
  proof-credit rules, and live-capital state are unchanged.

Next stage:

- D11O - Performance View Consolidation.

## 8. Implementation Order

Implement in this order:

1. DX-0 baseline audit.
2. DX-1 IA contract.
3. DX-2 terminology system.
4. DX-3 view-model layer.
5. DX-4 segmented shell.
6. DX-5 Overview.
7. DX-6 Trades.
8. DX-7 Sources.
9. DX-8 Reasoning.
10. DX-9 Performance.
11. DX-10 Operations.
12. DX-11 Governance.
13. DX-12 responsive/accessibility pass.
14. DX-13 user guide alignment.
15. DX-14 certification and deployment.

DX-3 through DX-5 are the highest-leverage stages. Once they are complete,
`/dashboard/` should already feel materially simpler even before every detail
workspace is refined.

## 9. Success Definition

The overhaul is complete when:

- A new founding Fund Manager can understand the dashboard from Overview alone.
- The Overview includes a compact health map of Qadam's data-to-decision system.
- The full page is no longer a single long scroll of every system panel.
- The guide, nav, and rendered dashboard share the same order and labels.
- Every old panel has a clear destination in the new IA.
- The Operations view contains the full expandable system map with node health,
  feed clusters, edge states, and authority boundaries.
- Trades, sources, reasoning, performance, operations, and governance are
  separated by task.
- Phase 7 demo-proof state is visible without burying users in phase internals.
- No UI route grants or implies new authority.
- Existing public-safe status boundaries still pass.
- The live `qadam.trade/dashboard/` deployment matches the certified local
  build.

## 9. Relationship To Existing Dashboard Docs

This plan supersedes the older navigation-only plan for future dashboard UX
work. It does not delete the earlier dashboard implementation plan, because that
document still defines important status-contract and cockpit-boundary history.

Use this document as the control plan for the dashboard overhaul stages. Use the
older dashboard implementation docs as technical background only.
