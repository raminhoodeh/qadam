# Broker History Recovery

## Incident

On 9 September 2026 at 13:33 UTC, the BNO protective paper exit filled. The
subsequent reconciliation failed with `position_entry_allocation_unresolved:ITA`.
The GET-only mirror requested only 100 orders and replaced its prior history.
An older ITA buy fell outside that window, contaminating FIFO attribution even
though the ledger still contained the broker receipt. Reconciliation then also
overwrote ITA's existing decision, exit-plan link and holding-period start.

Execution correctly froze on disagreement, but the supervisor classified the
failure as a code defect with no same-build recovery. Three-hour Telegram status
messages did not prominently explain that new entries AND due exits were blocked.
This was an engineering defect, not a trading qualification rejection.

## Repair Contract

- Traverse Alpaca order history through an empty page, including nested legs.
  Use `until` pagination and inspect saturated timestamp boundaries with a
  bounded flat overlap query. Do not assume a short nested page is complete.
- The live endpoint ignored the documented order-ID cursor during verification.
  Therefore it is not used. Nonadvancing cursors, invalid pages, ambiguous
  timestamp boundaries, exhausted page budgets and failed reads fail closed;
  incomplete fetches never replace the usable mirror.
- Keep account and epoch isolation and all unexplained-order/exposure checks.
  Failed position attribution must preserve the last verified exit contract and
  holding clock, without granting permission to use them for execution.
- For an allocation-only incident, the existing singleton PaperOps owner first
  refreshes and reconciles broker history. Two distinct provider observations,
  within 180 seconds, must pass and agree on account, epoch, positions and exit
  protection before the freeze clears. The recovery stage contains no broker
  writes. Normal entry/exit checks resume only after recovery, using existing
  idempotency records rather than replaying an earlier submission.
- A typed `broker_history_incomplete` outcome permits three bounded retries
  and the resident self-healer's existing stability revalidation schedule.
  Unknown orders, mixed reconciliation errors, manual holds and missing exit
  plans remain blocked for review. No retry fabricates missing evidence.
- The existing 60-second watchdog reports execution incidents directly to
  Telegram rather than waiting for a three-hour brief. Delivery failures retry;
  unchanged incidents are deduplicated. Verified recovery gets a separate
  message. Telegram delivery is not proof that a person read the alert.

## Verification

The targeted execution, reconciliation, mirror, attribution, epoch, operator,
critic and watchdog regression suite passed 319 tests. Changed-code Ruff and
`git diff --check` also passed.

Unit coverage includes the 100-order boundary, multiple pages, timestamp ties,
nested short pages, ignored cursors, failed reads, bounded retry classification,
preserved position lineage, matching protection receipts, unknown-order holds,
singleton recovery reads and Telegram retry/deduplication/recovery.

An isolated copy of the actual production SQLite ledger was reconciled against
two fresh broker reads on 10 September at 05:04 UTC. The provider returned 104
flattened orders. Both reconciliations passed; execution remained frozen after
the first and cleared after the second. ITA's original decision and exit plan
`exit-plan:dc286b1b665d974c97c22316` were restored with its original entry time,
3 September at 18:13:38 UTC. The replay made zero broker writes and zero writes
to the production ledger.

This fixes and tests the observed failure class. It is not a guarantee against
every future provider failure, trading loss or new defect. Real unattended soak
and market-session evidence still apply to the released build.
