# Qadam Communications Policy

Effective 27 October 2026, proactive Telegram and automation reports are limited
to confirmed paper fills and substantive market patterns in readable English.
The tracked preference is `config/qadam_communications.json`.

Patterns explain the observed relationship, relevant instruments, dated evidence
and uncertainty. Score refreshes, workflow changes and unchanged daily summaries
are not discoveries. No new findings means no filler message.

Routine and exceptional health alerts, recovery notices, pending-order notices,
portfolio digests and deployment updates are muted. This includes proactive
failure alerts, as requested by the user. On-demand Telegram replies remain
available. Existing health checks, repair processes, logs and dashboard health
continue operating independently of notification preferences.

The confirmed-fill sender retains its durable outbox, destination verification
and duplicate protection. Muted legacy messages are not recorded as delivered.
Historical failed or uncertain receipts remain available for audit. Muted health
backlogs cannot occupy the fill sender's delivery limit.

The existing daily learning automation retains its schedule and read-only
authority. Its user-facing output is limited to substantive new findings and
unreported confirmed trades. The existing five-minute research notifier remains
responsible for Telegram patterns; the automation must not add another sender.

The optional `QADAM_COMMUNICATION_PROFILE=all` compatibility override restores
legacy notification behaviour only when explicitly configured. The deployed
default is `trades_and_patterns`, including when the preference file is absent or
malformed. Notification preferences never grant execution or risk authority.
