# Qadam User Guide

This guide is for someone who has never heard of Qadam and needs to know how to
use it safely.

Qadam is a local-first macro intelligence and paper-trading system. It watches
world events and markets, builds trade hypotheses, checks them against evidence
and risk rules, runs paper/demo-proof trades only when the gates allow it, and
logs outcomes for review.

Qadam is not a public financial-advice product, not a signal channel, and not a
live-capital trading bot. In the current first-release workflow, live capital is
disabled and the user-facing cockpit is a read-only operating mirror.

## 1. The Short Version

Use Qadam through the cockpit at `qadam.trade`.

The cockpit shows:

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
| COO | The Python orchestrator. It coordinates modules, checks health, writes logs, and routes work. |
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

As of this guide update, Qadam is in Phase 7 demo-proof operation:

- the 30 consecutive calendar day demo-proof harness has started
- proof trades are collected only where Q7-qualified setups exist
- the discipline target is 3 proof trades per week where qualified setups exist
- no trades are forced
- Phase 5 test trades do not count as Phase 7 proof trades
- Phase 7 proof credit remains blocked until Phase 7 evidence earns it
- live capital is disabled
- broker live endpoints are disabled

The cockpit and runtime checks are the source of truth. If this guide and the
dashboard disagree, trust the latest backend-derived dashboard state and inspect
the corresponding runtime artifact or checker output.

## 6. Before You Start

If you are a founding Fund Manager using the website, you need:

- an allowlisted email address
- a Supabase account created through the Qadam sign-up route
- access to `qadam.trade`
- enough context to understand that Qadam is in paper/demo-proof mode, not live
  trading mode

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

1. Read Mission Control at the top of the dashboard.
2. Confirm Qadam is in paper mode.
3. Confirm live capital is disabled.
4. Confirm the Secure Live Bridge or static snapshot is read-only.
5. Open the System Operating Map to see how the fund is wired.
6. Open Watching to see source health.
7. Open Cognition to see current hypotheses.
8. Open the Worldview or Private Edge panel to see private-prior context.
9. Open the Trade Layer to separate observations from actual trade states.
10. Open Money to inspect the paper account.
11. Open Forbidden to see active blocks and kill-switch boundaries.
12. Open Communications to see Telegram dry-run or delivery state.
13. Add a comment only if you have a useful observation, concern, or proposed
    improvement.

## 9. How To Read The Dashboard

### Mission Control

Mission Control is the first read after login.

Use it to answer:

- how many sources are configured or connected
- whether durable Postgres/Timescale replay is online
- what trading philosophy Qadam is applying
- whether the COO, local LLM, Strategy Lead, quantum oracle, risk gates, paper
  account, and Telegram rail are healthy
- whether Qadam currently has observed signals, candidates, blocked trades,
  staged orders, submitted orders, positions, or postmortems
- whether live capital and broker writes remain disabled

Mission Control is a summary, not a command surface. It cannot promote
hypotheses, approve trades, submit paper orders, write to brokers, or enable
live capital.

### System Operating Map

The System Operating Map shows the architecture.

Use it to answer:

- which modules are online
- which modules are pending, degraded, blocked, or local-only
- how information moves from sources to reasoning to trade review
- where Qadam intentionally stops before it can act

### Watching

Watching shows the source registry.

Pipeline groups:

- Conflict
- Physical / OSINT
- Macro
- Market
- Narrative / social

Use this panel to check whether sources are online, missing credentials,
degraded, or deferred. A degraded or pending source should not be treated as
strong evidence.

### Cognition

Cognition is Qadam's research notebook.

Use it to answer:

- what Qadam is focused on
- which hypotheses are active
- which evidence packets exist
- which model produced the current assessment
- what corroboration is missing
- why an idea has not reached the trade layer

Do not treat Cognition as a trade recommendation.

### Worldview / Private Edge Layer

The private worldview is Qadam's hidden-incentive and power-map lens.

It can help Qadam ask:

- who benefits if a story is true
- who benefits if a story is false
- what the market is assuming
- what observable signatures would confirm or kill the thesis

The worldview is not evidence. It helps Qadam ask better questions, then live
sources must corroborate any tradable implication.

### Trade Layer

The Trade Layer shows the trade lifecycle.

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

### Money / Paper Account Timeline

Money shows the paper account.

Use it to answer:

- starting balance
- current balance
- realized P&L
- unrealized P&L
- drawdown
- open positions
- closed trades
- progress toward the 100 closed proof-trade maturity benchmark

This panel is not a live-capital account. It is part of the paper/demo-proof
trial.

### Forbidden

Forbidden shows the safety rails.

Use it to answer:

- is live capital blocked
- are broker writes blocked
- are prediction-market writes blocked
- are stale-data checks blocking action
- are missing credentials blocking action
- are kill-switches active

Do not treat blocks as bugs. Many blocks are intentional.

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

### Process Console

Process Console shows recent checks and runtime events. It is not a shell.

### Fund Manager Comments

Use comments to:

- challenge a hypothesis
- flag a broken or stale source
- suggest a new data source
- question a trade candidate
- add a postmortem observation
- suggest a strategy-level improvement

Comments are for governance and learning. They are not a way to manually manage
each paper trade.

### Communications / Telegram

Telegram is Qadam's outbound member notification rail.

It may show:

- disabled, dry-run, configured, degraded, or blocked state
- verified, pending, or failed member delivery state
- queued, sent, failed, retried, and suppressed message counts
- trade lifecycle messages
- insight digests
- system warnings
- postmortem reminders

Telegram cannot place, approve, reject, modify, close, or resize trades. It
should never show bot tokens, chat IDs, handles, raw message payloads, or local
paths.

It should never show bot tokens, chat IDs, handles, raw message payloads, or local paths.

It cannot place, approve, reject, modify, close, or resize trades.

## 10. Status Labels

Important labels:

| Label | Meaning |
| --- | --- |
| Online | The module or source is available in the current snapshot. |
| Pending | The module exists but is waiting for a credential, process, or later phase. |
| Degraded | The module is partially available but has a known limitation. |
| Blocked | Qadam is deliberately prevented from using that path. |
| Local-only | The capability exists on the MacBook but is not exposed to the web. |
| Read-only ready | The bridge can serve the public-safe snapshot, but cannot run commands or trade. |
| Dry-run | Qadam can render or queue a message locally, but no live send is allowed. |
| Notify-only | A module can communicate status but cannot approve or create trade actions. |
| Certified | A phase gate has passed its explicit checker. |
| Eligible | A stage can proceed under its guardrails, but this is not live trading approval. |

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

## 12. Akber's 6-Stage Filter

Qadam uses Akber's approach as the strategic filter:

1. Low volatility or suppressed implied volatility.
2. Options distribution gap.
3. Specific catalyst.
4. Technical setup.
5. On-balance volume or flow intelligence.
6. Judgment, risk, and approval policy.

Qadam's job is to apply this consistently and record whether it worked.

## 13. How To Review A Trade Idea

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

## 14. Demo-Proof Rules

Phase 7 is the demo-proof phase.

Operating rules:

- 30 consecutive calendar days
- 3 proof trades per week only where qualified setups exist
- no forced trades
- no manual trade-level overrides during the proof sample
- 100 closed proof trades is the maturity benchmark
- max drawdown must stay within the configured cap
- postmortems are required for closed proof trades
- Phase 5 test trades do not count as Phase 7 proof trades
- live capital stays disabled

If a day has no qualified setup, the correct action is to record the no-trade
rationale. Qadam should not trade just to satisfy a quota.

## 15. Daily Operating Routine

Use this routine when checking Qadam.

1. Start with Mission Control.
2. Confirm paper mode.
3. Confirm live capital is disabled.
4. Confirm the Secure Live Bridge is read-only or the static fallback is loaded.
5. Open Watching and review degraded or missing sources.
6. Open Cognition and read current hypotheses.
7. Check the Worldview lens to understand the question Qadam is asking.
8. Open Trade Layer and separate observations from candidates, blocked trades,
   and real order states.
9. Check Money to confirm paper account status.
10. Check Forbidden before assuming anything should trade.
11. Check Communications for dry-run Telegram queue, failed sends, suppressed
    messages, or stale member delivery state.
12. Check Phase 7 demo-proof status if the 30-day harness is active.
13. Add a comment if something looks wrong, unclear, or strategically important.

## 16. What Members Can And Cannot Do

What Members Can Do:

Members can:

- review the dashboard
- read trade reasoning
- see blocked actions
- comment on modules, sources, signals, trades, and postmortems
- suggest improvements
- challenge assumptions
- review Telegram communications once configured
- help decide strategy-level changes after review periods

Members cannot:

- use the dashboard to place live trades
- use Telegram to place trades
- use Telegram to approve, reject, modify, close, or resize trades
- use the Secure Live Bridge to run commands or trade
- bypass the Risk Agent
- bypass the Signal Integrity Gate
- bypass the Event Log
- turn worldview priors into trade evidence
- treat a candidate as an order
- manually interfere with individual proof trades during a clean demo-proof
  sample

Use the Secure Live Bridge to run commands or trade.
Use Telegram to approve, reject, modify, close, or resize trades.

## 17. Local Operator Instructions

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

### Running the Phase 7 demo-proof harness

The actual demo-proof runner should be allowed to advance by real calendar
time. Do not reset or backfill it unless there is an explicit governance
decision to restart the proof window.

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
- no Phase 7 proof credit unless a later gate earns it

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

## 18. Data Source Rules

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

## 19. Troubleshooting

If the dashboard will not load:

1. Confirm you are signed in.
2. Confirm your email is allowlisted.
3. Try `/login/?next=/dashboard/`.
4. Check whether the static snapshot is available.
5. Ask the local operator to run `scripts/check_cockpit_status.py`.

If sources look stale:

1. Check Watching for degraded reasons.
2. Check whether local durable replay is online.
3. Check whether credentials are missing or deferred.
4. Treat affected signals as lower confidence until source health recovers.

If a trade state looks wrong:

1. Check the Trade Layer state.
2. Check Forbidden.
3. Check the Event Log or process console entry.
4. Do not assume a candidate is an order.
5. Add a comment with the exact panel and concern.

If Telegram contradicts the dashboard:

1. Trust the backend-derived dashboard state.
2. Check Communications for dry-run, suppressed, failed, or stale messages.
3. Escalate with a comment.

## 20. Red Flags

Escalate or comment if:

- a dashboard panel looks hardcoded or stale
- a source says online but has no recent heartbeat
- Qadam implies a trade without a trade state
- a blocked trade is presented as a failure
- a candidate has no catalyst
- a trade has no invalidation
- the paper balance changes without a logged trade
- Telegram sends a message that does not match the dashboard
- the bridge claims write authority, broker authority, shell access, or local
  orchestrator exposure
- any secret, token, chat ID, local path, or credential appears in the UI
- any screen implies live capital is enabled

The bridge claims write authority, broker authority, shell access, or local orchestrator exposure.
Any secret, token, chat ID, local path, or credential appears in the UI.

## 21. Glossary

| Term | Meaning |
| --- | --- |
| Cockpit | The Qadam dashboard. |
| Mission Control | The top-level dashboard summary. |
| Paper mode | Test-account mode; no live capital. |
| Demo proof | The Phase 7 proof window for observing Qadam under real calendar time. |
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

## 22. First Release Success

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
