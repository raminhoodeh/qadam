# Research Telegram Reporting

## Operating Contract

The existing `com.qadam.learning-brief` launchd agent checks every five minutes.
It now runs research notifications before deciding whether the existing morning
or evening learning brief is due. No additional polling process or broker path
is introduced. Telegram notification failures do not prevent a due learning pass.

- New research relationships, material research-state changes, and new concrete
  catalysts linked to a relationship produce pattern alerts. Alerts explain the
  relationship, instruments, evidence and limitations. A score is not described
  as a probability of profit.
- Source freshness, refreshed timestamps, regenerated IDs, and score movement
  alone do not constitute a discovery. Fixture, expired, unresolved and unrelated
  event triggers are excluded. The first run quietly establishes a baseline;
  existing findings are not advertised as new discoveries.
- Once per actual local calendar date after the configured evening cutoff
  (currently 20:00 Asia/Dubai), a separate daily strategy note explains current
  directional hypotheses, linked evidence, entry status, invalidation, exits and
  routing constraints. It states when the recorded stance is unchanged. Missing
  or stale strategy evidence is reported explicitly instead of inventing a stance.
- Existing morning/evening research briefs, quantum-result reporting and trade
  notifications are retained. This addition does not authorize a strategy change,
  risk approval, order, broker write or paid quantum job.

## Delivery And Recovery

`data/runtime/qadam_research_telegram_state.json` is a notification-only outbox
and receipt cache, not an execution ledger. An exclusive file lock serializes
senders; atomic fsynced writes preserve pending and in-flight deliveries.
Confirmed Telegram message IDs establish successful delivery. Explicit API
rejections retry after 15 minutes. A timeout or crash during an ambiguous send
becomes `delivery_uncertain`, rather than blindly resending a possible duplicate.
Uncertain delivery needs receipt investigation; Telegram has no client-supplied
idempotency key that can guarantee exactly-once delivery across that failure.

At most three messages are attempted per pass, with the daily strategy note
prioritized. Pattern alerts expire after one hour; strategy notes expire at local
midnight, with no prior-day backfill. Pending daily text refreshes before retry.
Stale or superseded pattern states are not sent. Thirty-day receipt/event
retention avoids an unbounded append-only notification log. A missed/unsafe/
uncertain delivery is visible in notification status during that retention window.

The existing three-hour team health message includes reporting health. A missing
or older-than-15-minute notification check is reported as stale, independently
of trading-pipeline health. Persistent transport failures cannot be repaired by
pretending delivery succeeded.

## Configuration And Verification

This sender inherits the daily-learning Telegram enabled/dry-run flags, configured
group target and secret storage. Daily timing uses
`daily_learning_automation_timezone` and
`daily_learning_automation_after_local_time`. It requires paper mode with live
capital disabled. Disabling notifications or enabling dry-run prevents sends.

Preview without consuming a delivery key or advancing the live baseline:

```sh
.venv/bin/python scripts/run_research_telegram_notifications.py
```

Normal real-time pass, also called by the existing launchd scheduler:

```sh
.venv/bin/python scripts/run_research_telegram_notifications.py --live
```

Inspect `data/runtime/qadam_research_telegram_status.json` for the last check,
blockers, pending/confirmed/uncertain counts and daily timezone. Cross-check
actual sent receipts in the state file; a later pass with zero sends is not a
delivery failure. Neither command forces a daily note outside its real window.

## Release Verification

Focused tests cover source-refresh noise, concrete evidence changes, production
trigger vocabulary, fixture/expiry filtering, direction and version lineage,
restart deduplication, delivery failure states, paper-only flags, daily timing,
unchanged strategy reporting, stale evidence, queue draining and scheduler wiring.
Real-runtime previews must be reviewed before deployment; unit fixtures alone
cannot establish that current provider schemas are compatible.

Pre-deployment verification on 6 September 2026: 74 focused notification,
scheduler, team-health and critic tests passed. The 171-file comparable
regression selection plus notification tests returned 1,051 passed and the same
39 failures as the unchanged baseline, with no new failures. The seven existing
daily-learning tests in that failure set require runtime fixtures absent from a
clean checkout. Changed Python files passed Ruff. Read-only real-data inspection
confirmed five fresh research relationships and the actual trigger vocabulary;
the strategy preview correctly described the XAR hypothesis and its exact-version
duplicate-exposure veto. No preview submitted a message or order.
