# Qadam Dashboard Navigation UX Plan

This plan turns the protected Qadam cockpit from a long operating page into an intuitive mission-control interface. The aim is not to hide complexity. The aim is to give each Fund Manager a stable way to move between the questions they actually have:

- What is Qadam watching?
- What is alive, pending, degraded, blocked, or local-only?
- What is Qadam thinking about next?
- What is it forbidden from doing?
- What trades are candidates, blocked, staged, open, closed, or ready for postmortem?
- What money state does the GBP 1000 paper account show?
- Which worldview and trading philosophy are shaping the current review?

The dashboard remains read-only. Navigation must never create authority to approve signals, stage orders, submit paper orders, write to a broker, send Telegram commands, expose local secrets, or enable live capital.

## Navigation Model

The dashboard should be navigated by operating question, not by implementation module.

| Navigation Item | User Question | Primary Data Contract |
| --- | --- | --- |
| Mission | What should I know first? | `mission_control` |
| Map | How does Qadam flow from data to paper outcome? | `system_map`, `modules`, `mission_control.stack` |
| Sources | What is Qadam watching and which feeds are degraded? | `sources`, `watching`, `source_health` |
| Cognition | What is Qadam thinking and why is it blocked? | `cognition`, `shadow_packets`, `hypotheses` |
| Trades | What trades are candidates, blocked, staged, or postmortem-ready? | `trade_intent`, `signal_integrity`, `staged_paper_order` |
| Money | What does the GBP 1000 paper account show? | `paper_account`, `alpaca_paper_mirror` |
| Safety | What is Qadam forbidden from doing? | `forbidden_actions`, `risk_agent`, `execution_policy` |
| Runtime | What processes have run recently? | `event_log`, `process_console`, deployment receipt |
| Governance | What have Fund Managers suggested or accepted? | `fund_manager_comments`, `communications` |

Worldview and Telegram remain visible as supporting sections, but they should not dominate the main navigation. The worldview powers interpretation and trading philosophy; Telegram is notification infrastructure.

## Phase N0 - Freeze The Current Shell

Objective: keep the current working protected dashboard as the baseline before navigation changes.

Implementation:

- Preserve Supabase-gated `/dashboard/`.
- Preserve the Mission Control first-screen priority.
- Preserve the static snapshot fallback.
- Preserve the secure bridge preference when authenticated bridge data is available.
- Preserve every read-only authority boundary in the current cockpit.

Acceptance:

- Existing dashboard renderer, bridge, Mission Control, and deployment checks still pass.
- No new navigation code changes the status contract.
- No section is removed just to reduce scroll length.

## Phase N1 - Define Section Anchors

Objective: make every major cockpit area addressable by stable IDs.

Implementation:

- Add stable anchors for Mission, Map, Sources, Cognition, Trades, Money, Safety, Runtime, and Governance.
- Add `data-cockpit-section` labels so JavaScript, tests, and future accessibility tooling can discover sections consistently.
- Keep section IDs short and human-readable.
- Do not use anchors for volatile rows, individual source cards, or raw event-log entries.

Acceptance:

- Direct links such as `/dashboard/#trade-layer` and `/dashboard/#process-console` land on useful sections.
- Section IDs survive dynamic rendering.
- Sections have scroll offsets so sticky navigation does not cover headings.

## Phase N2 - Add Sticky Cockpit Navigation

Objective: give the Fund Manager a visible way to move without reading the whole page linearly.

Implementation:

- Add a sticky navigation rail below the dashboard hero.
- Keep the labels short: Mission, Map, Sources, Cognition, Trades, Money, Safety, Runtime, Governance.
- Show a current-section label so the user knows where they are.
- Use horizontal scroll on narrow screens rather than wrapping into a tall navigation block.
- Keep navigation visually restrained; it is a control surface, not a marketing banner.

Acceptance:

- Desktop users can jump between major cockpit areas in one click.
- Mobile users can move between sections without scrolling through the full page.
- The navigation rail does not hide Mission Control, cards, or section headings.

## Phase N3 - Mobile Navigation Behaviour

Objective: make the cockpit usable on a phone by founding members reviewing it quickly.

Implementation:

- Keep the nav sticky near the top of the viewport.
- Make links horizontally scrollable with clear tap targets.
- Keep the current-section label visible but compact.
- Avoid dropdown-only navigation for first release because it hides the operating structure.
- Keep section headings and cards below the sticky nav with adequate scroll margin.

Acceptance:

- A phone user can jump from Mission to Trades, Money, Safety, or Runtime without long manual scrolling.
- Text does not overflow navigation buttons.
- Taps target the correct section.

## Phase N4 - Active Section State

Objective: show where the user is inside the cockpit.

Implementation:

- Use `IntersectionObserver` when available to mark the visible section as active.
- Fall back to click state if the browser does not support observation.
- Update the current-section label from the active link.
- Keep the code defensive so renderer tests with fake DOMs do not fail.

Acceptance:

- The active nav item changes as the user scrolls.
- The current-section label updates.
- Browser compatibility failures degrade to static links.

## Phase N5 - Panel Cross-Navigation

Objective: connect related sections without making users remember the whole operating map.

Implementation:

- Add small contextual links inside panel briefs later, for example `View source detail`, `Review trade layer`, `See money state`, and `Check safety`.
- Link trade cards to relevant safety and money sections.
- Link worldview cards to cognition and trade decision context.
- Link runtime events to the section they refer to when the event schema supports it.

Acceptance:

- Users can move from a trade candidate to its source, cognition, money, and safety context.
- Cross-links remain read-only.
- Links never imply approval or execution authority.

## Phase N6 - Mission Control Summary Routes

Objective: make the first screen function as a navigation hub, not only a summary.

Implementation:

- Turn Mission Control summary cards into deep links to their matching sections.
- Add direct routes from source readiness to Sources, thinking state to Cognition, candidate state to Trades, P&L to Money, and hard blocks to Safety.
- Keep the links descriptive enough for non-technical Fund Managers.

Acceptance:

- The top Mission Control surface answers the core questions and gives a direct path to detail.
- The user can start from the summary and drill down without scanning the whole page.

## Phase N7 - Search And Command Palette

Objective: later, support direct lookup across modules, sources, trades, and runtime records.

Implementation:

- Add a read-only command palette after the section navigation is stable.
- Search sources by provider, pipeline, status, credential state, and trust tier.
- Search trades by candidate, blocked, staged, open, closed, and postmortem state.
- Search runtime events by module and latest process state.
- Never expose raw secrets, local filesystem paths, raw LLM prompts, broker-write endpoints, or admin commands.

Acceptance:

- A Fund Manager can type `Alpaca`, `ACLED`, `oil`, `blocked`, or `paper account` and jump to the relevant section.
- The palette is read-only.
- No command or mutation verbs appear in search results.

## Phase N8 - Remember User Preferences

Objective: keep the cockpit comfortable for repeated use.

Implementation:

- Continue using `localStorage` for Executive / Terminal density.
- Later remember the last active section for convenience.
- Keep preferences local to the browser.
- Do not store credentials, session tokens, trade approvals, or personal comments in local navigation state.

Acceptance:

- Density preference persists.
- Future last-section persistence does not override Supabase auth or allowlist checks.

## Phase N9 - Accessibility, Testing, And Deployment

Objective: make navigation durable enough to ship and maintain.

Implementation:

- Add an automated static check for navigation HTML, CSS, JS, section IDs, cache keys, plan coverage, and read-only copy.
- Include the check in dashboard deployment preflight.
- Verify JS syntax and dashboard renderer after every change.
- Deploy only through the guarded production deployment script.
- Verify live dashboard HTML and JS after deployment.

Acceptance:

- `scripts/check_dashboard_navigation_ux.js` passes.
- `scripts/preflight_dashboard_deployment.sh` passes.
- The live dashboard includes the navigation rail, active-state script, and current cache key.
- No navigation change creates broker-write, paper-order, live-capital, Telegram-command, or hardware-submission authority.

## First Implementation Slice

The current slice implements N1, N2, N3, N4, and N9:

- Stable section anchors.
- Sticky cockpit navigation rail.
- Compact mobile behaviour.
- Active-section state.
- Automated navigation UX check.
- Deployment preflight integration.

N5 through N8 should be implemented only after the current navigation rail has been used on mobile and desktop by the founding members.
