# Qadam User Guide

This guide is for someone who has never heard of Qadam and needs to know how to
use it safely.

Qadam is a local-first macro intelligence and paper-trading system. It watches
world events and markets, builds trade hypotheses, checks them against evidence
and risk rules, runs paper trades only when the gates allow it, and logs
outcomes for review.

Qadam is not a public financial-advice product, not a signal channel, and not a
live-capital trading bot. In the current first-release workflow, live capital is
disabled and the user-facing dashboard is a read-only operating mirror.

## 1. The Short Version

Use Qadam through the dashboard at `qadam.trade`.

The dashboard shows:

- what Qadam is watching
- what Qadam is thinking about
- which data sources are healthy, degraded, missing, or blocked
- which trade ideas are observations, hypotheses, candidates, blocked trades,
  staged paper orders, submitted paper orders, open positions, closed trades, or
  postmortems
- what the paper account is doing
- what Qadam is forbidden from doing
- what Qadam learned from prior paper outcomes

Most users should read, challenge, comment, and review. They should not try to
force trades. A blocked trade usually means Qadam's controls are working.

## 2. Who Can Use Qadam

First-release access is limited to the founding Fund Managers:

- Ramin
- Troy
- Akber
- Anas
- Ion

The dashboard, guide, and settings routes are protected by Supabase login plus a
Qadam allowlist. If your email is not allowlisted, you cannot use the private
cockpit.

## 3. What Qadam Is

Think of Qadam as a small fund team running inside a laptop.

| Role | Meaning |
| --- | --- |
| Fund Managers | The humans who oversee Qadam, review evidence, challenge assumptions, and improve the process. |
| Orchestrator | The Python coordinator. It coordinates modules, checks health, writes logs, and routes work. |
| Research Analyst | The local LLM. It filters noisy information locally. |
| Strategy Lead | The frontier LLM. It builds and challenges deeper strategy packets. |
| Head of Quant | The quantum/classical modelling layer. It acts as a bounded oracle, not a real-time trading brain. |
| Signal Integrity Gate | The evidence-quality gate before trade ideas can progress. |
| Risk Agent | The control layer that blocks oversize, stale, low-evidence, or unauthorized ideas. |
| Execution Layer | The guarded paper-order and lifecycle path. Live capital stays disabled. |
| Event Log | The system memory. If it is not logged, it did not happen. |
| Knowledge Graph | The learning memory built from approved outcomes and postmortems. |
| Cockpit | The web dashboard used by humans to read Qadam. |

## 4. The Main Rule

Qadam separates five states:

| State | Meaning |
| --- | --- |
| Observation | Something happened in a feed, chart, source, or market. |
| Worldview prior | Qadam's private lens says the event may matter. This is context only, not proof. |
| Hypothesis | Qadam thinks the observation could become meaningful. |
| Trade intent | Qadam has a structured trade idea. |
| Execution state | Qadam has permission to stage, submit, hold, close, or postmortem a paper trade. |

A hypothesis is not a trade. A candidate is not an order. A blocked trade means
the control system is working.

## 5. Current Operating Mode

As of this guide update, Qadam is in 60-day paper growth operation:

- the available paper trading account is GBP 100,000
- GBP 1,000 may appear only as a separate single-order/notional risk cap
- the paper portfolio target is GBP 200,000 within 60 days
- Qadam should wait for evidence-gated probability or pricing mispricing
  opportunities, then take selective larger paper positions only when strategy,
  risk, Q-CTRL, and Alpaca Paper gates agree
- no trades are forced
- the paper-live control plane is certified, visible, and guarded
- Q-CTRL Fire Opal product access is verified for the `qadam` organization
- verified performance maturity remains separate from the 60-day target
- Fire Opal plus IBM Quantum hardware discovery is a separate explicit gate; it
  needs IBM Quantum token/instance configuration before device probing
- live capital is disabled
- broker live endpoints are disabled

The cockpit and runtime checks are the source of truth. If this guide and the
dashboard disagree, trust the latest backend-derived dashboard state and inspect
the corresponding runtime artifact or checker output.

## 5A. Dashboard Health Language

The dashboard health labels mean:

| Label | Meaning |
| --- | --- |
| OK | The system or core dependency is healthy for the current paper-trading mode. |
| OK - read-only | The path is healthy for monitoring and cannot mutate Qadam state. |
| OK - paper only | The path is healthy for paper/demo operation only. |
| OK - live capital off | Real-money trading remains disabled by design. |
| Waiting | A normal hold, usually the 30-day proof window, no open position, or missing evidence. |
| Optional | Useful if configured, but not required for the current paper-trading core. |
| Not configured | A required credential, bridge, or artifact is missing. |
| Needs attention | A required dependency is stale, degraded, partial, or lower confidence. |
| Blocked | A safety, authority, risk, or policy stop is deliberately holding the path. |

Do not try to turn every optional feed into `OK`. For the paper-trading core,
`Optional` is a healthy non-blocking state.

## 5B. IBM Quantum Device Discovery

IBM Quantum credentials are local runtime secrets. They should live in
`.env.local` or another ignored secret store, never in Git.

Before running an IBM device-discovery probe:

```bash
set -a
source .env.local
set +a
```

Then run:

```bash
.venv/bin/python scripts/check_qctrl_fire_opal_ibm_quantum.py --probe-devices
```

This explicit probe may call Fire Opal and IBM Quantum to discover available
devices. It does not submit a hardware job, enable a hardware scheduler, create
a trade idea, approve risk, approve a paper order, call a broker, or enable live
capital.

## 6. Before You Start

If you are a founding Fund Manager using the website, you need:

- an allowlisted email address
- a Supabase account created through the Qadam sign-up route
- access to `qadam.trade`
- enough context to understand that Qadam is in paper mode, not live trading mode

If you are the local operator, you also need:

- the local Qadam repository
- the Python virtual environment
- local runtime secrets stored outside Git
- OrbStack or another Docker-compatible runtime when using Postgres/Timescale
- a rule that secrets never go into chat, docs, screenshots, public logs, or Git

## 7. First Login

1. Open `https://qadam.trade/`.
2. Click `Login`.
3. Sign in with your allowlisted email.
4. If you do not have an account yet, use `/sign-up/` with your allowlisted
   email.
5. After login, open `/dashboard/`.
6. Open `/guide/` from the dashboard whenever you need the protected web version
   of this guide.
7. If login succeeds but the dashboard denies access, your Supabase account may
   exist but your email may not be on the Qadam founding-manager allowlist.

Do not paste API keys, broker secrets, Telegram tokens, or private credentials
into comments, forms, chats, docs, or prompts.

## 8. First 10-Minute Tour

Use this sequence the first time you open Qadam.

1. Start in the Overview view.
2. Read Safety Status first: it should say OK - paper only, OK - read-only,
   OK - live capital off, Dashboard cannot place orders, and AI cannot bypass risk
   checks.
3. Read the seven Stage 7 dashboard sections in order: System Operating Map,
   System Status, Data Sources Connected, Trading Strategies, Qadam Activity
   Feed, Trade Consideration Board, and Paper Portfolio Capacity.
4. Use the System Operating Map to understand the handoff from sources, to the
   local and frontier models, to the quantum/quant review, risk gate, Alpaca
   Paper, and learning loop.
5. Use the Activity Feed and Trade Consideration Board to see what Qadam is
   thinking about without exposing hidden chain-of-thought or implying an order
   exists.
6. Use Paper Portfolio Capacity to track the GBP 100,000 paper baseline against
   the GBP 200,000 60-day target.
7. Open Advanced / Debug Mode only when you need the deeper Trades, Evidence,
   Reasoning, Operations, event-trail, or technical diagnostics views.
8. Treat a blocked/no-trade state as potentially healthy until the evidence
   says otherwise.
9. Add a comment only if you have a useful observation, concern, or proposed
    improvement.

## 9. How To Read The Dashboard

Start in the Overview view. Stage 7 makes Overview the default Fund Manager
cockpit instead of a long stack of technical cards. It is organized around seven
plain-language sections: System Operating Map, System Status, Data Sources
Connected, Trading Strategies, Qadam Activity Feed, Trade Consideration Board,
and Paper Portfolio Capacity.

The deeper Trades, Evidence, Reasoning, and Operations views still exist for
technical review, but they belong behind Advanced / Debug Mode. Use Advanced /
Debug Mode only when you need legacy audit sections, raw event trails,
deployment/runtime details, or exact diagnostic evidence.

### Overview / Stage 7 Cockpit

Use it to answer:

- how the whole system is wired from source observation to paper account and
  learning loop
- whether the core system is ready to observe, reason, quantify, paper trade, or
  needs attention
- how many data sources are connected and whether any required source gap is
  still blocking paper operation
- which strategy domains Qadam is watching: prediction markets, crude oil,
  defence, silver, and semiconductors
- what Qadam is currently focused on, in public-safe summary language
- what trade ideas are observations, hypotheses, candidates, blocked, submitted,
  open, closed, or postmortem-ready
- how much of the GBP 100,000 paper capacity is deployed against the GBP 200,000
  60-day target

Overview is a readout, not a command surface. It cannot promote hypotheses,
approve trades, submit paper orders, write to brokers, or enable live capital.

### Seven Stage 7 Dashboard Sections

| Section | What it tells you |
| --- | --- |
| System Operating Map | How Qadam's fund team hands work from sources, to the Python COO, local LLM, frontier LLM, quantum/quant review, risk gate, Alpaca Paper, and learning loop. |
| System Status | The consequence-based state: ready to observe, ready to reason, ready to quantify, ready to paper trade, or needs attention. |
| Data Sources Connected | The connected-source count, required blocker count, degraded feeds, and source groups without making the user hunt through every adapter. |
| Trading Strategies | The 60-day paper mandate, tracked markets, and active thesis families. |
| Qadam Activity Feed | A human-readable feed of what Qadam is evaluating now, without raw logs or hidden chain-of-thought. |
| Trade Consideration Board | The plain progression from observed signal to hypothesis, candidate, blocked, submitted, open, closed, or postmortem. |
| Paper Portfolio Capacity | The paper account value and deployment line against the GBP 100,000 baseline and GBP 200,000 target. |

### Advanced / Debug Mode

Advanced / Debug Mode is for inspection, not daily monitoring. It exposes the
deeper Trades, Evidence, Reasoning, Operations, and legacy diagnostic sections so
an operator can audit source evidence, runtime events, migration proofs, and
backend-derived status. It still cannot approve, submit, modify, close, resize,
or fund trades.

### Trades

Use Trades to answer:

- which observed signals exist
- which candidates exist
- which ideas are blocked and why
- whether any staged, submitted, open, closed, or postmortem states exist
- how the paper account is performing
- whether the paper growth trial is active, blocked, incomplete, or mature

Trade states:

| State | Meaning |
| --- | --- |
| Observed signal | Something was seen. No trade exists yet. |
| Candidate | A structured idea exists. No order exists yet. |
| Blocked | Qadam rejected or paused the idea. |
| Staged paper order | Qadam is allowed to prepare a paper order. |
| Submitted paper order | A paper order has been sent to the paper broker. |
| Open position | A paper trade is live. |
| Closed trade | A paper trade has ended. |
| Postmortem due | The result needs review. |
| Postmortem complete | The lesson has been logged. |

The dashboard should never imply Qadam is trading unless the backend state says
`staged_paper_order`, `submitted_paper_order`, `open_position`, or
`closed_trade`.

### Evidence

Use Evidence to answer:

- which source pipelines are online, degraded, pending, or missing credentials
- which setup evidence exists
- whether Yahoo Finance, Preference/PREF MCP, or other supplemental sources are
  available only as context
- whether an apparent signal has enough corroboration to matter

- Conflict
- Physical / OSINT
- Macro
- Market
- Narrative / social

Evidence is not a trade view. A degraded, stale, pending, or missing source
should reduce confidence or block an idea until the source posture improves.

### Reasoning

Use Reasoning to answer:

- what Qadam is focused on
- which hypotheses are active
- which evidence packets exist
- which private priors are shaping the question
- which factual evidence exists independently of those priors
- which model or analyst produced the current assessment
- what corroboration is missing
- why an idea has not reached Trades

The private worldview is Qadam's hidden-incentive and power-map lens. It can
help Qadam ask:

- who benefits if a story is true
- who benefits if a story is false
- what the market is assuming
- what observable signatures would confirm or kill the thesis

The worldview is not evidence. It helps Qadam ask better questions, then live
sources must corroborate any tradable implication.

### Operations

Use Operations when you need diagnostics rather than a quick operating read:

- the full system map
- event trail and process-console entries
- hard safety boundaries and kill switches
- Telegram notification state
- governance comments and member review
- bridge, runtime, and deployment diagnostics

Operations is still read-only. The full system map explains how modules connect;
its nodes are not controls.

### Six Founder Decision Blocks

| Block | What It Answers |
| --- | --- |
| System/team map | Which part of the Qadam operating team is active: data spine, Chief Operating Officer, Local Research Analyst, Strategy Lead, Head of Quant, safety policy, and paper/demo state. |
| Sources | Which data sources are online, degraded, missing, local-only, or blocked, and whether their quality can influence signal review. |
| Strategy | Which trading philosophy Qadam is currently applying, including Akber's filter and the second-order AI infrastructure lens. |
| Portfolio | Paper balance, open exposure, realized/unrealized P&L, drawdown, and whether the portfolio state matches the broker mirror. |
| Trades | Observed signals, candidates, blocked ideas, staged paper orders, submitted paper orders, open positions, closed trades, and postmortems. |
| Thinking | What Qadam is focused on next, what evidence is missing, which assumptions are being challenged, and where local/frontier/quant review fits. |

Diagnostics are not a seventh operating block. They are a retained technical
audit drawer for compatibility, checker evidence, and migration proof.

### Safety Status

Safety Status is the dashboard's global authority summary. Read it
before interpreting any panel.

Use it to answer:

- is Qadam paper only
- is the bridge read-only
- is live capital off
- are UI-to-broker and LLM-to-broker paths blocked
- does performance proof require verified records

If a deeper panel appears to contradict Safety Status, trust the backend
state and investigate before acting.

### Secure Live Bridge

The Secure Live Bridge is the read-only status path between the local runtime
and the authenticated dashboard.

It can:

- serve a sanitized cockpit snapshot
- expose public-safe health metadata
- rate-limit read requests
- fall back to a static snapshot if unavailable

It cannot:

- expose the local orchestrator
- read secrets
- expose raw payloads
- run shell commands
- approve, create, modify, close, resize, or submit trades
- call broker routes

### Old Implementation Terms

You may still see older module names in code, event logs, or status metadata.
Use this mapping when reading old notes:

| Old term | Read it now as |
| --- | --- |
| Mission Control | Overview / Stage 7 cockpit |
| System map | Overview's System Operating Map or Operations full map |
| Watching | Evidence |
| Cognition | Reasoning |
| Worldview / Private Edge | Reasoning prior context |
| Trade Layer | Trades |
| Money / Paper Account Timeline | Trades paper account and 60-day growth trial area |
| Forbidden | Operations safety diagnostics plus Safety Status |
| Process Console | Operations event trail |
| Fund Manager Comments | Operations governance |
| Communications / Telegram | Operations communications and member research intake |

Telegram has two separate rails. The outbound rail sends member notifications.
The inbound rail treats member messages as read-only research intake: useful
news, world-event context, articles, trading strategies, trading philosophy, or
approach notes can become logged datapoints or Strategy Lead considerations.
Telegram cannot place, approve, reject, modify, close, or resize trades, and it
should never show bot tokens, chat IDs, handles, raw message payloads, or local paths.

## 10. Status Labels

Important labels:

| Label | Meaning |
| --- | --- |
| Online | The module or source is available in the current snapshot. |
| Pending | The module exists but is waiting for a credential, process, or later phase. |
| Degraded | The module is partially available but has a known limitation. |
| Blocked | Qadam is deliberately prevented from using that path. |
| Local-only | The capability exists on the MacBook but is not exposed to the web. |
| Read-only ready | The bridge can serve dashboard status, but cannot run commands or trade. |
| Dry-run | Qadam can render or queue a message locally, but no live send is allowed. |
| Notify-only | A module can communicate status but cannot approve or create trade actions. |
| Certified | A phase gate has passed its explicit checker. |
| Eligible | A stage can proceed under its guardrails, but this is not live trading approval. |
| Paper mode | Paper account mode with live capital disabled. |
| Paper-live control plane certified | The guarded route, logs, checks, and dashboard visibility exist. This is not the same as active submission. |
| Paper-live certified | Full paper-live operation is allowed only when PT-10 reports `paper_live_certified=True`. |
| Paper order staged | A guarded paper order preparation record exists. |
| Paper order submitted | A paper order has been submitted to the paper broker under the allowed path. |
| Q-CTRL hold | Paper submission remains held while Q-CTRL product access or consultation is unresolved. The hold is clear when PT-1 reports `qctrl_paper_consultation_ready`. |
| Paper growth proof | Verified account-performance evidence for the 60-day paper growth trial. |

## 11. How Qadam Makes A Trade

The intended path is:

```text
Source event
  -> observation
  -> worldview lens shapes the question
  -> local Research Analyst filters noise
  -> Strategy Lead builds/challenges thesis
  -> evidence packet forms
  -> Akber 6-stage filter
  -> Signal Integrity Gate
  -> Risk Agent
  -> execution policy and kill-switch checks
  -> paper order can be staged/submitted only if allowed
  -> paper position opens/closes
  -> postmortem
  -> learning loop
```

Any missing step should block or degrade the trade.

## 12. How Qadam Finds And Acts On Edge

Qadam's edge is not one headline, one chart, one model opinion, or one private
worldview claim. Edge means Qadam has found a repeated, source-backed pattern
where real-world activity appears to move before market prices or prediction
probabilities fully reflect it.

Qadam looks for that edge across every watched sleeve:

- prediction markets
- crude oil
- silver
- semiconductors
- defence stocks

It uses all available source pipelines for all watched markets. Conflict,
shipping, aviation, macro, commodities, filings, prediction markets, technical
analysis, news, social context, and broker/account state are not treated as
separate little dashboards. They are normalized into evidence packets so Qadam
can ask whether the same pressure is showing up across multiple places.

The edge ladder is:

| Stage | Meaning |
| --- | --- |
| Observation | Something changed in the world, market, source spine, or price action. |
| Pattern candidate | Qadam sees a possible relationship between source activity and price or probability movement. |
| Edge under observation | The pattern repeats, has corroborating evidence, and has a clear market it might affect. |
| Trade candidate | Strategy Lead turns the edge into a specific paper-trade idea with entry, invalidation, sizing, and time window. |
| Guarded paper trade | Risk, signal integrity, Q-CTRL / quantum consultation where required, and execution policy all allow a paper order. |
| Postmortem | The outcome is reviewed after the paper position closes. |
| Strategy update proposal | Qadam proposes whether the pattern should increase, decrease, or change future strategy weight. |

The quantum/classical review is a core part of this process, not decoration. It
is used when Qadam is testing non-linear, ambiguous, or cross-source
relationships that a simple linear rule may miss. Quantum review can support,
weaken, or block a pattern hypothesis, but it does not place trades by itself.

What does not count as edge:

- a single headline
- a single technical setup without real-world evidence
- a private worldview prior without current corroboration
- one LLM saying a trade is interesting
- a Telegram message
- a green status label
- a dashboard pattern that has not entered the edge memory ledger

The edge memory ledger records pattern candidates, why Qadam cared, which
sources supported or contradicted them, what the market did next, whether the
paper trade worked, and what should change. This ledger is public-safe and
read-only. It cannot create trade candidates, approve risk, submit orders,
enable live capital, or grant proof credit.

Every day, Qadam should produce a daily Telegram learning brief in human
language explaining what it noticed and what it is still unsure about. Every
week, Qadam should produce a weekly thesis refresh that summarizes which
patterns strengthened, weakened, or stayed unproven. Strategy update proposals are not applied automatically:
they must survive promotion gates, postmortems, and the paper-only governance
boundary.

Qadam acts on edge only when the full chain is intact:

1. Evidence repeats before repricing.
2. The affected market or instrument is explicit.
3. The pattern has corroboration and contradiction review.
4. Quantum/classical review has completed where required.
5. Strategy Lead converts the pattern into a bounded trade candidate.
6. Signal Integrity and Risk approve the candidate.
7. Execution policy allows action.
8. Alpaca Paper is the only broker route used for paper orders.
9. The closed outcome updates the ledger and future strategy proposals.

## 13. Akber's 6-Stage Filter

Qadam uses Akber's approach as the strategic filter:

1. Low volatility or suppressed implied volatility.
2. Options distribution gap.
3. Specific catalyst.
4. Technical setup.
5. On-balance volume or flow intelligence.
6. Judgment, risk, and approval policy.

Qadam's job is to apply this consistently and record whether it worked.

## 14. How To Review A Trade Idea

When Qadam shows a signal or candidate, ask:

1. What is the catalyst?
2. Which instrument or market is affected?
3. What is the expected time window?
4. Which sources support it?
5. Which sources contradict it?
6. Is the private worldview only context, or is there live evidence?
7. What is the market pricing now?
8. What does Qadam think the probability or pricing gap is?
9. What is the entry logic?
10. What is the invalidation?
11. What is the risk cap?
12. What would prove Qadam wrong?
13. Why is the current state observation, candidate, blocked, staged, submitted,
    open, closed, or postmortem due?

If those answers are missing, the idea should remain blocked or under review.

## 15. Paper Growth Rules

Qadam's current paper mandate is the 60-day paper growth trial.

Operating rules:

- start from GBP 100,000 paper capital
- target GBP 200,000 paper portfolio value within 60 days
- favor fewer, larger, evidence-gated paper moves over low-conviction churn
- trade only where qualified setups exist
- no forced trades
- no manual trade-level overrides during the paper growth sample
- verified performance maturity remains separate from the 60-day growth target
- max drawdown must stay within the configured cap
- postmortems are required for closed paper trades
- live capital stays disabled

If a day has no qualified setup, the correct action is to record the no-trade
rationale. Qadam should not trade just to satisfy the 60-day target.

## 16. Daily Operating Routine

Use this routine when checking Qadam.

1. Start with Overview.
2. Read Safety Status and confirm paper-only, read-only, live-capital
   off, no UI-to-broker path, and no LLM-to-broker path.
3. Scan the System Operating Map, System Status, Data Sources Connected, Trading
   Strategies, Qadam Activity Feed, Trade Consideration Board, and Paper
   Portfolio Capacity sections.
4. Check whether any required source, reasoning, quant, risk, or paper-account
   dependency needs attention.
5. Separate what Qadam is watching from what it is considering, and separate
   trade ideas from actual paper trade states.
6. Open Advanced / Debug Mode only for the deeper Trades, Evidence, Reasoning,
   Operations, event trail, safety diagnostics, Telegram communications, or
   governance comments.
7. Record a no-trade rationale when there is no qualified setup. Do not force a
   paper trade to satisfy cadence.
8. Add a comment if something looks wrong, unclear, or strategically important.

## 17. What Members Can And Cannot Do

What Members Can Do:

Members can:

- review the dashboard
- read trade reasoning
- see blocked actions
- comment on modules, sources, signals, trades, and postmortems
- suggest improvements
- challenge assumptions
- review Telegram communications once configured
- send useful world-event articles or context to Qadam in Telegram
- send trading strategy, philosophy, or approach notes to Qadam in Telegram
- help decide strategy-level changes after review periods

Members cannot:

- use the dashboard to place live trades
- use Telegram to place trades
- Use Telegram to approve, reject, modify, close, or resize trades
- use Telegram to force a strategy change, qualified setup, paper order, or
  broker action
- Use the Secure Live Bridge to run commands or trade
- bypass the Risk Agent
- bypass the Signal Integrity Gate
- bypass the Event Log
- turn worldview priors into trade evidence
- treat a candidate as an order
- manually interfere with individual paper trades during a clean paper growth
  sample

## 18. Local Operator Instructions

Most members do not need this section. It is for the person operating Qadam from
the local repo.

### First local setup

1. Keep real secrets out of Git.
2. Put local runtime secrets only in ignored runtime secret files or environment
   variables.
3. Run:

```bash
scripts/bootstrap_runtime.sh
```

4. Start OrbStack or another Docker-compatible runtime if durable replay is
   needed.
5. Start the durable observation spine:

```bash
scripts/start_postgres_timescale_ingestion.sh
```

6. Verify cockpit status:

```bash
.venv/bin/python scripts/check_cockpit_status.py
```

### Running the paper trading routine

The actual paper trading runner should be allowed to advance by real market and
calendar time. Do not reset or backfill it unless there is an explicit
governance decision to restart the paper growth trial.

Run one operational pass:

```bash
.venv/bin/python scripts/run_phase7_demo_proof_harness.py
```

Then validate:

```bash
.venv/bin/python scripts/check_phase7_demo_proof_run.py
.venv/bin/python scripts/check_phase7_certification.py
.venv/bin/python scripts/check_phase7_live_promotion_review.py
```

Refresh cockpit status:

```bash
.venv/bin/python scripts/check_cockpit_status.py
node scripts/check_dashboard_phase7_demo_proof.js
```

The runner must preserve:

- no backfilled calendar days
- no simulated elapsed time
- no forced trades
- no live credentials loaded
- no live capital
- no broker live endpoints
- no mature performance claim unless verified records support it

### Source and dashboard checks

Useful checks:

```bash
.venv/bin/python scripts/check_postgres_timescale_replay.py --require-full-source-coverage
.venv/bin/python scripts/check_phase6_certification.py
.venv/bin/python scripts/check_phase7_readiness.py
.venv/bin/python scripts/check_cockpit_status.py
node scripts/check_dashboard_phase7_demo_proof.js
```

Never use a green dashboard as proof of live trading authority. Authority comes
from backend gates and explicit runtime artifacts.

## 19. Data Source Rules

Qadam uses five broad source pipelines:

- Conflict
- Physical / OSINT
- Macro
- Market
- Narrative / social

It also has supplemental data capabilities such as Yahoo Finance/yfinance and
Preference/PREF MCP. Supplemental sources are read-only context unless Qadam's
registry and trust policy explicitly promote them.

Data rules:

- one source is rarely enough
- stale data should block or degrade a trade
- private priors are not evidence
- raw payloads and secrets must not appear in the cockpit
- broker data and order receipts must be treated separately from market context
- prediction-market data can inform context, but write authority remains blocked
  unless a later explicit gate allows it

## 20. Troubleshooting

If the dashboard will not load:

1. Confirm you are signed in.
2. Confirm your email is allowlisted.
3. Try `/login/?next=/dashboard/`.
4. Check whether the static snapshot is available.
5. Ask the local operator to run `scripts/check_cockpit_status.py`.

If sources look stale:

1. Check Evidence for degraded reasons.
2. Check whether local durable replay is online.
3. Check whether credentials are missing or deferred.
4. Treat affected signals as lower confidence until source health recovers.

If a trade state looks wrong:

1. Check Trades for the exact lifecycle state.
2. Check Safety Status.
3. Check Operations for the Event Log or process-console entry.
4. Do not assume a candidate is an order.
5. Add a comment with the exact view and concern.

If Telegram contradicts the dashboard:

1. Trust the backend-derived dashboard state.
2. Check Operations for dry-run, suppressed, failed, or stale Telegram messages,
   plus inbound world-event and strategy-intake counters.
3. Escalate with a comment.

## 21. Red Flags

Escalate or comment if:

- a dashboard panel looks hardcoded or stale
- a source says online but has no recent heartbeat
- Qadam implies a trade without a trade state
- a blocked trade is presented as a failure
- a candidate has no catalyst
- a trade has no invalidation
- the paper balance changes without a logged trade
- Telegram sends a message that does not match the dashboard
- The bridge claims write authority, broker authority, shell access, or local orchestrator exposure
- Any secret, token, chat ID, local path, or credential appears in the UI
- any screen implies live capital is enabled

## 22. Glossary

| Term | Meaning |
| --- | --- |
| Cockpit | The Qadam dashboard. |
| Overview | The default Stage 7 dashboard cockpit: map, status, sources, strategies, activity feed, trade board, and paper capacity. |
| Trades | The dashboard view for signals, trade ideas, paper trades, paper-account performance, and verified records. |
| Evidence | The dashboard view for source posture, setup evidence, and supplemental context. |
| Reasoning | The dashboard view for priors, evidence, hypotheses, blockers, and analyst review. |
| Operations | The dashboard view for the full system map, event trail, communications, governance, and technical diagnostics. |
| Safety Status | The one global dashboard authority summary: paper only, read-only, live capital off, dashboard cannot place orders, AI cannot bypass risk checks. |
| Mission Control | Older implementation name now represented by Overview / Stage 7 cockpit. |
| Watching | Older implementation name now represented by Evidence. |
| Cognition | Older implementation name now represented by Reasoning. |
| Money | Older implementation name now represented inside Trades. |
| Forbidden | Older implementation name now represented by Safety Status plus Operations diagnostics. |
| Paper mode | Test-account mode; no live capital. |
| Paper growth trial | The 60-day paper operating window targeting GBP 200,000 from GBP 100,000. |
| Qualified setup | A setup that passes the current evidence, strategy, and risk prerequisites. |
| No-trade rationale | The logged reason Qadam did not trade. |
| Candidate | A structured trade idea, not an order. |
| Staged paper order | A guarded paper order preparation state. |
| Submitted paper order | A paper order submitted under the allowed paper path. |
| Postmortem | The after-action review for a closed paper trade. |
| Event Log | Append-only system memory. |
| Knowledge Graph | The learned context store. |
| Live capital | Real money trading authority; currently disabled. |
| Secure Live Bridge | Read-only dashboard status bridge. |
| Paper-live control plane certified | Guarded paper-trading machinery exists and is visible, but full submission may still be held. |
| Paper-live certified | Full guarded paper submission is allowed by PT-10. |
| Q-CTRL hold | A hold that blocks paper submission until Q-CTRL consultation/product access gates clear. |
| Edge memory ledger | Public-safe record of pattern candidates, evidence, outcomes, and strategy update proposals. |
| Daily Telegram learning brief | Human-readable daily summary of what Qadam noticed, what changed, and what remains unproven. |
| Weekly thesis refresh | Weekly review of which pattern-recognition theses strengthened, weakened, or stayed unresolved. |

## 23. First Release Success

Qadam is usable when a new founding member can answer:

- What is Qadam watching?
- What is Qadam thinking?
- Why does Qadam care?
- What is Qadam forbidden from doing?
- Which trades are ideas, blocked, staged, submitted, open, closed, or ready for
  postmortem?
- How is the paper account performing?
- What did Qadam learn?
- What should a human challenge or comment on next?

Qadam should feel understandable before it feels powerful.
