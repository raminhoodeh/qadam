# PaperOps availability repair - 28 September 2026

## Observed incident

At 13:40 UTC on 28 September, the local operator was running build
`e64a35335fc99536e8960e1c4cb050f06f9745c0`, but `guarded_paperops` had an open
`code_defect` circuit dating from 27 September at 15:04 UTC. The broker's current
clock was open, the mirror was fresh, and the paper account had zero positions
and zero open orders. Running research services did not establish execution
readiness.

The failed pass recorded three failures:

- The active-automation check fell back to the paused legacy cron binding.
  Its exact operator-owner rejection was not persisted, so the original reason
  for that fallback cannot be established from that artifact alone.
- The lifecycle poll reported a typed transient provider/network failure.
- Canonical paper control rejected a reconciliation aged 1,383 seconds.
  However, the wrapper subsequently completed a fresh, successful broker
  reconciliation. Its final health verdict still described the earlier state.

The wrapper preserved a transient lifecycle error only when it was the sole
failed command. The combined failure consequently became a non-retryable code
defect. The self-healer correctly refused to reset that classification blindly,
but the classification prevented recovery after connectivity returned.

## Changes

1. Run canonical paper control after the pass's final broker refresh and ledger
   reconciliation. This changes the health-check ordering, not order authority.
   Pre-submit checks, per-write reconciliation, and execution freezes remain.
2. Persist the runtime-owner check results in the active-automation artifact.
   Emit `dependency_unavailable` only for verified scheduler/lease availability
   failures, with no additional safety, schema, or checker-probe failure.
3. Preserve bounded recovery for the combination of typed read-only lifecycle
   failures and verified owner-availability failures. Unknown submission errors,
   broker disagreement, changed authority, unsafe write counters, and schema
   failures cannot use this recovery classification.
4. Add regressions for final-check ordering, failed final broker reads, combined
   availability failures, and failures that must continue to require escalation.

## Verification and operating limits

The first real canonical revalidation completed at 13:47:26 UTC with no failed
commands or validation errors. Final reconciliation age was 0.075 seconds.
All three real revalidation passes completed successfully by 13:51:14 UTC;
the circuit closed through that procedure, not a manual JSON reset.
The regression command `python -m pytest tests/test_qadam_*.py tests/test_paperops*.py -q`
passed 1,387 tests with 200 existing Qiskit deprecation warnings. Changed-file
Ruff and `git diff --check` passed. Release verification must also match the running operator
lease to the committed build and check the normal autonomous scheduler.

No trade-frequency target, research score, risk envelope, required directional
evidence, source freshness rule, or broker route was changed. A healthy
`ready_idle` pass is not a submitted order. At the first revalidation Router had
no accepted setup and no order was submitted. At that point the leading
semiconductor relationships lacked a resolved direction; their current live
volume confirmation did not meet the existing directional-fallback rule.

This repair addresses the observed execution lockout. It cannot ensure a trade
on a particular date, uninterrupted provider availability, or positive returns.
