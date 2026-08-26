# Qadam Telegram Read-Only Interface

Qadam's configured Telegram group can inspect current canonical state without
becoming a command or execution surface.

## Available Queries

| Query | What It Returns |
| --- | --- |
| `/status` | Operator, PaperOps, paper portfolio and self-healing summary. |
| `/portfolio` | Paper equity, P&L, cash and current holdings. |
| `/trading` | Latest Router explanation and guarded PaperOps pass. |
| `/patterns` | Three highest-ranked current research patterns. |
| `/health` | Service freshness, circuits and repair counts. |
| `/repairs` | Reliability critic state and open repair queue. |
| `/help` | Command reference and safety boundary. |

`Qadam status`, `Qadam patterns`, and commands addressed to the configured bot
username are also recognized. Answers are deterministic projections of local
runtime artifacts. No LLM interprets a query and no free-form instruction is
executed.

## Operating Model

The interface and Telegram research intake share one `getUpdates` consumer rail
protected by a non-blocking file lock. This prevents two local services from
consuming the same update independently. The interface checks for updates every
30 seconds, responds only inside the configured group, and advances the shared
offset only after a response succeeds. A delivered response is deduplicated by
update, message and query identity.

The response ledger stores only one-way hashes for Telegram identifiers. It
does not store bot tokens, raw chat identifiers, usernames, private message
payloads, credentials or local paths.

## Authority Boundary

Telegram can read Qadam's state and contribute read-only research intake. It
cannot create or modify research goals, evidence, patterns, strategies,
candidates, approvals, risk decisions, execution decisions, orders, broker
state, proof credit, policies, quantum jobs, code, secrets or live-capital
authority. Commands such as `/buy`, `/sell`, `/trade`, `/repair`, `/approve`,
and `/live` receive a boundary explanation and perform no action.

## Install And Verify

```bash
scripts/install_qadam_telegram_readonly_interface_launch_agent.sh --load
.venv/bin/python scripts/check_qadam_telegram_readonly_interface.py
```

The installer renders and loads
`com.qadam.telegram-readonly-interface`, registers the command menu only for the
configured group, and sends one deduplicated interface-ready notice.

Canonical artifacts:

- `data/runtime/qadam_telegram_readonly_interface_status.json`
- `data/runtime/qadam_telegram_readonly_interface_checks.json`
- `data/runtime/qadam_telegram_readonly_response_ledger.jsonl`

Logs:

- `data/runtime/qadam-telegram-readonly-interface.stdout.log`
- `data/runtime/qadam-telegram-readonly-interface.stderr.log`

Uninstall only this service with:

```bash
scripts/uninstall_qadam_telegram_readonly_interface_launch_agent.sh
```
