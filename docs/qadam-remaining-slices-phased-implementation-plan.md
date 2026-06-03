# Qadam Remaining Slices Phased Implementation Plan

This plan turns the remaining Qadam slices into an implementation sequence.
Its goal is simple: Qadam should be free to use its full paper-trading
capability while preserving the hard first-release boundary that live capital
is off.

This document extends the master plan. It does not replace
`docs/qadam-master-implementation-plan.md`.

## 1. Definition Of Full Paper Potential

Qadam is fulfilling its first-release potential when it can:

- watch live and replayed sources on the configured cadence;
- create Research Goals from real observations;
- compress evidence through the Local Research Analyst;
- challenge theses through the Strategy Lead;
- use the Head of Quant as a shadow ambiguity/pattern annotation only;
- pass qualified setups through Signal Integrity, Risk, Execution Policy,
  kill-switch, idempotency, broker-readiness, and Event Log gates;
- submit multiple Alpaca paper trades per day when distinct qualified setups
  exist and risk limits allow them;
- poll, reconcile, close, and postmortem those paper trades;
- show Fund Managers what happened, what is blocked, and why;
- keep all canonical saved state local unless a later cloud-sync decision is
  explicitly approved.

Full paper potential does not mean unlimited trading. It means no stale,
contradictory, or accidental blocker prevents a valid paper-only setup from
moving through the guarded path.

## 2. Paper Authority Contract

Qadam may submit guarded paper trades only when all of these are true:

- `live_capital_enabled=false`;
- account mode is paper/test only;
- Alpaca paper credentials and endpoint are configured;
- a distinct qualified setup exists;
- source quorum and market-confirmation rules pass;
- Signal Integrity passes or explicitly routes to a paper-eligible state;
- Risk Agent produces a paper-size decision inside limits;
- Execution Policy and kill switches allow the attempt;
- Event Log prewrite and pre-trade snapshot exist;
- idempotency key exists and is unique for the paper order intent;
- duplicate-order guard passes;
- paper-submit path is active;
- active PaperOps automation or the explicitly invoked guarded runner is active;
- broker response is reconciled after submit;
- dashboard, Telegram, LLMs, quantum output, and Fund Manager comments do not
  create direct order authority.

Qadam must not:

- trade live capital;
- let a dashboard button place an order;
- let Telegram commands place, modify, resize, close, approve, or reject a
  trade;
- let a Local LLM, Frontier LLM, or quantum oracle approve risk or originate an
  order;
- count old Phase 5 test artifacts as proof-trial trades;
- force a trade when no qualified setup exists;
- treat a daily target as a ceiling when additional qualified setups exist and
  risk budget remains.

Order-creating POST retry rule:

- live-capital POST retries remain disallowed;
- Alpaca paper-submit retries are allowed only for the guarded paper route,
  only on timeout, HTTP 429, or HTTP 5xx, only with the same idempotency key,
  and only within the configured max-attempt contract;
- a retry must never create a new order intent.

## 3. Rate-Limit And 429 Operating Rule

The `429 Too Many Requests` condition is not a trading thesis blocker. It is an
operational throttle.

For Codex, Vercel, model, Telegram, or provider API rate limits:

- stop repeated immediate retries;
- prefer local checks over redeploying or re-calling remote APIs;
- preserve the last valid local status;
- record the provider as degraded/rate-limited when it affects source data;
- retry only after the provider backoff window or `Retry-After` value;
- batch validations so deploys and live probes happen once per slice;
- never let a 429 on a non-critical source block a valid paper trade if source
  quorum, market confirmation, and risk gates are otherwise satisfied;
- never let a 429 on a paper-order POST create a second order intent.

## 4. Phase RS-0 - Authority Reconciliation And Blocker Hygiene

Objective: remove stale contradictions and classify remaining blockers by type.

Build:

- Add a single paper-authority summary contract:
  - allowed paper actions;
  - forbidden live-capital actions;
  - current blocker list;
  - stale/historical blocker list;
  - external blocker list;
  - opportunity/risk blocker list.
- Treat `automation_not_active` / `scheduler_inactive` as an operational
  blocker to surface and fix, not as a reason to weaken paper gates.
- Update master-plan language so paper orders are not globally described as
  disabled after PaperOps gates exist.
- Reconcile retry language so paper-submit idempotent retry policy is allowed,
  while live-capital retry remains forbidden.
- Make the dashboard distinguish:
  - `ready_idle_daily_target_met`;
  - `ready_waiting_for_qualified_setup`;
  - `blocked_by_risk`;
  - `blocked_by_source_quorum`;
  - `blocked_by_external_rate_limit`;
  - `blocked_by_safety`;
  - `stale_historical_blocker`.

Likely files:

- `orchestrator/cockpit_status.py`
- `orchestrator/paperops_active_paper_trading_automation.py`
- `scripts/check_paper_authority_reconciliation.py`
- `scripts/check_cockpit_status.py`
- `landing-page-repo/dashboard.js`
- `docs/qadam-master-implementation-plan.md`

Acceptance:

- The current status can say Qadam is paper-authorized without implying live
  capital is authorized.
- Stale historical Phase 5/Phase 7 blockers do not appear as current blockers.
- The dashboard can explain why Qadam did or did not trade today.
- PaperOps validation remains green with `live_capital_enabled=false`.

## 5. Phase RS-1 - Role Contracts And Execution Separation

Objective: make each Qadam role's authority explicit and testable.

Build:

- Add or extend role contracts for:
  - COO / Python Orchestrator;
  - Research Analyst / Local LLM;
  - Strategy Lead / Frontier LLM;
  - Head of Quant / quantum oracle;
  - Signal Auditor;
  - Risk Agent;
  - Execution Auditor;
  - Fund Manager Interface.
- Add explicit handoff rules:
  - observation to Research Goal;
  - Research Goal to hypothesis;
  - hypothesis to trade candidate;
  - candidate to risk;
  - risk to staged paper order;
  - staged paper order to paper submit;
  - submitted paper order to lifecycle and postmortem.

Acceptance:

- No role has hidden broker-write authority.
- No LLM role can approve risk.
- No quantum role can originate a trade.
- COO can run guarded paper operations only through explicit paper-only gates.

## 6. Phase RS-2 - Research Goal Lifecycle Hardening

Objective: make Research Goals the required bridge from watching to trading.

Build:

- Add scoring fields:
  - source quorum score;
  - market confirmation score;
  - worldview relevance score;
  - Akber-stage score;
  - contradiction score;
  - latency/freshness score;
  - risk-readiness score.
- Add aging and expiry:
  - stale goals expire or move to `closed_no_trade`;
  - repeated contradictory evidence lowers priority;
  - fresh corroboration raises priority.
- Require every trade candidate to reference a Research Goal.

Acceptance:

- No candidate can exist without `goal_id`.
- A goal can become `candidate_ready` only through evidence and scoring.
- A goal can close as `no_trade` without being treated as failure.

## 7. Phase RS-3 - Market Context Packet And Source Quality

Objective: give every trading decision a consistent market/evidence context.

Build:

- Add `market_context_packet` with:
  - source observations;
  - source taxonomy;
  - trust scores;
  - latency/freshness;
  - price/volume context;
  - Yahoo Finance supplemental context;
  - TradingView technical-analysis context when available;
  - Alpaca paper account context;
  - contradictory evidence;
  - source quorum result.
- Use Yahoo Finance only as supplemental market confirmation, never as broker
  truth or fill/reconciliation truth.
- Keep ACLED, UnusualWhales, Kalshi, and other credential-gated sources visible
  as degraded/missing/deferred until their external blockers are resolved.

Acceptance:

- At least 20 configured sources have live/degraded/missing status with reason.
- At least two physical/logistics sources pass live trust/latency thresholds
  when credentials and network allow.
- Source 429s degrade the affected source without blocking the whole system
  unless source quorum fails.

## 8. Phase RS-4 - Intelligence Cycle Activation

Objective: make the Local Research Analyst and Strategy Lead useful every cycle.

Build:

- Run the Local Research Analyst over Research Goals and market context.
- Run the Strategy Lead over higher-priority or contradictory packets.
- Preserve structured outputs:
  - thesis;
  - evidence;
  - missing evidence;
  - contradiction;
  - action class;
  - next handoff;
  - explicit non-authority flags.
- Keep Gemini/frontier model calls batched and rate-limit aware.

Acceptance:

- Local LLM status shows online when LM Studio is running.
- Strategy Lead status shows online/configured when Gemini probe is current.
- Outputs remain non-executable until Signal Integrity and Risk gates advance
  them.

## 9. Phase RS-5 - Guarded Paper Autonomy

Objective: ensure Qadam can make multiple paper trades per day when the market
actually produces qualified setups.

Build:

- Treat the daily paper-trade target as a minimum discipline target, not a hard
  ceiling.
- Keep the 20-minute opportunity scan as candidate refresh.
- Keep the guarded submit runner as the only paper-submit transport until a
  local scheduler upgrade is audited.
- Allow multiple paper submissions in a day only when each one has:
  - distinct Research Goal;
  - distinct candidate;
  - distinct idempotency key;
  - passing risk budget;
  - no duplicate exposure conflict;
  - no daily drawdown breach;
  - no source-quorum breach;
  - no live-capital route.
- Add a clear `why_not_trading_now` status when no paper submit occurs.

Acceptance:

- Qadam can submit more than one Alpaca paper trade per day if multiple
  qualified setups exist.
- Qadam idles cleanly when the daily target is met and no additional qualified
  setup exists.
- Qadam does not idle only because a minimum target was met if a later distinct
  setup passes every gate.
- `scripts/run_active_paper_trading_automation.py --execute-paper-automation`
  remains the guarded route.

## 10. Phase RS-6 - Lifecycle, Portfolio, And Postmortem Hardening

Objective: make every paper trade auditable from idea to outcome.

Build:

- Poll Alpaca paper orders and positions.
- Mirror balance, equity, buying power, open positions, orders, fills, closed
  trades, realized/unrealized P&L, and drawdown.
- Create postmortem items for closed paper trades.
- Link each postmortem back to:
  - Research Goal;
  - hypothesis;
  - candidate;
  - market context packet;
  - risk packet;
  - paper order;
  - broker receipt;
  - position/fill state.

Acceptance:

- Dashboard balance ticker is broker/account derived, not display inferred.
- Closed paper trades require postmortem records.
- Paper proof ledger uses only verified paper lifecycle records.

## 11. Phase RS-7 - Operator Inbox, Telegram, And Human Oversight

Objective: make Qadam understandable and controllable without giving humans or
chat commands unsafe direct execution power.

Build:

- Add durable inbox items for:
  - source degraded;
  - credential expiring;
  - research goal needs review;
  - strategy challenge ready;
  - signal blocked;
  - paper trade candidate ready;
  - paper order submitted;
  - position opened;
  - position closed;
  - postmortem due;
  - kill switch triggered.
- Add read-only commands:
  - `/status`;
  - `/sources`;
  - `/research-goals`;
  - `/trades`;
  - `/blocked`;
  - `/portfolio`;
  - `/worldview`;
  - `/postmortems`.
- Send Telegram notifications for allowed message classes.

Acceptance:

- Telegram can notify and summarize.
- Telegram cannot place orders.
- Fund Managers can acknowledge, comment, and request review.
- Comments cannot approve trades.

## 12. Phase RS-8 - Dashboard Mission Control Completion

Objective: make the dashboard answer the Fund Manager questions without
scrolling through debug output.

Build:

- Make Mission Control the top view:
  - sources connected;
  - current philosophy;
  - active Research Goals;
  - trade candidates;
  - blocked reasons;
  - open positions;
  - portfolio value;
  - paper-trade timeline;
  - next action.
- Make sections navigable:
  - Mission;
  - Map;
  - Sources;
  - Reasoning;
  - Trades;
  - Portfolio;
  - Safety;
  - Inbox;
  - Runtime.
- Add visible click/tap expand controls for every major card.

Acceptance:

- The dashboard can answer:
  - What is Qadam watching?
  - What is Qadam thinking?
  - What can it not do?
  - What is it considering?
  - What did it trade?
  - What is the portfolio worth?
  - Why is it blocked?

## 13. Phase RS-9 - Learning Loop And Full-Potential Review

Objective: let Qadam improve from paper outcomes without mutating strategy or
trust scores without review.

Build:

- Convert postmortems into learning proposals.
- Add proposed updates for:
  - strategy weights;
  - source trust;
  - risk sizing;
  - market-context interpretation;
  - worldview lens strength.
- Keep actual mutation behind Fund Manager approval until the learning gate is
  explicitly opened.

Acceptance:

- Qadam can recommend improvements.
- Qadam cannot silently rewrite its strategy, source trust, or risk rules.
- The system can explain whether it is improving, degrading, or uncertain.

## 14. Phase RS-10 - Final Paper Autonomy Certification

Objective: certify that Qadam is free to trade paper at full first-release
capacity.

Certification requires:

- no stale blocker shown as current;
- no live-capital route enabled;
- no dashboard or Telegram execution route;
- paper account mirror green;
- durable source/replay green or explicitly degraded with reason;
- Local Research Analyst and Strategy Lead current or explicitly degraded;
- Research Goal to candidate lineage present;
- Signal Integrity and Risk gates current;
- paper-submit route active;
- lifecycle poller active;
- postmortem route active;
- paper proof ledger current;
- rate-limit handling present;
- all public cockpit status is sanitized.

Exit state:

- Qadam can autonomously submit multiple guarded Alpaca paper trades per day
  when multiple qualified setups exist.
- Qadam can also choose not to trade and explain why.
- Qadam remains unable to trade live capital.

## 15. Recommended Implementation Order

Implement in this order:

1. RS-0 Authority Reconciliation And Blocker Hygiene.
2. RS-2 Research Goal Lifecycle Hardening.
3. RS-3 Market Context Packet And Source Quality.
4. RS-5 Guarded Paper Autonomy.
5. RS-6 Lifecycle, Portfolio, And Postmortem Hardening.
6. RS-7 Operator Inbox, Telegram, And Human Oversight.
7. RS-8 Dashboard Mission Control Completion.
8. RS-1 Role Contracts if any role boundary drift appears during the above.
9. RS-9 Learning Loop once closed paper-trade postmortems are reliable.
10. RS-10 Final Paper Autonomy Certification.

The next implementation slice should be RS-0. It is the highest-leverage slice
because it removes stale contradictions before adding more capability.
