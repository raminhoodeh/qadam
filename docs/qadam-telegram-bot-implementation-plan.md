# Qadam Telegram Bot Implementation Plan

This plan defines Telegram as Qadam's member communications rail.

The Telegram bot is not a trading interface. It is a supervised outbound channel that sends Qadam trade lifecycle updates, insight digests, system warnings, and postmortem summaries to the founding Fund Managers. The dashboard remains the canonical control surface; Telegram is the high-signal alert layer.

## 1. Purpose

The bot should answer one practical question:

What does Qadam need the members to know without requiring them to keep the dashboard open?

It should send:

- Trade lifecycle communications: observed signal, candidate created, candidate blocked, paper order staged, paper order submitted, position opened, position closed, postmortem due, postmortem complete.
- Insight communications: high-confidence hypothesis, major evidence change, worldview lens applied, source corroboration found, source contradiction found.
- Risk and governance communications: live capital blocked, stale data block, kill-switch activation, broker degraded, source outage, model unavailable.
- Daily/weekly digests: what Qadam watched, what it learned, what it blocked, current paper-account state, and next focus.

It should not send:

- Raw secrets.
- Raw source payloads.
- Raw local file paths.
- Broker credentials.
- Order-creating links.
- Any message implying a trade is guaranteed unless backend state is `staged_paper_order`, `submitted_paper_order`, `open_position`, or `closed_trade`.

## 2. Operating Boundary

First release boundary:

- Telegram is outbound-only.
- No Telegram command can place, modify, close, approve, reject, or resize a trade.
- No LLM can directly send Telegram messages.
- Messages are created from structured Event Log/status records through a template renderer.
- Every sent, skipped, retried, failed, or suppressed message is logged locally.
- Bot token and chat IDs are local secrets and never appear in the public cockpit snapshot.
- Dashboard shows bot health and delivery status, not secret identifiers.

Later boundary:

- Read-only inbound commands can be considered after the D9 secure bridge has proven stable in read-only status mode.
- Emergency commands such as `/status` or `/kill_switch_request` require explicit design, member identity verification, confirmation, and Event Log audit.
- Telegram still cannot become a broker path.

## 3. Architecture

```text
Qadam Event Log / runtime state
  -> Notification Router
  -> Telegram Message Template Renderer
  -> Local Telegram Outbox
  -> Telegram Dispatcher
  -> Telegram Bot API
  -> Founding Fund Manager private chat/group

Dispatcher status
  -> cockpit-status.json
  -> qadam.trade dashboard Communications panel
```

### Components

| Component | Purpose |
| --- | --- |
| Telegram member registry | Maps founding Fund Managers to verified Telegram chat IDs locally. |
| Notification Router | Decides which Event Log/status events are eligible for Telegram. |
| Message Template Renderer | Converts structured events into short, consistent, non-hype messages. |
| Local Telegram Outbox | JSONL/SQLite queue for pending, sent, failed, retried, and suppressed messages. |
| Telegram Dispatcher | Sends messages through the Telegram Bot API with rate limits and retries. |
| Cockpit Communications Panel | Shows bot health, subscriber count, queue count, last sent, failed deliveries, and message categories. |
| Acceptance Check | Validates no secrets leak, no execution authority exists, and test messages render safely. |

## 4. Local Configuration

Required local env values:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_BOT_USERNAME`
- `TELEGRAM_DEFAULT_CHAT_ID` or member-specific chat IDs
- `QADAM_TELEGRAM_ENABLED=false` by default
- `QADAM_TELEGRAM_DRY_RUN=true` by default

Local files:

- `data/runtime/telegram-members.json`
- `data/runtime/telegram-outbox.jsonl`
- `data/runtime/telegram-deliveries.jsonl`
- `data/runtime/telegram-digests.jsonl`

Public status export must redact:

- Bot token.
- Chat IDs.
- User handles unless explicitly approved.
- Raw message payloads if they include sensitive detail.

## 5. Member Onboarding

Phase one onboarding should use a private group or direct bot chats.

1. Create the bot through BotFather.
2. Store the token locally.
3. Add the bot to a private Qadam Telegram group, or have each member start the bot directly.
4. Capture each verified chat ID locally.
5. Map chat IDs to founding members: Ramin, Troy, Akber, Anas, Ion.
6. Send a dry-run welcome message.
7. Enable real sends only after the dashboard shows the bot as configured and dry-run tests pass.

The system should support missing member records. If Akber or Anas do not have verified chat IDs yet, the bot marks them as pending instead of failing the whole channel.

## 6. Message Classes

### Trade Lifecycle

Messages should be compact and stateful:

- `observed_signal`: Qadam saw something worth tracking.
- `trade_candidate`: Qadam created a structured candidate.
- `blocked_trade`: Qadam rejected or held a candidate, with reason.
- `staged_paper_order`: Qadam is allowed to prepare a paper order.
- `submitted_paper_order`: A paper order was submitted.
- `open_position`: A paper position is open.
- `closed_trade`: A paper trade closed with P&L.
- `postmortem_due`: A closed trade needs review.
- `postmortem_complete`: The lesson was logged.

### Insight Digest

Insight messages should summarize:

- Current hypothesis.
- Evidence that strengthened it.
- Evidence that weakened or blocked it.
- Worldview lens used as private prior.
- Missing corroboration.
- Whether it is still non-executable.

### System Health

System messages should cover:

- Source outage.
- Stale data.
- LM Studio/local model unavailable.
- Gemini provider unavailable.
- Quantum provider unavailable.
- Paper account mirror degraded.
- Kill-switch state.
- Dashboard snapshot stale.

## 7. Dashboard Integration

Add a Communications panel to the dashboard and a Telegram node to the system map.

The panel should show:

- Bot status: disabled, dry-run, configured, sending, degraded, blocked.
- Mode: dry-run or live-send.
- Subscriber count: verified, pending, failed.
- Queue count: pending, sent, failed, suppressed.
- Last sent time.
- Last failed reason.
- Last digest title.
- Active message classes.
- Boundary: outbound-only, no execution authority.

The system map should show:

- `Telegram Bot`
- owner: `Fund Manager Interface`
- status from `communications.telegram.status`
- current process: queue count and last sent time
- authority: `notify_only`

## 8. Implementation Phases

### Phase T0 - Contract And Boundaries

Build:

- Define `telegram_members`, `telegram_outbox`, `telegram_delivery`, and `telegram_status` schemas.
- Add `communications.telegram` to the cockpit status contract.
- Add sanitizer checks for bot token, chat IDs, and raw Telegram payloads.
- Add dashboard placeholder panel reading from the status contract.

Exit gate:

- Dashboard can show Telegram as disabled/dry-run from local JSON.
- Public status snapshot contains no bot token, chat IDs, or private handles.
- Telegram has no execution or approval authority.

Status: implemented for D8A as a local dry-run contract. The public status key is `communications.telegram`; it exposes mode, send gate, member counts, queue counts, message classes, recent message metadata, and an outbound-only boundary.

Current local state as of 2026-05-18: bot token and bot username are configured in the ignored local secret file, while `TELEGRAM_DEFAULT_CHAT_ID` is still pending. The send gate remains disabled and dry-run remains enabled.

### Phase T1 - BotFather Setup And Local Secret

Build:

- Create bot through BotFather.
- Store `TELEGRAM_BOT_TOKEN` locally.
- Store `TELEGRAM_BOT_USERNAME` locally for diagnostics.
- Add `TELEGRAM_DEFAULT_CHAT_ID` only after the target chat has messaged the bot or the bot has been added to the private test group.
- Add `.env.example` placeholders only.
- Add `scripts/check_telegram_config.py`.

Exit gate:

- Config check confirms token presence without printing it.
- Missing token degrades the module instead of failing Qadam startup.

### Phase T2 - Dry-Run Outbox

Build:

- Add local outbox writer.
- Add message templates for trade lifecycle, insight, system health, and digest.
- Add dry-run renderer that writes messages to outbox without sending.
- Add Event Log entries for queued/suppressed messages.

Exit gate:

- Test trade candidate creates a dry-run Telegram message.
- Blocked trade creates a dry-run Telegram message.
- Insight digest creates a dry-run Telegram message.
- No network call is made.

Status: implemented for D8A with deterministic dry-run sample messages for one trade candidate, one blocked trade, one insight digest, and one system warning.

### Phase T3 - Private Test Send

Build:

- Add Telegram Bot API client.
- Send one explicit test message to Ramin's verified chat or private Qadam group.
- Add retry/backoff for transient failures.
- Add fail-closed behavior for missing/invalid chat IDs.

Exit gate:

- One test message is delivered.
- Delivery is logged locally.
- Dashboard shows last sent time and delivery status.

### Phase T4 - Founding Member Rollout

Build:

- Add verified member mapping for Ramin, Troy, Akber, Anas, and Ion as they opt in.
- Add member delivery preferences: critical only, trades only, insights and trades, daily digest.
- Add per-member delivery status.

Exit gate:

- Bot can send the same digest to all verified founding members.
- Pending members do not block verified-member delivery.
- Dashboard shows verified/pending member counts.

### Phase T5 - Trade Lifecycle Hooks

Build:

- Connect outbox creation to trade intent state changes.
- Connect blocked-trade messages to Risk Agent and Signal Integrity Gate blocks.
- Connect paper-account mirror events to open/close/postmortem messages.

Exit gate:

- Candidate, blocked, staged, submitted, open, closed, and postmortem states each have safe Telegram templates.
- Messages never imply execution before the backend state allows it.

### Phase T6 - Insight And Worldview Digests

Build:

- Daily digest summarizing what Qadam watched, thought, blocked, and learned.
- Include worldview lens only as private prior.
- Include missing corroboration and forbidden-action state.

Exit gate:

- Digest clearly separates observation, worldview prior, hypothesis, trade candidate, and execution state.
- Digest can be rendered into dashboard and Telegram without contradicting cockpit wording.

### Phase T7 - Later Inbound Commands

Build later only:

- `/status`
- `/latest`
- `/paper_account`
- `/open_positions`
- `/blocked`
- `/kill_switch_request`

Exit gate:

- Commands are read-only by default.
- Any emergency command requires identity check, confirmation, Event Log write, dashboard visibility, and policy approval.
- No command can send broker instructions directly.

## 9. Message Style Rules

Telegram messages should be short and operational.

Use this structure:

```text
Qadam: [state]
[instrument/theme]
Why it matters: ...
Evidence: ...
Block/risk: ...
Status: ...
Dashboard: qadam.trade/dashboard/
```

Avoid:

- Hype.
- Certainty language.
- Long essays.
- Financial advice phrasing.
- "Qadam will trade" unless order state is actually staged/submitted.
- "Guaranteed", "sure thing", "risk-free", or similar language.

## 10. Acceptance Criteria

The Telegram bot is ready for first release when:

- Bot token is local only.
- Member chat IDs are local only.
- Dashboard shows Telegram communications status.
- Dry-run messages are generated from Event Log/status events.
- One private test message can be delivered.
- Delivery, failure, retry, and suppression are logged.
- No Telegram input can place trades.
- No Telegram output leaks secrets, local paths, raw tokens, or broker authority.
- Trade messages match dashboard state exactly.
