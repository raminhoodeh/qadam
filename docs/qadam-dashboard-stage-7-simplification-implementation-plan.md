# Qadam Dashboard Stage 7 - Useful Simplification Implementation Plan

Date: 2026-06-14
Status: plan only, not implemented

This plan defines the next dashboard overhaul stage after source/evidence
runtime work. It does not change code, status contracts, deployment assets, or
runtime behavior yet.

## 1. Purpose

The current dashboard has already been simplified, but some of that
simplification is too shallow. It reduces visible clutter, but it can also hide
the shape of Qadam's operating system. Stage 7 should make the dashboard easier
to understand without making it feel thin, generic, or disconnected from the
actual fund system.

The desired result is a Fund Manager cockpit that answers:

- What is Qadam doing right now?
- Is the system healthy enough to trust?
- Which data sources are connected and useful?
- What strategies are active?
- What is Qadam currently considering?
- What trades could it make, and why has it not made them yet?
- How much of the GBP 100,000 paper portfolio is deployed, idle, at risk, or
  reserved?
- Where can I drill down when I need proof?

The goal is not a shorter dashboard for its own sake. The goal is a dashboard
where every visible item earns its place.

## 2. Product Principle

Stage 7 should represent Qadam as a hedge fund team inside a laptop:

```text
World events and markets
  -> COO watches and routes
  -> Research Analyst compresses evidence
  -> Strategy Lead forms hypotheses
  -> Head of Quant annotates difficult calls
  -> Signal Integrity and Risk decide whether an idea is allowed
  -> Alpaca Paper executes only approved paper orders
  -> Postmortems teach the next cycle
  -> Fund Manager supervises the whole chain
```

The dashboard should show that chain clearly. It should not expose every raw
debug artifact on the main page, and it should not collapse Qadam into a few
plain status cards that fail to explain how the machine thinks.

## 3. Non-Negotiable Boundaries

- Dashboard remains read-only.
- No UI control may create trades, approvals, broker writes, Telegram commands,
  quantum jobs, proof credit, or live-capital state.
- "Qadam's thoughts" means public-safe reasoning summaries, decision logs, and
  activity events. It must not expose raw hidden model chain-of-thought.
- Readiness must come from backend status contracts and runtime artifacts, not
  frontend inference.
- The dashboard may simplify language, but it must not hide real blockers,
  missing credentials, degraded sources, safety holds, or stale runtime state.
- Advanced/debug data remains reachable, but not primary.

## 4. Current UX Diagnosis

Stage 7 should assume the current dashboard has these weaknesses:

- Important information is split across too many panels.
- Some panels repeat the same safety, source, or lifecycle information with
  different labels.
- Overview can still feel like a compressed index rather than a true operating
  room.
- Source status, strategy status, reasoning status, and trade status are visible
  but not always connected into one causal story.
- Advanced/debug content is hidden better than before, but the Fund Manager
  view still lacks a strong "what matters now" hierarchy.
- Some simplification removes detail instead of reorganizing it into useful
  layers.
- The paper portfolio capacity is not treated as a first-class live operating
  constraint.
- Qadam's current reasoning/activity feed is not prominent enough.

## 5. Target Information Architecture

Stage 7 should use three levels of detail.

### Level 1 - Operating Brief

Visible by default on `/dashboard/`. It should fit into roughly two desktop
viewports and remain readable on mobile.

Required sections:

1. System Operating Map.
2. System Status.
3. Data Sources Connected.
4. Trading Strategies.
5. Qadam Activity Feed.
6. Trade Consideration Board.
7. Paper Portfolio Capacity.

### Level 2 - Proof Drawers

Accessible from Level 1, but not always expanded.

Proof drawers should explain:

- Which sources support a setup.
- Which evidence packets exist.
- Which strategy lens is active.
- Which risk rule blocked or allowed the idea.
- Whether quantum/classical consultation happened.
- Whether Alpaca Paper is ready, submitted, filled, or waiting.

### Level 3 - Advanced / Debug Mode

Only visible after explicit Advanced / Debug toggle.

This contains:

- raw module health;
- phase/certification compatibility artifacts;
- detailed source ledgers;
- full process console;
- long event lists;
- static bridge/exporter diagnostics;
- legacy labels needed for debugging.

## 6. Target Default Dashboard

### 6.1 System Operating Map

The first substantial surface should be a real system map, not a row of
unattached statuses.

Required node groups:

| Node | Plain label | Main question |
| --- | --- | --- |
| Fund Manager | You supervise | What needs review? |
| World sources | Data sources | Is the outside world visible? |
| Python COO | COO | Is routing and scheduling alive? |
| Local LLM | Research Analyst | Is local triage available? |
| Frontier LLM | Strategy Lead | Is deeper reasoning available? |
| Quantum / Quant | Head of Quant | Is quant consultation ready? |
| Signal + Risk | Risk gate | Can any idea become a paper trade? |
| Alpaca Paper | Paper desk | Can approved paper orders execute? |
| Postmortems | Learning loop | Are outcomes being learned from? |

Required edge semantics:

- Solid edge: active evidence/data flow.
- Dashed edge: context-only influence.
- Locked edge: explicit safety or authority boundary.
- Faded edge: degraded, waiting, or optional.
- Red edge: fail-closed block.

The map should show one sentence under it:

```text
Qadam is watching sources, turning evidence into hypotheses, filtering them
through strategy, quant, and risk, then using Alpaca Paper only when gates pass.
```

### 6.2 System Status

System status should be grouped by consequence, not by subsystem name.

Recommended rows:

- Ready to observe: source spine, durable replay, evidence runtime.
- Ready to reason: local LLM, frontier LLM, strategy lead.
- Ready to quantify: Q-CTRL/IBM/classical fallback status.
- Ready to paper trade: Alpaca Paper, execution policy, risk, kill switches.
- Needs attention: only items requiring Fund Manager action.

Avoid repeating the same global safety boundary in every row. Render it once as
the single safety strip.

### 6.3 Data Sources Connected

This should show source capability, not a long source inventory.

Default readout:

- online / total canonical sources;
- required source blockers;
- optional source gaps;
- most important connected source groups;
- source groups currently influencing trade ideas.

The long per-source table moves to Advanced / Debug Mode.

### 6.4 Trading Strategies

This should explain what Qadam is trying to trade in plain language.

Required strategy readouts:

- active paper mandate: grow GBP 100,000 toward GBP 200,000 over 60 days;
- active domains: prediction markets, crude oil, defence, silver,
  semiconductors;
- setup style: event-driven, evidence-gated, pricing/probability mispricing;
- current strategy posture: waiting, researching, blocked, staging, submitted,
  managing, learning;
- latest strategy packet summary.

This section should connect strategy to current evidence and trade candidates,
not sit as a static manifesto.

### 6.5 Qadam Activity Feed

This replaces vague "thoughts" with a public-safe live activity feed.

Feed item types:

- source observation;
- evidence packet created;
- research assessment;
- strategy hypothesis;
- signal integrity decision;
- risk decision;
- quant annotation;
- paper order event;
- position lifecycle event;
- postmortem or learning event;
- Fund Manager action item.

Every item should include:

- timestamp;
- actor;
- plain-language summary;
- status tone;
- link to proof drawer or advanced record;
- authority boundary where relevant.

The feed must never expose raw model hidden reasoning. It should show
summaries, decisions, and cited evidence.

### 6.6 Trade Consideration Board

This should answer what trades Qadam is thinking about making.

Default columns:

1. Watching.
2. Evidence forming.
3. Candidate.
4. Risk/quant review.
5. Paper order.
6. Position / exit.
7. Postmortem.

Each row should show:

- instrument/domain;
- setup thesis in one sentence;
- current gate;
- confidence/quality label;
- size or paper-capacity effect if known;
- blocker or next condition.

This is not an execution board. It is a decision-state board.

### 6.7 Paper Portfolio Capacity

This should be a first-class chart, not a buried account mirror.

Required chart:

- x-axis: time;
- y-axis: GBP portfolio value or paper capacity;
- baseline: GBP 100,000;
- target: GBP 200,000;
- overlays: deployed capital, idle cash, open risk, realized P&L,
  unrealized P&L;
- annotations: submitted paper orders, opens, closes, postmortems, halt states.

If historical points are sparse, show a clear honest state instead of a fake
curve.

## 7. Staged Implementation Plan

### S7A - Dashboard Truth Audit

Objective: prove exactly what the current dashboard repeats, hides, or fails to
explain.

Work:

- Inventory all visible labels, panels, badges, drawers, tables, and charts.
- Map each item to one user question.
- Identify duplicates across Overview, Evidence, Reasoning, Trades, Operations,
  and Advanced / Debug Mode.
- Identify items that are implementation-only and should move to debug.
- Identify missing Level 1 concepts.

Acceptance:

- Audit lists every primary dashboard section and whether it stays, merges,
  moves to drawer, moves to debug, or is removed.
- No implementation change is made.

Expected artifacts:

- `docs/qadam-dashboard-stage-7a-truth-audit-YYYY-MM-DD.md`
- `scripts/check_dashboard_stage7_truth_audit.js`

### S7B - Fund Manager Information Contract

Objective: define the exact default dashboard contract before changing UI.

Work:

- Define Level 1, Level 2, and Level 3 content rules.
- Define maximum visible sections on default Overview.
- Define required answer for each section.
- Define plain-language names and banned labels.
- Define mobile order.

Acceptance:

- The default dashboard has no more than seven Level 1 sections.
- Every Level 1 section answers a Fund Manager question.
- Every internal diagnostic term has a debug-only destination.
- The contract preserves all safety and authority boundaries.

Expected artifacts:

- `docs/qadam-dashboard-stage-7b-information-contract.json`
- `docs/qadam-dashboard-stage-7b-information-contract-audit-YYYY-MM-DD.md`

### S7C - View Model Reshape

Objective: build the new dashboard around purpose-built view models, not raw
status object sprawl.

Work:

- Add or reshape pure view-model builders for:
  - operating map;
  - system status;
  - connected source summary;
  - strategy posture;
  - activity feed;
  - trade consideration board;
  - paper portfolio capacity.
- Keep evidence runtime and durable replay visible as source-of-truth status,
  not as standalone debug clutter.
- Keep all authority fields false unless backend explicitly says otherwise.

Acceptance:

- View models render useful Level 1 summaries from the current cockpit status.
- Missing or stale runtime data creates honest empty states.
- No view model grants authority or infers readiness.

Expected files:

- `landing-page-repo/dashboard.js`
- `scripts/check_dashboard_stage7_view_models.js`

### S7D - Overview Rebuild

Objective: turn Overview into the real Fund Manager cockpit.

Work:

- Replace the current Overview composition with the seven Level 1 sections.
- Put the operating map first.
- Put the paper portfolio chart where it is visible without deep scrolling.
- Keep proof drawers collapsed by default.
- Preserve direct links to Trades, Evidence, Reasoning, and Operations detail.

Acceptance:

- Desktop default Overview fits in roughly two viewports without hiding any
  essential Level 1 section.
- Mobile Overview uses a clear section order and does not require scrolling
  through debug content.
- Overview does not show unexplained phase labels, raw status keys, or
  implementation codes.

Expected files:

- `landing-page-repo/dashboard.js`
- `landing-page-repo/auth.css`
- `scripts/check_dashboard_stage7_overview.js`

### S7E - Activity Feed And Thought Surface

Objective: make Qadam's reasoning process visible without exposing hidden model
chain-of-thought.

Work:

- Build a public-safe activity feed from existing event, cognition, evidence,
  trade, paper lifecycle, and postmortem status.
- Normalize actors as COO, Research Analyst, Strategy Lead, Head of Quant,
  Risk Gate, Paper Desk, Learning Loop, and Fund Manager.
- Link feed items to proof drawers or advanced records.
- Add freshness and source labels.

Acceptance:

- Feed shows the latest meaningful system events.
- Feed explains why Qadam is waiting or acting.
- Feed never exposes secrets, raw payloads, local paths, broker identifiers, or
  hidden chain-of-thought.

Expected files:

- `landing-page-repo/dashboard.js`
- `scripts/check_dashboard_stage7_activity_feed.js`

### S7F - Trade Consideration Board

Objective: make "what trades is Qadam thinking about?" answerable at a glance.

Work:

- Merge observed signals, hypotheses, candidates, staged orders, submitted
  orders, positions, exits, and postmortems into one board.
- Show gate state and blocker in plain language.
- Keep the old detailed trade lifecycle as proof drawers or Trades detail.

Acceptance:

- A Fund Manager can see every active idea and its current gate.
- Candidate, order, and position are visually distinct.
- The board cannot create or imply execution authority.

Expected files:

- `landing-page-repo/dashboard.js`
- `scripts/check_dashboard_stage7_trade_board.js`

### S7G - Paper Portfolio Capacity Chart

Objective: show how much of the GBP 100,000 paper portfolio is deployed,
idle, at risk, or progressing toward the GBP 200,000 target.

Work:

- Build a capacity series from local paper mirror, portfolio snapshots, paper
  order records, open positions, and closed trades.
- Render a line/area chart with baseline and target.
- Add honest empty states for missing history.
- Do not fabricate backfilled points.

Acceptance:

- Chart shows current paper value, baseline, target, deployed/idle split where
  available, and open-risk context.
- Historical gaps are labelled instead of smoothed over.
- Chart data is public-safe and read-only.

Expected files:

- `orchestrator/cockpit_status.py` if a sanitized chart series is needed.
- `landing-page-repo/dashboard.js`
- `scripts/check_dashboard_stage7_portfolio_capacity.js`

### S7H - Detail View Compression

Objective: keep detail available while reducing page length and duplication.

Work:

- Compress Trades, Evidence, Reasoning, and Operations into one or two primary
  sections each.
- Move long ledgers into proof drawers.
- Move raw/debug tables behind Advanced / Debug Mode.
- Remove repeated safety copy where the single safety strip already covers it.

Acceptance:

- Default detail views are materially shorter.
- No important operational fact is lost.
- Advanced / Debug Mode still exposes audit detail.

Expected files:

- `landing-page-repo/dashboard.js`
- `landing-page-repo/auth.css`
- `scripts/check_dashboard_stage7_detail_compression.js`

### S7I - Copy And Visual Discipline

Objective: make the dashboard feel like a serious fund cockpit, not a generic
admin template.

Work:

- Replace cryptic terms with fund-team language.
- Use status labels by consequence: OK, Waiting, Needs attention, Blocked,
  Optional, Read-only.
- Use fewer badges and more sentence-level explanations where useful.
- Use section dividers rather than nested card walls.
- Preserve the true dark cockpit aesthetic.

Acceptance:

- No visible primary copy depends on phase names or internal checker names.
- Each section has one direct explainer.
- Status colors are semantic and consistent.
- The UI remains dense enough for monitoring without feeling cramped.

Expected files:

- `landing-page-repo/dashboard.js`
- `landing-page-repo/auth.css`
- `scripts/check_dashboard_stage7_copy_visuals.js`

### S7J - User Guide Alignment

Objective: make the guide teach the same mental model as the dashboard.

Work:

- Rewrite the dashboard section of the user guide around the seven Level 1
  sections.
- Explain Advanced / Debug Mode separately.
- Explain that Qadam's activity feed is public-safe reasoning output, not raw
  hidden chain-of-thought.
- Explain the paper portfolio capacity chart and 60-day paper growth target.

Acceptance:

- User guide order matches dashboard order.
- No guide section refers to removed/default-hidden panels as primary.

Expected files:

- `docs/qadam-user-guide.md`
- `landing-page-repo/guide/index.html`
- `scripts/check_dashboard_stage7_guide_alignment.js`

### S7K - Testing And Acceptance

Objective: prove the simplification made the dashboard clearer and did not
weaken safety.

Work:

- Add static contract checks for all Stage 7 models.
- Add UI checks for default Overview section count and section order.
- Add copy checks for banned slop/internal labels.
- Add authority checks proving no UI-to-broker or UI-to-approval path exists.
- Add mobile and desktop screenshot checks.
- Add live JSON compatibility checks.

Acceptance:

- All existing dashboard checks still pass.
- New Stage 7 checks pass.
- Preflight deployment passes.
- Screenshots prove the default dashboard is shorter and clearer.
- Authority and public-safe boundaries are unchanged.

Expected commands:

```bash
node --check landing-page-repo/dashboard.js
node scripts/check_dashboard_stage7_view_models.js
node scripts/check_dashboard_stage7_overview.js
node scripts/check_dashboard_stage7_activity_feed.js
node scripts/check_dashboard_stage7_trade_board.js
node scripts/check_dashboard_stage7_portfolio_capacity.js
node scripts/check_dashboard_stage7_detail_compression.js
node scripts/check_dashboard_stage7_copy_visuals.js
node scripts/check_dashboard_stage7_guide_alignment.js
node scripts/check_dashboard_acceptance.js
./scripts/preflight_dashboard_deployment.sh
```

### S7L - Deployment Discipline

Objective: ship only after local and live truth match.

Work:

- Run full preflight.
- Deploy through `landing-page-repo/scripts/deploy-vercel-production.sh`.
- Verify live `https://qadam.trade/status/cockpit-status.json`.
- Verify live `https://qadam.trade/dashboard.js` includes Stage 7 markers.
- Commit root and dashboard repo changes separately.
- Push root and dashboard repo branches.

Acceptance:

- Live dashboard matches committed bundle.
- `qadam.trade` and `www.qadam.trade` aliases point to the same deployment.
- Both worktrees are clean.

## 8. Removal And Merge Rules

Stage 7 should use these rules during implementation:

- Remove a visible element if it is duplicated elsewhere and has no unique
  user question.
- Merge elements when they describe the same state from different modules.
- Move elements to a proof drawer when they support a Level 1 answer but are
  not the answer itself.
- Move elements to Advanced / Debug Mode when they are only useful for building,
  auditing, or debugging.
- Keep elements visible when hiding them would obscure a blocker, risk, source
  gap, trade state, or safety boundary.

## 9. Success Definition

Stage 7 is complete when:

- Overview shows the system map, system status, data sources, strategies,
  activity feed, trade consideration board, and paper portfolio capacity.
- A new Fund Manager can understand what Qadam is doing in under 60 seconds.
- A technical operator can still find detailed runtime proof in Advanced /
  Debug Mode.
- Page length is reduced without erasing operating truth.
- Duplicate safety, source, reasoning, and trade labels are materially reduced.
- The paper portfolio chart makes the GBP 100,000 to GBP 200,000 target visible.
- Qadam's reasoning/activity is visible as public-safe summaries and decisions.
- No new execution, approval, broker, quantum-job, Telegram-command, or
  live-capital authority is introduced.

## 10. Current Status

This is only the implementation plan. No Stage 7 implementation work has been
performed from this document yet.
