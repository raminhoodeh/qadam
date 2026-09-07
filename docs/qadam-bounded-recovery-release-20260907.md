# Bounded Recovery and Unattended Sign-Off

## Incident

The September 7 owner receipts show repeated full-heal batches. One 19-service
revalidation took approximately 41 minutes. Earlier services aged beyond their
30-minute health deadline before the batch finished. A second recovery batch
immediately repeated much of that work. These were actual operator-owned
recovery runs, not evidence that an ordinary scheduler cycle had those timings.

A later qualitative-evidence run failed at generation publication with an
`Operation not permitted` error. Its abbreviated receipt does not identify the
exact filesystem operation. Metadata-copy hardening addresses one reproducible
failure mode; it is not proof that every permission error has the same cause.

## Reviewed Changes

- The installed owner uses incremental recovery through its ordinary dispatcher.
  Recovery no longer runs an entire forced service batch before normal work.
  The synchronous compatibility entry point remains for explicit integration
  checks, not the installed unattended loop.
- Each dispatch has a 120-second scheduling budget, checked between completed
  services. Running transactions are not killed at that boundary. Existing
  command timeouts, resource locks, process leases and broker reconciliation
  continue to apply. A single slow service can exceed this scheduling budget.
- Deadline slack includes measured whole-service duration. Overdue publication,
  market and research work can precede domain overflow instead of starving at
  the back of a batch. Reservations remain the ordering tie-breaker.
- Concurrent recovery requests coalesce atomically without discarding progress.
  Completed work must have a post-request receipt from the exact running build.
  Worker launch identity is retained in its completion receipt. A worker start,
  busy lock, stale receipt, future timestamp or another build is not completion.
- Recovery obeys retry deadlines, requires circuit confirmation, and limits
  failed attempts per service and request. Unrepairable research work does not
  suppress unrelated safe repairs. Safety and research-integrity holds remain
  hard stops; recovery cannot edit policy or bypass guarded PaperOps.
- Immutable generations copy bytes rather than platform file metadata. The
  copied bytes must match the pre-copy identity before pointer publication.
  Concurrent source changes fail closed and enter bounded revalidation.
- A current market-closed check does not require an execution-time generation
  join, but it cannot hide a previous bad executed join. The scheduler consults
  the existing provider calendar, including holidays and early closes.
- New soak samples are timestamped at verification completion and carry a
  verified provider market period. Weekday wall-clock time cannot manufacture
  an open-market observation. No soak credits are backfilled.
- `operational_ready` now also requires current service health. Telegram health
  reports include recovery progress and distinguish current health from final
  unattended certification. Stale pattern-message evidence requests the actual
  producing services instead of appearing only in a message suffix.

## Acceptance

Regression tests cover resumable/coalesced recovery, exact-build receipt binding,
deadline ordering, service-boundary yielding, fault isolation, generation copy
failure and races, worker lineage, and closed-market generation checks. The
broader existing regression suite must pass on the released tree.

After activation, verify the lease against the exact tested commit, no duplicate
owner, complete recovery receipts, all registered services fresh, zero open
circuits/repair requests, current signed public status, and current research
messaging. Observe multiple ordinary cycles without requesting another forced
full heal. Retain the real receipts and elapsed timestamps in the runtime audit.

## Sign-Off Boundary

An instantaneous healthy snapshot is not unattended sign-off. The existing
permanent reliability certificate still requires a contiguous 24-hour soak,
120 real observations, both verified open and closed market periods, and every
engineering certification group passing on this release. Other strategy and
market-session admission requirements are unchanged.

Network, provider, credential, storage and hardware failures cannot be guaranteed
never to occur. The acceptance target is bounded recovery, truthful degradation,
safe handling of existing paper exposure, and explicit escalation when reviewed
automatic actions cannot resolve a fault. No larger positions, forced trades,
live-capital access or profitability claim is introduced by this release.
