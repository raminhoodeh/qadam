# Storage Capacity and Recovery Classification Repair

## Recorded incident

On 11 September the central database reached its 512 MiB internal ceiling.
Approximately 385 MiB was `service_runs`, not portfolio or research authority.
File-system maintenance checked free disk and rotated JSONL files, but never
bounded the SQLite copy of those receipts. Every later growth transaction could
roll back, including source capture, shadow benchmarks, Router and execution
reconciliation. The Mac still had roughly 275 GiB free.

On 12 September a lifecycle read printed a typed transient-network failure.
The supervisor matched `schema_version` elsewhere in the same stdout first and
classified the failure as schema drift, disabling retries. Shadow dependency
failures were also mislabeled as independent code defects.

## Implemented protections

- Before each dispatch, inspect database capacity separately from free disk.
  Archive old service-run telemetry when the hot row count exceeds 10,000 or
  live database usage reaches 70 percent. Keep the newest 5,000 runs and the last
  run of each service. Archive at most 100 batches of 1,000 rows per pass.
- Each archive preserves full rows and payload hashes, is compressed, fsynced,
  reread and digest-verified before deletion under a SQLite writer transaction.
  Interrupted batches retain database rows or their already verified archive.
  These archives are not subject to disposable JSONL telemetry pruning.
- Reuse SQLite free pages when enforcing the unchanged 512 MiB live-data cap.
  No risk limits are enlarged. No hypotheses, decisions, orders, fills, positions,
  outcomes, execution leases, idempotency records or safety state are pruned.
- Report capacity warnings and maintenance failures through the existing
  storage check. Continued protected-ledger growth still requires explicit
  capacity management; finite storage cannot provide infinite retention.
- Honor explicit failure classes before incidental metrics. Preserve safety,
  research-integrity and credential failures as non-retryable. Treat exact
  capacity and dependency diagnostics as bounded maintenance/revalidation work.
- A reviewed build may reinterpret an old failure only from the matching
  failed-command receipt. It leaves the circuit open for actual revalidation.
- New capacity failures receive a specific execution-freeze reason. Only the
  execution owner may clear it after two fresh agreeing broker reconciliations
  with matching position-protection digests. Unknown control-plane errors,
  manual stops and unexplained exposure are not auto-cleared.
- The one-time migration of the old generic freeze requires its time-matched
  PaperOps failure receipt proving the size-ceiling exception. It changes only
  the incident classification, records an audit event, and keeps execution frozen.

## Verification and operational boundary

Regression tests cover repeated growth without raising the cap, full-capacity
recovery, archive corruption and rollback, bounded/dry runs, typed diagnostics,
safe incident migration, protected circuit classes, and two-observation recovery.
The real 512 MiB database copy was reduced to about 157 MiB live data while all
25 non-telemetry tables remained byte-for-byte equivalent as serialized rows.
SQLite integrity and foreign-key checks passed and a new transaction succeeded.

Release verification must additionally confirm the exact running build, fresh
services, zero circuits/repairs, current broker reconciliation and signed public
publication. An operational pass is not a completed real unattended soak or a
profit guarantee. Existing paper-only, single-owner, Q-CTRL and dashboard UX
boundaries remain unchanged.
