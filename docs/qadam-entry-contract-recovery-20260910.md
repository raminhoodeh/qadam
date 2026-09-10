# Entry Contract and Transport Recovery Repair

## Incident

On 10 September 2026, the repaired broker-history path successfully closed ITA,
NVDA, XAR and XLE. No new entry followed. Inspection identified three separate
problems, not a recurrence of the truncated broker history:

1. Router consumed a 3 September release projection for risk policy version 5,
   despite the durable 6 September amendment already approving version 6.
2. Graph hypotheses did not carry the nested market-confirmation copy that
   Router expected. Sizing had independently measured market price and
   volatility, but Router treated those measurements as missing.
3. The read-only mirror's `ConnectError` was classified as `code_defect` rather
   than a transient transport failure. The service stopped without a read retry.

## Repairs

- Router revalidates the original launch receipt, epoch, calendar, current
  policies and signed-off amendment bindings on every evaluation. It republishes
  the derived readiness in the existing bounded generation store. This does not
  create approval, reset the trial or accept a new unapproved policy version.
- Discovery confirmation consumes sizing evidence only when hypothesis, symbol,
  Akber result, decision generation and evidence digest agree. It requires a
  recent, non-future proposal with positive measured price and volatility and the
  guarded paper route. Current trigger evidence remains required.
- The broker checker preserves typed network and HTTP-status failures without
  exposing exception details or credentials. Known transient reads use bounded
  retries and the existing low-frequency recovery probe. Authentication errors,
  safety violations, schema failures and unknown code defects remain separate.
- The continuously scheduled broker-disabled journey suite now includes the
  graph-shaped hypothesis path through real evidence, sizing, Router and handoff
  functions. A future regression fails the service check instead of looking like
  normal inactivity.

## Boundaries and Acceptance

No numeric risk limit, broker-write owner, exit policy, Q-CTRL check, idempotency
rule, live-capital restriction or dashboard UX is changed. Broker-disabled
journeys test reachability, not trading performance, and grant no research proof.

Release acceptance requires passing targeted regression tests, the full journey
suite, a safe exact-build deployment, resident-owner service revalidation and
fresh broker reconciliation. A live pass with no accepted candidate is reported
as idle, not as a trade. The real unattended soak must complete on the released
build; a one-time health check is not permanent reliability or a profit guarantee.
