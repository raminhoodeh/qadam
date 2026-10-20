# Conversion Publication And Recovery Repair

Date: 20 October 2026, Asia/Dubai.

## Observed Failure

The conversion command completed successfully at 17:26:50 UTC (21:26:50 Dubai),
with zero orders and zero broker writes. The service nevertheless failed while
publishing its artifact generations:

`generation_source_changed_during_copy:qadam_improvement_pipeline_dashboard.json`

The durable failing receipt is `operator-receipt:0fb8191b8f6a1b3512c770bf`.
It records a successful command followed by a publication error. The evidence
does not support calling this a failed strategy calculation or an attempted
trade. The operator later reported 20/21 services fresh, an open conversion
circuit and two repair requests. Position protection remained healthy.

## Root Causes

1. Publication verified ownership of declared outputs, then copied every live
   file registered to each affected resource, including other producers' files.
   A resource generation therefore depended on unrelated mutable dashboard work.
2. The operator dashboard rewrote four learning-owned files without owning the
   learning resource: the learning-cycle dashboard/events and improvement
   dashboard/proposals. That violated the single-producer contract and supplied
   the conflicting write observed during the conversion snapshot.
3. The conversion registry retained a no-automatic-broker-write retry class and
   a PaperOps dependency despite its worker command being broker-disabled with
   `--no-paperops`. The dispatcher rejected safe recovery of that exact command.
   It opened the circuit after the first failure and required outside repair.
4. Isolated worker launch/completion omitted the circuit-revalidation metadata
   present in synchronous dispatch. That could lose the stable repair identity
   and prevent stability retry counts from representing actual worker attempts.

## Repair Contract

- Publish only the current service's declared, ownership-checked output files.
  Other producers' files come from the last validated immutable generation,
  protected by a reader lease. Record carried-forward provenance explicitly;
  preserve their existing bytes and observation times.
- With no previous pointer, publish only declared outputs. An invalid existing
  generation is an integrity failure, not permission to silently bootstrap or
  replace it. Missing foreign artifacts remain unavailable until their owner
  publishes them.
- Retry a changing output capture at most three times. These retries copy files
  only: they cannot rerun conversion commands or broker operations. Repeated
  changes leave the previous pointer intact and produce a typed failure.
- Dashboard refresh still embeds fresh learning views in its own view model,
  but no longer writes canonical learning-owned files. The learning service
  remains their publisher; dashboard UX and navigation are unchanged.
- Permit automatic transient recovery only for the exact reviewed conversion
  command and its exact broker-disabled canary. Missing flags, extra arguments,
  a substituted executable or a broker wrapper cannot qualify. Research-lock,
  market-session, dependency, resource, evidence and release checks remain.
- Persist revalidation metadata before starting a worker and bind its completion
  receipt to that run. Count failed stability attempts; require three successful
  confirmations on one executable repair identity to close an open circuit.
- Transient consistency failures retain the existing 5/10/20/40/60-second
  backoff, bounded stability recovery and three-hour cooldown probe after
  exhaustion. Credential, safety, integrity and unreviewed code defects do not
  gain automatic conversion-retry authority. Repeated failure remains visible.
- The guarded execution owner retains its existing reconciliation-first recovery
  protocol. No blind retry of a potentially accepted broker POST is introduced.
  No risk limits, trading gates, account identity, paper epoch or live-capital
  settings change.

## Verification And Deployment

Regression coverage reproduces the observed foreign-file race, enforces the
single learning writer, verifies byte-only capture retries and unchanged last-good
pointers, rejects corrupt prior generations and unsafe commands, and exercises
normal dispatcher recovery through three confirmations. Worker tests verify
metadata is persisted before process start, failure counts are bounded and a
cooldown probe can later resume safe work.

Live acceptance requires the existing open circuit to recover after deployment
through the normal singleton operator, without manually clearing circuit JSON or
launching a second execution owner. Inspect the durable worker/service receipts,
new immutable-generation provenance, refreshed conversion certification, repair
queue, broker reconciliation and signed dashboard publication. An accepted
conversion with no admissible setup is a valid result; a forced trade is not a
recovery test.

The final source commit is recorded in the running build identity. Live evidence
is retained in `data/runtime/qadam_conversion_recovery_release_verification_20261020.json`
and the existing canonical service/worker receipt history. This verification
record is not execution authority.

This repair addresses the identified race and the recovery-policy mismatch. It
does not promise immunity to unrelated software, provider, disk or host failures,
nor establish profitable strategies. The five-real-session reliability sign-off
remains separate from this cause-specific recovery check.
