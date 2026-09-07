# Calendar-Aware Health and Verified Repair Closure

## Root Cause

The September 7 operator correctly used Alpaca's exchange calendar and did not
schedule open-market conversion during the holiday. The dashboard freshness
audit instead used Monday-to-Friday wall-clock hours. At 13:30 UTC it switched
Friday's EF11 validation artifacts to the 30-minute open-market deadline and
created a repair request. The older 72-hour weekend allowance would also have
expired before Tuesday's opening.

The independent critic inspected critical repair counts but not noncritical
artifact repair requests. It could consequently report healthy while the
operator reported observation_ready=false and restarted its continuous soak.

## Changes

- The freshness audit and critic use the same verified provider-calendar
  primitive as the operator. Missing, expired, malformed, uncovered or
  future-dated calendars cannot grant a closed-market allowance. A fresh
  provider-clock disagreement also prevents that allowance.
- EF11 carry-forward measures elapsed regular-session time, including provider
  holidays, early closes and daylight-saving boundaries. Old records retain
  their original timestamp, hash and explicit display label. They are counted
  separately as not_due_market_closed, never counted as freshly regenerated.
- At opening, the ordinary 30-minute producer-health deadline resumes. A
  carried record is labelled awaiting_open_revalidation until that deadline;
  missing records or previously missed session work remain failures. This is
  not execution evidence: trade-time clocks, liquidity checks, decision
  generations, risk limits and guarded PaperOps are unchanged.
- The read-only broker mirror renews its calendar before the existing six-hour
  validity limit, with a 15-minute refresh margin. It does not extend calendar
  validity or manufacture a new observation timestamp for cached data.
- Every monitored artifact has an explicit, tested producer mapping. Known
  stale-artifact requests queue those producers plus dashboard/publication
  through the existing singleton operator. Unknown requests and unsafe
  circuits remain visible blockers; there is no direct broker or policy path.
- The critic now carries open repair details, classifies noncritical open
  repairs as unresolved, and independently refuses a successful final
  verification while any operator repair remains open. Unexplained operator
  non-readiness cannot be labelled healthy either.

## Acceptance and Limits

Tests cover the actual holiday/next-open sequence, a long weekend beyond
72 hours, an early close, daylight-saving changes, missing and invalid evidence,
calendar-cache renewal, producer routing, unsafe circuits, and repair closure.
The broader operator, execution, dashboard and learning regression suite must
also pass on the release commit.

Live acceptance requires the exact reviewed build, a cleared repair queue,
fresh services and public status, a new successful critic pass, and ordinary
healthy cycles without manual artifact rewriting or forced trades. The real
24-hour/120-observation unattended certificate restarts on this new build;
no prior soak time or market-session credits are imported.

This removes the identified calendar inconsistency and false healthy verdict.
It does not guarantee recovery from every external outage or trading profits.
