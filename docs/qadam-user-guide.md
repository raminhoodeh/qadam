# Qadam User Guide

This guide is for the founding Fund Managers using the Qadam cockpit.

Qadam is a local-first macro intelligence and paper-trading system. The dashboard at `qadam.trade/dashboard/` is the operating mirror: it shows what Qadam is watching, what it is thinking about, what it is blocked from doing, which trade ideas exist, how the paper account is performing, and what the system has communicated to members.

## 1. Who Can Use Qadam

First-release access is limited to:

- Ramin
- Troy
- Akber
- Anas
- Ion

The first release is a £1000 paper/test-account trial. Qadam is allowed to become autonomous only inside the test account after the required gates exist. Live capital is out of scope.

## 2. What Qadam Is

Think of Qadam as a small fund team running inside a laptop:

| Role | Meaning |
| --- | --- |
| Fund Managers | The humans overseeing Qadam. They review, comment, challenge, and improve the system. |
| COO | The Python orchestrator. It coordinates modules, checks health, writes logs, and routes work. |
| Research Analyst | The local LLM. It filters noisy information locally before anything escalates. |
| Strategy Lead | The frontier LLM. It builds and challenges deeper strategy packets. |
| Head of Quant | The quantum/classical modelling layer. It acts as a bounded weekly oracle, not a real-time trading brain. |
| Risk Agent | The control layer that blocks oversize, stale, low-evidence, or unauthorized trades. |
| Event Log | The system memory. If it is not logged, it did not happen. |
| Secure Live Bridge | The D9 read-only status path. It lets the dashboard refresh without a manual deploy, but cannot run commands or trade. |
| Cockpit | The web dashboard. It is the readable operating view for members. |

## 3. The Main Rule

Qadam separates five states:

| State | Meaning |
| --- | --- |
| Observation | Something happened in a feed, chart, source, or market. |
| Worldview prior | Qadam's private worldview says the event may matter. This is context only, not proof. |
| Hypothesis | Qadam thinks the observation could become meaningful. |
| Trade intent | Qadam has a structured trade idea. |
| Execution state | Qadam has permission to stage, submit, hold, close, or postmortem a paper trade. |

A hypothesis is not a trade. A candidate is not an order. A blocked trade is not failure; it means the control system is working.

## 4. How To Read The Dashboard

### Mission Control

This is the first read after login.

Use it to answer:

- Which data sources are configured or connected?
- Is the durable Postgres/Timescale replay spine online, partial, or still waiting for the local service?
- What trading philosophy is Qadam currently applying to itself?
- How are the API spine, Python COO, local LLM, frontier LLM, quantum oracle, risk gates, and paper account connected?
- What is Qadam thinking about now?
- Which trade ideas are candidates, blocked, or still only observed signals?
- What positions, orders, balance, P&L, and drawdown are visible in the paper account?
- What is Qadam forbidden from doing?

Important boundary: Mission Control is a summary, not a command surface. It cannot promote hypotheses, approve trades, submit paper orders, write to brokers, or enable live capital.

Durable replay means Qadam can replay observations from its local Postgres/Timescale store. If Mission Control shows replay as offline or `0/35`, Qadam can still display the static cockpit and JSONL runtime state, but the full durable observation spine has not been started yet.

### System Operating Map

This is the top-level map of Qadam.

Use it to answer:

- Which modules are alive?
- Which modules are pending, blocked, degraded, or local-only?
- How does information move from data to reasoning to trade review?
- Where does Qadam stop before it can act?

Important labels:

- `online`: the module is available in the current snapshot.
- `pending`: the module exists but is waiting for a credential, process, or later phase.
- `degraded`: the module is partially available but has a known limitation.
- `blocked`: Qadam is deliberately prevented from using that path.
- `local-only`: the capability exists on the MacBook but is not exposed to the web.
- `read-only ready`: the Secure Live Bridge can serve the public-safe snapshot, but cannot run commands or write trades.
- `dry-run`: Qadam can render or queue a message locally, but no live send is allowed.
- `notify-only`: a module can communicate status but cannot approve or create trade actions.

### Watching

This panel shows the source registry.

It answers:

- What is Qadam watching?
- Which data pipelines are alive?
- Which sources are missing credentials?
- Which feeds are degraded?

Pipeline groups:

- Conflict
- Physical / OSINT
- Macro
- Market
- Narrative / social

If a source is degraded or pending, it should not be treated as strong evidence.

### Cognition

This panel shows what Qadam is thinking about.

It answers:

- What hypotheses are active?
- Which evidence packets support or weaken them?
- Which model is responsible for the current analysis?
- What corroboration is missing?
- Why has the idea not reached the trade layer?

Read this panel as Qadam's research notebook, not as a trading signal.

### Private Edge Layer / Worldview

This panel shows Qadam's private worldview lens.

It answers:

- Which hidden-incentive or power-map lens is shaping the question?
- Which private prior is active?
- What market channels might be affected?

Important boundary: the worldview is not evidence. It helps Qadam ask better questions. Live sources must still corroborate any tradable implication.

### Trade Layer

This panel shows the trade ladder.

It answers:

- Which observed signals exist?
- Which trade candidates exist?
- Which trades are blocked?
- Are there staged paper orders?
- Are there submitted orders?
- Are there open positions?
- Are there closed trades?
- Which trades need postmortem?

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

The dashboard should never imply Qadam is about to trade unless the state is `staged_paper_order` or `submitted_paper_order`.

The dry-run paper-submit receipt section is deliberately conservative. It may show an idempotency preview, Event Log prewrite schema, pre-trade snapshot schema, and duplicate-order guard schema, but those are readiness checks only. Until the later execution gates are explicitly enabled, Qadam cannot allocate a broker-usable order ID, write a pre-order event, submit to Alpaca, or create broker state.

### Money / Paper Account Timeline

This panel shows the £1000 paper/test account.

It answers:

- Starting balance.
- Current balance.
- Realized P&L.
- Unrealized P&L.
- Drawdown.
- Open positions.
- Closed trades.
- Progress toward the 100-closed-trade maturity benchmark.

Until a real read-only broker connection exists, this panel is a local mirror, not a live broker account.

### Forbidden

This panel shows what Qadam is not allowed to do.

It answers:

- Is live capital blocked?
- Are broker writes blocked?
- Are stale-data checks blocking action?
- Are missing credentials blocking action?
- Are kill-switches active?

Do not treat blocks as bugs. Most blocks are intentional safety rails.

### Secure Live Bridge

The Secure Live Bridge is the D9 status path between Qadam's local runtime and the authenticated dashboard.

It can:

- Serve the sanitized cockpit status snapshot.
- Prove the snapshot with a detached signature or digest file.
- Rate-limit read requests.
- Fall back to the static snapshot if the bridge is unavailable.

It cannot:

- Expose the local MacBook orchestrator.
- Read secrets, raw payloads, or local files.
- Run shell commands.
- Approve, create, modify, close, resize, or submit trades.
- Send broker orders.

### Process Console

This panel shows runtime events.

It answers:

- What did Qadam recently check?
- What changed in the last snapshot?
- Which processes are running, blocked, or waiting?

This is not a shell. It is a read-only event feed.

### Fund Manager Comments

This panel is for member suggestions and governance notes.

Use it to:

- Suggest improvements.
- Flag a bad source.
- Challenge a hypothesis.
- Comment on a trade candidate.
- Add postmortem observations.

Comments should be linked to the relevant module, source, signal, trade, or postmortem when possible.

### Communications / Telegram

The Communications panel shows the Telegram member communications rail.

In D8A it is dry-run by default. It shows:

- Whether Telegram is disabled, dry-run, configured, degraded, or blocked.
- Whether the send gate is enabled or disabled.
- Verified, pending, and failed member counts.
- Queued, sent, failed, retried, and suppressed message counts.
- Recent outbox metadata for trade lifecycle updates, insight digests, system warnings, and postmortem reminders.

Telegram is outbound-only in the first release. It cannot place, approve, reject, modify, close, or resize trades. It should never show bot tokens, chat IDs, handles, raw message payloads, or local paths.

## 5. Daily Operating Routine

Use this routine when checking Qadam.

1. Start with the System Operating Map.
2. Check whether Qadam is in paper mode and live capital is disabled.
3. Confirm the Secure Live Bridge is read-only ready or that the static fallback is loaded.
4. Open Watching and look for degraded or missing sources.
5. Open Cognition and read current hypotheses.
6. Check the Worldview lens to understand the question Qadam is asking.
7. Open Trade Layer and separate observations from candidates, blocked trades, and real order states.
8. Check Money to confirm paper account status.
9. Check Forbidden before assuming anything should trade.
10. Check Communications for dry-run Telegram queue, failed sends, suppressed messages, or stale member delivery state.
11. Add a comment if something looks wrong, unclear, or strategically important.

## 6. What Members Can Do

Members can:

- Review the dashboard.
- Read trade reasoning.
- See blocked actions.
- Comment on modules, sources, signals, trades, and postmortems.
- Suggest improvements.
- Use allowed system-level controls once implemented.
- Receive Telegram communications once configured.

Members cannot:

- Use the dashboard to place live trades.
- Use Telegram to place trades.
- Use Telegram to approve, reject, modify, close, or resize trades.
- Use the Secure Live Bridge to run commands or trade.
- Bypass the Risk Agent.
- Bypass the Signal Integrity Gate.
- Bypass the Event Log.
- Turn worldview priors into trade evidence.
- Treat a candidate as an order.

## 7. How Qadam Makes A Trade

The intended path is:

```text
Source event
  -> observation
  -> worldview lens shapes the question
  -> local Research Analyst filters noise
  -> Strategy Lead builds/challenges thesis
  -> evidence packet forms
  -> Akber 6-stage filter
  -> Risk Agent checks size, freshness, and policy
  -> paper order can be staged/submitted
  -> paper position opens/closes
  -> postmortem
  -> learning loop
```

Any missing step should block or degrade the trade.

## 8. Akber's 6-Stage Filter

Qadam uses Akber's approach as the strategic filter:

1. Low volatility or suppressed implied volatility.
2. Options distribution gap.
3. Specific catalyst.
4. Technical setup.
5. On-balance volume or flow intelligence.
6. Judgment, risk, and approval policy.

Qadam's job is to apply this consistently and record whether it worked.

## 9. The Worldview Boundary

The `how-the-world-works/` corpus is a private edge layer.

It helps Qadam ask:

- Who benefits?
- Which narrative is being sold?
- Which institution has an incentive to hide stress?
- Which energy, chip, dollar, or security dependency is exposed?
- What would the market price if the official story is wrong?

But the worldview cannot trigger a trade. It must become observable signatures, then evidence, then a candidate, then a risk-approved paper action.

## 10. Red Flags

Escalate or comment if:

- A dashboard panel looks hardcoded or stale.
- A source says online but has no recent heartbeat.
- Qadam implies a trade without a trade state.
- A blocked trade looks mislabeled as a failure.
- A candidate has no catalyst.
- A trade has no invalidation.
- The paper balance changes without a logged trade.
- Telegram sends a message that does not match the dashboard.
- The bridge claims write authority, broker authority, shell access, or local orchestrator exposure.
- Any secret, token, chat ID, local path, or credential appears in the UI.

## 11. First Release Success

The first release succeeds when the founding members can clearly answer:

- What is Qadam watching?
- What is Qadam thinking?
- Why does Qadam care?
- What is Qadam forbidden from doing?
- Which trades are ideas, blocked, staged, open, closed, or ready for postmortem?
- How is the £1000 test account performing?
- What did Qadam learn?

Qadam should feel understandable before it feels powerful.
