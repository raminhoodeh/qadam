# Discovery and Telegram reliability repair - 28 September 2026

## Incident evidence

The afternoon PaperOps repair restored execution. The resident operator later
submitted an NVDA paper short at 15:58 UTC: 13 shares, filled at USD 229.966923.
The submission notification has a successful Telegram receipt, message 815.
A read-only getChat check confirmed that the configured destination is the
Qadam Bot group. Neither fact proves that a participant read the message.

At 17:54 UTC the discovery service failed its current-expectancy certification.
The foundry had successfully evaluated 12 queued relationships, placing all 12
on explicit research holds. It correctly produced zero expectancy records.
The certification incorrectly required a nonempty collection and classified
this normal transition as a code defect. Tests and a healthy snapshot earlier
in the day did not exercise the later active-to-empty transition.

The submission notifier also hardcoded GBP even when the account reported USD,
and did not send a separate broker-confirmed fill. Its success predicate trusted
the API's ok flag without validating a message ID and destination. The original
message cannot be claimed missing or unread from the available API evidence.

## Implemented changes

- The foundry publishes a completed generation with row count, row digest and
  input queue digest. A fresh, consistent completed-empty generation is healthy
  research inactivity, not permission to trade. Missing, stale or superseded
  generations request bounded dependency recovery. Corrupt records, mismatched
  counts and authority violations remain failures.
- An independent fill reporter runs on the existing 30-second Telegram agent,
  before inbound polling. It reads the broker mirror; it cannot create orders.
  A small SQLite outbox and exclusive process lock preserve delivery identities
  across restarts. Initial activation reports the preceding day's fills, not
  archived account history. Confirmed receipt requires the expected destination
  and a positive Telegram message ID. API acceptance is not a read receipt.
- Explicit rate limits receive bounded delayed retries. A timeout or interrupted
  send is delivery-uncertain and cannot be automatically duplicated. Invalid
  configuration or unresolved delivery remains visible, not silently healthy.
- Fill text distinguishes opening a short from selling a long, reports the
  actual account currency, execution price and execution time. Submission text
  explicitly distinguishes an order submission from a fill.
- The independent monitor also reports failures that persist for two minutes
  and verified recovery. It detects a missing operator heartbeat, not merely an
  error reported by the operator itself. The three-hour critic includes fill
  delivery health, can refresh a stale delivery worker through its bounded,
  locked entry point, and does not let a messaging failure prevent independent
  allowlisted runtime repairs.
- Research reporting retains old uncertain receipts unchanged. Once an expired
  message is over a day old and a later message of the same class has a confirmed
  receipt, it is a visible historical warning, not a current delivery outage.
  Missing subsequent confirmation or a recent failure still needs attention.

## Regression and release checks

Regression coverage includes active -> empty -> active research, absent and
corrupt artifacts, queue advancement, stale outputs, restart deduplication,
rate-limit backoff/exhaustion, send interruption, uncertain/wrong-destination
receipts, archived epoch exclusion, sustained fault/recovery reporting and
critic sign-off when messaging is unavailable.

The broad Qadam/PaperOps regression run passed 1,410 tests with 200 existing
Qiskit deprecation warnings. The focused 70-test run passed again after the
final monitoring addition. The live Telegram worker obtained destination-matched
receipt 819 for the NVDA fill update and subsequent polls did not duplicate it.
The discovery service recovered from the completed-empty generation without
lowering a trading threshold or manufacturing evidence.

Release acceptance requires the exact committed operator build, fresh service
receipts, closed circuits, no outstanding repair requests, current team checks,
current broker reconciliation, and confirmed notification delivery. Multiple
normal cycles must be observed after deployment; a manually edited health flag
is not acceptance. Dashboard UX, paper-only routing, risk limits, execution
ownership and broker reconciliation remain unchanged.

The full conversation shows the same recurring engineering mistake: equating
implementation checks or one successful refresh with durable operational
health. This release narrows that gap with explicit empty-state contracts,
transition/failure testing and an observer outside the trading process. It does
not establish unlimited uptime, positive expectancy or a trade-frequency promise.
Long-running market-session certification still requires real elapsed sessions.
Network loss, Telegram delivery uncertainty and credentials may still require
escalation; safely reporting that is preferable to duplicate writes or invented
success. The Mac must remain awake and connected.
