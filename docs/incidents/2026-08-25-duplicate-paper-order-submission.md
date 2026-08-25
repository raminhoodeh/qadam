# Duplicate Paper Order Submission Incident - 25 August 2026

## Impact

Between 22:15 UTC on 24 August and 00:21 UTC on 25 August, repeated guarded
PaperOps passes submitted 20 Alpaca Paper market orders while the US market was
closed. Eighteen were duplicate NVDA opening sells; the other two attempted to
close the existing BNO and ITA positions. None filled. The operator was stopped
and all 20 pending orders were cancelled before the next market open. The live
paper account retained 2 BNO and 1 ITA positions.

## Root Cause

Qadam enforced idempotency per research record, but did not enforce one
aggregate economic-exposure reservation per symbol. Distinct research lineage
and idempotency keys therefore allowed several orders expressing the same NVDA
exposure. Router checks also depended on a broker mirror that could lag a
successful POST, leaving a race before the next refresh.

A separate deployment preflight invoked the mutating canonical PaperOps wrapper
while trying to verify dashboard readiness. Repeated verification therefore had
the ability to submit orders. Health reporting checked service circuits and
artifact freshness, but did not treat duplicate pending exposure as a critical
operator-health failure.

## Corrective Actions

- Add batch-level symbol reservations in Router V3.
- Treat successful, not-yet-mirrored submissions as durable pending exposure.
- Serialize the final broker read-and-POST sequence with a process lock.
- Re-read Alpaca Paper orders, positions, account, clock and asset state
  immediately before every POST.
- Block opening or increasing an already-held symbol, duplicate pending orders,
  after-hours market orders and unsafe short openings.
- Allow only bounded close orders against an existing matching position.
- Make dashboard deployment preflight report-only.
- Mark duplicate or stale pending market orders as a critical operator repair
  and block guarded PaperOps scheduling.
- Provide an incident-scoped, paper-only quarantine tool whose default is dry
  run and whose audit record excludes raw broker identifiers.

## Verification

The incident quarantine selected exactly 20 orders and submitted 20 successful
paper cancellations with zero failures. A subsequent live read-only Alpaca
mirror reported zero open orders, two open positions, disabled live capital and
no broker-write authority. The focused regression suite covers batch
reservation, mirror-lag reservation, broker preflight, operator-health
invariants, quarantine boundaries and read-only deployment verification.

## Trust Boundary

This repair prevents the identified duplicate-exposure and verification-side
effect paths. It does not prove investment performance or guarantee that no
future defect is possible. Qadam remains paper-only; production confidence must
come from broker reconciliation, invariant monitoring and unattended soak
evidence, not from a component-level green status alone.
