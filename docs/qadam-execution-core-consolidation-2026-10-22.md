# Execution Core Consolidation

## Incident And Scope

At inspection, the running reviewed build had 20 of 21 services fresh, but
`guarded_paperops` was open after the legacy PT-8 checker reconstructed an
unarmed delegation from operator lease, service-running and guarded-route JSON.
The blocked owner also stopped timely canonical reconciliation and exit care.
The exact original event that made those projections disagree is unproven;
the confirmed design fault is multiple mutable authority reads on the executing
path. A reachable process was incorrectly presented as sufficient reassurance.

Separately, Gemini generation repeatedly returned HTTP 402 despite a successful
model-list probe. The owner then supplied a Google Cloud suspension notice.
This is an external account/security investigation, not a code repair or proof
of a confirmed compromise. No new account, credential purchase or appeal is
performed by this release.

## Six Consolidation Phases

| Phase | Implemented change | Acceptance |
| --- | --- | --- |
| 1. Authority | Reviewed execution policy in schema 7; immutable per-pass binding to fenced owner, epoch, code digest and entry/care scope. | Stale scheduler JSON cannot revoke a legitimate pass; wrong/expired tokens and policy/code changes block execution. |
| 2. Execution owner | Entry POST and executing exit engine require the same durable contract. Existing sole-owner lease, prewrites, reconciliation and idempotency remain. | A care-only pass cannot authorize an entry; no new broker-writing process or risk threshold. |
| 3. Care isolation | Independent registered care job uses the same wrapper/lock, with no research or entry-circuit dependency. | Care-only wrapper never calls entry routing and does not overwrite the entry summary; dispatch continues under an entry circuit/research lock. |
| 4. Recovery and liveness | Explicit failure classes, current broker-health alerts through the existing outbox, separate care/entry reporting. Suspended Gemini calls are held explicitly. | Stale reconciliation triggers a deduplicated alert even with a green heartbeat; account action is never labelled self-healed. |
| 5. Retirement and migration | Legacy scheduler checker removed from executing sequence, redundant ownership re-read removed. Compatibility diagnostics retained. Approved dashboard hashes refreshed to the already deployed release. | All pre-existing ledger table rows, payloads and migration receipts survive isolated migration; only empty new tables permitted. |
| 6. Release and observation | Maintenance/drained cutover, reviewed policy installation, scheduled revalidation, signed publication checks, existing dashboard UX. | Record actual deployed build and live receipts separately; no simulated 24-hour/five-session assurance or profitability claim. |

## Unchanged Constraints

Alpaca Paper only. Existing validated/discovery strategy admission, portfolio
risk, fresh executable quote, direction, invalidation, provider-backed liquidity,
pre/post-submit reconciliation, exactly-once identity and exit controls remain.
No forced trade, quota, fabricated evidence, capital increase or live broker
authority is introduced. Research rank is not an expected-return estimate.

The operator and watchdog remain responsible for bounded known repairs. A
nonrecoverable code defect or external account suspension is visible and
escalated, not patched automatically. Healthy operation is not guaranteed profit
or indefinite host uptime. Review real session coverage and independent net
outcomes before increasing experimental allocation.

## Pre-Deployment Verification

- Full isolated suite with network disabled: 1,803 passed. The 200 warnings are
  the existing Qiskit IBM plugin deprecation.
- Ruff passed for all 32 changed/new Python files; `git diff --check` passed.
- Actual-ledger read-only replay migrated schema 6 to 7 in a private snapshot:
  all pre-existing rows, payload hashes and migration receipts unchanged;
  integrity checks passed and zero foreign-key errors. The new policy table was
  empty before explicit deployment approval. No broker/notification calls.
- Protected dashboard audit: four of four approved assets match production
  frontend `d5708b83a20b53158e31cec6e4d2e4b7ea21a773`; no UX rewrite.
- Production observation is recorded after installation, separately from these
  code-level results. Provider account restoration and real elapsed sessions
  cannot be claimed from test fixtures.

Live cutover found one response-contract omission in the newly introduced
Gemini hold: `credential_configured` was missing, so a downstream provider
summary raised `KeyError`. The follow-up preserves the complete probe contract
and tests the actual summary consumer with a held account. It does not relabel
the suspended account as healthy. The execution circuit independently completed
three successful revalidations and closed; broker care remained current.
