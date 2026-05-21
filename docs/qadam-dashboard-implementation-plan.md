# Qadam Dashboard Implementation Plan

This document defines the cockpit as an operational mirror of Qadam, not a marketing page and not a static explainer.

The dashboard must answer five questions immediately:

1. What is Qadam watching?
2. Which modules are alive, pending, blocked, degraded, or local-only?
3. What is Qadam thinking about, and how is it analyzing sources and news?
4. Which trades is Qadam considering, blocking, preparing, holding, closing, or reviewing?
5. How is the £1,000 test account performing over time?

The live dashboard can start as a static site on `qadam.trade`, but its content must be driven by a read-only status contract exported from Qadam's local runtime.

## 1. Dashboard Principle

The cockpit is the visible nervous system of Qadam.

It should show:

- The data Qadam is watching.
- The state of each module.
- The current reasoning queue.
- The evidence behind current hypotheses.
- The trade candidates forming.
- The trades blocked by policy or risk.
- The paper account balance, drawdown, and timeline.
- The postmortem loop after a trade closes.
- The Fund Manager comments and governance notes.
- Telegram member communications: trade lifecycle messages, insight digests, system warnings, delivery state, and suppressed messages.

It should not show:

- Secret values.
- Broker credentials.
- Raw private tokens.
- A raw terminal with shell access.
- Any live-capital execution control.
- Any path from browser UI directly to broker orders.

## 2. Operating Boundary

First release mode:

- Account: £1,000 test/paper account.
- Live capital: disabled.
- Human access: founding Fund Managers only.
- Data persistence: local MacBook is canonical.
- Production web dashboard: read-only mirror.
- TradingView: chart/market-view layer now, webhook alert source later.
- Trade execution: only after deterministic Risk Agent, Signal Integrity Gate, broker adapter, Event Log, kill-switch, and postmortem contracts exist.

The dashboard can say what Qadam is considering. It cannot imply a trade is guaranteed unless the backend state actually says an order is staged or submitted.

## 3. The Questions The Dashboard Must Answer

The dashboard is successful only when it can answer these questions from system state, not from hardcoded copy.

| Question | Dashboard Answer | Source Of Truth |
| --- | --- | --- |
| What is Qadam watching? | Source groups, live/degraded status, last payload, trust score, and whether the source can influence signals. | Source Registry, heartbeat results, Event Log. |
| What modules are alive? | Node status for COO, Event Log, local LLM, frontier LLM, quantum engine, Risk Agent, trade layer, and cockpit bridge. | Orchestrator health contract. |
| What is Qadam thinking about? | Current focus, hypotheses, evidence packets, model activity, missing corroboration, blocked reasons. | Shadow Intelligence queue, Research Analyst output, Strategy Lead review records. |
| What worldview is shaping the question? | Private world-model lens, active priors, decision chain, and evidence boundary. | `how-the-world-works/`, world-model claim cards, status contract. |
| What news or data changed its mind? | Evidence timeline showing which source event entered which hypothesis and whether it strengthened, weakened, or blocked a thesis. | Event Log and Evidence Packet store. |
| What trade is Qadam considering? | Trade candidates with instrument, direction, venue, catalyst, confidence, risk, proposed entry, invalidation, and status. | Trade Candidate store. |
| What trade is Qadam about to make? | Only items in `staged_paper_order` or `submitted_paper_order`; everything else is only an idea, hypothesis, blocked candidate, risk review, or execution-policy hold. | Risk Agent, Execution Policy, staged-order, and broker adapter state. |
| What is Qadam forbidden from doing? | Live-capital disabled flag, broker-write authority status, stale-data blocks, missing credential blocks, and kill-switch state. | Policy Gate, Execution Venue Registry, Risk Agent. |
| Is Qadam making money? | Starting balance, current paper balance, realized/unrealized P&L, drawdown, open positions, closed trades, and maturity count. | Paper broker/account mirror, Trade Journal. |
| What is the timeline? | Source event -> hypothesis -> candidate -> risk decision -> order -> position -> exit -> postmortem. | Event Log joins across source, cognition, risk, and trade events. |
| What did Qadam tell members? | Telegram message queue, last sent message, failed/suppressed messages, subscriber state, and digest status. | Telegram communications outbox and delivery log. |

## 4. Truth Boundaries

The dashboard must separate four different kinds of information:

| Layer | Meaning | Dashboard Treatment |
| --- | --- | --- |
| Observation | Something happened in a data source, chart, feed, or news stream. | Show as source event or watch item. |
| Worldview prior | Qadam's private power-map lens says which hidden incentives, narratives, or strategic relationships may matter. | Show as decision context, never as proof. |
| Interpretation | Qadam thinks the observation may matter. | Show as hypothesis, with evidence and missing corroboration. |
| Trade intent | Qadam has a structured trade idea. | Show as candidate, blocked candidate, or risk review. |
| Execution state | Qadam has permission to place, hold, or close a paper trade. | Show only when Risk Agent, Execution Policy, staged-order, and broker state confirm it. |

This prevents the cockpit from exaggerating. A hypothesis is not a trade. A candidate is not an order. A blocked trade is not a failure; it is proof that the control system is working.

The worldview lens is also not evidence. It powers Qadam's trading philosophy by shaping the questions it asks about power, narrative, energy, money, institutions, and US-China relations, but every tradable implication must still pass live corroboration, the Akber filter, Signal Integrity Gate, and Risk Agent.

## 5. Dashboard Architecture

### Current Production Constraint

`qadam.trade` currently serves a static cockpit from `landing-page-repo`.

The local MacBook orchestrator is private and not exposed to Vercel.

Therefore the next dashboard architecture is:

```text
Local Qadam runtime
  -> writes canonical Event Log and runtime state
  -> exports sanitized cockpit-status.json
  -> copies static-safe snapshot into landing-page-repo/status/
  -> Vercel serves qadam.trade/dashboard/
  -> dashboard fetches status/cockpit-status.json
```

This gives the founding members a real operational view without opening inbound access to the MacBook.

### Later Architecture

When the static snapshot is too limited:

```text
Local Qadam runtime
  -> signed read-only status bridge
  -> authenticated API endpoint
  -> qadam.trade dashboard
```

This later bridge must be read-only, rate-limited, authenticated, and incapable of sending broker commands.

## 6. Core Data Contract

The dashboard should render from one sanitized status file:

```json
{
  "schema_version": 1,
  "generated_at": "2026-05-16T20:00:00Z",
  "mode": "paper",
  "capital": {
    "mirror_status": "ok",
    "account_scope": "first_release_gbp_1000_trial",
    "broker": "local_mirror_pending_alpaca_readonly",
    "connection_status": "local_mirror_not_broker_connected",
    "starting_balance_gbp": 1000,
    "current_balance_gbp": 1000,
    "cash_gbp": 1000,
    "equity_gbp": 1000,
    "realized_pnl_gbp": 0,
    "unrealized_pnl_gbp": 0,
    "drawdown_pct": 0,
    "max_drawdown_pct": 0,
    "live_capital_enabled": false,
    "write_authority": false,
    "maturity_closed_trade_target": 100,
    "maturity_closed_trade_count": 0,
    "open_positions": [],
    "closed_trades": [],
    "postmortems_due": [],
    "postmortems_complete": [],
    "equity_curve": []
  },
  "watching": [],
  "modules": [],
  "process_console": [],
  "decision_philosophy": {
    "status": "ok",
    "corpus": "how-the-world-works",
    "role": "private_worldview_prior",
    "claim_count": 5,
    "foundational_prior_count": 5,
    "decision_chain": [
      "private worldview prior",
      "observable signatures",
      "live-source corroboration",
      "Akber 6-stage filter",
      "Signal Integrity Gate",
      "Risk Agent",
      "paper trade or postmortem"
    ],
    "active_lenses": [],
    "boundary": "World-model claims are private priors, not factual evidence or trade triggers."
  },
  "cognition": {
    "status": "shadow_ready",
    "current_focus": [],
    "shadow_packets": [],
    "hypotheses": [],
    "evidence_packets": [],
    "model_activity": [],
    "analysis_timeline": [],
    "blocked_reasons": [],
    "boundary": "Cognition is shadow-only until Signal Integrity Gate, Risk Agent, Execution Policy, staged-order, and broker contracts all pass."
  },
  "trade_layer": {
    "summary": {
      "status": "ok",
      "intent_count": 0,
      "candidate_count": 0,
      "blocked_count": 0,
      "execution_allowed_count": 0,
      "paper_order_allowed_count": 0
    },
    "watching": [],
    "candidates": [],
    "blocked": [],
    "staged_orders": [],
    "open_positions": [],
    "closed_trades": [],
    "postmortems_due": [],
    "postmortems_complete": []
  },
  "forbidden_actions": [],
  "fund_manager_notes": []
}
```

No secret values or raw credentials may appear in this file.

### Required Top-Level Contract Sections

| Section | Purpose |
| --- | --- |
| `capital` | Shows paper account money, P&L, drawdown, and live-capital disabled state. |
| `watching` | Shows source groups, source health, last payloads, and data quality. |
| `modules` | Shows system-map nodes, status, heartbeat, current process, and authority. |
| `process_console` | Shows read-only runtime events, never shell access. |
| `decision_philosophy` | Shows the private worldview lens, claim-card count, decision chain, and evidence boundary. |
| `cognition` | Shows what Qadam is currently analyzing and why. |
| `trade_layer` | Shows candidates, blocked trades, paper orders, positions, exits, and postmortems. |
| `forbidden_actions` | Shows what the system is explicitly blocked from doing. |
| `fund_manager_notes` | Shows private human oversight comments and suggestions. |

## 7. Main Dashboard Views

### A. System Map

This is the main view.

It shows:

```text
Live Sources / Watching
  -> Source Registry
  -> Event Log / Raw Archive / Knowledge Graph
  -> Local LLM [Research Analyst]
  -> Frontier LLM [Strategy Lead]
  -> Quantum/Classical Oracle [Head of Quant]
  -> Strategy + Risk Gate
  -> Trade Layer
  -> Postmortem / Learning Loop
```

Each node must show:

- Status: online, degraded, pending, blocked, offline, local-only.
- Last heartbeat.
- Current process.
- Degraded reason.
- Whether execution authority exists.
- Whether the node is local-only or visible in the web cockpit.

The map should be readable on mobile in portrait mode. The first screen should explain the whole fund at diagram level before the user scrolls into detailed tables.

### B. Watching View

This answers: what is Qadam watching?

It should show live source groups:

- Conflict: ACLED, GDELT, Oref.
- Physical: NASA FIRMS, AIS, Wingbits.
- Macro: FRED, BLS, ECB, BIS.
- Market: Alpaca, Kalshi, Polymarket, Unusual Whales.
- Social/narrative: RSS, Telegram, X, Reddit.
- TradingView: manual chart layer now, webhook alerts later.

Each source should show:

- Status.
- Trust score.
- Last successful heartbeat.
- Last payload time.
- Credential status.
- Latency.
- Whether it can influence signals.

### C. Cognition View

This answers: what is Qadam thinking about?

It should not show vague AI text. It should show structured reasoning state:

- Current focus.
- Hypotheses under review.
- Evidence packets.
- Model used: local LLM, frontier LLM, quantum/classical job.
- Confidence state.
- Missing corroboration.
- Why a hypothesis is still blocked.

Example:

```text
Hypothesis: oil supply shock risk rising
Evidence: FIRMS refinery heat anomaly, GDELT regional escalation, crude futures move
Missing: shipping confirmation, second source, options flow
State: shadow review
Execution: forbidden
```

It should also show the latest analysis timeline:

```text
Data source changed -> Research Analyst summarized -> Strategy Lead challenged -> Risk Gate accepted/blocked -> trade layer updated
```

The viewer should be able to tell whether Qadam is idle, waiting for data, compressing noisy data locally, escalating a thesis to the frontier model, running a quant comparison, or refusing to act.

### D. Trade Layer

This answers: what trades is Qadam considering or making?

Trade states:

| State | Meaning |
| --- | --- |
| `observed_signal` | Raw data suggests something may matter. |
| `hypothesis` | Qadam has formed a possible market thesis. |
| `candidate` | Thesis has enough structure to be reviewed as a trade idea. |
| `blocked` | Trade idea failed evidence, risk, policy, latency, or credential checks. |
| `risk_review` | Candidate is being checked for size, drawdown, venue, and stale data. |
| `staged_paper_order` | Paper order is ready but not submitted. |
| `submitted_paper_order` | Paper order was sent to the test broker. |
| `open_position` | Paper position is live. |
| `exit_planned` | Exit/invalidation is active. |
| `closed_trade` | Position is closed. |
| `postmortem_due` | Trade closed but has not been reviewed. |
| `postmortem_complete` | Lesson is recorded. |

Every trade candidate should show:

- Instrument.
- Direction.
- Venue.
- Catalyst.
- Evidence summary.
- Current estimated probability.
- Market-implied probability or price gap where applicable.
- Proposed entry.
- Invalidation.
- Expected holding window.
- Risk size.
- Status.
- Why it is allowed or blocked.

The trade layer must show blocked trades as first-class objects. Blocked trades are evidence that the system is enforcing discipline.

### Trade Intent Rules

The dashboard wording must follow these rules:

| Dashboard Phrase | Allowed When |
| --- | --- |
| `Watching` | Source event exists but no thesis exists. |
| `Thinking About` | Hypothesis exists, but no trade candidate exists. |
| `Considering Trade` | Candidate exists but Risk Agent has not approved a paper order. |
| `Blocked` | Evidence, policy, latency, risk, credential, or mode checks failed. |
| `Preparing Paper Trade` | Risk Agent has approved a staged paper order. |
| `Submitted Paper Trade` | Broker adapter confirms paper order submission. |
| `Open Paper Position` | Paper broker/account mirror confirms position. |
| `Closed` | Paper broker/account mirror confirms exit. |
| `Postmortem Due` | Closed trade has no completed review yet. |

The dashboard must never say Qadam is "going to make" a trade unless the trade state is `staged_paper_order` or `submitted_paper_order`.

### E. Money And Timeline View

This answers: how much money is Qadam making or losing, and over what period?

For the first month:

- Starting balance: £1,000.
- Current balance.
- Realized P&L.
- Unrealized P&L.
- Drawdown.
- Number of trade candidates.
- Number blocked.
- Number submitted.
- Number open.
- Number closed.
- Win/loss count after close.
- Expectancy only after enough trades.
- 100-trade maturity benchmark progress.

The timeline should show:

```text
Source event -> hypothesis -> candidate -> risk decision -> order -> position -> exit -> postmortem
```

In early phases, this view should show `not connected yet` rather than invented P&L. Once paper-account mirroring exists, the money panel becomes authoritative for the £1,000 trial account.

### F. Process Console

This answers: what is currently running?

It should be a read-only event feed, not a shell terminal.

Examples:

```text
20:41 source heartbeat completed: 35 sources checked
20:42 NASA FIRMS degraded: credential missing
20:43 Research Analyst idle: LM Studio not running
20:44 Gemini probe pending
20:45 execution blocked: Phase 1 only
```

Console events should come from Event Log or runtime status, never arbitrary shell output.

### G. Fund Manager View

This answers: what should a human overseer understand now?

It should show:

- System status.
- What Qadam is watching.
- What Qadam is thinking about.
- Trades forming.
- Trades blocked.
- Current account state.
- Open questions for humans.
- Fund Manager comments.
- Suggestions awaiting review.

The Fund Manager should not need to read code to understand the system.

## 8. Dashboard Panels

The first operational dashboard should contain these panels.

| Panel | Purpose | Phase |
| --- | --- | --- |
| Operating Map | Shows how Qadam flows from source data to reasoning to trade layer. | D0-D2 |
| Status Strip | Shows paper mode, live-capital disabled, snapshot freshness, and kill-switch state. | D1-D2 |
| Watching Queue | Shows what sources and themes are active. | D3 |
| Cognition Queue | Shows current focus, hypotheses, evidence packets, and missing corroboration. | D4 |
| Trade Intent Board | Shows candidates, blocked trades, staged orders, open positions, closed trades, and postmortems. | D5-D6 |
| Money Timeline | Shows £1,000 paper balance, P&L, drawdown, trade count, and 100-trade benchmark progress. | D6 |
| Worldview Lens | Shows how the `how-the-world-works/` corpus frames decisions without becoming evidence. | D0-D7 |
| Process Console | Shows read-only runtime events. | D1-D2 |
| Forbidden Actions | Shows why live capital, broker writes, stale data, or unverified sources are blocked. | D1-D5 |
| User Guide | Explains the dashboard panels, statuses, trade states, member permissions, daily routine, and red flags. | D8A |
| Fund Manager Notes | Shows private comments and improvement suggestions. | D8 |
| Communications | Shows Telegram Bot status, dry-run/live-send mode, verified members, queued messages, failed sends, suppressed sends, and last delivered trade/insight update. | D8A |

## 8A. Modular Dashboard Build Track

The D-phases describe delivery milestones. The dashboard should be built as smaller modules so each section can be designed, implemented, reviewed, and tested independently.

Each dashboard module must include:

- A status-contract slice.
- A renderer slice.
- A plain-English empty state.
- A status/error/degraded state.
- A section hoverover explainer.
- A sanitizer check if it renders runtime, source, member, Telegram, broker, or credential-adjacent data.
- A local acceptance check that proves the section is populated from state, not hardcoded claims.

Recommended module order:

| Module | Purpose | Depends On | Exit Check |
| --- | --- | --- | --- |
| M0 Safety Frame | Persistent paper-mode, live-capital-disabled, broker-write-blocked, and kill-switch visibility. | Status contract shell. | A user can identify Qadam's authority before reading any panel. |
| M1 Help System | Shared info/hoverover component and copy registry for every dashboard section. | None. | Every dashboard section has a hover/focus explainer. |
| M2 System Flow Map | Real node-edge map showing how notes/modules connect from sources to postmortems. | `modules`, `watching`, `trade_layer`. | A user can trace the system path without reading the guide. |
| M3 Watching | Source groups, source health, credentials, heartbeat, trust, and signal influence. | `watching`, source heartbeat. | Every source group explains what it is watching and whether it can act as evidence. |
| M4 Cognition | Current focus, hypotheses, evidence packets, model activity, missing corroboration, and blocked reasons. | `cognition`. | A hypothesis cannot be mistaken for a trade. |
| M5 Private Edge | Worldview lens, private priors, observables to check, and evidence boundary. | `decision_philosophy`. | The UI clearly says private priors are not proof. |
| M6 Trade Layer | Observed signals, candidates, blocked trades, staged/submitted paper orders, open/closed positions, postmortems. | `trade_layer`, `capital`. | The trade state vocabulary matches backend state exactly. |
| M7 Money Timeline | Paper balance, P&L, drawdown, positions, closed trades, maturity progress. | `capital`. | The panel never invents broker-derived values. |
| M8 Forbidden Actions | Live-capital, broker-write, stale-data, credential, risk, and kill-switch blocks. | `forbidden_actions`, execution registry. | Blocks read as deliberate safety rails, not generic errors. |
| M9 Process Console | Read-only runtime events. | `process_console`. | No shell-like wording or command affordance appears. |
| M10 Fund Manager Notes | Private comments linked to modules, sources, signals, trades, and postmortems. | Auth, comments store. | A comment can be linked to a specific dashboard object. |
| M11 Communications | Telegram notify-only status, dry-run/live mode, queue, delivery, failure, suppression. | `communications.telegram`. | Telegram cannot be read as an execution channel. |
| M12 Guide Alignment | Protected User Guide and in-dashboard explainers stay in sync. | M1-M11. | Guide and hoverover copy define the same states and boundaries. |

Implementation rule: do not start a module's richer UI until its contract slice and explainer copy exist. This keeps the dashboard understandable while it becomes more powerful.

## 8B. Section Hoverover Explainer Contract

Every dashboard section must have an information hoverover. The hoverover is not marketing copy. It is a short operator explanation that helps a founding Fund Manager understand what the section means and what it cannot do.

Interaction requirements:

- Show the explainer on hover.
- Show the same explainer on keyboard focus.
- Support mobile by making the information control tappable/focusable.
- Use plain language from `docs/qadam-user-guide.md`.
- Include the section's authority boundary where confusion would create risk.
- Never expose secrets, local paths, raw payloads, chat IDs, broker credentials, or raw model text.

Recommended explainer shape:

```json
{
  "id": "trade_layer",
  "title": "Trade Layer",
  "body": "Shows observed signals, candidates, blocked trades, paper orders, open positions, closed trades, and postmortems.",
  "boundary": "A candidate is not an order. Qadam is not about to trade unless the state is staged_paper_order or submitted_paper_order."
}
```

Required first-release explainers:

| Section | Hoverover Explainer |
| --- | --- |
| Status / Safety Strip | Shows operating mode, paper account scope, live-capital block, broker-write block, and kill-switch state before any detail. |
| System Operating Map | Shows how information moves from watched sources through logs, reasoning, risk checks, paper execution, postmortems, and learning. |
| Watching | Shows source groups, heartbeat, trust, credential state, and whether a source can influence evidence. Degraded sources are weak evidence. |
| Cognition | Shows current hypotheses, model activity, evidence packets, missing corroboration, and why the idea is blocked from the trade layer. |
| Private Edge Layer | Shows Qadam's private worldview lens. It can shape questions but cannot become evidence or trigger trades. |
| Trade Layer | Shows the trade ladder. Observed signals, hypotheses, candidates, blocked trades, orders, positions, and postmortems must remain distinct. |
| Money | Shows the £1,000 paper/test mirror, P&L, drawdown, positions, closed trades, and 100-trade maturity progress. |
| Forbidden | Shows what Qadam is deliberately blocked from doing. Blocks are safety rails, not generic failures. |
| Process Console | Shows read-only runtime events. It is not shell access and cannot run commands. |
| Fund Manager Comments | Shows member suggestions and governance notes linked to modules, sources, signals, trades, or postmortems. |
| Telegram Communications | Shows outbound-only notification state. Telegram cannot place, approve, reject, modify, close, or resize trades. |
| User Guide | Opens the protected full guide for members who need the longer explanation. |

Exit gate:

- A user can hover or focus every panel heading and understand what the panel is for.
- The hoverover copy matches the User Guide vocabulary.
- The hoverover copy makes execution authority explicit where relevant.
- The hoverover works without JavaScript if possible; JavaScript may enhance dismissal or mobile behavior later.

## 9. Implementation Phases

### Phase D0 - Static Cockpit Proof

Status: implemented locally as the first live shell, with a static fallback that remains understandable even if the status snapshot is unavailable.

Scope:

- Supabase login.
- Founding Fund Manager allowlist.
- Static dashboard.
- Static system map.
- Static trade layer.
- D0/foundation shell label.
- Static fallback content for System Map, Watching, Cognition, Forbidden, Trade Layer, Money, Process Console, Worldview, and Comments before JSON hydration.
- Login redirect errors that explain non-allowlisted access.

Limit:

- Explains Qadam but does not yet read live Qadam state.
- No additional hardcoded dashboard claims should be added here unless they are explicitly marked as placeholders.
- Live routing remains stable while D1/D2 are built behind it.
- Anas cannot sign in until his allowlist email is known and added; the current email allowlist covers Ramin, Troy, Akber, and Ion.

Exit gate:

- Founding member can log in and see the cockpit.
- `qadam.trade` exposes `/login/`, `/sign-up/`, and `/dashboard/`.
- The page labels itself as a static/foundation shell and does not imply live orchestrator connectivity.

### Phase D1 - Read-Only Status Snapshot

Objective: make the dashboard truthful.

Status: implemented and hardened as the first local public-safe status contract.

Build:

- `orchestrator/cockpit_status.py` builds and validates the public-safe contract.
- `scripts/export_cockpit_status.py` writes the status snapshot.
- `scripts/check_cockpit_status.py` validates D0 freeze, paper mode, blocked live capital, modules, sources, and sanitizer rules.
- `data/runtime/cockpit-status.json` is the local runtime output.
- `landing-page-repo/status/cockpit-status.json` is the static-safe copy for the live site.
- Snapshot sanitizer blocks raw tokens, local absolute paths, secret names, allowlist emails, and shell/broker authority.
- The payload includes `d1_snapshot` metadata declaring `phase=D1`, `read_only=true`, `public_safe=true`, `browser_authority=read_only`, and `local_orchestrator_exposed=false`.
- `scripts/check_cockpit_status.py` validates both the runtime copy and the landing-site copy, then fails if they differ.
- Sanitizer coverage includes token-like values, emails, known API-key prefixes, raw payload keys, local absolute paths, chat IDs, bot tokens, access/refresh tokens, private keys, and webhook secret keys.

Data sources:

- Orchestrator health.
- Source heartbeat.
- Agent runtime summary.
- Shadow intelligence summary.
- Execution registry.
- Empty trade stores.

Exit gate:

- Dashboard renders real module/source status from JSON.
- Timestamp shows when the snapshot was generated.
- No secret values appear.
- No allowlist emails appear.
- No local absolute paths appear.
- Runtime and static-site status copies match exactly.
- Browser authority remains read-only.
- The local orchestrator is not exposed to the web.
- D1 does not yet change the live dashboard rendering; that happens in D2.

### Phase D2 - Dynamic Dashboard Renderer

Objective: make `qadam.trade/dashboard/` fetch and render the snapshot.

Status: implemented and contract-checked locally in the static cockpit repo.

Build:

- `landing-page-repo/dashboard.js` fetches `/status/cockpit-status.json`.
- `landing-page-repo/dashboard/index.html` now contains data placeholders instead of a hardcoded operating map.
- `landing-page-repo/auth.js` renders the dashboard only after Supabase session and allowlist checks pass.
- The dashboard renders system nodes, source status groups, cognition queue, forbidden actions, trade state, capital fields, and process console from the status contract.
- Empty trade arrays render explicitly as `not connected yet`; D6 paper-account fields now render from the read-only mirror instead of invented activity.
- Status-derived HTML is escaped before insertion into the cockpit UI, and dynamic status class names are normalized before use.
- The renderer marks the document as `data-dashboard-status=rendered` after a successful snapshot render and `snapshot-error` when the snapshot cannot be fetched.
- `scripts/check_dashboard_renderer.js` executes the browser renderer against `landing-page-repo/status/cockpit-status.json` with a mocked DOM and fetch layer.

Exit gate:

- Hardcoded node statuses are removed.
- Dashboard visibly changes when the JSON changes.
- Local render contract check proves the renderer populates all key dashboard panels from `landing-page-repo/status/cockpit-status.json`.
- Local render contract check proves a changed source and changed trade candidate appear in the rendered dashboard output.
- Failed snapshot fetches render the `Status contract unavailable` state instead of silently leaving stale dynamic state.

### Phase D3 - Watching View

Objective: answer what Qadam is watching.

Status: implemented and contract-checked locally in the status contract and static dashboard renderer.

Build:

- `orchestrator/cockpit_status.py` now exports source readiness, registry status, promoted-adapter flag, auth class, cadence, endpoint count, degraded reason, credential status, trust score, last heartbeat, and signal-influence boundary.
- `source_pipeline_summary` groups source counts, degraded counts, pending counts, missing credentials, and adapter-ready counts by pipeline.
- `source_heartbeat_history` exports the last compact heartbeat runs without local paths or secrets.
- `landing-page-repo/dashboard.js` renders every source under expandable pipeline groups.
- `landing-page-repo/auth.css` supports mobile-readable source rows, badges, and metadata chips.
- The Watching renderer now exposes auth class, registry status, endpoint count, last payload state, latency state, heartbeat, credential state, trust score, adapter status, and signal-influence boundary for each source.
- The summary strip shows source count, online/degraded/pending/local-only counts, missing credentials, promoted adapters, last heartbeat, and signal-influence count.
- `scripts/check_cockpit_status.py` validates D3 source fields, 35 registered World Monitor sources plus the TradingView alert row, 5 pipeline groups, pipeline/source-count agreement, and blocked signal influence.
- `scripts/check_dashboard_watching_view.js` verifies the rendered Watching panel includes D3 source details, the TradingView observed-alert source, pipeline grouping, and the empty-source fallback.

Exit gate:

- All registered sources appear as online, degraded, pending, or local-only, with raw unavailable/deferred reasons visible on the source row.
- All 35 registered sources are rendered under their 5 pipeline groups; D7 appends TradingView paid alerts as an observed market alert source.
- The Watching panel exposes credential/readiness state without exposing secret names or local paths.
- The Watching panel exposes each source's auth class, registry state, endpoint count, payload/heartbeat state, and signal-influence boundary.
- A local D3 render check proves the panel renders 36 watched sources under 5 pipeline groups and shows the no-source empty state when the array is empty.

### Phase D4 - Cognition View

Objective: answer what Qadam is thinking about.

Status: implemented and contract-checked locally in the status contract and static dashboard renderer.

Build:

- Shadow packet store exposed through the public-safe status contract.
- Hypothesis cards with thesis, confidence, evidence count, invalidation, and generated-by state.
- Evidence packet cards and evidence item summaries, with raw references stripped.
- Model activity state for Research Analyst, Strategy Lead, and Head of Quant.
- Head of Quant oracle state: latest backend, recommendation, result count, optional simulator availability, and zero-authority flags.
- Read-only paper-account context inside Cognition: £1000 policy allocation, Alpaca paper mirror balance, P&L, drawdown, position/order counts, maturity progress, and explicit no-authority flags.
- Signal Integrity Gate summary inside Cognition: total reviews, blocked/held/risk-shadow counts, candidates created, execution count, and explicit no-order/no-candidate boundary.
- Recent Signal Integrity Review cards: instrument focus, integrity score, source/evidence counts, trust scores, missing correlations, Akber filter output, failure reasons, required next steps, worldview-prior status, and non-execution flags.
- Missing corroboration field.
- Blocked-by-reason display.
- Analysis timeline showing why the trade layer has not been reached.
- The Cognition renderer now opens with a compact state summary: cognition state, focus count, hypothesis count, evidence item count, shadow packet count, local assessment count, model count, Signal Integrity review count, and execution boundary.
- Hypothesis cards are explicitly labelled `Hypothesis, not trade` and `Execution blocked`, with created time, linked evidence packet, invalidation, missing corroboration, worldview context, Signal Integrity status/score, and the Risk Agent boundary.
- Evidence packet cards now show source count, evidence item count, trust scores, created time, source list, missing correlations, and sanitized evidence item summaries without raw references.
- Shadow packets show their no-signal/no-risk/no-execution boundary.
- `scripts/check_dashboard_cognition_view.js` verifies the rendered Cognition panel includes model roles, read-only paper-account context, Signal Integrity Gate state, Head of Quant model activity, Akber filter output, non-executable authority, hypotheses, evidence packets, missing corroboration, blocked execution, the trade-layer boundary, and empty-state behavior.

Exit gate:

- At least one test hypothesis can appear with evidence and blocked execution state.
- `scripts/check_cockpit_status.py` validates shadow packets, model activity, evidence items, analysis timeline, blocked reasons, and non-executable hypotheses.
- `scripts/check_cockpit_status.py` also validates D4 required fields for shadow packets, local Research Analyst assessments, read-only paper-account context, Signal Integrity summaries/reviews, Head of Quant oracle summary, hypotheses, evidence packets, non-executable model authority, evidence links, raw-reference stripping, and the `trade layer not reached` timeline boundary.
- A local D4 render check proves the panel renders 5 hypotheses, 5 evidence packets, 5 shadow packets, 5 Signal Integrity reviews, model activity, blocked execution, and the empty cognition fallback.

### Phase D5 - Trade Intent Board

Objective: answer which trades Qadam is considering.

Status: implemented and contract-checked locally as a non-executing Trade Intent Store.

Build:

- `trade_candidates.jsonl` local store.
- `risk_policy_reviews.jsonl` local Risk Agent policy-review store.
- `execution_policy_reviews.jsonl` local Execution Policy / kill-switch review store.
- Trade candidate schema.
- Blocked trade schema.
- Read-only Risk Agent review schema.
- Read-only Execution Policy review schema.
- Candidate status transitions.
- Dashboard candidate and blocked-trade tables.
- Public-safe cockpit export with `execution_allowed=false` and `paper_order_allowed=false` for D5 candidate/blocked records.
- Public-safe cockpit export with Risk Agent policy-review status, policy score, blocked reasons, required next steps, account context, and explicit zero-authority flags.
- Public-safe cockpit export with Execution Policy status, selected venue, venue mode, kill switches, execution checks, blocked reasons, required next steps, and explicit zero-authority flags.
- Public-safe cockpit export with Broker Reconciliation status, broker echo state, idempotency/prewrite/duplicate-guard state, blocked reasons, required next steps, and explicit zero-authority flags.
- Public-safe cockpit export with Dry-run Paper-submit Receipt status, simulated receipt state, receipt checks, blocked reasons, required next steps, and explicit zero-authority flags for broker POST, paper-order submission, broker writes, and live capital.
- D5 test records: one candidate and one blocked trade intent, both clearly marked as local test intent with no broker route.
- The Trade Board now renders an explicit state ladder: observed signal, candidate, blocked trade, unavailable paper order states, and postmortem.
- Observed TradingView alerts are labelled `Observed signal only`, `not a candidate`, `execution blocked`, and `no paper order`.
- Candidate records are labelled `Candidate, not order`, with strategy, price gap, source signal, Akber filter, risk checks, tags, and no-broker-route boundary.
- Blocked trades are rendered as first-class board items with blocked reason, failed/pending filter state, risk checks, and zero execution authority.
- Risk Agent policy reviews are rendered as first-class board items with status, policy score, max-risk cap, account state, Signal Integrity reference, blocked reasons, required next steps, and badges for execution blocked, no paper order, no order created, and broker write blocked.
- Execution Policy reviews are rendered as first-class board items with status, selected venue, venue mode, kill switches, execution checks, blocked reasons, required next steps, and badges for execution blocked, no staged paper order, no paper order created, broker write blocked, and live capital disabled.
- Disabled staged paper-order reviews are rendered as first-class board items with status, hypothetical order, reconciliation checks, blocked reasons, required next steps, and badges for execution blocked, no staged order created, paper order not submittable, broker write blocked, and live capital disabled.
- Read-only broker reconciliation reviews are rendered as first-class board items with status, broker echo, reconciliation checks, blocked reasons, required next steps, and badges for idempotency not allocated, Event Log prewrite not created, duplicate guard not ready, broker echo not verified, paper submit blocked, broker write blocked, and live capital disabled.
- Dry-run paper-submit receipt reviews are rendered as first-class board items with status, simulated receipt, idempotency preview, Event Log prewrite schema, pre-trade snapshot schema, duplicate-order guard schema, receipt checks, blocked reasons, required next steps, and badges for dry-run receipt not created, paper order not submitted, broker POST not called, broker write blocked, and live capital disabled.
- `scripts/check_dashboard_trade_board.js` verifies the rendered Trade Board includes observed signal, candidate, blocked trade, Risk Agent policy router, Execution Policy and kill switches, disabled staged paper-order contract, read-only broker reconciliation, dry-run paper-submit receipt, state ladder, no broker route boundary, unavailable lifecycle states, and empty-state behavior.

Exit gate:

- Dashboard can show a candidate and a blocked trade from local data.
- `scripts/check_trade_intent.py` validates the store, candidate count, blocked count, and zero execution authority.
- `scripts/check_trade_intent.py` also validates D5 sample records, Akber filter fields, risk-check fields, zero risk size, no broker route boundary, and blocked-reason discipline.
- `scripts/check_risk_agent_policy_router.py` validates the Risk Agent policy-review store, required checks, blocked/hold/readiness statuses, zero execution authority, zero paper-order authority, zero order creation, and zero broker-write authority.
- `scripts/check_execution_policy_router.py` validates the Execution Policy review store, required kill switches, required execution checks, kill-switch holds, zero execution authority, zero staged-paper-order authority, zero paper-order creation, zero broker-write authority, and zero live-capital authority.
- `scripts/check_staged_paper_order_contract.py` validates the disabled staged paper-order review store, hypothetical-order contract, reconciliation checks, zero staged-order creation, zero paper-order submission, zero broker-write authority, and zero live-capital authority.
- `scripts/check_broker_reconciliation_contract.py` validates the read-only broker reconciliation review store, broker echo contract, idempotency/prewrite/duplicate-guard checks, zero paper-order submission, zero broker-write authority, and zero live-capital authority.
- `scripts/check_paper_submit_receipt_contract.py` validates the dry-run paper-submit receipt review store, simulated receipt contract, deterministic idempotency preview, Event Log prewrite schema, pre-trade snapshot schema, duplicate-order guard schema, receipt checks, zero broker POST calls, zero paper-order submission, zero broker-write authority, and zero live-capital authority.
- `scripts/check_cockpit_status.py` validates D5 trade-layer summary counts, observed-signal fields, candidate/blocked fields, Risk Agent policy-review fields, Execution Policy review fields, disabled staged paper-order review fields, broker reconciliation review fields, dry-run paper-submit receipt fields, zero execution/paper-order authority, no created candidate from TradingView alerts, and no broker order path.
- A local D5 render check proves the board renders 1 observed signal, 1 candidate, 1 blocked trade, and lifecycle states as `not connected yet`.
- A local D5 render check proves the board also renders Risk Agent policy-review cards from the public-safe snapshot.
- A local D5 render check proves the board also renders Execution Policy / kill-switch cards from the public-safe snapshot.
- A local D5 render check proves the board also renders disabled staged paper-order review cards from the public-safe snapshot.
- A local D5 render check proves the board also renders read-only broker reconciliation cards from the public-safe snapshot.
- A local D5 render check proves the board also renders dry-run paper-submit receipt cards from the public-safe snapshot.
- No broker order path exists yet.

### Phase D6 - Paper Account Mirror

Objective: show money and positions.

Status: implemented and contract-checked locally as a read-only account mirror for the £1,000 trial allocation and the connected Alpaca paper account.

Build:

- `orchestrator/paper_account.py` defines the paper account snapshot, open-position snapshot, order snapshot, closed-trade snapshot, and maturity tracker contracts.
- `scripts/check_paper_account.py` initializes and validates the D6 mirror.
- `scripts/check_alpaca_paper_mirror.py --live` refreshes the Alpaca paper account through GET-only endpoints for account, positions, orders, and portfolio history.
- `orchestrator/cockpit_status.py` exports D6 account state into `capital` and joins open/closed/postmortem records into `trade_layer`.
- `landing-page-repo/dashboard.js` renders the money panel from `capital`, including balance, realized/unrealized P&L, drawdown, read-only mirror status, open positions, mirrored paper orders, closed trades, postmortems due, and equity timeline.
- `landing-page-repo/auth.css` makes the paper account mirror mobile-readable.
- The Money panel now exposes account scope, broker mirror state, connection status, observed time, timeline status, cash, equity, peak equity, max drawdown, postmortem counts, and the no-broker/no-live-capital boundary.
- `scripts/check_paper_account.py` validates D6 snapshot fields, local-mirror or Alpaca-read-only connection state, no live capital, no write authority, order authority disabled, 100-trade maturity target, count agreement, and no broker-write boundary.
- `scripts/check_cockpit_status.py` validates the public `capital` contract, equity curve fields, paper position/order/closed trade schemas, count agreement, local-mirror or Alpaca-read-only connection state, and zero-authority controls.
- `scripts/check_dashboard_money_panel.js` verifies the rendered Money panel shows the read-only mirror, account scope, broker/connection state, cash/equity/P&L/drawdown, maturity progress, open/closed trade empty states, equity timeline, and empty-equity fallback.

Current D6 state:

- Starting balance: £1,000.
- Current balance: mirrors the Alpaca paper account when the live read-only sync has run; the Qadam trial allocation remains £1,000 by policy.
- Realized P&L: £0.
- Unrealized P&L: £0.
- Drawdown: 0%.
- Open positions: 0.
- Closed trades: 0.
- Maturity progress: 0/100 closed proof trades.
- Broker connection: Alpaca paper mirror can be connected read-only; it still has no broker-write path.
- Authority: read-only, no write path, no live capital.

Exit gate:

- Dashboard shows starting balance, current balance, P&L, drawdown, open positions, and closed trades from read-only data.
- Dashboard shows mirrored paper orders when Alpaca returns them, without treating them as Qadam-created orders.
- `scripts/check_paper_account.py` passes.
- `scripts/check_alpaca_paper_mirror.py --live` passes when Alpaca credentials and network are available.
- `scripts/check_cockpit_status.py` validates `mirror_status=ok`, `write_authority=false`, `live_capital_enabled=false`, and 100-trade maturity target.
- A local D6 render check proves the panel renders the £1,000 paper mirror, zero P&L, zero drawdown, zero open/closed trades, 0/100 maturity progress, one equity snapshot, and the no-broker/no-live-capital boundary.
- The dashboard does not invent P&L, open positions, closed trades, or postmortems.

### Phase D7 - TradingView Alert Source

Objective: ingest TradingView alerts safely.

Status: implemented and contract-checked locally as an intake contract; the public webhook receiver remains later work.

Implemented now:

- `orchestrator/tradingview_alerts.py` defines the TradingView alert schema.
- `scripts/check_tradingview_alerts.py` validates sample alert intake, duplicate protection, receiver-key fail-closed behavior, and zero execution authority.
- Alert records are written to `tradingview_alerts.jsonl` as observed signals only.
- Safe Event Log entries are emitted for observed alerts.
- `orchestrator/cockpit_status.py` exports TradingView alert state into `tradingview_alerts`, appends a TradingView row to `watching`, and joins observed alerts into `trade_layer.watching`.
- `landing-page-repo/dashboard.js` renders TradingView alerts as observed signals in the Trade Layer.
- The Trade Layer now exposes the TradingView receiver state, duplicate-protection mode, alert count, latest observed time, zero execution count, zero paper-order count, zero candidate-created count, and observed-signal-only boundary.
- `scripts/check_tradingview_alerts.py` validates persisted alert fields, SHA-256 dedupe key shape, duplicate count stability, receiver-key fail-closed behavior, no persisted receiver key/raw payload fields, indicator state, and zero authority.
- `scripts/check_cockpit_status.py` validates the public `tradingview_alerts` summary, receiver status, dedupe mode, alert count agreement, observed-signal fields, zero authority, and no candidate creation.
- `scripts/check_dashboard_tradingview_source.js` verifies the Watching row, Trade Layer alert-source summary, observed TradingView alert card, observation-only labels, no-candidate/no-order boundary, and receiver-pending empty state.

Deferred until secure bridge:

- Public authenticated webhook endpoint.
- Real TradingView webhook URL.
- Signed payload or shared receiver key configured through local secrets.
- Network-facing replay tests.

Exit gate:

- TradingView alert appears as an observed signal only.
- Alert cannot create an order.
- Alert cannot create a trade candidate.
- Duplicate alert is ignored by dedupe key.
- Receiver authentication fails closed in the local contract.
- A local D7 render check proves the dashboard shows TradingView as a market source and Trade Layer observed signal, with receiver `local_contract_only`, duplicate protection `dedupe_key_sha256`, and zero execution/paper-order/candidate authority.

### Phase D8 - Fund Manager Forum

Objective: make comments operational.

Build:

- Supabase-backed comments.
- Module/signal/trade/postmortem references.
- Author identity.
- Status: suggestion, accepted, rejected, implemented.
- Export to local Event Log if approved.

Exit gate:

- Founding manager can comment on a module, source, trade candidate, or postmortem.

D8 implementation status:

- The dashboard comments panel now has an operational Fund Manager forum form with reference type, reference key, comment body, and `suggestion` / `accepted` / `rejected` / `implemented` status controls.
- The browser client writes to Supabase table `fund_manager_comments` after the existing Supabase session and allowlist checks pass.
- The public cockpit status exposes only a safe local governance mirror: counts, allowed target types, allowed statuses, redacted recent comments, and the boundary that comments cannot approve trades or place orders.
- Accepted or implemented local governance comments export an approval marker to the local Event Log without broker authority.
- `scripts/check_governance_forum.py` and `scripts/check_dashboard_forum.js` validate the D8 local store, Event Log export boundary, dashboard render, Supabase client wiring, and migration contract.

### Phase D8A - Telegram Bot Communications

Objective: connect Qadam to founding members through a supervised Telegram bot and make the communications rail visible in the dashboard.

This is not a trading interface. Telegram is outbound-only in the first release.

Build:

- Add `communications.telegram` to the cockpit status contract.
- Add a local Telegram member registry for verified/pending founding members.
- Add a local Telegram outbox for queued, sent, failed, retried, and suppressed messages.
- Add dry-run message templates for trade lifecycle events, insight digests, system warnings, and postmortem reminders.
- Add a Telegram Bot node to the system map with `notify_only` authority.
- Add a dashboard Communications panel showing bot status, mode, verified/pending members, pending queue count, failed count, suppressed count, last sent time, and last failure reason.
- Add sanitizer checks so bot tokens, chat IDs, handles, and raw Telegram payloads never enter the public status snapshot.
- Add `scripts/check_telegram_config.py` and `scripts/check_telegram_outbox.py` once implementation starts.

Message classes:

- `observed_signal`
- `trade_candidate`
- `blocked_trade`
- `staged_paper_order`
- `submitted_paper_order`
- `open_position`
- `closed_trade`
- `postmortem_due`
- `postmortem_complete`
- `insight_digest`
- `source_degraded`
- `model_degraded`
- `kill_switch`
- `dashboard_snapshot_stale`

Dashboard wording rules:

- Telegram can say Qadam observed, considered, blocked, staged, submitted, opened, closed, or reviewed something only when the backend state says so.
- Telegram cannot say Qadam is "about to trade" unless the trade state is `staged_paper_order` or `submitted_paper_order`.
- Telegram cannot expose raw model text. Messages must be rendered from structured status/Event Log fields.
- Telegram cannot expose the private world-model as proof. It can say which worldview lens shaped the question as a private prior.

Exit gate:

- Dashboard shows Telegram as disabled or dry-run from the status contract.
- Dry-run messages are generated for at least one candidate, one blocked trade, one insight digest, and one system warning.
- No token, chat ID, handle, raw local path, or raw payload appears in `cockpit-status.json`.
- No Telegram input can place, approve, reject, modify, close, or resize a trade.
- One real test message can be sent later only after BotFather token and chat ID are stored locally.

D8A implementation status:

- `orchestrator/telegram_comms.py` defines the local member registry, dry-run outbox, safe template renderer, and public-safe Telegram status summary.
- The cockpit status contract now includes `communications.telegram` with dry-run mode, disabled send gate, member counts, queue counts, last delivery fields, active message classes, and redacted recent-message metadata only.
- The dashboard System Map includes a `Telegram Bot` node with `notify_only` authority.
- The dashboard includes a Communications panel showing Telegram status, dry-run/live mode, verified/pending members, queue/failure/suppression counts, message classes, recent outbox metadata, and the outbound-only boundary.
- `scripts/check_telegram_config.py`, `scripts/check_telegram_outbox.py`, and `scripts/check_dashboard_communications.js` validate local config safety, dry-run sample generation, public redaction, and dashboard rendering.

### Phase D8B - Protected User Guide

Objective: make Qadam understandable from inside the cockpit.

Status: implemented locally as a protected static guide route.

Build:

- Add `docs/qadam-user-guide.md` as the source guide.
- Add `landing-page-repo/guide/index.html` as the dashboard-accessible guide page.
- Protect `/guide/` with the same Supabase allowlist check used by `/dashboard/`.
- Add a `User Guide` link in the dashboard navigation.
- Cover system roles, dashboard panels, status labels, trade states, member permissions, daily operating routine, worldview boundary, Telegram boundary, and red flags.

Exit gate:

- Authenticated founding members can open `/guide/` from the dashboard.
- Unauthenticated users are redirected to `/login/?next=/guide/` by the existing static auth flow.
- Guide copy does not expose secrets, local file paths, chat IDs, or broker authority.
- The guide distinguishes observation, worldview prior, hypothesis, trade intent, and execution state.

D8B implementation status:

- `docs/qadam-user-guide.md` is the source guide and now matches the D8/D8A cockpit vocabulary for Communications, dry-run Telegram, notify-only status, trade states, member permissions, and red flags.
- `landing-page-repo/guide/index.html` is protected by the same Supabase allowlist flow as `/dashboard/`, links back to the dashboard, and shows the signed-in member email.
- The dashboard navigation links to `/guide/`.
- `scripts/check_protected_user_guide.js` validates route protection wiring, guide/dashboard linkage, required guide vocabulary, safety boundaries, and obvious HTML regressions.

### Phase D9 - Secure Live Bridge

Objective: replace static snapshots with a controlled read-only live status bridge.

Build:

- Local signed status publisher.
- Read-only remote status endpoint.
- Rate limits.
- Health checks.
- Snapshot fallback.
- No broker-write route.

Exit gate:

- Dashboard updates without manual deploy.
- Browser still cannot trigger trading.

D9 implementation status:

- `orchestrator/live_bridge.py` defines the D9 bridge contract, allowed methods, forbidden write methods, cache/fallback policy, rate-limit metadata, and detached status signature manifest.
- `orchestrator/cockpit_status.py` exports `live_bridge` into the public-safe snapshot and writes `cockpit-status.signature.json` beside both runtime and landing snapshots.
- `cockpit/app/api/cockpit-status/route.ts` exposes a read-only authenticated status endpoint for founding Fund Managers, accepts Supabase bearer or cockpit cookie auth, rate-limits requests, serves only the sanitized snapshot, and blocks `POST`, `PUT`, `PATCH`, and `DELETE`.
- `landing-page-repo/dashboard.js` tries `/api/cockpit-status` first and falls back to `/status/cockpit-status.json` if the live bridge is unavailable.
- The System Map now includes the Secure Live Bridge as a read-only node.
- `scripts/check_live_bridge.py` validates bridge contract, signature output, API route safety markers, dashboard source order, and env placeholders.

Non-negotiable D9 boundaries:

- The bridge can return only the public-safe cockpit status snapshot.
- The bridge cannot expose the local MacBook orchestrator, shell, raw local paths, secrets, raw payloads, or broker credentials.
- The bridge cannot create, approve, modify, resize, close, or submit a trade.
- If the live bridge fails, the dashboard must fall back to the static snapshot or fail closed.

## 10. Current Dashboard Sprint

D0 through D9 are now implemented locally.

Implemented deliverables:

- Modular dashboard build track added so each panel can be implemented and accepted independently.
- Section hoverover contract added; every first-release panel must include a hover/focus explainer.
- Static cockpit panel headings now include first-pass information hoverovers for status/safety, System Map, Watching, Cognition, Forbidden, Trade Layer, Money, Process Console, Private Edge, and Fund Manager Comments.
- Cockpit status JSON schema.
- Snapshot exporter.
- Sanitized status file copied into the live site folder.
- Dashboard fetch/render script.
- Watching View with 35 registered sources grouped under 5 pipeline groups plus the D7 TradingView observed-alert source.
- Cognition View with current focus, model activity, shadow packets, hypotheses, evidence packets, missing corroboration, analysis timeline, and blocked reasons.
- Trade Intent Board with a local candidate record and a blocked trade record from `trade_candidates.jsonl`.
- Paper Account Mirror with £1,000 starting/current balance, zero P&L, zero drawdown, empty open/closed trade lists, postmortem counts, and 0/100 maturity progress from `paper_account_snapshots.jsonl`.
- TradingView Alert Source with one local observed chart-signal fixture, duplicate protection, Event Log write, and no candidate/order authority.
- Worldview Lens with 5 private claim cards from `how-the-world-works/`, rendered in the system map, Private Edge panel, hypothesis cards, and each observed-signal/trade decision card.
- Fund Manager Forum with private governance comments, local mirror export, and accepted/implemented Event Log markers without broker authority.
- Telegram Bot Communications rail in dry-run notify-only mode.
- Protected User Guide aligned with the cockpit vocabulary and Supabase allowlist flow.
- Secure Live Bridge contract with an authenticated read-only status endpoint, detached signature output, rate-limit boundary, write-method blocks, and static snapshot fallback.
- Real answers for:
  - what Qadam is watching,
  - module status,
  - next process state,
  - what Qadam is thinking about,
  - which private worldview lens is shaping the decision context,
  - why cognition is blocked from execution,
  - which TradingView observed alerts exist,
  - which local trade intents are candidates or blocked,
  - how the paper account mirror currently stands,
  - forbidden actions,
  - empty but real staged/order/position/postmortem states.

Still not included yet:

- Actual LLM reasoning.
- Production signal-derived trade candidates.
- Actual broker integration.
- Public TradingView webhook ingestion.
- Real broker-derived P&L and positions.

Those come after the dashboard can render real state without lying.

### Phase D10A - Scrollable Cockpit Page Architecture

Objective: remove the fixed-height cockpit shell so the dashboard can be read as a normal operating page.

Status: implemented locally.

Implemented now:

- The desktop dashboard no longer locks `body`, `.dashboard-shell`, or `.dashboard-workspace` to one viewport.
- The dashboard shell uses `min-height` and page-flow content instead of `height: 100dvh` plus clipped overflow.
- Panel bodies expand into the page by default instead of creating nested scroll traps.
- The system map, fund-model strip, and live dashboard grid can grow vertically, so section content is not forced into tiny card interiors.
- `scripts/check_dashboard_page_architecture.js` prevents the old fixed-height / nested-scroll pattern from returning.

Exit gate:

- Browser-level vertical scroll is available on desktop.
- Dashboard panels do not all create independent scrollbars.
- The existing renderer and status-contract checks still pass.

### Phase D10B - Dashboard Information Hierarchy

Objective: make the cockpit read in the order a founding Fund Manager should review it.

Status: implemented locally and extended with the Mission Control top surface.

Implemented now:

- Added a Mission Control band above the system map with connected/logged-in data sources, durable replay readiness, trading philosophy, API/model/quant stack, current thinking, trade intent, paper holdings, P&L, and hard safety boundaries.
- The Mission Control surface renders from the sanitized cockpit status snapshot through `mission_control` plus `renderMissionControl(status, source)`.
- The status contract now includes `durable_ingestion` and the Mission Control `durable_spine` summary so the top panel shows whether Postgres/Timescale replay is offline, partial, or complete, without granting source observations any signal, order, broker-write, or live-capital authority.
- The older operating summary cards remain beneath Mission Control as compact paper account, source quality, cognition, trade layer, safety, and bridge summaries via `renderOperatingSummary(status, source)`.
- The dashboard now introduces the detailed sections with an explicit review sequence: sources, cognition, trade state, money, safety, governance, runtime.
- The detailed panel layout prioritizes Watching and Cognition first, then Trade Layer and Money, then Safety, Worldview, Communications, Comments, and Runtime.
- Runtime events are visually last instead of competing with the operating panels.
- `scripts/check_dashboard_information_hierarchy.js` prevents the page from regressing into an undifferentiated card grid.

Exit gate:

- A Fund Manager can see connected sources, the current trading philosophy, the system stack, what Qadam is thinking about, what trades it is considering or blocking, what positions/orders it holds, P&L, live-capital state, and bridge source before reading any detailed table.
- The detailed panels follow Qadam's operating sequence.
- The existing dashboard renderer and status-contract checks still pass.

### Phase D10C - Real System Map

Objective: turn the top system map into a connected operating diagram instead of a horizontally scrolling node strip.

Status: implemented locally.

Implemented now:

- The static dashboard fallback now uses a lane-based system map with `Observation`, `COO Memory`, `Research`, `Quant + Risk`, `Paper Trial`, and `Members`.
- The dynamic renderer now builds the same lane-based map from the sanitized status contract.
- Each map node keeps status, role, current process, input, output, and authority.
- Handoff labels now explain what moves between nodes, for example observed facts, logged state, shadow analysis, bounded oracle check, risk decision, paper state, and learning feedback.
- The map includes side-channel governance and communications without implying execution authority.
- The map ends with a closed-loop rule: observations, hypotheses, risk decisions, paper states, comments, and postmortems return to the Event Log before they change Qadam.
- `scripts/check_dashboard_system_map.js` prevents the map from regressing into the old horizontal strip.

Exit gate:

- A Fund Manager can understand the operating flow from source observation to paper outcome and postmortem.
- Status labels visually belong to specific nodes and lanes.
- The map distinguishes observation, research, gating, paper trading, learning, and member communications.
- The map remains read-only and adds no broker-write authority.

### Phase D10D - Visual System Upgrade

Objective: make the cockpit feel like a premium operating surface without weakening Qadam's read-only dashboard boundaries.

Status: implemented locally.

Implemented now:

- Replaced the old green-black surface with an obsidian visual foundation and reusable design tokens for panels, lines, text, status colors, shadows, and glows.
- Added a dual typography system: system sans for navigation and explanatory text, monospaced tabular typography for statuses, metrics, timestamps, node facts, and execution-style labels.
- Upgraded panels, explainers, and hover cards with frosted-glass layering, stronger depth, and clearer focus states.
- Added semantic status glows for online, pending/degraded, dry-run, and blocked states across map nodes, priority cards, inline badges, lanes, and trade intent cards.
- Refined the real system map, Mission Control cards, summary metrics, source rows, cognition cards, trade cards, and progress bars so the visual hierarchy matches Qadam's fund-team model.
- Added tactile hover/focus transitions with a reduced-motion guard.
- Bumped the dashboard stylesheet cache key to `20260517-d10d-visual` so the cockpit does not silently keep serving the old D9 CSS after deployment.
- Added `scripts/check_dashboard_visual_system.js` to prevent regressions to the old palette, Arial typography, decorative radial backgrounds, or flat status styling.

Exit gate:

- The page uses a true dark foundation rather than pure black or the old `#071012` surface.
- Status color and glow communicate system meaning without depending on disconnected pills.
- Numeric and operational fields are visually distinct from explanatory prose.
- Hover explainers read as layered utility surfaces rather than ordinary cards.
- The visual system adds no broker-write authority and changes no dashboard data contract.

### Phase D10E - Section Explainers

Objective: make every dashboard section self-explanatory without forcing the user to leave the cockpit for the User Guide.

Status: implemented locally.

Implemented now:

- Upgraded the first-pass hoverovers into structured operator explainers with `Use it to`, `Watch for`, and `Boundary` rows.
- Added an explainer to the Operating Detail divider so the review sequence itself is clear.
- Aligned the explainer vocabulary with the protected User Guide: observations, hypotheses, candidates, paper states, worldview priors, hard blocks, notify-only Telegram, and read-only bridge boundaries.
- Made execution authority explicit in every risky section: sources cannot create orders, hypotheses are not trades, candidates are not orders, Telegram is notify-only, comments are governance only, and the process console is not shell access.
- Expanded explainer styling so hover cards can hold structured guidance without becoming unreadable.
- Bumped the dashboard stylesheet cache key to `20260517-d10e-explainers`.
- Added `scripts/check_dashboard_section_explainers.js` to enforce required section explainers and authority-boundary copy.

Exit gate:

- Every major cockpit section has a hover/focus explainer.
- Each explainer answers what the section is for, what the Fund Manager should watch, and what the section cannot do.
- The explainers include no secrets, local paths, raw payloads, chat IDs, broker credentials, or raw model text.
- The existing dashboard renderer, visual-system, page-architecture, and status-contract checks still pass.

### Phase D10F - Panel-Level Redesign

Objective: make each operating panel readable at a glance before the user digs into metrics, rows, and detailed cards.

Status: implemented locally.

Implemented now:

- Added a reusable `panel-brief` pattern to the static dashboard fallback and live renderer.
- Each major panel now starts with a compact operating readout: the question it answers, current state, what to watch, and authority boundary.
- Live-rendered panels for Cognition, Private Edge, Telegram, Trade Layer, and Money now include dynamic panel briefs generated from the sanitized status snapshot.
- Panels whose list content is updated in place, such as Watching, Forbidden, Process Console, and Fund Manager Comments, keep static briefs and receive live state updates through `replacePanelBrief`.
- The Trade Layer now opens with a panel-level ladder readout before metrics, TradingView source, candidates, blocked trades, and paper lifecycle sections.
- The Money panel now opens with account-trust context before balance/P&L metrics and paper maturity detail.
- The Process Console now clearly reads as a read-only event stream before showing runtime events.
- Added panel-level CSS for brief cards, facts, responsive layout, and semantic online/pending/blocked panel tones.
- Bumped the dashboard CSS and JS cache keys to `20260517-d10f-panels`.
- Added `scripts/check_dashboard_panel_redesign.js` to enforce panel briefs in the static HTML, renderer, CSS, and live-rendered panels.

Exit gate:

- A user can read the first block inside each panel and understand what question the panel answers.
- Panel bodies no longer begin with unexplained metrics or raw list rows.
- Every panel-level redesign preserves the same sanitized status contract and does not add command, broker-write, shell, or live-capital authority.
- The existing section-explainer, visual-system, renderer, and bridge checks still pass.

### Phase D10G - Executive / Terminal Density Toggle

Objective: let a founding Fund Manager switch the cockpit between a readable operating overview and a denser monitoring surface without changing Qadam's data or authority model.

Status: implemented locally.

Implemented now:

- Added an Executive / Terminal segmented control to the operating-mode cluster.
- The dashboard defaults to Executive density for plain-English review and stores the user's chosen density in `localStorage`.
- The document root now carries `data-dashboard-density`, giving CSS and future renderers a stable density hook.
- Executive mode keeps the D10F panel-first layout with fuller panel briefs and breathable spacing.
- Terminal mode compresses the cockpit shell, panel padding, panel briefs, metrics, cards, source rows, trade route, tag rows, and system-map lanes for higher-density monitoring.
- Terminal mode hides secondary panel-brief prose while preserving the state, watchpoint, and boundary facts.
- Bumped dashboard CSS and JS cache keys to `20260521-mission-control`.
- Added `scripts/check_dashboard_density_toggle.js` to enforce the toggle UI, persisted renderer hook, terminal CSS selectors, cache keys, and default Executive state.
- Added `scripts/check_dashboard_mission_control.js` to enforce the Mission Control status contract and rendered top-panel output.
- Added `scripts/check_dashboard_durable_spine.js` to enforce the public-safe durable replay status and Mission Control rendering.

Exit gate:

- The density switch is visible in the cockpit header.
- Executive mode remains the default and prioritizes comprehension.
- Terminal mode increases scan density without removing authority boundaries or changing snapshot data.
- The existing panel redesign, section explainer, visual-system, renderer, and bridge checks still pass.

### Phase D10H - Testing And Acceptance

Objective: make the D10 dashboard overhaul testable as one cockpit acceptance gate, not only as isolated phase checks.

Status: implemented locally.

Implemented now:

- Added a consolidated D10H acceptance script at `scripts/check_dashboard_acceptance.js`.
- The acceptance gate verifies that all D10A-D10G phase checks still exist and that this implementation plan records each phase.
- The gate checks the static dashboard for the scrollable detail architecture, morning review, real system map, section explainers, panel briefs, Executive / Terminal density toggle, visual-system hooks, cache keys, and public read-only authority copy.
- The gate checks the live renderer contract against the sanitized cockpit status snapshot, including the operating summary, fund model, system map, watching state, cognition, private edge, communications, trade layer, money, comments, and runtime panels.
- The gate verifies that the dashboard still defaults to Executive density, prefers the authenticated read-only bridge, and marks the snapshot as rendered.
- The gate includes a public-text safety check for local paths, raw tokens, and common secret variable names.
- D10H intentionally keeps the Python bridge checks as separate sequential checks because those exporters write bridge/status artifacts and should not be mixed into a browser-only renderer assertion.

Exit gate:

- `scripts/check_dashboard_acceptance.js` passes locally.
- The phase-specific dashboard checks still pass after the consolidated gate.
- `scripts/check_cockpit_status.py` and `scripts/check_live_bridge.py` pass sequentially after the JavaScript dashboard checks.
- `git diff --check` passes for the dashboard, plan, and D10 test files.
- No test implies broker-write authority, shell authority, command execution, live-capital access, or trade approval from the dashboard.

### Phase D10I - Deployment Discipline

Objective: make dashboard production deployment explicit, preflighted, and auditable so Qadam is not described as live unless Vercel actually returns and aliases a production deployment.

Status: implemented locally; production deployment still requires networked Vercel access and a local `VERCEL_TOKEN`.

Implemented now:

- Added a local deployment preflight at `scripts/preflight_dashboard_deployment.sh`.
- Added `scripts/check_dashboard_deployment_readiness.js` to verify the production deploy target, required static dashboard files, protected guide, status snapshot, `.vercelignore`, Vercel project link, deploy-script guardrails, deployment receipt behavior, and secret hygiene.
- The production deploy script at `landing-page-repo/scripts/deploy-vercel-production.sh` now runs the local deployment preflight before it attempts Vercel production deployment.
- The preflight runs the D10H acceptance gate, D10I deployment-readiness gate, phase-specific dashboard checks, protected guide check, status exporter checks, renderer syntax check, and whitespace check.
- The deploy script still requires a local `VERCEL_TOKEN`; it does not read, print, or commit the token.
- A production deploy can bypass preflight only by explicitly setting `QADAM_SKIP_DEPLOY_PREFLIGHT=1`, which is recorded in the deployment receipt.
- On successful Vercel deployment and aliasing, the script writes `data/runtime/dashboard-deployment-receipt.json` with the Vercel deployment URL, aliases, timestamp, and preflight status.
- The receipt is local runtime state only and must not contain Vercel tokens, session cookies, broker credentials, dashboard secrets, or model/API keys.

Exit gate:

- `scripts/preflight_dashboard_deployment.sh` passes locally.
- `scripts/check_dashboard_deployment_readiness.js` passes locally.
- Production deployment is attempted only through `landing-page-repo/scripts/deploy-vercel-production.sh`, not ad hoc terminal commands.
- A live claim is valid only when the deploy script prints a production deployment URL and aliases `qadam.trade` and `www.qadam.trade`.
- If Vercel cannot be reached from the execution environment, the correct result is “locally deployment-ready, not deployed.”

## 11. Acceptance Criteria

The dashboard is acceptable when a founding Fund Manager can answer:

- What is Qadam watching right now?
- What data is degraded or missing?
- Which modules are alive?
- Which modules are blocked?
- What is Qadam thinking about?
- Why is execution blocked?
- What trade candidates exist?
- Which trades were blocked?
- What positions are open?
- How much has the £1,000 paper account gained or lost?
- Which trades need postmortem?
- What Qadam has communicated to members, and whether any messages failed or were suppressed?

Each answer must be discoverable in two ways: from the panel itself, and from that panel's information hoverover.

If any of those answers are hardcoded, the dashboard is still a demo shell. If they come from a sanitized Qadam status contract, the dashboard is becoming operational.
